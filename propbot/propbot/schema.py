"""Core data contracts shared across the system.

Pure standard library (dataclasses + enums) so the core runs and tests without
any third-party dependency. The LLM produces a ``TradePlan``; the deterministic
watcher/risk/executor layers consume it.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional


class Direction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"

    @property
    def sign(self) -> int:
        return 1 if self is Direction.LONG else -1


class SetupState(str, Enum):
    """Lifecycle of a conditional trade plan."""
    WAITING_FOR_PRICE = "WAITING_FOR_PRICE"  # price not yet in entry zone
    ARMED = "ARMED"                          # price in zone, watching for confirmation
    CONFIRMED = "CONFIRMED"                   # confirmation met -> awaiting human approval
    EXECUTING = "EXECUTING"                   # order sent, awaiting broker confirmation
    OPEN = "OPEN"                             # position live at broker
    CLOSED = "CLOSED"                         # position closed (SL/TP/manual)
    EXPIRED = "EXPIRED"                       # valid_until passed before confirmation
    INVALIDATED = "INVALIDATED"              # price broke setup before confirming
    CANCELLED = "CANCELLED"                  # rejected by human or risk veto


class RiskZone(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass
class Candle:
    time: int          # epoch seconds of candle open
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class ConfirmationRule:
    """A deterministic condition the watcher evaluates on each closed candle.

    ``kind`` selects the check; ``params`` carries its arguments. Keeping this
    data-only (not code) means plans are serialisable and auditable.
    """
    kind: str                       # e.g. "candle_close_above", "rsi_above"
    params: dict = field(default_factory=dict)


@dataclass
class TradePlan:
    """Conditional plan emitted by the LLM analyst. Never a market order itself.

    The plan says: *when* price reaches this zone *and* these confirmations hold,
    *then* ask the human to approve an entry with this SL/TP and this rationale.
    """
    symbol: str
    direction: Direction
    entry_zone_low: float
    entry_zone_high: float
    stop_loss: float
    take_profit: float
    confirmations: list[ConfirmationRule] = field(default_factory=list)
    valid_until: int = 0            # epoch seconds; 0 => no expiry
    confidence: float = 0.0         # 0..1 from the LLM
    grade: str = "B"                # A+, A, B ... used by yellow-zone gating
    rationale: str = ""
    # runtime fields
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    state: SetupState = SetupState.WAITING_FOR_PRICE
    created_at: int = field(default_factory=lambda: int(time.time()))
    ticket: Optional[int] = None    # broker ticket once open
    history: list[dict] = field(default_factory=list)

    @property
    def risk_reward(self) -> float:
        entry = (self.entry_zone_low + self.entry_zone_high) / 2
        risk = abs(entry - self.stop_loss)
        reward = abs(self.take_profit - entry)
        return reward / risk if risk > 0 else 0.0

    def price_in_zone(self, price: float) -> bool:
        return self.entry_zone_low <= price <= self.entry_zone_high

    def is_expired(self, now: Optional[int] = None) -> bool:
        if self.valid_until == 0:
            return False
        return (now or int(time.time())) >= self.valid_until

    def to_dict(self) -> dict:
        d = asdict(self)
        d["direction"] = self.direction.value
        d["state"] = self.state.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TradePlan":
        d = dict(d)
        d["direction"] = Direction(d["direction"])
        d["state"] = SetupState(d.get("state", SetupState.WAITING_FOR_PRICE.value))
        d["confirmations"] = [
            ConfirmationRule(**c) if isinstance(c, dict) else c
            for c in d.get("confirmations", [])
        ]
        return cls(**d)


@dataclass
class AccountState:
    """Snapshot used by the risk manager. day_start_equity resets at broker 00:00."""
    balance: float
    equity: float
    day_start_equity: float
    initial_balance: float
    high_water_mark: float          # peak equity ever, for trailing drawdown
    open_positions: int = 0
    trading_days: int = 0

    @property
    def day_pnl(self) -> float:
        return self.equity - self.day_start_equity

    @property
    def day_pnl_pct(self) -> float:
        return self.day_pnl / self.day_start_equity if self.day_start_equity else 0.0


@dataclass
class OrderIntent:
    """What we intend to send once the human approves."""
    symbol: str
    direction: Direction
    volume: float
    stop_loss: float
    take_profit: float
    plan_id: str
    deviation_points: int = 15
    magic: int = 0
    comment: str = "propbot"


@dataclass
class OrderResult:
    ok: bool
    retcode: int = 0
    ticket: Optional[int] = None
    fill_price: Optional[float] = None
    filled_volume: float = 0.0
    requested_volume: float = 0.0
    message: str = ""

    @property
    def partial(self) -> bool:
        return self.ok and 0 < self.filled_volume < self.requested_volume
