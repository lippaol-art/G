import unittest

from propbot.execution import MockAdapter, execute_with_confirmation
from propbot.execution.lifecycle import reconcile
from propbot.execution.mock import RETCODE_DONE
from propbot.llm.plan_parser import PlanParseError, parse_llm_response
from propbot.market.news import NewsCalendar, NewsEvent
from propbot.schema import Direction, OrderIntent


def intent(vol=0.1) -> OrderIntent:
    return OrderIntent(symbol="US30", direction=Direction.LONG, volume=vol,
                       stop_loss=39950.0, take_profit=40100.0, plan_id="p1")


class TestLifecycle(unittest.TestCase):
    def test_happy_path(self):
        a = MockAdapter()
        a.set_price("US30", 40000.0)
        rep = execute_with_confirmation(a, intent(), reference_price=40000.0,
                                        max_slippage=5.0, news_fail_closed=False,
                                        now=1000)
        self.assertTrue(rep.ok, rep.messages)
        self.assertEqual(rep.stage, "done")
        self.assertEqual(rep.result.retcode, RETCODE_DONE)
        self.assertFalse(rep.sl_missing)

    def test_broker_reject(self):
        a = MockAdapter(reject_next=True)
        a.set_price("US30", 40000.0)
        rep = execute_with_confirmation(a, intent(), 40000.0, 5.0,
                                        news_fail_closed=False, now=1000)
        self.assertFalse(rep.ok)
        self.assertEqual(rep.stage, "send")

    def test_missing_sl_alarm(self):
        a = MockAdapter()
        a.set_price("US30", 40000.0)
        a.drop_sl_next = True
        rep = execute_with_confirmation(a, intent(), 40000.0, 5.0,
                                        news_fail_closed=False, now=1000)
        self.assertTrue(rep.sl_missing)

    def test_partial_fill_flagged(self):
        a = MockAdapter()
        a.set_price("US30", 40000.0)
        a.partial_fill_next = 0.05
        rep = execute_with_confirmation(a, intent(0.2), 40000.0, 5.0,
                                        news_fail_closed=False, now=1000)
        self.assertTrue(rep.partial)

    def test_news_gate_blocks(self):
        a = MockAdapter()
        a.set_price("US30", 40000.0)
        cal = NewsCalendar([NewsEvent(time=1000, currency="USD",
                                      impact="high", title="CPI")],
                           loaded_at=1000)
        rep = execute_with_confirmation(a, intent(), 40000.0, 5.0,
                                        calendar=cal, news_window_min=2,
                                        now=1000)
        self.assertFalse(rep.ok)
        self.assertEqual(rep.stage, "gate")

    def test_final_risk_veto(self):
        a = MockAdapter()
        a.set_price("US30", 40000.0)
        rep = execute_with_confirmation(
            a, intent(), 40000.0, 5.0, news_fail_closed=False,
            final_gate=lambda: (False, "equity moved below floor"), now=1000)
        self.assertFalse(rep.ok)
        self.assertIn("risk veto", rep.messages[0])

    def test_slippage_measured(self):
        a = MockAdapter(slippage_points=3.0)
        a.set_price("US30", 40000.0)
        rep = execute_with_confirmation(a, intent(), 40000.0, 5.0,
                                        news_fail_closed=False, now=1000)
        self.assertAlmostEqual(rep.slippage, 3.0)

    def test_reconcile_detects_missing(self):
        a = MockAdapter()
        a.set_price("US30", 40000.0)
        r = a.send_order(intent())
        diff = reconcile(a, known_tickets={r.ticket, 999})
        self.assertIn(999, diff["missing"])
        self.assertEqual(diff["unknown"], [])


class TestPlanParser(unittest.TestCase):
    def test_valid(self):
        js = ('{"trade_today": true, "grade": "A", "bias": "LONG", '
              '"confidence": 0.7, "rationale": "trend day", "warnings": []}')
        d = parse_llm_response(js)
        self.assertEqual(d.grade, "A")
        self.assertEqual(d.bias, "LONG")

    def test_strips_code_fence(self):
        js = ('```json\n{"trade_today": false, "grade": "skip", '
              '"bias": "BOTH", "confidence": 0.2, "rationale": "chop", '
              '"warnings": ["ranging"]}\n```')
        d = parse_llm_response(js)
        self.assertEqual(d.grade, "skip")
        self.assertFalse(d.trade_today)

    def test_bad_grade_rejected(self):
        js = ('{"trade_today": true, "grade": "AAA", "bias": "LONG", '
              '"confidence": 0.5, "rationale": "x", "warnings": []}')
        with self.assertRaises(PlanParseError):
            parse_llm_response(js)

    def test_skip_contradiction_rejected(self):
        js = ('{"trade_today": true, "grade": "skip", "bias": "LONG", '
              '"confidence": 0.5, "rationale": "x", "warnings": []}')
        with self.assertRaises(PlanParseError):
            parse_llm_response(js)

    def test_confidence_out_of_range(self):
        js = ('{"trade_today": true, "grade": "A", "bias": "LONG", '
              '"confidence": 1.5, "rationale": "x", "warnings": []}')
        with self.assertRaises(PlanParseError):
            parse_llm_response(js)

    def test_not_json(self):
        with self.assertRaises(PlanParseError):
            parse_llm_response("I think you should go long today!")


if __name__ == "__main__":
    unittest.main()
