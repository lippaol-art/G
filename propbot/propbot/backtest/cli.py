"""Backtest CLI.

    python -m propbot.backtest.cli US30.csv
    python -m propbot.backtest.cli US30.csv --symbol US30 --balance 10000

CSV columns: time,open,high,low,close[,volume]  (time = epoch secs or ISO).
Risk limits + symbol specs come from config (settings.yaml + prop_firms.yaml),
so the backtest runs under the SAME rules as live.
"""
from __future__ import annotations

import argparse

from dataclasses import replace

from ..config import (load_settings, resolve_orb_config, resolve_risk_limits,
                      slippage_buffer)
from ..risk import SymbolSpec
from .runner import BacktestRunner, load_candles_csv


def main() -> None:
    ap = argparse.ArgumentParser(description="ORB backtest under prop-firm rules")
    ap.add_argument("csv", help="M15 candles CSV")
    ap.add_argument("--symbol", default="US30")
    ap.add_argument("--balance", type=float, default=None)
    ap.add_argument("--range-min", type=int, default=30, help="opening range minutes")
    ap.add_argument("--target-r", type=float, default=1.5)
    args = ap.parse_args()

    settings = load_settings()
    limits = resolve_risk_limits(settings)
    balance = args.balance or settings.initial_balance
    spec = settings.symbol_specs.get(
        args.symbol, SymbolSpec(pip_size=1.0, pip_value_per_lot=1.0))

    candles = load_candles_csv(args.csv)
    print(f"Loaded {len(candles)} candles | firm={settings.prop_firm} "
          f"| DD={limits.drawdown_type} | balance={balance}")

    # Start from the configured session (broker server clock) and let CLI
    # flags override the tunables.
    orb_cfg = replace(resolve_orb_config(settings),
                      range_minutes=args.range_min, target_r=args.target_r)
    runner = BacktestRunner(
        limits, spec, orb_cfg,
        initial_balance=balance,
        slippage_points=slippage_buffer(settings),
        symbol=args.symbol)
    result = runner.run(candles)

    print("\n" + "=" * 50)
    print(result.summary())
    print("=" * 50)
    if result.max_dd_breach_day:
        print(f"⚠️  Account would be LOST on {result.max_dd_breach_day} "
              f"(max-drawdown floor breached).")
    elif result.daily_loss_breaches:
        print(f"⚠️  {result.daily_loss_breaches} daily-loss-limit breach day(s).")
    else:
        print("✅ No prop-rule breaches over the sample.")


if __name__ == "__main__":
    main()
