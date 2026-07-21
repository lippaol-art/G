"""Deterministic Risk Management System (RMS).

This layer is INDEPENDENT of the LLM and has final veto over every trade. It
implements the pieces the research flags as decisive:

  * Daily Loss Limit (DLL) with a safety buffer (alpha).
  * Maximum Drawdown (MDD), static or trailing (high-water-mark) with the
    "trailing drawdown trap" handled explicitly.
  * Graduated Recovery Protocol: green / yellow / red zones scale risk per trade
    down to zero as intraday drawdown grows.
  * Dynamic position sizing from money-at-risk and stop distance.
  * Concurrency and correlated-exposure caps.

Nothing here trusts the model: if the numbers say no, it is no.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from ..schema import AccountState, Direction, RiskZone, TradePlan


@dataclass
class RiskLimits:
    """Resolved limits for the active prop firm + phase (fractions of balance)."""
    daily_loss_limit: float
    max_drawdown: float
    drawdown_type: str               # "static" | "trailing"
    profit_target: float
    min_trading_days: int
    safety_buffer: float = 0.80
    max_concurrent_positions: int = 2
    max_correlated_exposure: int = 1
    # zone -> (max_dd fraction, risk_per_trade fraction)
    zones: dict = field(default_factory=lambda: {
        RiskZone.GREEN:  (0.020, 0.010),
        RiskZone.YELLOW: (0.035, 0.005),
        RiskZone.RED:    (1.000, 0.000),
    })


@dataclass
class SymbolSpec:
    """Broker instrument spec needed for sizing (mirrors MT5 symbol_info)."""
    pip_size: float          # price movement of one pip (e.g. 0.0001 EURUSD)
    pip_value_per_lot: float # account-currency value of one pip for 1.0 lot
    volume_min: float = 0.01
    volume_max: float = 100.0
    volume_step: float = 0.01
    digits: int = 5


@dataclass
class RiskDecision:
    allowed: bool
    zone: RiskZone
    volume: float = 0.0
    risk_pct: float = 0.0
    money_at_risk: float = 0.0
    reasons: list[str] = field(default_factory=list)   # veto reasons if blocked
    notes: list[str] = field(default_factory=list)


class RiskManager:
    def __init__(self, limits: RiskLimits, slippage_pips_buffer: float = 3.0):
        self.limits = limits
        self.slippage_pips_buffer = slippage_pips_buffer

    # --- limit levels -----------------------------------------------------

    def daily_loss_floor(self, acct: AccountState) -> float:
        """Equity level at which our own (buffered) daily stop trips.

        Real hard floor = day_start_equity * (1 - DLL). We trip earlier, at
        alpha * DLL, to survive slippage/spread on the forced close.
        """
        hard_loss = acct.day_start_equity * self.limits.daily_loss_limit
        buffered_loss = hard_loss * self.limits.safety_buffer
        return acct.day_start_equity - buffered_loss

    def max_drawdown_floor(self, acct: AccountState) -> float:
        """Absolute equity floor for the account (static or trailing)."""
        if self.limits.drawdown_type == "trailing":
            # Trailing floor rides the high-water mark up and never comes back down.
            return acct.high_water_mark * (1 - self.limits.max_drawdown)
        return acct.initial_balance * (1 - self.limits.max_drawdown)

    def effective_floor(self, acct: AccountState) -> float:
        """Whichever floor is nearer to current equity binds first."""
        return max(self.daily_loss_floor(acct), self.max_drawdown_floor(acct))

    # --- zones ------------------------------------------------------------

    def current_zone(self, acct: AccountState) -> RiskZone:
        """Zone from intraday drawdown (fraction of day-start equity)."""
        dd = -acct.day_pnl_pct  # positive when in drawdown
        green_max = self.limits.zones[RiskZone.GREEN][0]
        yellow_max = self.limits.zones[RiskZone.YELLOW][0]
        if dd <= green_max:
            return RiskZone.GREEN
        if dd <= yellow_max:
            return RiskZone.YELLOW
        return RiskZone.RED

    def risk_pct_for_zone(self, zone: RiskZone) -> float:
        return self.limits.zones[zone][1]

    # --- sizing -----------------------------------------------------------

    def size_position(self, money_at_risk: float, stop_pips: float,
                      spec: SymbolSpec) -> float:
        """Lots such that a stop-out loses ~money_at_risk.

        Slippage buffer is added to the stop distance so a realistic fill still
        stays within budget.
        """
        effective_pips = stop_pips + self.slippage_pips_buffer
        if effective_pips <= 0 or spec.pip_value_per_lot <= 0:
            return 0.0
        raw = money_at_risk / (effective_pips * spec.pip_value_per_lot)
        stepped = round(raw / spec.volume_step) * spec.volume_step
        stepped = max(spec.volume_min, min(spec.volume_max, stepped))
        # never round *up* past budget
        if stepped * effective_pips * spec.pip_value_per_lot > money_at_risk \
                and stepped > spec.volume_min:
            stepped = max(spec.volume_min, stepped - spec.volume_step)
        return round(stepped, 2)

    def stop_distance_pips(self, plan: TradePlan, spec: SymbolSpec) -> float:
        entry = (plan.entry_zone_low + plan.entry_zone_high) / 2
        return abs(entry - plan.stop_loss) / spec.pip_size

    # --- the gate ---------------------------------------------------------

    def evaluate(self, plan: TradePlan, acct: AccountState, spec: SymbolSpec,
                correlated_open: int = 0) -> RiskDecision:
        """Full pre-trade check. Returns a sized decision or a vetoed one."""
        zone = self.current_zone(acct)
        reasons: list[str] = []
        notes: list[str] = []

        # 1. Hard floors already breached / at zero risk.
        if zone is RiskZone.RED:
            reasons.append("RED zone: intraday drawdown exceeds yellow band; "
                          "trading blocked for the day")
        if acct.equity <= self.effective_floor(acct):
            reasons.append("Equity at/below effective floor "
                          f"({self.effective_floor(acct):.2f})")

        # 2. Concurrency / correlation.
        if acct.open_positions >= self.limits.max_concurrent_positions:
            reasons.append(f"Max concurrent positions reached "
                          f"({acct.open_positions}/{self.limits.max_concurrent_positions})")
        if correlated_open >= self.limits.max_correlated_exposure:
            reasons.append(f"Correlated exposure cap reached "
                          f"({correlated_open}/{self.limits.max_correlated_exposure})")

        # 3. Yellow zone only takes the very best setups.
        risk_pct = self.risk_pct_for_zone(zone)
        if zone is RiskZone.YELLOW and plan.grade not in ("A+", "A"):
            reasons.append(f"YELLOW zone accepts only A/A+ setups; plan is {plan.grade}")

        # 4. Size it.
        stop_pips = self.stop_distance_pips(plan, spec)
        if stop_pips <= 0:
            reasons.append("Non-positive stop distance")

        money_at_risk = acct.equity * risk_pct
        volume = 0.0
        if not reasons and money_at_risk > 0:
            volume = self.size_position(money_at_risk, stop_pips, spec)
            if volume <= 0:
                reasons.append("Sized volume rounds to zero")
            else:
                projected_loss = volume * (stop_pips + self.slippage_pips_buffer) \
                    * spec.pip_value_per_lot
                # Would this stop-out push us below a floor?
                if acct.equity - projected_loss < self.effective_floor(acct):
                    reasons.append("Projected stop-out would breach effective floor")

        if plan.risk_reward < 1.0:
            notes.append(f"Low R:R ({plan.risk_reward:.2f})")

        allowed = not reasons
        return RiskDecision(
            allowed=allowed,
            zone=zone,
            volume=volume if allowed else 0.0,
            risk_pct=risk_pct,
            money_at_risk=money_at_risk if allowed else 0.0,
            reasons=reasons,
            notes=notes,
        )

    # --- housekeeping the caller runs each tick ---------------------------

    def update_high_water_mark(self, acct: AccountState) -> AccountState:
        if acct.equity > acct.high_water_mark:
            acct.high_water_mark = acct.equity
        return acct

    def should_flatten(self, acct: AccountState) -> bool:
        """True when open risk must be cut immediately (red zone / floor hit)."""
        return (self.current_zone(acct) is RiskZone.RED
                or acct.equity <= self.effective_floor(acct))

    def target_reached(self, acct: AccountState) -> bool:
        gain = (acct.equity - acct.initial_balance) / acct.initial_balance
        return gain >= self.limits.profit_target
