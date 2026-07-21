"""Telegram bot runtime (VPS only — requires python-telegram-bot).

Wires the human-approval loop:
  * announces the daily setup (reject button only),
  * pings on breakout confirmation with ✅ Wykonaj / ❌ Anuluj,
  * edits the message immediately on click (anti-double-click UX; the hard
    idempotency lock lives in execution/lifecycle.py),
  * /status, /pause, /resume, /positions commands.

The orchestrator (app.py, to be built) injects callbacks; this module owns no
trading logic.
"""
from __future__ import annotations

import os
from typing import Awaitable, Callable, Optional

from ..schema import TradePlan

try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
    from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                              ContextTypes)
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False


def approval_keyboard(plan_id: str):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Wykonaj", callback_data=f"exec:{plan_id}"),
        InlineKeyboardButton("❌ Anuluj", callback_data=f"cancel:{plan_id}"),
    ]])


def setup_keyboard(plan_id: str):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Odrzuć setup", callback_data=f"cancel:{plan_id}"),
    ]])


class PropBot:
    def __init__(self,
                 token: Optional[str] = None,
                 allowed_chat_ids: Optional[set[int]] = None,
                 on_approve: Optional[Callable[[str], Awaitable[str]]] = None,
                 on_cancel: Optional[Callable[[str], Awaitable[str]]] = None,
                 on_status: Optional[Callable[[], Awaitable[str]]] = None,
                 on_pause: Optional[Callable[[bool], Awaitable[str]]] = None):
        if not HAS_TELEGRAM:
            raise RuntimeError("python-telegram-bot not installed "
                               "(pip install -r requirements.txt on the VPS)")
        # strip() guards against a stray newline/space from a shell paste
        self.token = (token or os.environ["TELEGRAM_BOT_TOKEN"]).strip()
        self.allowed_chat_ids = allowed_chat_ids or set()
        self.on_approve = on_approve
        self.on_cancel = on_cancel
        self.on_status = on_status
        self.on_pause = on_pause
        self.app: Application = Application.builder().token(self.token).build()
        self._register()
        self._chat_id: Optional[int] = None

    def _register(self) -> None:
        self.app.add_handler(CommandHandler("start", self._cmd_start))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(CommandHandler("pause", self._cmd_pause))
        self.app.add_handler(CommandHandler("resume", self._cmd_resume))
        self.app.add_handler(CallbackQueryHandler(self._on_button))

    def _authorized(self, chat_id: int) -> bool:
        return not self.allowed_chat_ids or chat_id in self.allowed_chat_ids

    # --- outgoing --------------------------------------------------------

    async def announce_setup(self, text: str, plan: TradePlan) -> None:
        if self._chat_id is None:
            return
        await self.app.bot.send_message(self._chat_id, text,
                                        reply_markup=setup_keyboard(plan.id))

    async def request_approval(self, text: str, plan: TradePlan) -> None:
        if self._chat_id is None:
            return
        await self.app.bot.send_message(self._chat_id, text,
                                        reply_markup=approval_keyboard(plan.id))

    async def notify(self, text: str) -> None:
        if self._chat_id is not None:
            await self.app.bot.send_message(self._chat_id, text)

    # --- handlers --------------------------------------------------------

    async def _cmd_start(self, update: Update,
                         ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update.effective_chat.id):
            return
        self._chat_id = update.effective_chat.id
        await update.message.reply_text(
            "🤖 propbot połączony. Komendy: /status /pause /resume")

    async def _cmd_status(self, update: Update,
                          ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update.effective_chat.id):
            return
        text = await self.on_status() if self.on_status else "brak danych"
        await update.message.reply_text(text)

    async def _cmd_pause(self, update: Update,
                         ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update.effective_chat.id):
            return
        text = await self.on_pause(True) if self.on_pause else "⏸️ pauza"
        await update.message.reply_text(text)

    async def _cmd_resume(self, update: Update,
                          ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update.effective_chat.id):
            return
        text = await self.on_pause(False) if self.on_pause else "▶️ wznowiono"
        await update.message.reply_text(text)

    async def _on_button(self, update: Update,
                         ctx: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not self._authorized(query.message.chat.id):
            return
        await query.answer()
        action, _, plan_id = query.data.partition(":")
        # Kill the buttons instantly — UX anti-double-click. The execution
        # lock in lifecycle.py is the real idempotency guarantee.
        await query.edit_message_reply_markup(reply_markup=None)
        if action == "exec" and self.on_approve:
            await query.message.reply_text("⏳ Składam zlecenie...")
            result_text = await self.on_approve(plan_id)
        elif action == "cancel" and self.on_cancel:
            result_text = await self.on_cancel(plan_id)
        else:
            result_text = "nieznana akcja"
        await query.message.reply_text(result_text)

    def run(self) -> None:
        self.app.run_polling()
