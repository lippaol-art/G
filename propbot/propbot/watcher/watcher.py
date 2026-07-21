"""Candle-close watcher.

Runs deterministic checks over active TradePlans every time a candle closes.
This is the cheap hot path: no LLM, no network — a setup can sit ARMED for
hours at zero cost. State changes go through the StateMachine and are persisted
via the PlanStore, so restarts lose nothing.

Events are emitted through a callback so the Telegram layer (or a test) can
react without the watcher knowing anything about Telegram.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from ..market.indicators import closes, rsi
from ..schema import Candle, ConfirmationRule, Direction, SetupState, TradePlan
from ..state.machine import StateMachine
from ..state.store import PlanStore


@dataclass
class WatchEvent:
    """Something the outside world may want to react to."""
    kind: str            # "armed" | "confirmed" | "expired" | "invalidated" | "disarmed"
    plan: TradePlan
    detail: str = ""


def evaluate_confirmation(rule: ConfirmationRule, candles: Sequence[Candle]) -> bool:
    """Evaluate one deterministic confirmation rule on closed candles.

    Supported kinds (all operate on the LAST CLOSED candle / series):
      candle_close_above {level}      close > level
      candle_close_below {level}      close < level
      rsi_above {period=14, value}    RSI(period) > value
      rsi_below {period=14, value}    RSI(period) < value
      min_candle_range {points}       last candle high-low >= points (momentum)
    Unknown kinds fail closed (return False) — never trade on a rule we
    don't understand.
    """
    if not candles:
        return False
    last = candles[-1]
    p = rule.params
    if rule.kind == "candle_close_above":
        return last.close > float(p["level"])
    if rule.kind == "candle_close_below":
        return last.close < float(p["level"])
    if rule.kind == "rsi_above":
        val = rsi(closes(candles), int(p.get("period", 14)))
        return val is not None and val > float(p["value"])
    if rule.kind == "rsi_below":
        val = rsi(closes(candles), int(p.get("period", 14)))
        return val is not None and val < float(p["value"])
    if rule.kind == "min_candle_range":
        return (last.high - last.low) >= float(p["points"])
    return False  # fail closed


class Watcher:
    def __init__(self, store: PlanStore,
                on_event: Callable[[WatchEvent], None] | None = None):
        self.store = store
        self.on_event = on_event or (lambda e: None)

    def _emit(self, kind: str, plan: TradePlan, detail: str = "") -> None:
        self.on_event(WatchEvent(kind=kind, plan=plan, detail=detail))

    # ------------------------------------------------------------------

    def _invalidated(self, plan: TradePlan, candle: Candle) -> bool:
        """Price broke through the stop side before confirming — setup is dead."""
        if plan.direction is Direction.LONG:
            return candle.close <= plan.stop_loss
        return candle.close >= plan.stop_loss

    def on_candle_close(self, symbol: str, candles: Sequence[Candle],
                        now: int | None = None) -> list[WatchEvent]:
        """Process all active plans for `symbol` against the latest closed candle.

        `candles` must be closed candles, oldest→newest, newest = just closed.
        Returns the events produced (also sent to the callback).
        """
        produced: list[WatchEvent] = []
        if not candles:
            return produced
        last = candles[-1]
        ts = now if now is not None else last.time

        for plan in self.store.active():
            if plan.symbol != symbol:
                continue
            if plan.state not in (SetupState.WAITING_FOR_PRICE, SetupState.ARMED):
                continue  # CONFIRMED+ lifecycles are owned by approval/executor

            # 1. Expiry beats everything.
            if plan.is_expired(ts):
                StateMachine.transition(plan, SetupState.EXPIRED,
                                        "valid_until passed", now=ts)
                self.store.upsert(plan)
                ev = WatchEvent("expired", plan)
                produced.append(ev); self.on_event(ev)
                continue

            # 2. Stop side broken before entry -> invalidated.
            if self._invalidated(plan, last):
                StateMachine.transition(plan, SetupState.INVALIDATED,
                                        f"close {last.close} broke stop side", now=ts)
                self.store.upsert(plan)
                ev = WatchEvent("invalidated", plan)
                produced.append(ev); self.on_event(ev)
                continue

            # 3. Zone tracking.
            in_zone = plan.price_in_zone(last.close)
            if plan.state is SetupState.WAITING_FOR_PRICE and in_zone:
                StateMachine.transition(plan, SetupState.ARMED,
                                        f"close {last.close} entered zone", now=ts)
                self.store.upsert(plan)
                ev = WatchEvent("armed", plan)
                produced.append(ev); self.on_event(ev)
                # fall through: confirmations may already hold on this candle

            # 4. Confirmations (only when armed).
            if plan.state is SetupState.ARMED:
                if all(evaluate_confirmation(r, candles) for r in plan.confirmations):
                    StateMachine.transition(plan, SetupState.CONFIRMED,
                                            "all confirmations satisfied", now=ts)
                    self.store.upsert(plan)
                    ev = WatchEvent("confirmed", plan,
                                    detail=f"close={last.close}")
                    produced.append(ev); self.on_event(ev)
                elif not in_zone and not plan.confirmations:
                    # zone-only plans that drift out just disarm
                    StateMachine.transition(plan, SetupState.WAITING_FOR_PRICE,
                                            "price left zone", now=ts)
                    self.store.upsert(plan)
                    ev = WatchEvent("disarmed", plan)
                    produced.append(ev); self.on_event(ev)

        return produced
