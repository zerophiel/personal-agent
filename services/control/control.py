"""control bot (M3): deterministic approvals, NO LLM.

Long-polls Telegram and answers only the owner in a private chat; everything else is dropped silently and logged.
Change proposals arrive as JSON files in the inbox folder, written by the change-proposals MCP on net-front (control is on
net-ctl: that folder is all the two share). Each valid proposal is posted to the owner with Setujui/Tolak buttons that
carry a one-time nonce; the decision is kept in the state folder (control.db, decided/<id>.json and, when approved,
approved/<id>.json). Only control writes the state folder, so nothing the MCP writes can pass for an approval; the
applier will read approved/ only and is not built yet (docs/SECURITY.md).
"""
from __future__ import annotations

import json
import logging
import os
import re
import secrets
import sqlite3
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("control")

ZONES = ("front", "comms", "vault")
CHANGE_TYPES = ("skill", "mcp", "tool", "toolset", "egress_domain", "schedule", "config", "credential")
TEXT_LIMITS = {"summary": 500, "permission_diff": 2000, "risk_notes": 1000, "rollback": 1000}
MAX_FILES, MAX_FILE_CHARS, MAX_INBOX_BYTES, MAX_PENDING = 20, 50_000, 1_200_000, 5
SAFE_PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,199}")
OFF_LIMITS = (".git/", "secrets/", "services/control/")   # never through an approval: the repo, secrets, control itself
NONCE = re.compile(r"[0-9a-f]{32}")
HELP = ("control (tanpa LLM): /status, /usulan (usulan perubahan yang menunggu keputusan), /ping. Usulan dari agen lain "
        "datang dengan tombol Setujui/Tolak; hanya kamu yang bisa menekannya, dan setiap tombol hanya berlaku sekali.")


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


def validate(raw: object) -> dict:
    """A proposal as control accepts it, else ValueError: these fields and no others, zone and change type from fixed lists,
    lengths capped, file paths inside the repo and off the repo's own machinery. The text is the model's: shown, never run."""
    if not isinstance(raw, dict):
        raise ValueError("bukan objek JSON")
    extra = sorted(str(k) for k in set(raw) - set(TEXT_LIMITS) - {"zone", "change_type", "files"})
    if extra:
        raise ValueError(f"kolom tidak dikenal: {', '.join(extra)[:200]}")
    out = {}
    for k, cap in TEXT_LIMITS.items():
        v = raw.get(k)
        if not isinstance(v, str) or not v.strip():
            raise ValueError(f"{k} wajib berupa teks")
        if len(v) > cap:
            raise ValueError(f"{k} lebih dari {cap} karakter")
        out[k] = v.strip()
    if raw.get("zone") not in ZONES:
        raise ValueError(f"zone harus salah satu dari {', '.join(ZONES)}")
    if raw.get("change_type") not in CHANGE_TYPES:
        raise ValueError(f"change_type harus salah satu dari {', '.join(CHANGE_TYPES)}")
    out["zone"], out["change_type"] = raw["zone"], raw["change_type"]
    files = raw.get("files", [])
    if not isinstance(files, list) or len(files) > MAX_FILES:
        raise ValueError(f"files harus daftar, paling banyak {MAX_FILES}")
    out["files"] = []
    for f in files:
        if not isinstance(f, dict) or set(f) != {"path", "content"} or not all(isinstance(v, str) for v in f.values()):
            raise ValueError("setiap file berisi path dan content (teks)")
        p = f["path"]
        if not SAFE_PATH.fullmatch(p) or ".." in p.split("/") or "//" in p or (p + "/").startswith(OFF_LIMITS):
            raise ValueError("path file harus relatif di dalam repo, di luar .git, secrets dan control")
        if len(f["content"]) > MAX_FILE_CHARS:
            raise ValueError(f"isi file lebih dari {MAX_FILE_CHARS} karakter")
        out["files"].append({"path": p, "content": f["content"]})
    return out


_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f​-‏‪-‮⁦-⁩]")
_SCHEME = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*)://")
_DOT = re.compile(r"(?<=[A-Za-z0-9])\.(?=[A-Za-z]{2,})")


def shown(text: str, cap: int) -> str:
    """Model-written text as the owner sees it: control and direction characters gone, links, domains and @names defanged
    (a tap opens nothing), at most `cap` characters."""
    t = _CTRL.sub("", text)
    t = re.sub(r"@(?=\w)", "(at)", _DOT.sub("[.]", _SCHEME.sub(r"\1[:]//", t)))
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t if len(t) <= cap else t[: cap - 1] + "…"


