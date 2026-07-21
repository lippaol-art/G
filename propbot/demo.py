"""End-to-end demo on the mock adapter — no MT5, no API key, no real money.

Shows the full hybrid flow:
  1. LLM (stubbed here) grades the day and stamps a grade on the ORB plans.
  2. Watcher arms + confirms a setup on a breakout candle.
  3. Risk manager sizes the position and can veto.
  4. Human approval is simulated (auto-approve).
  5. Executor sends the order and verifies the full lifecycle.

Run:  python3 demo.py
"""
from __future__ import annotations

import tempfile
from datetime import datetime
from zoneinfo import ZoneInfo

from propbot.execution import MockAdapter, execute_with_confirmation
from propbot.risk import RiskLimits, RiskManager, SymbolSpec
from propbot.schema import Candle, OrderIntent, SetupState
from propbot.state import PlanStore, StateMachine
from propbot.strategy.orb import (ORBConfig, build_opening_range,
                                  make_orb_plans, session_open_ts)
from propbot.telegram.cards import (format_confirmed_card,
                                    format_execution_report, format_setup_card)
from propbot.watcher import Watcher

NY = ZoneInfo("America/New_York")


def build_breakout_session() -> list[Candle]:
    day = datetime(2026, 7, 21, 12, 0, tzinfo=NY)
    open_ts = session_open_ts(int(day.timestamp()))
    base = 40000.0
    candles = [
        Candle(open_ts, base, base + 50, base - 50, base + 10),
        Candle(open_ts + 900, base + 10, base + 40, base - 40, base),
    ]
    for i in range(2, 12):
        t = open_ts + i * 900
        price = base + 55 + (i - 2) * 10   # break above the range high (40050)
        candles.append(Candle(t, price - 5, price + 12, price - 6, price))
    return candles


def main() -> None:
    print("=" * 64)
    print("propbot demo — hybrid AI/human ORB flow (mock adapter)")
    print("=" * 64)

    limits = RiskLimits(daily_loss_limit=0.05, max_drawdown=0.10,
                        drawdown_type="static", profit_target=0.10,
                        min_trading_days=0)
    spec = SymbolSpec(pip_size=1.0, pip_value_per_lot=1.0)
    risk = RiskManager(limits, slippage_pips_buffer=1.0)

    adapter = MockAdapter(initial_balance=10000.0)
    store = PlanStore(tempfile.mktemp(suffix=".json"))
    watcher = Watcher(store)

    session = build_breakout_session()
    day_ts = session[0].time

    # --- 1. LLM grade (stub) + ORB plan factory -----------------------
    orb = build_opening_range(session, day_ts, ORBConfig(range_minutes=30))
    print(f"\n[LLM] Day graded 'A', bias LONG (stub)")
    print(f"[ORB] Opening range {orb.low:.0f}–{orb.high:.0f}")
    plans = make_orb_plans("US30", orb, atr_value=60.0, day_ts=day_ts,
                           grade="A", confidence=0.72,
                           rationale="Gap up + trend alignment, clean range.")
    for p in plans:
        store.upsert(p)
        print("\n" + format_setup_card(p))

    # --- 2. Watcher walks the session candle by candle ----------------
    # Only post-range candles reach the watcher (plans don't exist until the
    # opening range has formed) — same as live and the backtest runner.
    print("\n[WATCHER] streaming closed candles...")
    confirmed_plan = None
    seen: list[Candle] = [c for c in session if c.time < orb.end_ts]
    for c in [c for c in session if c.time >= orb.end_ts]:
        seen.append(c)
        events = watcher.on_candle_close("US30", seen, now=c.time)
        for e in events:
            print(f"  {e.kind.upper():12} {e.plan.direction.value} "
                  f"@ close {c.close:.0f}")
            if e.kind == "confirmed":
                confirmed_plan = e.plan
        if confirmed_plan:
            break

    if confirmed_plan is None:
        print("No confirmation today."); return

    # --- 3. Risk manager sizes + gates --------------------------------
    adapter.set_price("US30", confirmed_plan.entry_zone_high)
    acct = adapter.account_state()
    decision = risk.evaluate(confirmed_plan, acct, spec)
    print("\n" + format_confirmed_card(confirmed_plan, decision, acct))
    if not decision.allowed:
        print("Risk veto:", decision.reasons); return

    # --- 4. Human approves (simulated) --------------------------------
    print("\n[HUMAN] ✅ Wykonaj  (auto-approved in demo)")
    StateMachine.transition(confirmed_plan, SetupState.EXECUTING, "approved")

    # --- 5. Execute with full lifecycle confirmation ------------------
    intent = OrderIntent(symbol="US30", direction=confirmed_plan.direction,
                         volume=decision.volume,
                         stop_loss=confirmed_plan.stop_loss,
                         take_profit=confirmed_plan.take_profit,
                         plan_id=confirmed_plan.id)
    report = execute_with_confirmation(
        adapter, intent,
        reference_price=confirmed_plan.entry_zone_high,
        max_slippage=5.0, news_fail_closed=False, now=day_ts)
    print("\n" + format_execution_report(report, confirmed_plan))

    if report.ok and report.result.ticket:
        StateMachine.transition(confirmed_plan, SetupState.OPEN, "filled")
        confirmed_plan.ticket = report.result.ticket
        store.upsert(confirmed_plan)
        print(f"\n[STATE] plan {confirmed_plan.id} -> OPEN "
              f"(ticket {confirmed_plan.ticket})")
    print("\ndemo complete.")


if __name__ == "__main__":
    main()
