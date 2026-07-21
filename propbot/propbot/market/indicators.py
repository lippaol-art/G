"""Small, dependency-free technical indicators used by the watcher.

Deterministic and cheap: these run on every closed candle, so they must not
call the LLM or the network.
"""
from __future__ import annotations

from typing import Sequence

from ..schema import Candle


def sma(values: Sequence[float], period: int) -> float | None:
    if len(values) < period or period <= 0:
        return None
    return sum(values[-period:]) / period


def ema(values: Sequence[float], period: int) -> float | None:
    if len(values) < period or period <= 0:
        return None
    k = 2 / (period + 1)
    # seed with SMA of the first `period` values, then walk forward
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def rsi(values: Sequence[float], period: int = 14) -> float | None:
    if len(values) < period + 1:
        return None
    gains, losses = 0.0, 0.0
    # initial average over the first `period` deltas
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        gains += max(delta, 0.0)
        losses += max(-delta, 0.0)
    avg_gain, avg_loss = gains / period, losses / period
    # Wilder smoothing for the rest
    for i in range(period + 1, len(values)):
        delta = values[i] - values[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(delta, 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-delta, 0.0)) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1 + rs)


def atr(candles: Sequence[Candle], period: int = 14) -> float | None:
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        c, p = candles[i], candles[i - 1]
        trs.append(max(
            c.high - c.low,
            abs(c.high - p.close),
            abs(c.low - p.close),
        ))
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def closes(candles: Sequence[Candle]) -> list[float]:
    return [c.close for c in candles]
