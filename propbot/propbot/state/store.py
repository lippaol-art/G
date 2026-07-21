"""Durable plan store.

Plans must survive process restarts and container recycling: a setup can sit in
ARMED for hours. This is a simple, atomic JSON-file store keyed by plan id.
Swap for SQLite/Redis in production; the interface stays the same.
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Iterable

from ..schema import SetupState, TradePlan
from .machine import TERMINAL


class PlanStore:
    def __init__(self, path: str):
        self.path = path
        self._plans: dict[str, TradePlan] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        self._plans = {pid: TradePlan.from_dict(d) for pid, d in raw.items()}

    def _flush(self) -> None:
        """Atomic write: temp file + rename, so a crash never truncates state."""
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        data = {pid: p.to_dict() for pid, p in self._plans.items()}
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(self.path) or ".",
                                   suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    # --- CRUD -------------------------------------------------------------

    def upsert(self, plan: TradePlan) -> None:
        self._plans[plan.id] = plan
        self._flush()

    def get(self, plan_id: str) -> TradePlan | None:
        return self._plans.get(plan_id)

    def all(self) -> list[TradePlan]:
        return list(self._plans.values())

    def active(self) -> list[TradePlan]:
        """Plans the watcher still needs to look at."""
        return [p for p in self._plans.values() if p.state not in TERMINAL]

    def by_state(self, *states: SetupState) -> list[TradePlan]:
        wanted = set(states)
        return [p for p in self._plans.values() if p.state in wanted]

    def open_positions(self) -> list[TradePlan]:
        return self.by_state(SetupState.OPEN)

    def prune_terminal(self, keep_last: int = 200) -> None:
        """Trim old terminal plans so the file doesn't grow forever."""
        terminal = sorted(
            (p for p in self._plans.values() if p.state in TERMINAL),
            key=lambda p: p.created_at,
        )
        excess = len(terminal) - keep_last
        for p in terminal[:max(0, excess)]:
            del self._plans[p.id]
        self._flush()
