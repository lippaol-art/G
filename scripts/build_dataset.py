#!/usr/bin/env python3
"""Pobranie i oczyszczenie danych MNQ/NQ z Databento.

Specyfikacja: PLAN.pdf rozdz. 4.1-4.3, 4.6.

UWAGA — KLUCZ API:
    Skrypt czyta wylacznie zmienna srodowiskowa DATABENTO_API_KEY.
    NIGDY nie zapisuj klucza w tym pliku ani nigdzie indziej w repo.

        export DATABENTO_API_KEY="db-..."
        python3 scripts/build_dataset.py --estimate-only

STATUS: skrypt gotowy, ale niewykonany — host hist.databento.com jest
zablokowany przez polityke egress srodowiska (403 na CONNECT). Uruchomic po
odblokowaniu sieci.

Kolejnosc operacji (rozdz. 4.2):
    [1] dedup + sortowanie po ts_event
    [2] walidacja: monotonicznosc, OHLC-spojnosc, wolumen >= 0
    [3] KLASYFIKACJA LUK wg kalendarza CME: expected vs anomaly
    [4] mapowanie kontraktow + tabela dat rolowania (wolumenowa)
    [5] sklejenie kontraktu ciaglego + back-adjust roznicowy
    [6] konwersja stref: UTC w pliku, sesje indeksowane w ET
    [7] segmenty sesji i dzien sesyjny
    [8] flagi: dst_transition, short_day, days_to_roll, halt_window
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date

DATASET = "GLBX.MDP3"
SCHEMA = "ohlcv-1m"
SYMBOLS = ["MNQ", "NQ", "ES"]    # ES: test transferu (7.5) + baza klasy K6 (4.7)
START = date(2019, 4, 14)        # start produktu MNQ na CME
STYPE_IN = "parent"              # wszystkie nogi kontraktowe danego produktu


def parent_symbol(root: str) -> str:
    """Symbol w formacie wymaganym przez stype_in='parent'.

    Databento oczekuje '[ROOT].FUT' — samo 'MNQ' konczy sie bledem
    symbology_invalid_symbol. Sufiks dodajemy tu, zeby wywolania skryptu
    przyjmowaly naturalne nazwy ('MNQ', nie 'MNQ.FUT').
    """
    root = root.upper().strip()
    return root if root.endswith((".FUT", ".OPT", ".SPOT")) else f"{root}.FUT"


def get_api_key() -> str:
    """Klucz wylacznie ze srodowiska. Brak wartosci domyslnej — celowo."""
    key = os.environ.get("DATABENTO_API_KEY", "").strip()
    if not key:
        sys.exit(
            "BLAD: brak zmiennej srodowiskowej DATABENTO_API_KEY.\n"
            "  export DATABENTO_API_KEY='db-...'\n"
            "Klucza NIE zapisujemy w repo ani w plikach konfiguracyjnych."
        )
    if not key.startswith("db-"):
        sys.exit("BLAD: klucz Databento powinien zaczynac sie od 'db-'")
    return key


def estimate_cost(client, symbols: list[str], start: date, end: date) -> float:
    """Szacunek kosztu PRZED pobraniem (rozdz. 4.1 — obowiazkowy krok).

    Nowe konto ma 125 USD kredytow startowych; pelna historia MNQ+NQ M1
    to okolo 25-60 USD, wiec praktyczny koszt tej fazy wynosi zero.
    """
    total = 0.0
    for sym in symbols:
        cost = client.metadata.get_cost(
            dataset=DATASET,
            symbols=[parent_symbol(sym)],
            schema=SCHEMA,
            stype_in=STYPE_IN,
            start=start.isoformat(),
            end=end.isoformat(),
        )
        print(f"  {sym:5s} {SCHEMA}  {start} -> {end}:  {cost:.2f} USD")
        total += float(cost)
    return total


def _year_chunks(start: date, end: date) -> list[tuple[date, date]]:
    """Dzieli zakres na odcinki roczne.

    Pobieranie 7 lat barow minutowych jednym zapytaniem trwa dlugo i jest
    nieodporne: przerwanie oznacza utrate calosci. Odcinki roczne daja
    widocznosc postepu i WZNAWIALNOSC — istniejace pliki sa pomijane, wiec
    ponowne uruchomienie dociaga tylko brakujace lata.
    """
    out: list[tuple[date, date]] = []
    cur = start
    while cur < end:
        nast = min(date(cur.year + 1, 1, 1), end)
        out.append((cur, nast))
        cur = nast
    return out


def _download_symbol(client, sym: str, start: date, end: date, out_dir: str) -> None:
    """Pobiera symbol odcinkami rocznymi, pomijajac juz istniejace pliki."""
    for a, b in _year_chunks(start, end):
        path = os.path.join(out_dir, f"{sym.lower()}_{SCHEMA}_{a.year}.dbn.zst")
        if os.path.exists(path) and os.path.getsize(path) > 0:
            print(f"  {sym} {a.year}: juz pobrany, pomijam")
            continue
        print(f"  {sym} {a.year}: {a} -> {b} ...", flush=True)
        data = client.timeseries.get_range(
            dataset=DATASET,
            symbols=[parent_symbol(sym)],
            schema=SCHEMA,
            stype_in=STYPE_IN,
            start=a.isoformat(),
            end=b.isoformat(),
        )
        data.to_file(path)
        print(f"    -> {path} ({os.path.getsize(path) / 1e6:.1f} MB)", flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description="Pobranie danych MNQ/NQ z Databento")
    p.add_argument("--estimate-only", action="store_true",
                   help="tylko oszacuj koszt, nie pobieraj")
    p.add_argument("--symbols", nargs="+", default=SYMBOLS)
    p.add_argument("--start", type=date.fromisoformat, default=START)
    p.add_argument("--end", type=date.fromisoformat, default=date.today())
    p.add_argument("--out", default="data/raw")
    args = p.parse_args()

    key = get_api_key()

    try:
        import databento as db
    except ImportError:
        sys.exit(
            "BLAD: brak pakietu databento.\n"
            "  pip install 'projekt-g[data]'   albo   pip install databento"
        )

    client = db.Historical(key)

    print(f"Szacowanie kosztu ({DATASET} / {SCHEMA}):")
    total = estimate_cost(client, args.symbols, args.start, args.end)
    print(f"  RAZEM: {total:.2f} USD")

    if args.estimate_only:
        print("\n--estimate-only: konczę bez pobierania.")
        return 0

    if total > 100:
        resp = input(f"\nKoszt {total:.2f} USD przekracza 100 USD. Kontynuowac? [t/N] ")
        if resp.strip().lower() not in {"t", "tak", "y", "yes"}:
            print("Przerwano.")
            return 1

    os.makedirs(args.out, exist_ok=True)
    for sym in args.symbols:
        _download_symbol(client, sym, args.start, args.end, args.out)

    print(
        "\nGotowe. Nastepny krok: czyszczenie i budowa kontraktu ciaglego.\n"
        "Pamietaj o wpisie w data/manifest.md: zakres, wersja schematu, data\n"
        "pobrania i sumy kontrolne (rozdz. 4.1 — dostawca zmienil normalizacje\n"
        "GLBX.MDP3 w lipcu 2026, wiec wersja musi byc przypieta)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
