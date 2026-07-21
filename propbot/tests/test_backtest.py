import unittest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from propbot.backtest import BacktestRunner
from propbot.risk import RiskLimits, SymbolSpec
from propbot.schema import Candle
from propbot.strategy.orb import ORBConfig, session_open_ts

NY = ZoneInfo("America/New_York")


def build_day(day: datetime, breakout: bool) -> list[Candle]:
    """One synthetic NY session. If breakout, price runs up after the range."""
    open_ts = session_open_ts(int(day.timestamp()))
    base = 40000.0
    candles = [
        Candle(open_ts, base, base + 50, base - 50, base + 10),
        Candle(open_ts + 900, base + 10, base + 40, base - 40, base),
    ]
    for i in range(2, 24):
        t = open_ts + i * 900
        if breakout:
            price = base + 60 + (i - 2) * 8   # trend up through the high
            candles.append(Candle(t, price - 5, price + 10, price - 8, price))
        else:
            candles.append(Candle(t, base, base + 20, base - 20, base + 3))
    return candles


class TestBacktest(unittest.TestCase):
    def _runner(self):
        limits = RiskLimits(daily_loss_limit=0.05, max_drawdown=0.10,
                            drawdown_type="static", profit_target=0.10,
                            min_trading_days=0)
        spec = SymbolSpec(pip_size=1.0, pip_value_per_lot=1.0)
        return BacktestRunner(limits, spec, ORBConfig(range_minutes=30),
                              initial_balance=10000.0, slippage_points=1.0)

    def test_runs_and_produces_trades(self):
        candles = []
        for d in range(1, 8):
            day = datetime(2026, 7, d, 12, 0, tzinfo=NY)
            candles += build_day(day, breakout=(d % 2 == 0))
        result = self._runner().run(candles)
        self.assertEqual(result.initial_balance, 10000.0)
        self.assertGreater(len(result.trades), 0)
        # equity curve has one point per traded/evaluated day
        self.assertGreater(len(result.equity_curve), 0)
        # summary renders without error
        self.assertIn("Trades:", result.summary())

    def test_no_data_is_safe(self):
        result = self._runner().run([])
        self.assertEqual(result.trades, [])
        self.assertEqual(result.final_equity, 10000.0)

    def test_metrics_present(self):
        candles = []
        for d in range(1, 6):
            day = datetime(2026, 7, d, 12, 0, tzinfo=NY)
            candles += build_day(day, breakout=True)
        result = self._runner().run(candles)
        self.assertTrue(0 <= result.win_rate <= 1)
        self.assertTrue(result.max_drawdown_pct >= 0)


if __name__ == "__main__":
    unittest.main()
