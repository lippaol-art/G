"""High-impact news blackout gate.

The5ers High Stakes: no order EXECUTION from 2 minutes before to 2 minutes
after a high-impact (red folder, per Forex Factory) event. Holding through
news is allowed — so this gate blocks opening, not existing positions.

Events are loaded from a simple JSON file the operator refreshes (manually or
via a calendar export job on the VPS):

    [{"time": "2026-07-21T14:30:00+00:00", "currency": "USD",
      "impact": "high", "title": "CPI y/y"}, ...]

Fail-closed policy: if the calendar file is missing or stale on a trading day,
`is_blackout` can be configured to return True (block) — a missing calendar
must never silently allow news execution.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class NewsEvent:
    time: int              # epoch seconds
    currency: str
    impact: str            # "high" | "medium" | "low"
    title: str = ""


def _parse_time(value) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    dt = datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())


class NewsCalendar:
    def __init__(self, events: list[NewsEvent], loaded_at: int | None = None):
        self.events = sorted(events, key=lambda e: e.time)
        self.loaded_at = loaded_at

    @classmethod
    def from_file(cls, path: str) -> "NewsCalendar":
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        events = [NewsEvent(time=_parse_time(e["time"]),
                            currency=e.get("currency", ""),
                            impact=e.get("impact", "high").lower(),
                            title=e.get("title", ""))
                  for e in raw]
        mtime = int(os.path.getmtime(path))
        return cls(events, loaded_at=mtime)

    def high_impact(self, currencies: set[str] | None = None) -> list[NewsEvent]:
        out = [e for e in self.events if e.impact == "high"]
        if currencies:
            out = [e for e in out if e.currency in currencies]
        return out

    def is_blackout(self, ts: int, window_min: int = 2,
                    currencies: set[str] | None = None) -> tuple[bool, NewsEvent | None]:
        """True when ts falls inside +/- window_min of a high-impact event."""
        w = window_min * 60
        for e in self.high_impact(currencies):
            if e.time - w <= ts <= e.time + w:
                return True, e
        return False, None

    def next_event(self, ts: int,
                  currencies: set[str] | None = None) -> NewsEvent | None:
        for e in self.high_impact(currencies):
            if e.time >= ts:
                return e
        return None

    def is_stale(self, ts: int, max_age_hours: int = 24) -> bool:
        """Calendar older than max_age_hours — treat as unreliable."""
        if self.loaded_at is None:
            return True
        return ts - self.loaded_at > max_age_hours * 3600


def news_gate(calendar: NewsCalendar | None, ts: int, window_min: int = 2,
              currencies: set[str] | None = None,
              fail_closed: bool = True) -> tuple[bool, str]:
    """(allowed, reason). The single entry point the executor calls before
    sending any order. Missing/stale calendar blocks when fail_closed."""
    if calendar is None:
        return (not fail_closed,
                "no news calendar loaded" if fail_closed else "no calendar (fail-open)")
    if calendar.is_stale(ts):
        return (not fail_closed, "news calendar is stale")
    hit, event = calendar.is_blackout(ts, window_min, currencies)
    if hit and event is not None:
        return False, f"news blackout: {event.currency} {event.title}"
    return True, "clear"
