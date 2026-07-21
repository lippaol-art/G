"""Step 2 — connect MT5 (demo) and VERIFY the contract specs.

Run this ON THE WINDOWS VPS with the MetaTrader5 terminal installed and logged
into the demo account, and 'Algo Trading' enabled. It:

  1. connects to the running terminal,
  2. prints account info (balance, equity, leverage, currency),
  3. for each symbol, dumps the numbers we NEED for sizing:
     point size, tick value, min/step/max volume, digits.

Copy the point value / min lot into config/settings.yaml -> symbol_specs.
For an index CFD, pip_value_per_lot = tick_value / tick_size * point.

Usage (on the VPS):
    python scripts/check_mt5.py US30 NAS100
"""
import sys

try:
    import MetaTrader5 as mt5
except ImportError:
    print("MetaTrader5 package not found — run this on the Windows VPS "
          "with the terminal installed (pip install MetaTrader5).")
    sys.exit(1)


def main() -> None:
    symbols = sys.argv[1:] or ["US30", "NAS100"]
    if not mt5.initialize():
        print("initialize() failed:", mt5.last_error())
        sys.exit(1)

    acct = mt5.account_info()
    if acct:
        print(f"✅ Connected: #{acct.login} {acct.server}")
        print(f"   balance={acct.balance} equity={acct.equity} "
              f"leverage=1:{acct.leverage} currency={acct.currency}\n")

    for sym in symbols:
        info = mt5.symbol_info(sym)
        if info is None:
            print(f"❌ {sym}: not found — check the exact symbol name in "
                  f"Market Watch (US30 / DJI30 / [DJI30] / US30.cash ...)")
            continue
        if not info.visible:
            mt5.symbol_select(sym, True)
            info = mt5.symbol_info(sym)
        # Value of a 1.0-lot move of ONE FULL PRICE UNIT (e.g. one index point,
        # like 52196 -> 52197) in account currency. Our strategy expresses SL/TP
        # distances in raw price units, not in the broker's minimal tick, so we
        # must NOT multiply by info.point (the tick size) here — that undercounts
        # by 100x on brokers quoting with 2 decimals (point=0.01, digits=2).
        pip_value_per_lot = None
        if info.trade_tick_size:
            pip_value_per_lot = info.trade_tick_value / info.trade_tick_size
        print(f"── {sym} ──")
        print(f"   point={info.point} digits={info.digits} "
              f"contract_size={info.trade_contract_size}")
        print(f"   tick_size={info.trade_tick_size} tick_value={info.trade_tick_value}")
        print(f"   volume_min={info.volume_min} step={info.volume_step} "
              f"max={info.volume_max}")
        if pip_value_per_lot:
            print(f"   => pip_value_per_lot (1 full price unit @ 1.0 lot) ≈ "
                  f"{pip_value_per_lot:.4f} {acct.currency if acct else ''}")
            print(f"   => put in settings.yaml: pip_size: 1.0, "
                  f"pip_value_per_lot: {pip_value_per_lot:.4f}")
            # quick sizing sanity for 1% on this account
            if acct:
                risk = acct.equity * 0.01
                for stop in (40, 60, 100):
                    lots = risk / (stop * pip_value_per_lot)
                    print(f"      1% risk, {stop}pt stop -> {lots:.2f} lots "
                          f"(min {info.volume_min})")
        print()

    mt5.shutdown()


if __name__ == "__main__":
    main()
