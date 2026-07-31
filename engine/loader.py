"""Wczytywanie oczyszczonych danych — PLAN.pdf rozdz. 4.2.

=========================================================================
GRANICA PROJEKTU: ten modul jest jedynym, ktorego NIE DA SIE uruchomic bez
realnych danych rynkowych w data/clean/. Kod jest gotowy; testy funkcjonalne
sa oznaczone `@pytest.mark.needs_data` i pomijane do czasu pobrania danych.

Stan na 31.07.2026: host hist.databento.com odrzucany przez polityke egress
srodowiska (403 na CONNECT). Procedura odblokowania: patrz HANDOFF.md.
=========================================================================

Zasada niezmienniczosci: pliki w data/clean/ sa ARTEFAKTAMI WERSJONOWANYMI.
Zaden backtest nie czyta z data/raw/; jedynym wejsciem badan jest data/clean/.
Dzieki temu kazdy wynik w projekcie jest odtwarzalny co do bajta.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DATA_CLEAN = Path("data/clean")

# Schemat obowiazkowy pliku parquet (rozdz. 4.2 krok 6-8)
REQUIRED_COLUMNS = (
    "ts_utc",          # znacznik czasu w UTC — zawsze UTC w pliku
    "open", "high", "low", "close", "volume",
    "contract",        # ktora noga kontraktowa
    "px_raw",          # cena surowa      -> poziomy miedzysesyjne (rozdz. 4.3)
    "px_adj",          # cena skorygowana -> P&L i statystyki zwrotow
    "trade_date",      # dzien sesyjny (od 18:00 ET dnia poprzedniego)
    "segment",         # segment doby
    "gap_kind",        # "none" | "expected" | "anomaly"  (rozdz. 4.2 krok 3)
    "data_condition",  # "available" | "degraded" | "missing" — wg dostawcy
)

OPTIONAL_COLUMNS = (
    "dst_transition", "short_day", "days_to_roll", "halt_window",
)


class DataNotAvailableError(FileNotFoundError):
    """Dane nie zostaly jeszcze pobrane — patrz HANDOFF.md."""


class SchemaError(ValueError):
    """Plik istnieje, ale nie spelnia kontraktu schematu."""


@dataclass(frozen=True)
class DatasetInfo:
    path: Path
    n_rows: int
    columns: tuple[str, ...]
    first_ts: object
    last_ts: object


def clean_path(symbol: str, timeframe: str = "1m") -> Path:
    return DATA_CLEAN / f"{symbol.lower()}_{timeframe}_cont.parquet"


def is_available(symbol: str, timeframe: str = "1m") -> bool:
    """Czy oczyszczone dane sa dostepne. Uzywane przez testy `needs_data`."""
    return clean_path(symbol, timeframe).exists()


def validate_schema(columns: list[str] | tuple[str, ...]) -> None:
    """Sprawdza kontrakt schematu przed jakimkolwiek uzyciem danych.

    Brak `px_raw`/`px_adj` jest bledem krytycznym: bez rozdzielenia serii
    poziomy referencyjne policzylyby sie na cenach skorygowanych, a to jest
    dokladnie ten cichy blad, ktory generuje sygnaly na nieistniejacych
    poziomach (rozdz. 4.3).
    """
    brakuje = [c for c in REQUIRED_COLUMNS if c not in columns]
    if brakuje:
        raise SchemaError(
            f"Brak wymaganych kolumn: {brakuje}. "
            "Dane musza pochodzic z pipeline'u scripts/build_dataset.py "
            "(PLAN.pdf rozdz. 4.2) — nie wczytuj surowych plikow dostawcy."
        )


def load_continuous(symbol: str, timeframe: str = "1m"):
    """Wczytuje kontrakt ciagly z data/clean/.

    Zwraca polars.DataFrame. Rzuca `DataNotAvailableError` z instrukcja, gdy
    danych jeszcze nie ma — komunikat ma prowadzic do rozwiazania, nie tylko
    informowac o braku.
    """
    path = clean_path(symbol, timeframe)
    if not path.exists():
        raise DataNotAvailableError(
            f"Brak pliku {path}.\n"
            "Dane nie zostaly jeszcze pobrane (Etap 1 projektu).\n"
            "Procedura: HANDOFF.md, sekcja 'Etap 1 krok po kroku'.\n"
            "  1. export DATABENTO_API_KEY='db-...'\n"
            "  2. python3 scripts/build_dataset.py --estimate-only\n"
            "  3. python3 scripts/build_dataset.py"
        )

    import polars as pl

    df = pl.read_parquet(path)
    validate_schema(df.columns)
    return df


def describe(symbol: str, timeframe: str = "1m") -> DatasetInfo:
    """Podstawowe informacje o zbiorze — do sanity-reportu (rozdz. 4.6)."""
    df = load_continuous(symbol, timeframe)
    return DatasetInfo(
        path=clean_path(symbol, timeframe),
        n_rows=df.height,
        columns=tuple(df.columns),
        first_ts=df["ts_utc"].min(),
        last_ts=df["ts_utc"].max(),
    )
