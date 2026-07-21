import unittest

from propbot.risk import RiskDecision, RiskLimits, RiskManager, SymbolSpec
from propbot.schema import AccountState, Direction, RiskZone, TradePlan


def limits(**kw) -> RiskLimits:
    base = dict(daily_loss_limit=0.05, max_drawdown=0.10,
                drawdown_type="static", profit_target=0.10,
                min_trading_days=0)
    base.update(kw)
    return RiskLimits(**base)


def acct(equity=10000.0, day_start=10000.0, initial=10000.0, hwm=10000.0,
         open_positions=0) -> AccountState:
    return AccountState(balance=equity, equity=equity,
                        day_start_equity=day_start, initial_balance=initial,
                        high_water_mark=hwm, open_positions=open_positions)


def plan(direction=Direction.LONG, grade="B") -> TradePlan:
    return TradePlan(symbol="US30", direction=direction,
                     entry_zone_low=40000.0, entry_zone_high=40010.0,
                     stop_loss=39950.0, take_profit=40100.0, grade=grade)


SPEC = SymbolSpec(pip_size=1.0, pip_value_per_lot=1.0)


class TestZones(unittest.TestCase):
    def test_green_zone_at_start(self):
        rm = RiskManager(limits())
        self.assertIs(rm.current_zone(acct()), RiskZone.GREEN)

    def test_yellow_zone(self):
        rm = RiskManager(limits())
        a = acct(equity=9750.0)          # -2.5% intraday
        self.assertIs(rm.current_zone(a), RiskZone.YELLOW)

    def test_red_zone(self):
        rm = RiskManager(limits())
        a = acct(equity=9600.0)          # -4%
        self.assertIs(rm.current_zone(a), RiskZone.RED)
        self.assertTrue(rm.should_flatten(a))


class TestFloors(unittest.TestCase):
    def test_daily_floor_uses_safety_buffer(self):
        rm = RiskManager(limits())
        # hard daily loss 5% = 500; buffered 0.8 * 500 = 400 -> floor 9600
        self.assertAlmostEqual(rm.daily_loss_floor(acct()), 9600.0)

    def test_static_max_dd_floor(self):
        rm = RiskManager(limits())
        self.assertAlmostEqual(rm.max_drawdown_floor(acct()), 9000.0)

    def test_trailing_dd_trap(self):
        """The trap from the research: profits raise the floor permanently."""
        rm = RiskManager(limits(drawdown_type="trailing"))
        a = acct(equity=10500.0, hwm=10800.0)
        self.assertAlmostEqual(rm.max_drawdown_floor(a), 9720.0)  # 10800*0.9
        # floor is now ABOVE the initial-balance floor
        self.assertGreater(rm.max_drawdown_floor(a), 9000.0)


class TestSizing(unittest.TestCase):
    def test_size_respects_budget(self):
        rm = RiskManager(limits(), slippage_pips_buffer=3.0)
        # $100 risk, 50pt stop + 3 slippage = 53 -> 1.88 -> stepped to <=$100
        vol = rm.size_position(100.0, 50.0, SPEC)
        self.assertLessEqual(vol * 53.0 * SPEC.pip_value_per_lot, 100.0 + 1e-9)
        self.assertGreater(vol, 0)

    def test_never_rounds_past_budget(self):
        rm = RiskManager(limits(), slippage_pips_buffer=0.0)
        vol = rm.size_position(10.0, 33.0, SPEC)
        self.assertLessEqual(vol * 33.0, 10.0 + 1e-9)


class TestEvaluate(unittest.TestCase):
    def test_green_zone_allows(self):
        rm = RiskManager(limits())
        d = rm.evaluate(plan(), acct(), SPEC)
        self.assertTrue(d.allowed, d.reasons)
        self.assertGreater(d.volume, 0)
        self.assertAlmostEqual(d.risk_pct, 0.01)

    def test_red_zone_vetoes(self):
        rm = RiskManager(limits())
        d = rm.evaluate(plan(), acct(equity=9500.0), SPEC)
        self.assertFalse(d.allowed)

    def test_yellow_zone_rejects_b_grade(self):
        rm = RiskManager(limits())
        d = rm.evaluate(plan(grade="B"), acct(equity=9750.0), SPEC)
        self.assertFalse(d.allowed)

    def test_yellow_zone_accepts_a_plus_at_half_risk(self):
        rm = RiskManager(limits())
        d = rm.evaluate(plan(grade="A+"), acct(equity=9750.0), SPEC)
        self.assertTrue(d.allowed, d.reasons)
        self.assertAlmostEqual(d.risk_pct, 0.005)

    def test_concurrency_cap(self):
        rm = RiskManager(limits())
        d = rm.evaluate(plan(), acct(open_positions=2), SPEC)
        self.assertFalse(d.allowed)

    def test_correlation_cap(self):
        rm = RiskManager(limits())
        d = rm.evaluate(plan(), acct(), SPEC, correlated_open=1)
        self.assertFalse(d.allowed)

    def test_projected_stopout_must_not_breach_floor(self):
        rm = RiskManager(limits())
        # equity barely above the daily floor: any loss breaches it
        d = rm.evaluate(plan(), acct(equity=9610.0), SPEC)
        self.assertFalse(d.allowed)

    def test_target_reached(self):
        rm = RiskManager(limits())
        self.assertTrue(rm.target_reached(acct(equity=11000.0)))
        self.assertFalse(rm.target_reached(acct(equity=10500.0)))


if __name__ == "__main__":
    unittest.main()
