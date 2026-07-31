"""Pipeline danych: raw -> clean. PLAN.pdf rozdz. 4.2 (osiem krokow).

    Databento (.dbn / parquet, data/raw/, gitignore)
        [1] dedup + sortowanie po ts_event
        [2] walidacja: monotonicznosc, OHLC-spojnosc, wolumen >= 0
        [3] klasyfikacja luk wg kalendarza CME: expected vs anomaly
        [4] mapowanie kontraktow + tabela dat rolowania (wolumenowa)
        [5] sklejenie kontraktu ciaglego + back-adjust roznicowy
        [6] konwersja stref: przechowujemy UTC, indeksujemy sesje w ET
        [7] segmenty sesji i dzien sesyjny
        [8] flagi: dst_transition, short_day, days_to_roll, halt_window
    -> data/clean/*.parquet  (artefakt wersjonowany, commitowany do repo)

SEMANTYKA OHLCV, KTORA RZADZI CALYM MODULEM:
    "If no trade occurs within the interval, no record is printed."
    BRAK BARA JEST POPRAWNYM OPISEM RYNKU, nie defektem feedu. Wersja 1.0 planu
    zakladala ~1380 barow dziennie i kazdy brak traktowala jako anomalie —
    sanity-report tonalby w falszywych alarmach z cienkich godzin sesji
    azjatyckiej. Stad krok [3] nie zlicza luk, tylko je KLASYFIKUJE.

    Forward-fill jest dozwolony dla wskaznikow i BEZWZGLEDNIE ZAKAZANY dla
    barow wejscia i stop-lossa — dlatego ten modul nigdy nie dopisuje barow,
    ktorych nie ma w danych dostawcy. Wolumen zero znaczy, ze nie bylo gdzie
    sie wykonac; wyprodukowanie takiego bara tworzy zysk niemozliwy do wziecia.

REPREZENTACJA CEN (rozdz. 4.3 — rozdzielenie serii):
    open/high/low/close  — seria SKORYGOWANA (px_adj): P&L, equity, zwroty
    px_raw               — cena surowa aktywnego kontraktu: PDH/PDL/PDC i inne
                           poziomy miedzysesyjne
    px_raw_offset        — px_raw - px_adj; pozwala odtworzyc kazda z czterech
                           cen surowych bez trzymania osmiu kolumn
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

import polars as pl

from engine.roll import ContractDay, RollEvent, cumulative_offsets, find_roll_dates
from engine.sessions import (
    ET,
    HALT_ABOLISHED,
    UTC,
    SessionCalendar,
    segment_of,
    uncovered_minutes,
)

RAW_COLUMNS = ("ts_event", "symbol", "open", "high", "low", "close", "volume")

# Kody miesiecy CME. Kontrakty indeksowe sa kwartalne (H, M, U, Z), ale
# parser przyjmuje pelna tabele — pomylka w kodzie ma failowac glosno.
MONTH_CODES = {
    "F": 1, "G": 2, "H": 3, "J": 4, "K": 5, "M": 6,
    "N": 7, "Q": 8, "U": 9, "V": 10, "X": 11, "Z": 12,
}
_CONTRACT_RE = re.compile(r"^([A-Z0-9]{1,4}?)([FGHJKMNQUVXZ])(\d{1,2})$")

BERLIN_OFFSET_NORMALNY = timedelta(hours=6)   # roznica ET <-> Europa poza tygodniami przejsciowymi


class RawDataError(ValueError):
    """Dane surowe naruszaja zalozenie, ktorego pipeline nie ma prawa naprawiac."""


@dataclass
class CleanReport:
    """Slad z przebiegu pipeline'u — wchodzi do sanity-reportu i manifestu."""

    n_raw: int = 0
    n_clean: int = 0
    duplicates_removed: int = 0
    unsorted_rows: int = 0
    ohlc_violations: list[str] = field(default_factory=list)
    negative_volume: int = 0
    zero_volume_bars: int = 0
    expected_gaps: int = 0
    anomaly_gaps: int = 0
    anomalies: list[tuple[datetime, datetime]] = field(default_factory=list)
    rolls: list[RollEvent] = field(default_factory=list)
    contracts: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """Czy dane nadaja sie do badan bez recznego przegladu."""
        return not self.ohlc_violations and self.negative_volume == 0 and self.anomaly_gaps == 0


