import json
import os
import tempfile
import unittest

from propbot.config import (load_settings, news_window_min,
                            resolve_risk_limits, slippage_buffer)
from propbot.market import calendar as cal


class TestConfig(unittest.TestCase):
    def test_loads_example(self):
        s = load_settings()
        self.assertEqual(s.prop_firm, "the5ers_high_stakes")
        self.assertIn("US30", s.symbol_specs)

    def test_resolve_limits_trailing(self):
        s = load_settings()
        rl = resolve_risk_limits(s)
        self.assertEqual(rl.drawdown_type, "trailing")
        self.assertAlmostEqual(rl.daily_loss_limit, 0.05)
        self.assertAlmostEqual(rl.profit_target, 0.10)   # p1 high stakes
        self.assertAlmostEqual(rl.safety_buffer, 0.80)

    def test_news_window_and_buffer(self):
        s = load_settings()
        self.assertEqual(news_window_min(s), 2)
        self.assertGreater(slippage_buffer(s), 0)

    def test_correlation_group(self):
        s = load_settings()
        grp = s.correlation_group_of("US30")
        self.assertIn("NAS100", grp)


class TestCalendar(unittest.TestCase):
    def test_ff_csv_to_json_and_validate(self):
        tmp = tempfile.mkdtemp()
        csv_path = os.path.join(tmp, "ff.csv")
        json_path = os.path.join(tmp, "cal.json")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("Title,Country,Date,Time,Impact\n")
            f.write("CPI y/y,USD,2026-07-21,14:30,High\n")
            f.write("Random chat,EUR,2026-07-21,10:00,Low\n")
            f.write("Bank Holiday,USD,2026-07-21,All Day,High\n")
        n = cal.from_forexfactory_csv(csv_path, json_path)
        self.assertEqual(n, 1)                 # only the timed high-impact event
        with open(json_path) as f:
            data = json.load(f)
        self.assertEqual(data[0]["currency"], "USD")

        # loads back and blocks at the event time
        calendar = cal.load(json_path)
        from datetime import datetime, timezone
        ts = int(datetime(2026, 7, 21, 14, 30, tzinfo=timezone.utc).timestamp())
        hit, _ = calendar.is_blackout(ts, window_min=2)
        self.assertTrue(hit)

    def test_validate_flags_missing(self):
        problems = cal.validate("/nonexistent/cal.json")
        self.assertTrue(problems)


class TestAppWiring(unittest.TestCase):
    def test_build_engine_with_mock(self):
        from propbot.app import build_engine
        from propbot.execution import MockAdapter
        s = load_settings()
        # force mock so no MT5/Telegram/anthropic needed
        s.adapter = "mock"
        s.raw["llm"] = {"provider": "none"}
        eng = build_engine(s, adapter=MockAdapter(10000.0))
        self.assertEqual(eng.settings.prop_firm, "the5ers_high_stakes")
        # status renders through the fully-wired engine
        self.assertIn("Status konta", eng.status().text)


if __name__ == "__main__":
    unittest.main()
