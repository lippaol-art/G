"""Opening Range Breakout (ORB) on index CFDs.

Evidence-backed core strategy (Zarattini/Barbon/Aziz, SSRN 4729284; ~56% WR,
R:R 1.8 on 15-min S&P ORB). Rules are fully deterministic:

  * Opening range = high/low of the first `range_minutes` of the US cash
    session, measured on the BROKER SERVER CLOCK (see below).
  * LONG plan above the range high, SHORT plan below the range low.
  * Confirmation = M15 candle CLOSE beyond the range edge (handled by the
    watcher, not here).
  * SL = range midpoint (capped at `max_sl_atr` * ATR from entry).
  * TP = `target_r` multiples of the risk.
  * Plans expire at session cutoff — no overnight risk from this strategy.

Clock note (important): MetaTrader stamps every candle with the *broker's
server wall-clock* (typically GMT+2/+3), stored as a Unix timestamp with NO
offset — so `datetime.fromtimestamp(t, tz=utc)` on an MT5 candle yields the
server wall-clock, not real UTC. On such a feed the US cash open (New York
09:30) lands at server 16:30 year-round: both the US and the EU shift DST, so
the New-York-to-server gap stays a constant 7h. We therefore locate the
opening range by the server clock (default 16:30 open, 22:00 cutoff, tz=UTC)
rather than converting through America/New_York — which would land in the
wrong window and skip every day. Brokers on a different server offset can
override the hours via config (market.session_* in settings.yaml).

The LLM does not invent entries. It grades the day (A+/A/B/skip) and its grade
feeds the risk manager's yellow-zone gate.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence
from zoneinfo import ZoneInfo

from ..schema import Candle, ConfirmationRule, Direction, TradePlan


@dataclass
class ORBConfig:
    range_minutes: int = 30          # opening range window (server 16:30-17:00)
    # Session times are on the broker server clock (see module docstring).
    # Defaults suit a GMT+2/+3 MT5 feed where the US open is server 16:30.
    session_open_hour: int = 16
    session_open_minute: int = 30
    cutoff_hour: int = 22            # no confirmations after server 22:00
    session_tz: str = "UTC"          # how candle timestamps are interpreted
    target_r: float = 1.5            # TP = 1.5R
    max_sl_atr: float = 1.5          # SL distance cap in ATR units
    min_range_atr: float = 0.3       # skip degenerate ranges (< 0.3 ATR)
    max_range_atr: float = 3.0       # skip blown-out ranges (> 3 ATR)

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.session_tz)


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


def session_open_ts(day_ts: int, cfg: ORBConfig | None = None) -> int:
    """Epoch seconds of the session open on the trading day containing day_ts.

    Interpreted on the broker server clock (cfg.tz, default UTC = how MT5
    stamps candles). Default hour/minute = 16:30, the US cash open on a
    GMT+2/+3 feed. See the module docstring for why this is not a NY
    conversion.
    """
    cfg = cfg or ORBConfig()
    dt = datetime.fromtimestamp(day_ts, tz=cfg.tz)
    open_dt = dt.replace(hour=cfg.session_open_hour, minute=cfg.session_open_minute,
                         second=0, microsecond=0)
    return int(open_dt.timestamp())


# Backwards-compatible alias: the session clock is no longer NY-based, but
# callers/tests written before the fix still import this name.
ny_session_open_ts = session_open_ts


def session_cutoff_ts(day_ts: int, cfg: ORBConfig | None = None) -> int:
    cfg = cfg or ORBConfig()
    dt = datetime.fromtimestamp(day_ts, tz=cfg.tz)
    cut = dt.replace(hour=cfg.cutoff_hour, minute=0, second=0, microsecond=0)
    return int(cut.timestamp())


def build_opening_range(candles: Sequence[Candle], day_ts: int,
                        cfg: ORBConfig | None = None) -> OpeningRange | None:
    """High/low of candles fully inside the opening window, or None if the
    window isn't fully covered by closed candles yet."""
    cfg = cfg or ORBConfig()
    start = session_open_ts(day_ts, cfg)
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
