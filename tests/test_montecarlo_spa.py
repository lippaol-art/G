"""Testy Monte Carlo i SPA — PLAN.pdf rozdz. 7.2.

Znowu technika testow o znanej odpowiedzi. Dla bootstrapu blokowego kluczowa
wlasnoscia jest to, ze przy danych ZALEZNYCH daje przedzialy SZERSZE niz wariant
iid — gdyby dawal wezsze albo takie same, nie robilby tego, po co istnieje.
"""

from __future__ import annotations

import numpy as np
import pytest

from validation.montecarlo import (
    DEFAULT_N_SYNTHETIC,
    block_bootstrap_series,
    bootstrap_expectancy,
    max_drawdown,
    permutation_test,
    synthetic_pvalue,
    synthetic_test_passes,
)
from validation.spa import superior_predictive_ability

# ==========================================================================
# PERMUTACJA
# ==========================================================================

class TestPermutation:
    def test_mdd_liczony_poprawnie(self):
        equity = np.array([0.0, 10.0, 5.0, 12.0, 2.0, 8.0])
        assert max_drawdown(equity) == pytest.approx(10.0)   # szczyt 12 -> dolek 2

    def test_mdd_rosnacej_krzywej_to_zero(self):
        assert max_drawdown(np.array([0.0, 1.0, 2.0, 3.0])) == 0.0

    def test_permutacja_daje_rozklad_mdd(self):
        rng = np.random.default_rng(1)
        wynik = permutation_test(rng.normal(0.05, 1.0, 200), n_permutations=500, seed=1)
        assert wynik.mdd_distribution.size == 500
        assert wynik.mdd_p95 > 0

    def test_planowanie_bierze_p95_nie_historie(self):
        """Historia pokazala jedna kolejnosc z wielu — nie ma powodu sadzic,
        ze byla najgorsza. Stad p95 rozkladu jako podstawa planowania."""
        rng = np.random.default_rng(2)
        wynik = permutation_test(rng.normal(0.05, 1.0, 300), n_permutations=800, seed=2)
        assert wynik.mdd_p95 >= np.median(wynik.mdd_distribution)

    def test_za_malo_transakcji_odrzucone(self):
        with pytest.raises(ValueError):
            permutation_test(np.array([1.0]))


# ==========================================================================
# BOOTSTRAP — kluczowa wlasnosc: blokowy jest SZERSZY
# ==========================================================================

class TestBootstrap:
    def test_blokowy_daje_szersze_ci_przy_danych_zaleznych(self):
        """ZNANA ODPOWIEDZ: przy autokorelacji bootstrap iid zanizal by szerokosc
        przedzialu, czyli dawal falszywa pewnosc. Blokowy musi byc szerszy."""
        rng = np.random.default_rng(3)
        # silnie autokorelowany szereg (AR(1), phi=0.85)
        n = 600
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = 0.85 * x[i - 1] + rng.normal(0, 0.01)

        blok = bootstrap_expectancy(x, block=True, mean_block_len=20,
                                    n_resamples=800, seed=3)
        iid = bootstrap_expectancy(x, block=False, n_resamples=800, seed=3)

        assert blok.width > iid.width, (
            f"blokowy CI ({blok.width:.5f}) nie jest szerszy od iid ({iid.width:.5f}) "
            "— bootstrap blokowy nie robi tego, po co istnieje"
        )

    def test_metoda_jest_raportowana(self):
        """Raport musi jawnie mowic, ktora metoda uzyto — to warunek bramki."""
        rng = np.random.default_rng(4)
        x = rng.normal(0.001, 0.01, 200)
        assert bootstrap_expectancy(x, block=True, n_resamples=200).method == "block_daily"
        assert bootstrap_expectancy(x, block=False, n_resamples=200).method == "iid_trades"

    def test_ci_zawiera_estymator_punktowy(self):
        rng = np.random.default_rng(5)
        w = bootstrap_expectancy(rng.normal(0.002, 0.01, 400), n_resamples=500, seed=5)
        assert w.ci_low <= w.point_estimate <= w.ci_high

    def test_wyrazna_przewaga_daje_dodatnia_dolna_granice(self):
        rng = np.random.default_rng(6)
        w = bootstrap_expectancy(rng.normal(0.01, 0.005, 400), n_resamples=500, seed=6)
        assert w.passes and w.ci_low > 0

    def test_szum_nie_przechodzi(self):
        rng = np.random.default_rng(7)
        w = bootstrap_expectancy(rng.normal(0.0, 0.01, 400), n_resamples=500, seed=7)
        assert not w.passes

    def test_za_malo_obserwacji_odrzucone(self):
        with pytest.raises(ValueError):
            bootstrap_expectancy(np.ones(5))


