#!/usr/bin/env python3
"""Diagnostyka rozjazdu liczby rekordow — czy nasze pliki sa OBCIETE.

PYTANIE, NA KTORE TO ODPOWIADA. Metadane Databento podaja dzis dla naszych
sesji o ~2,6% wiecej rekordow, niz maja pobrane pliki. Sa dwie mozliwosci
i roznia sie one WSZYSTKIM:

  A. pliki sa NIEPELNE — pobrane w czasie awarii serwisu, ktora zaniżała
     tez metadane, wiec `kompletny()` porownal je z ta sama zla liczba
     i przepuscil. Wtedy trzeba je pobrac ponownie i zaplacic drugi raz.

  B. pliki sa PELNE — pokrywaja cale okno RTH bez luk, a rozjazd dotyczy
     wylacznie metadanych. Wtedy nie kupujemy nic, tylko pytamy dostawce.

Rozstrzyga sie to LOKALNIE i ZA DARMO: plik pelny musi zaczynac sie tuz po
13:30 UTC i konczyc tuz przed 20:00 UTC. Plik obciety konczy sie wczesniej.

Skrypt NIE laczy sie z siecia i NIE kupuje niczego.

Uruchomienie:
    python scripts/diag_dryf.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import databento as db

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.paths import raw_dir  # noqa: E402

KATALOGI = ("d5b2_mbo", "d5c_mbo")
UTC = dt.UTC


def skanuj(p: Path) -> dict:
    """Pierwszy i ostatni znacznik czasu oraz liczba rekordow — jednym przejsciem.

    Czytamy strumieniowo, bo plik sesji ma setki MB i wczytanie go w calosci
    do pamieci nie jest potrzebne do odpowiedzi na to pytanie.
    """
    n = 0
    pierwszy = ostatni = None
    for r in db.DBNStore.from_file(p):
        ts = getattr(r, "ts_recv", None) or getattr(r, "ts_event", None)
        if ts is not None:
            if pierwszy is None:
                pierwszy = ts
            ostatni = ts
        n += 1
    return {"rekordow": n, "pierwszy": pierwszy, "ostatni": ostatni}


def main() -> int:
    pliki = sorted(p for kat in KATALOGI if raw_dir(kat).exists()
                   for p in raw_dir(kat).glob("mnq_mbo_rth_*.dbn.zst"))
    if not pliki:
        sys.exit("Nie znalazlem zadnego pliku MBO. Sprawdz PROJECT_G_DATA_ROOT.")

    print(f"Znalezione pliki: {len(pliki)}\n")
    print(f"{'sesja':12} {'rekordow':>13} {'pierwszy UTC':>14} "
          f"{'ostatni UTC':>13} {'do 20:00':>10}  ocena")
    print("-" * 78)

    for p in pliki:
        sesja = p.stem.replace("mnq_mbo_rth_", "").replace(".dbn", "")
        try:
            w = skanuj(p)
        except Exception as e:                                  # noqa: BLE001
            print(f"{sesja:12} BLAD ODCZYTU: {type(e).__name__}: {e}")
            continue

        if w["pierwszy"] is None:
            print(f"{sesja:12} {w['rekordow']:>13,}  brak znacznikow czasu")
            continue

        a = dt.datetime.fromtimestamp(w["pierwszy"] / 1e9, UTC)
        b = dt.datetime.fromtimestamp(w["ostatni"] / 1e9, UTC)
        y, m, d = map(int, sesja.split("-"))
        koniec = dt.datetime(y, m, d, 20, 0, tzinfo=UTC)
        # 2026-07-03 zamyka sie o 13:00 ET = 17:00 UTC (swieto obserwowane).
        if sesja == "2026-07-03":
            koniec = dt.datetime(y, m, d, 17, 0, tzinfo=UTC)
        brak_s = (koniec - b).total_seconds()

        ocena = ("PELNY" if brak_s < 60 else
                 f"OBCIETY o {brak_s / 60:.0f} min")
        print(f"{sesja:12} {w['rekordow']:>13,} {a.strftime('%H:%M:%S'):>14} "
              f"{b.strftime('%H:%M:%S'):>13} {brak_s:>9.0f}s  {ocena}")

    print("\n" + "=" * 78)
    print("JAK CZYTAC WYNIK")
    print("  wszystkie PELNE  -> pliki pokrywaja cale okno; rozjazd dotyczy")
    print("                      metadanych, NIE kupujemy nic (wariant B),")
    print("  ktorykolwiek OBCIETY -> pobranie bylo niepelne mimo zgodnej")
    print("                      liczby rekordow; ta sesja wymaga ponownego")
    print("                      pobrania i wpisu do data/KOSZTY.md (wariant A).")
    print("\nWynik wklej do docs/D5_DRYF_METADANYCH.md §3 przed wyslaniem maila.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
