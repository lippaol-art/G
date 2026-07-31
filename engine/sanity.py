"""Sanity-report danych — PLAN.pdf rozdz. 4.6.

Raport powstaje po KAZDEJ regeneracji data/clean/ i ma jedno zadanie: pokazac,
czego w danych nie rozumiemy, zanim ktos policzy na nich pierwsza strategie.

Zasada, ktora rzadzi calym modulem: BRAK BARA NIE JEST LUKA W DANYCH.
Databento nie drukuje bara, gdy w minucie nie bylo transakcji. Dlatego raport
nigdzie nie porownuje liczby barow z 1380 — liczy je per segment, bo oczekiwana
liczba zalezy od plynnosci pory doby, i klasyfikuje kazda przerwe zamiast ja
zliczac.

Raport nie zwraca oceny "dane sa dobre". Zwraca liste pozycji do przejrzenia
przez czlowieka — bo jedyna rzecza gorsza od brudnych danych sa brudne dane
z zielonym stemplem.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

import polars as pl

from engine.sessions import SessionCalendar, trade_date

# Bar o zakresie ponad 0.5% ceny w jedna minute (rozdz. 4.6) — do obejrzenia
# z lista dat. Zwykle to publikacja makro, czasem blad danych; roznica jest
# widoczna dopiero po spojrzeniu na date.
PROG_OUTLIERA = 0.005

# Zdarzenia rangi 1, ktore MUSZA wystapic w kazdym miesiacu historii.
ZDARZENIA_MIESIECZNE = ("CPI", "NFP")
POSIEDZENIA_FOMC_ROCZNIE = 8


@dataclass
class Sekcja:
    """Jedna sekcja raportu. `do_przegladu` niepuste = pozycja dla czlowieka."""

    tytul: str
    tresc: str = ""
    do_przegladu: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.do_przegladu


@dataclass
class SanityReport:
    sekcje: list[Sekcja] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return all(s.ok for s in self.sekcje)

    @property
    def do_przegladu(self) -> list[str]:
        return [p for s in self.sekcje for p in s.do_przegladu]

    def render(self) -> str:
        linie = [
            "# Raport jakosci danych",
            "",
            f"Wygenerowano: {self.meta.get('generated', datetime.now().isoformat(timespec='seconds'))}",
            "",
        ]
        if self.ok:
            linie += ["**Brak pozycji do przegladu.**", ""]
        else:
            linie += [
                f"**Pozycji do przegladu: {len(self.do_przegladu)}.** "
                "Zaden wynik badawczy liczony na tych danych nie jest wiarygodny, "
                "dopoki lista nie zostanie przejrzana i zamknieta.",
                "",
            ]
        for s in self.sekcje:
            linie += [f"## {s.tytul}", ""]
            if s.tresc:
                linie += [s.tresc, ""]
            if s.do_przegladu:
                linie += ["**Do przegladu:**", ""]
                linie += [f"- {p}" for p in s.do_przegladu]
                linie += [""]
        return "\n".join(linie)


def _liczba(v) -> str:
    """Liczby w tabelach raportu.

    Notacja wykladnicza jest tu bledem uzytkowym: 2.101e+04 zamiast 21007.5
    ukrywa dokladnie te cyfry, dla ktorych czlowiek czyta raport (poziom ceny
    z dokladnoscia do ticka).
    """
    if isinstance(v, bool) or not isinstance(v, float):
        return str(v)
    return f"{v:.4f}".rstrip("0").rstrip(".") or "0"


def _tabela(df: pl.DataFrame) -> str:
    """Ramka jako tabela markdown."""
    if df.is_empty():
        return "_(brak wierszy)_"
    naglowek = "| " + " | ".join(df.columns) + " |"
    linia = "|" + "|".join(["---"] * len(df.columns)) + "|"
    wiersze = ["| " + " | ".join(_liczba(v) for v in row) + " |" for row in df.iter_rows()]
    return "\n".join([naglowek, linia, *wiersze])


# --------------------------------------------------------------------------
# Sekcje raportu
# --------------------------------------------------------------------------

def bary_per_segment(df: pl.DataFrame) -> Sekcja:
    """Liczba barow na dzien sesyjny, ROZBITA NA SEGMENTY.

    Rozbicie jest istotne: w RTH spodziewamy sie blisko 390 barow, w sesji
    azjatyckiej istotnie mniej — i to jest normalne. Wspolna srednia dobowa
    zamazalaby jedno i drugie.
    """
    per_dzien = (
        df.group_by(["trade_date", "segment"]).len()
        .group_by("segment")
        .agg(
            pl.col("len").mean().round(1).alias("srednia"),
            pl.col("len").min().alias("min"),
            pl.col("len").max().alias("max"),
            pl.col("len").len().alias("dni"),
        )
        .sort("segment")
    )
    return Sekcja("Bary na dzien sesyjny wg segmentu", _tabela(per_dzien))


def luki(df: pl.DataFrame) -> Sekcja:
    """Histogram luk z OBOWIAZKOWA klasyfikacja kazdej z nich."""
    zliczenia = df.group_by("gap_kind").len().sort("gap_kind")
    anomalie = df.filter(pl.col("gap_kind") == "anomaly")

    do_przegladu = [
        f"luka bez wyjasnienia przed barem {row['ts_utc']} "
        f"(segment {row['segment']}, dzien sesyjny {row['trade_date']})"
        for row in anomalie.head(50).iter_rows(named=True)
    ]
    if anomalie.height > 50:
        do_przegladu.append(f"...oraz {anomalie.height - 50} dalszych luk-anomalii")

    return Sekcja(
        "Klasyfikacja luk",
        _tabela(zliczenia) + "\n\n"
        "_expected_ = przerwa serwisowa, weekend, swieto, dzien skrocony, halt "
        "albo cisza mieszczaca sie w normie segmentu. _anomaly_ = wszystko inne.",
        do_przegladu,
    )


def wolumen_zero(df: pl.DataFrame) -> Sekcja:
    """Udzial barow o zerowym wolumenie w segmencie.

    Bar z wolumenem zero w danych minutowych Databento nie powinien istniec —
    jesli jest, prawdopodobnie powstal z forward-fillu gdzies w drodze. Silnik
    i tak zabroni w nim wykonania (engine/guards.py), ale zrodlo trzeba znalezc.
    """
    per_segment = (
        df.group_by("segment")
        .agg(
            pl.col("volume").len().alias("bary"),
            (pl.col("volume") == 0).sum().alias("wolumen_zero"),
        )
        .with_columns(
            (pl.col("wolumen_zero") / pl.col("bary") * 100).round(3).alias("udzial_%")
        )
        .sort("segment")
    )
    zerowe = int(df.filter(pl.col("volume") == 0).height)
    do_przegladu = []
    if zerowe:
        do_przegladu.append(
            f"{zerowe} barow o wolumenie zero — dane minutowe dostawcy nie powinny "
            "ich zawierac; sprawdz, czy nie powstaly z forward-fillu"
        )
    return Sekcja("Bary o zerowym wolumenie", _tabela(per_segment), do_przegladu)


def outliery_zakresu(df: pl.DataFrame, prog: float = PROG_OUTLIERA) -> Sekcja:
    """Bary o zakresie ponad `prog` ceny w jedna minute — z lista dat."""
    z_zakresem = df.with_columns(
        ((pl.col("high") - pl.col("low")) / pl.col("close").abs()).alias("zakres_rel")
    )
    outliery = z_zakresem.filter(pl.col("zakres_rel") > prog).sort("zakres_rel", descending=True)

    tresc = _tabela(
        outliery.head(25).select("ts_utc", "segment", "open", "high", "low", "close",
                                 "volume", "zakres_rel")
    )
    do_przegladu = []
    if outliery.height:
        dni = outliery["trade_date"].unique().sort().to_list()
        do_przegladu.append(
            f"{outliery.height} barow o zakresie > {prog:.2%} w minute, "
            f"w {len(dni)} dniach sesyjnych: {', '.join(str(d) for d in dni[:15])}"
            + (" ..." if len(dni) > 15 else "")
        )
    return Sekcja(f"Bary o zakresie > {prog:.2%}", tresc, do_przegladu)


def ciaglosc_rolowania(df: pl.DataFrame, udzial_spreadu: float = 0.5) -> Sekcja:
    """Zero SZTUCZNYCH skokow w dniach rolowan po adjustmencie (rozdz. 4.3, 5.6).

    Nieskorygowane sklejenie zostawia w serii skok o spread miedzy kontraktami.
    Strategia "kupuj spadki" na takiej serii zarabia na lukach, ktore nigdy nie
    byly handlowalne — jeden z najczestszych sposobow, w jaki amatorskie
    backtesty futures produkuja fikcyjne zyski.

    Progiem NIE moze byc stala liczba punktow: rolowanie wypada na granicy dni
    sesyjnych, wiec kazde przejscie zawiera w sobie normalna luke nocna. Pytanie
    brzmi "czy skok przypomina spread rolowania", a nie "czy skok jest duzy" —
    stad porownanie z faktycznym spreadem, odtworzonym z kolumny px_raw_offset
    (roznica offsetow dwoch nog to dokladnie spread, o ktory je sklejono).
    """
    z_poprzednim = df.sort("ts_utc").with_columns(
        pl.col("close").shift(1).alias("_prev_close"),
        pl.col("contract").shift(1).alias("_prev_contract"),
        pl.col("px_raw_offset").shift(1).alias("_prev_offset"),
    )
    granice = z_poprzednim.filter(
        pl.col("_prev_contract").is_not_null()
        & (pl.col("contract") != pl.col("_prev_contract"))
    ).with_columns(
        (pl.col("open") - pl.col("_prev_close")).abs().alias("skok"),
        (pl.col("px_raw_offset") - pl.col("_prev_offset")).abs().alias("spread"),
    )

    do_przegladu = [
        f"{row['trade_date']}: przejscie {row['_prev_contract']} -> {row['contract']} "
        f"ze skokiem {row['skok']:.2f} pkt przy spreadzie rolowania {row['spread']:.2f} pkt "
        "— back-adjust nie zadzialal"
        for row in granice.iter_rows(named=True)
        if row["spread"] > 1e-6 and row["skok"] > udzial_spreadu * row["spread"]
    ]
    return Sekcja(
        "Ciaglosc serii w dniach rolowan",
        _tabela(granice.select("trade_date", "_prev_contract", "contract", "skok", "spread")),
        do_przegladu,
    )


def rozjazd_raw_adj(df: pl.DataFrame) -> Sekcja:
    """Kontrola, ze rozdzielenie serii z rozdz. 4.3 dziala.

    W obrebie jednego kontraktu roznica px_raw - px_adj musi byc STALA. Gdyby
    plywala, poziomy referencyjne liczylyby sie raz na jednej, raz na drugiej
    skali — i nikt by tego nie zauwazyl poza dziwnymi sygnalami raz na kwartal.
    """
    per_kontrakt = (
        df.with_columns((pl.col("px_raw") - pl.col("px_adj")).alias("_roznica"))
        .group_by("contract")
        .agg(
            pl.col("_roznica").min().alias("offset_min"),
            pl.col("_roznica").max().alias("offset_max"),
            pl.col("px_raw_offset").n_unique().alias("wartosci_offsetu"),
        )
        .sort("contract")
    )
    do_przegladu = [
        f"kontrakt {row['contract']}: offset px_raw-px_adj nie jest stala "
        f"({row['offset_min']:.2f} .. {row['offset_max']:.2f})"
        for row in per_kontrakt.iter_rows(named=True)
        if abs(row["offset_max"] - row["offset_min"]) > 1e-6
    ]
    return Sekcja("Rozdzielenie serii px_raw / px_adj", _tabela(per_kontrakt), do_przegladu)


def zgodnosc_z_kalendarzem(df: pl.DataFrame, calendar: SessionCalendar) -> Sekcja:
    """Kalendarz kontra dane — w obie strony.

    Kalendarz jest generowany z regul, wiec moze sie mylic: dorazne zamkniecie
    (zaloba narodowa, awaria gieldy) nie wynika z zadnej reguly. Dwa objawy
    rozjazdu: bary w dniu oznaczonym jako zamkniety oraz dzien handlowy bez
    ani jednego bara.
    """
    dni_w_danych = set(df["trade_date"].unique().to_list())
    do_przegladu: list[str] = []

    zamkniete_z_barami = sorted(d for d in dni_w_danych if not calendar.is_trading_day(d))
    for d in zamkniete_z_barami[:20]:
        do_przegladu.append(
            f"{d}: kalendarz mowi 'brak sesji', a w danych sa bary — popraw kalendarz "
            "albo wyjasnij pochodzenie barow"
        )

    if dni_w_danych:
        pierwszy, ostatni = min(dni_w_danych), max(dni_w_danych)
        brakujace = [
            d for d in _dni_robocze(pierwszy, ostatni)
            if calendar.is_trading_day(d) and d not in dni_w_danych
        ]
        for d in brakujace[:20]:
            do_przegladu.append(f"{d}: dzien handlowy bez ani jednego bara")
        if len(brakujace) > 20:
            do_przegladu.append(f"...oraz {len(brakujace) - 20} dalszych dni bez barow")

    tresc = (
        f"Dni sesyjnych w danych: {len(dni_w_danych)}. "
        f"Kalendarz zweryfikowany z publikacja gieldy: "
        f"{'TAK' if calendar.verified else 'NIE'}."
    )
    if not calendar.verified:
        do_przegladu.append(
            "kalendarz CME nie zostal porownany z kalendarzem opublikowanym przez gielde "
            "(SessionCalendar.verified = False) — generator z regul nie przewidzi sesji "
            "odwolanej doraznie"
        )
    return Sekcja("Zgodnosc z kalendarzem CME", tresc, do_przegladu)


def pokrycie_zdarzen(events: pl.DataFrame | None, pierwszy: date, ostatni: date) -> Sekcja:
    """Kazdy miesiac historii musi miec komplet zdarzen rangi 1.

    CPI i NFP publikowane sa co miesiac, FOMC ma osiem posiedzen w roku. Dziura
    w kalendarzu zdarzen nie objawia sie jako blad — objawia sie jako hipoteza
    zdarzeniowa, ktora "nie dziala" w miesiacach, w ktorych po prostu nie
    wiedzielismy o publikacji.
    """
    if events is None or events.is_empty():
        return Sekcja(
            "Pokrycie kalendarza zdarzen",
            "_(brak pliku events.csv)_",
            ["kalendarz zdarzen nie zostal jeszcze zbudowany (rozdz. 4.5)"],
        )

    ev = events.with_columns(
        pl.col("ts_utc").dt.year().alias("_rok"), pl.col("ts_utc").dt.month().alias("_mies")
    )
    ranga1 = ev.filter(pl.col("rank") == 1)
    do_przegladu: list[str] = []

    for rok, mies in _miesiace(pierwszy, ostatni):
        w_miesiacu = ranga1.filter((pl.col("_rok") == rok) & (pl.col("_mies") == mies))
        nazwy = w_miesiacu["name"].to_list()
        for wymagane in ZDARZENIA_MIESIECZNE:
            if not any(wymagane in str(n) for n in nazwy):
                do_przegladu.append(f"{rok}-{mies:02d}: brak zdarzenia {wymagane}")

    for rok in range(pierwszy.year, ostatni.year + 1):
        fomc = ranga1.filter(
            (pl.col("_rok") == rok) & pl.col("name").str.contains("FOMC_decision")
        ).height
        pelny_rok = pierwszy.year < rok < ostatni.year
        if pelny_rok and fomc < POSIEDZENIA_FOMC_ROCZNIE:
            do_przegladu.append(
                f"{rok}: {fomc} posiedzen FOMC w kalendarzu, oczekiwane "
                f"{POSIEDZENIA_FOMC_ROCZNIE}"
            )

    zliczenia = ev.group_by("rank").len().sort("rank")
    return Sekcja("Pokrycie kalendarza zdarzen", _tabela(zliczenia), do_przegladu)


def weryfikacja_krzyzowa(df: pl.DataFrame, n_sesji: int = 10) -> Sekcja:
    """Lista sesji do RECZNEGO porownania ze zrodlem niezaleznym (rozdz. 4.6).

    Tego kroku nie da sie zautomatyzowac w tym repo: wymaga drugiego zrodla
    danych. Raport wyznacza wiec deterministyczna probke — pelny miesiac plus
    n sesji rozlozonych rownomiernie po historii — i podaje ekstrema, ktore
    maja sie zgadzac do dwoch tickow.
    """
    dni = df["trade_date"].unique().sort().to_list()
    if not dni:
        return Sekcja("Weryfikacja krzyzowa", "_(brak danych)_")

    krok = max(1, len(dni) // n_sesji)
    probka = dni[::krok][:n_sesji]
    ekstrema = (
        df.filter(pl.col("trade_date").is_in(probka))
        .group_by("trade_date")
        .agg(pl.col("px_raw").max().alias("max_raw"), pl.col("px_raw").min().alias("min_raw"))
        .sort("trade_date")
    )
    miesiac = dni[len(dni) // 2].strftime("%Y-%m")
    return Sekcja(
        "Weryfikacja krzyzowa (krok reczny)",
        f"Miesiac do porownania w calosci: **{miesiac}**.\n\n"
        "Sesje do porownania z niezaleznym wykresem — ekstrema maja sie zgadzac "
        "do 2 tickow (0.50 pkt), ceny SUROWE, nie skorygowane:\n\n"
        + _tabela(ekstrema),
        ["weryfikacja krzyzowa nie zostala jeszcze wykonana (krok reczny, wymaga drugiego zrodla)"],
    )


# --------------------------------------------------------------------------
# Orkiestracja
# --------------------------------------------------------------------------

def build_report(
    df: pl.DataFrame,
    calendar: SessionCalendar,
    *,
    events: pl.DataFrame | None = None,
    meta: dict | None = None,
) -> SanityReport:
    """Pelny sanity-report dla oczyszczonej ramki."""
    dni = df["trade_date"].unique().sort().to_list()
    pierwszy, ostatni = (dni[0], dni[-1]) if dni else (date.today(), date.today())

    metadane = {
        "generated": datetime.now().isoformat(timespec="seconds"),
        "n_bars": df.height,
        "zakres": f"{pierwszy} — {ostatni}",
        "kontrakty": ", ".join(sorted(set(df["contract"].to_list()))),
        **(meta or {}),
    }
    brak_metadanych = [
        k for k in ("schema_version", "downloaded", "sha256") if not metadane.get(k)
    ]

    sekcje = [
        Sekcja(
            "Metadane zbioru",
            "\n".join(f"- **{k}**: {v}" for k, v in metadane.items()),
            [
                f"brak metadanej '{k}' — bez niej wyniku nie da sie odtworzyc "
                "(dostawca zmienil normalizacje GLBX.MDP3 w lipcu 2026)"
                for k in brak_metadanych
            ],
        ),
        bary_per_segment(df),
        luki(df),
        wolumen_zero(df),
        outliery_zakresu(df),
        ciaglosc_rolowania(df),
        rozjazd_raw_adj(df),
        zgodnosc_z_kalendarzem(df, calendar),
        pokrycie_zdarzen(events, pierwszy, ostatni),
        weryfikacja_krzyzowa(df),
    ]
    return SanityReport(sekcje=sekcje, meta=metadane)


def _dni_robocze(od: date, do: date):
    from datetime import timedelta
    d = od
    while d <= do:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def _miesiace(od: date, do: date):
    rok, mies = od.year, od.month
    while (rok, mies) <= (do.year, do.month):
        yield rok, mies
        rok, mies = (rok + 1, 1) if mies == 12 else (rok, mies + 1)


__all__ = [
    "PROG_OUTLIERA",
    "Sekcja",
    "SanityReport",
    "bary_per_segment",
    "build_report",
    "ciaglosc_rolowania",
    "luki",
    "outliery_zakresu",
    "pokrycie_zdarzen",
    "rozjazd_raw_adj",
    "trade_date",
    "weryfikacja_krzyzowa",
    "wolumen_zero",
    "zgodnosc_z_kalendarzem",
]
