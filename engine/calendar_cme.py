"""Kalendarz sesyjny CME dla kontraktow indeksowych — PLAN.pdf rozdz. 4.2, 4.4.

Dokument stanowi jasno: kalendarz jest OSOBNYM, WERSJONOWANYM ARTEFAKTEM, a nie
wnioskiem z danych. Wnioskowanie swiat z braku barow jest bledem cyrkularnym:
kalendarz sluzy do klasyfikacji luk, wiec nie moze z luk powstawac — inaczej
kazda awaria feedu zostalaby uznana za swieto i zniknelaby z raportu jakosci.

KLUCZOWE ROZROZNIENIE — CME NIE JEST NYSE:
    W wiekszosc swiat federalnych, w ktore gielda kasowa jest zamknieta
    (Memorial Day, Labor Day, Dzien Dziekczynienia, MLK, Presidents' Day,
    Juneteenth, 4 lipca), kontrakty na indeksy akcyjne NA GLOBEXIE HANDLUJA
    SIE — z wczesnym zamknieciem o 12:00 CT (13:00 ET). Sa to wiec dla nas
    DNI SKROCONE, nie dni bez sesji.

    Pelnym zamknieciem sa tylko: Wielki Piatek, Boze Narodzenie i Nowy Rok.

    Pomylka w te strone jest kosztowna: oznaczenie Memorial Day jako dnia bez
    sesji kazaloby sanity-reportowi uznac cala luke 13:00-17:00 ET za
    oczekiwana i przy okazji przemilczec kazda prawdziwa anomalie tego dnia.

WERYFIKACJA (wymog przed pierwszym badaniem):
    Ten modul GENERUJE kalendarz z regul, zamiast go przepisywac. Reguly sa
    stabilne od dekad, ale gielda ma prawo zamknac rynek doraznie — pogrzeb
    panstwowy, huragan Sandy w 2012, 11 wrzesnia. Takich dni zadna regula nie
    przewidzi, dlatego lista `DORAZNE_ZAMKNIECIA` jest jawna i uzupelniana
    recznie, a `SessionCalendar.verified` pozostaje False do czasu porownania
    z opublikowanym kalendarzem CME (procedura: sanity-report, rozdz. 4.6).
"""

from __future__ import annotations

from datetime import date, timedelta

from engine.sessions import SessionCalendar

# Doraznie odwolane sesje — zdarzenia, ktorych reguly nie opisuja.
# W oknie danych projektu (od 2019-04-14) wystapil jeden taki dzien.
DORAZNE_ZAMKNIECIA: frozenset[date] = frozenset({
    date(2018, 12, 5),   # zaloba narodowa po smierci George'a H. W. Busha
})

# Juneteenth stal sie swietem gieldowym dopiero w 2022 — wczesniej byl dniem
# handlowym. Pomylka w tej dacie zamienia trzy zwykle sesje w "anomalie".
JUNETEENTH_OD = 2022


def easter(year: int) -> date:
    """Niedziela Wielkanocna wg algorytmu anonimowego gregorianskiego.

    Potrzebna wylacznie po to, zeby wyznaczyc Wielki Piatek — jedyne ruchome
    swieto w kalendarzu gieldowym.
    """
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    lam = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * lam) // 451
    month, day = divmod(h + lam - 7 * m + 114, 31)
    return date(year, month, day + 1)


def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """n-ty dzien tygodnia w miesiacu (weekday: 0 = poniedzialek)."""
    d = date(year, month, 1)
    przesuniecie = (weekday - d.weekday()) % 7
    return d + timedelta(days=przesuniecie + 7 * (n - 1))


def last_weekday(year: int, month: int, weekday: int) -> date:
    """Ostatni dzien tygodnia w miesiacu — Memorial Day to ostatni poniedzialek maja."""
    d = date(year, month, 28)
    while (d + timedelta(days=1)).month == month:
        d += timedelta(days=1)
    return d - timedelta(days=(d.weekday() - weekday) % 7)