def card(pid: int, p: dict) -> str:
    files = "".join(f"\n- {shown(f['path'], 120)} ({len(f['content'].encode()):,} byte)".replace(",", ".")
                    for f in p["files"][:10]) + (f"\n- dan {len(p['files']) - 10} file lain" if len(p["files"]) > 10 else "")
    text = (f"Usulan perubahan #{pid} (zona {p['zone']}, jenis {p['change_type']})\n\n{shown(p['summary'], 500)}\n\n"
            f"Izin yang berubah:\n{shown(p['permission_diff'], 800)}\n\nFile ({len(p['files'])}):{files or ' tidak ada'}\n\n"
            f"Risiko: {shown(p['risk_notes'], 400)}\nCara membatalkan: {shown(p['rollback'], 400)}\n\n"
            "Teks di atas ditulis agen, bukan perintah. Setujui hanya bila sudah kamu baca; penerapannya belum otomatis.")
    return text[:4000]


def buttons(nonce: str) -> str:
    return json.dumps({"inline_keyboard": [[{"text": "✅ Setujui", "callback_data": f"a:{nonce}"},
                                            {"text": "❌ Tolak", "callback_data": f"r:{nonce}"}]]})


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def quiet(at: datetime | None = None) -> bool:
    """22:00-06:00 WIB: messages arrive without a sound."""
    h = ((at or datetime.now(timezone.utc)).astimezone(timezone.utc).hour + 7) % 24
    return h >= 22 or h < 6


