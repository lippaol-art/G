"""Benchmarki B01-B04 — PLAN.pdf rozdz. 8.4 (test oryginalnosci, krok 1 i 3).

CO TO JEST I CZYM NIE JEST.

To NIE sa kandydaci na strategie. To grupa kontrolna. Kazda przyszla karta
hipotezy musi wykazac przyrost PONAD najblizszy jej benchmark (krok 3 testu
oryginalnosci) — bez tej linii odniesienia "nasza regula zarabia" nie znaczy
nic, bo nie wiadomo, czy zarabia cokolwiek ponad publicznie znany setup.

DLATEGO NIE WOLNO ICH OPTYMALIZOWAC. Parametry pochodza wprost z literatury
i sa wpisane jako stale z podanym zrodlem. Kazde "podkrecenie" zamienia
benchmark w slabego konkurenta i zaniza poprzeczke dla kart wlasnych —
dokladnie odwrotnie, niz chcemy. Z tego samego powodu benchmarki NIE ZUZYWAJA
globalnego licznika prob: nie sa proba znalezienia przewagi.

OGRANICZENIE WSPOLNE DLA WSZYSTKICH CZTERECH. Silnik wykonuje zlecenie po
otwarciu bara NASTEPNEGO po sygnale (zasada 2 z rozdz. 5.1). Literatura mowi
zwykle "wejscie po cenie otwarcia sesji"; my wchodzimy minute pozniej. Nie jest
to niedokladnosc do naprawienia, tylko uczciwa cena zakazu lookaheadu — ta sama
dla benchmarkow i dla kart wlasnych, wiec porownanie miedzy nimi pozostaje
sprawiedliwe.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import time

from engine.backtest import Bar, Order
from engine.sessions import to_et

# Segmenty skladajace sie na sesje kasowa (RTH).
RTH = ("rth_open", "midday", "afternoon", "close")


def _et_time(bar: Bar) -> time:
    return to_et(bar.ts).time()


class _DzienRTH:
    """Akumulator statystyk sesji kasowej, budowany bar po barze.

    Nie ma tu ani jednego odwolania do przyszlosci: statystyki dnia D staja sie
    dostepne dopiero wtedy, gdy strategia zobaczy pierwszy bar dnia D+1. Ta
    konstrukcja jest celowo niewygodna — wygodna wersja (tabela dzienna liczona
    z gory) roznilaby sie tylko tym, ze pozwalalaby sie pomylic.
    """

    def __init__(self) -> None:
        self.td: object = None
        self.o = self.h = self.lo = self.c = 0.0
        self.zamkniete: list[dict] = []      # dni ZAKONCZONE, w kolejnosci

    def obserwuj(self, bar: Bar) -> bool:
        """Zwraca True, jesli to pierwszy bar RTH nowego dnia sesyjnego."""
        if bar.segment not in RTH:
            return False
        nowy = bar.trade_date != self.td
        if nowy:
            if self.td is not None:
                self.zamkniete.append(
                    dict(td=self.td, open=self.o, high=self.h, low=self.lo, close=self.c)
                )
            self.td = bar.trade_date
            self.o, self.h, self.lo, self.c = bar.open, bar.high, bar.low, bar.close
        else:
            self.h = max(self.h, bar.high)
            self.lo = min(self.lo, bar.low)
            self.c = bar.close
        return nowy

    @property
    def wczoraj(self) -> dict | None:
        return self.zamkniete[-1] if self.zamkniete else None


# --------------------------------------------------------------------------
# B01 — domykanie luki otwarcia
# --------------------------------------------------------------------------

class B01GapFill:
    """Fade luki otwarcia RTH z celem na wczorajszym zamknieciu.

    Zrodlo reguly: klasyka indeksowa, wersja kanoniczna sprowadza sie do trzech
    zdan — jesli sesja otwiera sie luka wzgledem wczorajszego zamkniecia RTH,
    zajmij pozycje PRZECIW luce, celuj we wczorajsze zamkniecie, wyjdz na
    zamknieciu sesji, jesli cel nie zostal osiagniety.

    Parametry z literatury, NIE dobierane:
      * prog luki: 0.10% ceny — odsiewa szum otwarcia, nie selekcjonuje sygnalu;
      * cel: dokladnie wczorajsze zamkniecie RTH (definicja "domkniecia luki");
      * stop: rozmiar luki odlozony po drugiej stronie wejscia (symetryczny 1:1);
      * wyjscie czasowe: zamkniecie sesji.
    """

    PROG_LUKI_PCT = 0.0010

    def __init__(self) -> None:
        self.dzien = _DzienRTH()

    def on_bar(self, bar: Bar, history, state) -> list[Order]:
        pierwszy = self.dzien.obserwuj(bar)
        if not pierwszy or state.get("position_side") is not None:
            return []
        wczoraj = self.dzien.wczoraj
        if wczoraj is None:
            return []

        luka = bar.open - wczoraj["close"]
        if abs(luka) < self.PROG_LUKI_PCT * bar.open:
            return []

        cel = wczoraj["close"]
        if luka > 0:                                   # luka w gore -> short
            return [Order(side="short", sl=bar.open + abs(luka), tp=cel, tag="B01")]
        return [Order(side="long", sl=bar.open - abs(luka), tp=cel, tag="B01")]


# --------------------------------------------------------------------------
# B02 — cykl kontrakcja-ekspansja (NR7)
# --------------------------------------------------------------------------

class B02NR7:
    """Wybicie z dnia o najwezszym zakresie z ostatnich siedmiu.

    Zrodlo: Toby Crabel, "Day Trading with Short Term Price Patterns" (~1990) —
    NR7 i wybicie zakresu dnia poprzedniego. Regula kanoniczna: po dniu, ktorego
    zakres jest najwezszy z siedmiu, zloz zlecenia stop po obu stronach zakresu
    tego dnia; strona wyzwolona wchodzi, druga jest kasowana; stop po
    przeciwnej stronie zakresu; wyjscie na zamknieciu sesji.

    To jedyny benchmark wymagajacy zlecen OCZEKUJACYCH — udawanie wybicia
    zleceniem rynkowym po fakcie dawaloby inna cene i inny moment.
    """

    OKNO = 7

    def __init__(self) -> None:
        self.dzien = _DzienRTH()

    def on_bar(self, bar: Bar, history, state) -> list[Order]:
        pierwszy = self.dzien.obserwuj(bar)
        if not pierwszy or state.get("position_side") is not None:
            return []

        dni = self.dzien.zamkniete
        if len(dni) < self.OKNO:
            return []

        okno = dni[-self.OKNO:]
        zakresy = [d["high"] - d["low"] for d in okno]
        wczoraj = okno[-1]
        if zakresy[-1] > min(zakresy):
            return []                                  # wczoraj nie byl NR7

        gora, dol = wczoraj["high"], wczoraj["low"]
        if gora <= dol:
            return []
        return [
            Order(side="long", kind="stop", px=gora, sl=dol, tag="B02", oco_group="B02"),
            Order(side="short", kind="stop", px=dol, sl=gora, tag="B02", oco_group="B02"),
        ]


# --------------------------------------------------------------------------
# B03 — efekt weekendu
# --------------------------------------------------------------------------

class B03Weekend:
    """Krotka pozycja przez weekend: piatek na zamknieciu -> poniedzialek.

    Zrodlo: Cross (1973), French (1980) — zwroty poniedzialkowe istotnie ujemne,
    piatkowe dodatnie. Kanoniczna postac handlowa tego efektu to wlasnie krotka
    pozycja trzymana przez weekend.

    Karta jest w katalogu jako benchmark, nie kandydat, bo efekt uwaza sie za
    wygasly po 1987 r. Uruchamiamy ja mimo to: jesli jakas przyszla karta bedzie
    warunkowac cokolwiek dniem tygodnia, musi pokazac przyrost ponad TE liczbe.
    """

    PIATEK = 4

    def __init__(self) -> None:
        self.ostatni_td: object = None

    def on_bar(self, bar: Bar, history, state) -> list[Order]:
        if bar.segment != "close" or state.get("position_side") is not None:
            return []
        # Wejscie w ostatnim kwadransie sesji piatkowej — na tyle blisko
        # zamkniecia, ze cena odpowiada zamknieciu, i bez zgadywania, ktory
        # bar bedzie ostatni (tego bez lookaheadu wiedziec nie mozna).
        if _et_time(bar) < time(15, 45):
            return []
        td = bar.trade_date
        if td == self.ostatni_td or getattr(td, "weekday", lambda: -1)() != self.PIATEK:
            return []
        self.ostatni_td = td
        return [Order(side="short", sl=None, tag="B03")]


# --------------------------------------------------------------------------
# B04 — momentum wewnatrzdzienne
# --------------------------------------------------------------------------

class B04IntradayMomentum:
    """Ostatnie pol godziny podaza za pierwszym pol godziny.

    Zrodlo: Gao, Han, Li, Zhou, "Market intraday momentum", Journal of Financial
    Economics 129(2), 2018. Regula z pracy, bez zmian: policz zwrot pierwszego
    polgodzinnego odcinka sesji (09:30-10:00 ET); na poczatku ostatniego odcinka
    (15:30 ET) zajmij pozycje ZGODNA z jego znakiem; zamknij na zamknieciu sesji.

    Praca raportuje efekt na SPY; MNQ jest innym instrumentem, wiec brak wyniku
    nie falsyfikuje pracy. Nas interesuje wylacznie linia odniesienia dla kart
    warunkujacych cokolwiek na porze dnia.
    """

    def __init__(self) -> None:
        self.td: object = None
        self.px_0930: float | None = None
        self.r_pierwsze_30: float | None = None
        self.wyslane = False

    def on_bar(self, bar: Bar, history, state) -> list[Order]:
        if bar.trade_date != self.td:
            self.td = bar.trade_date
            self.px_0930 = None
            self.r_pierwsze_30 = None
            self.wyslane = False

        t = _et_time(bar)
        if bar.segment not in RTH:
            return []

        if self.px_0930 is None:
            self.px_0930 = bar.open                    # pierwszy bar sesji kasowej
            return []

        # Domkniecie pierwszego polgodzinnego odcinka.
        if self.r_pierwsze_30 is None and t >= time(10, 0):
            self.r_pierwsze_30 = bar.open / self.px_0930 - 1.0
            return []

        # Sygnal na barze 15:29 -> wypelnienie po otwarciu 15:30 (zasada 2).
        if (self.r_pierwsze_30 is not None and not self.wyslane
                and time(15, 29) <= t < time(15, 30)
                and state.get("position_side") is None):
            self.wyslane = True
            if self.r_pierwsze_30 == 0.0:
                return []
            strona = "long" if self.r_pierwsze_30 > 0 else "short"
            return [Order(side=strona, sl=None, tag="B04")]
        return []


# --------------------------------------------------------------------------
# Wyjscia czasowe — wspolne dla B01, B02, B04
# --------------------------------------------------------------------------

def flat_na_zamknieciu_sesji() -> Callable[[Bar, object], bool]:
    """Przymusowe zamkniecie na pierwszym barze po sesji kasowej (rozdz. 5.4)."""
    return lambda bar, pos: bar.segment == "after_hours"


def flat_w_nastepnej_sesji() -> Callable[[Bar, object], bool]:
    """Wyjscie B03: pierwszy bar zamkniecia NASTEPNEGO dnia sesyjnego."""
    def _f(bar: Bar, pos) -> bool:
        return (bar.segment == "close"
                and _et_time(bar) >= time(15, 45)
                and bar.trade_date != pos.entry_trade_date)
    return _f


BENCHMARKI = {
    "B01": ("Domykanie luki otwarcia", B01GapFill, flat_na_zamknieciu_sesji),
    "B02": ("Wybicie po NR7 (Crabel ~1990)", B02NR7, flat_na_zamknieciu_sesji),
    "B03": ("Efekt weekendu (Cross 1973 / French 1980)", B03Weekend, flat_w_nastepnej_sesji),
    "B04": ("Momentum wewnatrzdzienne (Gao i in. JFE 2018)", B04IntradayMomentum,
            flat_na_zamknieciu_sesji),
}
