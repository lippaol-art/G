"""Analysis pack builder.

Bundles everything the LLM needs to grade the trading day into one JSON-
serialisable dict. Sent to the Claude API by client.py (or pasted manually in
the /plan fallback mode). Keeping it a plain dict = auditable + testable.
"""
from __future__ import annotations

import json
from typing import Sequence

from ..market.indicators import atr, closes, ema, rsi
from ..market.news import NewsCalendar
from ..schema import AccountState, Candle
from ..strategy.orb import OpeningRange


def _candles_brief(candles: Sequence[Candle], keep: int) -> list[dict]:
    return [
        {"t": c.time, "o": c.open, "h": c.high, "l": c.low, "c": c.close}
        for c in candles[-keep:]
    ]


def build_analysis_pack(symbol: str,
                        m15: Sequence[Candle],
                        h1: Sequence[Candle],
                        d1: Sequence[Candle],
                        acct: AccountState,
                        risk_zone: str,
                        orb: OpeningRange | None = None,
                        calendar: NewsCalendar | None = None,
                        now: int = 0) -> dict:
    """One dict with market context, account state and today's constraints."""
    m15_closes = closes(m15)
    h1_closes = closes(h1)
    d1_closes = closes(d1)

    news_today: list[dict] = []
    if calendar is not None:
        news_today = [
            {"time": e.time, "currency": e.currency, "title": e.title}
            for e in calendar.high_impact({"USD"})
            if now <= e.time <= now + 24 * 3600
        ]

    pack: dict = {
        "symbol": symbol,
        "now": now,
        "market": {
            "m15_candles": _candles_brief(m15, 40),
            "h1_candles": _candles_brief(h1, 24),
            "d1_candles": _candles_brief(d1, 10),
            "indicators": {
                "atr14_m15": atr(m15, 14),
                "rsi14_m15": rsi(m15_closes, 14),
                "ema20_h1": ema(h1_closes, 20),
                "ema50_h1": ema(h1_closes, 50),
                "rsi14_h1": rsi(h1_closes, 14),
                "ema20_d1": ema(d1_closes, 20),
            },
            "prev_day": {
                "high": d1[-2].high if len(d1) >= 2 else None,
                "low": d1[-2].low if len(d1) >= 2 else None,
                "close": d1[-2].close if len(d1) >= 2 else None,
            },
        },
        "opening_range": None if orb is None else {
            "high": orb.high, "low": orb.low, "size": orb.size,
            "start_ts": orb.start_ts, "end_ts": orb.end_ts,
        },
        "news_today_usd_high_impact": news_today,
        "account": {
            "equity": acct.equity,
            "day_pnl_pct": round(acct.day_pnl_pct, 5),
            "risk_zone": risk_zone,
            "open_positions": acct.open_positions,
        },
    }
    return pack


def pack_to_json(pack: dict) -> str:
    return json.dumps(pack, indent=2)
