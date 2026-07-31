#!/usr/bin/env python3
"""Generator raportu jakosci danych — PLAN.pdf rozdz. 4.6.

Uruchamiany po KAZDEJ regeneracji data/clean/:

    python3 scripts/sanity_report.py --symbol mnq

Wynik trafia do reports/data_quality.md. Kod wyjscia 1 oznacza, ze raport ma
pozycje do przegladu — nadaje sie wprost do CI, kiedy dane juz beda w repo.

Raport nie stempluje danych jako dobrych. Wypisuje, czego w nich nie rozumiemy.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import date
from pathlib import Path

from engine.calendar_cme import PROJECT_CALENDAR
from engine.loader import DataNotAvailableError, clean_path, load_continuous
from engine.sanity import build_report

EVENTS = Path("data/clean/events.csv")
DEFAULT_OUT = Path("reports/data_quality.md")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blok in iter(lambda: f.read(1 << 20), b""):
            h.update(blok)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser(description="Raport jakosci danych")
    p.add_argument("--symbol", default="mnq")
    p.add_argument("--timeframe", default="1m")
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument("--schema-version", default="", help="wersja schematu dostawcy z manifestu")
    p.add_argument("--downloaded", default="", help="data pobrania (YYYY-MM-DD)")
    args = p.parse_args()

    try:
        df = load_continuous(args.symbol, args.timeframe)
    except DataNotAvailableError as e:
        print(e, file=sys.stderr)
        return 2

    import polars as pl

    events = pl.read_csv(EVENTS, try_parse_dates=True) if EVENTS.exists() else None

    sciezka = clean_path(args.symbol, args.timeframe)
    raport = build_report(
        df, PROJECT_CALENDAR, events=events,
        meta={
            "plik": str(sciezka),
            "sha256": sha256(sciezka),
            "schema_version": args.schema_version,
            "downloaded": args.downloaded or date.today().isoformat(),
        },
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(raport.render(), encoding="utf-8")
    print(f"Raport zapisany: {args.out}")

    if raport.ok:
        print("Brak pozycji do przegladu.")
        return 0
    print(f"\nPozycji do przegladu: {len(raport.do_przegladu)}")
    for pozycja in raport.do_przegladu[:20]:
        print(f"  - {pozycja}")
    if len(raport.do_przegladu) > 20:
        print(f"  ... oraz {len(raport.do_przegladu) - 20} dalszych")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
