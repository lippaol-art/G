"""Mock execution adapter — paper trading & tests.

Deterministic by default; optional slippage simulation for stress-testing the
lifecycle checks. Also drives the backtest runner.
"""
from __future__ import annotations

from typing import Optional

from ..schema import AccountState, Candle, Direction, OrderIntent, OrderResult
from .base import ExecutionAdapter, Position

RETCODE_DONE = 10009        # mirrors mt5.TRADE_RETCODE_DONE
RETCODE_REJECT = 10006


class MockAdapter(ExecutionAdapter):
    def __init__(self, initial_balance: float = 10000.0,
                 slippage_points: float = 0.0,
                 reject_next: bool = False):
        self.balance = initial_balance
        self.initial_balance = initial_balance
        self.equity = initial_balance
        self.day_start_equity = initial_balance
        self.high_water_mark = initial_balance
        self.slippage_points = slippage_points
        self.reject_next = reject_next
        self.drop_sl_next = False       # simulate broker losing the SL
        self.partial_fill_next = 0.0    # if >0, fill only this volume
        self._ticket_seq = 1000
        self._positions: dict[int, Position] = {}
        self._prices: dict[str, float] = {}
        self._candles: dict[tuple[str, str], list[Candle]] = {}
        self.trading_days = 0

    # --- test / backtest wiring -----------------------------------------

    def set_price(self, symbol: str, price: float) -> None:
        self._prices[symbol] = price

    def set_candles(self, symbol: str, timeframe: str,
                    candles: list[Candle]) -> None:
        self._candles[(symbol, timeframe)] = candles

    def mark_to_market(self, point_value_per_lot: float = 1.0) -> None:
        """Recompute equity from open positions at current prices."""
        pnl = 0.0
        for p in self._positions.values():
            price = self._prices.get(p.symbol, p.entry)
            pnl += (price - p.entry) * p.direction_sign * p.volume \
                * point_value_per_lot
            p.profit = pnl
        self.equity = self.balance + pnl
        if self.equity > self.high_water_mark:
            self.high_water_mark = self.equity

    # --- adapter interface ----------------------------------------------

    def account_state(self) -> AccountState:
        return AccountState(
            balance=self.balance,
            equity=self.equity,
            day_start_equity=self.day_start_equity,
            initial_balance=self.initial_balance,
            high_water_mark=self.high_water_mark,
            open_positions=len(self._positions),
            trading_days=self.trading_days,
        )

    def candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        data = self._candles.get((symbol, timeframe), [])
        return data[-count:]

    def current_price(self, symbol: str, side: str) -> float:
        return self._prices.get(symbol, 0.0)

    def send_order(self, intent: OrderIntent) -> OrderResult:
        if self.reject_next:
            self.reject_next = False
            return OrderResult(ok=False, retcode=RETCODE_REJECT,
                               requested_volume=intent.volume,
                               message="requote")
        price = self._prices.get(intent.symbol, 0.0)
        sign = intent.direction.sign
        fill_price = price + sign * self.slippage_points
        volume = intent.volume
        if self.partial_fill_next > 0:
            volume = min(volume, self.partial_fill_next)
            self.partial_fill_next = 0.0
        self._ticket_seq += 1
        sl = 0.0 if self.drop_sl_next else intent.stop_loss
        self.drop_sl_next = False
        self._positions[self._ticket_seq] = Position(
            ticket=self._ticket_seq, symbol=intent.symbol, volume=volume,
            entry=fill_price, sl=sl, tp=intent.take_profit,
            direction_sign=sign,
        )
        return OrderResult(ok=True, retcode=RETCODE_DONE,
                           ticket=self._ticket_seq, fill_price=fill_price,
                           filled_volume=volume,
                           requested_volume=intent.volume)

    def positions(self) -> list[Position]:
        return list(self._positions.values())

    def position_by_ticket(self, ticket: int) -> Optional[Position]:
        return self._positions.get(ticket)

    def close_position(self, ticket: int,
                       point_value_per_lot: float = 1.0) -> OrderResult:
        pos = self._positions.pop(ticket, None)
        if pos is None:
            return OrderResult(ok=False, retcode=RETCODE_REJECT,
                               message="position not found")
        price = self._prices.get(pos.symbol, pos.entry)
        pnl = (price - pos.entry) * pos.direction_sign * pos.volume \
            * point_value_per_lot
        self.balance += pnl
        self.mark_to_market(point_value_per_lot)
        return OrderResult(ok=True, retcode=RETCODE_DONE, ticket=ticket,
                           fill_price=price, filled_volume=pos.volume,
                           requested_volume=pos.volume,
                           message=f"closed pnl={pnl:+.2f}")

    def new_day(self) -> None:
        self.day_start_equity = self.equity
        self.trading_days += 1
