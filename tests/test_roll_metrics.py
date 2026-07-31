"""Testy rolowania (rozdz. 4.3) i metryk (rozdz. 6.1-6.3).

Fixture'y kontraktow konstruowane recznie — to dane testowe, nie rynkowe.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from engine.metrics import (
    CONCENTRATION_GATE,
    PF_SUSPICIOUS,
    drawdown_stats,
    expectancy,
    profit_factor,
    sharpe_lo_correction,
    sharpe_ratio,
    sortino_ratio,
    sqn,
    summarize,
    top_n_concentration,
)
from engine.roll import (
    ContractDay,
    RollEvent,
    adjust_price,
    cumulative_offsets,
    days_to_roll,
    find_roll_dates,
    unadjust_price,
)

# ==========================================================================
# ROLOWANIE
# ==========================================================================

class TestRoll:
    def _dwa_kontrakty(self):
        """MNQH5 traci plynnosc, MNQM5 ja przejmuje 2025-03-13."""
        h5 = [
            ContractDay(date(2025, 3, 11), "MNQH5", 20000.0, 900_000),
            ContractDay(date(2025, 3, 12), "MNQH5", 20010.0, 700_000),
            ContractDay(date(2025, 3, 13), "MNQH5", 20020.0, 300_000),
            ContractDay(date(2025, 3, 14), "MNQH5", 20030.0, 100_000),
        ]
        m5 = [
            ContractDay(date(2025, 3, 11), "MNQM5", 20100.0, 100_000),
            ContractDay(date(2025, 3, 12), "MNQM5", 20110.0, 400_000),
            ContractDay(date(2025, 3, 13), "MNQM5", 20125.0, 800_000),
            ContractDay(date(2025, 3, 14), "MNQM5", 20135.0, 950_000),
        ]
        return {"MNQH5": h5, "MNQM5": m5}

    def test_rolowanie_w_dniu_przewagi_wolumenu(self):
        """Regula wolumenowa, nie kalendarzowa — odzwierciedla migracje plynnosci."""
        ev = find_roll_dates(self._dwa_kontrakty(), ["MNQH5", "MNQM5"])
        assert len(ev) == 1
        assert ev[0].roll_date == date(2025, 3, 13)
        assert ev[0].spread == pytest.approx(20125.0 - 20020.0)   # +105

    def test_brak_rolowania_gdy_wolumen_nie_przechodzi(self):
        dane = self._dwa_kontrakty()
        for d in dane["MNQM5"]:
            object.__setattr__(d, "volume", 1)
        assert find_roll_dates(dane, ["MNQH5", "MNQM5"]) == []

    def test_offset_najnowszego_kontraktu_to_zero(self):
        """Ceny najnowszego kontraktu sa 'prawdziwe' — to punkt odniesienia."""
        ev = find_roll_dates(self._dwa_kontrakty(), ["MNQH5", "MNQM5"])
        off = cumulative_offsets(ev)
        assert off["MNQM5"] == 0.0
        assert off["MNQH5"] == pytest.approx(105.0)

    def test_offsety_kumuluja_sie_wstecz(self):
        ev = [
            RollEvent(date(2025, 3, 13), "A", "B", 100.0),
            RollEvent(date(2025, 6, 12), "B", "C", 50.0),
        ]
        off = cumulative_offsets(ev)
        assert off["C"] == 0.0
        assert off["B"] == pytest.approx(50.0)
        assert off["A"] == pytest.approx(150.0), "offset A = suma obu spreadow"

    def test_adjust_i_unadjust_sa_odwrotne(self):
        """Rozdzielenie serii wymaga konwersji w obie strony (rozdz. 4.3)."""
        off = {"MNQH5": 105.0, "MNQM5": 0.0}
        raw = 20020.0
        adj = adjust_price(raw, "MNQH5", off)
        assert adj == pytest.approx(20125.0)
        assert unadjust_price(adj, "MNQH5", off) == pytest.approx(raw)

    def test_back_adjust_zachowuje_roznice_cen(self):
        """Klucz metody roznicowej: P&L w punktach i ATR sa nietkniete."""
        off = {"MNQH5": 105.0}
        a_raw, b_raw = 20000.0, 20010.0
        a_adj = adjust_price(a_raw, "MNQH5", off)
        b_adj = adjust_price(b_raw, "MNQH5", off)
        assert (b_adj - a_adj) == pytest.approx(b_raw - a_raw)

    def test_nieznany_kontrakt_traktowany_jak_najnowszy(self):
        assert adjust_price(100.0, "NIEZNANY", {"A": 5.0}) == 100.0

    def test_dni_do_rolowania(self):
        ev = [RollEvent(date(2025, 3, 13), "A", "B", 100.0)]
        assert days_to_roll(date(2025, 3, 10), ev) == 3
        assert days_to_roll(date(2025, 3, 13), ev) == 0
        assert days_to_roll(date(2025, 3, 20), ev) is None


# ==========================================================================
# METRYKI
# ==========================================================================

class TestMetrics:
    def test_expectancy_to_srednia_w_r(self):
        assert expectancy(np.array([1.0, -1.0, 2.0, -1.0])) == pytest.approx(0.25)

    def test_profit_factor(self):
        assert profit_factor(np.array([2.0, -1.0, 1.0, -1.0])) == pytest.approx(1.5)

    def test_profit_factor_bez_strat_to_nieskonczonosc(self):
        assert profit_factor(np.array([1.0, 2.0])) == float("inf")

    def test_prog_podejrzliwosci(self):
        """PF > 2 w intraday: protokol nakazuje najpierw szukac bledu."""
        m = summarize(np.array([3.0, -1.0, 3.0, -1.0]), np.array([1.0, -0.3, 1.0, -0.3]))
        assert m.profit_factor > PF_SUSPICIOUS
        assert m.suspicious

    def test_sharpe_annualizowany(self):
        rng = np.random.default_rng(1)
        d = rng.normal(0.001, 0.01, 500)
        sr_d = sharpe_ratio(d, annualize=False)
        assert sharpe_ratio(d) == pytest.approx(sr_d * np.sqrt(252))

    def test_poprawka_lo_zmniejsza_modul_sharpe_przy_autokorelacji(self):
        """Autokorelacja ZAWYZA MODUL annualizowanego Sharpe'a.

        Uwaga na kierunek: poprawka dzieli przez sqrt(czynnik) > 1, wiec przy
        DODATNIM Sharpie obniza wartosc, a przy UJEMNYM podnosi ja (ku zeru).
        Wlasnoscia niezmiennicza jest zmniejszenie modulu — i to testujemy.
        (Pierwsza wersja tego testu asertowala na wartosci ze znakiem i poleglа
        na serii, ktorej zrealizowany dryf wyszedl ujemny.)
        """
        rng = np.random.default_rng(2)
        n = 600
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = 0.6 * x[i - 1] + rng.normal(0.004, 0.01)   # wyrazny dodatni dryf

        surowy = sharpe_ratio(x)
        poprawiony = sharpe_lo_correction(x)
        assert surowy > 0, "test wymaga dodatniego Sharpe'a, zeby kierunek byl jednoznaczny"
        assert abs(poprawiony) < abs(surowy)
        assert poprawiony < surowy

    def test_poprawka_lo_zmniejsza_modul_takze_dla_ujemnego_sharpe(self):
        """Kontrola symetrii: przy ujemnym Sharpie poprawka przesuwa go ku zeru."""
        rng = np.random.default_rng(21)
        n = 600
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = 0.6 * x[i - 1] + rng.normal(-0.004, 0.01)

        surowy = sharpe_ratio(x)
        poprawiony = sharpe_lo_correction(x)
        assert surowy < 0
        assert abs(poprawiony) < abs(surowy)
        assert poprawiony > surowy, "ujemny Sharpe po poprawce zbliza sie do zera"

    def test_poprawka_lo_neutralna_bez_autokorelacji(self):
        rng = np.random.default_rng(3)
        d = rng.normal(0.001, 0.01, 800)
        assert sharpe_lo_correction(d) == pytest.approx(sharpe_ratio(d), rel=0.25)

    def test_sortino_wyzszy_gdy_ogon_jest_po_stronie_zyskow(self):
        symetryczny = np.array([0.01, -0.01] * 50)
        asymetryczny = np.array([0.03, -0.005] * 50)
        assert sortino_ratio(asymetryczny) > sortino_ratio(symetryczny)

    def test_drawdown_i_czas_pod_woda(self):
        equity = np.array([0.0, 5.0, 3.0, 2.0, 6.0, 4.0])
        mdd, czas = drawdown_stats(equity)
        assert mdd == pytest.approx(3.0)     # szczyt 5 -> dolek 2
        assert czas == 2                      # dwa kroki ponizej szczytu

    def test_rosnaca_krzywa_bez_obsuniecia(self):
        mdd, czas = drawdown_stats(np.array([0.0, 1.0, 2.0, 3.0]))
        assert mdd == 0.0 and czas == 0

    def test_koncentracja_lapie_strategie_z_kilku_dni(self):
        """Chroni przed strategia 'z trzech szczesliwych dni' (rozdz. 1.3)."""
        skoncentrowana = np.array([10.0, 10.0, 10.0, 10.0, 10.0] + [0.01] * 200)
        rozlozona = np.array([0.5] * 205)
        assert top_n_concentration(skoncentrowana, 5) > CONCENTRATION_GATE
        assert top_n_concentration(rozlozona, 5) < CONCENTRATION_GATE

    def test_sqn_rosnie_z_liczba_transakcji(self):
        maly = np.array([1.0, -0.5] * 10)
        duzy = np.array([1.0, -0.5] * 100)
        assert sqn(duzy) > sqn(maly)

    def test_summarize_zwraca_komplet(self):
        rng = np.random.default_rng(4)
        r = rng.normal(0.1, 1.0, 300)
        d = rng.normal(0.002, 0.01, 300)
        m = summarize(r, d)
        assert m.n_trades == 300
        assert 0.0 <= m.win_rate <= 1.0
        assert isinstance(m.gate_report(), dict)
        assert set(m.gate_report()) == {"profit_factor", "sharpe", "koncentracja"}

    def test_puste_dane_nie_wywalaja(self):
        assert expectancy(np.array([])) == 0.0
        assert sharpe_ratio(np.array([1.0])) == 0.0
        assert drawdown_stats(np.array([])) == (0.0, 0)
