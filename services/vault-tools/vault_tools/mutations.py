"""Bank account mutations (rekening koran): record, reconcile, categorize, analyse.

Conventions: amounts are signed integer Rupiah, outflow negative. The model extracts rows from
untrusted statement text; everything here is deterministic. Rows are deduplicated across
overlapping files, and a balance mismatch is flagged, never corrected. Category 'transfer_internal'
(moves between the owner's own accounts) is excluded from income and expense.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
import statistics
from collections import defaultdict
from datetime import date, datetime, timezone

from .money import check_idr, format_idr

MAX_ROWS = 2000
INTERNAL = "transfer_internal"
ONE_OFF = "sekali:"     # windfalls and one-time moves (JHT, bonus, THR, a lump-sum card payoff): not part of the monthly picture


def excluded(category: str | None) -> bool:
    """Not counted in monthly income/expense: own-account moves and one-off items."""
    c = category or ""
    return c == INTERNAL or c.startswith(ONE_OFF)
_REF = re.compile(r"\d{6,}")
_CTRL = re.compile(r"[\x00-\x1f\x7f]")


def clean_text(s: str, limit: int = 120) -> str:
    return _CTRL.sub(" ", s).strip()[:limit]


def normalize(desc: str) -> str:
    """Stable merchant key: lowercase, long digit runs (refs/accounts) -> '#', spaces collapsed."""
    return " ".join(_REF.sub("#", desc.lower()).split())[:100]


def record_mutations(conn: sqlite3.Connection, account_alias: str, file_hash: str, period_start: str,
                     period_end: str, opening_balance: int | None, closing_balance: int | None,
                     rows: list[dict]) -> dict:
    """rows: [{date, description, amount (signed), balance?}]. Idempotent: re-sending a file or an
    overlapping period adds only rows not seen before."""
    if len(file_hash) != 64:
        raise ValueError("file_hash must be the sha256 from ingest_statement")
    if not 0 < len(rows) <= MAX_ROWS:
        raise ValueError(f"rows must be 1..{MAX_ROWS}")
    ps, pe = date.fromisoformat(period_start), date.fromisoformat(period_end)
    if pe < ps:
        raise ValueError("period_end before period_start")
    for v in (opening_balance, closing_balance):
        if v is not None:
            check_idr(v)
    acct = conn.execute("SELECT id FROM accounts WHERE alias=?", (account_alias,)).fetchone()
    if acct is None:
        raise ValueError(f"rekening {account_alias} belum terdaftar (upsert_account dulu)")
    seen_file = conn.execute("SELECT new_rows, reconciled FROM mutation_files WHERE file_hash=?",
                             (file_hash,)).fetchone()
    if seen_file:
        return {"status": "duplicate", "new_rows": 0, "reconciled": bool(seen_file["reconciled"])}

    parsed, total = [], 0
    for r in rows:
        d = date.fromisoformat(r["date"])
        check_idr(r["amount"])
        if r["amount"] == 0:
            continue
        total += r["amount"]
        parsed.append((d.isoformat(), clean_text(r["description"]), r["amount"]))
    if not parsed:
        raise ValueError("no non-zero rows")

    reconciled, diff = True, 0
    if opening_balance is not None and closing_balance is not None:
        diff = closing_balance - (opening_balance + total)
        reconciled = diff == 0

    counts: dict[tuple, int] = defaultdict(int)
    new = 0
    rules = {p: c for p, c in conn.execute("SELECT pattern, category FROM category_rules")}
    for d, desc, amount in parsed:
        key_base = (d, amount, normalize(desc))
        counts[key_base] += 1       # n-th identical row of the day within this file
        raw = f"{acct['id']}|{d}|{amount}|{key_base[2]}|{counts[key_base]}"
        key = hashlib.sha256(raw.encode()).hexdigest()
        category = rules.get(key_base[2])
        cur = conn.execute(
            "INSERT OR IGNORE INTO transactions(account_id,txn_date,merchant,amount,category,status,source,"
            "dedupe_key,file_hash) VALUES (?,?,?,?,?,?,?,?,?)",
            (acct["id"], d, desc, amount, category, "verified" if category else "unverified",
             "mutation", key, file_hash))
        new += cur.rowcount
        if cur.rowcount and amount < 0:           # a purchase already captured from a screenshot is merged, not double counted
            from .health import merge_receipt_into_mutation
            merge_receipt_into_mutation(conn, cur.lastrowid, d, amount)
    conn.execute(
        "INSERT INTO mutation_files VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (file_hash, acct["id"], period_start, period_end, opening_balance, closing_balance,
         len(parsed), new, int(reconciled), diff, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    out = {"status": "stored", "rows": len(parsed), "new_rows": new, "already_known": len(parsed) - new,
           "reconciled": reconciled}
    if not reconciled:
        out["warning"] = (f"REKONSILIASI TIDAK COCOK: saldo akhir tercetak {closing_balance}, hasil hitung "
                          f"{opening_balance + total}, selisih {diff}. Ada baris yang mungkin hilang atau salah baca.")
    return out


# ---- categorization ----------------------------------------------------------------------

def set_category(conn, txn_id: int, category: str) -> str:
    cat = clean_text(category, 40).lower()
    if not cat:
        raise ValueError("category kosong")
    n = conn.execute("UPDATE transactions SET category=?, status='verified' WHERE id=?", (cat, txn_id)).rowcount
    if n == 0:
        raise ValueError("transaksi tidak ditemukan")
    conn.commit()
    return f"transaksi {txn_id} -> {cat}"


def set_category_rule(conn, merchant: str, category: str) -> str:
    """Remember a category for a merchant and apply it to matching rows not yet verified."""
    pattern, cat = normalize(merchant), clean_text(category, 40).lower()
    if not pattern or not cat:
        raise ValueError("merchant dan category wajib")
    conn.execute("INSERT INTO category_rules VALUES (?,?) ON CONFLICT(pattern) DO UPDATE SET category=excluded.category",
                 (pattern, cat))
    hit = 0
    for r in conn.execute("SELECT id, merchant FROM transactions WHERE source IN ('mutation','receipt')"
                          " AND status='unverified' AND merged_into IS NULL").fetchall():
        if normalize(r["merchant"]) == pattern:
            conn.execute("UPDATE transactions SET category=?, status='verified' WHERE id=?", (cat, r["id"]))
            hit += 1
    conn.commit()
    return f"aturan '{pattern}' -> {cat}; {hit} transaksi diperbarui"


def list_uncategorized(conn, limit: int = 30) -> list[str]:
    """Most frequent unverified merchants first, so one rule fixes many rows."""
    groups: dict[str, list] = defaultdict(list)
    for r in conn.execute("SELECT id, merchant, amount, category FROM transactions "
                          "WHERE source IN ('mutation','receipt') AND status='unverified' AND merged_into IS NULL"):
        groups[normalize(r["merchant"])].append(r)
    out = []
    for pat, rs in sorted(groups.items(), key=lambda kv: -len(kv[1]))[:limit]:
        guess = next((r["category"] for r in rs if r["category"]), None)
        out.append(f"{pat} | {len(rs)}x | contoh id={rs[0]['id']} {format_idr(rs[0]['amount'])}"
                   + (f" | usulan: {guess}" if guess else ""))
    return out


# ---- analysis ----------------------------------------------------------------------------

def _month_rows(conn, month: str):
    return conn.execute(
        "SELECT merchant, amount, category, status FROM transactions "
        "WHERE source='mutation' AND substr(txn_date,1,7)=?", (month,)).fetchall()


def cashflow(conn, month: str) -> dict:
    """Income, expenses, net and savings rate for YYYY-MM (own-account transfers excluded)."""
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("month harus YYYY-MM")
    rows = _month_rows(conn, month)
    income = sum(r["amount"] for r in rows if r["amount"] > 0 and not excluded(r["category"]))
    spend = -sum(r["amount"] for r in rows if r["amount"] < 0 and not excluded(r["category"]))
    one_off_in = sum(r["amount"] for r in rows if r["amount"] > 0 and (r["category"] or "").startswith(ONE_OFF))
    one_off_out = -sum(r["amount"] for r in rows if r["amount"] < 0 and (r["category"] or "").startswith(ONE_OFF))
    by_cat: dict[str, int] = defaultdict(int)
    merchants: dict[str, int] = defaultdict(int)
    for r in rows:
        if r["amount"] < 0 and not excluded(r["category"]):
            by_cat[r["category"] or "belum dikategorikan"] += -r["amount"]
            merchants[normalize(r["merchant"])] += -r["amount"]
    bad = conn.execute("SELECT COUNT(*) FROM mutation_files WHERE reconciled=0").fetchone()[0]
    return {
        "month": month, "rows": len(rows), "income": income, "expenses": spend, "net": income - spend,
        "one_off_in": one_off_in, "one_off_out": one_off_out,
        "savings_rate_bp": (income - spend) * 10_000 // income if income > 0 else None,
        "by_category": sorted(by_cat.items(), key=lambda kv: -kv[1]),
        "top_merchants": sorted(merchants.items(), key=lambda kv: -kv[1])[:5],
        "unverified": sum(1 for r in rows if r["status"] == "unverified"),
        "unreconciled_files": bad,
    }


def format_cashflow(c: dict) -> str:
    if c["rows"] == 0:
        return f"Belum ada mutasi untuk {c['month']}."
    rate = "-" if c["savings_rate_bp"] is None else f"{c['savings_rate_bp'] / 100:.1f}%"
    lines = [f"Arus kas {c['month']} ({c['rows']} transaksi)",
             f"Pemasukan {format_idr(c['income'])}; pengeluaran {format_idr(c['expenses'])}; "
             f"selisih {format_idr(c['net'])}; rasio tabung {rate}"]
    lines += [f"- {k}: {format_idr(v)}" for k, v in c["by_category"][:8]]
    lines.append("Terbesar: " + "; ".join(f"{k} {format_idr(v)}" for k, v in c["top_merchants"]))
    if c.get("one_off_in") or c.get("one_off_out"):
        lines.append(f"Sekali (tidak dihitung dalam rasio): masuk {format_idr(c['one_off_in'])}; keluar {format_idr(c['one_off_out'])}")
    if c["unverified"]:
        lines.append(f"Catatan: {c['unverified']} transaksi belum diverifikasi kategorinya.")
    if c["unreconciled_files"]:
        lines.append(f"PERINGATAN: {c['unreconciled_files']} file mutasi belum cocok saat rekonsiliasi.")
    return "\n".join(lines)


def recurring(conn, min_months: int = 3, tolerance_pct: int = 15) -> list[str]:
    """Outflows with the same merchant key, similar amount, in at least `min_months` months."""
    by: dict[str, list] = defaultdict(list)
    for r in conn.execute("SELECT merchant, amount, substr(txn_date,1,7) m, category FROM transactions "
                          "WHERE source='mutation' AND amount < 0"):
        if not excluded(r["category"]):
            by[normalize(r["merchant"])].append((r["m"], -r["amount"]))
    out = []
    for key, items in by.items():
        med = statistics.median(a for _, a in items)
        close = [(m, a) for m, a in items if abs(a - med) * 100 <= tolerance_pct * med]
        months = {m for m, _ in close}
        if len(months) >= min_months:
            out.append((len(months), f"{key} | {len(months)} bulan | sekitar {format_idr(int(med))}/bulan"))
    return [s for _, s in sorted(out, reverse=True)]


def suggest_salary(conn, lookback_months: int = 4) -> str:
    """Largest monthly credit that repeats with a similar amount: a candidate salary for the owner to confirm."""
    by_month: dict[str, tuple[int, str]] = {}
    for r in conn.execute("SELECT merchant, amount, substr(txn_date,1,7) m FROM transactions "
                          "WHERE source='mutation' AND amount >= 1000000 AND IFNULL(category,'') != ?"
                          " AND IFNULL(category,'') NOT LIKE 'sekali:%'", (INTERNAL,)):
        if r["m"] not in by_month or r["amount"] > by_month[r["m"]][0]:
            by_month[r["m"]] = (r["amount"], normalize(r["merchant"]))
    recent = sorted(by_month.items())[-lookback_months:]
    if len(recent) < 2:
        return "Data belum cukup untuk menebak gaji (butuh minimal 2 bulan mutasi)."
    amounts = [a for _, (a, _) in recent]
    med = statistics.median(amounts)
    similar = [(m, a, d) for m, (a, d) in recent if abs(a - med) * 100 <= 15 * med]
    if len(similar) < 2:
        return "Tidak ada pemasukan bulanan yang jumlahnya mirip; tanyakan gaji ke pemilik."
    desc = statistics.mode([d for _, _, d in similar])
    return (f"Dugaan gaji: sekitar {format_idr(int(med))}/bulan dari '{desc}' pada "
            f"{', '.join(m for m, _, _ in similar)}. Minta pemilik konfirmasi sebelum set net_salary.")
