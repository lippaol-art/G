"""Testy frameworku walidacji — walk-forward, CPCV, PBO.

Kluczowa technika: TESTY O ZNANEJ ODPOWIEDZI. Konstruujemy sytuacje, w ktorych
poprawny wynik da sie wyprowadzic z definicji, i sprawdzamy, czy modul go zwraca.
Dla PBO to szczegolnie wazne — metryka jest na tyle abstrakcyjna, ze bledna
implementacja moze latami zwracac liczby wygladajace sensownie.
"""

from __future__ import annotations

from datetime import date

import numpy as np
import pytest

from validation.cpcv import (
    expected_n_paths,
    make_blocks,
    make_cpcv,
    path_sharpes,
    summarize_paths,
)
from validation.pbo import PBO_GATE, probability_of_backtest_overfitting
from validation.walkforward import (
    EMBARGO_INTRADAY,
    embargo_for,
    is_oos_divergence,
    make_split,
    stitch_oos,
)

# ==========================================================================
# WALK-FORWARD
# ==========================================================================

class TestWalkForward:
    def test_okna_nie_zachodza_na_siebie_w_oos(self):
        """Zszyty OOS nie moze liczyc tego samego dnia dwa razy."""
        split = make_split(date(2019, 1, 1), date(2026, 7, 1))
        for a, b in zip(split.windows, split.windows[1:], strict=False):
            assert a.oos_end <= b.oos_start, f"okna OOS zachodza: {a} / {b}"

    def test_purge_oddziela_trening_od_testu(self):
        """Miedzy IS a OOS musi byc bufor — bez niego autokorelacja przecieka."""
        split = make_split(date(2019, 1, 1), date(2026, 7, 1), horizon="intraday")
        for w in split.windows:
            assert w.oos_start > w.is_end, f"brak purge w {w}"
            assert w.purge_days >= 1

    def test_embargo_swing_jest_dluzsze_niz_intraday(self):
        """Pozycje wielodniowe wymagaja szerszego bufora."""
        assert embargo_for("swing", max_position_days=3) > embargo_for("intraday")

    def test_embargo_intraday_nie_jest_zerowe(self):
        """v1.0 zwalniala intraday z embargo — blednie (rozdz. 7.3)."""
        assert embargo_for("intraday") > EMBARGO_INTRADAY

    def test_nieznany_horyzont_odrzucony(self):
        with pytest.raises(ValueError, match="horyzont"):
            embargo_for("scalping")

    def test_lockbox_jest_poza_wszystkimi_oknami(self):
        """Sejf musi pozostac nietkniety przez caly walk-forward."""
        split = make_split(date(2019, 1, 1), date(2026, 7, 1))
        for w in split.windows:
            assert w.oos_end <= split.lockbox_start, f"{w} wchodzi w lockbox"

    def test_lockbox_ma_zadana_dlugosc(self):
        split = make_split(date(2019, 1, 1), date(2026, 7, 1), lockbox_months=6)
        dni = (split.lockbox_end - split.lockbox_start).days
        assert 170 <= dni <= 190, f"lockbox ma {dni} dni, oczekiwano ~180"

    def test_za_krotka_historia_odrzucona(self):
        """Lepiej glosny blad niz cichy podzial na jedno okno."""
        with pytest.raises(ValueError):
            make_split(date(2025, 1, 1), date(2025, 6, 1))

    def test_dluzsza_historia_daje_wiecej_okien(self):
        krotka = make_split(date(2021, 1, 1), date(2026, 7, 1))
        dluga = make_split(date(2019, 1, 1), date(2026, 7, 1))
        assert len(dluga) > len(krotka)

    def test_zszywanie_zachowuje_kolejnosc_i_dlugosc(self):
        okna = [[1.0, 2.0], [3.0], [4.0, 5.0, 6.0]]
        assert stitch_oos(okna) == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]

    def test_rozjazd_is_oos(self):
        """> 50% rozjazdu PF to czerwona flaga przeuczenia."""
        assert is_oos_divergence(2.0, 1.0) == pytest.approx(0.5)
        assert is_oos_divergence(1.2, 1.15) < 0.1


