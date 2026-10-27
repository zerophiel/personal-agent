"""Digital subscriptions (Google One, Apple, Anthropic, ...): recurring charges that sit inside card/bank spending.

Statements keep only totals, so the owner (or the agent reading a statement, then confirmed by the owner) records
each one. Active ones are a known part of monthly spending; ended ones are remembered so they are not "found" again."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone

from .money import check_idr, format_idr

STATUSES = ("active", "ended", "unsure")


def upsert(conn: sqlite3.Connection, alias: str, name: str, amount: int, source: str, status: str = "active",
           note: str | None = None) -> str:
    check_idr(amount)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", alias):
        raise ValueError("alias: huruf kecil/angka/strip, 2-41 karakter")
    if amount < 0 or (status == "active" and amount == 0):
        raise ValueError("amount per bulan harus > 0 untuk langganan aktif")
    if status not in STATUSES:
        raise ValueError("status: active, ended, atau unsure")
    conn.execute(
        "INSERT INTO subscriptions(alias,name,amount,source,status,note,updated_at) VALUES (?,?,?,?,?,?,?)"
        " ON CONFLICT(alias) DO UPDATE SET name=excluded.name, amount=excluded.amount, source=excluded.source,"
        " status=excluded.status, note=excluded.note, updated_at=excluded.updated_at",
        (alias, name[:60], amount, source[:40], status, (note or "")[:120] or None, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return f"{alias}: {status}, {format_idr(amount)}/bulan via {source}."


def active_total(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COALESCE(SUM(amount),0) FROM subscriptions WHERE status='active'").fetchone()[0]


def format_list(conn: sqlite3.Connection) -> str:
    rows = conn.execute("SELECT * FROM subscriptions ORDER BY status, alias").fetchall()
    if not rows:
        return "Belum ada langganan tercatat."
    label = {"active": "AKTIF", "ended": "berhenti", "unsure": "belum pasti"}
    lines = [f"- {r['name']} ({r['alias']}): {label[r['status']]}, {format_idr(r['amount'])}/bulan via {r['source']}"
             + (f" - {r['note']}" if r["note"] else "") for r in rows]
    lines.append(f"Total langganan aktif: {format_idr(active_total(conn))}/bulan. Sudah termasuk di belanja kartu/rekening: "
                 "bagian dari biaya hidup, bukan tambahan. Langganan dolar berubah mengikuti kurs.")
    return "\n".join(lines)
