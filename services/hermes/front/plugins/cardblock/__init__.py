"""cardblock: a card number sent to the front bot never reaches the model (front profile only).

Front cannot keep a number safely (vault-tools, where vault's cardguard stores one, is out of its reach), and a card
number sent here was meant for the vault bot, so pre_gateway_dispatch DROPS every message whose text holds a Luhn-valid
13-19 digit run: photo captions and the text documents Hermes inlines into the message are checked the same way (a
photo's pixels are not: SOUL.md). For the owner in a private chat the raw message is also deleted in Telegram and a fixed
notice sent; anyone else's message is dropped without a word (Hermes runs this hook BEFORE its own sender check). A
message without such a number is left alone. Everything fails CLOSED: any error drops the message (Hermes treats a hook
exception as "allow", which would pass the raw number on). Only metadata is ever logged, never text or numbers. The
detection is vault's cardguard's; tests/test_cardblock.py keeps the two equal.
"""
import json
import logging
import os
import re
import threading
import urllib.parse
import urllib.request

log = logging.getLogger("cardblock")
_CANDIDATE = re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")
NOTICE = ("Pesanmu berisi deret angka yang mirip nomor kartu, jadi pesan itu sudah dihapus dan tidak diteruskan ke "
          "asisten. Nomor kartu hanya dikirim ke @danoevault_agent. Kalau ada pertanyaan lain di pesan itu, kirim ulang "
          "tanpa deret angkanya.")


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def _digits_of(raw: str) -> str | None:
    digits = re.sub(r"\D", "", raw)
    return digits if 13 <= len(digits) <= 19 and _luhn(digits) else None


def find_numbers(text: str) -> list[str]:
    return [d for m in _CANDIDATE.finditer(text) if (d := _digits_of(m.group(0)))]


def _owner_ids() -> set[str]:
    """The ids in TELEGRAM_ALLOWED_USERS (front.env: the owner's alone); empty means nobody gets a notice."""
    return {x.strip() for x in os.environ.get("TELEGRAM_ALLOWED_USERS", "").split(",") if x.strip()}


# ---- Telegram Bot API (front bot token, this process only) ----------------------------

def _bot(method: str, **params):
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        return None
    data = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{method}", data, timeout=15) as r:
            body = json.load(r)
        return body.get("result") if body.get("ok") else None
    except Exception:  # noqa: BLE001 - never log: the URL contains the token
        return None


def _tell_owner(chat_id, message_id) -> None:
    """Delete the owner's raw message (incoming, private chat, <48h), then send the notice; off the dispatch path."""
    deleted = _bot("deleteMessage", chat_id=chat_id, message_id=message_id)
    log.info("cardblock: deleteMessage %s for message %s", "ok" if deleted else "FAILED", message_id)
    if _bot("sendMessage", chat_id=chat_id, text=NOTICE, disable_web_page_preview="true") is None:
        log.error("cardblock: notice not sent for message %s", message_id)


# ---- hook ------------------------------------------------------------------------------

def on_inbound(event, **kwargs):
    try:
        text = getattr(event, "text", None)
        if not text or not find_numbers(text):
            return None
        src = getattr(event, "source", None)
        chat_id, mid = getattr(src, "chat_id", None), getattr(event, "message_id", None)
        user_id = getattr(src, "user_id", None)
        owner = getattr(src, "chat_type", None) == "dm" and user_id is not None and str(user_id) in _owner_ids()
        if owner and chat_id is not None and mid is not None:
            threading.Thread(target=_tell_owner, args=(chat_id, mid), daemon=True).start()
        log.info("cardblock dropped message %s (%s)", mid if mid is not None else "?", "owner" if owner else "not the owner")
        return {"action": "skip", "reason": "cardblock"}
    except Exception:  # noqa: BLE001 - fail closed, see module docstring
        log.error("cardblock failed; dropping message %s", getattr(event, "message_id", "?"))
        return {"action": "skip", "reason": "cardblock-error"}


def register(ctx):
    ctx.register_hook("pre_gateway_dispatch", on_inbound)
