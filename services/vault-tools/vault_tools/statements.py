"""record_statement: validate the model's extraction and reconcile deterministically."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

from .money import check_idr
from .reconcile import reconcile


def record_statement(conn: sqlite3.Connection, card_alias: str, file_hash: str,
                     statement_date: str, due_date: str, previous_balance: int, payments: int,
                     charges: int, fees: int, total_due: int, minimum_due: int) -> dict:
    """Store one statement. Idempotent by file hash. A reconciliation mismatch is stored and
    flagged (reconciled=0), never corrected."""
    for v in (previous_balance, payments, charges, fees, total_due, minimum_due):
        check_idr(v)
        if v < 0:
            raise ValueError("amounts are positive magnitudes as printed on the statement")
    if minimum_due > total_due:
        raise ValueError("minimum_due cannot exceed total_due")
    sd, dd = date.fromisoformat(statement_date), date.fromisoformat(due_date)
    if dd < sd:
        raise ValueError("due_date before statement_date")
    if len(file_hash) != 64:
        raise ValueError("file_hash must be the sha256 hex from ingest_statement")
    card = conn.execute("SELECT id FROM cards WHERE alias=?", (card_alias,)).fetchone()
    if card is None:
        raise ValueError(f"kartu {card_alias} belum terdaftar (upsert_card dulu)")
    dup = conn.execute("SELECT id, reconciled FROM statements WHERE file_hash=?", (file_hash,)).fetchone()
    if dup:
        return {"status": "duplicate", "statement_id": dup["id"], "reconciled": bool(dup["reconciled"])}
    same = conn.execute("SELECT id, reconciled FROM statements WHERE card_id=? AND statement_date=?", (card["id"], statement_date)).fetchone()
    if same:     # the same bill delivered twice (email and Telegram, different PDF bytes): keep the first, with its payments
        return {"status": "duplicate", "statement_id": same["id"], "reconciled": bool(same["reconciled"])}
    r = reconcile(previous_balance, payments, charges, fees, total_due)
    cur = conn.execute(
        "INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,"
        "charges,fees,total_due,minimum_due,reconciled,recon_diff,ingested_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (card["id"], file_hash, statement_date, due_date, previous_balance, payments, charges, fees,
         total_due, minimum_due, int(r.ok), r.diff, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    out = {"status": "stored", "statement_id": cur.lastrowid, "reconciled": r.ok}
    if not r.ok:
        out["warning"] = (f"REKONSILIASI TIDAK COCOK: total tercetak {total_due}, "
                          f"hasil hitung {r.expected_total}, selisih {r.diff}. Mohon periksa ulang angka.")
    return out