# ==========================================================================
# CPCV
# ==========================================================================

class TestCPCV:
    def test_liczba_sciezek_to_dwumian(self):
        """N=6, k=2 -> C(6,2) = 15 sciezek. To definicja, nie przyblizenie."""
        assert expected_n_paths(6, 2) == 15
        split = make_cpcv(1000, n_blocks=6, k_test=2)
        assert split.n_paths == 15

    @pytest.mark.parametrize("n,k,expected", [(6, 2, 15), (8, 2, 28), (6, 3, 20), (10, 2, 45)])
    def test_liczba_sciezek_dla_roznych_konfiguracji(self, n, k, expected):
        assert make_cpcv(2000, n_blocks=n, k_test=k).n_paths == expected

    def test_bloki_sa_rozlaczne_i_pokrywaja_calosc(self):
        bounds = make_blocks(1000, 6)
        assert bounds[0][0] == 0
        assert bounds[-1][1] == 1000
        for a, b in zip(bounds, bounds[1:], strict=False):
            assert a[1] == b[0], "bloki musza sie stykac bez luk i nakladek"

    def test_trening_nie_styka_sie_z_testem(self):
        """Sedno purgingu: bloki sasiadujace z testowymi wypadaja z treningu."""
        split = make_cpcv(1200, n_blocks=6, k_test=2, purge_adjacent=True)
        for p in split.paths:
            for t in p.test_blocks:
                assert t - 1 not in p.train_blocks, f"blok {t-1} styka sie z testem {t}"
                assert t + 1 not in p.train_blocks, f"blok {t+1} styka sie z testem {t}"

    def test_bez_purgingu_trening_dotyka_testu(self):
        """Kontrola negatywna — pokazuje, ze purging faktycznie cos zmienia."""
        z = make_cpcv(1200, n_blocks=6, k_test=2, purge_adjacent=True)
        bez = make_cpcv(1200, n_blocks=6, k_test=2, purge_adjacent=False)
        assert sum(len(p.train_blocks) for p in bez.paths) > \
               sum(len(p.train_blocks) for p in z.paths)

    def test_zbiory_sa_rozlaczne(self):
        split = make_cpcv(1200, n_blocks=6, k_test=2)
        for p in split.paths:
            assert not (set(p.test_blocks) & set(p.train_blocks))
            assert not (set(p.test_blocks) & set(p.purged_blocks))
            assert not (set(p.train_blocks) & set(p.purged_blocks))

    def test_kazdy_blok_bywa_testowy(self):
        """CPCV ma testowac 100% danych w warunkach OOS (przewaga nad WFO)."""
        split = make_cpcv(1200, n_blocks=6, k_test=2)
        uzyte = {b for p in split.paths for b in p.test_blocks}
        assert uzyte == set(range(6))

    def test_bledne_parametry_odrzucone(self):
        with pytest.raises(ValueError):
            make_cpcv(1000, n_blocks=6, k_test=6)   # k musi byc < N
        with pytest.raises(ValueError):
            make_cpcv(3, n_blocks=6, k_test=2)      # za malo probek

    def test_rozklad_sharpe_zamiast_punktu(self):
        """CPCV ma dawac ROZKLAD — to jego glowna przewaga nad walk-forward."""
        rng = np.random.default_rng(11)
        sciezki = [rng.normal(0.001, 0.01, 250) for _ in range(15)]
        s = summarize_paths(path_sharpes(sciezki))
        assert s["n_paths"] == 15
        assert s["min"] < s["median"] < s["max"], "rozklad musi miec rozrzut"
        assert 0.0 <= s["frac_positive"] <= 1.0

    def test_stala_seria_daje_sharpe_zero(self):
        assert path_sharpes([np.ones(100)])[0] == 0.0


# ==========================================================================
# PBO — testy o znanej odpowiedzi
# ==========================================================================

