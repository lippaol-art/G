"""MetaTrader 5 execution adapter (real / demo account on the Windows VPS).

Import-guarded: the MetaTrader5 package only exists on Windows, so the core
suite and backtests never touch this module. All order-lifecycle verification
lives in lifecycle.py and is shared with the mock adapter.
"""
from __future__ import annotations

from typing import Optional

from ..schema import AccountState, Candle, Direction, OrderIntent, OrderResult
from .base import ExecutionAdapter, Position

try:
    import MetaTrader5 as mt5
    HAS_MT5 = True
except ImportError:
    mt5 = None  # type: ignore[assignment]
    HAS_MT5 = False

_TIMEFRAMES = {}
if HAS_MT5:
    _TIMEFRAMES = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }


class MT5Adapter(ExecutionAdapter):
    def __init__(self, magic: int, deviation_points: int = 15,
                 initial_balance: float = 10000.0,
                 day_start_equity: Optional[float] = None,
                 high_water_mark: Optional[float] = None):
        if not HAS_MT5:
            raise RuntimeError("MetaTrader5 package not available "
                               "(Windows + installed terminal required)")
        if not mt5.initialize():
            raise ConnectionError(f"MT5 initialize failed: {mt5.last_error()}")
        self.magic = magic
        self.deviation_points = deviation_points
        self.initial_balance = initial_balance
        acct = mt5.account_info()
        self._day_start_equity = day_start_equity if day_start_equity is not None \
            else (acct.equity if acct else initial_balance)
        self._high_water_mark = high_water_mark if high_water_mark is not None \
            else (acct.equity if acct else initial_balance)

    def shutdown(self) -> None:
        mt5.shutdown()

    # --- adapter interface ----------------------------------------------

    def account_state(self) -> AccountState:
        acct = mt5.account_info()
        if acct is None:
            raise ConnectionError("MT5 account_info unavailable")
        if acct.equity > self._high_water_mark:
            self._high_water_mark = acct.equity
        return AccountState(
            balance=acct.balance,
            equity=acct.equity,
            day_start_equity=self._day_start_equity,
            initial_balance=self.initial_balance,
            high_water_mark=self._high_water_mark,
            open_positions=len(self.positions()),
        )

    def new_day(self) -> None:
        """Call at broker-server midnight — resets the daily-loss reference."""
        acct = mt5.account_info()
        if acct is not None:
            self._day_start_equity = acct.equity

    def candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        rates = mt5.copy_rates_from_pos(symbol, _TIMEFRAMES[timeframe], 0, count)
        if rates is None:
            return []
        out = [Candle(time=int(r["time"]), open=float(r["open"]),
                      high=float(r["high"]), low=float(r["low"]),
                      close=float(r["close"]),
                      volume=float(r["tick_volume"])) for r in rates]
        # drop the still-forming candle: watcher wants closed candles only
        return out[:-1] if out else out

    def current_price(self, symbol: str, side: str) -> float:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise ConnectionError(f"no tick for {symbol}")
        return tick.ask if side == "ask" else tick.bid

    def send_order(self, intent: OrderIntent) -> OrderResult:
        side = "ask" if intent.direction is Direction.LONG else "bid"
        price = self.current_price(intent.symbol, side)
        order_type = mt5.ORDER_TYPE_BUY if intent.direction is Direction.LONG \
            else mt5.ORDER_TYPE_SELL
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": intent.symbol,
            "volume": float(intent.volume),
            "type": order_type,
            "price": float(price),
            "sl": float(intent.stop_loss),
            "tp": float(intent.take_profit),
            "deviation": self.deviation_points,
            "magic": self.magic,
            "comment": intent.comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None:
            return OrderResult(ok=False, retcode=-1,
                               requested_volume=intent.volume,
                               message=f"order_send returned None: {mt5.last_error()}")
        ok = result.retcode == mt5.TRADE_RETCODE_DONE
        return OrderResult(
            ok=ok, retcode=result.retcode,
            ticket=getattr(result, "order", None) if ok else None,
            fill_price=getattr(result, "price", None),
            filled_volume=getattr(result, "volume", 0.0),
            requested_volume=intent.volume,
            message=getattr(result, "comment", ""),
        )

    def positions(self) -> list[Position]:
        raw = mt5.positions_get()
        if raw is None:
            return []
        out = []
        for p in raw:
            if p.magic != self.magic:
                continue  # not ours — never touch other positions
            sign = 1 if p.type == mt5.POSITION_TYPE_BUY else -1
            out.append(Position(ticket=p.ticket, symbol=p.symbol,
                                volume=p.volume, entry=p.price_open,
                                sl=p.sl, tp=p.tp, direction_sign=sign,
                                profit=p.profit))
        return out

    def position_by_ticket(self, ticket: int) -> Optional[Position]:
        raw = mt5.positions_get(ticket=ticket)
        if not raw:
            return None
        p = raw[0]
        sign = 1 if p.type == mt5.POSITION_TYPE_BUY else -1
        return Position(ticket=p.ticket, symbol=p.symbol, volume=p.volume,
                        entry=p.price_open, sl=p.sl, tp=p.tp,
                        direction_sign=sign, profit=p.profit)

    def close_position(self, ticket: int) -> OrderResult:
        pos = self.position_by_ticket(ticket)
        if pos is None:
            return OrderResult(ok=False, retcode=-1, message="position not found")
        is_long = pos.direction_sign > 0
        side = "bid" if is_long else "ask"
        price = self.current_price(pos.symbol, side)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": mt5.ORDER_TYPE_SELL if is_long else mt5.ORDER_TYPE_BUY,
            "position": ticket,
            "price": float(price),
            "deviation": self.deviation_points,
            "magic": self.magic,
            "comment": "propbot close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        ok = result is not None and result.retcode == mt5.TRADE_RETCODE_DONE
        return OrderResult(ok=ok,
                           retcode=result.retcode if result else -1,
                           ticket=ticket,
                           message=getattr(result, "comment", "") if result else "")
