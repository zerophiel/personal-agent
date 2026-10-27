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
        return {"action": "rewrite", "text": new_text}
    except Exception:  # noqa: BLE001 - deliberately broad, see docstring
        log.error("cardguard failed; dropping message %s", getattr(event, "message_id", "?"))
        return {"action": "skip"}


def register(ctx):
    ctx.register_hook("pre_gateway_dispatch", on_inbound)