def observed(d: date) -> date | None:
    """Dzien obchodzenia swiata o stalej dacie.

    Sobota -> piatek poprzedzajacy, niedziela -> poniedzialek nastepujacy.
    Zwraca None, gdy przesuniecie wyprowadza poza rok — przypadek 1 stycznia
    wypadajacego w sobote, ktorego gielda nie obchodzi wcale.
    """
    if d.weekday() == 5:
        przesuniety = d - timedelta(days=1)
        return None if przesuniety.year != d.year else przesuniety
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def federal_holidays(year: int) -> set[date]:
    """Swieta gieldy kasowej — dni, w ktorych NYSE nie handluje.

    Dla nas nie sa to dni bez sesji: kontrakty indeksowe na Globexie handluja
    sie w wiekszosci z nich do 12:00 CT. Funkcja sluzy jako wspolna podstawa
    dla `holidays` (pelne zamkniecia) i `short_days` (wczesne zamkniecia).
    """
    out: set[date] = set()

    nowy_rok = observed(date(year, 1, 1))
    if nowy_rok:
        out.add(nowy_rok)
    # 1 stycznia w niedziele przenosi sie na 2 stycznia; 1 stycznia w sobote
    # nie jest obchodzony wcale — gielda po prostu pracuje 31 grudnia i 2 stycznia.

    out.add(nth_weekday(year, 1, 0, 3))          # Martin Luther King Jr. Day
    out.add(nth_weekday(year, 2, 0, 3))          # Washington's Birthday
    out.add(easter(year) - timedelta(days=2))    # Wielki Piatek
    out.add(last_weekday(year, 5, 0))            # Memorial Day

    if year >= JUNETEENTH_OD:
        juneteenth = observed(date(year, 6, 19))
        if juneteenth:
            out.add(juneteenth)

    swieto_niepodleglosci = observed(date(year, 7, 4))
    if swieto_niepodleglosci:
        out.add(swieto_niepodleglosci)

    out.add(nth_weekday(year, 9, 0, 1))          # Labor Day
    out.add(nth_weekday(year, 11, 3, 4))         # Thanksgiving (4. czwartek)

    boze_narodzenie = observed(date(year, 12, 25))
    if boze_narodzenie:
        out.add(boze_narodzenie)

    return out


def holidays(year: int) -> set[date]:
    """PELNE zamkniecia Globexu dla kontraktow indeksowych.

    Wielki Piatek, Boze Narodzenie i Nowy Rok. Reszta swiat federalnych to dni
    skrocone — patrz `short_days` i naglowek modulu.

    Wyjatek udokumentowany: 3 kwietnia 2026 (Wielki Piatek) zbiegl sie
    z publikacja NFP i produkty indeksowe mialy skrocona sesje poranna. Dzien
    zostaje tu jako zamkniety: klasyfikator luk nie zglasza barow obecnych
    w dniu bez sesji, a sanity-report i tak wypisze osobno kazdy dzien
    oznaczony jako zamkniety, w ktorym dane zawieraja bary.
    """
    out = {
        easter(year) - timedelta(days=2),        # Wielki Piatek
    }
    nowy_rok = observed(date(year, 1, 1))
    if nowy_rok:
        out.add(nowy_rok)
    boze_narodzenie = observed(date(year, 12, 25))
    if boze_narodzenie:
        out.add(boze_narodzenie)

    out |= {d for d in DORAZNE_ZAMKNIECIA if d.year == year}
    return out


def short_days(year: int) -> set[date]:
    """Dni skrocone — sesja konczy sie o 13:00 ET zamiast 16:00.

    Dwie rodziny: swieta federalne, w ktore Globex handluje do 12:00 CT, oraz
    klasyczne polowki dnia (dzien po Swiecie Dziekczynienia, dzien przed
    4 lipca, Wigilia).

    Wykluczamy te dni z analiz segmentu zamkniecia: godzina 15:00-16:00 ET, na
    ktorej opiera sie caly segment `close`, w tych dniach po prostu nie istnieje.
    """
    pelne = holidays(year)
    out: set[date] = federal_holidays(year) - pelne

    # Dzien po Swiecie Dziekczynienia.
    out.add(nth_weekday(year, 11, 3, 4) + timedelta(days=1))

    # Dzien poprzedzajacy Swieto Niepodleglosci, o ile sam jest dniem handlowym.
    dzien_wczesniej = date(year, 7, 4) - timedelta(days=1)
    if dzien_wczesniej.weekday() < 5:
        out.add(dzien_wczesniej)

    # Wigilia — tylko gdy wypada w dzien roboczy.
    wigilia = date(year, 12, 24)
    if wigilia.weekday() < 5:
        out.add(wigilia)

    return {d for d in out if d.weekday() < 5 and d not in pelne}


def build_calendar(start_year: int, end_year: int) -> SessionCalendar:
    """Kalendarz dla zakresu lat wlacznie — wejscie do klasyfikacji luk."""
    if end_year < start_year:
        raise ValueError("end_year musi byc >= start_year")
    h: set[date] = set()
    s: set[date] = set()
    for y in range(start_year, end_year + 1):
        h |= holidays(y)
        s |= short_days(y)
    return SessionCalendar(holidays=frozenset(h), short_days=frozenset(s))


# Kalendarz okna danych projektu: od startu produktu MNQ z zapasem w przod.
PROJECT_CALENDAR = build_calendar(2019, 2030)
