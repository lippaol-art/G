"""Setup lifecycle state machine.

A TradePlan moves through explicit states. Only whitelisted transitions are
allowed, and every transition is appended to the plan's history so the whole
decision trail is auditable (important for prop-firm code reviews).
"""
from __future__ import annotations

import time

from ..schema import SetupState, TradePlan


class InvalidTransition(Exception):
    pass


# Allowed transitions. Anything not listed here is rejected.
TRANSITIONS: dict[SetupState, set[SetupState]] = {
    SetupState.WAITING_FOR_PRICE: {
        SetupState.ARMED,
        SetupState.EXPIRED,
        SetupState.INVALIDATED,
        SetupState.CANCELLED,
    },
    SetupState.ARMED: {
        SetupState.CONFIRMED,
        SetupState.WAITING_FOR_PRICE,   # price left the zone again
        SetupState.EXPIRED,
        SetupState.INVALIDATED,
        SetupState.CANCELLED,
    },
    SetupState.CONFIRMED: {
        SetupState.EXECUTING,
        SetupState.CANCELLED,           # human pressed cancel / risk veto
        SetupState.EXPIRED,
        SetupState.INVALIDATED,
    },
    SetupState.EXECUTING: {
        SetupState.OPEN,
        SetupState.CANCELLED,           # broker rejected
    },
    SetupState.OPEN: {
        SetupState.CLOSED,
    },
    # terminal states
    SetupState.CLOSED: set(),
    SetupState.EXPIRED: set(),
    SetupState.INVALIDATED: set(),
    SetupState.CANCELLED: set(),
}

TERMINAL = {
    SetupState.CLOSED,
    SetupState.EXPIRED,
    SetupState.INVALIDATED,
    SetupState.CANCELLED,
}


class StateMachine:
    @staticmethod
    def can(src: SetupState, dst: SetupState) -> bool:
        return dst in TRANSITIONS.get(src, set())

    @staticmethod
    def transition(plan: TradePlan, dst: SetupState, reason: str = "",
                  now: int | None = None) -> TradePlan:
        src = plan.state
        if not StateMachine.can(src, dst):
            raise InvalidTransition(f"{src.value} -> {dst.value} not allowed")
        plan.state = dst
        plan.history.append({
            "at": now or int(time.time()),
            "from": src.value,
            "to": dst.value,
            "reason": reason,
        })
        return plan

    @staticmethod
    def is_terminal(plan: TradePlan) -> bool:
        return plan.state in TERMINAL
