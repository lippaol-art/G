"""Testy kalendarza CME — PLAN.pdf rozdz. 4.2, 4.4.

Kalendarz jest generowany z regul, wiec testy sprawdzaja go na DATACH ZNANYCH
NIEZALEZNIE (Wielki Piatek, przenoszenie swiat wypadajacych w weekend, rok
wprowadzenia Juneteenth). Blad w tym module nie objawia sie jako awaria, tylko
jako cicho przemilczana anomalia w danych albo lawina falszywych alarmow.
"""

from __future__ import annotations

from datetime import date

from engine.calendar_cme import (
    build_calendar,
    easter,
    federal_holidays,
    holidays,
    last_weekday,
    nth_weekday,
    observed,
    short_days,
)


def test_wielkanoc_znane_daty():
    assert easter(2019) == date(2019, 4, 21)
    assert easter(2021) == date(2021, 4, 4)
    assert easter(2024) == date(2024, 3, 31)
    assert easter(2026) == date(2026, 4, 5)


def test_wielki_piatek_jest_pelnym_zamknieciem():
    assert date(2024, 3, 29) in holidays(2024)
    assert date(2026, 4, 3) in holidays(2026)
    assert date(2024, 3, 29) not in short_days(2024)


def test_swieta_federalne_to_dni_skrocone_a_nie_zamkniete():
    """Na Globexie kontrakty indeksowe handluja sie w te dni do 12:00 CT."""
    memorial_2024 = date(2024, 5, 27)
    labor_2024 = date(2024, 9, 2)
    thanksgiving_2024 = date(2024, 11, 28)

    for d in (memorial_2024, labor_2024, thanksgiving_2024):
        assert d in federal_holidays(2024)
        assert d in short_days(2024), "Globex handluje w to swieto do 12:00 CT"
        assert d not in holidays(2024), "to nie jest dzien bez sesji"


def test_pelne_zamkniecia_to_tylko_trzy_swieta():
    assert holidays(2024) == {date(2024, 1, 1), date(2024, 3, 29), date(2024, 12, 25)}


def test_przeniesienie_swiat_wypadajacych_w_weekend():
    # 1 stycznia 2022 to sobota — gielda nie obchodzi go wcale.
    assert not any(d.month == 1 for d in holidays(2022))
    # Boze Narodzenie 2022 wypada w niedziele -> poniedzialek 26 grudnia.
    assert date(2022, 12, 26) in holidays(2022)
    # Boze Narodzenie 2021 wypada w sobote -> piatek 24 grudnia.
    assert date(2021, 12, 24) in holidays(2021)
    assert date(2021, 12, 24) not in short_days(2021), "dzien zamkniety nie jest skrocony"


def test_juneteenth_dopiero_od_2022():
    assert date(2021, 6, 18) not in short_days(2021)
    assert date(2021, 6, 21) not in short_days(2021)
    assert date(2022, 6, 20) in short_days(2022), "19.06.2022 to niedziela -> poniedzialek"
    assert date(2024, 6, 19) in short_days(2024)


def test_polowki_dnia():
    # Dzien po Swiecie Dziekczynienia 2024.
    assert date(2024, 11, 29) in short_days(2024)
    # 3 lipca 2024 (sroda) — dzien przed swietem.
    assert date(2024, 7, 3) in short_days(2024)
    # Wigilia 2024 (wtorek).
    assert date(2024, 12, 24) in short_days(2024)
    # Wigilia 2022 wypada w sobote — nie ma czego skracac.
    assert date(2022, 12, 24) not in short_days(2022)


def test_dzien_skrocony_ma_zamkniecie_o_13():
    cal = build_calendar(2024, 2024)
    assert cal.close_time(date(2024, 11, 29)).hour == 13
    assert cal.close_time(date(2024, 11, 26)).hour == 16


def test_dzien_bez_sesji():
    cal = build_calendar(2024, 2024)
    assert not cal.is_trading_day(date(2024, 3, 29)), "Wielki Piatek"
    assert not cal.is_trading_day(date(2024, 3, 30)), "sobota"
    assert cal.is_trading_day(date(2024, 5, 27)), "Memorial Day — sesja skrocona, ale jest"


def test_kalendarz_nie_jest_zweryfikowany_zanim_ktos_go_nie_porowna():
    """Generator z regul nie przewidzi sesji odwolanej doraznie (zaloba, huragan)."""
    assert build_calendar(2019, 2026).verified is False


def test_pomocnicze_wyznaczanie_dat():
    assert nth_weekday(2024, 1, 0, 3) == date(2024, 1, 15)     # 3. poniedzialek stycznia
    assert last_weekday(2024, 5, 0) == date(2024, 5, 27)       # ostatni poniedzialek maja
    assert observed(date(2027, 12, 25)) == date(2027, 12, 24)  # sobota -> piatek
    assert observed(date(2022, 1, 1)) is None                  # przeniesienie poza rok
