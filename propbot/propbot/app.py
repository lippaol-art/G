"""Live orchestrator (Windows VPS entrypoint).

Wires the Engine to a real ExecutionAdapter (MT5 or mock) and the Telegram bot,
and runs the trading loop:

  * schedule run_daily_analysis around the NY session open,
  * poll on_candle_close each M15 close,
  * run monitor() between closes (reconcile + red-zone flatten),
  * route ✅/❌ taps and /status /pause through the Engine.

MT5 + Telegram are import-guarded via their adapters, so importing this module
never fails in the dev sandbox; run() does require them.

    python -m propbot.app          # uses config/settings.yaml
"""
from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from .config import (Settings, load_settings, resolve_orb_config,
                     resolve_risk_limits)
from .engine import Engine, EngineEvent
from .execution import MockAdapter
from .risk import RiskManager
from .state import PlanStore
from .strategy.orb import session_cutoff_ts, session_open_ts


def build_adapter(settings: Settings):
    if settings.adapter == "mt5":
        from .execution.mt5 import MT5Adapter
        return MT5Adapter(magic=settings.magic_base,
                          deviation_points=settings.deviation_points,
                          initial_balance=settings.initial_balance)
    return MockAdapter(initial_balance=settings.initial_balance)


def build_engine(settings: Settings, adapter=None) -> Engine:
    adapter = adapter or build_adapter(settings)
    risk = RiskManager(resolve_risk_limits(settings))
    store_path = os.environ.get("PROPBOT_STATE", "state/plans.json")
    store = PlanStore(store_path)
    calendar = None
    cal_path = os.environ.get("PROPBOT_CALENDAR", "data/calendar.json")
    if os.path.exists(cal_path):
        from .market.calendar import load
        calendar = load(cal_path)
    analyst = None
    if settings.raw.get("llm", {}).get("provider") == "anthropic":
        try:
            from .llm.client import AnalystClient
            analyst = AnalystClient()
        except Exception as e:   # missing SDK / key -> engine falls back to grade B
            print(f"[app] LLM disabled: {e}")
    return Engine(adapter, risk, store, settings, analyst=analyst,
                  calendar=calendar, orb_cfg=resolve_orb_config(settings),
                  news_fail_closed=settings.news_fail_closed)


class App:
    """Glue between the Engine and the Telegram bot."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = build_engine(settings)
        self.bot = None
        self._analysed_today: set[str] = set()

    def _make_bot(self):
        from .telegram.bot import PropBot

        async def on_approve(pid): return self.engine.approve(pid).text
        async def on_cancel(pid): return self.engine.cancel(pid).text
        async def on_status(): return self.engine.status().text
        async def on_pause(p): return self.engine.set_paused(p).text

        return PropBot(allowed_chat_ids=set(self.settings.allowed_chat_ids),
                       on_approve=on_approve, on_cancel=on_cancel,
                       on_status=on_status, on_pause=on_pause)

    async def _emit(self, events: list[EngineEvent]) -> None:
        for ev in events:
            if ev.kind == "announce_setup" and ev.plan:
                await self.bot.announce_setup(ev.text, ev.plan)
            elif ev.kind == "request_approval" and ev.plan:
                await self.bot.request_approval(ev.text, ev.plan)
            else:
                await self.bot.notify(ev.text)

    def _server_now(self) -> int | None:
        """Broker server time (epoch). MT5 stamps candles on the server wall
        clock, and every session comparison must use that same clock — never
        local UTC, which is offset from it (see propbot/strategy/orb.py). We
        read it off the newest candle; None until the feed has warmed up."""
        latest = 0
        for symbol in self.settings.symbols:
            cs = self.engine.adapter.candles(symbol, self.settings.timeframe, 1)
            if cs:
                latest = max(latest, cs[-1].time)
        return latest or None

    async def _trading_loop(self) -> None:
        """One tick per minute: analyse at the session window, watch each M15
        close, monitor in between. New broker day resets the daily reference."""
        last_day = None
        while True:
            now = self._server_now()
            if now is None:                     # feed not ready yet
                await self._emit(self.engine.monitor())
                await asyncio.sleep(60)
                continue
            day_key = datetime.fromtimestamp(now, tz=timezone.utc).strftime("%Y-%m-%d")
            if day_key != last_day:
                self.engine.new_trading_day()
                self._analysed_today.clear()
                last_day = day_key

            for symbol in self.settings.symbols:
                open_ts = session_open_ts(now, self.engine.orb_cfg)
                range_end = open_ts + self.engine.orb_cfg.range_minutes * 60
                cutoff = session_cutoff_ts(now, self.engine.orb_cfg)
                # analyse once, just after the opening range forms
                if symbol not in self._analysed_today and range_end <= now < cutoff:
                    await self._emit(self.engine.run_daily_analysis(symbol))
                    self._analysed_today.add(symbol)
                # watch confirmations during the session
                if open_ts <= now <= cutoff:
                    await self._emit(self.engine.on_candle_close(symbol))

            await self._emit(self.engine.monitor())
            await asyncio.sleep(60)

    def run(self) -> None:
        self.bot = self._make_bot()

        async def _post_init(app):
            app.create_task(self._trading_loop())

        self.bot.app.post_init = _post_init
        self.bot.run()


def main() -> None:
    settings = load_settings()
    print(f"[app] firm={settings.prop_firm} phase={settings.phase} "
          f"adapter={settings.adapter} symbols={settings.symbols}")
    App(settings).run()


if __name__ == "__main__":
    main()
