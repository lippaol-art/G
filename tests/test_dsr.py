"""Testy DSR — regresja na liczbach opublikowanych w PLAN.pdf rozdz. 6.5.

Tabele w dokumencie zalozycielskim sa kontraktem: jesli implementacja sie z nimi
rozjedzie, albo dokument klamie, albo kod ma blad. Oba przypadki musza wywolac
czerwony test.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from validation.dsr import (
    TRADING_DAYS,
    days_to_certify,
    deflated_sharpe,
    deflated_sharpe_annualized,
    effective_trials,
    expected_max_sr,
    sigma_sr_fallback,
    sigma_sr_from_trials,
)


# --------------------------------------------------------------------------
# REGRESJA: tabela wykonalnosci DSR z PLAN.pdf rozdz. 6.5
# --------------------------------------------------------------------------

# (SR annualizowany, N_eff) -> DSR przy T = 1500 dni
PLAN_TABLE_T1500 = {
    (0.8, 1): 0.974, (0.8, 5): 0.776, (0.8, 10): 0.647, (0.8, 30): 0.452,
    (1.0, 1): 0.993, (1.0, 5): 0.894, (1.0, 10): 0.806, (1.0, 30): 0.643,
    (1.2, 1): 0.998, (1.2, 5): 0.958, (1.2, 10): 0.912, (1.2, 30): 0.803,
    (1.5, 1): 1.000, (1.5, 5): 0.993, (1.5, 10): 0.981, (1.5, 30): 0.943,
}


@pytest.mark.parametrize("key,expected", sorted(PLAN_TABLE_T1500.items()))
def test_dsr_matches_published_table(key, expected):
    """Tabela DSR(SR, N_eff) przy T=1500 musi zgadzac sie z dokumentem."""
    sr_ann, n_eff = key
    got = deflated_sharpe_annualized(sr_ann, t_days=1500, n_eff=n_eff).dsr
    assert got == pytest.approx(expected, abs=0.001), (
        f"SR={sr_ann}, N_eff={n_eff}: kod daje {got:.3f}, dokument mowi {expected:.3f}"
    )


# (SR annualizowany) -> wymagane T przy N_eff = 1, tolerancja +-10 dni
PLAN_DAYS_TO_CERTIFY = {0.8: 1070, 1.0: 690, 1.2: 480, 1.5: 310}


@pytest.mark.parametrize("sr_ann,expected_days", sorted(PLAN_DAYS_TO_CERTIFY.items()))
def test_days_to_certify_matches_published(sr_ann, expected_days):
    """Ile dni OOS do DSR=0.95 przy pojedynczej probie — tabela z rozdz. 6.5."""
    got = days_to_certify(sr_ann, n_eff=1)
    assert got is not None
    assert abs(got - expected_days) <= 10, (
        f"SR={sr_ann}: kod daje {got} dni, dokument mowi ~{expected_days}"
    )


def test_bramka_nieprzechodnia_dla_sr08():
    """Kluczowe ustalenie audytu: SR 0.8 nie przechodzi przy realnej liczbie prob.

    To jest wlasnie powod istnienia systemu dwustopniowego (rozdz. 1.3).
    """
    assert deflated_sharpe_annualized(0.8, 1500, 1).passes      # tylko przy 1 probie
    assert not deflated_sharpe_annualized(0.8, 1500, 5).passes
    assert not deflated_sharpe_annualized(0.8, 1500, 10).passes


def test_limit_30_wariantow_byl_samobojczy():
    """Przy N_eff=30 nie przechodzi nawet SR 1.5 — stad limit 10 (rozdz. 6.5)."""
    assert not deflated_sharpe_annualized(1.5, 1500, 30).passes
    assert deflated_sharpe_annualized(1.5, 1500, 10).passes


# --------------------------------------------------------------------------
# Wlasnosci matematyczne
# --------------------------------------------------------------------------

def test_sr0_rosnie_z_liczba_prob():
    """Im wiecej prob, tym wyzszy prog losowosci do pobicia."""
    sigma = sigma_sr_fallback(1000)
    vals = [expected_max_sr(n, sigma) for n in (1, 2, 5, 10, 50, 200)]
    assert vals[0] == 0.0
    assert all(a < b for a, b in zip(vals, vals[1:]))


def test_dsr_rosnie_z_dlugoscia_proby():
    a = deflated_sharpe_annualized(1.0, 500, 5).dsr
    b = deflated_sharpe_annualized(1.0, 1500, 5).dsr
    assert b > a


def test_dsr_maleje_z_liczba_prob():
    a = deflated_sharpe_annualized(1.0, 1500, 2).dsr
    b = deflated_sharpe_annualized(1.0, 1500, 20).dsr
    assert b < a


def test_annualizacja_jest_odwracalna():
    """Opakowanie annualizowane musi dawac to samo co wersja dzienna."""
    sr_ann = 1.1
    sr_d = sr_ann / math.sqrt(TRADING_DAYS)
    assert deflated_sharpe_annualized(sr_ann, 1200, 4).dsr == pytest.approx(
        deflated_sharpe(sr_d, 1200, 4).dsr
    )


def test_wstawienie_sr_annualizowanego_daje_absurd():
    """Ochrona przed najczestszym bledem implementacji DSR.

    SR annualizowany wstawiony jako dzienny zawyza wynik do 1.0 — test
    dokumentuje, dlaczego istnieje osobne opakowanie `_annualized`.
    """
    poprawnie = deflated_sharpe_annualized(0.8, 1500, 10).dsr
    blednie = deflated_sharpe(0.8, 1500, 10).dsr   # SR roczny podany jako dzienny
    assert poprawnie < 0.7
    assert blednie > 0.99


def test_skosnosc_i_kurtoza_wplywaja_na_wynik():
    """Grube ogony i ujemna skosnosc musza obnizac DSR."""
    base = deflated_sharpe_annualized(1.2, 1500, 5, skew=0.0, kurtosis=3.0).dsr
    fat = deflated_sharpe_annualized(1.2, 1500, 5, skew=-0.5, kurtosis=8.0).dsr
    assert fat < base


def test_sigma_sr_z_prob_vs_fallback():
    """Wersja FST (rozrzut prob) i fallback musza byc rozroznialne w raporcie."""
    trials = [0.03, 0.05, 0.02, 0.06, 0.04]
    r_fst = deflated_sharpe(0.05, 1000, 5, trial_sharpes_daily=trials)
    r_fb = deflated_sharpe(0.05, 1000, 5)
    assert r_fst.sigma_sr_source == "cross_trial"
    assert r_fb.sigma_sr_source == "fallback_1_over_sqrt_T"
    assert sigma_sr_from_trials(trials) == pytest.approx(np.std(trials, ddof=1))


def test_sigma_sr_z_jednej_proby_odrzucone():
    with pytest.raises(ValueError):
        sigma_sr_from_trials([0.05])


# --------------------------------------------------------------------------
# Efektywna liczba prob
# --------------------------------------------------------------------------

def test_neff_skorelowane_warianty_kolapsuja():
    """10 niemal identycznych wariantow to nie 10 niezaleznych prob."""
    rng = np.random.default_rng(42)
    base = rng.normal(0, 0.01, 500)
    trials = np.array([base + rng.normal(0, 0.0005, 500) for _ in range(10)])
    n_eff, _ = effective_trials(trials, method="cutoff", cutoff=0.7)
    assert n_eff < 10, f"skorelowane warianty daly N_eff={n_eff}, oczekiwano znacznie mniej"


def test_neff_niezalezne_warianty_nie_kolapsuja():
    rng = np.random.default_rng(7)
    trials = rng.normal(0, 0.01, (8, 500))
    n_eff, _ = effective_trials(trials, method="cutoff", cutoff=0.7)
    assert n_eff >= 6, f"niezalezne warianty daly N_eff={n_eff}, oczekiwano ~8"


def test_neff_pojedynczy_wariant():
    n_eff, _ = effective_trials(np.zeros((1, 100)), method="cutoff", cutoff=0.7)
    assert n_eff == 1
