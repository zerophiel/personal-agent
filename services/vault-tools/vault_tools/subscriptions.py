"""Digital subscriptions (Google One, Apple, Anthropic, ...): recurring charges that sit inside card/bank spending.

Statements keep only totals, so the owner (or the agent reading a statement, then confirmed by the owner) records
each one. Active ones are a known part of monthly spending; ended ones are remembered so they are not "found" again."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone

from . import changelog
from .money import check_idr, format_idr

STATUSES = ("active", "ended", "unsure")
NOTE_MAX = 300


def upsert(conn: sqlite3.Connection, alias: str, name: str, amount: int, source: str, status: str = "active",
           note: str | None = None, ends: str | None = None, essential: bool | None = None) -> str:
    """`ends` = YYYY-MM of the last charge for a contract that stops by itself (e.g. a rental paid off in 24 months).
    `essential` = never proposed as a cut (the owner's rule, e.g. anything for the children).
    For `note`, `ends` and `essential`, None keeps what is stored: an update that only moves the card or the price must not
    wipe the owner's facts (2026-10-28 three notes were lost that way). An empty string clears a note or an end month."""
    check_idr(amount)
    if ends and not re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", ends):
        raise ValueError("berakhir: format YYYY-MM (bulan tagihan terakhir)")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", alias):
        raise ValueError("alias: huruf kecil/angka/strip, 2-41 karakter")
    if amount < 0 or (status == "active" and amount == 0):
        raise ValueError("amount per bulan harus > 0 untuk langganan aktif")
    if status not in STATUSES:
        raise ValueError("status: active, ended, atau unsure")
    if note and len(note) > NOTE_MAX:
        raise ValueError(f"catatan maksimal {NOTE_MAX} karakter (sekarang {len(note)}); ringkas tanpa membuang fakta dari pemilik")
    row = conn.execute("SELECT * FROM subscriptions WHERE alias=?", (alias,)).fetchone()
    if essential is None:
        essential = bool(row and row["essential"])
    if note is None:
        note = row["note"] if row else None
    if ends is None:
        ends = row["ends"] if row else None
    conn.execute(
        "INSERT INTO subscriptions(alias,name,amount,source,status,note,updated_at,ends,essential) VALUES (?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(alias) DO UPDATE SET name=excluded.name, amount=excluded.amount, source=excluded.source,"
        " status=excluded.status, note=excluded.note, updated_at=excluded.updated_at, ends=excluded.ends, essential=excluded.essential",
        (alias, name[:60], amount, source[:40], status, note or None, datetime.now(timezone.utc).isoformat(), ends or None,
         1 if essential else 0))
    after = conn.execute("SELECT * FROM subscriptions WHERE alias=?", (alias,)).fetchone()
    if row is None or any(row[k] != after[k] for k in after.keys() if k != "updated_at"):    # every change stays traceable
        changelog.log(conn, "subscriptions", alias, "ubah" if row else "baru", dict(row) if row else None, dict(after))
    conn.commit()
    return (f"{alias}: {status}, {format_idr(amount)}/bulan via {source}" + (f", sampai {ends}" if ends else "")
            + (", WAJIB (tidak diusulkan untuk dipotong)." if essential else "."))


def active_total(conn: sqlite3.Connection, month: str | None = None) -> int:
    """Monthly total of the active subscriptions; with `month` (YYYY-MM) only those still charged in that month."""
    if month is None:
        return conn.execute("SELECT COALESCE(SUM(amount),0) FROM subscriptions WHERE status='active'").fetchone()[0]
    return conn.execute("SELECT COALESCE(SUM(amount),0) FROM subscriptions WHERE status='active' AND (ends IS NULL OR ends >= ?)",
                        (month,)).fetchone()[0]


def format_list(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT * FROM subscriptions ORDER BY status, alias").fetchall()
    if not rows:
        return "Belum ada langganan tercatat."
    label = {"active": "AKTIF", "ended": "berhenti", "unsure": "belum pasti"}
    lines = [f"- {r['name']} ({r['alias']}): {label[r['status']]}, {format_idr(r['amount'])}/bulan via {r['source']}"
             + (f", sampai {r['ends']}" if r["ends"] else "") + (", WAJIB: jangan diusulkan dipotong" if r["essential"] else "")
             + (f" - {r['note']}" if r["note"] else "") for r in rows]
    lines.append(f"Total langganan aktif: {format_idr(active_total(conn))}/bulan. Sudah termasuk di belanja kartu/rekening: "
                 "bagian dari biaya hidup, bukan tambahan. Langganan dolar berubah mengikuti kurs.")
    return "\n".join(lines)
