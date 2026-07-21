"""ORB backtest runner.

Runs the SAME components as live trading — ORB plan factory, watcher state
machine, risk manager — over historical M15 candles, with auto-approval in
place of the human click. Purpose: validate parameters and prop-rule survival
BEFORE paying for a challenge. Not a tick-accurate simulator; conservative
assumptions (SL-first on ambiguous candles, slippage charged on entry).

CSV format (epoch seconds or ISO time):
    time,open,high,low,close[,volume]
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..market.indicators import atr
from ..risk.risk_manager import RiskLimits, RiskManager, SymbolSpec
from ..schema import AccountState, Candle, Direction, SetupState
from ..state.machine import StateMachine
from ..strategy.orb import (ORBConfig, build_opening_range, make_orb_plans,
                            ny_session_open_ts, session_cutoff_ts)


def load_candles_csv(path: str) -> list[Candle]:
    out: list[Candle] = []
    with open(path, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            t = row["time"]
            try:
                ts = int(float(t))
            except ValueError:
                dt = datetime.fromisoformat(t)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                ts = int(dt.timestamp())
            out.append(Candle(time=ts, open=float(row["open"]),
                              high=float(row["high"]), low=float(row["low"]),
                              close=float(row["close"]),
                              volume=float(row.get("volume", 0) or 0)))
    out.sort(key=lambda c: c.time)
    return out


@dataclass
class Trade:
    day: str
    direction: str
    entry: float
    exit: float
    volume: float
    pnl: float
    r_multiple: float
    reason: str          # "tp" | "sl" | "eod"


@dataclass
class BacktestResult:
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    initial_balance: float = 0.0
    daily_loss_breaches: int = 0
    max_dd_breach_day: str = ""       # first day the account would be lost
    skipped_days: int = 0

    @property
    def final_equity(self) -> float:
        return self.equity_curve[-1] if self.equity_curve else self.initial_balance

    @property
    def total_pnl(self) -> float:
        return sum(t.pnl for t in self.trades)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        return sum(1 for t in self.trades if t.pnl > 0) / len(self.trades)

    @property
    def profit_factor(self) -> float:
        gains = sum(t.pnl for t in self.trades if t.pnl > 0)
        losses = -sum(t.pnl for t in self.trades if t.pnl < 0)
        return gains / losses if losses > 0 else float("inf")

    @property
    def max_drawdown_pct(self) -> float:
        peak, max_dd = float("-inf"), 0.0
        for e in self.equity_curve:
            peak = max(peak, e)
            if peak > 0:
                max_dd = max(max_dd, (peak - e) / peak)
        return max_dd

    def summary(self) -> str:
        return (
            f"Trades: {len(self.trades)} | WR: {self.win_rate:.1%} | "
            f"PF: {self.profit_factor:.2f}\n"
            f"PnL: {self.total_pnl:+,.2f} "
            f"({self.total_pnl / self.initial_balance:+.2%})\n"
            f"Max DD: {self.max_drawdown_pct:.2%} | "
            f"Daily-loss breaches: {self.daily_loss_breaches} | "
            f"Account lost: {self.max_dd_breach_day or 'no'}\n"
            f"Skipped days: {self.skipped_days}"
        )


class BacktestRunner:
    def __init__(self, limits: RiskLimits, spec: SymbolSpec,
                 orb_cfg: ORBConfig | None = None,
                 initial_balance: float = 10000.0,
                 slippage_points: float = 1.0,
                 symbol: str = "US30"):
        self.limits = limits
        self.spec = spec
        self.orb_cfg = orb_cfg or ORBConfig()
        self.initial_balance = initial_balance
        self.slippage = slippage_points
        self.symbol = symbol
        self.risk = RiskManager(limits, slippage_pips_buffer=slippage_points)

    def _group_days(self, candles: list[Candle]) -> dict[str, list[Candle]]:
        days: dict[str, list[Candle]] = {}
        for c in candles:
            key = datetime.fromtimestamp(c.time, tz=timezone.utc).strftime("%Y-%m-%d")
            days.setdefault(key, []).append(c)
        return days

    def run(self, candles: list[Candle]) -> BacktestResult:
        result = BacktestResult(initial_balance=self.initial_balance)
        equity = self.initial_balance
        hwm = equity
        atr_window: list[Candle] = []

        for day_key, day_candles in sorted(self._group_days(candles).items()):
            day_start_equity = equity
            open_ts = ny_session_open_ts(day_candles[0].time, self.orb_cfg)
            cutoff = session_cutoff_ts(day_candles[0].time, self.orb_cfg)

            # ATR from the trailing window before today
            atr_val = atr(atr_window[-100:], 14) if len(atr_window) >= 15 else None
            atr_window.extend(day_candles)
            if atr_val is None:
                result.skipped_days += 1
                continue

            orb = build_opening_range(day_candles, day_candles[0].time, self.orb_cfg)
            if orb is None:
                result.skipped_days += 1
                continue
            plans = make_orb_plans(self.symbol, orb, atr_val,
                                   day_candles[0].time, self.orb_cfg)
            if not plans:
                result.skipped_days += 1
                continue

            # walk the session candle by candle after the range forms
            session = [c for c in day_candles if orb.end_ts <= c.time <= cutoff]
            seen: list[Candle] = [c for c in day_candles if c.time < orb.end_ts]
            traded = False

            for candle in session:
                seen.append(candle)
                if traded:
                    break
                for plan in plans:
                    if plan.state is not SetupState.WAITING_FOR_PRICE and \
                            plan.state is not SetupState.ARMED:
                        continue
                    # confirmation: candle CLOSE beyond the range edge
                    is_long = plan.direction is Direction.LONG
                    edge = orb.high if is_long else orb.low
                    confirmed = candle.close > edge if is_long \
                        else candle.close < edge
                    if not confirmed:
                        continue

                    StateMachine.transition(plan, SetupState.ARMED, "bt",
                                            now=candle.time) \
                        if plan.state is SetupState.WAITING_FOR_PRICE else None
                    StateMachine.transition(plan, SetupState.CONFIRMED, "bt",
                                            now=candle.time)

                    acct = AccountState(
                        balance=equity, equity=equity,
                        day_start_equity=day_start_equity,
                        initial_balance=self.initial_balance,
                        high_water_mark=hwm, open_positions=0)
                    decision = self.risk.evaluate(plan, acct, self.spec)
                    if not decision.allowed:
                        StateMachine.transition(plan, SetupState.CANCELLED,
                                                "risk veto", now=candle.time)
                        continue

                    entry = candle.close + plan.direction.sign * self.slippage
                    pnl, exit_price, reason = self._walk_position(
                        plan, entry, decision.volume,
                        [c for c in session if c.time > candle.time])
                    equity += pnl
                    hwm = max(hwm, equity)
                    risk_per_unit = abs(entry - plan.stop_loss) \
                        * decision.volume * self.spec.pip_value_per_lot
                    result.trades.append(Trade(
                        day=day_key, direction=plan.direction.value,
                        entry=entry, exit=exit_price,
                        volume=decision.volume, pnl=pnl,
                        r_multiple=pnl / risk_per_unit if risk_per_unit else 0.0,
                        reason=reason))
                    traded = True   # max 1 trade per day per symbol
                    break

            result.equity_curve.append(equity)

            # prop-rule survival checks
            if equity <= day_start_equity * (1 - self.limits.daily_loss_limit):
                result.daily_loss_breaches += 1
            floor = self.risk.max_drawdown_floor(AccountState(
                balance=equity, equity=equity,
                day_start_equity=day_start_equity,
                initial_balance=self.initial_balance, high_water_mark=hwm))
            if equity <= floor and not result.max_dd_breach_day:
                result.max_dd_breach_day = day_key

        return result

    def _walk_position(self, plan, entry: float, volume: float,
                       remaining: list[Candle]) -> tuple[float, float, str]:
        """Candle-walk to SL/TP/end-of-day. SL-first on ambiguous candles."""
        sign = plan.direction.sign
        point_value = self.spec.pip_value_per_lot / self.spec.pip_size
        for c in remaining:
            hit_sl = c.low <= plan.stop_loss if sign > 0 \
                else c.high >= plan.stop_loss
            hit_tp = c.high >= plan.take_profit if sign > 0 \
                else c.low <= plan.take_profit
            if hit_sl:  # conservative: SL wins ambiguous candles
                exit_price = plan.stop_loss - sign * self.slippage
                return ((exit_price - entry) * sign * volume * point_value,
                        exit_price, "sl")
            if hit_tp:
                return ((plan.take_profit - entry) * sign * volume * point_value,
                        plan.take_profit, "tp")
        if remaining:
            last = remaining[-1].close
            return ((last - entry) * sign * volume * point_value, last, "eod")
        return (0.0, entry, "eod")
