"""Deflated Sharpe Ratio i efektywna liczba prob.

Specyfikacja: PLAN.pdf rozdz. 6.5, aneks A.3.
Zrodla: Bailey & Lopez de Prado (JPM 2014); Lopez de Prado & Bailey,
        False Strategy Theorem (2021); Lopez de Prado & Lewis, ONC (2018).

TRZY WARUNKI POPRAWNEJ IMPLEMENTACJI (do sprawdzenia w code review):
  1. SR, gamma3, gamma4 liczone na zwrotach DZIENNYCH, nigdy annualizowanych.
     Wstawienie SR annualizowanego to najczestszy blad implementacji DSR.
  2. gamma4 to kurtoza SUROWA (rozklad normalny = 3), nie nadwyzkowa —
     spojnie z czlonem ((gamma4 - 1) / 4).
  3. sigma_SR to rozrzut SR-ow W POPRZEK prob, sqrt(V[{SR_n}]), zgodnie z FST.
     Uproszczenie 1/sqrt(T) to szczegolny przypadek czystego szumu iid —
     dopuszczalne wylacznie jako jawnie oznaczony fallback.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

EULER_MASCHERONI = 0.5772156649015329
TRADING_DAYS = 252


@dataclass(frozen=True)
class DSRResult:
    dsr: float
    sr_daily: float
    sr0_daily: float
    n_eff: int
    t_days: int
    sigma_sr_source: str   # "cross_trial" albo "fallback_1_over_sqrt_T"

    @property
    def passes(self) -> bool:
        """Bramka Tier 2 (rozdz. 1.3): DSR >= 0.95."""
        return self.dsr >= 0.95

    @property
    def sr_annualized(self) -> float:
        return self.sr_daily * math.sqrt(TRADING_DAYS)


def expected_max_sr(n_eff: int, sigma_sr: float) -> float:
    """SR_0 — oczekiwane maksimum SR z n_eff prob o zerowej prawdziwej przewadze.

        SR_0 = sigma_SR * [ (1-g)*Phi^-1(1 - 1/N) + g*Phi^-1(1 - 1/(N*e)) ]

    Dla N = 1 zwracamy 0: pojedyncza proba nie niesie kary za selekcje.
    """
    if n_eff <= 1:
        return 0.0
    g = EULER_MASCHERONI
    a = norm.ppf(1.0 - 1.0 / n_eff)
    b = norm.ppf(1.0 - 1.0 / (n_eff * math.e))
    return sigma_sr * ((1.0 - g) * a + g * b)


def sigma_sr_from_trials(trial_sharpes_daily: Sequence[float]) -> float:
    """sigma_SR wg False Strategy Theorem — odchylenie SR-ow w poprzek prob.

    To jest wersja POPRAWNA. Wymaga >= 2 zarejestrowanych prob.
    """
    arr = np.asarray(list(trial_sharpes_daily), dtype=float)
    if arr.size < 2:
        raise ValueError("sigma_SR z rozrzutu prob wymaga >= 2 prob; uzyj fallbacku 1/sqrt(T)")
    return float(np.std(arr, ddof=1))


def sigma_sr_fallback(t_days: int) -> float:
    """Fallback 1/sqrt(T) — szczegolny przypadek czystego szumu iid.

    Uzywac WYLACZNIE gdy prob jest za malo, by oszacowac wariancje miedzyprobowa,
    i zawsze oznaczac w raporcie.
    """
    return 1.0 / math.sqrt(t_days)


def deflated_sharpe(
    sr_daily: float,
    t_days: int,
    n_eff: int,
    *,
    skew: float = 0.0,
    kurtosis: float = 3.0,
    trial_sharpes_daily: Sequence[float] | None = None,
) -> DSRResult:
    """Deflated Sharpe Ratio.

        DSR = Phi( (SR - SR_0) * sqrt(T-1) / sqrt(1 - g3*SR + ((g4-1)/4)*SR^2) )

    Parametry
    ---------
    sr_daily : Sharpe DZIENNY (nie annualizowany!)
    t_days   : dlugosc szeregu w dniach
    n_eff    : efektywna liczba prob (z `effective_trials`)
    skew     : gamma3 zwrotow dziennych
    kurtosis : gamma4 SUROWA (normalny = 3)
    trial_sharpes_daily : SR-y wszystkich prob -> sigma_SR wg FST.
                          Gdy None, uzywany jest fallback 1/sqrt(T).
    """
    if t_days < 2:
        raise ValueError("t_days musi byc >= 2")

    if trial_sharpes_daily is not None and len(trial_sharpes_daily) >= 2:
        sigma_sr = sigma_sr_from_trials(trial_sharpes_daily)
        source = "cross_trial"
    else:
        sigma_sr = sigma_sr_fallback(t_days)
        source = "fallback_1_over_sqrt_T"

    sr0 = expected_max_sr(n_eff, sigma_sr)

    denom_sq = 1.0 - skew * sr_daily + ((kurtosis - 1.0) / 4.0) * sr_daily**2
    if denom_sq <= 0:
        raise ValueError(f"Mianownik DSR niedodatni ({denom_sq}); sprawdz momenty rozkladu")

    z = (sr_daily - sr0) * math.sqrt(t_days - 1) / math.sqrt(denom_sq)
    return DSRResult(
        dsr=float(norm.cdf(z)),
        sr_daily=sr_daily,
        sr0_daily=sr0,
        n_eff=n_eff,
        t_days=t_days,
        sigma_sr_source=source,
    )


def deflated_sharpe_annualized(
    sr_annual: float, t_days: int, n_eff: int, **kwargs
) -> DSRResult:
    """Wygodne opakowanie: przyjmuje SR ANNUALIZOWANY i sam go przelicza.

    Istnieje po to, zeby nikt nie wstawil SR rocznego do `deflated_sharpe`.
    """
    return deflated_sharpe(sr_annual / math.sqrt(TRADING_DAYS), t_days, n_eff, **kwargs)


def days_to_certify(
    sr_annual: float, n_eff: int = 1, target_dsr: float = 0.95,
    *, skew: float = 0.0, kurtosis: float = 3.0, max_days: int = 20_000
) -> int | None:
    """Ile dni OOS potrzeba, by DSR osiagnelo `target_dsr`.

    Narzedzie planowania hipotez (rozdz. 6.5): przed startem badania widac,
    czy budzet prob w ogole pozwala na certyfikacje.

    Zwraca None, gdy cel nieosiagalny w `max_days`.
    """
    lo, hi = 2, max_days
    if deflated_sharpe_annualized(sr_annual, hi, n_eff, skew=skew,
                                  kurtosis=kurtosis).dsr < target_dsr:
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        if deflated_sharpe_annualized(sr_annual, mid, n_eff, skew=skew,
                                      kurtosis=kurtosis).dsr >= target_dsr:
            hi = mid
        else:
            lo = mid + 1
    return lo


# --------------------------------------------------------------------------
# Efektywna liczba prob — algorytm z aneksu A.3
# --------------------------------------------------------------------------

def effective_trials(
    trial_returns: np.ndarray,
    *,
    method: str = "onc",
    cutoff: float | None = None,
) -> tuple[int, np.ndarray]:
    """N_eff przez klastrowanie skorelowanych wariantow.

    Warianty jednej hipotezy sa silnie skorelowane, wiec surowa liczba komorek
    siatki drastycznie przeszacowuje kare za selekcje. Algorytm (A.3):

        1. macierz korelacji C = corr(zwroty wariantow)
        2. metryka odleglosci  d_ij = sqrt(0.5 * (1 - C_ij))   <- nie surowa korelacja
        3. klastrowanie hierarchiczne, average linkage
        4. liczba klastrow: ONC (maksymalizacja silhouette) albo staly prog
        5. N_eff = liczba klastrow

    Parametry
    ---------
    trial_returns : macierz (n_trials, n_days) — zwroty dzienne kazdego wariantu
    method : "onc" (domyslnie) albo "cutoff"
    cutoff : prog korelacji dla method="cutoff" (np. 0.7)

    Zwraca (n_eff, etykiety_klastrow).
    """
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    X = np.asarray(trial_returns, dtype=float)
    if X.ndim != 2:
        raise ValueError("trial_returns musi byc macierza (n_trials, n_days)")
    n = X.shape[0]
    if n <= 1:
        return max(n, 1), np.zeros(max(n, 1), dtype=int)

    C = np.corrcoef(X)
    C = np.nan_to_num(C, nan=0.0)
    np.fill_diagonal(C, 1.0)

    D = np.sqrt(np.clip(0.5 * (1.0 - C), 0.0, None))
    np.fill_diagonal(D, 0.0)
    Z = linkage(squareform(D, checks=False), method="average")

    if method == "cutoff":
        if cutoff is None:
            raise ValueError('method="cutoff" wymaga podania `cutoff`')
        thr = math.sqrt(0.5 * (1.0 - cutoff))
        labels = fcluster(Z, t=thr, criterion="distance")
        return int(labels.max()), labels

    # ONC: wybor liczby klastrow maksymalizujacy silhouette
    from sklearn.metrics import silhouette_score

    best_k, best_score, best_labels = 1, -1.0, np.ones(n, dtype=int)
    for k in range(2, min(n, 20) + 1):
        labels = fcluster(Z, t=k, criterion="maxclust")
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(D, labels, metric="precomputed")
        if score > best_score:
            best_k, best_score, best_labels = k, score, labels
    return best_k, best_labels


def effective_trials_simple(trial_returns: np.ndarray, cutoff: float = 0.7) -> int:
    """METODA WYCOFANA METODOLOGICZNIE — ZAKAZANA W NOWYCH BADANIACH.

    Wariant bez zaleznosci od scikit-learn: klastrowanie po sztywnym progu
    korelacji. Rownowazny `method="cutoff"`.

    DLACZEGO WYCOFANA. Sztywne odciecie 0.7 jest arbitralne i audyt 2
    (poprawka A2-3) zastapil je algorytmem ONC — Lopez de Prado & Lewis 2018 —
    z odlegloscia d = sqrt(0.5*(1-rho)), average linkage i analiza wrazliwosci
    w zakresie 0.5-0.9. Roznica nie jest kosmetyczna: N_eff wchodzi wprost do
    mianownika DSR, wiec zly podzial na klastry przesuwa prog certyfikacji.

    Funkcja NIE ZOSTALA USUNIETA (decyzja wlasciciela, poz. N6) — zostaje jako
    slad historyczny metody, ktora projekt swiadomie porzucil. Do nowych
    obliczen uzywaj `effective_trials(..., method="onc")`.
    """
    n_eff, _ = effective_trials(trial_returns, method="cutoff", cutoff=cutoff)
    return n_eff
