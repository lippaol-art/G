"""Orchestration engine — pure, dependency-injected, testable with the mock.

Ties the layers together without knowing anything about Telegram or MT5:

  run_daily_analysis(symbol) -> announces conditional setups for the day
  on_candle_close(symbol)    -> drives the watcher; emits approval requests
  approve(plan_id)           -> final risk gate + execute + verify lifecycle
  cancel(plan_id)            -> mark the setup cancelled
  monitor()                  -> reconcile + red-zone flatten
  status()                   -> account status card

app.py wires these to Telegram + a scheduler; tests drive them directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .config import Settings, news_window_min, slippage_buffer
from .execution.base import ExecutionAdapter
from .execution.lifecycle import ExecutionReport, execute_with_confirmation, reconcile
from .llm.pack import build_analysis_pack
from .market.indicators import atr
from .market.news import NewsCalendar
from .risk import RiskManager
from .schema import Direction, OrderIntent, SetupState, TradePlan
from .state import PlanStore, StateMachine
from .strategy.orb import ORBConfig, build_opening_range, make_orb_plans
from .telegram.cards import (format_confirmed_card, format_execution_report,
                             format_setup_card, format_status, format_veto_card)
from .watcher import Watcher, WatchEvent


@dataclass
class EngineEvent:
    """Something app.py should surface to the human."""
    kind: str                       # announce_setup | request_approval | notify
    text: str
    plan: Optional[TradePlan] = None


@dataclass
class _Pending:
    plan: TradePlan
    intent: OrderIntent
    reference_price: float


class Engine:
    def __init__(self, adapter: ExecutionAdapter, risk: RiskManager,
                 store: PlanStore, settings: Settings,
                 analyst=None, calendar: Optional[NewsCalendar] = None,
                 orb_cfg: Optional[ORBConfig] = None,
                 news_fail_closed: bool = True):
        self.adapter = adapter
        self.risk = risk
        self.store = store
        self.settings = settings
        self.analyst = analyst           # AnalystClient or a stub; None -> grade B
        self.calendar = calendar
        # Fail-closed: no/stale calendar blocks execution. Only relax for
        # tests / paper runs where a news feed isn't wired up.
        self.news_fail_closed = news_fail_closed
        self.orb_cfg = orb_cfg or ORBConfig()
        self.paused = False
        self._confirmed: list[TradePlan] = []
        self.watcher = Watcher(store, on_event=self._on_watch_event)
        self.pending: dict[str, _Pending] = {}

    # --- daily analysis --------------------------------------------------

    def run_daily_analysis(self, symbol: str) -> list[EngineEvent]:
        m15 = self.adapter.candles(symbol, self.settings.timeframe, 200)
        if len(m15) < 20:
            return [EngineEvent("notify", f"{symbol}: za mało danych M15")]
        day_ts = m15[-1].time
        orb = build_opening_range(m15, day_ts, self.orb_cfg)
        if orb is None:
            return [EngineEvent("notify",
                                f"{symbol}: opening range jeszcze się nie uformował")]
        atr_val = atr(m15, 14)
        if not atr_val:
            return [EngineEvent("notify", f"{symbol}: brak ATR")]

        grade, bias, confidence, rationale = self._grade_day(symbol, m15, orb, day_ts)
        if grade == "skip":
            return [EngineEvent("notify",
                                f"📵 {symbol}: dzień oceniony 'skip' — {rationale}")]

        plans = make_orb_plans(symbol, orb, atr_val, day_ts, self.orb_cfg,
                               grade=grade, confidence=confidence,
                               rationale=rationale)
        # apply directional bias
        if bias == "LONG":
            plans = [p for p in plans if p.direction is Direction.LONG]
        elif bias == "SHORT":
            plans = [p for p in plans if p.direction is Direction.SHORT]

        events = []
        for p in plans:
            self.store.upsert(p)
            events.append(EngineEvent("announce_setup", format_setup_card(p), p))
        if not events:
            events.append(EngineEvent("notify", f"{symbol}: brak setupu na dziś"))
        return events

    def _grade_day(self, symbol, m15, orb, day_ts):
        if self.analyst is None:
            return ("B", "BOTH", 0.0, "Brak LLM — domyślny grade B (oba kierunki).")
        h1 = self.adapter.candles(symbol, "H1", 48)
        d1 = self.adapter.candles(symbol, "D1", 20)
        zone = self.risk.current_zone(self.adapter.account_state()).value
        pack = build_analysis_pack(symbol, m15, h1, d1,
                                   self.adapter.account_state(), zone,
                                   orb=orb, calendar=self.calendar, now=day_ts)
        try:
            da = self.analyst.analyze_day(pack)
        except Exception as e:  # malformed / refusal / network -> fail closed
            return ("skip", "BOTH", 0.0, f"Analiza LLM nieudana ({e}) — pomijam dzień.")
        return (da.grade, da.bias, da.confidence, da.rationale)

    # --- watcher-driven confirmation ------------------------------------

    def _on_watch_event(self, ev: WatchEvent) -> None:
        if ev.kind == "confirmed":
            self._confirmed.append(ev.plan)

    def on_candle_close(self, symbol: str) -> list[EngineEvent]:
        if self.paused:
            return []
        candles = self.adapter.candles(symbol, self.settings.timeframe, 200)
        if not candles:
            return []
        self._confirmed.clear()
        self.watcher.on_candle_close(symbol, candles, now=candles[-1].time)

        events: list[EngineEvent] = []
        for plan in self._confirmed:
            events.extend(self._handle_confirmation(plan))
        return events

    def _handle_confirmation(self, plan: TradePlan) -> list[EngineEvent]:
        acct = self.adapter.account_state()
        self.risk.update_high_water_mark(acct)
        spec = self.settings.symbol_specs.get(plan.symbol)
        if spec is None:
            return [EngineEvent("notify",
                                f"{plan.symbol}: brak specyfikacji — nie mogę policzyć wolumenu")]
        corr = self._correlated_open(plan.symbol)
        decision = self.risk.evaluate(plan, acct, spec, correlated_open=corr)
        if not decision.allowed:
            StateMachine.transition(plan, SetupState.CANCELLED, "risk veto",
                                    now=None)
            self.store.upsert(plan)
            return [EngineEvent("notify", format_veto_card(plan, decision), plan)]

        reference = self.adapter.current_price(
            plan.symbol, "ask" if plan.direction is Direction.LONG else "bid")
        intent = OrderIntent(
            symbol=plan.symbol, direction=plan.direction,
            volume=decision.volume, stop_loss=plan.stop_loss,
            take_profit=plan.take_profit, plan_id=plan.id,
            deviation_points=self.settings.deviation_points,
            magic=self.settings.magic_base, comment="propbot")
        self.pending[plan.id] = _Pending(plan, intent, reference)
        return [EngineEvent("request_approval",
                            format_confirmed_card(plan, decision, acct), plan)]

    def _correlated_open(self, symbol: str) -> int:
        group = self.settings.correlation_group_of(symbol)
        return sum(1 for p in self.store.open_positions() if p.symbol in group)

    # --- human actions ---------------------------------------------------

    def approve(self, plan_id: str) -> EngineEvent:
        pend = self.pending.pop(plan_id, None)
        if pend is None:
            return EngineEvent("notify", "Ten setup już nie oczekuje na decyzję.")
        plan = pend.plan

        def final_gate() -> tuple[bool, str]:
            acct = self.adapter.account_state()
            if self.risk.should_flatten(acct):
                return False, "red zone / floor breach at click time"
            spec = self.settings.symbol_specs[plan.symbol]
            d = self.risk.evaluate(plan, acct, spec,
                                   correlated_open=self._correlated_open(plan.symbol))
            return (d.allowed, "; ".join(d.reasons))

        StateMachine.transition(plan, SetupState.EXECUTING, "approved")
        self.store.upsert(plan)
        report: ExecutionReport = execute_with_confirmation(
            self.adapter, pend.intent, pend.reference_price,
            max_slippage=slippage_buffer(self.settings) * 2,
            calendar=self.calendar,
            news_window_min=news_window_min(self.settings),
            news_fail_closed=self.news_fail_closed,
            final_gate=final_gate,
            entry_jitter_ms=self.settings.entry_jitter_ms)

        if report.ok and report.result and report.result.ticket:
            StateMachine.transition(plan, SetupState.OPEN, "filled")
            plan.ticket = report.result.ticket
        else:
            StateMachine.transition(plan, SetupState.CANCELLED,
                                    "execution failed")
        self.store.upsert(plan)
        return EngineEvent("notify", format_execution_report(report, plan), plan)

    def cancel(self, plan_id: str) -> EngineEvent:
        self.pending.pop(plan_id, None)
        plan = self.store.get(plan_id)
        if plan and not StateMachine.is_terminal(plan):
            # cancel from wherever it currently is, if the transition is legal
            if StateMachine.can(plan.state, SetupState.CANCELLED):
                StateMachine.transition(plan, SetupState.CANCELLED, "human cancel")
                self.store.upsert(plan)
        return EngineEvent("notify", "❌ Anulowano.")

    def set_paused(self, paused: bool) -> EngineEvent:
        self.paused = paused
        return EngineEvent("notify", "⏸️ Pauza — nowe wejścia wstrzymane."
                           if paused else "▶️ Wznowiono.")

    # --- monitoring ------------------------------------------------------

    def monitor(self) -> list[EngineEvent]:
        events: list[EngineEvent] = []
        acct = self.adapter.account_state()
        self.risk.update_high_water_mark(acct)

        # red zone / floor breach -> flatten everything immediately
        if self.risk.should_flatten(acct) and self.store.open_positions():
            results = self.adapter.close_all()
            for p in self.store.open_positions():
                StateMachine.transition(p, SetupState.CLOSED, "red-zone flatten")
                self.store.upsert(p)
            events.append(EngineEvent(
                "notify", f"🔴 Strefa RED / floor — zamknięto {len(results)} "
                          f"pozycji, blokuję handel do końca dnia."))

        # reconciliation: our OPEN plans vs broker positions
        known = {p.ticket for p in self.store.open_positions() if p.ticket}
        diff = reconcile(self.adapter, known)
        for ticket in diff["missing"]:
            plan = next((p for p in self.store.open_positions()
                         if p.ticket == ticket), None)
            if plan:
                StateMachine.transition(plan, SetupState.CLOSED,
                                        "closed at broker (SL/TP?)")
                self.store.upsert(plan)
                events.append(EngineEvent(
                    "notify", f"ℹ️ Pozycja #{ticket} zamknięta u brokera "
                              f"(SL/TP lub ręcznie)."))
        for ticket in diff["unknown"]:
            events.append(EngineEvent(
                "notify", f"⚠️ Nieznana pozycja #{ticket} u brokera — sprawdź."))

        # daily-loss proximity warning
        floor = self.risk.effective_floor(acct)
        if acct.equity <= floor * 1.01 and not self.risk.should_flatten(acct):
            events.append(EngineEvent(
                "notify", f"⚠️ Blisko floora ({floor:,.2f}), equity {acct.equity:,.2f}."))
        return events

    def status(self) -> EngineEvent:
        acct = self.adapter.account_state()
        zone = self.risk.current_zone(acct).value
        floor = self.risk.effective_floor(acct)
        open_plans = len([p for p in self.store.active()])
        text = format_status(acct, zone, floor, self.risk.limits.profit_target,
                             open_plans)
        return EngineEvent("notify", text)

    def new_trading_day(self) -> None:
        """Call at broker-server midnight: resets the daily-loss reference and
        expires stale plans."""
        if hasattr(self.adapter, "new_day"):
            self.adapter.new_day()
        for p in self.store.active():
            if p.state in (SetupState.WAITING_FOR_PRICE, SetupState.ARMED,
                           SetupState.CONFIRMED):
                if StateMachine.can(p.state, SetupState.EXPIRED):
                    StateMachine.transition(p, SetupState.EXPIRED, "new day")
                    self.store.upsert(p)
        self.pending.clear()
