"""Kalendarz CME Equity Index — swieta i dni skrocone.

Specyfikacja: PLAN.pdf rozdz. 4.2 (klasyfikacja luk: expected vs anomaly wg
JAWNEGO kalendarza sesji CME), rozdz. 4.6 (kalendarz sesji jako osobny
artefakt), rozdz. 3.2 (godziny handlu i dni skrocone). Poprawka A4-3 z audytu
4: brak bara nie jest defektem feedu, a rozroznienie wymaga kalendarza.

DLACZEGO TEN MODUL ISTNIEJE.
`SessionCalendar` przyjmowal swieta i dni skrocone jako argument, ale
`build_continuous` wolal go BEZ ARGUMENTOW. Skutek: `short_days` bylo puste,
a kolumna `short_day` wychodzila False dla wszystkich 2 551 265 barow zbioru.
Flaga istniala w schemacie i nic nie znaczyla.

ZRODLO PRAWDY — REGULA, NIE DANE.
Ponizsze reguly sa transkrypcja opublikowanego harmonogramu CME dla kontraktow
Equity Index. Dane rynkowe sluza WYLACZNIE do ich weryfikacji
(`tests/test_cme_calendar.py::TestZgodnoscZDanymi`), nigdy do wyprowadzania.

To rozroznienie jest istotne, nie kosmetyczne: mniejsza liczba barow moze
wynikac z defektu danych albo z braku transakcji w cienkim dniu. W zbiorze sa
dokladnie takie przypadki — 2020-02-28 (89 barow) i 2020-06-30 (41 barow) —
i oba sa DEFEKTAMI oznaczonymi w `degraded_days.json`, a nie dniami skroconymi.
Klasyfikator oparty na liczbie barow uznalby je za sesje skrocone.

DWA ROZNE ZAMKNIECIA.
Poprzednia wersja `SessionCalendar.close_time` zwracala stale 13:00 dla kazdego
dnia skroconego. To jest niepoprawne dla trzeciej czesci z nich:

  13:00 ET (12:00 CT) — sesja w SAM DZIEN swiateczny: MLK, Dzien Prezydentow,
                        Memorial Day, Juneteenth, 4 lipca, Labor Day,
                        Swieto Dziekczynienia.
  13:15 ET (12:15 CT) — dzien PRZYLEGAJACY do swieta: 3 lipca (gdy sam nie jest
                        swietem obserwowanym), piatek po Swiecie Dziekczynienia,
                        24 grudnia.

Roznica wynosi 15 minut sesji i zostala potwierdzona na wszystkich 66 dniach
skroconych w zbiorze 2019-2026.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

from engine.sessions import SessionCalendar

#: Zamkniecie w sam dzien swiateczny (12:00 CT).
CLOSE_1300 = dt.time(13, 0)
#: Zamkniecie w dzien przylegajacy do swieta (12:15 CT).
CLOSE_1315 = dt.time(13, 15)

#: Juneteenth stal sie swietem federalnym w czerwcu 2021; CME obserwuje je
#: od 2022. Potwierdzone w danych: 2021-06-18 jest sesja pelna.
JUNETEENTH_OD = 2022


def _nty_dzien_tygodnia(rok: int, miesiac: int, dzien_tyg: int, n: int) -> dt.date:
    """n-ty `dzien_tyg` (0 = poniedzialek) danego miesiaca."""
    d = dt.date(rok, miesiac, 1)
    d += dt.timedelta(days=(dzien_tyg - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def _ostatni_dzien_tygodnia(rok: int, miesiac: int, dzien_tyg: int) -> dt.date:
    """Ostatni `dzien_tyg` danego miesiaca."""
    d = (dt.date(rok, miesiac + 1, 1) if miesiac < 12 else dt.date(rok + 1, 1, 1))
    d -= dt.timedelta(days=1)
    return d - dt.timedelta(days=(d.weekday() - dzien_tyg) % 7)


def _obserwowane(d: dt.date) -> dt.date:
    """Swieto w sobote -> piatek; w niedziele -> poniedzialek."""
    if d.weekday() == 5:
        return d - dt.timedelta(days=1)
    if d.weekday() == 6:
        return d + dt.timedelta(days=1)
    return d


def independence_observed(rok: int) -> dt.date:
    """Obserwowany Dzien Niepodleglosci.

    To jest sedno zgloszonego defektu: 4 lipca 2026 wypada w SOBOTE, wiec
    swieto obserwowane jest w piatek 3 lipca. Tego dnia sesja jest swiateczna
    (13:00), a NIE przeddniem swieta (13:15) — i dlatego 2026-07-03 ma
    210 barow RTH, a nie 225 jak 2025-07-03.
    """
    return _obserwowane(dt.date(rok, 7, 4))


def good_friday(rok: int) -> dt.date:
    """Wielki Piatek — algorytm Meeusa/Jonesa/Butchera (Wielkanoc gregorianska)."""
    a, b, c = rok % 19, rok // 100, rok % 100
    d, e = b // 4, b % 4
    g = (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    ll = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ll) // 451
    miesiac = (h + ll - 7 * m + 114) // 31
    dzien = ((h + ll - 7 * m + 114) % 31) + 1
    return dt.date(rok, miesiac, dzien) - dt.timedelta(days=2)


#: Jednorazowe zamkniecia spoza cyklu rocznego. Bez tej tablicy zaden
#: algorytm kalendarzowy ich nie odtworzy.
ZAMKNIECIA_JEDNORAZOWE: frozenset[dt.date] = frozenset({
    # Ogolnokrajowy dzien zaloby po pogrzebie prezydenta Cartera.
    dt.date(2025, 1, 9),
})


def _nowy_rok(rok: int) -> dt.date:
    """Nowy Rok — obserwacja WYLACZNIE w przod (niedziela -> poniedzialek).

    Swieto w sobote przenosi sie zwykle na poprzedzajacy piatek, ale dla
    Nowego Roku ten piatek nalezy do POPRZEDNIEGO roku i rynek go nie zamyka.
    Potwierdzone w danych: 1 stycznia 2022 wypadl w sobote, a 2021-12-31 mial
    pelna sesje RTH. Pierwotna wersja tej funkcji uzywala reguly symetrycznej
    i blednie oznaczala 2021-12-31 jako swieto — zlapal to test zgodnosci
    z danymi, nie przeglad kodu.
    """
    d = dt.date(rok, 1, 1)
    return d + dt.timedelta(days=1) if d.weekday() == 6 else d


def _swieta_roku(rok: int) -> set[dt.date]:
    """Dni BEZ sesji RTH."""
    return {
        _nowy_rok(rok),
        good_friday(rok),                       # Wielki Piatek
        _obserwowane(dt.date(rok, 12, 25)),     # Boze Narodzenie
    } | {d for d in ZAMKNIECIA_JEDNORAZOWE if d.year == rok}


def _skrocone_roku(rok: int) -> dict[dt.date, dt.time]:
    """Dni skrocone z przypisanym RZECZYWISTYM czasem zamkniecia."""
    swieta = _swieta_roku(rok)
    dziekczynienie = _nty_dzien_tygodnia(rok, 11, 3, 4)      # 4. czwartek listopada
    lipiec = independence_observed(rok)

    out: dict[dt.date, dt.time] = {
        _nty_dzien_tygodnia(rok, 1, 0, 3): CLOSE_1300,       # MLK
        _nty_dzien_tygodnia(rok, 2, 0, 3): CLOSE_1300,       # Dzien Prezydentow
        _ostatni_dzien_tygodnia(rok, 5, 0): CLOSE_1300,      # Memorial Day
        lipiec: CLOSE_1300,                                  # Dzien Niepodleglosci
        _nty_dzien_tygodnia(rok, 9, 0, 1): CLOSE_1300,       # Labor Day
        dziekczynienie: CLOSE_1300,
        dziekczynienie + dt.timedelta(days=1): CLOSE_1315,   # piatek po
    }
    if rok >= JUNETEENTH_OD:
        out[_obserwowane(dt.date(rok, 6, 19))] = CLOSE_1300

    # 3 lipca zamyka sie o 13:15 TYLKO wtedy, gdy jest odrebnym dniem
    # handlowym, a nie samym swietem obserwowanym (przypadek 2020 i 2026).
    trzeci = dt.date(rok, 7, 3)
    if trzeci.weekday() < 5 and trzeci != lipiec:
        out[trzeci] = CLOSE_1315

    wigilia = dt.date(rok, 12, 24)
    if wigilia.weekday() < 5:
        out[wigilia] = CLOSE_1315

    # Dzien skrocony musi byc dniem handlowym.
    return {d: t for d, t in out.items() if d.weekday() < 5 and d not in swieta}


@lru_cache(maxsize=32)
def cme_calendar(rok_od: int, rok_do: int) -> SessionCalendar:
    """Kalendarz CME Equity Index dla zakresu lat (wlacznie)."""
    swieta: set[dt.date] = set()
    skrocone: dict[dt.date, dt.time] = {}
    for r in range(rok_od, rok_do + 1):
        swieta |= _swieta_roku(r)
        skrocone |= _skrocone_roku(r)
    return SessionCalendar(
        holidays=frozenset(swieta),
        short_days=frozenset(skrocone),
        early_closes=frozenset(skrocone.items()),
    )
