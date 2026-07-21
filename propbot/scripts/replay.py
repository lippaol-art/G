"""Replay historical candles through the live engine + Telegram.

Feeds a CSV of M15 candles into the engine as if they were arriving live, so
you get real setup cards on Telegram with ✅/❌ buttons and paper fills — no
real orders, no waiting for the NY session. Great for seeing how the bot picks
entries over past days.

Usage (needs TELEGRAM_BOT_TOKEN in .env, and a candles CSV):
    python scripts/replay.py US30_M15.csv --symbol US30 --speed 1.0

--speed = seconds between candle steps (lower = faster). When a setup confirms,
the replay PAUSES until you tap ✅/❌ (or a timeout), so the fill price matches.

Export a CSV first with:  python scripts/export_mt5_candles.py US30 --days 60
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone

from propbot.backtest.runner import load_candles_csv
from propbot.config import load_settings, resolve_risk_limits
from propbot.engine import Engine
from propbot.execution.replay import ReplayAdapter
from propbot.risk import RiskManager, SymbolSpec
from propbot.state import PlanStore
from propbot.strategy.orb import (ORBConfig, ny_session_open_ts,
                                  session_cutoff_ts)
from propbot.telegram.bot import PropBot


def group_by_day(candles):
    days = {}
    for c in candles:
        key = datetime.fromtimestamp(c.time, tz=timezone.utc).strftime("%Y-%m-%d")
        days.setdefault(key, []).append(c)
    return dict(sorted(days.items()))


class Replay:
    def __init__(self, csv, symbol, speed, pause):
        self.settings = load_settings()
        self.symbol = symbol
        self.speed = speed
        self.pause = pause
        spec = self.settings.symbol_specs.get(
            symbol, SymbolSpec(pip_size=1.0, pip_value_per_lot=1.0))
        point_value = spec.pip_value_per_lot / spec.pip_size
        candles = load_candles_csv(csv)
        self.days = group_by_day(candles)
        self.adapter = ReplayAdapter(symbol, candles, point_value,
                                     self.settings.initial_balance)
        self.orb_cfg = ORBConfig()
        self.engine = Engine(
            self.adapter, RiskManager(resolve_risk_limits(self.settings)),
            PlanStore(f"state/replay_{symbol}.json"), self.settings,
            analyst=None, orb_cfg=self.orb_cfg, news_fail_closed=False)
        self.bot = self._make_bot()

    def _make_bot(self):
        async def on_approve(pid): return self.engine.approve(pid).text
        async def on_cancel(pid): return self.engine.cancel(pid).text
        async def on_status(): return self.engine.status().text
        async def on_pause(p): return self.engine.set_paused(p).text
        return PropBot(allowed_chat_ids=set(self.settings.allowed_chat_ids),
                       on_approve=on_approve, on_cancel=on_cancel,
                       on_status=on_status, on_pause=on_pause)

    async def _emit(self, events):
        for ev in events:
            if ev.kind == "announce_setup" and ev.plan:
                await self.bot.announce_setup(ev.text, ev.plan)
            elif ev.kind == "request_approval" and ev.plan:
                await self.bot.request_approval(ev.text, ev.plan)
            else:
                await self.bot.notify(ev.text)

    async def _run(self):
        # wait until the user sends /start so we have a chat to talk to
        while self.bot._chat_id is None:
            await asyncio.sleep(1)
        await self.bot.notify(
            f"▶️ Replay {self.symbol}: {len(self.days)} dni. Lecę...")

        for day_key, day_candles in self.days.items():
            self.engine.new_trading_day()
            open_ts = ny_session_open_ts(day_candles[0].time, self.orb_cfg)
            range_end = open_ts + self.orb_cfg.range_minutes * 60
            cutoff = session_cutoff_ts(day_candles[0].time, self.orb_cfg)
            analysed = False

            while self.adapter.cursor < len(self.adapter._all) and \
                    self.adapter._all[self.adapter.cursor].time <= day_candles[-1].time:
                c = self.adapter.advance()
                # close positions hit by this candle
                for ticket, reason, pnl in self.adapter.check_exits():
                    emoji = "🎯" if reason == "tp" else "🛑"
                    await self.bot.notify(
                        f"{emoji} Pozycja #{ticket} zamknięta ({reason.upper()}) "
                        f"PnL {pnl:+.2f} | equity {self.adapter.equity:,.0f}")
                # once the opening range is done, ask for the day's setups
                if not analysed and c.time >= range_end:
                    await self._emit(self.engine.run_daily_analysis(self.symbol))
                    analysed = True
                # watch for confirmations during the session
                if open_ts <= c.time <= cutoff:
                    events = self.engine.on_candle_close(self.symbol)
                    await self._emit(events)
                    # pause for a tap if a setup is now awaiting approval
                    if any(e.kind == "request_approval" for e in events):
                        await self._await_decision()
                await asyncio.sleep(self.speed)

        await self.bot.notify(
            f"🏁 Replay koniec. Equity: {self.adapter.equity:,.2f} "
            f"({(self.adapter.equity/self.settings.initial_balance-1):+.2%})")

    async def _await_decision(self):
        """Hold the replay until pending approvals resolve or time out."""
        for _ in range(int(self.pause * 2)):
            if not self.engine.pending:
                return
            await asyncio.sleep(0.5)
        # timed out: drop any still-pending setup so replay moves on
        for pid in list(self.engine.pending):
            self.engine.cancel(pid)
            await self.bot.notify("⏭️ Brak decyzji — pomijam setup, lecę dalej.")

    def run(self):
        async def _post_init(app):
            app.create_task(self._run())
        self.bot.app.post_init = _post_init
        self.bot.run()


def main():
    ap = argparse.ArgumentParser(description="Replay candles through Telegram")
    ap.add_argument("csv")
    ap.add_argument("--symbol", default="US30")
    ap.add_argument("--speed", type=float, default=1.0,
                    help="seconds between candle steps (lower = faster)")
    ap.add_argument("--pause", type=float, default=60,
                    help="seconds to wait for your tap on a setup")
    args = ap.parse_args()
    print(f"[replay] {args.csv} symbol={args.symbol} speed={args.speed}s")
    print("[replay] open Telegram and send /start to begin")
    Replay(args.csv, args.symbol, args.speed, args.pause).run()


if __name__ == "__main__":
    main()
