"""cardguard: keep full card numbers out of the model's world, and serve the owner's slash commands (vault profile only).

pre_gateway_dispatch, in this order of precedence:
 1. "/rincian": ask vault-tools (internal API) for the transfer list WITH full numbers, send it
    straight to Telegram via the Bot API, record it for auto-deletion, and `skip` so Hermes never
    sees the reply or the command.
 2. Luhn-valid 13-19 digit numbers: store each via vault-tools `/internal/store_payee`, rewrite the
    text to [[CARD:alias]], delete the owner's raw message in Telegram, continue with the token.
 3. Report commands (/rencana, /tagihan, /cicilan, /anggaran, /peta, /kondisi, /data, /bantuan): vault-tools renders the
    text from the ledger, the plugin sends it and `skip`s (no model, no cost).
 The Telegram "/" menu is pushed by this plugin shortly after Hermes registers its own (the owner's list replaces the
 stock one). Everything fails CLOSED: any error drops the message (Hermes treats a hook exception as "allow",
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



# ---- report commands and the "/" menu --------------------------------------------------------

REPORTS = ("bantuan", "rencana", "tagihan", "cicilan", "anggaran", "peta", "kondisi", "data")
_REPORT_CMD = re.compile(r"^/(" + "|".join(REPORTS) + r")(?:@\w+)?\s*$", re.I)
MENU = [
    ("bantuan", "Apa saja yang bisa saya lakukan"),
    ("rencana", "Rencana gajian dan pembayaran terdekat"),
    ("tagihan", "Tagihan kartu terbuka dan jatuh tempo"),
    ("cicilan", "Cicilan kartu dan langganan"),
    ("anggaran", "Anggaran bulan ini dan pemakaiannya"),
    ("peta", "Peta jalan bebas utang"),
    ("kondisi", "Penilaian kesehatan keuangan"),
    ("data", "Ringkasan semua data yang tersimpan"),
    ("rincian", "Nomor tujuan transfer lengkap (terhapus 24 jam)"),
    ("rekening", "Simpan rekening: /rekening alias bank nomor"),
    ("va", "Simpan virtual account: /va alias bank nomor"),
    ("new", "Mulai percakapan baru (data tidak hilang)"),
    ("stop", "Hentikan proses yang sedang berjalan"),
]
MENU_FIRST_DELAY = int(os.environ.get("CARDGUARD_MENU_DELAY", "45"))
MENU_CHECK_EVERY = int(os.environ.get("CARDGUARD_MENU_CHECK", "120"))
_SCOPES = ({"type": "default"}, {"type": "all_private_chats"})


def push_menu() -> int:
    """setMyCommands in the scopes Hermes also writes, so the owner's list is the one Telegram shows."""
    cmds = json.dumps([{"command": c, "description": d} for c, d in MENU])
    return sum(1 for scope in _SCOPES if _bot("setMyCommands", commands=cmds, scope=json.dumps(scope)) is not None)


def menu_is_ours() -> bool:
    """True when Telegram already shows the owner's list in every scope (Hermes rewrites its stock menu on each
    (re)connect, at a moment we cannot predict, so we look instead of guessing)."""
    want = [{"command": c, "description": d} for c, d in MENU]
    for scope in _SCOPES:
        got = _bot("getMyCommands", scope=json.dumps(scope))
        if got is None or [{"command": g.get("command"), "description": g.get("description")} for g in got] != want:
            return False
    return True


def ensure_menu() -> bool:
    """Push only when the shown menu differs. Returns True when a push was needed."""
    if menu_is_ours():
        return False
    ok = push_menu()
    log.info("cardguard: command menu restored in %d scope(s)", ok)
    return True


def _menu_loop() -> None:
    time.sleep(MENU_FIRST_DELAY)
    while True:
        try:
            ensure_menu()
        except Exception:  # noqa: BLE001
            log.error("cardguard: command menu check failed")
        time.sleep(MENU_CHECK_EVERY)