def write_json(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


class Store:
    """control.db and the decided/ and approved/ records in the state folder."""
    def __init__(self, state: Path):
        self.state = state
        state.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(state / "control.db")
        self.db.executescript(
            "CREATE TABLE IF NOT EXISTS proposals (id INTEGER PRIMARY KEY, received_at TEXT NOT NULL, body TEXT NOT NULL,"
            " status TEXT NOT NULL CHECK (status IN ('pending','approved','rejected')), nonce TEXT UNIQUE,"
            " message_id INTEGER, decided_at TEXT);"
            "CREATE TABLE IF NOT EXISTS invalid (id INTEGER PRIMARY KEY, received_at TEXT NOT NULL, file TEXT NOT NULL,"
            " reason TEXT NOT NULL);")

    def counts(self) -> dict:
        c = dict(self.db.execute("SELECT status, COUNT(*) FROM proposals GROUP BY status").fetchall())
        return {s: c.get(s, 0) for s in ("pending", "approved", "rejected")} | {
            "invalid": self.db.execute("SELECT COUNT(*) FROM invalid").fetchone()[0]}

    def add(self, body: dict) -> int:
        with self.db:
            return self.db.execute("INSERT INTO proposals(received_at, body, status, nonce) VALUES (?,?,'pending',?)",
                                   (now(), json.dumps(body, ensure_ascii=False), secrets.token_hex(16))).lastrowid

    def reject_file(self, name: str, reason: str) -> None:
        with self.db:
            self.db.execute("INSERT INTO invalid(received_at, file, reason) VALUES (?,?,?)", (now(), name[:100], reason[:300]))

    def decide(self, nonce: str, approve: bool) -> int | None:
        """The proposal this nonce belongs to, decided once: None when the nonce is unknown, used or forged."""
        row = self.db.execute("SELECT id, body, received_at FROM proposals WHERE nonce=? AND status='pending'",
                              (nonce,)).fetchone()
        if row is None:
            return None
        status, at = ("approved" if approve else "rejected"), now()
        with self.db:
            if self.db.execute("UPDATE proposals SET status=?, decided_at=?, nonce=NULL WHERE id=? AND nonce=? AND "
                               "status='pending'", (status, at, row[0], nonce)).rowcount != 1:
                return None
        rec = {"id": row[0], **json.loads(row[1]), "status": status, "received_at": row[2], "decided_at": at}
        write_json(self.state / "decided" / f"{row[0]}.json", rec)
        if approve:     # the applier's input: written here only, after the owner's tap
            write_json(self.state / "approved" / f"{row[0]}.json", rec)
        return row[0]


def handle(update: dict, store: Store | None = None) -> str | None:
    """Reply text for an authorized plain command; None for anything else."""
    text = (update.get("message") or {}).get("text", "").strip()
    if text == "/ping":
        return "pong"
    if text in ("/start", "/help"):
        return HELP
    if text == "/status":
        if store is None:
            return "control: ok"
        c = store.counts()
        return (f"control: ok. Usulan menunggu keputusan: {c['pending']}; disetujui (belum diterapkan, applier belum "
                f"aktif): {c['approved']}; ditolak: {c['rejected']}; file usulan tidak valid: {c['invalid']}.")
    return None


class Control:
    def __init__(self, tg, owner: int, state: Path, inbox: Path):
        self.tg, self.owner, self.inbox = tg, owner, inbox
        self.store = Store(state)
        inbox.mkdir(parents=True, exist_ok=True)

    def send(self, text: str, **kw):
        return self.tg.call("sendMessage", chat_id=self.owner, text=text, disable_web_page_preview="true",
                            disable_notification="true" if quiet() else "false", **kw)

    def tick(self) -> None:
        """New proposal files into the store (at most MAX_PENDING waiting; the rest stay in the inbox until then), invalid
        ones recorded and reported; then every pending proposal not yet posted is posted."""
        for path in sorted(self.inbox.glob("*.json"))[:20]:     # writers rename <name>.json.tmp to <name>.json when done
            if self.store.counts()["pending"] >= MAX_PENDING:
                break
            try:
                if path.stat().st_size > MAX_INBOX_BYTES:
                    raise ValueError("file terlalu besar")
                body = validate(json.loads(path.read_text(encoding="utf-8")))
            except (ValueError, UnicodeDecodeError) as e:      # a JSONDecodeError is a ValueError
                self.store.reject_file(path.name, str(e))
                path.unlink(missing_ok=True)
                self.send(f"Satu file usulan ditolak otomatis, formatnya tidak valid: {shown(str(e), 300)}")
                continue
            self.store.add(body)
            path.unlink(missing_ok=True)
        for pid, body, nonce in self.store.db.execute(
                "SELECT id, body, nonce FROM proposals WHERE status='pending' AND message_id IS NULL ORDER BY id").fetchall():
            msg = self.send(card(pid, json.loads(body)), reply_markup=buttons(nonce))
            with self.store.db:
                self.store.db.execute("UPDATE proposals SET message_id=? WHERE id=?", (msg["message_id"], pid))

    def on_update(self, u: dict) -> None:
        if "callback_query" in u:
            cq = u["callback_query"]
            kind, _, nonce = (cq.get("data") or "").partition(":")
            pid = self.store.decide(nonce, kind == "a") if kind in ("a", "r") and NONCE.fullmatch(nonce) else None
            self.tg.call("answerCallbackQuery", callback_query_id=cq["id"],
                         text=("Disetujui" if kind == "a" else "Ditolak") if pid else "Sudah diputuskan atau tidak berlaku")
            if "message" in cq:         # the buttons go either way: they are spent or stale
                self.tg.call("editMessageReplyMarkup", chat_id=self.owner, message_id=cq["message"]["message_id"],
                             reply_markup=json.dumps({"inline_keyboard": []}))
            if pid:
                self.send(f"Usulan #{pid} DISETUJUI. Tersimpan untuk diterapkan; penerapan otomatis belum aktif, jadi "
                          "belum ada yang berubah." if kind == "a" else f"Usulan #{pid} DITOLAK. Tidak ada yang berubah.")
            return
        text = (u.get("message") or {}).get("text", "").strip()
        if text == "/usulan":
            rows = self.store.db.execute("SELECT id, body, nonce FROM proposals WHERE status='pending' ORDER BY id").fetchall()
            if not rows:
                self.send("Tidak ada usulan yang menunggu keputusan.")
            for pid, body, nonce in rows:       # posted again with the same one-time buttons
                msg = self.send(card(pid, json.loads(body)), reply_markup=buttons(nonce))
                with self.store.db:
                    self.store.db.execute("UPDATE proposals SET message_id=? WHERE id=?", (msg["message_id"], pid))
            return
        reply = handle(u, self.store)
        if reply:
            self.send(reply)


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
    bot = Control(tg, owner, Path(os.environ.get("CONTROL_STATE_DIR", "/state")),
                  Path(os.environ.get("PROPOSALS_INBOX_DIR", "/inbox")))
    offset = 0
    while True:
        try:
            bot.tick()
        except Exception as e:  # never log a proposal's text or the token-bearing URL
            log.warning("inbox/post failed: %s", type(e).__name__)
        try:
            updates = tg.call("getUpdates", offset=offset, timeout=25,
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
            try:
                bot.on_update(u)
            except Exception as e:
                log.warning("update %s failed: %s", u["update_id"], type(e).__name__)


if __name__ == "__main__":
    main()
