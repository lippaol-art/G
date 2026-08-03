"""Test SPA Hansena — Superior Predictive Ability.

Specyfikacja: PLAN.pdf rozdz. 7.2.
Zrodla: Hansen, "A Test for Superior Predictive Ability", JBES 2005;
        White, "A Reality Check for Data Snooping", Econometrica 2000.

PYTANIE, NA KTORE ODPOWIADA:
    Czy NAJLEPSZY wariant z calej puli bije benchmark zerowy PO UWZGLEDNIENIU
    tego, ze wybieralismy najlepszego z wielu?

    To nie to samo co DSR (ktory patrzy na pojedynczy SR wzgledem liczby prob)
    ani PBO (ktory mierzy stabilnosc rankingu IS->OOS). SPA testuje hipoteze
    zerowa "zaden wariant nie ma przewagi" na calej puli naraz, bootstrapem
    stacjonarnym po szeregach wszystkich wariantow.

SPA vs Reality Check White'a:
    SPA ma wieksza moc dzieki studentyzacji i mniejsza wrazliwosc na obecnosc
    slabych wariantow w puli. RC potrafi zostac "rozcienczony" przez dosypanie
    beznadziejnych wariantow — SPA nie.

IMPLEMENTACJA:
    Preferowana: `arch.bootstrap.SPA` (dojrzala, przetestowana).
    Fallback wlasny: bootstrap stacjonarny, gdy `arch` niedostepny — z jawna
    informacja w wyniku, ktora sciezka zostala uzyta.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

DEFAULT_N_BOOTSTRAP = 1_000
DEFAULT_BLOCK_SIZE = 10
ALPHA = 0.05


@dataclass(frozen=True)
class SPAResult:
    pvalue: float
    best_variant: int
    best_mean: float
    n_variants: int
    implementation: str      # "arch" albo "fallback_stationary_bootstrap"

    @property
    def passes(self) -> bool:
        """Odrzucenie H0 przy alfa 0.05 = najlepszy wariant bije zero."""
        return self.pvalue < ALPHA

    def __repr__(self) -> str:
        verdict = "PASS" if self.passes else "FAIL"
        return (f"SPAResult(p={self.pvalue:.4f} [{verdict}], wariant={self.best_variant}, "
                f"impl={self.implementation})")


def _stationary_bootstrap_indices(
    n: int, block_size: float, rng: np.random.Generator
) -> np.ndarray:
    """Indeksy bootstrapu stacjonarnego (Politis & Romano).

    Dlugosc bloku ~ geometryczna(1/block_size), zawijanie cykliczne.
    Zachowuje zaleznosc szeregowa, ktorej zwykly bootstrap iid nie widzi.
    """
    p = 1.0 / max(block_size, 1.0)
    idx = np.empty(n, dtype=int)
    i = 0
    while i < n:
        start = int(rng.integers(0, n))
        length = min(max(1, int(rng.geometric(p))), n - i)
        idx[i:i + length] = (np.arange(start, start + length)) % n
        i += length
    return idx


def _spa_fallback(
    losses: np.ndarray, n_bootstrap: int, block_size: float, seed: int
) -> tuple[float, int, float]:
    """Wlasna implementacja SPA — uzywana, gdy `arch` niedostepny.

    `losses` : (n_obs, n_variants) — zwroty wariantow (dodatnie = lepiej niz benchmark).
    Statystyka: max_k sqrt(n) * mean_k / std_k, studentyzowana, z rekcentrowaniem
    wg Hansena (odejmowanie sredniej tylko dla wariantow "nieistotnie zlych").
    """
    rng = np.random.default_rng(seed)
    n, k = losses.shape

    means = losses.mean(axis=0)
    stds = losses.std(axis=0, ddof=1)
    stds = np.where(stds > 0, stds, np.inf)

    t_stats = np.sqrt(n) * means / stds
    t_max = float(np.max(t_stats))
    best = int(np.argmax(t_stats))

    # Rekcentrowanie Hansena: warianty istotnie gorsze od zera nie podnosza progu.
    threshold = -np.sqrt(2.0 * np.log(np.log(max(n, 3))))
    recenter = np.where(t_stats >= threshold, means, 0.0)

    boot_max = np.empty(n_bootstrap)
    for b in range(n_bootstrap):
        idx = _stationary_bootstrap_indices(n, block_size, rng)
        sample = losses[idx]
        bm = sample.mean(axis=0) - recenter
        bs = sample.std(axis=0, ddof=1)
        bs = np.where(bs > 0, bs, np.inf)
        boot_max[b] = np.max(np.sqrt(n) * bm / bs)

    pvalue = float((1 + np.sum(boot_max >= t_max)) / (1 + n_bootstrap))
    return pvalue, best, float(means[best])


def superior_predictive_ability(
    returns_matrix: np.ndarray,
    *,
    n_bootstrap: int = DEFAULT_N_BOOTSTRAP,
    block_size: float = DEFAULT_BLOCK_SIZE,
    seed: int = 0,
    force_fallback: bool = False,
) -> SPAResult:
    """Test SPA Hansena na puli wariantow.

    Parametry
    ---------
    returns_matrix : (n_obs, n_variants) — zwroty kazdego wariantu wzgledem
                     benchmarku zerowego (dla nas: same zwroty strategii).
    force_fallback : wymusza wlasna implementacje (uzywane w testach porownawczych).

    Zwraca p-wartosc dla H0: "zaden wariant nie ma dodatniej przewagi".
    """
    M = np.asarray(returns_matrix, dtype=float)
    if M.ndim != 2:
        raise ValueError("returns_matrix musi byc macierza (n_obs, n_variants)")
    if M.shape[0] < 20:
        raise ValueError("potrzeba >= 20 obserwacji")
    if M.shape[1] < 1:
        raise ValueError("potrzeba >= 1 wariantu")

    if not force_fallback:
        try:
            from arch.bootstrap import SPA

            # ZNAK. `arch.bootstrap.SPA` operuje na STRATACH — mniej znaczy
            # lepiej — a jego H0 brzmi "benchmark nie jest gorszy od zadnego
            # modelu". Nasze `returns_matrix` to ZWROTY, wiec trzeba je
            # odwrocic. Bez tego minusa testowana jest hipoteza PRZECIWNA do
            # zamierzonej i wynik jest gorszy niz bezuzyteczny, bo wyglada
            # wiarygodnie: pula z przewaga 1 sigma (t~20) dawala p=0.898,
            # a pula, w ktorej KAZDY wariant traci — p=0.000.
            #
            # Blad przezyl 233 testy, bo kazdy z nich wolal te funkcje
            # z `force_fallback=True`. Sciezka domyslna nie byla testowana
            # w ogole. Wykryl to dopiero golden baseline, ktory zapisal obie
            # sciezki obok siebie i pokazal, ze `arch` zwraca identyczne
            # p=0.898 dla szumu i dla realnej przewagi.
            straty = -M
            benchmark = np.zeros(M.shape[0])
            spa = SPA(benchmark, straty, reps=n_bootstrap,
                      block_size=int(block_size), seed=seed)
            spa.compute()
            means = M.mean(axis=0)
            best = int(np.argmax(means))
            return SPAResult(
                pvalue=float(spa.pvalues["consistent"]),
                best_variant=best,
                best_mean=float(means[best]),
                n_variants=M.shape[1],
                implementation="arch",
            )
        except ImportError:
            pass

    p, best, mean = _spa_fallback(M, n_bootstrap, block_size, seed)
    return SPAResult(p, best, mean, M.shape[1], "fallback_stationary_bootstrap")
