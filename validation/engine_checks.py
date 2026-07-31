"""Walidacja SILNIKA, zanim policzy on cokolwiek — PLAN.pdf rozdz. 5.6.

    "Silnik, ktoremu nie udowodniono poprawnosci, produkuje smiecie
     z dokladnoscia do szesciu miejsc po przecinku."

Cztery testy z rozdz. 5.6, kazdy odpowiadajacy na inne pytanie:

  1. ZEROWA PRZEWAGA — losowe wejscia, symetryczny SL/TP na REALNYCH danych.
     Wynik musi wyjsc ~ -(koszty x liczba transakcji). Kryterium jest
     jednostronne: rzut moneta, ktory ZARABIA, nie ma innego wyjasnienia niz
     przeciek informacji w silniku, a rzut moneta, ktory traci wiecej od
     nominalnych kosztow, to tylko konserwatyzm modelu poslizgu.

  2. ZNANY EFEKT — asymetria overnight/intraday na indeksach US. To nie jest
     nasza strategia, tylko LINIJKA: sprawdzamy, czy silnik mierzy to samo,
     co daje bezposredni rachunek na barach. Rozjazd znaczy, ze silnik zle
     mierzy, a wtedy nie ma znaczenia, co pokaze na hipotezie.

  3. SYMETRIA — odwrocenie long<->short na strategii losowej daje wynik
     lustrzany przed kosztami. Rozjazd = blad w obsludze jednej ze stron.

  4. DETERMINIZM — dwa przebiegi z tym samym ziarnem daja wyniki bitowo
     identyczne. Bez tego zaden wynik projektu nie jest odtwarzalny.

Testy 1 i 2 wymagaja REALNYCH danych (rozdz. 5.6 mowi o tym wprost) i sa
uruchamiane przez scripts/engine_validation.py po Etapie 1. Testy 3 i 4
dzialaja na dowolnej serii, wiec chodza takze na fixture'ach w CI.
"""

from __future__ import annotations

import math
import random
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field

from engine.backtest import Bar, Order, Result, run
from engine.costs import CostModel
from engine.sessions import to_et

# Ile odchylen standardowych sredniej wolno odbiegac od oczekiwania, zanim
# uznamy wynik za niezgodny. 3 sigma przy kilku tysiacach transakcji to prog,
# ktorego czysty przypadek praktycznie nie przekracza — a przeciek przekracza
# go natychmiast i o rzedy wielkosci.
PROG_SIGMA = 3.0


@dataclass
class CheckResult:
    """Wynik jednego testu silnika."""

    nazwa: str
    zdany: bool
    opis: str
    liczby: dict = field(default_factory=dict)

    def __str__(self) -> str:
        stempel = "OK  " if self.zdany else "BLAD"
        return f"[{stempel}] {self.nazwa}: {self.opis}"


# --------------------------------------------------------------------------
# Strategie-narzedzia. Zadna z nich nie jest kandydatem do handlu.
# --------------------------------------------------------------------------

class RandomStrategy:
    """Rzut moneta z symetrycznym SL/TP — narzedzie do testu zerowej przewagi.

    Symetria SL i TP jest istotna: przy nierownym stosunku R:R rozklad wynikow
    brutto nie jest symetryczny nawet w idealnym silniku, wiec test przestalby
    cokolwiek rozstrzygac.

    Losowosc jest ziarnowana i zyje W STRATEGII, nie w silniku — silnik pozostaje
    deterministyczny (rozdz. 5.6, test 4).
    """

    def __init__(self, seed: int = 0, *, prawdopodobienstwo: float = 0.01,
                 odleglosc_pkt: float = 10.0, odwroc: bool = False):
        self.seed = seed
        self.p = prawdopodobienstwo
        self.odleglosc = odleglosc_pkt
        self.odwroc = odwroc
        self._rng = random.Random(seed)

    def on_bar(self, bar: Bar, history: Sequence[Bar], state: dict) -> list[Order]:
        if self._rng.random() >= self.p:
            return []
        side = "long" if self._rng.random() < 0.5 else "short"
        if self.odwroc:
            side = "short" if side == "long" else "long"
        znak = 1.0 if side == "long" else -1.0
        return [Order(
            side=side,
            sl=bar.close - znak * self.odleglosc,
            tp=bar.close + znak * self.odleglosc,
        )]


def _minuta_et(bar: Bar) -> int:
    et = to_et(bar.ts)
    return et.hour * 60 + et.minute


