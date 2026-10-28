"""Credit-card installments ("cicilan kartu", printed on the statement as 03/12 = payment 3 of 12).

Each statement that still lists an installment refreshes it; one that stops appearing is treated as finished.
A committed future charge: it is not day-to-day living cost and it will be in every following statement."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from .money import check_idr, format_idr

MAX_TENOR = 60
STALE_DAYS = 5      # an item not refreshed by the card's latest statement (minus this slack) is no longer billed


def record(conn: sqlite3.Connection, card_alias: str, as_of: str, items: list[dict]) -> str:
    """items: {description, amount, seq, total}. seq/total are the x/y printed on the statement `as_of`."""
    d = date.fromisoformat(as_of)
    card = conn.execute("SELECT id FROM cards WHERE alias=?", (card_alias,)).fetchone()
    if card is None:
        raise ValueError(f"kartu {card_alias} belum terdaftar (upsert_card dulu)")
    for it in items:
        check_idr(it["amount"])
        if it["amount"] <= 0:
            raise ValueError("amount cicilan harus > 0")
        if not (2 <= it["total"] <= MAX_TENOR and 1 <= it["seq"] <= it["total"]):
            raise ValueError(f"cicilan {it['seq']}/{it['total']} tidak masuk akal (tenor 2-{MAX_TENOR}, ke-x <= y)")
    stored = 0
    conn.execute("INSERT OR IGNORE INTO card_installment_scans(card_id, statement_date) VALUES (?,?)", (card["id"], as_of))
    seen: dict[str, int] = {}
    for it in items:
        # identity = amount + tenor, never the description: the model words it differently on every statement
        base = f"{it['amount']}/{it['total']}"
        seen[base] = seen.get(base, 0) + 1
        key = base if seen[base] == 1 else f"{base}#{seen[base]}"
        old = conn.execute("SELECT as_of FROM card_installments WHERE card_id=? AND key=?", (card["id"], key)).fetchone()
        if old and old["as_of"] > as_of:
            continue                                  # an older statement never overwrites a newer one
        conn.execute(
            "INSERT INTO card_installments(card_id,key,description,per_month,seq,total,as_of) VALUES (?,?,?,?,?,?,?)"
            " ON CONFLICT(card_id,key) DO UPDATE SET per_month=excluded.per_month, seq=excluded.seq,"
            " as_of=excluded.as_of, description=excluded.description",
            (card["id"], key, it["description"][:80], it["amount"], it["seq"], it["total"], as_of))
        stored += 1
    conn.commit()
    act = active(conn)
    mine = [a for a in act if a["card"] == card_alias]
    return (f"{card_alias}: {stored} cicilan tercatat. Aktif sekarang {len(mine)} cicilan, "
            f"{format_idr(sum(a['per_month'] for a in mine))}/bulan.")


def _add_months(d: date, n: int) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    return date(y, m + 1, min(d.day, 28))


def active(conn: sqlite3.Connection) -> list[dict]:
    """Installments still being billed: not finished and still printed on the card's latest statement THAT WAS READ
    for installments (a newer statement nobody has scanned yet proves nothing)."""
    out = []
    for r in conn.execute(
            "SELECT i.*, c.alias AS card,"
            " COALESCE((SELECT MAX(statement_date) FROM card_installment_scans x WHERE x.card_id=i.card_id), i.as_of) AS last_stmt"
            " FROM card_installments i JOIN cards c ON c.id=i.card_id ORDER BY c.alias, i.as_of, i.description"):
        left = r["total"] - r["seq"]
        if left <= 0:
            continue
        if r["last_stmt"] and date.fromisoformat(r["as_of"]) < date.fromisoformat(r["last_stmt"]) - timedelta(days=STALE_DAYS):
            continue
        out.append({"card": r["card"], "description": r["description"], "per_month": r["per_month"], "seq": r["seq"],
                    "total": r["total"], "left": left, "remaining": left * r["per_month"],
                    "ends": _add_months(date.fromisoformat(r["as_of"]), left).isoformat()})
    return out


def monthly_total(conn: sqlite3.Connection) -> int:
    return sum(a["per_month"] for a in active(conn))


def format_list(conn: sqlite3.Connection) -> str:
    act = active(conn)
    if not act:
        return "Tidak ada cicilan kartu yang tercatat aktif."
    lines = [f"- {a['card']}: {a['description']} {a['seq']}/{a['total']}, {format_idr(a['per_month'])}/bulan, "
             f"sisa {a['left']} bulan ({format_idr(a['remaining'])}), selesai sekitar {a['ends'][:7]}" for a in act]
    lines.append(f"Total cicilan kartu: {format_idr(monthly_total(conn))}/bulan; sisa total {format_idr(sum(a['remaining'] for a in act))}. "
                 "Ini sudah termasuk di tagihan kartu tiap bulan: bukan biaya hidup dan bukan pengeluaran baru.")
    return "\n".join(lines)