def _chunks(text: str, limit: int = 3800) -> list[str]:
    """Split on blank lines (each paragraph is self-contained HTML), packing up to `limit` characters; a paragraph that is
    itself too long falls back to line, then hard, cuts."""
    parts, cur = [], ""
    for para in text.split("\n\n"):
        pieces = [para] if len(para) <= limit else [para[i:i + limit] for i in range(0, len(para), limit)]
        for piece in pieces:
            if cur and len(cur) + 2 + len(piece) > limit:
                parts.append(cur)
                cur = piece
            else:
                cur = f"{cur}\n\n{piece}" if cur else piece
    if cur:
        parts.append(cur)
    return parts


def _plain(html_text: str) -> str:
    import html as _html
    return _html.unescape(re.sub(r"</?(?:b|i|code|pre|u|s)>", "", html_text))


def _report(event, name: str):
    status, body = _post("/internal/report", {"name": name}, timeout=30)
    chat_id = event.source.chat_id
    if status != 200:
        log.error("cardguard: report %s failed status=%s", name, status)
        _notify(event, "Gagal mengambil laporan. Coba lagi nanti.")
        return {"action": "skip"}
    for part in _chunks(body.decode()):
        sent = _bot("sendMessage", chat_id=chat_id, text=part, parse_mode="HTML", disable_web_page_preview="true")
        if sent is None:                  # Telegram refused the markup: send the same text plain rather than nothing
            log.error("cardguard: report %s html rejected, sending plain", name)
            _bot("sendMessage", chat_id=chat_id, text=_plain(part), disable_web_page_preview="true")
    return {"action": "skip"}


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


_PAYEE_CMD = re.compile(r"^/(rekening|va)(?:@\w+)?(?:\s+(.*))?$", re.I | re.S)
_PAYEE_ARGS = re.compile(r"^([a-z0-9][a-z0-9-]{1,40})\s+([A-Za-z][A-Za-z0-9 ]{1,20}?)\s+([\d][\d -]{6,26}\d)$", re.I)
_USAGE = ("Format: /rekening <alias> <bank> <nomor>  (atau /va ...). Contoh: /rekening bca-rek BCA 1234567890. "
          "Pesan Anda dihapus dan nomor tidak disimpan.")


def _payee_command(event, text: str):
    """/rekening and /va: store an account/VA number straight into the vault, tell the owner, delete the
    message, and skip. The model never sees the number or the command."""
    m = _PAYEE_CMD.match(text.strip())
    kind = "account" if m.group(1).lower() == "rekening" else "va"
    args = _PAYEE_ARGS.match((m.group(2) or "").strip())
    _delete_async(event)
    if not args:
        _notify(event, _USAGE)
        return {"action": "skip"}
    alias, bank, number = args.group(1).lower(), " ".join(args.group(2).split()), re.sub(r"\D", "", args.group(3))
    if not 8 <= len(number) <= 24:
        _notify(event, _USAGE)
        return {"action": "skip"}
    status, raw = _post("/internal/store_payee", {"alias": alias, "kind": kind, "bank": bank, "number": number})
    body = json.loads(raw or b"{}")
    if status == 200 and body.get("ok"):
        again = " (nomor ini sudah tersimpan sebelumnya)" if body.get("duplicate") else ""
        _notify(event, f"Tersimpan: {body['alias']} ****{number[-4:]} ({bank}, {kind}){again}. Pesan Anda sudah dihapus.")
    else:
        log.error("cardguard: payee command failed status=%s", status)
        _notify(event, "Gagal menyimpan nomor dengan aman. Pesan dihapus; coba lagi nanti.")
    return {"action": "skip"}


def on_inbound(event, **kwargs):
    try:
        text = getattr(event, "text", None)
        if not text:
            return None
        private = getattr(getattr(event, "source", None), "chat_type", None) == "dm"
        m = _REPORT_CMD.match(text.strip())
        if private and m:
            return _report(event, m.group(1).lower())
        if private and text.strip().lower() == "/rincian":
            return _rincian(event)
        if private and _PAYEE_CMD.match(text.strip()):
            return _payee_command(event, text)
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
        threading.Thread(target=_menu_loop, daemon=True).start()
