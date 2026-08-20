"""Segmentacja doby handlowej MNQ.

Specyfikacja: PLAN.pdf rozdz. 3.3 (anatomia doby), 4.4 (strefy czasowe), 4.6 (kalendarz).

Zasady nienaruszalne:
  * Dane przechowujemy w UTC, sesje definiujemy w ET (America/New_York).
    Otwarcie RTH to ZAWSZE 9:30 ET — w UTC to 13:30 albo 14:30 zaleznie od pory roku.
    Definicja w UTC rozjezdza wszystkie statystyki otwarcia dwa razy w roku.
  * Dzien sesyjny (`trade_date`) zaczyna sie o 18:00 ET dnia POPRZEDNIEGO.
    Sesja nocna "poniedzialkowa" zaczyna sie w niedziele wieczorem.
  * Kalendarz CME (swieta, dni skrocone, historyczny halt) jest osobnym,
    jawnym artefaktem — nie wnioskujemy go z danych.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
CT = ZoneInfo("America/Chicago")
UTC = ZoneInfo("UTC")

# Kolejnosc ma znaczenie: segmenty sa rozlaczne i pokrywaja cala dobe handlowa.
SEGMENTS = (
    "globex_open",   # 18:00-19:00 ET — reakcja na wyniki spolek po zamknieciu
    "asia",          # 19:00-02:00 ET — najnizsza plynnosc doby
    "europe",        # 02:00-08:30 ET — plynnosc rosnie od otwarcia Frankfurtu
    "premarket",     # 08:30-09:30 ET — publikacje makro uderzaja przed sesja kasowa
    "rth_open",      # 09:30-10:30 ET — najwyzsza zmiennosc i wolumen doby
    "midday",        # 10:30-13:30 ET — obejmuje dolek lunchowy 11:30-13:30
    "afternoon",     # 13:30-15:00 ET
    "close",         # 15:00-16:00 ET — drugi szczyt wolumenu, imbalance MOC od 15:50
    "after_hours",   # 16:00-17:00 ET — wyniki spolek, plynnosc ucieka
    "maintenance",   # 17:00-18:00 ET — przerwa serwisowa CME
)

# Granice segmentow w czasie ET jako (godzina, minuta).
_BOUNDS: tuple[tuple[time, str], ...] = (
    (time(18, 0), "globex_open"),
    (time(19, 0), "asia"),
    (time(2, 0), "europe"),
    (time(8, 30), "premarket"),
    (time(9, 30), "rth_open"),
    (time(10, 30), "midday"),
    (time(13, 30), "afternoon"),
    (time(15, 0), "close"),
    (time(16, 0), "after_hours"),
    (time(17, 0), "maintenance"),
)

RTH_OPEN = time(9, 30)
RTH_CLOSE = time(16, 0)
SESSION_START = time(18, 0)   # start dnia sesyjnego (Globex open)
MAINT_START = time(17, 0)
MAINT_END = time(18, 0)

# Historyczny halt 15:15-15:30 CT, zniesiony 2021-06-27 (PLAN rozdz. 4.6).
# W CT, bo tak definiuje go CME — konwersja do ET daje 16:15-16:30.
HALT_ABOLISHED = date(2021, 6, 27)
_HALT_START_CT = time(15, 15)
_HALT_END_CT = time(15, 30)


@dataclass(frozen=True)
class SessionCalendar:
    """Jawny kalendarz CME. Zrodlo prawdy dla klasyfikacji luk (rozdz. 4.2).

    holidays      — dni bez sesji
    short_days    — dni skrocone (zamkniecie wczesniejsze niz 16:00 ET)
    early_closes  — rzeczywisty czas zamkniecia dnia skroconego

    DWA ROZNE ZAMKNIECIA. Wczesniejsza wersja zwracala stale 13:00 dla kazdego
    dnia skroconego. CME zamyka o 13:00 ET w sam dzien swiateczny, ale o 13:15
    w dzien przylegajacy do swieta (3 lipca, piatek po Swiecie Dziekczynienia,
    24 grudnia). Roznica to 15 minut sesji. `early_closes` pozwala podac
    faktyczny czas; `short_days` bez wpisu zachowuje domyslne 13:00, zeby stare
    wywolania nie zmienily znaczenia.
    """

    holidays: frozenset[date] = frozenset()
    short_days: frozenset[date] = frozenset()
    early_closes: frozenset[tuple[date, time]] = frozenset()

    def is_trading_day(self, d: date) -> bool:
        # Sobota nie ma sesji; niedziela ma tylko wieczorny start Globexu,
        # ktory nalezy juz do poniedzialkowego dnia sesyjnego.
        return d.weekday() < 5 and d not in self.holidays

    def close_time(self, d: date) -> time:
        if not self.short_days:
            return RTH_CLOSE
        wpis = dict(self.early_closes).get(d)
        if wpis is not None:
            return wpis
        return time(13, 0) if d in self.short_days else RTH_CLOSE


def to_et(ts_utc: datetime) -> datetime:
    """Konwersja UTC -> ET z pelna obsluga zmian czasu."""
    if ts_utc.tzinfo is None:
        ts_utc = ts_utc.replace(tzinfo=UTC)
    return ts_utc.astimezone(ET)


def segment_of(ts: datetime) -> str:
    """Segment doby dla znacznika czasu (UTC lub ET — konwersja automatyczna)."""
    et = to_et(ts)
    t = et.time()

    if t >= time(18, 0):
        return "globex_open" if t < time(19, 0) else "asia"
    if t < time(2, 0):
        return "asia"
    if t < time(8, 30):
        return "europe"
    if t < time(9, 30):
        return "premarket"
    if t < time(10, 30):
        return "rth_open"
    if t < time(13, 30):
        return "midday"
    if t < time(15, 0):
        return "afternoon"
    if t < time(16, 0):
        return "close"
    if t < time(17, 0):
        return "after_hours"
    return "maintenance"


def trade_date(ts: datetime) -> date:
    """Dzien sesyjny: zaczyna sie o 18:00 ET dnia poprzedniego.

    Barek o 20:00 ET w niedziele nalezy do poniedzialkowego dnia sesyjnego.
    Cala agregacja dzienna w projekcie dziala na tej funkcji, nie na dacie UTC.
    """
    et = to_et(ts)
    d = et.date()
    if et.time() >= SESSION_START:
        d = d + timedelta(days=1)
        # Piatek 18:00+ nie istnieje (rynek zamkniety do niedzieli 18:00),
        # ale niedziela 18:00+ -> poniedzialek.
        while d.weekday() >= 5:
            d = d + timedelta(days=1)
    return d


def is_rth(ts: datetime, calendar: SessionCalendar | None = None) -> bool:
    """Czy znacznik nalezy do sesji kasowej (RTH)."""
    et = to_et(ts)
    cal = calendar or SessionCalendar()
    return RTH_OPEN <= et.time() < cal.close_time(et.date())


def in_maintenance(ts: datetime) -> bool:
    """Codzienna przerwa serwisowa CME: 17:00-18:00 ET."""
    return MAINT_START <= to_et(ts).time() < MAINT_END


def in_historical_halt(ts: datetime) -> bool:
    """Halt 15:15-15:30 CT, obowiazujacy do 2021-06-27 wlacznie.

    Wystepuje w naszym oknie danych (2019-2021), wiec musi byc obslugiwany —
    inaczej sanity-report zglosi go jako anomalie, a analizy segmentu
    popoludniowego dla tamtych lat beda skazone.
    """
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)
    ct = ts.astimezone(CT)
    if ct.date() >= HALT_ABOLISHED:
        return False
    return _HALT_START_CT <= ct.time() < _HALT_END_CT


def is_expected_gap(ts_from: datetime, ts_to: datetime,
                    calendar: SessionCalendar | None = None) -> bool:
    """Czy przerwa miedzy barami jest oczekiwana, czy to anomalia (rozdz. 4.2).

    KLUCZOWE: Databento nie drukuje bara, gdy w danym interwale nie bylo
    transakcji ("If no trade occurs within the interval, no record is printed").
    Brak bara jest poprawnym opisem rynku, nie defektem feedu.

    Zwraca True dla: przerwy serwisowej, weekendu, swieta, dnia skroconego,
    historycznego haltu. Wszystko inne -> anomalia do przejrzenia.
    """
    cal = calendar or SessionCalendar()

    # Luka jednominutowa nie jest luka.
    if (ts_to - ts_from) <= timedelta(minutes=1):
        return True

    # Luka to przedzial MIEDZY barami: minuta `ts_from` ma dane, wiec nie nalezy
    # do luki. Rozpoczecie obchodu od `ts_from` zglaszaloby jako niepokryta
    # minute, ktora jest pokryta z definicji — a to oznaczaloby falszywa
    # anomalie na KAZDYM weekendzie (ostatni bar piatku lezy przed 17:00 ET).
    cur = ts_from + timedelta(minutes=1)
    step = timedelta(minutes=1)
    while cur < ts_to:
        et = to_et(cur)
        covered = (
            in_maintenance(cur)
            or in_historical_halt(cur)
            or not cal.is_trading_day(trade_date(cur))
            or (et.weekday() == 4 and et.time() >= MAINT_START)   # piatek po zamknieciu
            or (et.weekday() == 5)                                 # sobota
            or (et.weekday() == 6 and et.time() < SESSION_START)   # niedziela do 18:00
            or (et.date() in cal.short_days
                and et.time() >= cal.close_time(et.date()))
        )
        if not covered:
            return False
        cur += step
    return True
