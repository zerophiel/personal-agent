"""control bot (M3): deterministic approvals, NO LLM.

Long-polls Telegram and answers only the owner in a private chat; everything else is dropped silently and logged.
Change proposals arrive as JSON files in the inbox folder, written by the change-proposals MCP on net-front (control is on
net-ctl: that folder is all the two share). Each valid proposal is posted to the owner as a diff control computes from the
installed files (read-only mounts of the front tree and the squid confs, never text the agent wrote about its change),
then as a card with Setujui/Tolak buttons that carry a one-time nonce. The decision is kept in the state folder
(control.db, decided/<id>.json and, when approved, approved/<id>.json with the review: each file's hash when the diff was
made and whether the owner saw that diff whole). Only control writes the state folder, so nothing the MCP writes can pass
for an approval. The applier (services/applier, a root host unit) reads approved/ only and writes its outcome to a folder
mounted read-only here, which control reports once (docs/SECURITY.md).
"""
from __future__ import annotations

import difflib
import hashlib
import json
import logging
import os
import re
import secrets
import shutil
import sqlite3
import stat
import time
import unicodedata
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger("control")

ZONES = ("front", "comms", "vault")
# Where each kind of change may write ({zone} filled in; a trailing / is a folder). Everything else is refused before the
# owner sees it: host scripts, compose, plugins, control and secrets never change through a button (a new service is an
# escalation, a secret value goes through make secret-set; a credential proposal only asks for one, so it has no files).
PATHS = {
    "skill": ("services/hermes/{zone}/skills/",),
    "mcp": ("services/hermes/{zone}/config.yaml",),
    "tool": ("services/hermes/{zone}/config.yaml",),
    "toolset": ("services/hermes/{zone}/config.yaml",),
    "schedule": ("services/hermes/{zone}/config.yaml",),
    "config": ("services/hermes/{zone}/config.yaml", "services/hermes/{zone}/SOUL.md"),
    "egress_domain": ("config/squid/{zone}.conf",),
    "credential": (),
}
CHANGE_TYPES = tuple(PATHS)
TEXT_LIMITS = {"summary": 500, "permission_diff": 2000, "risk_notes": 1000, "rollback": 1000}
MAX_FILES, MAX_FILE_CHARS, MAX_INBOX_BYTES, MAX_PENDING = 20, 50_000, 1_200_000, 5
SAFE_PATH = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./-]{0,199}")
NONCE = re.compile(r"[0-9a-f]{32}")
HELP = ("control (tanpa LLM): /status, /usulan (usulan perubahan yang menunggu keputusan), /ping. Usulan dari agen lain "
        "datang dengan tombol Setujui/Tolak; hanya kamu yang bisa menekannya, dan setiap tombol hanya berlaku sekali.")
# The files the applier writes and the service each is mounted into. services/applier/applier.py (FRONT_FILES) decides
# on its own; control only uses this to tell the owner whether a tap changes something or waits for a human, and a test
# keeps the two equal.
AUTO_APPLY = {"services/hermes/front/config.yaml": "front", "services/hermes/front/SOUL.md": "front",
              "config/squid/front.conf": "squid-front"}
SERVICE_NAMES = {"front": "front (@danoefront_agent)", "squid-front": "proxy front"}
REPO_MOUNTS = ("services/hermes/front/", "config/squid/")   # mounted read-only under the repo folder (compose)
DIFF_LIMIT = 3000           # one Telegram message with its header and notes (at most 4096 characters)
OUTCOMES = ("applied", "refused", "rolled_back", "rollback_failed")
OUTCOME_FILE = re.compile(r"(\d{1,9})\.json")


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


def path_allowed(path: str, zone: str, change_type: str) -> bool:
    if not SAFE_PATH.fullmatch(path) or ".." in path.split("/") or "//" in path:
        return False
    return any((path.startswith(p) and len(path) > len(p)) if p.endswith("/") else path == p
               for p in (x.format(zone=zone) for x in PATHS[change_type]))


