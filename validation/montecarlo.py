"""Testy Monte Carlo: permutacja, bootstrap blokowy, syntetyki.

Specyfikacja: PLAN.pdf rozdz. 7.2.

Trzy testy mierza TRZY ROZNE rzeczy i zaden nie zastepuje pozostalych:

  (a) permutacja kolejnosci transakcji  -> rozklad sciezki i MDD.
      NIE mowi nic o istnieniu przewagi — tylko o tym, jak zle moglo pojsc
      przy tym samym zestawie transakcji w innej kolejnosci.

  (b) bootstrap wyniku                  -> przedzial ufnosci dla expectancy.
      WARIANT BLOKOWY jest obowiazkowy: transakcje NIE sa niezalezne
      (klastrowanie zmiennosci, rezimy), wiec bootstrap po pojedynczych
      transakcjach daje przedzialy ZA WASKIE, czyli falszywa pewnosc.

  (c) pelny pipeline na syntetykach     -> ile "zysku" generuje sama procedura.
      Najmocniejszy pojedynczy test w arsenale. Warunek krytyczny: na
      syntetykach wykonujemy DOKLADNIE TYLE SAMO prob optymalizacyjnych
      co na danych realnych — inaczej test zaniza prog.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_N_PERMUTATIONS = 5_000
DEFAULT_N_BOOTSTRAP = 5_000
DEFAULT_N_SYNTHETIC = 1_000      # v1.0 miala 200 — za malo (min. p = 0.005, szumny p95)


@dataclass(frozen=True)
class PermutationResult:
    mdd_observed: float
    mdd_p95: float
    mdd_distribution: np.ndarray

    @property
    def passes(self) -> bool:
        """Realny MDD musi miescic sie ponizej 95. percentyla rozkladu."""
        return self.mdd_observed <= self.mdd_p95


@dataclass(frozen=True)
class BootstrapResult:
    point_estimate: float
    ci_low: float
    ci_high: float
    method: str          # "block_daily" albo "iid_trades"
    n_resamples: int

    @property
    def passes(self) -> bool:
        """Dolna granica przedzialu musi byc dodatnia."""
        return self.ci_low > 0

    @property
    def width(self) -> float:
        return self.ci_high - self.ci_low


def max_drawdown(equity: np.ndarray) -> float:
    """Maksymalne obsuniecie krzywej kapitalu (wartosc dodatnia)."""
    arr = np.asarray(equity, dtype=float)
    if arr.size == 0:
        return 0.0
    peak = np.maximum.accumulate(arr)
    return float(np.max(peak - arr))


def permutation_test(
    trade_results: np.ndarray,
    *,
    n_permutations: int = DEFAULT_N_PERMUTATIONS,
    seed: int = 0,
) -> PermutationResult:
    """Rozklad MDD przy losowych permutacjach kolejnosci transakcji.

    Planowanie kapitalu bierze 95. percentyl tego rozkladu, NIE historyczny MDD —
    historia pokazala jedna kolejnosc z wielu mozliwych i nie ma powodu sadzic,
    ze byla najgorsza.
    """
    r = np.asarray(trade_results, dtype=float)
    if r.size < 2:
        raise ValueError("potrzeba >= 2 transakcji")

    rng = np.random.default_rng(seed)
    observed = max_drawdown(np.cumsum(r))

    dist = np.empty(n_permutations)
    for i in range(n_permutations):
        dist[i] = max_drawdown(np.cumsum(rng.permutation(r)))

    return PermutationResult(observed, float(np.percentile(dist, 95)), dist)


def _bca_interval(
    boot: np.ndarray, theta_hat: float, jackknife: np.ndarray, alpha: float
) -> tuple[float, float]:
    """Przedzial BCa — korekta na obciazenie i skosnosc.

    Zwykly percentyl bootstrapu niedokrywa przy skosnych rozkladach, a wyniki
    tradingowe sa skosne niemal zawsze.
    """
    from scipy.stats import norm

    z0 = norm.ppf(np.mean(boot < theta_hat)) if 0 < np.mean(boot < theta_hat) < 1 else 0.0
    jack_mean = jackknife.mean()
    num = np.sum((jack_mean - jackknife) ** 3)
    den = 6.0 * (np.sum((jack_mean - jackknife) ** 2) ** 1.5)
    a = num / den if den != 0 else 0.0

    def adj(p: float) -> float:
        zp = norm.ppf(p)
        val = z0 + (z0 + zp) / (1 - a * (z0 + zp))
        return float(np.clip(norm.cdf(val) * 100, 0.1, 99.9))

    return (float(np.percentile(boot, adj(alpha / 2))),
            float(np.percentile(boot, adj(1 - alpha / 2))))


def bootstrap_expectancy(
    daily_pnl: np.ndarray,
    *,
    block: bool = True,
    mean_block_len: float = 1.0,
    n_resamples: int = DEFAULT_N_BOOTSTRAP,
    alpha: float = 0.05,
    seed: int = 0,
) -> BootstrapResult:
    """Przedzial ufnosci BCa dla sredniego dziennego wyniku.

    `block=True` (DOMYSLNIE i wymagane przez bramke): bootstrap blokowy
    o losowej dlugosci bloku ~ geometryczna(1/mean_block_len). Zachowuje
    lokalna strukture zaleznosci, wiec przedzial jest UCZCIWIE szerszy.

    `block=False`: wariant iid — dostepny wylacznie do porownania, zeby pokazac,
    o ile bootstrap po pojedynczych obserwacjach zawyza pewnosc.
    """
    x = np.asarray(daily_pnl, dtype=float)
    n = x.size
    if n < 10:
        raise ValueError("potrzeba >= 10 obserwacji dziennych")

    rng = np.random.default_rng(seed)
    theta_hat = float(x.mean())
    boot = np.empty(n_resamples)

    if block:
        p = 1.0 / max(mean_block_len, 1.0)
        for i in range(n_resamples):
            sample: list[float] = []
            while len(sample) < n:
                start = rng.integers(0, n)
                length = max(1, int(rng.geometric(p)))
                idx = (np.arange(start, start + length)) % n   # zawijanie cykliczne
                sample.extend(x[idx])
            boot[i] = np.mean(sample[:n])
        method = "block_daily"
    else:
        for i in range(n_resamples):
            boot[i] = x[rng.integers(0, n, n)].mean()
        method = "iid_trades"

    jack = np.array([np.mean(np.delete(x, i)) for i in range(n)])
    lo, hi = _bca_interval(boot, theta_hat, jack, alpha)
    return BootstrapResult(theta_hat, lo, hi, method, n_resamples)


def block_bootstrap_series(
    returns: np.ndarray, *, mean_block_len: float = 390.0, seed: int = 0
) -> np.ndarray:
    """Jedna seria syntetyczna: bootstrap blokowy zwrotow M1.

    Zachowuje rozklad i klastry zmiennosci, NISZCZY strukture czasowa —
    dokladnie to, czego potrzebujemy: rynek o tych samych wlasnosciach
    statystycznych, ale bez zadnej struktury do znalezienia.

    `mean_block_len=390` ~ jedna sesja RTH w barach minutowych.
    """
    x = np.asarray(returns, dtype=float)
    n = x.size
    if n < 2:
        raise ValueError("potrzeba >= 2 obserwacji")

    rng = np.random.default_rng(seed)
    p = 1.0 / max(mean_block_len, 1.0)
    out: list[float] = []
    while len(out) < n:
        start = rng.integers(0, n)
        length = max(1, int(rng.geometric(p)))
        idx = (np.arange(start, start + length)) % n
        out.extend(x[idx])
    return np.array(out[:n])


def synthetic_pvalue(observed: float, synthetic_scores: np.ndarray) -> float:
    """p-wartosc wzgledem rozkladu wynikow na danych bez struktury.

    p = (1 + #{syntetyk >= obserwacja}) / (1 + N)

    Postac z jedynkami gwarantuje p > 0 — przy 1000 syntetykach minimalne
    osiagalne p wynosi ~0.001. To wlasnie dlatego v1.0 z 200 seriami byla
    niewystarczajaca: nie dalo sie zejsc ponizej 0.005.
    """
    s = np.asarray(synthetic_scores, dtype=float)
    if s.size == 0:
        raise ValueError("brak wynikow syntetycznych")
    return float((1 + np.sum(s >= observed)) / (1 + s.size))


def synthetic_test_passes(observed: float, synthetic_scores: np.ndarray) -> bool:
    """Wynik realny musi przekroczyc 95. percentyl syntetykow (rozdz. 7.2c)."""
    return observed > float(np.percentile(np.asarray(synthetic_scores, dtype=float), 95))
