"""Probability of Backtest Overfitting przez CSCV.

Specyfikacja: PLAN.pdf rozdz. 7.2. Zrodlo: Bailey, Borwein, Lopez de Prado, Zhu,
"The Probability of Backtest Overfitting", Journal of Computational Finance 2017.

CZEGO NIE MIERZA POZOSTALE TESTY:
    Permutacja, bootstrap i syntetyki opisuja wlasnosci ZNALEZIONEJ strategii.
    Zaden z nich nie odpowiada na pytanie, ile przewagi wygenerowal sam PROCES
    WYBIERANIA najlepszego wariantu z puli. PBO odpowiada wprost:

        PBO = P(najlepszy wariant in-sample wypadnie PONIZEJ MEDIANY out-of-sample)

    Interpretacja: PBO = 0.5 znaczy, ze wybor najlepszego IS jest bezwartosciowy —
    rownie dobrze moglibysmy losowac. PBO bliskie 0 znaczy, ze ranking IS niesie
    realna informacje o przyszlosci.

    Bramka projektu: PBO < 0.20 (rozdz. 1.3).

ALGORYTM CSCV:
    1. Macierz M: (n_obs, n_variants) — zwroty kazdego wariantu w czasie
    2. Podziel czas na S rownych blokow (S parzyste)
    3. Dla kazdej kombinacji S/2 blokow jako IS (reszta jako OOS):
       a. wybierz wariant o najwyzszym Sharpe IS
       b. sprawdz jego RANGE wsrod wszystkich wariantow w OOS
       c. policz logit wzglednej rangi
    4. PBO = odsetek kombinacji, w ktorych logit < 0 (czyli ranga ponizej mediany)
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

DEFAULT_N_SPLITS = 8      # S — musi byc parzyste; C(8,4) = 70 kombinacji
PBO_GATE = 0.20           # bramka z rozdz. 1.3


@dataclass(frozen=True)
class PBOResult:
    pbo: float
    n_combinations: int
    n_variants: int
    logits: np.ndarray
    best_is_indices: np.ndarray      # ktory wariant wygral IS w kazdej kombinacji
    oos_ranks: np.ndarray            # jego wzgledna ranga OOS (0..1)

    @property
    def passes(self) -> bool:
        return self.pbo < PBO_GATE

    def __repr__(self) -> str:
        verdict = "PASS" if self.passes else "FAIL"
        return (f"PBOResult(pbo={self.pbo:.3f} [{verdict}, bramka <{PBO_GATE}], "
                f"kombinacji={self.n_combinations}, wariantow={self.n_variants})")


def _sharpe(x: np.ndarray) -> np.ndarray:
    """Sharpe kolumnowo. Kolumny o zerowej wariancji -> 0."""
    mean = x.mean(axis=0)
    std = x.std(axis=0, ddof=1)
    out = np.zeros_like(mean, dtype=float)
    ok = std > 0
    out[ok] = mean[ok] / std[ok]
    return out


def probability_of_backtest_overfitting(
    returns_matrix: np.ndarray,
    *,
    n_splits: int = DEFAULT_N_SPLITS,
) -> PBOResult:
    """PBO metoda CSCV.

    Parametry
    ---------
    returns_matrix : (n_obs, n_variants) — zwroty (np. dzienne) kazdego wariantu.
                     Kolumna = jeden wariant parametryczny hipotezy.
    n_splits       : liczba blokow czasowych S (parzysta). Domyslnie 8 -> 70 kombinacji.

    Uwaga: PBO wymaga >= 2 wariantow. Dla jednego wariantu pojecie "wyboru
    najlepszego" nie istnieje i metryka jest bezprzedmiotowa.
    """
    M = np.asarray(returns_matrix, dtype=float)
    if M.ndim != 2:
        raise ValueError("returns_matrix musi byc macierza (n_obs, n_variants)")
    n_obs, n_var = M.shape
    if n_var < 2:
        raise ValueError(
            "PBO wymaga >= 2 wariantow — przy jednym nie ma czego wybierac. "
            "Pojedynczy wariant oceniaj przez DSR, nie PBO."
        )
    if n_splits % 2 != 0:
        raise ValueError("n_splits musi byc parzyste")
    if n_obs < n_splits * 2:
        raise ValueError(f"za malo obserwacji ({n_obs}) na {n_splits} blokow")

    edges = np.linspace(0, n_obs, n_splits + 1).astype(int)
    blocks = [np.arange(edges[i], edges[i + 1]) for i in range(n_splits)]

    logits: list[float] = []
    best_is: list[int] = []
    ranks: list[float] = []

    half = n_splits // 2
    for is_blocks in combinations(range(n_splits), half):
        oos_blocks = [b for b in range(n_splits) if b not in is_blocks]

        is_idx = np.concatenate([blocks[b] for b in is_blocks])
        oos_idx = np.concatenate([blocks[b] for b in oos_blocks])

        sr_is = _sharpe(M[is_idx])
        sr_oos = _sharpe(M[oos_idx])

        n_star = int(np.argmax(sr_is))          # zwyciezca in-sample
        best_is.append(n_star)

        # Wzgledna ranga zwyciezcy IS wsrod wszystkich wariantow w OOS.
        # rank w [0,1]: 1.0 = najlepszy OOS, 0.0 = najgorszy
        order = np.argsort(sr_oos)
        rank_pos = int(np.where(order == n_star)[0][0])
        rel_rank = (rank_pos + 1) / (n_var + 1)   # (0,1), unika logit(0) i logit(1)
        ranks.append(rel_rank)

        logits.append(float(np.log(rel_rank / (1.0 - rel_rank))))

    logits_arr = np.array(logits)
    pbo = float((logits_arr <= 0).mean())

    return PBOResult(
        pbo=pbo,
        n_combinations=len(logits),
        n_variants=n_var,
        logits=logits_arr,
        best_is_indices=np.array(best_is),
        oos_ranks=np.array(ranks),
    )
