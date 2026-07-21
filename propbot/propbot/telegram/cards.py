"""Telegram message formatting — pure functions, no bot dependency.

Kept separate from bot.py so card rendering is unit-testable in the core
suite (python-telegram-bot is only installed on the VPS).
"""
from __future__ import annotations

from datetime import datetime, timezone

from ..execution.lifecycle import ExecutionReport
from ..risk.risk_manager import RiskDecision
from ..schema import AccountState, Direction, TradePlan

_ZONE_EMOJI = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}


def _fmt_time(ts: int) -> str:
    if not ts:
        return "-"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%H:%M UTC")


def _dir_emoji(d: Direction) -> str:
    return "📈 LONG" if d is Direction.LONG else "📉 SHORT"


def format_setup_card(plan: TradePlan) -> str:
    """Daily setup announcement — informational, only a reject button."""
    return (
        f"📋 Setup dnia: {plan.symbol} {_dir_emoji(plan.direction)}  "
        f"[{plan.grade}]\n"
        f"Strefa wejścia: {plan.entry_zone_low:.1f} – {plan.entry_zone_high:.1f}\n"
        f"SL {plan.stop_loss:.1f} | TP {plan.take_profit:.1f} "
        f"| R:R 1:{plan.risk_reward:.1f}\n"
        f"Ważny do: {_fmt_time(plan.valid_until)}\n"
        f"Pewność: {plan.confidence:.0%}\n"
        f"💬 {plan.rationale}"
    )


def format_confirmed_card(plan: TradePlan, decision: RiskDecision,
                          acct: AccountState) -> str:
    """Breakout confirmed — the approve/cancel moment."""
    zone = _ZONE_EMOJI.get(decision.zone.value, "")
    lines = [
        f"🔔 POTWIERDZENIE! {plan.symbol} {_dir_emoji(plan.direction)} "
        f"[{plan.grade}]",
        f"Wolumen: {decision.volume:.2f} lota "
        f"(ryzyko {decision.risk_pct:.1%} = {decision.money_at_risk:.0f} USD)",
        f"SL {plan.stop_loss:.1f} | TP {plan.take_profit:.1f} "
        f"| R:R 1:{plan.risk_reward:.1f}",
        f"Equity: {acct.equity:,.0f} | Dzienny P/L: {acct.day_pnl_pct:+.2%} "
        f"| Strefa: {zone} {decision.zone.value}",
    ]
    for note in decision.notes:
        lines.append(f"⚠️ {note}")
    return "\n".join(lines)


def format_veto_card(plan: TradePlan, decision: RiskDecision) -> str:
    reasons = "\n".join(f"  • {r}" for r in decision.reasons)
    return (
        f"⛔ Setup {plan.symbol} {plan.direction.value} potwierdzony, "
        f"ale ZABLOKOWANY przez risk managera:\n{reasons}"
    )


def format_execution_report(report: ExecutionReport, plan: TradePlan) -> str:
    if not report.ok:
        msgs = "\n".join(f"  • {m}" for m in report.messages)
        return f"❌ NIE WYKONANO ({report.stage}):\n{msgs}"
    r = report.result
    lines = [
        f"✅ WYPEŁNIONE  #{r.ticket}",
        f"{plan.symbol} {plan.direction.value} {r.filled_volume:.2f} lota "
        f"@ {r.fill_price:.1f}",
        f"Slippage: {report.slippage:+.2f} pkt",
        f"SL {plan.stop_loss:.1f} | TP {plan.take_profit:.1f}",
    ]
    if report.partial:
        lines.append("⚠️ CZĘŚCIOWE wypełnienie!")
    if report.sl_missing:
        lines.append("🚨 ALARM: brak SL na pozycji — reaguj natychmiast!")
    for m in report.messages:
        lines.append(f"⚠️ {m}")
    return "\n".join(lines)


def format_status(acct: AccountState, zone: str, floor: float,
                  target_pct: float, open_plans: int) -> str:
    gain = (acct.equity - acct.initial_balance) / acct.initial_balance
    return (
        f"📊 Status konta\n"
        f"Equity: {acct.equity:,.2f} (start dnia: {acct.day_start_equity:,.2f})\n"
        f"Dzienny P/L: {acct.day_pnl_pct:+.2%} | "
        f"Strefa: {_ZONE_EMOJI.get(zone, '')} {zone}\n"
        f"Floor (twardy stop): {floor:,.2f}\n"
        f"Postęp do celu: {gain:+.2%} / {target_pct:.0%}\n"
        f"Otwarte pozycje: {acct.open_positions} | Aktywne plany: {open_plans}"
    )
