#!/usr/bin/env python3
"""Pobranie probki D5-B: 21 sesji RTH lipca 2026, MNQU6, schemat `trades`.

WZNAWIALNY. Plik uznaje sie za kompletny, gdy daje sie sparsowac i liczba
rekordow zgadza sie z `metadata.get_record_count`. Niekompletne sa pobierane
ponownie — inaczej przerwanie transferu zostawiloby po cichu obcieta sesje.

Zakres wg zamrozonej specyfikacji `docs/D5_ETAP2_SPEC.md` (commit 00fdcad):
RTH = 09:30-16:00 `America/New_York`, UTC WYPROWADZANE ze strefy ET.
Sesja 2026-07-30 NIE jest pobierana — posiadamy ja z Etapu 1.
Sesja 2026-07-31 NIE jest pobierana — brak odniesienia OHLCV do kontroli.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import databento as db

ET = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")
KAT = Path("data/raw/d5b_rth")
META = Path("data/manifest_d5b.json")

ZAPYTANIE = dict(
    dataset="GLBX.MDP3", symbols=["MNQU6"], stype_in="raw_symbol", schema="trades"
)
SESJE = [f"2026-07-{d:02d}" for d in
         (1, 2, 3, 6, 7, 8, 9, 10, 13, 14, 15, 16, 17, 20, 21, 22, 23, 24, 27, 28, 29)]
LIMIT_USD = 30.00


def okno(sesja: str) -> tuple[str, str]:
    """RTH wyprowadzone ZE STREFY ET — nigdy ze stalej UTC."""
    y, m, d = map(int, sesja.split("-"))
    a = dt.datetime(y, m, d, 9, 30, tzinfo=ET).astimezone(UTC)
    b = dt.datetime(y, m, d, 16, 0, tzinfo=ET).astimezone(UTC)
    return a.strftime("%Y-%m-%dT%H:%M"), b.strftime("%Y-%m-%dT%H:%M")


def kompletny(p: Path, oczekiwane: int) -> bool:
    if not p.exists() or p.stat().st_size == 0:
        return False
    try:
        return sum(1 for _ in db.DBNStore.from_file(p)) == oczekiwane
    except Exception:
        return False


def main() -> int:
    c = db.Historical(os.environ["DATABENTO_API_KEY"])
    KAT.mkdir(parents=True, exist_ok=True)

    plan = []
    suma = 0.0
    for s in SESJE:
        a, b = okno(s)
        k = c.metadata.get_cost(**ZAPYTANIE, start=a, end=b)
        n = c.metadata.get_record_count(**ZAPYTANIE, start=a, end=b)
        plan.append((s, a, b, k, n))
        suma += k

    print(f"wycena 21 sesji RTH: {suma:.4f} USD  (limit {LIMIT_USD})", flush=True)
    if suma > LIMIT_USD:
        sys.exit(f"STOP: {suma:.4f} > {LIMIT_USD} — zakup NIEWYKONANY")

    wpisy, pobrane, pominiete = [], 0, 0
    for s, a, b, k, n in plan:
        out = KAT / f"mnq_trades_rth_{s}.dbn.zst"
        if kompletny(out, n):
            pominiete += 1
            print(f"  {s}  POMINIETA (kompletna, {n:,} rek.)", flush=True)
        else:
            # `get_range` odmawia nadpisania, wiec niekompletny plik trzeba
            # najpierw usunac. Bez tego wznowienie wywraca sie na pierwszym
            # obcietym transferze.
            out.unlink(missing_ok=True)
            c.timeseries.get_range(**ZAPYTANIE, start=a, end=b, path=str(out))
            pobrane += 1
            print(f"  {s}  pobrano {out.stat().st_size / 1e6:6.1f} MB, {n:,} rek.",
                  flush=True)
        raw = out.read_bytes()
        wpisy.append(dict(sesja=s, start_utc=a, end_utc=b, plik=out.name,
                          rekordow=n, bajtow=len(raw), koszt_usd=round(k, 4),
                          sha256=hashlib.sha256(raw).hexdigest()))

    info = dict(
        zapytanie=ZAPYTANIE,
        rth="09:30-16:00 America/New_York (UTC wyprowadzone ze strefy)",
        sesji=len(wpisy), pobranych_teraz=pobrane, pominietych=pominiete,
        koszt_wyceny_usd=round(suma, 4),
        rekordow=sum(w["rekordow"] for w in wpisy),
        bajtow=sum(w["bajtow"] for w in wpisy),
        pobrano_utc=dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
        databento=db.__version__, pliki=wpisy,
    )
    META.write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(f"\nRAZEM {info['sesji']} sesji  {info['rekordow']:,} rek.  "
          f"{info['bajtow'] / 1e6:.1f} MB  wycena {info['koszt_wyceny_usd']} USD")
    print(f"pobrano teraz: {pobrane}, pominieto jako kompletne: {pominiete}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