class TestPBO:
    def test_czysty_szum_daje_pbo_okolo_polowy(self):
        """ZNANA ODPOWIEDZ: gdy wszystkie warianty to szum, zwyciezca IS jest
        losowy, wiec jego ranga OOS rozklada sie rownomiernie -> PBO ~ 0.5.

        To najwazniejszy test tego modulu: implementacja, ktora tu nie daje ~0.5,
        jest bledna niezaleznie od tego, jak sensownie wyglada na realnych danych.
        """
        rng = np.random.default_rng(42)
        M = rng.normal(0, 0.01, (1000, 12))
        wynik = probability_of_backtest_overfitting(M, n_splits=8)
        assert 0.35 <= wynik.pbo <= 0.65, f"szum dal PBO={wynik.pbo:.3f}, oczekiwano ~0.5"
        assert not wynik.passes, "czysty szum nie moze przejsc bramki"

    def test_prawdziwa_przewaga_daje_pbo_bliskie_zeru(self):
        """ZNANA ODPOWIEDZ: gdy jeden wariant ma trwala przewage, wygrywa IS
        i pozostaje najlepszy OOS -> PBO ~ 0."""
        rng = np.random.default_rng(7)
        M = rng.normal(0, 0.01, (1000, 12))
        M[:, 3] += 0.004          # wariant 3 ma realny, staly edge
        wynik = probability_of_backtest_overfitting(M, n_splits=8)
        assert wynik.pbo < 0.10, f"prawdziwa przewaga dala PBO={wynik.pbo:.3f}"
        assert wynik.passes
        # zwyciezca IS powinien byc niemal zawsze ten sam wariant
        assert (wynik.best_is_indices == 3).mean() > 0.8

    def test_przewaga_tylko_w_pierwszej_polowie_zwieksza_pbo(self):
        """Efekt, ktory wygasa, to dokladnie przypadek, ktory PBO ma lapac."""
        rng = np.random.default_rng(3)
        M = rng.normal(0, 0.01, (1000, 12))
        M[:500, 5] += 0.006       # przewaga istnieje tylko na poczatku
        trwala = rng.normal(0, 0.01, (1000, 12))
        trwala[:, 5] += 0.006
        wygasla = probability_of_backtest_overfitting(M, n_splits=8).pbo
        stala = probability_of_backtest_overfitting(trwala, n_splits=8).pbo
        assert wygasla > stala

    def test_liczba_kombinacji_to_dwumian(self):
        """S=8 -> C(8,4) = 70 kombinacji IS/OOS."""
        rng = np.random.default_rng(1)
        wynik = probability_of_backtest_overfitting(rng.normal(0, 0.01, (500, 5)), n_splits=8)
        assert wynik.n_combinations == 70

    def test_pojedynczy_wariant_odrzucony(self):
        """Przy jednym wariancie nie ma czego wybierac — metryka bezprzedmiotowa."""
        rng = np.random.default_rng(1)
        with pytest.raises(ValueError, match="2 wariantow"):
            probability_of_backtest_overfitting(rng.normal(0, 0.01, (500, 1)))

    def test_nieparzysta_liczba_blokow_odrzucona(self):
        rng = np.random.default_rng(1)
        with pytest.raises(ValueError, match="parzyste"):
            probability_of_backtest_overfitting(rng.normal(0, 0.01, (500, 4)), n_splits=7)

    def test_bramka_zgodna_z_dokumentem(self):
        assert PBO_GATE == 0.20

    def test_logity_i_rangi_maja_spojne_rozmiary(self):
        rng = np.random.default_rng(5)
        w = probability_of_backtest_overfitting(rng.normal(0, 0.01, (800, 6)), n_splits=8)
        assert len(w.logits) == len(w.oos_ranks) == len(w.best_is_indices) == w.n_combinations
        assert np.all((w.oos_ranks > 0) & (w.oos_ranks < 1)), "ranga musi byc w (0,1)"
