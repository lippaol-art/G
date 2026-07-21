"""Economic calendar helpers.

The blackout gate (market/news.py) consumes a simple JSON list. This module
loads/validates that file and converts a Forex Factory weekly CSV export into
it, so the operator can refresh the calendar without hand-editing JSON.

No network calls here — fetching the FF/investing feed is an ops job on the VPS
(cron a downloader, or export the week manually); this module only normalises
what's on disk. Keeps the trading process free of external HTTP dependencies.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone

from .news import NewsCalendar


def load(path: str) -> NewsCalendar:
    """Load the blackout JSON the executor uses. Raises on a missing file so a
    fail-closed setup surfaces the problem instead of silently trading."""
    return NewsCalendar.from_file(path)


def from_forexfactory_csv(csv_path: str, out_json_path: str,
                          impacts=("High",)) -> int:
    """Convert a Forex Factory weekly CSV export to the blackout JSON.

    FF export columns include: Title, Country, Date, Time, Impact. Times are in
    the exporter's timezone — verify the export is set to UTC (or adjust here).
    Returns the number of high-impact events written.
    """
    wanted = {i.lower() for i in impacts}
    events = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            impact = (row.get("Impact") or "").strip()
            if impact.lower() not in wanted:
                continue
            date = (row.get("Date") or "").strip()
            time = (row.get("Time") or "").strip()
            if not date or time.lower() in ("all day", "tentative", ""):
                continue
            try:
                dt = datetime.strptime(f"{date} {time}", "%m-%d-%Y %I:%M%p")
            except ValueError:
                try:
                    dt = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
                except ValueError:
                    continue
            dt = dt.replace(tzinfo=timezone.utc)
            events.append({
                "time": dt.isoformat(),
                "currency": (row.get("Country") or row.get("Currency") or "").strip(),
                "impact": "high",
                "title": (row.get("Title") or "").strip(),
            })
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
    return len(events)


def validate(path: str, now: int | None = None) -> list[str]:
    """Sanity-check a blackout JSON. Returns a list of problems (empty == ok)."""
    problems: list[str] = []
    try:
        cal = NewsCalendar.from_file(path)
    except Exception as e:
        return [f"cannot load: {e}"]
    now = now or int(datetime.now(tz=timezone.utc).timestamp())
    if cal.is_stale(now):
        problems.append("calendar is stale (>24h old) — refresh it")
    if not cal.high_impact():
        problems.append("no high-impact events — is the export empty?")
    return problems