class SessionBoundaryStrategy:
    """Kupuje na zamknieciu RTH i trzyma do otwarcia (albo odwrotnie).

    Sluzy wylacznie do testu znanego efektu — mierzy, ile silnik naliczy na
    ruchu miedzy sesjami w porownaniu z bezposrednim rachunkiem na barach.
    Stop jest umyslnie odlegly: chodzi o zmierzenie ruchu, nie o zarzadzanie
    ryzykiem, a stop trafiony po drodze zafalszowalby pomiar.

    Wyjscie nie moze byc godzina ("zamknij po 9:30"), bo pozycja overnight
    przechodzi przez polnoc — stad predykat `wyjscie` przekazywany silnikowi
    jako `flat_by`.
    """

    WEJSCIE = {"overnight": 15 * 60 + 59, "intraday": 9 * 60 + 29}
    WYJSCIE = {"overnight": 9 * 60 + 30, "intraday": 15 * 60 + 59}

    def __init__(self, *, tryb: str = "overnight", stop_pkt: float = 2000.0):
        if tryb not in self.WEJSCIE:
            raise ValueError("tryb: 'overnight' albo 'intraday'")
        self.tryb = tryb
        self.stop = stop_pkt

    def on_bar(self, bar: Bar, history: Sequence[Bar], state: dict) -> list[Order]:
        # Sygnal na ostatnim barze przed granica -> wykonanie na open nastepnego.
        if _minuta_et(bar) == self.WEJSCIE[self.tryb]:
            return [Order(side="long", sl=bar.close - self.stop, tag=self.tryb)]
        return []

    def wyjscie(self, bar: Bar) -> bool:
        return _minuta_et(bar) == self.WYJSCIE[self.tryb]


# --------------------------------------------------------------------------
# Test 1 — zerowa przewaga
# --------------------------------------------------------------------------

def zero_edge_check(
    bars: Sequence[Bar],
    *,
    seed: int = 20260731,
    cost: CostModel | None = None,
    prog_sigma: float = PROG_SIGMA,
) -> CheckResult:
    """Losowe wejscia musza tracic mniej wiecej tyle, ile wynosza koszty.

    Kryterium jest JEDNOSTRONNE i jest to decyzja, nie uproszczenie.

    Wynik "brutto" liczymy przed prowizja, ale PO POSLIZGU — i po stronie
    poslizgu silnik jest konserwatywny z zalozenia: stop wykonuje sie na samo
    dotkniecie, a limit dopiero po przebiciu o tick. Zdrowy silnik daje wiec
    na rzucie moneta wynik ujemny, i to tym pewniej, im wieksza proba. Test
    dwustronny odrzucalby poprawny silnik tym czesciej, im wiecej ma danych.

    Kierunek, ktory unicestwia projekt, jest tylko jeden: rzut moneta, ktory
    ZARABIA. Nie ma dla tego zadnego niewinnego wyjasnienia poza przeciekiem
    informacji, i wylacznie ten kierunek zapala czerwone swiatlo.
    """
    cm = cost or CostModel()
    strategia = RandomStrategy(seed=seed)
    wynik = run(bars, strategia, cost=cm)

    if len(wynik.trades) < 30:
        return CheckResult(
            "zerowa przewaga", False,
            f"za malo transakcji ({len(wynik.trades)}) — test bez mocy; "
            "potrzebna dluzsza seria albo wyzsze prawdopodobienstwo wejscia",
            {"n_trades": len(wynik.trades)},
        )

    prowizja = cm.commission_rt
    brutto = [t.pnl_usd + prowizja * t.qty for t in wynik.trades]
    netto = [t.pnl_usd for t in wynik.trades]

    n = len(brutto)
    srednia_brutto = statistics.fmean(brutto)
    sd = statistics.stdev(brutto)
    se = sd / math.sqrt(n) if sd > 0 else 0.0
    t_stat = (srednia_brutto / se) if se > 0 else 0.0

    wygrane = sum(1 for x in brutto if x > 0)
    win_rate = wygrane / n

    zdany = t_stat <= prog_sigma
    opis = (
        f"{n} transakcji, brutto {srednia_brutto:+.2f} USD/transakcje "
        f"(t={t_stat:+.2f}), netto {statistics.fmean(netto):+.2f} USD, "
        f"win rate {win_rate:.1%}"
    )
    if not zdany:
        opis += (
            " — rzut moneta nie ma prawa miec przewagi. Szukaj przecieku "
            "informacji w silniku, zanim policzysz cokolwiek innego."
        )
    elif t_stat < -prog_sigma:
        opis += (
            " (strata istotnie glebsza niz szum — spodziewana przy poslizgu "
            "i wymogu przebicia limitu; sprawdz, czy model kosztow nie jest "
            "przesadnie konserwatywny)"
        )
    return CheckResult("zerowa przewaga", zdany, opis, {
        "n_trades": n,
        "brutto_srednia": srednia_brutto,
        "netto_srednia": statistics.fmean(netto),
        "t_stat": t_stat,
        "win_rate": win_rate,
        "koszt_na_transakcje": prowizja,
    })


