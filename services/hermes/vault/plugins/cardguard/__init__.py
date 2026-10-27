"""cardguard: keep full card numbers out of the model's world (vault profile only).

pre_gateway_dispatch, in this order of precedence:
 1. "/rincian": ask vault-tools (internal API) for the transfer list WITH full numbers, send it
    straight to Telegram via the Bot API, record it for auto-deletion, and `skip` so Hermes never
    sees the reply or the command.
 2. Luhn-valid 13-19 digit numbers: store each via vault-tools `/internal/store_payee`, rewrite the
    text to [[CARD:alias]], delete the owner's raw message in Telegram, continue with the token.
 Everything fails CLOSED: any error drops the message (Hermes treats a hook exception as "allow",
 which would leak the raw number). Only metadata is ever logged, never text or numbers.
"""
import json
import logging
import os
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger("cardguard")
VAULT_URL = os.environ.get("VAULT_TOOLS_URL", "http://vault-tools:8000")
TTL_FILE = os.environ.get("CARDGUARD_TTL_FILE", "/opt/data/ttl/rincian.jsonl")
TTL_SECONDS = int(os.environ.get("RINCIAN_TTL_SECONDS", "86400"))
_CANDIDATE = re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")
_ttl_lock = threading.Lock()


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


def replace_numbers(text: str, alias_by_digits: dict[str, str]) -> str:
    def repl(m):
        d = _digits_of(m.group(0))
        return f"[[CARD:{alias_by_digits[d]}]]" if d else m.group(0)
    return _CANDIDATE.sub(repl, text)


# ---- vault-tools internal API ---------------------------------------------------------

def _post(path: str, body: dict, timeout: int = 8) -> tuple[int, bytes]:
    token = os.environ.get("VAULT_TOOLS_INTERNAL_TOKEN", "")
    req = urllib.request.Request(VAULT_URL + path, json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {token}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


# ---- Telegram Bot API (vault bot token, this process only) ----------------------------

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


def _delete_async(event, deleter=None) -> None:
    """Delete the owner's raw message (incoming, private chat, <48h). dm chats only."""
    src = getattr(event, "source", None)
    if getattr(src, "chat_type", None) != "dm":
        return
    chat_id, mid = getattr(src, "chat_id", None), getattr(event, "message_id", None)
    if chat_id is None or mid is None:
        return
    fn = deleter or (lambda c, m: log.info("cardguard: deleteMessage %s for message %s",
                                           "ok" if _bot("deleteMessage", chat_id=c, message_id=m) else "FAILED", m))
    threading.Thread(target=fn, args=(chat_id, mid), daemon=True).start()


def _notify(event, text: str) -> None:
    chat_id = getattr(getattr(event, "source", None), "chat_id", None)
    if chat_id is not None:
        _bot("sendMessage", chat_id=chat_id, text=text, disable_web_page_preview="true")


# ---- /rincian auto-delete -------------------------------------------------------------

def _ttl_record(chat_id, message_id) -> None:
    os.makedirs(os.path.dirname(TTL_FILE), exist_ok=True)
    with _ttl_lock, open(TTL_FILE, "a") as f:
        f.write(json.dumps({"c": chat_id, "m": message_id, "exp": time.time() + TTL_SECONDS}) + "\n")


def sweep_ttl(now: float | None = None, deleter=None) -> int:
    """Delete recorded messages past their TTL; keep the rest. Returns number deleted."""
    now = now or time.time()
    deleter = deleter or (lambda c, m: _bot("deleteMessage", chat_id=c, message_id=m))
    with _ttl_lock:
        try:
            with open(TTL_FILE) as f:
                rows = [json.loads(line) for line in f if line.strip()]
        except FileNotFoundError:
            return 0
        keep, gone = [], 0
        for r in rows:
            if r["exp"] <= now:
                deleter(r["c"], r["m"])
                gone += 1
            else:
                keep.append(r)
        with open(TTL_FILE, "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in keep)
    return gone


def _sweeper_loop() -> None:
    while True:
        time.sleep(900)
        try:
            sweep_ttl()
        except Exception:  # noqa: BLE001
            log.error("cardguard: ttl sweep failed")


# ---- hook ------------------------------------------------------------------------------

def _rincian(event):
    status, body = _post("/internal/rincian", {})
    if status != 200:
        log.error("cardguard: rincian failed status=%s", status)
        _notify(event, "Gagal mengambil rincian. Coba lagi nanti.")
        return {"action": "skip"}
    src = event.source
    sent = _bot("sendMessage", chat_id=src.chat_id, text=body.decode(), parse_mode="Markdown",
                disable_web_page_preview="true")
    if sent and "message_id" in sent:
        _ttl_record(src.chat_id, sent["message_id"])
        log.info("cardguard: rincian sent, auto-delete in %ss", TTL_SECONDS)
    else:
        log.error("cardguard: rincian send failed")
    return {"action": "skip"}


def on_inbound(event, **kwargs):
    try:
        text = getattr(event, "text", None)
        if not text:
            return None
        private = getattr(getattr(event, "source", None), "chat_type", None) == "dm"
        if private and text.strip().lower() == "/rincian":
            return _rincian(event)
        digits_list = find_numbers(text)
        if not digits_list:
            return None
        if not private:
            return {"action": "skip"}
        mapping = {}
        for digits in dict.fromkeys(digits_list):
            status, raw = _post("/internal/store_payee",
                                {"alias": f"num-{digits[-4:]}", "kind": "card", "bank": "?",
                                 "number": digits, "raw_text": text})
            body = json.loads(raw or b"{}")
            if status == 422 and body.get("error") == "cvv_or_expiry_rejected":
                _delete_async(event)
                _notify(event, "Jangan kirim CVV atau tanggal kedaluwarsa. Pesan dihapus dan tidak disimpan.")
                return {"action": "skip"}
            if not body.get("ok"):
                log.error("cardguard: store failed status=%s message=%s", status, getattr(event, "message_id", "?"))
                _delete_async(event)
                _notify(event, "Gagal menyimpan nomor dengan aman. Pesan dihapus; coba kirim lagi nanti.")
                return {"action": "skip"}
            mapping[digits] = body["alias"]
        log.info("cardguard rewrote %d number(s) in message %s", len(mapping), getattr(event, "message_id", "?"))
        _delete_async(event)
        return {"action": "rewrite", "text": replace_numbers(text, mapping)}
    except Exception:  # noqa: BLE001 - fail closed, see module docstring
        log.error("cardguard failed; dropping message %s", getattr(event, "message_id", "?"))
        return {"action": "skip"}


_started = False


def register(ctx):
    global _started
    ctx.register_hook("pre_gateway_dispatch", on_inbound)
    if not _started:
        _started = True
        threading.Thread(target=_sweeper_loop, daemon=True).start()
