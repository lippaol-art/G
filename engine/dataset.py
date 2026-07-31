"""Pipeline raw -> clean: budowa kontraktu ciaglego z danych dostawcy.

Specyfikacja: PLAN.pdf rozdz. 4.2 (osiem krokow), 4.3 (rozdzielenie serii).

Osiem krokow z dokumentu:
    [1] dedup + sortowanie po ts_event
    [2] walidacja: monotonicznosc, spojnosc OHLC, wolumen >= 0
    [3] KLASYFIKACJA LUK wg kalendarza CME: expected vs anomaly
    [4] mapowanie kontraktow + tabela dat rolowania (wolumenowa)
    [5] sklejenie kontraktu ciaglego + back-adjust roznicowy
    [6] konwersja stref: UTC w pliku, sesje indeksowane w ET
    [7] segmenty sesji i dzien sesyjny
    [8] flagi: dst_transition, short_day, days_to_roll, halt_window

ZASADA NIEZMIENNICZOSCI: wyjscie tego modulu jest ARTEFAKTEM WERSJONOWANYM.
Zaden backtest nie czyta z data/raw/. Kazda regeneracja podbija wpis w manifescie.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

import polars as pl

from engine.loader import REQUIRED_COLUMNS
from engine.roll import ContractDay, RollEvent, cumulative_offsets, find_roll_dates
from engine.sessions import (
    SessionCalendar,
    in_historical_halt,
    is_expected_gap,
    segment_of,
    to_et,
    trade_date,
)


@dataclass
class BuildReport:
    """Slad z budowy zbioru — wchodzi do manifestu i sanity-reportu."""

    n_raw: int = 0
    n_after_dedup: int = 0
    n_final: int = 0
    n_contracts: int = 0
    roll_events: list[RollEvent] = field(default_factory=list)
    ohlc_violations: int = 0
    negative_volume: int = 0
    zero_volume_bars: int = 0
    degraded_bars: int = 0
    expected_gaps: int = 0
    anomaly_gaps: list[tuple[datetime, datetime]] = field(default_factory=list)
    first_ts: datetime | None = None
    last_ts: datetime | None = None

    def summary(self) -> str:
        return (
            f"barow surowych: {self.n_raw:,} -> po dedup: {self.n_after_dedup:,} "
            f"-> koncowo: {self.n_final:,} | kontraktow: {self.n_contracts} | "
            f"rolowan: {len(self.roll_events)} | luk anomalnych: {len(self.anomaly_gaps)}"
        )


def _validate_ohlc(df: pl.DataFrame, rep: BuildReport) -> pl.DataFrame:
    """Krok 2: spojnosc OHLC i nieujemny wolumen.

    Bar naruszajacy low <= min(open, close) <= max(open, close) <= high jest
    fizycznie niemozliwy — usuwamy i liczymy, bo to sygnal problemu u dostawcy.
    """
    ok = (
        (pl.col("low") <= pl.col("open"))
        & (pl.col("low") <= pl.col("close"))
        & (pl.col("high") >= pl.col("open"))
        & (pl.col("high") >= pl.col("close"))
        & (pl.col("high") >= pl.col("low"))
    )
    rep.ohlc_violations = int(df.filter(~ok).height)
    rep.negative_volume = int(df.filter(pl.col("volume") < 0).height)
    return df.filter(ok & (pl.col("volume") >= 0))


def _contract_days(df: pl.DataFrame) -> dict[str, list[ContractDay]]:
    """Krok 4: agregacja dzienna per kontrakt — wejscie do reguly wolumenowej."""
    agg = (
        df.group_by(["contract", "trade_date"])
        .agg([pl.col("close").last().alias("close"), pl.col("volume").sum().alias("volume")])
        .sort(["contract", "trade_date"])
    )
    out: dict[str, list[ContractDay]] = {}
    for row in agg.iter_rows(named=True):
        out.setdefault(row["contract"], []).append(
            ContractDay(row["trade_date"], row["contract"], row["close"], int(row["volume"]))
        )
    return out


def _contract_order(days: dict[str, list[ContractDay]]) -> list[str]:
    """Kolejnosc kontraktow wg pierwszego dnia notowania."""
    return sorted(days, key=lambda c: min(d.trade_date for d in days[c]))


def _classify_gaps(ts: list[datetime], calendar: SessionCalendar, rep: BuildReport) -> list[str]:
    """Krok 3: expected vs anomaly.

    KLUCZOWE (rozdz. 4.2): brak bara NIE jest defektem feedu. Databento nie
    drukuje bara, gdy w interwale nie bylo transakcji. Sanity-report, ktory
    tego nie rozroznia, tonie w falszywych alarmach.
    """
    kinds = ["none"] * len(ts)
    for i in range(1, len(ts)):
        delta = (ts[i] - ts[i - 1]).total_seconds()
        if delta <= 60:
            continue
        if is_expected_gap(ts[i - 1], ts[i], calendar):
            kinds[i] = "expected"
            rep.expected_gaps += 1
        else:
            kinds[i] = "anomaly"
            rep.anomaly_gaps.append((ts[i - 1], ts[i]))
    return kinds


def load_degraded_days(path: str = "data/clean/degraded_days.json") -> dict[str, str]:
    """Dni o obnizonej jakosci wg dostawcy (`metadata.get_dataset_condition`).

    Dostawca oznacza czesc dni jako `degraded` albo `missing`. Wiekszosc
    `missing` to soboty (brak handlu — zero problemu), ale kilka `degraded`
    wypada w dni robocze i MUSI byc oznaczone w danych, bo:

      * 2020-02-27 i 2020-02-28 to szczyt krachu covidowego, czyli najbardziej
        ekstremalna zmiennosc w calej probce — dokladnie tam, gdzie strategia
        moglaby "znalezc" przewage na artefakcie danych;
      * analiza rezimow bez tej flagi nie odrozni prawdziwego zachowania rynku
        od dziury w feedzie.

    Zwraca mape 'YYYY-MM-DD' -> 'degraded'|'missing'. Brak pliku = pusta mapa
    (flaga bedzie wszedzie False, co jest bezpiecznym domyslnym zachowaniem).
    """
    import json
    from pathlib import Path

    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text())


def build_continuous(
    df_raw: pl.DataFrame,
    *,
    calendar: SessionCalendar | None = None,
    report: BuildReport | None = None,
    degraded_days: dict[str, str] | None = None,
) -> tuple[pl.DataFrame, BuildReport]:
    """Buduje kontrakt ciagly ze wszystkich nog kontraktowych.

    Wejscie: DataFrame z kolumnami ts_utc, open, high, low, close, volume, contract.
    Wyjscie: DataFrame o schemacie `engine.loader.REQUIRED_COLUMNS`.
    """
    cal = calendar or SessionCalendar()
    rep = report or BuildReport()
    degraded = degraded_days if degraded_days is not None else load_degraded_days()
    rep.n_raw = df_raw.height

    # [1] dedup + sortowanie
    df = df_raw.unique(subset=["ts_utc", "contract"], keep="last").sort(["ts_utc", "contract"])
    rep.n_after_dedup = df.height

    # [2] walidacja
    df = _validate_ohlc(df, rep)

    # [6-7] strefy, dzien sesyjny, segmenty — potrzebne juz do agregacji dziennej
    ts_list = df["ts_utc"].to_list()
    df = df.with_columns([
        pl.Series("trade_date", [trade_date(t) for t in ts_list]),
        pl.Series("segment", [segment_of(t) for t in ts_list]),
        pl.Series("et_hour", [to_et(t).hour for t in ts_list]),
    ])

    # [4] daty rolowan regula wolumenowa
    days = _contract_days(df)
    order = _contract_order(days)
    rep.n_contracts = len(order)
    rep.roll_events = find_roll_dates(days, order)

    # Ktory kontrakt jest aktywny w danym dniu sesyjnym
    active: dict[date, str] = {}
    if rep.roll_events:
        granice = [(e.roll_date, e.to_contract) for e in rep.roll_events]
        biezacy = rep.roll_events[0].from_contract
        wszystkie_dni = sorted({d for lst in days.values() for d in (x.trade_date for x in lst)})
        idx = 0
        for d in wszystkie_dni:
            while idx < len(granice) and d >= granice[idx][0]:
                biezacy = granice[idx][1]
                idx += 1
            active[d] = biezacy
    else:
        jedyny = order[0] if order else ""
        for lst in days.values():
            for cd in lst:
                active[cd.trade_date] = jedyny

    df = df.with_columns(
        pl.Series("active_contract", [active.get(d, "") for d in df["trade_date"].to_list()])
    ).filter(pl.col("contract") == pl.col("active_contract")).drop("active_contract")

    # [5] back-adjust roznicowy — px_raw zostaje nietkniete (rozdz. 4.3)
    offsets = cumulative_offsets(rep.roll_events)
    contracts = df["contract"].to_list()
    off_col = [offsets.get(c, 0.0) for c in contracts]

    df = df.with_columns([
        pl.col("close").alias("px_raw"),
        (pl.col("close") + pl.Series("_off", off_col)).alias("px_adj"),
    ])

    # [3] klasyfikacja luk — na finalnej, przefiltrowanej serii
    kinds = _classify_gaps(df["ts_utc"].to_list(), cal, rep)
    df = df.with_columns(pl.Series("gap_kind", kinds))

    # [8] flagi
    ts_list = df["ts_utc"].to_list()
    td_list = df["trade_date"].to_list()
    roll_dates = [e.roll_date for e in rep.roll_events]

    def _days_to_roll(d: date) -> int:
        przyszle = [r for r in roll_dates if r >= d]
        return (min(przyszle) - d).days if przyszle else -1

    df = df.with_columns([
        pl.Series("halt_window", [in_historical_halt(t) for t in ts_list]),
        pl.Series("short_day", [d in cal.short_days for d in td_list]),
        pl.Series("days_to_roll", [_days_to_roll(d) for d in td_list]),
        pl.Series("dst_transition", [_is_dst_week(d) for d in td_list]),
        pl.Series("data_condition",
                  [degraded.get(d.isoformat(), "available") for d in td_list]),
    ])

    rep.degraded_bars = int(df.filter(pl.col("data_condition") != "available").height)
    rep.zero_volume_bars = int(df.filter(pl.col("volume") == 0).height)
    rep.n_final = df.height
    if df.height:
        rep.first_ts = df["ts_utc"].min()
        rep.last_ts = df["ts_utc"].max()

    brakuje = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if brakuje:
        raise ValueError(f"pipeline nie wyprodukowal wymaganych kolumn: {brakuje}")

    return df, rep


def _is_dst_week(d: date) -> bool:
    """Tydzien zmiany czasu w USA (2. niedziela marca, 1. niedziela listopada).

    USA i Europa zmieniaja czas w roznych tygodniach — przez 1-3 tygodnie w roku
    relacja miedzy otwarciem Europy a godzinami USA jest przesunieta (rozdz. 4.4).
    """
    if d.month == 3:
        return 8 <= d.day <= 14
    if d.month == 11:
        return 1 <= d.day <= 7
    if d.month == 10:
        return d.day >= 25          # zmiana w Europie
    return False


def is_spread_symbol(symbol: str) -> bool:
    """Czy symbol oznacza spread kalendarzowy, a nie kontrakt outright.

    CME notuje spready jako 'MNQM9-MNQU9'. Databento zwraca je w tym samym
    strumieniu co kontrakty zwykle — i to jest PULAPKA, bo ich ceny to
    ROZNICE miedzy kontraktami (rzedu 14-31 punktow), a nie poziomy indeksu
    (rzedu 7000-23000).

    Pojedynczy bar spreadu wpuszczony do serii ciaglej wyglada jak krach
    o 99.6% z natychmiastowym odbiciem w kolejnej minucie. Strategia
    "kupuj spadki" zrobilaby na takich barach fikcyjna fortune — to jest
    dokladnie ta klasa cichego bledu, ktory produkuje spektakularne wyniki
    backtestu nie do powtorzenia na zywo.
    """
    return "-" in symbol


def normalize_databento(df: pl.DataFrame) -> pl.DataFrame:
    """Mapuje surowy DataFrame Databento na schemat wejsciowy pipeline'u.

    Odfiltrowuje spready kalendarzowe (patrz `is_spread_symbol`) i normalizuje
    ceny — Databento potrafi zwracac je jako liczby calkowite w jednostkach
    1e-9 albo juz jako float, zaleznie od sciezki odczytu.
    """
    kolumny = df.columns
    out = df

    if "ts_event" in kolumny:
        out = out.rename({"ts_event": "ts_utc"})

    for c in ("open", "high", "low", "close"):
        if c in out.columns and out[c].dtype in (pl.Int64, pl.Int32):
            out = out.with_columns((pl.col(c) / 1e9).alias(c))

    if "symbol" in out.columns and "contract" not in out.columns:
        out = out.rename({"symbol": "contract"})

    # ODFILTROWANIE SPREADOW — musi nastapic przed jakakolwiek agregacja,
    # inaczej zafalszuja i szereg cenowy, i regule wolumenowa rolowania.
    out = out.filter(~pl.col("contract").str.contains("-"))

    return out.select(
        ["ts_utc", "open", "high", "low", "close", "volume", "contract"]
    )
