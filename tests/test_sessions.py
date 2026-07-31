"""Testy segmentacji doby — PLAN.pdf rozdz. 3.3, 4.4, 4.6.

Nacisk na pulapki stref czasowych: to klasa bledow, ktora nie objawia sie jako
awaria, tylko jako cicho zafalszowany wynik dwa razy w roku.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from engine.sessions import (
    ET,
    SessionCalendar,
    in_historical_halt,
    in_maintenance,
    is_expected_gap,
    is_rth,
    segment_of,
    to_et,
    trade_date,
)


def utc(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=UTC)


def et(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=ET)


# --------------------------------------------------------------------------
# Otwarcie RTH to ZAWSZE 9:30 ET — w UTC rozne zaleznie od pory roku
# --------------------------------------------------------------------------

def test_rth_open_zima_i_latem_ten_sam_segment():
    """Definicja sesji w UTC rozjechalaby statystyki otwarcia dwa razy w roku."""
    zima = utc(2024, 1, 15, 14, 30)    # 9:30 ET (EST = UTC-5)
    lato = utc(2024, 7, 15, 13, 30)    # 9:30 ET (EDT = UTC-4)
    assert to_et(zima).hour == 9 and to_et(zima).minute == 30
    assert to_et(lato).hour == 9 and to_et(lato).minute == 30
    assert segment_of(zima) == segment_of(lato) == "rth_open"


def test_ta_sama_godzina_utc_to_inne_segmenty():
    """14:30 UTC to otwarcie RTH zima, ale juz premarket latem."""
    assert segment_of(utc(2024, 1, 15, 14, 30)) == "rth_open"
    assert segment_of(utc(2024, 7, 15, 14, 30)) == "midday"


@pytest.mark.parametrize("h,m,expected", [
    (18, 0, "globex_open"), (18, 59, "globex_open"),
    (19, 0, "asia"), (1, 59, "asia"),
    (2, 0, "europe"), (8, 29, "europe"),
    (8, 30, "premarket"), (9, 29, "premarket"),
    (9, 30, "rth_open"), (10, 29, "rth_open"),
    (10, 30, "midday"), (13, 29, "midday"),
    (13, 30, "afternoon"), (14, 59, "afternoon"),
    (15, 0, "close"), (15, 59, "close"),
    (16, 0, "after_hours"), (16, 59, "after_hours"),
    (17, 0, "maintenance"), (17, 59, "maintenance"),
])
def test_granice_segmentow(h, m, expected):
    assert segment_of(et(2024, 3, 20, h, m)) == expected


# --------------------------------------------------------------------------
# trade_date — dzien sesyjny zaczyna sie o 18:00 ET dnia poprzedniego
# --------------------------------------------------------------------------

def test_trade_date_wieczor_nalezy_do_nastepnego_dnia():
    assert trade_date(et(2024, 3, 19, 20, 0)) == date(2024, 3, 20)
    assert trade_date(et(2024, 3, 20, 10, 0)) == date(2024, 3, 20)


def test_trade_date_niedziela_wieczor_to_poniedzialek():
    """Sesja nocna 'poniedzialkowa' zaczyna sie w niedziele wieczorem."""
    niedziela = et(2024, 3, 17, 19, 0)
    assert niedziela.weekday() == 6
    assert trade_date(niedziela) == date(2024, 3, 18)


def test_trade_date_przed_18_to_ten_sam_dzien():
    assert trade_date(et(2024, 3, 20, 17, 30)) == date(2024, 3, 20)


def test_trade_date_agreguje_cala_dobe_handlowa():
    """Bary od niedzieli 18:00 do poniedzialku 17:00 to jeden dzien sesyjny."""
    start = et(2024, 3, 17, 18, 0)
    dni = {trade_date(start + timedelta(hours=h)) for h in range(0, 23)}
    assert dni == {date(2024, 3, 18)}


# --------------------------------------------------------------------------
# Przerwa serwisowa i historyczny halt
# --------------------------------------------------------------------------

def test_przerwa_serwisowa():
    assert in_maintenance(et(2024, 3, 20, 17, 30))
    assert not in_maintenance(et(2024, 3, 20, 16, 30))
    assert not in_maintenance(et(2024, 3, 20, 18, 30))


def test_historyczny_halt_istnieje_przed_czerwcem_2021():
    """Halt 15:15-15:30 CT wystepuje w naszym oknie danych (2019-2021)."""
    assert in_historical_halt(datetime(2020, 5, 12, 20, 20, tzinfo=UTC))


def test_historyczny_halt_zniesiony_po_2021_06_27():
    assert not in_historical_halt(datetime(2022, 5, 12, 20, 20, tzinfo=UTC))
    assert not in_historical_halt(datetime(2024, 5, 12, 20, 20, tzinfo=UTC))


def test_halt_tylko_w_swoim_oknie():
    assert not in_historical_halt(datetime(2020, 5, 12, 19, 0, tzinfo=UTC))


# --------------------------------------------------------------------------
# Klasyfikacja luk — brak bara nie jest defektem (rozdz. 4.2)
# --------------------------------------------------------------------------

def test_luka_przerwy_serwisowej_jest_oczekiwana():
    assert is_expected_gap(et(2024, 3, 20, 17, 0), et(2024, 3, 20, 18, 0))


def test_luka_weekendowa_jest_oczekiwana():
    assert is_expected_gap(et(2024, 3, 22, 17, 0), et(2024, 3, 24, 18, 0))


def test_luka_w_srodku_rth_to_anomalia():
    """Dziesiec minut bez bara w najplynniejszym segmencie doby = do przejrzenia."""
    assert not is_expected_gap(et(2024, 3, 20, 10, 0), et(2024, 3, 20, 10, 10))


def test_luka_swiateczna_jest_oczekiwana():
    """Przerwa mieszczaca sie w calosci w dniu swiatecznym."""
    cal = SessionCalendar(holidays=frozenset({date(2024, 7, 4)}))
    assert is_expected_gap(et(2024, 7, 4, 9, 0), et(2024, 7, 4, 17, 0), cal)


def test_luka_obejmujaca_wznowienie_po_swiecie_to_anomalia():
    """Globex wznawia handel wieczorem po swiecie — brak barow w nocy z 4 na 5
    lipca NIE jest oczekiwany, bo rynek juz wtedy dziala.

    Ten przypadek zlapal blad w pierwotnej wersji testu: latwo zalozyc, ze
    "swieto = cala przerwa oczekiwana", a doba handlowa zaczyna sie wieczorem
    dnia poprzedniego i sesja nocna po swiecie jest normalna sesja.
    """
    cal = SessionCalendar(holidays=frozenset({date(2024, 7, 4)}))
    assert not is_expected_gap(et(2024, 7, 3, 18, 0), et(2024, 7, 5, 9, 0), cal)


def test_luka_jednominutowa_nie_jest_luka():
    assert is_expected_gap(et(2024, 3, 20, 10, 0), et(2024, 3, 20, 10, 1))


# --------------------------------------------------------------------------
# RTH i dni skrocone
# --------------------------------------------------------------------------

def test_is_rth():
    assert is_rth(et(2024, 3, 20, 10, 0))
    assert not is_rth(et(2024, 3, 20, 9, 0))
    assert not is_rth(et(2024, 3, 20, 16, 30))


def test_dzien_skrocony_zamyka_sie_o_13():
    cal = SessionCalendar(short_days=frozenset({date(2024, 11, 29)}))
    assert is_rth(et(2024, 11, 29, 12, 30), cal)
    assert not is_rth(et(2024, 11, 29, 14, 0), cal)
    assert is_rth(et(2024, 11, 28, 14, 0))   # zwykly dzien: nadal RTH
