"""Testy modelu kosztow (rozdz. 3.2, 5.5) i mocy testu (rozdz. 6.4, aneks A.1).

Liczby kosztowe i tabela mocy sa opublikowane w PLAN.pdf — te testy sa
regresja wzgledem dokumentu.
"""

from __future__ import annotations

import math

import pytest

from engine.costs import (
    TICK_VALUE,
    CostModel,
    annual_cost,
    gap_stop_slippage_ticks,
    points_to_usd,
    slippage_ticks,
)
from validation.power import (
    FLOOR_TRADES,
    TARGET_TRADES,
    achieved_power,
    minimum_detectable_effect,
    required_sample_size,
)

# --------------------------------------------------------------------------
# Koszty — regresja na liczbach z rozdz. 3.2
# --------------------------------------------------------------------------

def test_baza_kosztow_to_220_usd():
    """Decyzja z 31.07.2026: prowizja 1.20 + 2x1 tick = 2.20 USD RT.

    Wersja 1.0 dokumentu podawala 3.20 przy tym samym wzorze — blad arytmetyczny
    wychwycony przez audyt.
    """
    assert CostModel().round_turn_cost(slippage_ticks_total=2) == pytest.approx(2.20)


def test_stress_test_podwaja_poslizg_nie_prowizje():
    """Stress x2 dotyczy poslizgu; prowizja jest staloscia umowna."""
    base = CostModel()
    stress = CostModel(stress_multiplier=2.0)
    assert base.round_turn_cost(2) == pytest.approx(2.20)
    assert stress.round_turn_cost(2) == pytest.approx(1.20 + 2 * TICK_VALUE * 2)  # 3.20


@pytest.mark.parametrize("trades_per_day,expected", [
    (0.5, 276), (2, 1104), (5, 2761), (10, 5522),
])
def test_koszt_roczny_zgodny_z_tabela(trades_per_day, expected):
    """Tabela wrazliwosci kosztow rocznych z rozdz. 3.2."""
    got = annual_cost(trades_per_day)
    assert got == pytest.approx(expected, abs=1.0)


def test_poslizg_bazowy_per_segment():
    """RTH poza otwarciem = 1 tick; otwarcie i Azja = 2 (rozdz. 5.5)."""
    assert slippage_ticks("midday") == 1.0
    assert slippage_ticks("rth_open") == 2.0
    assert slippage_ticks("asia") == 2.0


def test_poslizg_skaluje_sie_zmiennoscia():
    """Statyczna tabela zanizalaby koszt tam, gdzie jest najwiekszy."""
    spokojnie = slippage_ticks("midday", atr_m1=1.0, atr_m1_median=1.0)
    burzliwie = slippage_ticks("midday", atr_m1=2.5, atr_m1_median=1.0)
    assert burzliwie > spokojnie
    assert burzliwie == pytest.approx(2.5)


def test_mnoznik_zmiennosci_jest_ograniczony():
    """Clamp do [1.0, 3.0] — bez tego pojedynczy outlier rozsadzalby model."""
    ekstremum = slippage_ticks("midday", atr_m1=100.0, atr_m1_median=1.0)
    assert ekstremum == pytest.approx(3.0)
    cisza = slippage_ticks("midday", atr_m1=0.1, atr_m1_median=1.0)
    assert cisza == pytest.approx(1.0), "mnoznik nie schodzi ponizej 1 — nie nagradzamy ciszy"


def test_poslizg_zdarzeniowy_najwyzszy():
    assert slippage_ticks("midday", near_event=True) == 4.0


def test_poslizg_gap_rosnie_z_luka():
    """Po otwarciu luka plynnosc jest bliska zeru — 2-8 tickow ponad open."""
    mala = gap_stop_slippage_ticks(gap_points=1.0, atr_m1=2.0)
    duza = gap_stop_slippage_ticks(gap_points=8.0, atr_m1=2.0)
    assert duza > mala
    assert duza == pytest.approx(1.0 + 1.5 * 4.0)   # cap na 4x ATR


def test_konwersje_jednostek():
    assert points_to_usd(10.0) == pytest.approx(20.0)      # mnoznik 2 USD/pkt
    assert points_to_usd(10.0, contracts=3) == pytest.approx(60.0)
    assert pytest.approx(0.50) == TICK_VALUE


# --------------------------------------------------------------------------
# Moc testu — regresja na tabeli z rozdz. 6.4
# --------------------------------------------------------------------------

@pytest.mark.parametrize("power,expected", [(0.50, 384), (0.80, 785), (0.90, 1051)])
def test_licznosc_proby_zgodna_z_tabela(power, expected):
    """Tabela mocy testu z rozdz. 6.4 (sigma=1.2R, E=0.12R)."""
    got = required_sample_size(power=power).n_required
    assert abs(got - expected) <= 2, f"moc {power:.0%}: kod {got}, dokument {expected}"


