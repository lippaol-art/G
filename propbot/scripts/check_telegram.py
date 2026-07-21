"""Step 1 — connect Telegram.

Run this AFTER creating a bot with @BotFather and putting the token in .env
(or TELEGRAM_BOT_TOKEN in the environment). It:

  1. verifies the token (getMe),
  2. prints the chat_id of anyone who has messaged the bot — send it any
     message first (e.g. "hi"), then run this; copy the chat_id into
     TELEGRAM_ALLOWED_CHAT_IDS in .env,
  3. optionally sends a test message back if you pass a chat_id.

Usage:
    python scripts/check_telegram.py            # verify token + show chat ids
    python scripts/check_telegram.py <chat_id>  # also send a test message

Uses only urllib (stdlib) — no dependency needed just to check the pipe.
"""
import json
import os
import sys
import urllib.request

# .strip() tolerates a stray newline/space from a multi-line paste, which
# otherwise crashes with "URL can't contain control characters".
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()


def api(method: str, params: dict | None = None) -> dict:
    url = f"https://api.telegram.org/bot{TOKEN}/{method}"
    data = json.dumps(params).encode() if params else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def main() -> None:
    if not TOKEN:
        print("Set TELEGRAM_BOT_TOKEN (from @BotFather) in your environment/.env")
        sys.exit(1)

    me = api("getMe")
    if not me.get("ok"):
        print("Token rejected:", me)
        sys.exit(1)
    bot = me["result"]
    print(f"✅ Bot OK: @{bot['username']} ({bot['first_name']})")

    print("\nRecent chats that messaged the bot (send it 'hi' first if empty):")
    updates = api("getUpdates")
    seen = {}
    for u in updates.get("result", []):
        msg = u.get("message") or u.get("edited_message") or {}
        chat = msg.get("chat")
        if chat:
            seen[chat["id"]] = chat.get("username") or chat.get("first_name", "?")
    if not seen:
        print("  (none yet — open Telegram, message your bot, then re-run)")
    for cid, name in seen.items():
        print(f"  chat_id={cid}  ({name})   -> put this in TELEGRAM_ALLOWED_CHAT_IDS")

    if len(sys.argv) > 1:
        cid = int(sys.argv[1])
        res = api("sendMessage", {"chat_id": cid,
                                  "text": "✅ propbot połączony z Telegramem."})
        print("\nTest message sent:", res.get("ok"))


if __name__ == "__main__":
    main()