# --------------------------------------------------------------------------
# Test 2 — znany efekt (asymetria overnight/intraday)
# --------------------------------------------------------------------------

def overnight_intraday_split(bars: Sequence[Bar]) -> dict[str, float]:
    """Bezposredni rachunek na barach: ile punktow daje noc, ile sesja.

    Rachunek celowo NIE przechodzi przez silnik — jest niezalezna miara,
    z ktora porownujemy to, co silnik naliczy.
    """
    otwarcia: dict[object, float] = {}
    zamkniecia: dict[object, float] = {}
    kolejnosc: list[object] = []

    for bar in bars:
        et = to_et(bar.ts)
        minuta = et.hour * 60 + et.minute
        if not (9 * 60 + 30 <= minuta < 16 * 60):
            continue
        klucz = et.date()
        if klucz not in otwarcia:
            otwarcia[klucz] = bar.open
            kolejnosc.append(klucz)
        zamkniecia[klucz] = bar.close

    overnight = intraday = 0.0
    for poprzedni, biezacy in zip(kolejnosc, kolejnosc[1:], strict=False):
        overnight += otwarcia[biezacy] - zamkniecia[poprzedni]
    for d in kolejnosc:
        intraday += zamkniecia[d] - otwarcia[d]

    return {
        "overnight_pkt": overnight,
        "intraday_pkt": intraday,
        "sesji": len(kolejnosc),
    }


def known_effect_check(bars: Sequence[Bar], *, cost: CostModel | None = None) -> CheckResult:
    """Czy silnik mierzy to samo, co bezposredni rachunek na barach.

    Nie sprawdzamy, czy dryf nocny istnieje — to jest pytanie badawcze
    (karta H004). Sprawdzamy, czy LINIJKA jest prosta: silnik puszczony na
    strategii "kup na zamknieciu, sprzedaj na otwarciu" ma odtworzyc znak
    i rzad wielkosci rachunku recznego. Rozjazd znaczy, ze silnik zle mierzy.
    """
    cm = cost or CostModel()
    recznie = overnight_intraday_split(bars)
    if recznie["sesji"] < 5:
        return CheckResult("znany efekt", False,
                           f"za malo sesji RTH w danych ({recznie['sesji']})", recznie)

    strategia = SessionBoundaryStrategy(tryb="overnight")
    wynik = run(bars, strategia, cost=cm, blackout=False, flat_by=strategia.wyjscie)
    silnik_pkt = sum(t.pnl_points for t in wynik.trades)
    oczekiwane = recznie["overnight_pkt"]

    znak_zgodny = (silnik_pkt >= 0) == (oczekiwane >= 0) or abs(oczekiwane) < 1.0
    skala = abs(silnik_pkt) / abs(oczekiwane) if abs(oczekiwane) > 1e-9 else float("inf")
    rzad_zgodny = 0.2 <= skala <= 5.0 if abs(oczekiwane) >= 1.0 else True

    zdany = bool(znak_zgodny and rzad_zgodny)
    return CheckResult("znany efekt", zdany, (
        f"{recznie['sesji']} sesji: rachunek reczny {oczekiwane:+.1f} pkt overnight "
        f"vs {recznie['intraday_pkt']:+.1f} pkt intraday; silnik naliczyl "
        f"{silnik_pkt:+.1f} pkt na {len(wynik.trades)} transakcjach"
        + ("" if zdany else " — silnik mierzy co innego niz rachunek na barach")
    ), {**recznie, "silnik_pkt": silnik_pkt, "skala": skala})


# --------------------------------------------------------------------------
# Test 3 — symetria
# --------------------------------------------------------------------------

def mirror_bars(bars: Sequence[Bar], os_odbicia: float | None = None) -> list[Bar]:
    """Odbija serie wzgledem poziomu: cena -> 2k - cena, high <-> low.

    Odbita seria jest tym samym rynkiem widzianym "do gory nogami". Strategia
    long na oryginale i short na odbiciu musza dac identyczny wynik — jesli nie,
    jedna ze stron jest w silniku obslugiwana inaczej.
    """
    if not bars:
        return []
    k = os_odbicia if os_odbicia is not None else float(bars[0].open)
    return [
        Bar(ts=b.ts, open=2 * k - b.open, high=2 * k - b.low, low=2 * k - b.high,
            close=2 * k - b.close, volume=b.volume, segment=b.segment,
            px_raw_offset=b.px_raw_offset)
        for b in bars
    ]


