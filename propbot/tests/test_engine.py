import os
import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from propbot.config import load_settings, resolve_risk_limits
from propbot.engine import Engine
from propbot.execution import MockAdapter
from propbot.risk import RiskManager
from propbot.schema import Candle, SetupState
from propbot.state import PlanStore
from propbot.strategy.orb import ORBConfig, ny_session_open_ts

NY = ZoneInfo("America/New_York")


def breakout_session(day, base=40000.0):
    """Realistic proportions: 60-pt opening range, ~38-pt follow-through candles
    (so ATR ~ 0.6x the range -> ORB accepts it), trending up through the high."""
    open_ts = ny_session_open_ts(int(day.timestamp()))
    candles = [
        Candle(open_ts, base, base + 30, base - 30, base + 10),
        Candle(open_ts + 900, base + 10, base + 25, base - 25, base + 5),
    ]  # range high 40030, low 39970, size 60
    for i in range(2, 26):
        t = open_ts + i * 900
        mid = base + 35 + (i - 2) * 8      # closes above the 40030 high
        candles.append(Candle(t, mid - 10, mid + 20, mid - 18, mid + 10))
    return candles


class StubAnalyst:
    def __init__(self, grade="A", bias="LONG"):
        from propbot.llm.plan_parser import DayAnalysis
        self.da = DayAnalysis(trade_today=True, grade=grade, bias=bias,
                              confidence=0.7, rationale="stub", warnings=[])

    def analyze_day(self, pack):
        return self.da


class TestEngine(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings()
        self.settings.symbols = ["US30"]
        self.settings.entry_jitter_ms = (0, 0)   # keep tests fast
        self.risk = RiskManager(resolve_risk_limits(self.settings))
        self.adapter = MockAdapter(initial_balance=10000.0)
        self.store = PlanStore(tempfile.mktemp(suffix=".json"))
        self.day = datetime(2026, 7, 21, 12, 0, tzinfo=NY)
        self.session = breakout_session(self.day)
        self.orb_cfg = ORBConfig(range_minutes=30)

    def _engine(self, analyst=None):
        return Engine(self.adapter, self.risk, self.store, self.settings,
                      analyst=analyst, orb_cfg=self.orb_cfg,
                      news_fail_closed=False)   # no news feed in tests

    def test_daily_analysis_announces_setups(self):
        self.adapter.set_candles("US30", "M15", self.session)
        eng = self._engine(analyst=StubAnalyst(bias="LONG"))
        events = eng.run_daily_analysis("US30")
        kinds = [e.kind for e in events]
        self.assertIn("announce_setup", kinds)
        # LONG bias -> only the long plan announced
        plans = [e.plan for e in events if e.plan]
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].direction.value, "LONG")

    def test_skip_day_produces_no_plans(self):
        self.adapter.set_candles("US30", "M15", self.session)
        eng = self._engine(analyst=StubAnalyst(grade="skip"))
        events = eng.run_daily_analysis("US30")
        self.assertTrue(all(e.kind == "notify" for e in events))
        self.assertEqual(self.store.active(), [])

    def test_full_flow_to_open(self):
        eng = self._engine(analyst=StubAnalyst(bias="LONG"))
        # 1. announce (feed session through opening range)
        self.adapter.set_candles("US30", "M15", self.session)
        eng.run_daily_analysis("US30")
        plan = self.store.active()[0]

        # 2. feed post-range candles one at a time until approval requested
        orb_end = self.session[1].time + 900     # after the 2 range candles
        request = None
        seen = [c for c in self.session if c.time < orb_end]
        for c in [c for c in self.session if c.time >= orb_end]:
            seen.append(c)
            self.adapter.set_candles("US30", "M15", seen)
            self.adapter.set_price("US30", c.close)
            for ev in eng.on_candle_close("US30"):
                if ev.kind == "request_approval":
                    request = ev
            if request:
                break
        self.assertIsNotNone(request, "no approval request produced")
        self.assertIs(self.store.get(plan.id).state, SetupState.CONFIRMED)

        # 3. approve -> execute -> OPEN
        result = eng.approve(plan.id)
        self.assertIn("WYPEŁNIONE", result.text)
        self.assertIs(self.store.get(plan.id).state, SetupState.OPEN)
        self.assertIsNotNone(self.store.get(plan.id).ticket)

    def test_pause_blocks_entries(self):
        eng = self._engine()
        eng.set_paused(True)
        self.adapter.set_candles("US30", "M15", self.session)
        self.assertEqual(eng.on_candle_close("US30"), [])

    def test_status_renders(self):
        eng = self._engine()
        ev = eng.status()
        self.assertIn("Status konta", ev.text)

    def test_monitor_flattens_in_red_zone(self):
        eng = self._engine()
        # open a position then crash equity into the red zone
        self.adapter.set_price("US30", 40000.0)
        from propbot.schema import Direction, OrderIntent
        r = self.adapter.send_order(OrderIntent(
            symbol="US30", direction=Direction.LONG, volume=0.1,
            stop_loss=39900.0, take_profit=40200.0, plan_id="x"))
        # register an OPEN plan so reconcile/flatten can see it
        from propbot.strategy.orb import make_orb_plans, build_opening_range
        orb = build_opening_range(self.session, self.session[-1].time, self.orb_cfg)
        plan = make_orb_plans("US30", orb, 60.0, self.session[-1].time,
                              self.orb_cfg)[0]
        from propbot.state import StateMachine
        for st in (SetupState.ARMED, SetupState.CONFIRMED, SetupState.EXECUTING,
                   SetupState.OPEN):
            StateMachine.transition(plan, st, "test")
        plan.ticket = r.ticket
        self.store.upsert(plan)
        # drive equity to -4% (red)
        self.adapter.equity = 9600.0
        events = eng.monitor()
        self.assertTrue(any("RED" in e.text for e in events))
        self.assertEqual(self.adapter.positions(), [])


if __name__ == "__main__":
    unittest.main()
