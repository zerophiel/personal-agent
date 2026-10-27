"""control bot skeleton (M1): deterministic, NO LLM.

Long-polls Telegram and answers only the owner in a private chat.
Everything else is dropped silently and logged. Approvals/applier arrive in M3.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import urllib.request

log = logging.getLogger("control")


def is_authorized(update: dict, owner_id: int) -> bool:
    """True only for a private-chat message or callback from the owner."""
    if "message" in update:
        msg = update["message"]
        sender, chat = msg.get("from", {}), msg.get("chat", {})
    elif "callback_query" in update:
        cq = update["callback_query"]
        sender = cq.get("from", {})
        chat = cq.get("message", {}).get("chat", {})
    else:
        return False
    return sender.get("id") == owner_id and chat.get("type") == "private"


def handle(update: dict) -> str | None:
    """Return reply text for an authorized update (M1: /ping and /status only)."""
    text = (update.get("message") or {}).get("text", "").strip()
    if text == "/ping":
        return "pong"
    if text == "/status":
        return "control: ok (M1 skeleton)"
    return None


class Telegram:
    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}"

    def call(self, method: str, **params):
        data = urllib.parse.urlencode(params).encode()
        with urllib.request.urlopen(f"{self.base}/{method}", data, timeout=60) as r:
            return json.load(r)["result"]


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    owner = int(os.environ["MY_TELEGRAM_ID"])
    with open(os.environ["TELEGRAM_TOKEN_FILE"]) as f:
        tg = Telegram(f.read().strip())
    offset = 0
    while True:
        try:
            updates = tg.call("getUpdates", offset=offset, timeout=50,
                              allowed_updates=json.dumps(["message", "callback_query"]))
        except Exception:  # network/proxy blip; never log the token-bearing URL
            log.warning("getUpdates failed")
            time.sleep(5)
            continue
        for u in updates:
            offset = u["update_id"] + 1
            if not is_authorized(u, owner):
                log.warning("dropped update %s from unauthorized sender", u["update_id"])
                continue
            reply = handle(u)
            if reply:
                tg.call("sendMessage", chat_id=owner, text=reply,
                        disable_web_page_preview="true")


if __name__ == "__main__":
    main()
