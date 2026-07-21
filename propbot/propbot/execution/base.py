"""Execution adapter interface.

Everything above this layer (risk, watcher, telegram) talks to this interface
only — swapping mock -> MT5 -> (later) a futures broker changes nothing else.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from ..schema import AccountState, Candle, OrderIntent, OrderResult


class Position:
    """Broker-side open position snapshot."""
    def __init__(self, ticket: int, symbol: str, volume: float, entry: float,
                 sl: float, tp: float, direction_sign: int, profit: float = 0.0):
        self.ticket = ticket
        self.symbol = symbol
        self.volume = volume
        self.entry = entry
        self.sl = sl
        self.tp = tp
        self.direction_sign = direction_sign
        self.profit = profit


class ExecutionAdapter(ABC):
    @abstractmethod
    def account_state(self) -> AccountState: ...

    @abstractmethod
    def candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]: ...

    @abstractmethod
    def current_price(self, symbol: str, side: str) -> float:
        """side: 'ask' for buys, 'bid' for sells."""

    @abstractmethod
    def send_order(self, intent: OrderIntent) -> OrderResult: ...

    @abstractmethod
    def positions(self) -> list[Position]: ...

    @abstractmethod
    def position_by_ticket(self, ticket: int) -> Optional[Position]: ...

    @abstractmethod
    def close_position(self, ticket: int) -> OrderResult: ...

    def close_all(self) -> list[OrderResult]:
        """Flatten everything — used by the red-zone protocol."""
        return [self.close_position(p.ticket) for p in self.positions()]
