#!/usr/bin/env python3
"""Warstwa danych K6 — PLAN.pdf rozdz. 4.7 (dane uzupelniajace).

Sklada sie z trzech czesci, wszystkie ze zbioru XNAS.ITCH, schemat ohlcv-1m:

  * 8 megacapow NDX  — sygnal H013 (transmisja wynikow do wartosci godziwej),
  * QQQ              — proxy indeksu kasowego, kontrola bazisu futures-cash,
  * SOXX             — kontrola sektorowa (beta polprzewodnikowa).

POBIERANIE ODCINKAMI ROCZNYMI. Jednorazowe zadanie o calosc juz raz padlo na
limicie czasu przy MNQ, produkujac zero plikow i mozliwe obciazenie konta.
Odcinki roczne sa wznawialne: plik, ktory istnieje, jest pomijany, wiec
przerwanie w polowie kosztuje jeden odcinek, a nie caly zakres.

KLUCZ WYLACZNIE ZE ZMIENNEJ SRODOWISKOWEJ. Zadnej wartosci domyslnej —
domyslna wartosc klucza to zaproszenie do wyciekniecia.

Uruchomienie:
    python3 scripts/build_k6.py --estimate-only     # wycena, nie obciaza konta
    python3 scripts/build_k6.py                     # pobranie
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

RAW = Path("data/raw")
DATASET = "XNAS.ITCH"
SCHEMA = "ohlcv-1m"
START, END = "2019-05-06", "2026-07-30"

# Wagi w NDX ~50% lacznie. Lista jest STALA dla calego zakresu historii, bo
# sklad pierwszej osemki zmienial sie w tym okresie minimalnie; ewentualne
# roznice wychodza w wagach kwartalnych, nie w doborze spolek.
MEGACAPY = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AVGO", "TSLA"]
POPRZEDNIE_TICKERY = {"META": ("FB", "2022-06-09")}   # ticker -> (poprzednik, data zmiany)

# ZMIANA TICKERA W TRAKCIE HISTORII. Meta Platforms handlowala sie jako **FB**
# do 2022-06-09 i dopiero potem jako META. Zadanie o "META" za rok 2019 zwraca
# ostrzezenie "did not resolve" i PUSTY WYNIK — czyli po cichu gubi jeden
# z osmiu megacapow w trzech z siedmiu lat.
#
# Dla H013 byloby to zabojcze: suma wazona Sigma w_i * r_i jest arytmetycznym
# sercem karty, a brak spolki o wadze ~4% zaniza ja systematycznie, nie losowo.
# Blad nie objawilby sie wyjatkiem, tylko przesunietym sygnalem.
#
# FB pobieramy jako osobna grupe; pipeline sklei FB + META w jeden szereg.
GRUPY: dict[str, list[str]] = {
    "mega": MEGACAPY,
    "fb": ["FB"],          # 2019 -> 2022-06, poprzednik META
    "qqq": ["QQQ"],
    "soxx": ["SOXX"],
}


def klient():
    import databento as db

    klucz = os.environ.get("DATABENTO_API_KEY", "")
    if not klucz:
        sys.exit(
            "BLAD: brak zmiennej DATABENTO_API_KEY.\n"
            "  export DATABENTO_API_KEY='db-...'\n"
            "Klucz NIGDY nie trafia do pliku w repozytorium."
        )
    return db.Historical(klucz)


def odcinki() -> list[tuple[str, str]]:
    """Zakres podzielony na lata kalendarzowe."""
    out = []
    for rok in range(2019, 2027):
        a = max(f"{rok}-01-01", START)
        b = min(f"{rok}-12-31", END)
        if a < b:
            out.append((a, b))
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Pobranie warstwy danych K6")
    p.add_argument("--estimate-only", action="store_true",
                   help="tylko wycena — zapytanie read-only, nie obciaza konta")
    args = p.parse_args()

    c = klient()
    RAW.mkdir(parents=True, exist_ok=True)

    if args.estimate_only:
        suma = 0.0
        for nazwa, symbole in GRUPY.items():
            k = c.metadata.get_cost(dataset=DATASET, schema=SCHEMA, symbols=symbole,
                                    stype_in="raw_symbol", start=START, end=END)
            n = c.metadata.get_record_count(dataset=DATASET, schema=SCHEMA, symbols=symbole,
                                            stype_in="raw_symbol", start=START, end=END)
            suma += k
            print(f"  {nazwa:<6} ${k:>6.2f}  {n:>12,} rekordow  ({len(symbole)} symboli)")
        print(f"  {'RAZEM':<6} ${suma:>6.2f}")
        return 0

    for nazwa, symbole in GRUPY.items():
        for a, b in odcinki():
            cel = RAW / f"k6_{nazwa}_{SCHEMA}_{a[:4]}.dbn.zst"
            if cel.exists():
                print(f"  {cel.name}: juz jest, pomijam")
                continue
            print(f"  {cel.name}: pobieram {a} -> {b} ...", flush=True)
            dane = c.timeseries.get_range(
                dataset=DATASET, schema=SCHEMA, symbols=symbole,
                stype_in="raw_symbol", start=a, end=b,
            )
            dane.to_file(cel)
            print(f"    -> {cel.stat().st_size / 1e6:.1f} MB", flush=True)

    print("\nGotowe. Nastepny krok: pipeline wag NDX i pre-flight H013.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