def validate(raw: object) -> dict:
    """A proposal as control accepts it, else ValueError: these fields and no others, zone and change type from fixed lists,
    lengths capped, files only where that change type may write (PATHS). The text is the model's: shown, never run."""
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
    allowed = [x.format(zone=out["zone"]) for x in PATHS[out["change_type"]]]
    if not allowed and files:
        raise ValueError(f"usulan {out['change_type']} tidak berisi file")
    if allowed and not files:
        raise ValueError(f"usulan {out['change_type']} perlu file yang diubah")
    out["files"] = []
    for f in files:
        if not isinstance(f, dict) or set(f) != {"path", "content"} or not all(isinstance(v, str) for v in f.values()):
            raise ValueError("setiap file berisi path dan content (teks)")
        if not path_allowed(f["path"], out["zone"], out["change_type"]):
            raise ValueError(f"usulan {out['change_type']} untuk zona {out['zone']} hanya boleh mengubah: {', '.join(allowed)}")
        if len(f["content"]) > MAX_FILE_CHARS:
            raise ValueError(f"isi file lebih dari {MAX_FILE_CHARS} karakter")
        if f["path"] in (g["path"] for g in out["files"]):
            raise ValueError("satu path hanya boleh sekali")
        out["files"].append({"path": f["path"], "content": f["content"]})
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


def hidden_chars(path: str, text: str) -> list[str]:
    """What the owner would not see in a diff of this file, as U+XXXX: a config file (.yaml, .conf) may hold printable
    ASCII, tabs and newlines only (no look-alike letters either); any other file no control, format, private-use,
    unassigned or separator character but the space."""
    if path.endswith((".yaml", ".conf")):
        bad = {ch for ch in text if not (ch in "\n\t" or " " <= ch <= "~")}
    else:
        bad = {ch for ch in text if ch not in "\n\t" and (
            unicodedata.category(ch) in ("Cc", "Cf", "Co", "Cn", "Cs", "Zl", "Zp")
            or (unicodedata.category(ch) == "Zs" and ch != " "))}
    return sorted(f"U+{ord(ch):04X}" for ch in bad)


