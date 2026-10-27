"""cardguard (spike): rewrite Luhn-valid 13-19 digit numbers to [[CARD:****last4]].

Logs metadata only, never the text. In production this calls vault-tools store_payee_secret
before rewriting; the spike only proves the hook runs before persistence/logging.
"""
import logging
import re

log = logging.getLogger("cardguard")
_CANDIDATE = re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
        alt = not alt
    return total % 10 == 0


def _tokenize(text: str):
    hits = []

    def repl(m):
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and _luhn(digits):
            hits.append(digits[-4:])
            return f"[[CARD:****{digits[-4:]}]]"
        return m.group(0)

    return _CANDIDATE.sub(repl, text), hits


def _bot_delete(chat_id, message_id) -> None:
    """Bot API deleteMessage (incoming private-chat messages, within 48h). Uses the vault bot
    token from this process's environment; honours HTTPS_PROXY (squid-vault)."""
    import json
    import os
    import urllib.parse
    import urllib.request

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        log.warning("cardguard: no bot token, cannot delete message %s", message_id)
        return
    data = urllib.parse.urlencode({"chat_id": chat_id, "message_id": message_id}).encode()
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/deleteMessage",
                                    data, timeout=15) as r:
            ok = json.load(r).get("ok")
    except Exception:  # noqa: BLE001 - never log the URL (it contains the token)
        ok = False
    log.info("cardguard: deleteMessage %s for message %s", "ok" if ok else "FAILED", message_id)


def _delete_async(event, deleter=_bot_delete) -> None:
    """Delete the owner's raw message in the background; only in private (dm) chats."""
    import threading

    src = getattr(event, "source", None)
    if getattr(src, "chat_type", None) != "dm":
        return
    chat_id, mid = getattr(src, "chat_id", None), getattr(event, "message_id", None)
    if chat_id is None or mid is None:
        return
    threading.Thread(target=deleter, args=(chat_id, mid), daemon=True).start()


def on_inbound(event, **kwargs):
    """Fail closed: Hermes treats a hook exception as "allow", which would leak a raw number
    to the model. Any error here drops the message instead."""
    try:
        text = getattr(event, "text", None)
        if not text:
            return None
        new_text, hits = _tokenize(text)
        if not hits:
            return None
        log.info("cardguard rewrote %d number(s) in message %s", len(hits), getattr(event, "message_id", "?"))
        _delete_async(event)
        return {"action": "rewrite", "text": new_text}
    except Exception:  # noqa: BLE001 - deliberately broad, see docstring
        log.error("cardguard failed; dropping message %s", getattr(event, "message_id", "?"))
        return {"action": "skip"}


def register(ctx):
    ctx.register_hook("pre_gateway_dispatch", on_inbound)
