"""Moc testu i planowanie wielkosci proby.

Specyfikacja: PLAN.pdf rozdz. 6.4, aneks A.1.

Kluczowe rozroznienie, ktore v1.0 dokumentu przeoczyla:
    N = (1.96 * sigma / E)^2  to rachunek ISTOTNOSCI, nie MOCY.
    Przy tej licznosci wykryjemy prawdziwa przewage tylko w ~50% przypadkow.

Poprawny wzor zawiera czlon z_beta:
    N = ((z_{alpha/2} + z_beta) * sigma_R / E)^2

Dla sigma = 1.2R, E = 0.12R:
    moc 50% -> N ~ 384   (rachunek z v1.0 — NIEWYSTARCZAJACY)
    moc 80% -> N ~ 785   (cel operacyjny)
    moc 90% -> N ~ 1051
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from scipy.stats import norm

# Progi z rozdz. 1.3
FLOOR_TRADES = 400      # podloga bezwzgledna
TARGET_TRADES = 800     # cel operacyjny (moc ~80%)


@dataclass(frozen=True)
class SampleSizeResult:
    n_required: int
    power: float
    alpha: float
    sigma_r: float
    expectancy_r: float

    def verdict(self, n_available: int) -> str:
        if n_available < FLOOR_TRADES:
            return f"PONIZEJ PODLOGI ({n_available} < {FLOOR_TRADES}) — brak wnioskow"
        if n_available < self.n_required:
            return f"ponizej mocy {self.power:.0%} (potrzeba {self.n_required})"
        return f"OK — moc >= {self.power:.0%}"


def required_sample_size(
    expectancy_r: float = 0.12,
    sigma_r: float = 1.2,
    power: float = 0.80,
    alpha: float = 0.05,
) -> SampleSizeResult:
    """Liczba transakcji potrzebna do wykrycia przewagi `expectancy_r`.

        N = ((z_{alpha/2} + z_beta) * sigma_R / E)^2

    UWAGA: sigma_r = 1.2 to ZALOZENIE, nie pomiar. Strategie z dlugim ogonem
    zyskow maja sigma rzedu 1.5-2R, co podnosi wymagane N kilkukrotnie.
    Estymuj sigma empirycznie dla kazdej strategii; ten wzor sluzy PLANOWANIU
    proby, a kryterium decyzyjnym jest bootstrapowy przedzial BCa.
    """
    if expectancy_r <= 0:
        raise ValueError("expectancy_r musi byc dodatnia")
    z_alpha = norm.ppf(1.0 - alpha / 2.0)
    z_beta = norm.ppf(power)
    n = ((z_alpha + z_beta) * sigma_r / expectancy_r) ** 2
    return SampleSizeResult(
        n_required=int(math.ceil(n)),
        power=power,
        alpha=alpha,
        sigma_r=sigma_r,
        expectancy_r=expectancy_r,
    )


def minimum_detectable_effect(
    n: int, sigma_r: float = 1.2, power: float = 0.80, alpha: float = 0.05
) -> float:
    """Najmniejsza przewaga (w R) wykrywalna przy `n` transakcjach.

    Uzywane w sekcji "projekt eksperymentu" karty hipotezy (rozdz. 6.6):
    jesli MDE przekracza realistyczna przewage, hipoteza wraca do
    przeprojektowania ZANIM spali budzet prob.
    """
    if n < 2:
        raise ValueError("n musi byc >= 2")
    z_alpha = norm.ppf(1.0 - alpha / 2.0)
    z_beta = norm.ppf(power)
    return (z_alpha + z_beta) * sigma_r / math.sqrt(n)


def achieved_power(
    n: int, expectancy_r: float = 0.12, sigma_r: float = 1.2, alpha: float = 0.05
) -> float:
    """Moc testu faktycznie osiagnieta przy `n` transakcjach."""
    z_alpha = norm.ppf(1.0 - alpha / 2.0)
    z = expectancy_r * math.sqrt(n) / sigma_r - z_alpha
    return float(norm.cdf(z))
