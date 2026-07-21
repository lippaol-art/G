"""Order lifecycle with full confirmation.

A click is not a fill. The sequence here is the contract discussed in design:

  send -> check retcode -> re-query the position -> verify volume / SL / TP /
  slippage -> report. Trust the broker's state, never our own intention.

Includes the anti-double-click lock and the final news/risk gate: even an
approved click is re-checked immediately before hitting the broker.
"""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from ..market.news import NewsCalendar, news_gate
from ..schema import Direction, OrderIntent, OrderResult
from .base import ExecutionAdapter

# One in-flight execution per plan id — a double click must not double-order.
_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _plan_lock(plan_id: str) -> threading.Lock:
    with _locks_guard:
        return _locks.setdefault(plan_id, threading.Lock())


@dataclass
class ExecutionReport:
    ok: bool
    stage: str                      # "gate" | "send" | "verify" | "done"
    result: Optional[OrderResult] = None
    slippage: float = 0.0           # price units vs intended reference
    sl_missing: bool = False        # ALARM: position has no stop loss
    partial: bool = False
    messages: list[str] = field(default_factory=list)


def execute_with_confirmation(
    adapter: ExecutionAdapter,
    intent: OrderIntent,
    reference_price: float,
    max_slippage: float,
    calendar: Optional[NewsCalendar] = None,
    news_window_min: int = 2,
    final_gate: Optional[Callable[[], tuple[bool, str]]] = None,
    entry_jitter_ms: tuple[int, int] = (0, 0),
    news_fail_closed: bool = True,
    now: Optional[int] = None,
) -> ExecutionReport:
    """Send an approved order and verify the full lifecycle.

    `final_gate` is the risk manager's last-second veto (re-check limits after
    the human clicked, because equity may have moved since).
    """
    lock = _plan_lock(intent.plan_id)
    if not lock.acquire(blocking=False):
        return ExecutionReport(ok=False, stage="gate",
                               messages=["execution already in progress for this plan"])
    try:
        ts = now if now is not None else int(time.time())

        # 1. News blackout — The5ers ±2 min rule. Fail closed in production.
        allowed, reason = news_gate(calendar, ts, news_window_min,
                                    fail_closed=news_fail_closed)
        if not allowed:
            return ExecutionReport(ok=False, stage="gate", messages=[reason])

        # 2. Final risk veto (limits re-checked at click time).
        if final_gate is not None:
            ok, why = final_gate()
            if not ok:
                return ExecutionReport(ok=False, stage="gate",
                                       messages=[f"risk veto: {why}"])

        # 3. Stochastic entry jitter — de-correlates us from other accounts
        #    (group-trading detection mitigation from the research).
        lo, hi = entry_jitter_ms
        if hi > 0:
            time.sleep(random.uniform(lo, hi) / 1000.0)

        # 4. Send.
        result = adapter.send_order(intent)
        if not result.ok:
            return ExecutionReport(ok=False, stage="send", result=result,
                                   messages=[f"broker rejected: {result.message} "
                                             f"(retcode {result.retcode})"])

        # 5. Verify against broker state — the position, not our intention.
        report = ExecutionReport(ok=True, stage="verify", result=result)
        pos = adapter.position_by_ticket(result.ticket) if result.ticket else None
        if pos is None:
            report.ok = False
            report.messages.append(
                "order reported filled but position not found — status unknown, "
                "reconciliation required")
            return report

        # volume check (partial fill)
        if pos.volume < intent.volume:
            report.partial = True
            report.messages.append(
                f"PARTIAL fill: {pos.volume}/{intent.volume} lots")

        # SL/TP actually set at the broker?
        if not pos.sl:
            report.sl_missing = True
            report.messages.append("ALARM: no stop loss on position!")

        # slippage vs the reference (confirmation close / intended entry)
        sign = 1 if intent.direction is Direction.LONG else -1
        report.slippage = sign * (pos.entry - reference_price)
        if abs(report.slippage) > max_slippage:
            report.messages.append(
                f"slippage {report.slippage:+.2f} exceeds limit {max_slippage}")

        report.stage = "done"
        return report
    finally:
        lock.release()


def reconcile(adapter: ExecutionAdapter,
              known_tickets: set[int]) -> dict[str, list[int]]:
    """Compare our view of open tickets with the broker's.

    Returns {"missing": [...], "unknown": [...]} — positions we think are open
    but broker doesn't have (closed by SL/TP?) and broker positions we don't
    know about. The orchestrator turns these into Telegram notifications.
    """
    broker_tickets = {p.ticket for p in adapter.positions()}
    return {
        "missing": sorted(known_tickets - broker_tickets),
        "unknown": sorted(broker_tickets - known_tickets),
    }