def read_installed(repo: Path, path: str) -> bytes | None:
    """An installed file through control's read-only mounts of the tree: None when it does not exist, ValueError when
    control cannot see that folder or the file is not a small regular file (a link is never followed)."""
    mount = next((m for m in REPO_MOUNTS if path.startswith(m)), None)
    if mount is None or not (repo / mount).is_dir():
        raise ValueError("foldernya tidak di-mount ke control")
    try:
        fd = os.open(repo / path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        return None
    except OSError as e:
        raise ValueError("bukan file biasa") from e
    with os.fdopen(fd, "rb") as f:
        st = os.fstat(f.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_INBOX_BYTES:
            raise ValueError("bukan file biasa" if not stat.S_ISREG(st.st_mode) else "file terlalu besar")
        return f.read(MAX_INBOX_BYTES + 1)


def sha(data: bytes | None) -> str | None:
    return None if data is None else hashlib.sha256(data).hexdigest()


def review_of(p: dict, repo: Path) -> tuple[dict, str]:
    """The review of a proposal and the diff control posts before its card, computed here from the installed files.
    diff_shown is True only when the owner sees every change whole and as it is: each file readable here, nothing hidden
    in the new content, and the whole diff in one message (links defanged as everywhere else)."""
    base, chunks, why = {}, [], []
    for f in p["files"]:
        path = f["path"]
        try:
            old = read_installed(repo, path)
            before = "" if old is None else old.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as e:
            base[path] = None
            why.append(f"{path} yang terpasang tidak terbaca control ({e if isinstance(e, ValueError) else 'bukan UTF-8'})")
            chunks.append(f"{path}: isi yang terpasang tidak terbaca, diff-nya tidak bisa dibuat")
            continue
        base[path] = sha(old)
        hidden = hidden_chars(path, f["content"])
        if hidden:
            why.append(f"{path} berisi karakter yang tidak terlihat ({', '.join(hidden[:5])})")
        lines = list(difflib.unified_diff(before.split("\n"), f["content"].split("\n"),
                                          "/dev/null" if old is None else f"a/{path}", f"b/{path}", n=2, lineterm=""))
        chunks.append("\n".join(lines) if lines else f"{path}: isinya sama dengan yang terpasang")
    body = shown("\n\n".join(chunks), MAX_FILES * MAX_FILE_CHARS * 4)
    if len(body) > DIFF_LIMIT:
        why.append(f"diff-nya {len(body):,} karakter, lebih dari satu pesan".replace(",", "."))
        body = body[: DIFF_LIMIT - 15] + "\n… (terpotong)"
    review = {"base_sha256": base, "diff_shown": not why}
    if why:
        review["why"] = "; ".join(why)[:500]
    return review, body


def auto_reason(p: dict, review: dict | None) -> str | None:
    """Why the applier will not apply this proposal, for the card and the reply; None when it will try (it then checks
    everything again on its own: services/applier/applier.py)."""
    if p["zone"] != "front":
        return f"zona {p['zone']} dibangun manusia"
    if p["change_type"] == "credential":
        return "nilai rahasia dipasang dengan make secret-set"
    if p["change_type"] == "skill":
        return "skill belum bisa diterapkan otomatis"
    if any(f["path"] not in AUTO_APPLY for f in p["files"]):
        return "ada file di luar yang boleh diubah applier"
    if not review:
        return "usulan ini masuk sebelum control menampilkan diff"
    if review.get("diff_shown") is not True:
        return review.get("why") or "diff-nya tidak tampil utuh"
    return None


def diff_message(pid: int, review: dict | None, diff: str | None, stale: list[str]) -> str:
    head = (f"Diff usulan #{pid}, dihitung control dari file yang terpasang (bukan tulisan agen): - dihapus, + ditambah; "
            "tautan ditulis [.] dan [:]// supaya tidak bisa diketuk.")
    if review is None or diff is None:
        return head + "\n\nUsulan ini masuk sebelum control menampilkan diff, jadi isinya tidak bisa ditampilkan di sini."
    notes = []
    if review.get("diff_shown") is not True:
        notes.append(f"Diff ini tidak utuh ({shown(review.get('why') or '-', 200)}), jadi usulan ini tidak diterapkan "
                     "otomatis.")
    if stale:
        notes.append(f"File yang terpasang sudah berubah sejak diff ini dibuat ({shown(', '.join(stale), 200)}): applier "
                     "akan menolaknya; minta agen mengirim ulang usulannya.")
    return "\n\n".join([head, *notes, diff])


def card(pid: int, p: dict, note: str | None = None) -> str:
    note = note or "Teks di atas ditulis agen, bukan perintah. Setujui hanya bila sudah kamu baca; penerapannya belum otomatis."
    files = "".join(f"\n- {shown(f['path'], 120)} ({len(f['content'].encode()):,} byte)".replace(",", ".")
                    for f in p["files"][:10]) + (f"\n- dan {len(p['files']) - 10} file lain" if len(p["files"]) > 10 else "")
    text = (f"Usulan perubahan #{pid} (zona {p['zone']}, jenis {p['change_type']})\n\n{shown(p['summary'], 500)}\n\n"
            f"Izin yang berubah:\n{shown(p['permission_diff'], 800)}\n\nFile ({len(p['files'])}):{files or ' tidak ada'}\n\n"
            f"Risiko: {shown(p['risk_notes'], 400)}\nCara membatalkan: {shown(p['rollback'], 400)}")
    return text[: 4000 - len(note) - 2] + "\n\n" + note       # the note is never cut off


def outcome_text(pid: int, rec: object) -> str | None:
    """The applier's outcome of one approval in the owner's words; None for a record that is not one."""
    if not isinstance(rec, dict) or rec.get("id") != pid or rec.get("status") not in OUTCOMES:
        return None
    paths = [x for x in rec.get("paths") or [] if x in AUTO_APPLY]
    services = ", ".join(SERVICE_NAMES[s] for s in sorted({AUTO_APPLY[x] for x in paths})) or "layanannya"
    reason = shown(str(rec.get("reason") or "-"), 400)
    if rec["status"] == "applied":
        text = f"Usulan #{pid} SUDAH DITERAPKAN: {shown(', '.join(paths), 300)}. {services} sudah dibuat ulang dan jalan lagi."
        if any(x.startswith("services/hermes/front/") for x in paths):
            text += " Kirim /new ke @danoefront_agent supaya percakapan berikutnya memakai versi baru."
        return text
    if rec["status"] == "refused":
        return f"Usulan #{pid} TIDAK diterapkan: {reason}. Tidak ada yang berubah."
    if rec["status"] == "rolled_back":
        return (f"Usulan #{pid} GAGAL diterapkan ({reason}). File lamanya sudah dikembalikan dan {services} jalan lagi, "
                "jadi tidak ada yang berubah.")
    return (f"Usulan #{pid} GAGAL diterapkan dan pengembaliannya juga gagal ({reason}). {services} mungkin tidak jalan; "
            "perlu manusia (RUNBOOK, bagian Applier).")         # no file name: Telegram links a bare name.md


def buttons(nonce: str) -> str:
    return json.dumps({"inline_keyboard": [[{"text": "✅ Setujui", "callback_data": f"a:{nonce}"},
                                            {"text": "❌ Tolak", "callback_data": f"r:{nonce}"}]]})


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def quiet(at: datetime | None = None) -> bool:
    """22:00-06:00 WIB: messages arrive without a sound."""
    h = ((at or datetime.now(timezone.utc)).astimezone(timezone.utc).hour + 7) % 24
    return h >= 22 or h < 6


def read_proposal(path: Path) -> object:
    """An inbox file's JSON; ValueError for anything but a small regular file. A link is never followed: the writer is
    another container, and a link could point at control's own secret or state."""
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as e:
        raise ValueError("bukan file biasa") from e
    st = os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_INBOX_BYTES:
        os.close(fd)
        raise ValueError("bukan file biasa" if not stat.S_ISREG(st.st_mode) else "file terlalu besar")
    with os.fdopen(fd, "rb") as f:
        try:
            return json.loads(f.read(MAX_INBOX_BYTES + 1).decode("utf-8"))
        except RecursionError as e:
            raise ValueError("JSON terlalu bertingkat") from e


def discard(path: Path) -> None:
    try:
        path.unlink()           # a link goes, never its target
    except IsADirectoryError:
        shutil.rmtree(path, ignore_errors=True)
    except FileNotFoundError:
        pass


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
            " reason TEXT NOT NULL);"
            "CREATE TABLE IF NOT EXISTS reported (id INTEGER PRIMARY KEY, status TEXT NOT NULL, at TEXT NOT NULL);")
        cols = {r[1] for r in self.db.execute("PRAGMA table_info(proposals)")}
        for col in ("review", "diff"):      # since the applier (2026-11-01); earlier proposals keep NULL
            if col not in cols:
                self.db.execute(f"ALTER TABLE proposals ADD COLUMN {col} TEXT")
        self.db.commit()

    def counts(self) -> dict:
        c = dict(self.db.execute("SELECT status, COUNT(*) FROM proposals GROUP BY status").fetchall())
        return {s: c.get(s, 0) for s in ("pending", "approved", "rejected")} | {
            "invalid": self.db.execute("SELECT COUNT(*) FROM invalid").fetchone()[0]}

    def add(self, body: dict, review: dict | None = None, diff: str | None = None) -> int:
        with self.db:
            return self.db.execute(
                "INSERT INTO proposals(received_at, body, status, nonce, review, diff) VALUES (?,?,'pending',?,?,?)",
                (now(), json.dumps(body, ensure_ascii=False), secrets.token_hex(16),
                 None if review is None else json.dumps(review, sort_keys=True), diff)).lastrowid

    def get(self, pid: int) -> tuple[dict, dict | None]:
        body, review = self.db.execute("SELECT body, review FROM proposals WHERE id=?", (pid,)).fetchone()
        return json.loads(body), None if review is None else json.loads(review)

    def reject_file(self, name: str, reason: str) -> None:
        with self.db:
            self.db.execute("INSERT INTO invalid(received_at, file, reason) VALUES (?,?,?)", (now(), name[:100], reason[:300]))

    def decide(self, nonce: str, approve: bool) -> int | None:
        """The proposal this nonce belongs to, decided once: None when the nonce is unknown, used or forged."""
        row = self.db.execute("SELECT id, body, received_at, review FROM proposals WHERE nonce=? AND status='pending'",
                              (nonce,)).fetchone()
        if row is None:
            return None
        status, at = ("approved" if approve else "rejected"), now()
        with self.db:
            if self.db.execute("UPDATE proposals SET status=?, decided_at=?, nonce=NULL WHERE id=? AND nonce=? AND "
                               "status='pending'", (status, at, row[0], nonce)).rowcount != 1:
                return None
        rec = {"id": row[0], **json.loads(row[1]), "status": status, "received_at": row[2], "decided_at": at,
               "review": None if row[3] is None else json.loads(row[3])}
        write_json(self.state / "decided" / f"{row[0]}.json", rec)
        if approve:     # the applier's input: written here only, after the owner's tap
            write_json(self.state / "approved" / f"{row[0]}.json", rec)
        return row[0]

    def reported(self) -> set[int]:
        return {r[0] for r in self.db.execute("SELECT id FROM reported")}

    def mark_reported(self, pid: int, status: str) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO reported(id, status, at) VALUES (?,?,?)", (pid, status, now()))

    def outcome_counts(self) -> dict:
        c = dict(self.db.execute("SELECT status, COUNT(*) FROM reported GROUP BY status").fetchall())
        return {s: c.get(s, 0) for s in OUTCOMES}


def handle(update: dict, store: Store | None = None, installed: bool = False) -> str | None:
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
        if not installed:
            return (f"control: ok. Usulan menunggu keputusan: {c['pending']}; disetujui (belum diterapkan, applier belum "
                    f"aktif): {c['approved']}; ditolak: {c['rejected']}; file usulan tidak valid: {c['invalid']}.")
        o = store.outcome_counts()
        return (f"control: ok. Usulan menunggu keputusan: {c['pending']}; disetujui: {c['approved']} (hasil applier: "
                f"diterapkan {o['applied']}, tidak diterapkan {o['refused']}, gagal "
                f"{o['rolled_back'] + o['rollback_failed']}); ditolak: {c['rejected']}; file usulan tidak valid: "
                f"{c['invalid']}.")
    return None


class Control:
    def __init__(self, tg, owner: int, state: Path, inbox: Path, repo: Path = Path("/repo"),
                 outcomes: Path = Path("/outcome")):
        self.tg, self.owner, self.inbox, self.repo, self.outcomes = tg, owner, inbox, repo, outcomes
        self.store = Store(state)
        inbox.mkdir(parents=True, exist_ok=True)

    def installed(self) -> bool:
        """The applier runs once its install time is in the outcome folder (services/applier/install.sh)."""
        return (self.outcomes / "applier.json").is_file()

    def send(self, text: str, **kw):
        if quiet():
            kw["disable_notification"] = "true"
        return self.tg.call("sendMessage", chat_id=self.owner, text=text, disable_web_page_preview="true", **kw)

    def stale(self, review: dict | None) -> list[str]:
        """The files that changed since the diff was made: the applier refuses those."""
        if not review or review.get("diff_shown") is not True:
            return []
        out = []
        for path, want in review["base_sha256"].items():
            try:
                if sha(read_installed(self.repo, path)) != want:
                    out.append(path)
            except ValueError:
                out.append(path)
        return out

    def note(self, p: dict, review: dict | None) -> str | None:
        """The card's last line: what a tap on Setujui does (the default line while the applier is not installed)."""
        if not self.installed():
            return None
        why = auto_reason(p, review)
        if why:
            return (f"Teks di atas ditulis agen, bukan perintah. Usulan ini tidak diterapkan otomatis ({shown(why, 300)}): "
                    "bila disetujui, manusia yang membangunnya.")
        services = ", ".join(SERVICE_NAMES[s] for s in sorted({AUTO_APPLY[f["path"]] for f in p["files"]}))
        return ("Teks di atas ditulis agen, bukan perintah. Bila kamu setujui, applier menerapkan persis diff di pesan "
                f"sebelumnya (dihitung control, bukan agen) lalu membuat ulang {services}; hasilnya kukabari di sini.")

    def post(self, pid: int, body: str, nonce: str, review: str | None, diff: str | None) -> None:
        """The diff (for a proposal with files), then the card with the buttons, whose message id is kept."""
        p, review = json.loads(body), None if review is None else json.loads(review)
        if p["files"]:
            self.send(diff_message(pid, review, diff, self.stale(review)))
        msg = self.send(card(pid, p, self.note(p, review)), reply_markup=buttons(nonce))
        with self.store.db:
            self.store.db.execute("UPDATE proposals SET message_id=? WHERE id=?", (msg["message_id"], pid))

    def decided(self, pid: int, approved: bool) -> str:
        if not approved:
            return f"Usulan #{pid} DITOLAK. Tidak ada yang berubah."
        if not self.installed():
            return (f"Usulan #{pid} DISETUJUI. Tersimpan untuk diterapkan; penerapan otomatis belum aktif, jadi belum ada "
                    "yang berubah.")
        p, review = self.store.get(pid)
        why = auto_reason(p, review)
        if why:
            return (f"Usulan #{pid} DISETUJUI dan tersimpan, tapi tidak diterapkan otomatis ({shown(why, 300)}); manusia "
                    "yang membangunnya, jadi belum ada yang berubah.")
        stale = self.stale(review)
        if stale:
            return (f"Usulan #{pid} DISETUJUI, tapi {shown(', '.join(stale), 200)} sudah berubah sejak diff-nya dibuat: "
                    "applier akan menolaknya, jadi tidak ada yang berubah. Minta agen mengirim ulang usulannya.")
        return (f"Usulan #{pid} DISETUJUI. Applier memeriksanya dulu (aturan zona, dan file yang terpasang belum berubah "
                "sejak diff-nya), lalu menerapkannya; hasilnya kukabari di sini.")

    def report(self) -> None:
        """Each outcome the applier wrote (outcome/<id>.json, root's, read-only here) told to the owner once."""
        if not self.outcomes.is_dir():
            return
        done = self.store.reported()
        ids = sorted(int(m.group(1)) for p in self.outcomes.iterdir() if (m := OUTCOME_FILE.fullmatch(p.name)))
        for pid in (i for i in ids if i not in done):
            try:
                rec = read_proposal(self.outcomes / f"{pid}.json")
            except ValueError:
                log.warning("outcome %d not readable", pid)
                continue
            text = outcome_text(pid, rec)
            if text is None:
                log.warning("outcome %d is not an outcome record", pid)
                continue
            self.send(text)
            self.store.mark_reported(pid, rec["status"])

    def tick(self) -> None:
        """New proposal files into the store with their review (at most MAX_PENDING waiting; the rest stay in the inbox
        until then), invalid ones recorded and reported; every pending proposal not yet posted is posted; then the
        applier's new outcomes are reported."""
        for path in sorted(self.inbox.glob("*.json"))[:20]:     # writers rename <name>.json.tmp to <name>.json when done
            if self.store.counts()["pending"] >= MAX_PENDING:
                break
            try:
                body = validate(read_proposal(path))
            except ValueError as e:      # JSON and UTF-8 decode errors are ValueErrors
                self.store.reject_file(path.name, str(e))
                discard(path)
                self.send(f"Satu file usulan ditolak otomatis, formatnya tidak valid: {shown(str(e), 300)}")
                continue
            self.store.add(body, *review_of(body, self.repo))
            discard(path)
        for row in self.store.db.execute("SELECT id, body, nonce, review, diff FROM proposals WHERE status='pending' AND "
                                         "message_id IS NULL ORDER BY id").fetchall():
            self.post(*row)
        self.report()

    def on_update(self, u: dict) -> None:
        if "callback_query" in u:
            cq = u["callback_query"]
            kind, _, nonce = (cq.get("data") or "").partition(":")
            pid = self.store.decide(nonce, kind == "a") if kind in ("a", "r") and NONCE.fullmatch(nonce) else None
            self.tg.call("answerCallbackQuery", callback_query_id=cq["id"],
                         text=("Disetujui" if kind == "a" else "Ditolak") if pid else "Sudah diputuskan atau tidak berlaku")
            if "message" in cq:         # the buttons go either way: they are spent or stale
                try:
                    self.tg.call("editMessageReplyMarkup", chat_id=self.owner, message_id=cq["message"]["message_id"],
                                 reply_markup=json.dumps({"inline_keyboard": []}))
                except Exception as e:  # e.g. a message too old to edit; the decision stands and is still reported
                    log.warning("button removal failed: %s", type(e).__name__)
            if pid:
                self.send(self.decided(pid, kind == "a"))
            return
        text = (u.get("message") or {}).get("text", "").strip()
        if text == "/usulan":
            rows = self.store.db.execute("SELECT id, body, nonce, review, diff FROM proposals WHERE status='pending' "
                                         "ORDER BY id").fetchall()
            if not rows:
                self.send("Tidak ada usulan yang menunggu keputusan.")
            for row in rows:            # posted again with the same diff and the same one-time buttons
                self.post(*row)
            return
        reply = handle(u, self.store, self.installed())
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
                  Path(os.environ.get("PROPOSALS_INBOX_DIR", "/inbox")), Path(os.environ.get("CONTROL_REPO_DIR", "/repo")),
                  Path(os.environ.get("APPLIER_OUTCOME_DIR", "/outcome")))
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