# ==========================================================================
# SYNTETYKI
# ==========================================================================

class TestSynthetics:
    def test_bootstrap_blokowy_zachowuje_rozklad(self):
        """Syntetyk ma miec te same wlasnosci statystyczne, ale zadnej struktury."""
        rng = np.random.default_rng(8)
        oryginal = rng.normal(0, 0.01, 2000)
        syntetyk = block_bootstrap_series(oryginal, mean_block_len=390, seed=8)
        assert syntetyk.size == oryginal.size
        assert syntetyk.std() == pytest.approx(oryginal.std(), rel=0.25)

    def test_syntetyk_niszczy_strukture_czasowa(self):
        """Trend liniowy ma nie przetrwac bootstrapu blokowego.

        Testujemy ROZKLAD po wielu ziarnach, nie pojedyncze ziarno: funkcja jest
        stochastyczna, wiec jeden przebieg moze trafic w ogon i test bylby kruchy.
        (Pierwsza wersja tego testu wlasnie tak polegla — ziarno 9 dalo |r|=0.58
        przy srednim |r|=0.14.)
        """
        trend = np.linspace(0, 1, 1000)
        t = np.arange(1000)
        cors = np.array([
            abs(np.corrcoef(t, block_bootstrap_series(trend, mean_block_len=20, seed=s))[0, 1])
            for s in range(30)
        ])
        assert cors.mean() < 0.30, f"srednia |r| = {cors.mean():.3f} — struktura przetrwala"
        assert np.median(cors) < 0.25

    def test_dlugie_bloki_zachowuja_wiecej_struktury(self):
        """WAZNE DLA ROZDZ. 7.2c: dlugosc bloku steruje tym, ile struktury zostaje.

        Przy blokach dlugosci sesji (390 barow) czesc serii syntetycznych zachowuje
        istotna korelacje z czasem. Kierunek jest bezpieczny — resztkowa struktura
        PODNOSI poprzeczke, ktora musi przebic wynik realny, wiec test staje sie
        bardziej konserwatywny, nie mniej. Ale trzeba o tym wiedziec przy
        interpretacji p-wartosci syntetykow.
        """
        trend = np.linspace(0, 1, 1000)
        t = np.arange(1000)

        def srednia_korelacja(mbl: int) -> float:
            return float(np.mean([
                abs(np.corrcoef(t, block_bootstrap_series(trend, mean_block_len=mbl,
                                                          seed=s))[0, 1])
                for s in range(30)
            ]))

        assert srednia_korelacja(390) > srednia_korelacja(20)

    def test_pvalue_nigdy_nie_jest_zerem(self):
        """Postac (1+k)/(1+N) gwarantuje p > 0."""
        p = synthetic_pvalue(observed=100.0, synthetic_scores=np.zeros(1000))
        assert p > 0
        assert p == pytest.approx(1 / 1001)

    def test_minimalne_p_zalezy_od_liczby_syntetykow(self):
        """Powod podniesienia z 200 do 1000 serii: przy 200 min. p = 0.005."""
        p200 = synthetic_pvalue(1e9, np.zeros(200))
        p1000 = synthetic_pvalue(1e9, np.zeros(1000))
        assert p200 == pytest.approx(1 / 201)
        assert p1000 < p200
        assert DEFAULT_N_SYNTHETIC == 1000

    def test_wynik_gorszy_od_syntetykow_nie_przechodzi(self):
        rng = np.random.default_rng(10)
        syntetyki = rng.normal(1.0, 0.2, 1000)
        assert not synthetic_test_passes(observed=0.9, synthetic_scores=syntetyki)
        assert synthetic_test_passes(observed=2.0, synthetic_scores=syntetyki)


# ==========================================================================
# SPA
# ==========================================================================

