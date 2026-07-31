"""Testy tabeli rozstrzygniec wewnatrzbarowych — PLAN.pdf tabela 5.4.

Kazdy wiersz tabeli = osobny test. Bary sa konstruowane recznie: to FIXTURE'Y
TESTOWE, nie dane rynkowe. Rozroznienie jest istotne — zasada projektu "zero
syntetycznych danych" dotyczy danych badawczych i wnioskow o rynku. Bez recznie
zbudowanych barow nie da sie udowodnic poprawnosci silnika, a niesprawdzony
silnik produkuje smieci z dokladnoscia do szesciu miejsc po przecinku.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from engine.backtest import (
    AmbiguousBarPolicy,
    Bar,
    Order,
    Position,
    RiskGate,
    RiskLimits,
    is_ambiguous,
    resolve_exit,
)

TS = datetime(2024, 3, 15, 14, 30, tzinfo=timezone.utc)
SLIP = 0.25   # 1 tick w punktach


def bar(o, h, l, c, volume=100):
    return Bar(ts=TS, open=o, high=h, low=l, close=c, volume=volume)


def long_pos(entry=100.0, sl=98.0, tp=104.0):
    return Position(side="long", qty=1, entry_px=entry, entry_ts=TS, sl=sl, tp=tp)


def short_pos(entry=100.0, sl=102.0, tp=96.0):
    return Position(side="short", qty=1, entry_px=entry, entry_ts=TS, sl=sl, tp=tp)


# --------------------------------------------------------------------------
# Wiersz 1: bar dotyka tylko SL
# --------------------------------------------------------------------------

def test_tylko_sl_long():
    px, reason = resolve_exit(long_pos(), bar(100, 101, 97.5, 99), slippage_points=SLIP)
    assert reason == "stop_loss"
    assert px == pytest.approx(98.0 - SLIP), "stop wykonuje sie GORZEJ, nigdy lepiej"


def test_tylko_sl_short():
    px, reason = resolve_exit(short_pos(), bar(100, 102.5, 99, 101), slippage_points=SLIP)
    assert reason == "stop_loss"
    assert px == pytest.approx(102.0 + SLIP)


# --------------------------------------------------------------------------
# Wiersz 2: bar dotyka tylko TP — wymagane PRZEBICIE o >= 1 tick
# --------------------------------------------------------------------------

def test_tylko_tp_wymaga_przebicia():
    """Samo dotkniecie limitu nie gwarantuje wypelnienia (pozycja w kolejce)."""
    dotkniecie = resolve_exit(long_pos(), bar(100, 104.0, 99, 103), slippage_points=SLIP)
    assert dotkniecie is None, "samo dotkniecie TP nie moze liczyc sie jako wypelnienie"

    przebicie = resolve_exit(long_pos(), bar(100, 104.25, 99, 104), slippage_points=SLIP)
    assert przebicie is not None
    px, reason = przebicie
    assert reason == "take_profit"
    assert px == pytest.approx(104.0), "TP bez dodatniego poslizgu"


def test_tylko_tp_short_wymaga_przebicia():
    assert resolve_exit(short_pos(), bar(100, 101, 96.0, 97), slippage_points=SLIP) is None
    out = resolve_exit(short_pos(), bar(100, 101, 95.75, 96), slippage_points=SLIP)
    assert out is not None and out[1] == "take_profit"


# --------------------------------------------------------------------------
# Wiersz 3: bar dotyka SL I TP — najwazniejszy wiersz tabeli
# --------------------------------------------------------------------------

def test_bar_sporny_domyslnie_sl():
    """Fallback konserwatywny: bez danych 1s liczy sie SL."""
    b = bar(100, 104.5, 97.5, 100)
    assert is_ambiguous(long_pos(), b)
    px, reason = resolve_exit(long_pos(), b, policy=AmbiguousBarPolicy.SL_WINS,
                              slippage_points=SLIP)
    assert reason == "stop_loss"
    assert px == pytest.approx(98.0 - SLIP)


def test_bar_sporny_gorna_granica_pasma():
    """TP_WINS to gorny koniec pasma wrazliwosci — obowiazkowa metryka raportu."""
    b = bar(100, 104.5, 97.5, 100)
    px, reason = resolve_exit(long_pos(), b, policy=AmbiguousBarPolicy.TP_WINS,
                              slippage_points=SLIP)
    assert reason == "take_profit"
    assert px == pytest.approx(104.0)


def test_pasmo_wrazliwosci_ma_niezerowa_szerokosc():
    """Jesli strategia jest dobra tylko przy TP_WINS, nie jest dobra."""
    b = bar(100, 104.5, 97.5, 100)
    dol = resolve_exit(long_pos(), b, policy=AmbiguousBarPolicy.SL_WINS, slippage_points=SLIP)[0]
    gora = resolve_exit(long_pos(), b, policy=AmbiguousBarPolicy.TP_WINS, slippage_points=SLIP)[0]
    assert gora > dol


def test_subbar_wymaga_danych():
    """Polityka SUBBAR_1S bez resolvera musi failowac glosno, nie po cichu."""
    b = bar(100, 104.5, 97.5, 100)
    with pytest.raises(ValueError, match="SUBBAR_1S"):
        resolve_exit(long_pos(), b, policy=AmbiguousBarPolicy.SUBBAR_1S)


def test_subbar_rozstrzyga_faktycznie():
    """Z danymi 1s bar sporny przestaje byc sporny."""
    b = bar(100, 104.5, 97.5, 100)
    px, reason = resolve_exit(
        long_pos(), b, policy=AmbiguousBarPolicy.SUBBAR_1S,
        subbar_resolver=lambda pos, bar_: "tp", slippage_points=SLIP,
    )
    assert reason == "take_profit"

    px, reason = resolve_exit(
        long_pos(), b, policy=AmbiguousBarPolicy.SUBBAR_1S,
        subbar_resolver=lambda pos, bar_: "sl", slippage_points=SLIP,
    )
    assert reason == "stop_loss"


def test_subbar_nierozstrzygniety_wraca_do_konserwatyzmu():
    b = bar(100, 104.5, 97.5, 100)
    _, reason = resolve_exit(
        long_pos(), b, policy=AmbiguousBarPolicy.SUBBAR_1S,
        subbar_resolver=lambda pos, bar_: None, slippage_points=SLIP,
    )
    assert reason == "stop_loss"


# --------------------------------------------------------------------------
# Wiersz 4: open przeskakuje SL luka
# --------------------------------------------------------------------------

def test_gap_wykonanie_po_open_nie_po_sl():
    """Tak dziala stop w rzeczywistosci — nie da sie wyjsc po cenie SL."""
    b = bar(o=95.0, h=96.0, l=94.0, c=95.5)   # open juz ponizej SL=98
    px, reason = resolve_exit(long_pos(), b, slippage_points=SLIP)
    assert reason == "stop_gap"
    assert px == pytest.approx(95.0 - SLIP)
    assert px < 98.0, "wyjscie po cenie SL byloby fikcja"


def test_gap_zwiekszony_poslizg():
    """Po otwarciu luka plynnosc jest bliska zeru — kara musi rosnac."""
    b = bar(o=95.0, h=96.0, l=94.0, c=95.5)
    zwykly = resolve_exit(long_pos(), b, slippage_points=SLIP)[0]
    duzy = resolve_exit(long_pos(), b, slippage_points=SLIP, gap_slippage_points=1.0)[0]
    assert duzy < zwykly


def test_gap_short():
    b = bar(o=105.0, h=106.0, l=104.0, c=105.5)   # open powyzej SL=102
    px, reason = resolve_exit(short_pos(), b, slippage_points=SLIP)
    assert reason == "stop_gap"
    assert px == pytest.approx(105.0 + SLIP)


# --------------------------------------------------------------------------
# Pozycja przezywa bar
# --------------------------------------------------------------------------

def test_bar_neutralny():
    assert resolve_exit(long_pos(), bar(100, 102, 99, 101), slippage_points=SLIP) is None


def test_pozycja_bez_tp():
    pos = Position(side="long", qty=1, entry_px=100, entry_ts=TS, sl=98.0, tp=None)
    assert not is_ambiguous(pos, bar(100, 110, 97, 105))
    _, reason = resolve_exit(pos, bar(100, 110, 97.5, 105), slippage_points=SLIP)
    assert reason == "stop_loss"


# --------------------------------------------------------------------------
# Bar o zerowym wolumenie
# --------------------------------------------------------------------------

def test_bar_zerowy_wolumen_nie_jest_handlowalny():
    """volume == 0 znaczy, ze nie bylo gdzie sie wykonac (rozdz. 4.2)."""
    assert not bar(100, 101, 99, 100, volume=0).tradeable
    assert bar(100, 101, 99, 100, volume=1).tradeable


# --------------------------------------------------------------------------
# Warstwa ryzyka — dziala PRZED strategia
# --------------------------------------------------------------------------

def test_zlecenie_bez_stopa_odrzucone():
    gate = RiskGate()
    with pytest.raises(ValueError, match="stop-loss"):
        gate.validate(Order(side="long", sl=None), open_positions=0)


def test_usrednianie_w_strate_zablokowane():
    gate = RiskGate(RiskLimits(max_positions=1))
    with pytest.raises(ValueError, match="srednianie"):
        gate.validate(Order(side="long", sl=98.0), open_positions=1)


def test_limit_dzienny_blokuje_handel():
    gate = RiskGate(RiskLimits(daily_stop_r=2.0))
    gate.register("2024-03-15", "2024-W11", -1.0)
    assert not gate.blocked("2024-03-15", "2024-W11")
    gate.register("2024-03-15", "2024-W11", -1.2)
    assert gate.blocked("2024-03-15", "2024-W11"), "po -2R handel musi sie zatrzymac"


def test_limit_tygodniowy_blokuje_handel():
    gate = RiskGate(RiskLimits(daily_stop_r=2.0, weekly_stop_r=4.0))
    for day in range(4):
        gate.register(f"day{day}", "2024-W11", -1.1)
    assert gate.blocked("day4", "2024-W11")


def test_limit_dzienny_resetuje_sie_nastepnego_dnia():
    gate = RiskGate(RiskLimits(daily_stop_r=2.0, weekly_stop_r=10.0))
    gate.register("2024-03-15", "2024-W11", -2.5)
    assert gate.blocked("2024-03-15", "2024-W11")
    assert not gate.blocked("2024-03-18", "2024-W12")