# --------------------------------------------------------------------------
# [1] dedup + sortowanie
# --------------------------------------------------------------------------

def dedup_and_sort(df: pl.DataFrame, report: CleanReport | None = None) -> pl.DataFrame:
    """Jeden bar na (kontrakt, znacznik czasu), chronologicznie.

    Duplikaty pojawiaja sie przy ponownym pobraniu nakladajacych sie zakresow.
    Zostawiamy pierwszy wiersz — rekordy Databento dla tej samej minuty i tego
    samego kontraktu sa identyczne, wiec wybor nie ma znaczenia; znaczenie ma
    to, ze po tym kroku klucz jest unikalny.
    """
    brakuje = [c for c in RAW_COLUMNS if c not in df.columns]
    if brakuje:
        raise RawDataError(f"Dane surowe nie maja kolumn: {brakuje}")

    przed = df.height
    out = df.unique(subset=["symbol", "ts_event"], keep="first").sort(["symbol", "ts_event"])
    if report is not None:
        report.n_raw = przed
        report.duplicates_removed = przed - out.height
    return out


# --------------------------------------------------------------------------
# [2] walidacja
# --------------------------------------------------------------------------

def validate_bars(df: pl.DataFrame, report: CleanReport | None = None) -> list[str]:
    """Spojnosc OHLC i wolumenu. Zwraca liste naruszen (pusta = dane zdrowe).

    Naruszenia NIE sa naprawiane. Bar, w ktorym low > open, nie jest barem
    z drobna usterka — jest sygnalem, ze cos jest nie tak ze zrodlem albo
    z nasza interpretacja schematu. Cicha naprawa zamieniaja bledny bar
    w wiarygodnie wygladajacy falsz.
    """
    naruszenia: list[str] = []

    zle_ohlc = df.filter(
        (pl.col("low") > pl.col("open"))
        | (pl.col("low") > pl.col("close"))
        | (pl.col("high") < pl.col("open"))
        | (pl.col("high") < pl.col("close"))
        | (pl.col("high") < pl.col("low"))
    )
    for row in zle_ohlc.head(50).iter_rows(named=True):
        naruszenia.append(
            f"{row['ts_event']} {row['symbol']}: OHLC niespojne "
            f"(O={row['open']} H={row['high']} L={row['low']} C={row['close']})"
        )
    if zle_ohlc.height > 50:
        naruszenia.append(f"...oraz {zle_ohlc.height - 50} dalszych naruszen OHLC")

    ujemny = df.filter(pl.col("volume") < 0).height
    if ujemny:
        naruszenia.append(f"{ujemny} barow z ujemnym wolumenem")

    if report is not None:
        report.ohlc_violations = naruszenia
        report.negative_volume = ujemny
        report.zero_volume_bars = df.filter(pl.col("volume") == 0).height
    return naruszenia


# --------------------------------------------------------------------------
# [3] klasyfikacja luk
# --------------------------------------------------------------------------

# Ile minut ciszy jest w danym segmencie normalne (rozdz. 4.2: "brak transakcji
# w cienkiej godzinie"). Wartosci sa JAWNYM ZALOZENIEM, nie prawda objawiona:
# sanity-report drukuje histogram luk, zeby dalo sie je skalibrowac na danych,
# ktore realnie mamy. Zero w RTH nie jest przesada — brak transakcji przez pelna
# minute w najplynniejszym segmencie doby zasluguje na spojrzenie.
CISZA_NORMALNA_MIN: dict[str, int] = {
    "globex_open": 15,
    "asia": 120,        # najnizsza plynnosc doby; dwie godziny bez transakcji sie zdarzaja
    "europe": 30,
    "premarket": 10,
    "rth_open": 1,
    "midday": 3,
    "afternoon": 3,
    "close": 1,
    "after_hours": 45,
    "maintenance": 60,  # i tak wylapane przez kalendarz
}


