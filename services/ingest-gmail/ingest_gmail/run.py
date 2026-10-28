"""Daily ingest: Gmail label -> verified statement PDFs in the drop folder + structured events.

No LLM. Untrusted email content is never copied into events: only a bank key, a hash-named
file and fixed reason codes (sender strings are reduced to a safe charset).
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from dataclasses import dataclass, field

from . import auth
from .client import GmailError, TokenError

LABEL = "Keuangan/Kartu Kredit"
MAX_ATTACHMENT = 15 * 1024 * 1024
RETENTION_DAYS = 90
SEARCH_DAYS = 400


@dataclass
class Config:
    senders: dict[str, str]          # lowercase address -> bank key
    drop_dir: str
    state_db: str
    org_domains: dict[str, str] = field(default_factory=dict)   # bank key -> parent domain
    label: str = LABEL
    retention_days: int = RETENTION_DAYS
    search_days: int = SEARCH_DAYS
    search_senders: list[str] = field(default_factory=list)   # also look up these allowlisted senders without a label


def emit(cfg: Config, event: dict, now=time.time) -> None:
    event = {"ts": int(now()), **event}
    with open(os.path.join(cfg.drop_dir, "_events.jsonl"), "a") as f:
        f.write(json.dumps(event, sort_keys=True) + "\n")


def _state(cfg: Config) -> sqlite3.Connection:
    conn = sqlite3.connect(cfg.state_db)
    conn.execute("CREATE TABLE IF NOT EXISTS processed (message_id TEXT PRIMARY KEY, status TEXT, ts INTEGER)")
    return conn


def _headers(msg: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for h in msg.get("payload", {}).get("headers", []):
        out.setdefault(h["name"].lower(), []).append(h["value"])
    return out


def _pdf_parts(part: dict):
    name = (part.get("filename") or "").lower()
    if part.get("body", {}).get("attachmentId") and (name.endswith(".pdf") or part.get("mimeType") == "application/pdf"):
        yield part
    for sub in part.get("parts", []) or []:
        yield from _pdf_parts(sub)


def _save_pdf(cfg: Config, data: bytes) -> str:
    """Write <sha256>.pdf atomically; the name comes from the content, never from the email."""
    name = hashlib.sha256(data).hexdigest() + ".pdf"
    path = os.path.join(cfg.drop_dir, name)
    if not os.path.exists(path):
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    return name


def process_message(client, cfg: Config, mid: str, now=time.time) -> str:
    msg = client.get_message(mid)
    headers = _headers(msg)
    addr, domain = auth.from_address(headers)
    bank = cfg.senders.get(addr)
    if bank is None:
        emit(cfg, {"type": "rejected", "reason": "sender_not_allowlisted", "from": auth.safe_label(addr)}, now)
        return "rejected_sender"
    ok, why = auth.auth_ok(headers, domain, cfg.org_domains.get(bank))
    if not ok:
        emit(cfg, {"type": "rejected", "reason": f"auth_failed:{why}", "bank": bank}, now)
        return "rejected_auth"
    stored = 0
    for part in _pdf_parts(msg.get("payload", {})):
        if part["body"].get("size", 0) > MAX_ATTACHMENT:
            emit(cfg, {"type": "skipped", "reason": "attachment_too_large", "bank": bank}, now)
            continue
        data = client.get_attachment(mid, part["body"]["attachmentId"])
        if len(data) > MAX_ATTACHMENT or not data.startswith(b"%PDF"):
            emit(cfg, {"type": "skipped", "reason": "not_a_pdf", "bank": bank}, now)
            continue
        emit(cfg, {"type": "new_statement", "bank": bank, "file_ref": _save_pdf(cfg, data),
                   "received_ms": int(msg.get("internalDate", 0))}, now)
        stored += 1
    if not stored:
        emit(cfg, {"type": "skipped", "reason": "no_pdf", "bank": bank}, now)
        return "no_pdf"
    return "stored"


def sweep_retention(cfg: Config, now=time.time) -> int:
    """Delete statement PDFs older than the retention window (the drop folder is rw only here)."""
    cutoff, gone = now() - cfg.retention_days * 86400, 0
    for name in os.listdir(cfg.drop_dir):
        path = os.path.join(cfg.drop_dir, name)
        if name.endswith(".pdf") and os.path.isfile(path) and os.path.getmtime(path) < cutoff:
            os.remove(path)
            gone += 1
    return gone


def run(client, cfg: Config, now=time.time) -> dict:
    summary = {"processed": 0, "errors": 0, "swept": 0}
    try:
        label_id = client.label_id(cfg.label)
        if label_id is None:
            emit(cfg, {"type": "error", "reason": "label_not_found"}, now)
            summary["errors"] += 1
            return summary
        state = _state(cfg)
        done = {r[0] for r in state.execute("SELECT message_id FROM processed")}
        ids = list(client.list_message_ids(label_id))
        if cfg.search_senders:
            # statements are not always labelled; the sender allowlist plus the DKIM/DMARC check is the real gate
            q = f"from:({' OR '.join(cfg.search_senders)}) has:attachment filename:pdf newer_than:{cfg.search_days}d"
            try:
                ids += [m for m in client.search_message_ids(q) if m not in ids]
            except GmailError:
                emit(cfg, {"type": "error", "reason": "gmail_error"}, now)
                summary["errors"] += 1
        for mid in ids:
            if mid in done:
                continue
            try:
                status = process_message(client, cfg, mid, now)
            except TokenError:
                raise
            except GmailError:
                emit(cfg, {"type": "error", "reason": "gmail_error"}, now)
                summary["errors"] += 1
                continue  # not marked processed: retried next run
            state.execute("INSERT OR REPLACE INTO processed VALUES (?,?,?)", (mid, status, int(now())))
            state.commit()
            summary["processed"] += 1
    except TokenError:
        emit(cfg, {"type": "error", "reason": "token_expired"}, now)
        summary["errors"] += 1
    summary["swept"] = sweep_retention(cfg, now)
    return summary
