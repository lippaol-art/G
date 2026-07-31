"""Cechy pochodne od ceny — PLAN.pdf rozdz. 4.3, 5.2.

ZASADA NADRZEDNA (rozdz. 4.3):
    Poziomy referencyjne siegajace WSTECZ POZA BIEZACA SESJE (PDH, PDL, PDC)
    licza sie WYLACZNIE na cenach surowych. Na serii skorygowanej rozjezdzaja
    sie w dniach rolowan, generujac sygnaly wejscia na poziomach, ktorych nikt
    nigdy nie widzial na tablicy.

    Wielkosci wewnatrzsesyjne (VWAP, zakres dnia, ATR) sa niewrazliwe na stale
    przesuniecie back-adjustu, bo mieszcza sie w calosci w jednym kontrakcie.

Wszystkie funkcje przyjmuja WYLACZNIE dane historyczne — brak dostepu do
przyszlosci jest gwarantowany przez `HistoryView` z engine/guards.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from engine.guards import assert_raw_series


@dataclass(frozen=True)
class DayLevels:
    """Poziomy referencyjne poprzedniej sesji — liczone na cenach surowych."""

    pdh: float      # previous day high
    pdl: float      # previous day low
    pdc: float      # previous day close
    series_kind: str = "raw"


def true_range(high: float, low: float, prev_close: float) -> float:
    return max(high - low, abs(high - prev_close), abs(low - prev_close))


def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, n: int = 14) -> float:
    """Average True Range z ostatnich n barow.

    Uzywany wylacznie jako miara REZIMU (przez percentyl), nie jako sygnal —
    wskaznik nie jest przewaga, jest miernikiem (rozdz. 2.1).
    """
    h = np.asarray(highs, dtype=float)
    low_arr = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    if h.size < 2:
        return 0.0

    k = min(n, h.size - 1)
    trs = [true_range(h[i], low_arr[i], c[i - 1]) for i in range(h.size - k, h.size)]
    return float(np.mean(trs)) if trs else 0.0


def vwap(prices: np.ndarray, volumes: np.ndarray) -> float:
    """VWAP sesyjny.

    Niewrazliwy na back-adjust: caly liczony w obrebie jednej sesji, wiec stale
    przesuniecie przesuwa i ceny, i VWAP o tyle samo.
    """
    p = np.asarray(prices, dtype=float)
    v = np.asarray(volumes, dtype=float)
    if p.size == 0 or v.sum() == 0:
        return float(p[-1]) if p.size else 0.0
    return float((p * v).sum() / v.sum())


def vwap_sigma(prices: np.ndarray, volumes: np.ndarray) -> float:
    """Odchylenie standardowe ceny wokol VWAP, wazone wolumenem.

    Jednostka progow w H002: odchylenie mierzone w sigma sesji, nie w punktach —
    inaczej prog nie byloby porownywalny miedzy dniami o roznej zmiennosci.
    """
    p = np.asarray(prices, dtype=float)
    v = np.asarray(volumes, dtype=float)
    if p.size < 2 or v.sum() == 0:
        return 0.0
    m = vwap(p, v)
    war = float((v * (p - m) ** 2).sum() / v.sum())
    return float(np.sqrt(max(war, 0.0)))


def rolling_percentile(series: np.ndarray, value: float, window: int = 60) -> float:
    """Percentyl `value` w ostatnich `window` obserwacjach (0-100).

    Podstawa wszystkich definicji rezimu w projekcie — wlasne definicje
    operacyjne zamiast progow z podrecznika (rozdz. 8.4).
    """
    s = np.asarray(series, dtype=float)
    if s.size == 0:
        return 50.0
    okno = s[-window:] if s.size > window else s
    return float((okno < value).mean() * 100.0)


def overnight_range(highs: np.ndarray, lows: np.ndarray) -> float:
    """Zakres sesji nocnej (18:00-09:30 ET). Wielkosc wewnatrzdobowa."""
    h = np.asarray(highs, dtype=float)
    low_arr = np.asarray(lows, dtype=float)
    if h.size == 0:
        return 0.0
    return float(h.max() - low_arr.min())


def prev_day_levels(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    *,
    series_kind: str = "raw",
) -> DayLevels:
    """Poziomy poprzedniej sesji.

    WYMAGA serii surowej — `assert_raw_series` blokuje wywolanie na cenach
    skorygowanych. To nie jest ostrzezenie w dokumentacji, tylko wyjatek
    w czasie wykonania (rozdz. 4.3).
    """
    assert_raw_series(series_kind, what="poziomy PDH/PDL/PDC")

    h = np.asarray(highs, dtype=float)
    low_arr = np.asarray(lows, dtype=float)
    c = np.asarray(closes, dtype=float)
    if h.size == 0:
        raise ValueError("brak danych poprzedniej sesji")

    return DayLevels(float(h.max()), float(low_arr.min()), float(c[-1]), series_kind)


def initial_balance(highs: np.ndarray, lows: np.ndarray) -> tuple[float, float]:
    """Zakres pierwszych minut RTH (initial balance). Zwraca (high, low)."""
    h = np.asarray(highs, dtype=float)
    low_arr = np.asarray(lows, dtype=float)
    if h.size == 0:
        raise ValueError("brak barow initial balance")
    return float(h.max()), float(low_arr.min())


def atr_regime_ratio(atr_short: float, atr_long: float) -> float:
    """Wlasne proxy rezimu zmiennosci: ATR krotki / ATR dlugi (H010).

    Mierzy zmiennosc zrealizowana WZGLEDEM oczekiwan zbudowanych z samych cen,
    zamiast siegac po zewnetrzny indeks zmiennosci.
    """
    if atr_long <= 0:
        return 1.0
    return float(atr_short / atr_long)
