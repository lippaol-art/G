import tempfile
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo

from propbot.config import load_settings, resolve_risk_limits
from propbot.engine import Engine
from propbot.execution.replay import ReplayAdapter
from propbot.risk import RiskManager
from propbot.schema import Candle, SetupState
from propbot.state import PlanStore
from propbot.strategy.orb import ORBConfig, session_open_ts, session_cutoff_ts

NY = ZoneInfo("America/New_York")


def quiet_day(day, base=42000.0):
    """A flat warmup day so the next day has ATR history + >=20 candles."""
    open_ts = session_open_ts(int(day.timestamp()))
    return [Candle(open_ts + i * 900, base, base + 15, base - 15, base + 3)
            for i in range(0, 26)]


def breakout_day(day, base=42000.0, then_tp=True):
    """Opening range 60pt, breaks up, then runs to TP (or reverses to SL)."""
    open_ts = session_open_ts(int(day.timestamp()))
    c = [Candle(open_ts, base, base + 30, base - 30, base + 10),
         Candle(open_ts + 900, base + 10, base + 25, base - 25, base + 5)]
    for i in range(2, 26):
        t = open_ts + i * 900
        if then_tp:
            mid = base + 35 + (i - 2) * 12      # trend up hard -> hits TP
            c.append(Candle(t, mid - 10, mid + 25, mid - 12, mid + 12))
        else:
            if i < 6:
                mid = base + 40                  # nudge above high to confirm long
                c.append(Candle(t, mid - 5, mid + 15, mid - 8, mid + 8))
            else:
                mid = base - 30 - (i - 6) * 15   # then collapse -> hits SL
                c.append(Candle(t, mid + 10, mid + 12, mid - 20, mid - 10))
    return c


class TestReplayAdapter(unittest.TestCase):
    def setUp(self):
        self.settings = load_settings()
        self.settings.entry_jitter_ms = (0, 0)
        self.orb = ORBConfig(range_minutes=30)

    def _drive(self, days_candles, auto_approve=True):
        """days_candles: list of per-day candle lists, replayed in order."""
        all_candles = [c for day in days_candles for c in day]
        adapter = ReplayAdapter("US30", all_candles, point_value_per_lot=1.0,
                                initial_balance=10000.0)
        eng = Engine(adapter, RiskManager(resolve_risk_limits(self.settings)),
                     PlanStore(tempfile.mktemp(suffix=".json")), self.settings,
                     analyst=None, orb_cfg=self.orb, news_fail_closed=False)
        closes = []
        for day in days_candles:
            eng.new_trading_day()
            open_ts = session_open_ts(day[0].time, self.orb)
            range_end = open_ts + self.orb.range_minutes * 60
            cutoff = session_cutoff_ts(day[0].time, self.orb)
            analysed = False
            while adapter.has_next() and \
                    adapter._all[adapter.cursor].time <= day[-1].time:
                c = adapter.advance()
                closes += adapter.check_exits()
                if not analysed and c.time >= range_end:
                    eng.run_daily_analysis("US30")
                    analysed = True
                if open_ts <= c.time <= cutoff:
                    events = eng.on_candle_close("US30")
                    if auto_approve:
                        for e in events:
                            if e.kind == "request_approval":
                                eng.approve(e.plan.id)
        return adapter, eng, closes

    def test_breakout_hits_tp_and_profits(self):
        d1 = datetime(2026, 3, 2, 12, 0, tzinfo=NY)
        d2 = datetime(2026, 3, 3, 12, 0, tzinfo=NY)
        adapter, eng, closes = self._drive(
            [quiet_day(d1), breakout_day(d2, then_tp=True)])
        self.assertTrue(any(r == "tp" for _, r, _ in closes), closes)
        self.assertGreater(adapter.equity, 10000.0)   # TP => profit

    def test_reversal_hits_sl_and_loses(self):
        d1 = datetime(2026, 3, 3, 12, 0, tzinfo=NY)
        d2 = datetime(2026, 3, 4, 12, 0, tzinfo=NY)
        adapter, eng, closes = self._drive(
            [quiet_day(d1), breakout_day(d2, then_tp=False)])
        self.assertTrue(any(r == "sl" for _, r, _ in closes), closes)
        self.assertLess(adapter.equity, 10000.0)       # SL => loss

    def test_no_positions_left_open_after_exit(self):
        d1 = datetime(2026, 3, 2, 12, 0, tzinfo=NY)
        d2 = datetime(2026, 3, 3, 12, 0, tzinfo=NY)
        adapter, eng, closes = self._drive(
            [quiet_day(d1), breakout_day(d2, then_tp=True)])
        self.assertEqual(adapter.positions(), [])

    def test_cursor_reveals_progressively(self):
        day = datetime(2026, 3, 3, 12, 0, tzinfo=NY)
        candles = breakout_day(day)
        adapter = ReplayAdapter("US30", candles, 1.0, 10000.0)
        adapter.advance()
        self.assertEqual(len(adapter.candles("US30", "M15", 999)), 1)
        adapter.advance()
        self.assertEqual(len(adapter.candles("US30", "M15", 999)), 2)


if __name__ == "__main__":
    unittest.main()
