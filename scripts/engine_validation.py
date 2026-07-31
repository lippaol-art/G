#!/usr/bin/env python3
"""Walidacja silnika na realnych danych — PLAN.pdf rozdz. 5.6.

    python3 scripts/engine_validation.py --symbol mnq

BRAMKA PROJEKTU: dopoki ten skrypt nie jest zielony na danych z data/clean/,
nie wolno uruchomic zadnej eksploracji (HANDOFF.md, zasada 4). Silnik,
ktoremu nie udowodniono poprawnosci, produkuje smiecie z dokladnoscia do
szesciu miejsc po przecinku.

Kod wyjscia: 0 = komplet zdany, 1 = ktorys test nie przeszedl,
2 = brak danych (Etap 1 niewykonany).
"""

from __future__ import annotations

import argparse
import sys

from engine.backtest import Bar
from engine.loader import DataNotAvailableError, load_continuous
from validation.engine_checks import run_all


def bars_from_frame(df) -> list[Bar]:
    """Ramka z data/clean/ -> lista barow silnika.

    Bary niosa ceny SKORYGOWANE (P&L liczy sie na jednorodnej skali punktowej)
    plus offset, ktory pozwala odtworzyc cene surowa dla poziomow
    miedzysesyjnych — rozdzielenie serii z rozdz. 4.3.
    """
    return [
        Bar(ts=r["ts_utc"], open=r["open"], high=r["high"], low=r["low"],
            close=r["close"], volume=int(r["volume"]), segment=r["segment"],
            px_raw_offset=float(r["px_raw_offset"]))
        for r in df.iter_rows(named=True)
    ]


def main() -> int:
    p = argparse.ArgumentParser(description="Walidacja silnika (rozdz. 5.6)")
    p.add_argument("--symbol", default="mnq")
    p.add_argument("--timeframe", default="1m")
    p.add_argument("--seed", type=int, default=20260731)
    p.add_argument("--limit", type=int, default=0,
                   help="uzyj tylko pierwszych N barow (szybki przebieg kontrolny)")
    args = p.parse_args()

    try:
        df = load_continuous(args.symbol, args.timeframe)
    except DataNotAvailableError as e:
        print(e, file=sys.stderr)
        print(
            "\nTesty 3 (symetria) i 4 (determinizm) dzialaja na fixture'ach i chodza\n"
            "w CI; testy 1 (zerowa przewaga) i 2 (znany efekt) wymagaja realnych\n"
            "danych, bo tylko na nich cokolwiek znacza.",
            file=sys.stderr,
        )
        return 2

    if args.limit:
        df = df.head(args.limit)

    bars = bars_from_frame(df)
    print(f"Walidacja silnika na {len(bars)} barach ({args.symbol.upper()})\n")

    wyniki = run_all(bars, seed=args.seed)
    for w in wyniki:
        print(w)
        for k, v in w.liczby.items():
            print(f"        {k}: {v}")

    zdane = sum(1 for w in wyniki if w.zdany)
    print(f"\nZdanych: {zdane}/{len(wyniki)}")
    if zdane < len(wyniki):
        print(
            "\nBRAMKA ZAMKNIETA. Nie uruchamiaj eksploracji, dopoki komplet nie jest\n"
            "zielony — kazdy wynik policzony teraz bylby bez wartosci."
        )
        return 1
    print("\nBramka otwarta: silnik mozna uzywac do badan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
