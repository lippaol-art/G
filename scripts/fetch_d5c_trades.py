#!/usr/bin/env python3
"""Zakup pelnej doby `trades` dla sesji 2026-07-30 — kontrola Q7 audytu D5-C.

Specyfikacja zamrozona: docs/D5_ETAP1_SPEC.md (ten sam zakup co Etap 1 D5,
odtwarzany tutaj dla maszyny, ktora nie ma jeszcze pliku surowego — dane
surowe sa w .gitignore i nigdy nie trafiaja do repozytorium).

Okno: PELNA DOBA HANDLOWA `2026-07-29T22:00` -> `2026-07-30T21:00` UTC,
NIE tylko RTH — rekonstrukcja bara M1 w audycie D5-C potrzebuje calej sesji.

Oczekiwane po pobraniu (z golden/ZMIANY.md v6):
    rekordow : 1 696 891
    koszt    : 2,1240 USD (limit 2,15)
    SHA-256  : dfee7684c7bdce99272d91567752d7220291896bd8ebf694c281b6efab4df172

Uruchomienie:
    python3 scripts/fetch_d5c_trades.py --wycena   # sama wycena
    python3 scripts/fetch_d5c_trades.py            # wycena + zakup
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import databento as db

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.databento_io import metadane_z_ponowieniem  # noqa: E402
from engine.paths import raw_dir, wolne_gb  # noqa: E402

ZAPYTANIE = dict(dataset="GLBX.MDP3", symbols=["MNQU6"],
                 stype_in="raw_symbol", schema="trades")
START_UTC = "2026-07-29T22:00"
END_UTC = "2026-07-30T21:00"

#: Zamrozony w docs/D5_ETAP1_SPEC.md przed pierwszym zakupem tej sesji.
LIMIT_USD = 2.15
REZERWA_GB = 8.0
SHA256_OCZEKIWANY = ("dfee7684c7bdce99272d91567752d7220291896"
                     "bd8ebf694c281b6efab4df172")


def main() -> int:
    p = argparse.ArgumentParser(description="Zakup trades 2026-07-30 dla D5-C")
    p.add_argument("--wycena", action="store_true", help="tylko wycena")
    args = p.parse_args()

    c = db.Historical(os.environ["DATABENTO_API_KEY"])
    q = dict(**ZAPYTANIE, start=START_UTC, end=END_UTC)

    koszt = metadane_z_ponowieniem(c.metadata.get_cost, opis="get_cost", **q)
    rekordow = metadane_z_ponowieniem(c.metadata.get_record_count,
                                      opis="get_record_count", **q)
    print(f"okno UTC : {START_UTC} .. {END_UTC}")
    print(f"koszt    : {koszt:.4f} USD  (limit {LIMIT_USD:.2f})")
    print(f"rekordow : {rekordow:,}  (oczekiwane 1 696 891)", flush=True)

    if koszt > LIMIT_USD:
        sys.exit(f"STOP: {koszt:.4f} > {LIMIT_USD:.2f} USD — zakup NIEWYKONANY.")

    out = raw_dir("mnq_trades_2026-07-30.dbn.zst")
    wolne_przed = wolne_gb(out.parent)
    print(f"wolne    : {wolne_przed:.1f} GB w {out.parent}", flush=True)
    if wolne_przed < REZERWA_GB:
        sys.exit(f"STOP: wolne miejsce < {REZERWA_GB} GB.")

    if args.wycena:
        print("\nTryb wyceny — nic nie pobrano.")
        return 0

    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        sys.exit(f"STOP: {out} juz istnieje — usun swiadomie, jesli chcesz "
                 "pobrac ponownie.")

    print("\npobieranie...", flush=True)
    c.timeseries.get_range(**q, path=str(out))

    raw = out.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    del raw

    manifest = dict(
        etap="D5-C (kontrola Q7)", sesja="2026-07-30", zapytanie=ZAPYTANIE,
        start_utc=START_UTC, end_utc=END_UTC, limit_usd=LIMIT_USD,
        koszt_usd=round(koszt, 4), rekordow=rekordow, plik=out.name,
        sciezka=str(out), sha256=sha, databento=db.__version__,
    )
    Path("data/manifest_d5c_trades.json").write_text(
        json.dumps(manifest, indent=1), encoding="utf-8", newline="\n")

    print(f"\n-> {out}  ({out.stat().st_size / 1e6:.1f} MB)")
    print(f"   SHA-256   : {sha}")
    print(f"   oczekiwany: {SHA256_OCZEKIWANY}")
    print(f"   {'ZGODNY' if sha == SHA256_OCZEKIWANY else 'NIEZGODNY — SPRAWDZ'}")
    print(f"   koszt     : {manifest['koszt_usd']} USD")
    print("-> data/manifest_d5c_trades.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
