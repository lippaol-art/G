import unittest

from propbot.schema import (Candle, ConfirmationRule, Direction, SetupState,
                            TradePlan)
from propbot.state import PlanStore, StateMachine
from propbot.state.machine import InvalidTransition
from propbot.watcher import Watcher, evaluate_confirmation
import tempfile
import os


def plan(**kw) -> TradePlan:
    base = dict(symbol="US30", direction=Direction.LONG,
                entry_zone_low=40000.0, entry_zone_high=40030.0,
                stop_loss=39950.0, take_profit=40100.0,
                confirmations=[ConfirmationRule("candle_close_above",
                                                {"level": 40010.0})])
    base.update(kw)
    return TradePlan(**base)


def candle(close, high=None, low=None, t=1000) -> Candle:
    return Candle(time=t, open=close, high=high or close + 5,
                  low=low or close - 5, close=close)


class TestStateMachine(unittest.TestCase):
    def test_valid_path(self):
        p = plan()
        StateMachine.transition(p, SetupState.ARMED)
        StateMachine.transition(p, SetupState.CONFIRMED)
        StateMachine.transition(p, SetupState.EXECUTING)
        StateMachine.transition(p, SetupState.OPEN)
        StateMachine.transition(p, SetupState.CLOSED)
        self.assertTrue(StateMachine.is_terminal(p))
        self.assertEqual(len(p.history), 5)

    def test_illegal_transition(self):
        p = plan()
        with self.assertRaises(InvalidTransition):
            StateMachine.transition(p, SetupState.OPEN)  # skip states

    def test_terminal_is_dead_end(self):
        p = plan(state=SetupState.EXPIRED)
        with self.assertRaises(InvalidTransition):
            StateMachine.transition(p, SetupState.ARMED)


class TestConfirmationRules(unittest.TestCase):
    def test_close_above(self):
        r = ConfirmationRule("candle_close_above", {"level": 100.0})
        self.assertTrue(evaluate_confirmation(r, [candle(101.0)]))
        self.assertFalse(evaluate_confirmation(r, [candle(99.0)]))

    def test_unknown_rule_fails_closed(self):
        r = ConfirmationRule("teleport", {})
        self.assertFalse(evaluate_confirmation(r, [candle(100.0)]))

    def test_rsi_needs_history(self):
        r = ConfirmationRule("rsi_above", {"value": 50})
        self.assertFalse(evaluate_confirmation(r, [candle(100.0)]))


class TestWatcher(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.store = PlanStore(os.path.join(self.tmp, "plans.json"))
        self.events = []
        self.watcher = Watcher(self.store, on_event=self.events.append)

    def test_arm_and_confirm(self):
        p = plan()
        self.store.upsert(p)
        # price enters zone AND closes above edge in one candle
        self.watcher.on_candle_close("US30", [candle(40015.0, t=1000)])
        self.assertIs(self.store.get(p.id).state, SetupState.CONFIRMED)
        kinds = [e.kind for e in self.events]
        self.assertIn("armed", kinds)
        self.assertIn("confirmed", kinds)

    def test_wait_then_confirm(self):
        p = plan()
        self.store.upsert(p)
        # candle in-zone but not closing above edge -> ARMED, not confirmed
        self.watcher.on_candle_close("US30", [candle(40005.0, high=40008,
                                                     low=40002, t=1000)])
        self.assertIs(self.store.get(p.id).state, SetupState.ARMED)
        # next candle closes above -> CONFIRMED
        self.watcher.on_candle_close("US30", [candle(40005.0, t=1000),
                                              candle(40020.0, t=1900)])
        self.assertIs(self.store.get(p.id).state, SetupState.CONFIRMED)

    def test_invalidation_on_stop_break(self):
        p = plan()
        self.store.upsert(p)
        self.watcher.on_candle_close("US30", [candle(39940.0, t=1000)])
        self.assertIs(self.store.get(p.id).state, SetupState.INVALIDATED)

    def test_expiry(self):
        p = plan(valid_until=500)
        self.store.upsert(p)
        self.watcher.on_candle_close("US30", [candle(40005.0, t=1000)], now=1000)
        self.assertIs(self.store.get(p.id).state, SetupState.EXPIRED)


class TestStorePersistence(unittest.TestCase):
    def test_roundtrip(self):
        tmp = tempfile.mkdtemp()
        path = os.path.join(tmp, "p.json")
        store = PlanStore(path)
        p = plan()
        StateMachine.transition(p, SetupState.ARMED)
        store.upsert(p)
        # reload from disk
        store2 = PlanStore(path)
        loaded = store2.get(p.id)
        self.assertIsNotNone(loaded)
        self.assertIs(loaded.state, SetupState.ARMED)
        self.assertEqual(loaded.direction, Direction.LONG)
        self.assertEqual(len(loaded.confirmations), 1)


if __name__ == "__main__":
    unittest.main()