def test_v10_liczyla_istotnosc_nie_moc():
    """Rachunek z v1.0 (N~384) daje moc ~50% — czyli rzut moneta.

    To jest wlasnie powod podniesienia podlogi do 400 i celu do 800.
    """
    assert achieved_power(384) == pytest.approx(0.50, abs=0.02)
    assert achieved_power(785) == pytest.approx(0.80, abs=0.02)


def test_progi_projektu_spojne_z_wyprowadzeniem():
    assert FLOOR_TRADES == 400
    assert TARGET_TRADES == 800
    assert required_sample_size(power=0.80).n_required > FLOOR_TRADES


def test_mde_maleje_z_wielkoscia_proby():
    """Im wieksza proba, tym mniejszy efekt jestesmy w stanie wykryc."""
    assert minimum_detectable_effect(100) > minimum_detectable_effect(800)


def test_mde_dyskwalifikuje_hipotezy_o_rzadkich_sygnalach():
    """40 transakcji OOS -> wykrywalne dopiero E > 0.37R, czyli nierealistyczne.

    Karta o takiej czestosci sygnalow (dawne H008: ~52 obserwacje rocznie) nie
    moze zostac certyfikowana, cokolwiek pokaze backtest — i lepiej wiedziec
    to PRZED spaleniem budzetu prob (rozdz. 6.6).
    """
    assert minimum_detectable_effect(40) > 0.35


def test_sigma_wieksza_podnosi_wymagana_probe():
    """sigma=1.2R to zalozenie; strategie z dlugim ogonem maja 1.5-2R."""
    male = required_sample_size(sigma_r=1.2).n_required
    duze = required_sample_size(sigma_r=2.0).n_required
    assert duze > 2 * male


class TestCenyWarunkowania:
    """Wniosek W002 — warunkowanie kosztuje 1/sqrt(f).

    Reguly, wedlug ktorych bedziemy oceniac przyszle karty, musza byc testowane
    tak samo jak reszta kodu. Ta akurat powstala z badania W001 i decyduje
    o tym, ktore hipotezy w ogole warto uruchamiac.
    """

    def test_brak_warunkowania_nie_kosztuje_nic(self):
        from validation.power import conditional_edge_multiplier
        assert conditional_edge_multiplier(1.0) == pytest.approx(1.0)

    def test_polowa_okazji_kosztuje_pierwiastek_z_dwoch(self):
        from validation.power import conditional_edge_multiplier
        assert conditional_edge_multiplier(0.5) == pytest.approx(math.sqrt(2), rel=1e-12)

    def test_decyl_kosztuje_ponad_trzykrotnie(self):
        """Liczba z raportu W001: zawezenie do 10% nocy wymaga ~3.16x przewagi."""
        from validation.power import conditional_edge_multiplier
        assert conditional_edge_multiplier(0.1) == pytest.approx(3.1623, abs=1e-4)

    def test_mnoznik_rosnie_monotonicznie_przy_zwezaniu(self):
        from validation.power import conditional_edge_multiplier
        m = [conditional_edge_multiplier(f) for f in (1.0, 0.5, 0.25, 0.1, 0.05)]
        assert m == sorted(m), "zwezanie okna nie moze potaniec"

    def test_ulamek_poza_zakresem_jest_bledem(self):
        from validation.power import conditional_edge_multiplier
        for zly in (0.0, -0.1, 1.5):
            with pytest.raises(ValueError):
                conditional_edge_multiplier(zly)

    def test_wymagany_edge_odtwarza_liczby_z_W001(self):
        """Regresja na raporcie: sd nocna MNQ 0.755%, prog DSR SR 1.13.

        Raport W001 podaje 0.054% na noc dla wszystkich nocy i 0.170% dla decyla.
        Modul musi te liczby odtworzyc, inaczej raport i kod rozjezdzaja sie
        w czasie i nie wiadomo, ktory ma racje.
        """
        from validation.power import required_daily_edge
        sd = 0.00755
        assert required_daily_edge(1.13, sd, 1.0) == pytest.approx(0.000538, abs=5e-6)
        assert required_daily_edge(1.13, sd, 0.1) == pytest.approx(0.001700, abs=5e-6)

    def test_wymagany_edge_skaluje_sie_z_sharpem_liniowo(self):
        from validation.power import required_daily_edge
        a = required_daily_edge(0.8, 0.0075, 0.5)
        b = required_daily_edge(1.6, 0.0075, 0.5)
        assert b == pytest.approx(2 * a, rel=1e-12)

    def test_zerowa_zmiennosc_jest_bledem(self):
        from validation.power import required_daily_edge
        with pytest.raises(ValueError):
            required_daily_edge(1.0, 0.0)
