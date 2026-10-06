#!/usr/bin/env python3
"""Diagnostyka rozjazdu liczby rekordow — czy nasze pliki sa OBCIETE.

PYTANIE, NA KTORE TO ODPOWIADA. Metadane Databento podaja dzis dla naszych
sesji o ~2,6% wiecej rekordow, niz maja pobrane pliki. Sa dwie mozliwosci
i roznia sie one WSZYSTKIM:

  A. pliki sa NIEPELNE — brakuje w nich realnych zdarzen rynkowych.
     Wtedy trzeba je pobrac ponownie i zaplacic drugi raz.

  B'. pliki sa PELNE WEDLUG STAREJ WERSJI SERWOWANIA — te same zdarzenia,
     inna reprezentacja. Wtedy nie kupujemy nic, ale i tak NIE WOLNO mieszac
     ich z sesjami pobranymi po skoku.

Tych dwoch wariantow ten skrypt NIE rozroznia — na to potrzeba porownania
TRESCI. Skrypt odpowiada na pytanie wczesniejsze i tansze: czy niedobor jest
uciętym ogonem, czy siedzi w srodku sesji.

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

Oba testy sa LOKALNE i DARMOWE. Skrypt nie laczy sie z siecia i nic nie kupuje.

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
OKNO_SERWER_08_08 = 1_389_818
#: Liczby rekordow CALEJ sesji 2026-07-03: nasz plik / serwer 08.08.
#: Potrzebne, zeby porownac tempo niedoboru w oknie z tempem w calej sesji.
NASZ_SESJA = 2_660_629
SERW_SESJA = 2_708_424


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
        deficyt_okno = (OKNO_SERWER_08_08 - okno_nasz) / OKNO_SERWER_08_08
        deficyt_sesja = (SERW_SESJA - NASZ_SESJA) / SERW_SESJA
        print(f"  serwer 08.08, to samo okno   : {OKNO_SERWER_08_08:>10,}")
        print(f"  nasz plik {OKNO_SESJA}         : {okno_nasz:>10,}")
        print(f"  NIEDOBOR w oknie             : {OKNO_SERWER_08_08 - okno_nasz:>10,}"
              f"  ({100 * deficyt_okno:.4f}%)")
        print(f"  NIEDOBOR w calej sesji       : {SERW_SESJA - NASZ_SESJA:>10,}"
              f"  ({100 * deficyt_sesja:.4f}%)")
        print(f"  stosunek stop okno/sesja     : {deficyt_okno / deficyt_sesja:>10.3f}")
        print()
        # BEZ PROGU. Pierwsza wersja miala tolerancje dobrana z gory i uznala
        # realny wynik za "nieoczekiwany". Dostrajanie progu PO zobaczeniu
        # danych jest dokladnie tym nawykiem, ktorego zakazuje regula R2,
        # wiec zamiast tego raportujemy dwie liczby i ich stosunek.
        if okno_nasz >= OKNO_SERWER_08_08:
            print("  -> Plik ma w tym oknie tyle samo lub wiecej niz serwer.")
            print("     Niedobor calosci NIE siedzi w tym oknie.")
        else:
            print("  -> BRAK JEST WEWNATRZ OKNA, nie na koncu sesji.")
            print("     Ocena PELNY z testu 1 zostaje OBALONA empirycznie:")
            print("     pokrycie czasowe jest pelne, a rekordow brakuje.")
            print(f"     Stosunek stop {deficyt_okno / deficyt_sesja:.3f} —"
                  " przy braku idealnie jednorodnym")
            print("     wynosilby 1,000; odchylenie mowi, ze niedobor rozklada")
            print("     sie NIERWNOMIERNIE w czasie sesji.")
        print()
        print("  Czego to NIE rozstrzyga: czy brakujace rekordy to zdarzenia")
        print("  rynkowe nieobecne u nas (wariant A), czy inna reprezentacja")
        print("  tych samych zdarzen (wariant B'). Na to odpowiada wylacznie")
        print("  porownanie TRESCI — patrz D5_DRYF_METADANYCH §5.")

    print("\n" + "=" * 78)
    print("JAK CZYTAC CALOSC")
    print("  test 1 OBCIETY        -> pobranie urwane; sesja do ponowienia,")
    print("                           wpis do data/KOSZTY.md (wariant A),")
    print("  test 1 PELNY          -> brak UCIETEGO OGONA. To NIE jest dowod")
    print("                           kompletnosci — patrz test 2,")
    print("  test 2 brak w oknie   -> A ALBO B'. Ten skrypt ich NIE rozroznia;")
    print("                           rozstrzyga mikro-diff (D5_DRYF §5a) albo")
    print("                           odpowiedz dostawcy. Zakaz mieszania plikow")
    print("                           z obu okresow obowiazuje NIEZALEZNIE.")
    print("\nWynik wklej do docs/D5_DRYF_METADANYCH.md §3 przed wyslaniem maila.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
