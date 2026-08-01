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


def to_bars(df, *, price: str = "adj", limit: int | None = None) -> list:
    """DataFrame -> lista `engine.backtest.Bar`.

    KTORA SERIA. Kolumny `open/high/low/close` w pliku sa SUROWE — to ceny,
    ktore realnie widniały na tablicy danego kontraktu. Kolumna `px_adj` niesie
    close po back-adjuscie roznicowym. Roznica `px_adj - close` jest w obrebie
    jednego kontraktu STALA, wiec caly bar przesuwamy o nia (rozdz. 4.3).

    Domyslne `price="adj"` jest jedynym poprawnym wyborem do P&L i statystyk
    zwrotow: bez niego kazde rolowanie wstawialoby w serie sztuczny skok rzedu
    kilkudziesieciu punktow, na ktorym strategia "zarabialaby" bez pokrycia.
    `price="raw"` sluzy wylacznie poziomom miedzysesyjnym — i wtedy obowiazuje
    `engine.guards.assert_raw_series`.

    Kazdy bar niesie `px_raw_offset = px_raw - px_adj`, wiec z serii ciaglej
    da sie odtworzyc cene surowa bez ponownego siegania do pliku.
    """
    from engine.backtest import Bar

    if price not in {"adj", "raw"}:
        raise ValueError(f"price musi byc 'adj' albo 'raw', jest {price!r}")

    if limit is not None:
        df = df.head(limit)

    offset = (df["px_adj"] - df["close"]).to_list()   # 0 dla kontraktu najnowszego
    o, h, low, c = (df[k].to_list() for k in ("open", "high", "low", "close"))
    ts, vol, seg, td = (df[k].to_list() for k in ("ts_utc", "volume", "segment", "trade_date"))

    shift = offset if price == "adj" else [0.0] * len(offset)
    return [
        Bar(ts=ts[i], open=o[i] + shift[i], high=h[i] + shift[i],
            low=low[i] + shift[i], close=c[i] + shift[i],
            volume=int(vol[i]), segment=seg[i],
            px_raw_offset=-offset[i], trade_date=td[i])
        for i in range(len(ts))
    ]
