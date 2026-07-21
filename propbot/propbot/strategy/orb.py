"""Opening Range Breakout (ORB) on index CFDs.

Evidence-backed core strategy (Zarattini/Barbon/Aziz, SSRN 4729284; ~56% WR,
R:R 1.8 on 15-min S&P ORB). Rules are fully deterministic:

  * Opening range = high/low of the first `range_minutes` of the NY session
    (09:30 America/New_York, DST-aware via zoneinfo).
  * LONG plan above the range high, SHORT plan below the range low.
  * Confirmation = M15 candle CLOSE beyond the range edge (handled by the
    watcher, not here).
  * SL = range midpoint (capped at `max_sl_atr` * ATR from entry).
  * TP = `target_r` multiples of the risk.
  * Plans expire at session cutoff — no overnight risk from this strategy.

The LLM does not invent entries. It grades the day (A+/A/B/skip) and its grade
feeds the risk manager's yellow-zone gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence
from zoneinfo import ZoneInfo

from ..schema import Candle, ConfirmationRule, Direction, TradePlan

NY = ZoneInfo("America/New_York")


@dataclass
class ORBConfig:
    range_minutes: int = 30          # opening range window (09:30-10:00 NY)
    session_open_hour: int = 9
    session_open_minute: int = 30
    cutoff_hour: int = 15            # no confirmations after 15:00 NY
    target_r: float = 1.5            # TP = 1.5R
    max_sl_atr: float = 1.5          # SL distance cap in ATR units
    min_range_atr: float = 0.3       # skip degenerate ranges (< 0.3 ATR)
    max_range_atr: float = 3.0       # skip blown-out ranges (> 3 ATR)


@dataclass
class OpeningRange:
    high: float
    low: float
    start_ts: int
    end_ts: int

    @property
    def size(self) -> float:
        return self.high - self.low

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2


def ny_session_open_ts(day_ts: int, cfg: ORBConfig | None = None) -> int:
    """Epoch seconds of the NY session open on the trading day containing day_ts.

    zoneinfo handles EST/EDT, so 09:30 New York is correct year-round.
    """
    cfg = cfg or ORBConfig()
    dt = datetime.fromtimestamp(day_ts, tz=NY)
    open_dt = dt.replace(hour=cfg.session_open_hour, minute=cfg.session_open_minute,
                         second=0, microsecond=0)
    return int(open_dt.timestamp())


def session_cutoff_ts(day_ts: int, cfg: ORBConfig | None = None) -> int:
    cfg = cfg or ORBConfig()
    dt = datetime.fromtimestamp(day_ts, tz=NY)
    cut = dt.replace(hour=cfg.cutoff_hour, minute=0, second=0, microsecond=0)
    return int(cut.timestamp())


def build_opening_range(candles: Sequence[Candle], day_ts: int,
                        cfg: ORBConfig | None = None) -> OpeningRange | None:
    """High/low of candles fully inside the opening window, or None if the
    window isn't fully covered by closed candles yet."""
    cfg = cfg or ORBConfig()
    start = ny_session_open_ts(day_ts, cfg)
    end = start + cfg.range_minutes * 60
    window = [c for c in candles if start <= c.time < end]
    if not window:
        return None
    # require the window to be complete: last candle must close exactly at `end`
    covered = max(c.time for c in window)
    last_len = min((c2.time - c1.time) for c1, c2 in zip(window, window[1:])) \
        if len(window) > 1 else end - covered
    if covered + last_len < end:
        return None
    return OpeningRange(
        high=max(c.high for c in window),
        low=min(c.low for c in window),
        start_ts=start,
        end_ts=end,
    )


def make_orb_plans(symbol: str, orb: OpeningRange, atr_value: float,
                  day_ts: int, cfg: ORBConfig | None = None,
                  grade: str = "B", confidence: float = 0.0,
                  rationale: str = "") -> list[TradePlan]:
    """Long + short conditional plans off the opening range.

    Returns [] when the range is degenerate or blown out relative to ATR
    (both are documented failure modes of ORB).
    """
    cfg = cfg or ORBConfig()
    if atr_value <= 0:
        return []
    r_atr = orb.size / atr_value
    if r_atr < cfg.min_range_atr or r_atr > cfg.max_range_atr:
        return []

    cutoff = session_cutoff_ts(day_ts, cfg)
    plans: list[TradePlan] = []

    for direction in (Direction.LONG, Direction.SHORT):
        if direction is Direction.LONG:
            edge = orb.high
            sl = max(orb.mid, edge - cfg.max_sl_atr * atr_value)
            risk = edge - sl
            tp = edge + cfg.target_r * risk
            confirm = ConfirmationRule("candle_close_above", {"level": edge})
            # Zone straddles the edge: arm as price approaches from below,
            # confirm on a close beyond it.
            zone_low, zone_high = edge - 0.25 * atr_value, edge + 0.5 * atr_value
        else:
            edge = orb.low
            sl = min(orb.mid, edge + cfg.max_sl_atr * atr_value)
            risk = sl - edge
            tp = edge - cfg.target_r * risk
            confirm = ConfirmationRule("candle_close_below", {"level": edge})
            zone_low, zone_high = edge - 0.5 * atr_value, edge + 0.25 * atr_value

        if risk <= 0:
            continue
        plans.append(TradePlan(
            symbol=symbol,
            direction=direction,
            entry_zone_low=zone_low,
            entry_zone_high=zone_high,
            stop_loss=round(sl, 2),
            take_profit=round(tp, 2),
            confirmations=[confirm],
            valid_until=cutoff,
            grade=grade,
            confidence=confidence,
            rationale=rationale or
                f"ORB {direction.value}: range {orb.low:.1f}-{orb.high:.1f} "
                f"({r_atr:.2f} ATR), confirm close beyond {edge:.1f}",
        ))
    return plans
