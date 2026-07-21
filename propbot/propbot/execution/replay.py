"""Replay adapter — feed historical candles through the live engine.

Wraps the MockAdapter (paper fills) with a candle cursor: the engine sees only
candles up to `cursor`, exactly as if they were arriving live. SL/TP are
simulated on each advance (the broker would do this in real trading), so a
paper position actually closes when price hits its stop or target.

Used by scripts/replay.py to drive the full Telegram approval flow over past
data — no real orders, no waiting for the NY session.
"""
from __future__ import annotations

from typing import Optional

from ..schema import Candle
from .base import Position
from .mock import MockAdapter


class ReplayAdapter(MockAdapter):
    def __init__(self, symbol: str, candles: list[Candle],
                 point_value_per_lot: float = 1.0,
                 initial_balance: float = 10000.0):
        super().__init__(initial_balance=initial_balance)
        self.symbol = symbol
        self._all = sorted(candles, key=lambda c: c.time)
        self.cursor = 0                      # number of visible (closed) candles
        self.point_value_per_lot = point_value_per_lot

    # --- replay control --------------------------------------------------

    def has_next(self) -> bool:
        return self.cursor < len(self._all)

    def advance(self) -> Optional[Candle]:
        """Reveal the next candle as 'just closed'. Returns it (or None)."""
        if not self.has_next():
            return None
        c = self._all[self.cursor]
        self.cursor += 1
        self.set_candles(self.symbol, "M15", self._all[:self.cursor])
        self.set_price(self.symbol, c.close)
        self.mark_to_market(self.point_value_per_lot)
        return c

    def current_candle(self) -> Optional[Candle]:
        return self._all[self.cursor - 1] if self.cursor > 0 else None

    def check_exits(self) -> list[tuple[int, str, float]]:
        """Close any open position hit by the current candle's range.

        Conservative: if the candle touches BOTH sl and tp, the stop wins.
        Returns [(ticket, reason, pnl), ...] for the caller to report.
        """
        c = self.current_candle()
        if c is None:
            return []
        closed = []
        for pos in list(self._positions.values()):
            long = pos.direction_sign > 0
            hit_sl = c.low <= pos.sl if long else c.high >= pos.sl
            hit_tp = c.high >= pos.tp if long else c.low <= pos.tp
            exit_price = reason = None
            if pos.sl and hit_sl:               # stop wins ambiguous candles
                exit_price, reason = pos.sl, "sl"
            elif pos.tp and hit_tp:
                exit_price, reason = pos.tp, "tp"
            if exit_price is None:
                continue
            balance_before = self.balance
            self.set_price(self.symbol, exit_price)
            self.close_position(pos.ticket, self.point_value_per_lot)
            pnl = self.balance - balance_before
            # restore the candle close as the working price
            self.set_price(self.symbol, c.close)
            self.mark_to_market(self.point_value_per_lot)
            closed.append((pos.ticket, reason, pnl))
        return closed

    # ReplayAdapter's day boundary is driven by the script, but expose a hook
    def start_new_day(self) -> None:
        self.new_day()