def classify_gaps(
    timestamps: list[datetime],
    calendar: SessionCalendar,
    report: CleanReport | None = None,
    *,
    tolerancja: dict[str, int] | None = None,
) -> list[str]:
    """Dla kazdego bara: "none" | "expected" | "anomaly" — luka PRZED tym barem.

    Nie zliczamy brakow, tylko je KLASYFIKUJEMY. Luka jest oczekiwana, gdy:
      * kalendarz tlumaczy kazda brakujaca minute (przerwa serwisowa, weekend,
        swieto, dzien skrocony, historyczny halt), albo
      * minuty niewytlumaczone kalendarzem mieszcza sie w progu ciszy dla swojego
        segmentu — bo Databento nie drukuje bara, gdy nie bylo transakcji, a
        w sesji azjatyckiej to norma, nie usterka.

    Wersja 1.0 planu zakladala ~1380 barow dziennie i traktowala kazdy brak jako
    anomalie; raport tonalby w falszywych alarmach dokladnie tam, gdzie rynek
    jest po prostu cienki.
    """
    progi = tolerancja or CISZA_NORMALNA_MIN
    out: list[str] = ["none"] * len(timestamps)
    oczekiwane = anomalie = 0
    anomalia_lista: list[tuple[datetime, datetime]] = []

    for i in range(1, len(timestamps)):
        poprzedni, biezacy = timestamps[i - 1], timestamps[i]
        if biezacy - poprzedni <= timedelta(minutes=1):
            continue

        # Bary istnieja na obu koncach — brakuje minut POMIEDZY nimi.
        brakujace = uncovered_minutes(poprzedni + timedelta(minutes=1), biezacy, calendar)
        if not brakujace:
            out[i] = "expected"
            oczekiwane += 1
            continue

        prog = min(progi.get(segment_of(m), 0) for m in brakujace)
        if len(brakujace) <= prog:
            out[i] = "expected"
            oczekiwane += 1
        else:
            out[i] = "anomaly"
            anomalie += 1
            if len(anomalia_lista) < 200:
                anomalia_lista.append((poprzedni, biezacy))

    if report is not None:
        report.expected_gaps = oczekiwane
        report.anomaly_gaps = anomalie
        report.anomalies = anomalia_lista
    return out


# --------------------------------------------------------------------------
# [4] mapowanie kontraktow i daty rolowan
# --------------------------------------------------------------------------