class TestSPA:
    def test_szum_nie_odrzuca_hipotezy_zerowej(self):
        """ZNANA ODPOWIEDZ: pula samych szumowych wariantow nie moze dac
        istotnego wyniku — inaczej test przepuszczalby data-snooping."""
        rng = np.random.default_rng(11)
        M = rng.normal(0, 0.01, (400, 10))
        w = superior_predictive_ability(M, n_bootstrap=300, seed=11, force_fallback=True)
        assert not w.passes, f"szum dal p={w.pvalue:.4f} — test przepuszcza snooping"

    def test_prawdziwa_przewaga_odrzuca_hipoteze_zerowa(self):
        rng = np.random.default_rng(12)
        M = rng.normal(0, 0.01, (400, 10))
        M[:, 4] += 0.005
        w = superior_predictive_ability(M, n_bootstrap=300, seed=12, force_fallback=True)
        assert w.passes, f"realna przewaga dala p={w.pvalue:.4f}"
        assert w.best_variant == 4

    def test_dosypanie_slabych_wariantow_nie_rozciencza(self):
        """Przewaga SPA nad Reality Check: RC daje sie 'rozcienczyc' beznadziejnymi
        wariantami, SPA nie — dzieki rekcentrowaniu Hansena."""
        rng = np.random.default_rng(13)
        dobry = rng.normal(0, 0.01, (400, 3))
        dobry[:, 0] += 0.006

        slabe = rng.normal(-0.004, 0.01, (400, 12))   # warianty wyraznie zle
        rozcienczony = np.hstack([dobry, slabe])

        p_maly = superior_predictive_ability(dobry, n_bootstrap=300, seed=13,
                                             force_fallback=True).pvalue
        p_duzy = superior_predictive_ability(rozcienczony, n_bootstrap=300, seed=13,
                                             force_fallback=True).pvalue
        assert p_duzy < 0.10, f"dosypanie slabych wariantow rozcienczylo wynik (p={p_duzy:.4f})"
        assert abs(p_duzy - p_maly) < 0.15

    def test_implementacja_jest_raportowana(self):
        """Raport musi mowic, czy uzyto `arch` czy fallbacku."""
        rng = np.random.default_rng(14)
        w = superior_predictive_ability(rng.normal(0, 0.01, (100, 3)),
                                        n_bootstrap=100, force_fallback=True)
        assert w.implementation == "fallback_stationary_bootstrap"

    def test_za_malo_obserwacji_odrzucone(self):
        rng = np.random.default_rng(15)
        with pytest.raises(ValueError):
            superior_predictive_ability(rng.normal(0, 0.01, (10, 3)))


# ==========================================================================
# SPA — SCIEZKA `arch`
#
# DLACZEGO TA KLASA POWSTALA OSOBNO. Wszystkie testy w `TestSPA` wyzej
# przekazuja `force_fallback=True`. Sciezka `arch` — czyli DOMYSLNA, ta ktora
# realnie zadziala w kazdym uruchomieniu produkcyjnym — nie byla testowana
# w ogole. Blad znaku przezyl 233 testy wlasnie dlatego.
#
# Ponizsze testy sa testami o ZNANEJ ODPOWIEDZI na sciezce domyslnej.
# ==========================================================================

def _pula(n_obs: int, n_war: int, przewaga: float, seed: int) -> np.ndarray:
    """Macierz wariantow o znanej strukturze. Kolumna 0 dostaje przewage."""
    rng = np.random.default_rng(seed)
    M = rng.normal(0.0, 1.0, size=(n_obs, n_war))
    if przewaga:
        M[:, 0] += przewaga
    return M