def symmetry_check(bars: Sequence[Bar], *, seed: int = 20260731,
                   cost: CostModel | None = None) -> CheckResult:
    """Long na serii i short na jej odbiciu musza dac ten sam wynik."""
    cm = cost or CostModel()
    oryginal = run(bars, RandomStrategy(seed=seed), cost=cm)
    odbicie = run(mirror_bars(bars), RandomStrategy(seed=seed, odwroc=True), cost=cm)

    if not oryginal.trades:
        return CheckResult("symetria", False, "brak transakcji — test bez mocy", {})

    a = [round(t.pnl_points, 9) for t in oryginal.trades]
    b = [round(t.pnl_points, 9) for t in odbicie.trades]
    zdany = a == b

    roznice = [
        f"#{i}: {x:+.4f} vs {y:+.4f}"
        for i, (x, y) in enumerate(zip(a, b, strict=False)) if x != y
    ][:5]
    return CheckResult("symetria", zdany, (
        f"{len(a)} vs {len(b)} transakcji; "
        + ("wyniki lustrzane co do punktu" if zdany
           else "ROZJAZD: " + "; ".join(roznice))
    ), {"n_oryginal": len(a), "n_odbicie": len(b), "n_roznic": sum(
        1 for x, y in zip(a, b, strict=False) if x != y)})


# --------------------------------------------------------------------------
# Test 4 — determinizm
# --------------------------------------------------------------------------

def _odcisk(res: Result) -> tuple:
    return tuple(
        (t.entry_ts, t.entry_px, t.exit_ts, t.exit_px, t.pnl_usd, t.r_multiple, t.exit_reason)
        for t in res.trades
    )


def determinism_check(bars: Sequence[Bar], *, seed: int = 20260731,
                      cost: CostModel | None = None) -> CheckResult:
    """Dwa przebiegi z tym samym ziarnem — wyniki bitowo identyczne."""
    cm = cost or CostModel()
    a = run(bars, RandomStrategy(seed=seed), cost=cm)
    b = run(bars, RandomStrategy(seed=seed), cost=cm)

    if not a.trades:
        return CheckResult(
            "determinizm", False,
            "brak transakcji — dwa puste przebiegi sa identyczne z definicji, "
            "wiec test nie ma mocy; potrzebna dluzsza seria",
            {"n_trades": 0},
        )

    zgodne = _odcisk(a) == _odcisk(b) and a.equity == b.equity
    inne_ziarno = run(bars, RandomStrategy(seed=seed + 1), cost=cm)
    ziarno_dziala = _odcisk(a) != _odcisk(inne_ziarno)

    zdany = zgodne and ziarno_dziala
    opis = (
        f"{len(a.trades)} transakcji, dwa przebiegi identyczne"
        if zgodne else "ROZJAZD miedzy przebiegami z tym samym ziarnem"
    )
    if not ziarno_dziala:
        opis += " — ale zmiana ziarna nic nie zmienia, wiec test nie ma mocy"
    return CheckResult("determinizm", zdany, opis, {"n_trades": len(a.trades)})


# --------------------------------------------------------------------------
# Uruchomienie kompletu
# --------------------------------------------------------------------------

def run_all(bars: Sequence[Bar], *, seed: int = 20260731,
            cost: CostModel | None = None, wymagaj_danych: bool = True) -> list[CheckResult]:
    """Komplet z rozdz. 5.6. `wymagaj_danych=False` pomija testy 1-2.

    ZANIM URUCHOMISZ JAKIEKOLWIEK BADANIE, komplet musi byc zielony na
    REALNYCH danych. Niesprawdzony silnik produkuje smiecie z dokladnoscia
    do szesciu miejsc po przecinku.
    """
    wyniki = [
        symmetry_check(bars, seed=seed, cost=cost),
        determinism_check(bars, seed=seed, cost=cost),
    ]
    if wymagaj_danych:
        wyniki = [
            zero_edge_check(bars, seed=seed, cost=cost),
            known_effect_check(bars, cost=cost),
            *wyniki,
        ]
    return wyniki


__all__ = [
    "PROG_SIGMA",
    "CheckResult",
    "RandomStrategy",
    "SessionBoundaryStrategy",
    "determinism_check",
    "known_effect_check",
    "mirror_bars",
    "overnight_intraday_split",
    "run_all",
    "symmetry_check",
    "zero_edge_check",
]
