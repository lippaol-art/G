"""Config loading: settings.yaml + prop_firms.yaml -> typed objects.

Resolves the active prop firm + phase into a RiskLimits, and the broker
instrument specs into SymbolSpec objects. PyYAML is required (listed in
requirements.txt); the core trading logic itself stays stdlib-only.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import yaml

from .risk import RiskLimits, SymbolSpec
from .schema import RiskZone

_HERE = os.path.dirname(__file__)
_CONFIG_DIR = os.path.join(os.path.dirname(_HERE), "config")


@dataclass
class Settings:
    prop_firm: str
    phase: str
    initial_balance: float
    currency: str
    symbols: list[str]
    timeframe: str
    correlation_groups: dict[str, list[str]]
    symbol_specs: dict[str, SymbolSpec]
    adapter: str
    deviation_points: int
    magic_base: int
    news_fail_closed: bool
    entry_jitter_ms: tuple[int, int]
    require_llm_final_check: bool
    telegram_enabled: bool
    allowed_chat_ids: list[int]
    raw: dict = field(default_factory=dict)
    firms_raw: dict = field(default_factory=dict)

    def correlation_group_of(self, symbol: str) -> set[str]:
        for members in self.correlation_groups.values():
            if symbol in members:
                return set(members)
        return {symbol}


def _load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_settings(settings_path: Optional[str] = None,
                  firms_path: Optional[str] = None) -> Settings:
    settings_path = settings_path or os.path.join(_CONFIG_DIR, "settings.yaml")
    if not os.path.exists(settings_path):
        # fall back to the example so the loader is usable out of the box
        settings_path = os.path.join(_CONFIG_DIR, "settings.example.yaml")
    firms_path = firms_path or os.path.join(_CONFIG_DIR, "prop_firms.yaml")

    s = _load_yaml(settings_path)
    firms = _load_yaml(firms_path)

    acct = s.get("account", {})
    market = s.get("market", {})
    execu = s.get("execution", {})
    conf = s.get("confirmation", {})
    tg = s.get("telegram", {})

    specs = {}
    for sym, spec in (acct.get("symbol_specs") or {}).items():
        specs[sym] = SymbolSpec(
            pip_size=float(spec["pip_size"]),
            pip_value_per_lot=float(spec["pip_value_per_lot"]),
            volume_min=float(spec.get("volume_min", 0.01)),
            volume_max=float(spec.get("volume_max", 100.0)),
            volume_step=float(spec.get("volume_step", 0.01)),
            digits=int(spec.get("digits", 1)),
        )

    jitter = conf.get("entry_jitter_ms", [0, 0])
    return Settings(
        prop_firm=s.get("prop_firm", ""),
        phase=s.get("phase", "p1"),
        initial_balance=float(acct.get("initial_balance", 10000)),
        currency=acct.get("currency", "USD"),
        symbols=market.get("symbols", []),
        timeframe=market.get("timeframe", "M15"),
        correlation_groups=market.get("correlation_groups", {}) or {},
        symbol_specs=specs,
        adapter=execu.get("adapter", "mock"),
        deviation_points=int(execu.get("deviation_points", 15)),
        magic_base=int(execu.get("magic_base", 20260101)),
        # default False = demo-friendly (no calendar needed to trade); the
        # example config documents flipping it true for the real challenge.
        news_fail_closed=bool(execu.get("news_fail_closed", False)),
        entry_jitter_ms=(int(jitter[0]), int(jitter[1])),
        require_llm_final_check=bool(conf.get("require_llm_final_check", False)),
        telegram_enabled=bool(tg.get("enabled", False)),
        allowed_chat_ids=[int(c) for c in (tg.get("allowed_chat_ids") or [])],
        raw=s,
        firms_raw=firms,
    )


def resolve_risk_limits(settings: Settings) -> RiskLimits:
    firms = settings.firms_raw
    firm = (firms.get("firms", {}) or {}).get(settings.prop_firm)
    if firm is None:
        raise KeyError(f"prop_firm '{settings.prop_firm}' not in prop_firms.yaml")
    defaults = firms.get("defaults", {}) or {}

    # profit target by phase
    if settings.phase == "p2":
        target = float(firm.get("profit_target_p2", 0.05))
    else:  # p1 or funded — use the funded/p1 target
        target = float(firm.get("profit_target_p1", 0.08))

    zones_cfg = defaults.get("zones", {})
    zones = {
        RiskZone.GREEN: (float(zones_cfg.get("green", {}).get("max_dd", 0.02)),
                         float(zones_cfg.get("green", {}).get("risk_per_trade", 0.01))),
        RiskZone.YELLOW: (float(zones_cfg.get("yellow", {}).get("max_dd", 0.035)),
                          float(zones_cfg.get("yellow", {}).get("risk_per_trade", 0.005))),
        RiskZone.RED: (float(zones_cfg.get("red", {}).get("max_dd", 1.0)),
                       float(zones_cfg.get("red", {}).get("risk_per_trade", 0.0))),
    }

    return RiskLimits(
        daily_loss_limit=float(firm["daily_loss_limit"]),
        max_drawdown=float(firm["max_drawdown"]),
        drawdown_type=str(firm.get("drawdown_type", "static")),
        profit_target=target,
        min_trading_days=int(firm.get("min_trading_days", 0)),
        safety_buffer=float(defaults.get("safety_buffer", 0.80)),
        max_concurrent_positions=int(defaults.get("max_concurrent_positions", 2)),
        max_correlated_exposure=int(defaults.get("max_correlated_exposure", 1)),
        zones=zones,
    )


def slippage_buffer(settings: Settings) -> float:
    defaults = settings.firms_raw.get("defaults", {}) or {}
    return float(defaults.get("slippage_pips_buffer", 3))


def news_window_min(settings: Settings) -> int:
    firm = (settings.firms_raw.get("firms", {}) or {}).get(settings.prop_firm, {})
    return int(firm.get("news_window_min", 2))