class TestSPASciezkaArch:
    def test_arch_wykrywa_przewage_ktorej_szuka(self):
        """ZNANA ODPOWIEDZ: wariant z przewaga 1.0 sigma na 400 obserwacjach ma
        t okolo 20. Test, ktory tego nie odrzuca, testuje hipoteze PRZECIWNA
        do zamierzonej."""
        w = superior_predictive_ability(_pula(400, 6, 1.0, 22),
                                        n_bootstrap=500, seed=7)
        assert w.implementation == "arch"
        assert w.pvalue < 0.01, (
            f"sciezka arch dala p={w.pvalue:.4f} przy przewadze 1 sigma (t~20) — "
            "test nie reaguje na sygnal, ktorego szuka"
        )

    def test_arch_nie_odrzuca_na_samym_szumie(self):
        w = superior_predictive_ability(_pula(400, 6, 0.0, 22),
                                        n_bootstrap=500, seed=7)
        assert w.implementation == "arch"
        assert w.pvalue > 0.10, f"sam szum dal p={w.pvalue:.4f} — test przepuszcza snooping"

    def test_arch_rozroznia_szum_od_przewagi(self):
        """Najostrzejszy z tych testow. Identyczna p-wartosc dla szumu i dla
        przewagi jest ROZSTRZYGAJACA: znaczy, ze statystyka nie zalezy od tego,
        co miala mierzyc. Dokladnie to pokazal golden baseline (0.898 w obu
        przypadkach)."""
        p_szum = superior_predictive_ability(_pula(400, 6, 0.0, 22),
                                             n_bootstrap=500, seed=7).pvalue
        p_edge = superior_predictive_ability(_pula(400, 6, 0.30, 22),
                                             n_bootstrap=500, seed=7).pvalue
        assert p_edge < p_szum, (
            f"p przy przewadze ({p_edge:.4f}) nie jest mniejsze niz p przy szumie "
            f"({p_szum:.4f}) — statystyka nie rozroznia tych przypadkow"
        )

    def test_best_variant_i_best_mean_w_konwencji_zwrotow(self):
        """Wynik ma byc raportowany w ZWROTACH, nawet jesli implementacja
        wewnetrznie operuje na stratach. Wariant 0 jest tu najgorszy, wiec
        `best_variant` MUSI wskazac inny, a `best_mean` musi byc jego srednim
        ZWROTEM — nie strata i nie liczba ze zmienionym znakiem."""
        M = _pula(400, 5, 0.0, 31)
        M[:, 0] -= 1.0          # wariant 0 wyraznie najgorszy
        M[:, 3] += 0.50         # wariant 3 najlepszy

        w = superior_predictive_ability(M, n_bootstrap=300, seed=3)
        assert w.best_variant == 3, f"wskazano wariant {w.best_variant}, nie najlepszy"
        assert w.best_mean == pytest.approx(float(M[:, 3].mean()), abs=1e-12)
        assert w.best_mean > 0

    def test_sama_strategia_ujemna_nie_daje_istotnosci(self):
        """Pula, w ktorej KAZDY wariant traci. H0 nie ma prawa zostac odrzucona."""
        M = _pula(400, 4, 0.0, 41) - 0.50
        w = superior_predictive_ability(M, n_bootstrap=300, seed=4)
        assert not w.passes, f"pula samych stratnych wariantow dala p={w.pvalue:.4f}"

    def test_warianty_identyczne_zachowuja_sie_jak_jeden(self):
        """Zdegenerowany przypadek: piec kopii tego samego szeregu. Nie ma tu
        zadnego wyboru "najlepszego z wielu", wiec wynik musi byc taki sam jak
        dla jednego wariantu."""
        kolumna = _pula(400, 1, 0.60, 51)
        jeden = superior_predictive_ability(kolumna, n_bootstrap=300, seed=5)
        piec = superior_predictive_ability(np.hstack([kolumna] * 5),
                                           n_bootstrap=300, seed=5)
        assert jeden.passes and piec.passes
        assert piec.pvalue == pytest.approx(jeden.pvalue, abs=0.05)

    def test_obie_sciezki_zgodne_co_do_werdyktu(self):
        """Piec przypadkow o znanej odpowiedzi. `arch` i wlasny fallback moga
        dawac rozne p-wartosci — to dwie implementacje bootstrapu — ale MUSZA
        sie zgadzac co do odrzucenia H0. Rozbieznosc werdyktu znaczy, ze ktoras
        testuje cos innego."""
        przypadki = {
            "sam_szum": (_pula(400, 6, 0.0, 61), False),
            "silna_przewaga": (_pula(400, 6, 1.0, 62), True),
            "silnie_ujemna": (_pula(400, 4, 0.0, 63) - 0.50, False),
            "jeden_z_wielu_ma_przewage": (_pula(400, 8, 0.60, 64), True),
            "warianty_identyczne": (np.hstack([_pula(400, 1, 0.60, 65)] * 4), True),
        }
        for nazwa, (M, oczekiwane) in przypadki.items():
            a = superior_predictive_ability(M, n_bootstrap=300, seed=9)
            f = superior_predictive_ability(M, n_bootstrap=300, seed=9,
                                            force_fallback=True)
            assert a.passes is oczekiwane, (
                f"[{nazwa}] arch: p={a.pvalue:.4f}, oczekiwano "
                f"{'odrzucenia' if oczekiwane else 'braku odrzucenia'} H0"
            )
            assert f.passes is oczekiwane, (
                f"[{nazwa}] fallback: p={f.pvalue:.4f}, oczekiwano "
                f"{'odrzucenia' if oczekiwane else 'braku odrzucenia'} H0"
            )
