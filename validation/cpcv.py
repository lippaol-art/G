"""Combinatorial Purged Cross-Validation.

Specyfikacja: PLAN.pdf rozdz. 7.1. Zrodlo: Lopez de Prado, AFML rozdz. 12.

PROBLEM, KTORY ROZWIAZUJE:
    Klasyczny walk-forward generuje JEDNA sciezke OOS — te jedna, ktora historia
    akurat ulozyla. Ocena strategii staje sie przez to wrazliwa na przypadkowa
    kolejnosc rezimow rynkowych: ta sama regula wypadlaby inaczej, gdyby bessa
    2022 przyszla przed hossa AI, a nie po niej.

    CPCV dzieli historie na N spojnych blokow i wybiera k blokow testowych,
    generujac C(N,k) historycznie spojnych sciezek OOS zamiast jednej. Zamiast
    punktowego oszacowania Sharpe'a dostajemy jego ROZKLAD.

ROLA W PROJEKCIE:
    walk-forward -> symulacja realistycznego narastania kapitalu
    CPCV         -> OBOWIAZKOWA bramka przed otwarciem lockboxa + zrodlo PBO
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from math import comb

import numpy as np

DEFAULT_N_BLOCKS = 6
DEFAULT_K_TEST = 2


@dataclass(frozen=True)
class CPCVPath:
    """Jedna sciezka: ktore bloki testowe, ktore treningowe (po purgingu)."""

    test_blocks: tuple[int, ...]
    train_blocks: tuple[int, ...]
    purged_blocks: tuple[int, ...]

    def __repr__(self) -> str:
        return (f"CPCVPath(test={self.test_blocks}, train={self.train_blocks}, "
                f"purged={self.purged_blocks})")


@dataclass(frozen=True)
class CPCVSplit:
    n_blocks: int
    k_test: int
    paths: tuple[CPCVPath, ...]
    block_bounds: tuple[tuple[int, int], ...]   # (start, end) indeksow probek

    @property
    def n_paths(self) -> int:
        return len(self.paths)

    def block_indices(self, block: int) -> range:
        start, end = self.block_bounds[block]
        return range(start, end)


def make_blocks(n_samples: int, n_blocks: int) -> tuple[tuple[int, int], ...]:
    """Dzieli n_samples na n_blocks spojnych, rozlacznych blokow czasowych."""
    if n_blocks < 2:
        raise ValueError("n_blocks musi byc >= 2")
    if n_samples < n_blocks:
        raise ValueError(f"za malo probek ({n_samples}) na {n_blocks} blokow")

    edges = np.linspace(0, n_samples, n_blocks + 1).astype(int)
    return tuple((int(edges[i]), int(edges[i + 1])) for i in range(n_blocks))


def make_cpcv(
    n_samples: int,
    *,
    n_blocks: int = DEFAULT_N_BLOCKS,
    k_test: int = DEFAULT_K_TEST,
    purge_adjacent: bool = True,
) -> CPCVSplit:
    """Buduje wszystkie C(n_blocks, k_test) sciezek.

    Dla domyslnych N=6, k=2 daje 15 sciezek.

    `purge_adjacent`: bloki bezposrednio sasiadujace z testowymi sa USUWANE
    z treningu. Bez tego trening styka sie z testem i autokorelacja przecieka
    przez granice — konstrukcja przestaje byc uczciwa.
    """
    if not 1 <= k_test < n_blocks:
        raise ValueError("k_test musi spelniac 1 <= k_test < n_blocks")

    bounds = make_blocks(n_samples, n_blocks)
    paths: list[CPCVPath] = []

    for test in combinations(range(n_blocks), k_test):
        purged: set[int] = set()
        if purge_adjacent:
            for t in test:
                for nb in (t - 1, t + 1):
                    if 0 <= nb < n_blocks and nb not in test:
                        purged.add(nb)
        train = tuple(
            b for b in range(n_blocks) if b not in test and b not in purged
        )
        paths.append(CPCVPath(tuple(test), train, tuple(sorted(purged))))

    return CPCVSplit(n_blocks, k_test, tuple(paths), bounds)


def expected_n_paths(n_blocks: int = DEFAULT_N_BLOCKS, k_test: int = DEFAULT_K_TEST) -> int:
    """Liczba sciezek = C(n_blocks, k_test). Dla N=6, k=2 -> 15."""
    return comb(n_blocks, k_test)


def path_sharpes(
    returns_by_path: list[np.ndarray], trading_days: int = 252
) -> np.ndarray:
    """Annualizowany Sharpe dla kazdej sciezki OOS.

    Zwraca ROZKLAD, nie punkt — o to w CPCV chodzi. Raport hipotezy podaje
    medianę, rozstep miedzykwartylowy i odsetek sciezek dodatnich.
    """
    out = []
    for r in returns_by_path:
        arr = np.asarray(r, dtype=float)
        if arr.size < 2 or arr.std(ddof=1) == 0:
            out.append(0.0)
            continue
        out.append(float(np.sqrt(trading_days) * arr.mean() / arr.std(ddof=1)))
    return np.array(out)


def summarize_paths(sharpes: np.ndarray) -> dict[str, float]:
    """Podsumowanie rozkladu Sharpe'a po sciezkach CPCV."""
    arr = np.asarray(sharpes, dtype=float)
    if arr.size == 0:
        raise ValueError("brak sciezek do podsumowania")
    return {
        "n_paths": float(arr.size),
        "median": float(np.median(arr)),
        "mean": float(arr.mean()),
        "q25": float(np.percentile(arr, 25)),
        "q75": float(np.percentile(arr, 75)),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "frac_positive": float((arr > 0).mean()),
    }
