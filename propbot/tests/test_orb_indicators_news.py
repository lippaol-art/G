import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from propbot.market.indicators import atr, ema, rsi, sma
from propbot.market.news import NewsCalendar, NewsEvent, news_gate
from propbot.schema import Candle, Direction
from propbot.strategy.orb import (ORBConfig, build_opening_range,
                                  make_orb_plans, session_open_ts)

NY = ZoneInfo("America/New_York")


class TestIndicators(unittest.TestCase):
    def test_sma(self):
        self.assertEqual(sma([1, 2, 3, 4], 2), 3.5)
        self.assertIsNone(sma([1], 2))

    def test_ema_reacts_faster_than_sma(self):
        # flat then a jump: EMA weights recent data, so it sits above the SMA
        vals = [10] * 20 + [20] * 5
        self.assertGreater(ema(vals, 10), sma(vals, 10))

    def test_rsi_all_gains_is_100(self):
        self.assertEqual(rsi(list(range(1, 20)), 14), 100.0)

    def test_rsi_range(self):
        vals = [44, 44.3, 44.1, 43.6, 44.3, 44.8, 45.1, 45.4, 45.4, 45.1,
                46.2, 47.1, 46.6, 46.4, 46.2, 45.6]
        r = rsi(vals, 14)
        self.assertTrue(0 <= r <= 100)

    def test_atr(self):
        candles = [Candle(i, 10, 12, 8, 11) for i in range(20)]
        self.assertIsNotNone(atr(candles, 14))


class TestORB(unittest.TestCase):
    def _session_candles(self, day, base=40000.0):
        """Build M15 candles for a session day (broker server clock)."""
        open_ts = session_open_ts(int(day.timestamp()))
        out = []
        # opening range 09:30-10:00 -> 2 M15 candles, high 40050 low 39950
        out.append(Candle(open_ts, base, base + 50, base - 50, base + 10))
        out.append(Candle(open_ts + 900, base + 10, base + 40, base - 40, base))
        # subsequent candles
        for i in range(2, 20):
            t = open_ts + i * 900
            out.append(Candle(t, base, base + 20, base - 20, base + 5))
        return out

    def test_session_open_uses_server_clock(self):
        # MT5 stamps candles on the broker server clock, stored as an
        # offset-less epoch. The session open must land at the configured
        # server hour (default 16:30 = US cash open on a GMT+2/+3 feed),
        # NOT be re-derived through a New York conversion. This holds
        # year-round because both the US and EU shift DST together.
        for month in (1, 7):   # winter (EST/EET) and summer (EDT/EEST)
            day = datetime(2026, month, 15, 8, 0, tzinfo=timezone.utc)
            ts = session_open_ts(int(day.timestamp()))
            got = datetime.fromtimestamp(ts, tz=timezone.utc)
            self.assertEqual((got.hour, got.minute), (16, 30))

    def test_session_hours_are_configurable(self):
        # A broker on a different server offset can move the window.
        day = datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc)
        cfg = ORBConfig(session_open_hour=15, session_open_minute=30,
                        cutoff_hour=21)
        ts = session_open_ts(int(day.timestamp()), cfg)
        got = datetime.fromtimestamp(ts, tz=timezone.utc)
        self.assertEqual((got.hour, got.minute), (15, 30))

    def test_build_range(self):
        day = datetime(2026, 7, 15, 12, 0, tzinfo=NY)
        candles = self._session_candles(day)
        orb = build_opening_range(candles, int(day.timestamp()),
                                  ORBConfig(range_minutes=30))
        self.assertIsNotNone(orb)
        self.assertAlmostEqual(orb.high, 40050.0)
        self.assertAlmostEqual(orb.low, 39950.0)

    def test_make_plans_long_and_short(self):
        day = datetime(2026, 7, 15, 12, 0, tzinfo=NY)
        candles = self._session_candles(day)
        orb = build_opening_range(candles, int(day.timestamp()),
                                  ORBConfig(range_minutes=30))
        plans = make_orb_plans("US30", orb, atr_value=60.0,
                               day_ts=int(day.timestamp()))
        self.assertEqual(len(plans), 2)
        longp = next(p for p in plans if p.direction is Direction.LONG)
        self.assertGreater(longp.take_profit, longp.entry_zone_high)
        self.assertLess(longp.stop_loss, longp.entry_zone_low)

    def test_degenerate_range_skipped(self):
        day = datetime(2026, 7, 15, 12, 0, tzinfo=NY)
        candles = self._session_candles(day)
        orb = build_opening_range(candles, int(day.timestamp()),
                                  ORBConfig(range_minutes=30))
        # ATR huge relative to range -> below min_range_atr -> no plans
        plans = make_orb_plans("US30", orb, atr_value=10000.0,
                               day_ts=int(day.timestamp()))
        self.assertEqual(plans, [])


class TestNewsGate(unittest.TestCase):
    def test_blackout_window(self):
        cal = NewsCalendar([NewsEvent(time=1000, currency="USD",
                                      impact="high", title="CPI")],
                           loaded_at=1000)
        hit, ev = cal.is_blackout(1030, window_min=2)   # within +2min
        self.assertTrue(hit)
        hit2, _ = cal.is_blackout(1200, window_min=2)   # outside
        self.assertFalse(hit2)

    def test_gate_blocks_during_news(self):
        cal = NewsCalendar([NewsEvent(time=1000, currency="USD",
                                      impact="high", title="NFP")],
                           loaded_at=1000)
        allowed, _ = news_gate(cal, 1000, window_min=2)
        self.assertFalse(allowed)

    def test_missing_calendar_fails_closed(self):
        allowed, reason = news_gate(None, 1000, fail_closed=True)
        self.assertFalse(allowed)

    def test_stale_calendar_fails_closed(self):
        cal = NewsCalendar([], loaded_at=0)
        allowed, _ = news_gate(cal, 10 * 3600 * 24, fail_closed=True)
        self.assertFalse(allowed)


if __name__ == "__main__":
    unittest.main()
