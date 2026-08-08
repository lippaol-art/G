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

DWA TESTY, BO JEDEN NIE WYSTARCZA.

  1. ZAKRES (pierwszy i ostatni znacznik). Wykrywa UCIETY OGON. To jest test
     konieczny, ale NIEWYSTARCZAJACY: plik, ktoremu brakuje 2,6% rekordow
     rozsianych rownomiernie, zaczyna sie o 13:30, konczy o 19:59:59 i dostanie
     ocene PELNY. "PELNY" wyklucza obciecie, NIE wyklucza przerzedzenia.
     Zarzut wniesiony przez recenzje P1 — przyjety.

  2. GESTOSC W OKNIE. Liczy rekordy naszego pliku w waskim oknie, dla ktorego
     mamy dzisiejszy pomiar serwera. Jesli plik ma tam mniej, roznica jest
     ROZSIANA w srodku sesji, a nie na koncu — i wtedy "PELNY" nie dowodzi
     niczego o kompletnosci.

Oba testy sa LOKALNE i DARMOWE. Skrypt nie laczy sie z siecia.

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

#: Okno kontrolne o ZMIERZONEJ wartosci serwerowej. 08.08.2026 zapytanie
#: o 2026-07-03 13:30-14:30 zwrocilo 1 389 818 rekordow — zweryfikowane
#: dwoma sposobami (jednym wywolaniem i dwoma po 30 min, roznica 0).
OKNO_SESJA = "2026-07-03"
OKNO_OD_H, OKNO_DO_H = 13.5, 14.5
OKNO_SERWER_08_08 = 1_389_818
#: Udzial starej wyceny w nowej dla tej sesji: 2 660 629 / 2 708 424.
UDZIAL_STARY = 2_660_629 / 2_708_424


def skanuj(p: Path) -> dict:
    """Pierwszy i ostatni znacznik czasu oraz liczba rekordow — jednym przejsciem.

    Czytamy strumieniowo, bo plik sesji ma setki MB i wczytanie go w calosci
    do pamieci nie jest potrzebne do odpowiedzi na to pytanie.
    """
    n = 0
    pierwszy = ostatni = None
    w_oknie = 0
    y, m, d = map(int, p.stem.replace("mnq_mbo_rth_", "").replace(".dbn", "")
                  .split("-"))
    od = dt.datetime(y, m, d, 13, 30, tzinfo=UTC).timestamp() * 1e9
    do = dt.datetime(y, m, d, 14, 30, tzinfo=UTC).timestamp() * 1e9
    for r in db.DBNStore.from_file(p):
        ts = getattr(r, "ts_recv", None) or getattr(r, "ts_event", None)
        if ts is not None:
            if pierwszy is None:
                pierwszy = ts
            ostatni = ts
            if od <= ts < do:
                w_oknie += 1
        n += 1
    return {"rekordow": n, "pierwszy": pierwszy, "ostatni": ostatni,
            "w_oknie": w_oknie}


def main() -> int:
    pliki = sorted(p for kat in KATALOGI if raw_dir(kat).exists()
                   for p in raw_dir(kat).glob("mnq_mbo_rth_*.dbn.zst"))
    if not pliki:
        sys.exit("Nie znalazlem zadnego pliku MBO. Sprawdz PROJECT_G_DATA_ROOT.")

    okno_nasz = None
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
        if sesja == OKNO_SESJA:
            okno_nasz = w["w_oknie"]
        print(f"{sesja:12} {w['rekordow']:>13,} {a.strftime('%H:%M:%S'):>14} "
              f"{b.strftime('%H:%M:%S'):>13} {brak_s:>9.0f}s  {ocena}")

    print("\n" + "=" * 78)
    print("TEST 2 — GESTOSC W OKNIE 13:30-14:30")
    if okno_nasz is None:
        print(f"  brak pliku {OKNO_SESJA} — testu nie wykonano")
    else:
        oczek_stary = round(OKNO_SERWER_08_08 * UDZIAL_STARY)
        print(f"  serwer 08.08, to samo okno   : {OKNO_SERWER_08_08:>10,}")
        print(f"  nasz plik {OKNO_SESJA}         : {okno_nasz:>10,}")
        print(f"  gdyby brak byl ROZSIANY      : {oczek_stary:>10,} (oczekiwane)")
        roznica = okno_nasz - OKNO_SERWER_08_08
        print(f"  roznica wobec serwera        : {roznica:>+10,} "
              f"({100 * roznica / OKNO_SERWER_08_08:+.2f}%)")
        if abs(okno_nasz - OKNO_SERWER_08_08) <= 2:
            print("\n  -> WNIOSEK: w tym oknie plik zgadza sie z DZISIEJSZYM")
            print("     liczeniem. Roznica calosci nie siedzi tutaj — pytanie")
            print("     przenosi sie na definicje calego zakresu.")
        elif abs(okno_nasz - oczek_stary) <= max(50, oczek_stary // 1000):
            print("\n  -> WNIOSEK: brak jest ROZSIANY po sesji, nie na koncu.")
            print("     Ocena PELNY z testu 1 NIE dowodzi kompletnosci pliku.")
            print("     Natura nadwyzki staje sie pytaniem glownym.")
        else:
            print("\n  -> WNIOSEK: ani stary udzial, ani dzisiejsza wartosc.")
            print("     Wynik nieoczekiwany — opisz go w §3, nie interpretuj.")

    print("\n" + "=" * 78)
    print("JAK CZYTAC CALOSC")
    print("  test 1 OBCIETY        -> pobranie urwane; sesja do ponowienia,")
    print("                           wpis do data/KOSZTY.md (wariant A),")
    print("  test 1 PELNY          -> brak UCIETEGO OGONA. To NIE jest dowod")
    print("                           kompletnosci — patrz test 2,")
    print("  test 2 rozsiany brak  -> wariant B': pliki pelne wg STAREJ wersji")
    print("                           serwowania, ale nowe pobrania roznia sie")
    print("                           trescia. Zakaz mieszania obowiazuje")
    print("                           NIEZALEZNIE od wyniku.")
    print("\nWynik wklej do docs/D5_DRYF_METADANYCH.md §3 przed wyslaniem maila.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
