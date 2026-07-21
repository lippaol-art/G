"""Export historical M15 candles from MT5 to CSV — feeds the backtest.

Run on the Windows VPS with MT5 connected. Closes the data loop:
    MT5 -> CSV -> python -m propbot.backtest.cli <csv>

Usage:
    python scripts/export_mt5_candles.py US30 --days 120 --out US30_M15.csv
"""
import argparse
import csv
import sys
from datetime import datetime, timedelta, timezone

try:
    import MetaTrader5 as mt5
except ImportError:
    print("Run on the Windows VPS with MetaTrader5 installed.")
    sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("symbol")
    ap.add_argument("--days", type=int, default=120)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out = args.out or f"{args.symbol}_M15.csv"

    if not mt5.initialize():
        print("initialize() failed:", mt5.last_error()); sys.exit(1)
    mt5.symbol_select(args.symbol, True)

    end = datetime.now(tz=timezone.utc)
    start = end - timedelta(days=args.days)
    rates = mt5.copy_rates_range(args.symbol, mt5.TIMEFRAME_M15, start, end)
    mt5.shutdown()
    if rates is None or len(rates) == 0:
        print("No data returned — check symbol name / history availability.")
        sys.exit(1)

    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["time", "open", "high", "low", "close", "volume"])
        for r in rates:
            w.writerow([int(r["time"]), r["open"], r["high"], r["low"],
                        r["close"], int(r["tick_volume"])])
    print(f"✅ Wrote {len(rates)} candles to {out}")
    print(f"   Backtest:  python -m propbot.backtest.cli {out} --symbol {args.symbol}")


if __name__ == "__main__":
    main()