def parse_contract(symbol: str, reference_year: int) -> tuple[str, int, int]:
    """"MNQH5" -> ("MNQ", 2025, 3). Zwraca (root, rok, miesiac wygasniecia).

    Jednocyfrowy rok jest niejednoznaczny co do dekady; rozstrzygamy go przez
    rok referencyjny (pierwszy rok w danych) — kontrakt nie moze wygasac przed
    poczatkiem historii ani ponad dekade po niej.
    """
    m = _CONTRACT_RE.match(symbol.strip().upper())
    if not m:
        raise RawDataError(
            f"Nierozpoznany symbol kontraktu: {symbol!r}. Oczekiwany format "
            "ROOT + kod miesiaca + rok, np. MNQH5 albo MNQH25."
        )
    root, kod, rok_txt = m.groups()
    miesiac = MONTH_CODES[kod]

    if len(rok_txt) == 2:
        rok = 2000 + int(rok_txt)
    else:
        cyfra = int(rok_txt)
        dekada = (reference_year // 10) * 10
        rok = dekada + cyfra
        if rok < reference_year:
            rok += 10
    return root, rok, miesiac


def contract_order(symbols: list[str], reference_year: int) -> list[str]:
    """Kontrakty uporzadkowane wg terminu wygasniecia."""
    return sorted(set(symbols), key=lambda s: parse_contract(s, reference_year)[1:3])


def daily_contract_volume(df: pl.DataFrame, trade_dates: list[date]) -> dict[str, list[ContractDay]]:
    """Dzienny wolumen i close kazdej nogi kontraktowej — wejscie do reguly rolowania."""
    tmp = df.with_columns(pl.Series("trade_date", trade_dates))
    agg = (
        tmp.group_by(["symbol", "trade_date"])
        .agg(pl.col("volume").sum().alias("volume"), pl.col("close").last().alias("close"))
        .sort(["symbol", "trade_date"])
    )
    out: dict[str, list[ContractDay]] = {}
    for row in agg.iter_rows(named=True):
        out.setdefault(row["symbol"], []).append(ContractDay(
            trade_date=row["trade_date"], contract=row["symbol"],
            close=float(row["close"]), volume=int(row["volume"]),
        ))
    return out


def active_contract_map(
    rolls: list[RollEvent], order: list[str], dni: list[date]
) -> dict[date, str]:
    """Ktory kontrakt jest aktywny w danym dniu sesyjnym.

    Przed pierwszym rolowaniem aktywny jest kontrakt najstarszy; po rolowaniu
    z dnia D nowa noga obowiazuje OD TEGO DNIA (wolumen juz sie przeniosl —
    handlowalibysmy tam na zywo).
    """
    if not order:
        return {}
    mapa: dict[date, str] = {}
    biezacy = order[0]
    po_dacie = {ev.roll_date: ev.to_contract for ev in rolls}
    for d in sorted(dni):
        if d in po_dacie:
            biezacy = po_dacie[d]
        mapa[d] = biezacy
    return mapa


# --------------------------------------------------------------------------
# [6][7][8] czas, segmenty, flagi — wektorowo
# --------------------------------------------------------------------------

def _minuta_doby(czas: pl.Expr) -> pl.Expr:
    """Minuta od polnocy w podanej strefie.

    Rzutowanie na Int32 nie jest kosmetyka: `dt.hour()` zwraca Int8, wiec
    `hour * 60` przekreca sie dla kazdej godziny po 02:00 i daje ciche,
    prawdopodobnie wygladajace bzdury zamiast bledu.
    """
    return czas.dt.hour().cast(pl.Int32) * 60 + czas.dt.minute().cast(pl.Int32)


def _segment_expr(minuta_et: pl.Expr) -> pl.Expr:
    """Segment doby z minuty liczonej od polnocy ET (rozdz. 3.3).

    Odpowiednik `sessions.segment_of`, policzony wektorowo. Rownowaznosc obu
    implementacji jest przedmiotem testu — dwie definicje segmentow, ktore
    rozjezdzaja sie o minute, to najlepszy sposob na niepowtarzalny wynik.
    """
    return (
        pl.when(minuta_et >= 18 * 60).then(
            pl.when(minuta_et < 19 * 60).then(pl.lit("globex_open")).otherwise(pl.lit("asia"))
        )
        .when(minuta_et < 2 * 60).then(pl.lit("asia"))
        .when(minuta_et < 8 * 60 + 30).then(pl.lit("europe"))
        .when(minuta_et < 9 * 60 + 30).then(pl.lit("premarket"))
        .when(minuta_et < 10 * 60 + 30).then(pl.lit("rth_open"))
        .when(minuta_et < 13 * 60 + 30).then(pl.lit("midday"))
        .when(minuta_et < 15 * 60).then(pl.lit("afternoon"))
        .when(minuta_et < 16 * 60).then(pl.lit("close"))
        .when(minuta_et < 17 * 60).then(pl.lit("after_hours"))
        .otherwise(pl.lit("maintenance"))
    )


def annotate_time(df: pl.DataFrame, ts_col: str = "ts_event") -> pl.DataFrame:
    """Kolumny czasowe: segment, trade_date, dst_transition, halt_window.

    Przechowujemy UTC, indeksujemy w ET (rozdz. 4.4). Otwarcie RTH to zawsze
    9:30 ET — w UTC 13:30 albo 14:30 zaleznie od pory roku, wiec definicja
    w UTC rozjechalaby wszystkie statystyki otwarcia dwa razy w roku.
    """
    et = pl.col(ts_col).dt.convert_time_zone("America/New_York")
    minuta = _minuta_doby(et)

    # Dzien sesyjny zaczyna sie o 18:00 ET dnia poprzedniego; niedzielny wieczor
    # nalezy juz do poniedzialku.
    baza = pl.when(minuta >= 18 * 60).then(
        et.dt.date() + pl.duration(days=1)
    ).otherwise(et.dt.date())
    dzien_tygodnia = baza.dt.weekday()          # 1 = poniedzialek ... 7 = niedziela
    trade_dt = (
        pl.when(dzien_tygodnia == 6).then(baza + pl.duration(days=2))
        .when(dzien_tygodnia == 7).then(baza + pl.duration(days=1))
        .otherwise(baza)
    )

    # Tydzien przejsciowy DST: USA i Europa zmieniaja czas w rozne tygodnie,
    # wiec relacja miedzy otwarciem Europy a godzinami USA jest przez 1-3
    # tygodnie w roku przesunieta. Zamiast wypisywac daty, mierzymy roznice
    # stref bezposrednio — definicja odporna na kazda zmiane przepisow.
    berlin = pl.col(ts_col).dt.convert_time_zone("Europe/Berlin")
    roznica = (berlin.dt.replace_time_zone(None) - et.dt.replace_time_zone(None))

    ct = pl.col(ts_col).dt.convert_time_zone("America/Chicago")
    minuta_ct = _minuta_doby(ct)

    return df.with_columns(
        _segment_expr(minuta).alias("segment"),
        trade_dt.alias("trade_date"),
        (roznica != pl.duration(hours=6)).alias("dst_transition"),
        (
            (ct.dt.date() < pl.lit(HALT_ABOLISHED))
            & (minuta_ct >= 15 * 60 + 15)
            & (minuta_ct < 15 * 60 + 30)
        ).alias("halt_window"),
    )


# --------------------------------------------------------------------------
# Orkiestracja
# --------------------------------------------------------------------------

def build_continuous(
    raw: pl.DataFrame,
    calendar: SessionCalendar,
    *,
    ts_col: str = "ts_event",
    strict: bool = True,
) -> tuple[pl.DataFrame, CleanReport]:
    """Pelny przebieg raw -> clean. Zwraca (ramka, raport).

    `strict=True` przerywa przy naruszeniu spojnosci OHLC albo ujemnym
    wolumenie: to nie sa usterki do obejscia, tylko sygnal, ze zrodlo albo
    interpretacja schematu wymaga wyjasnienia PRZED liczeniem czegokolwiek.
    """
    report = CleanReport()

    # [1] dedup + sortowanie
    df = dedup_and_sort(raw, report)
    if df.is_empty():
        raise RawDataError("Dane surowe sa puste")
    if df[ts_col].dtype.time_zone is None:
        df = df.with_columns(pl.col(ts_col).dt.replace_time_zone("UTC"))

    # [2] walidacja
    naruszenia = validate_bars(df, report)
    if naruszenia and strict:
        raise RawDataError(
            "Dane surowe nie przechodza walidacji:\n  " + "\n  ".join(naruszenia[:10])
            + "\nNaruszen NIE naprawiamy po cichu — wyjasnij zrodlo przed dalsza praca."
        )

    # [6][7][8] czas i segmenty (potrzebne juz do agregacji dziennej)
    df = annotate_time(df, ts_col)

    # [4] mapowanie kontraktow + daty rolowan (regula wolumenowa)
    rok_bazowy = int(df[ts_col].min().year)
    kontrakty = contract_order(df["symbol"].to_list(), rok_bazowy)
    dzienne = daily_contract_volume(df, df["trade_date"].to_list())
    rolls = find_roll_dates(dzienne, kontrakty)
    report.rolls = rolls
    report.contracts = kontrakty

    # [5] sklejenie: w kazdym dniu sesyjnym zostaje wylacznie noga aktywna
    aktywny = active_contract_map(rolls, kontrakty, df["trade_date"].unique().to_list())
    df = df.with_columns(
        pl.col("trade_date").replace_strict(aktywny, default=None).alias("_aktywny")
    ).filter(pl.col("symbol") == pl.col("_aktywny")).drop("_aktywny")

    # back-adjust roznicowy: px_adj = px_raw + offset(kontrakt)
    offsets = cumulative_offsets(rolls)
    off = pl.col("symbol").replace_strict(offsets, default=0.0, return_dtype=pl.Float64)
    df = df.with_columns(
        pl.col("close").alias("px_raw"),
        (pl.col("open") + off).alias("open"),
        (pl.col("high") + off).alias("high"),
        (pl.col("low") + off).alias("low"),
        (pl.col("close") + off).alias("close"),
        (-off).alias("px_raw_offset"),        # px_raw - px_adj
    ).with_columns(pl.col("close").alias("px_adj"))

    # [3] klasyfikacja luk — dopiero na serii ciaglej, bo dopiero ona jest
    # tym, co realnie widzialby handlujacy jedna noga naraz
    df = df.sort(ts_col)
    df = df.with_columns(
        pl.Series("gap_kind", classify_gaps(df[ts_col].to_list(), calendar, report))
    )

    # [8] pozostale flagi
    dni_do_rolowania = sorted(ev.roll_date for ev in rolls)
    df = df.with_columns(
        pl.col("trade_date").map_elements(
            lambda d: _dni_do_rolowania(d, dni_do_rolowania), return_dtype=pl.Int32
        ).alias("days_to_roll"),
        pl.col("trade_date").is_in(list(calendar.short_days)).alias("short_day"),
    )

    df = df.rename({ts_col: "ts_utc", "symbol": "contract"}).select(
        "ts_utc", "open", "high", "low", "close", "volume", "contract",
        "px_raw", "px_adj", "px_raw_offset", "trade_date", "segment", "gap_kind",
        "dst_transition", "short_day", "days_to_roll", "halt_window",
    )
    report.n_clean = df.height
    return df, report


def _dni_do_rolowania(d: date, daty: list[date]) -> int | None:
    przyszle = [x for x in daty if x >= d]
    return (min(przyszle) - d).days if przyszle else None


def manifest_entry(
    df: pl.DataFrame, report: CleanReport, *, path: str, schema_version: str,
    downloaded: date, sha256: str,
) -> str:
    """Wpis do data/manifest.md — bez niego wynik nie jest odtwarzalny.

    Databento zmienil normalizacje GLBX.MDP3 w lipcu 2026: bez przypietej
    wersji schematu nie da sie pozniej ustalic, na czym liczone byly wyniki.
    """
    return "\n".join([
        f"## {path}",
        "",
        f"- zakres: {df['ts_utc'].min()} — {df['ts_utc'].max()}",
        f"- barow: {df.height}",
        f"- kontrakty: {', '.join(report.contracts)}",
        f"- rolowania: {len(report.rolls)}",
        f"- wersja schematu dostawcy: {schema_version}",
        f"- data pobrania: {downloaded.isoformat()}",
        f"- sha256: {sha256}",
        f"- luki oczekiwane / anomalie: {report.expected_gaps} / {report.anomaly_gaps}",
        "",
    ])


__all__ = [
    "ET",
    "UTC",
    "CleanReport",
    "RawDataError",
    "active_contract_map",
    "annotate_time",
    "build_continuous",
    "classify_gaps",
    "contract_order",
    "daily_contract_volume",
    "dedup_and_sort",
    "manifest_entry",
    "parse_contract",
    "validate_bars",
]
