"""Expense capture, budgets and the financial health check. Deterministic: the model reads a
screenshot and passes the fields; every threshold, ratio and verdict is computed here.

Conventions
- Amounts are integer Rupiah; money out is negative in `transactions`.
- Categories that are NOT discretionary spending: 'transfer_internal', anything starting with
  'wajib:' (obligations such as school, lessons, loans, card bills) or 'sinking:' (pot deposits).
  Everything else (including uncategorized) counts as day-to-day spending.
- A receipt later seen in a bank mutation is merged (`merged_into`), so it is never counted twice.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone

from .money import check_idr, format_idr
from .mutations import INTERNAL, cashflow, clean_text, normalize

OBLIGATION_PREFIXES = ("wajib:", "sinking:", "sekali:", "berhenti:", "perantara:")   # berhenti: = a recurring cost that has ended
DEFAULT_MIN_SAVINGS_BP = 1000      # save at least 10% of income unless the owner sets another figure
DEFAULT_DSR_MAX_BP = 3000          # monthly debt payments <= 30% of net income
WATCH_PCT, OVER_PCT, PACE_SLACK = 80, 100, 15
MATCH_DAYS = 2


def is_discretionary(category: str | None) -> bool:
    c = category or ""
    return c != INTERNAL and not c.startswith(OBLIGATION_PREFIXES)


def _th(conn, key: str, default=None):
    row = conn.execute("SELECT value FROM thresholds WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


# ---- recording expenses (screenshots) ----------------------------------------------------

def record_expense(conn: sqlite3.Connection, today: date, amount: int, merchant: str, txn_date: str,
                   category: str | None = None, account_alias: str | None = None,
                   card_alias: str | None = None, allow_duplicate: bool = False) -> dict:
    """One purchase (from a screenshot or the owner's words). `amount` is the positive size of the spend.
    Stored unverified. A second record with the same date, amount and merchant is flagged, not added,
    unless allow_duplicate=True (two identical purchases in a day do happen)."""
    check_idr(amount)
    if amount <= 0:
        raise ValueError("amount harus > 0 (besar pengeluaran)")
    d = date.fromisoformat(txn_date)
    if d > today + timedelta(days=1):
        raise ValueError("tanggal transaksi di masa depan")
    merchant = clean_text(merchant, 120)
    if not merchant:
        raise ValueError("merchant kosong")
    key = normalize(merchant)
    ids = {}
    for label, alias, table in (("account_id", account_alias, "accounts"), ("card_id", card_alias, "cards")):
        if alias:
            row = conn.execute(f"SELECT id FROM {table} WHERE alias=?", (alias,)).fetchone()
            if row is None:
                raise ValueError(f"{table[:-1]} {alias} belum terdaftar")
            ids[label] = row["id"]
    # the same money from the same account or card is a duplicate whatever the merchant text says: a new chat session
    # describes a re-sent screenshot in other words ("Isi saldo Flazz" vs "Isi Flazz BCA"), and it remembers nothing
    same = [r for r in conn.execute(
        "SELECT id, merchant, account_id, card_id FROM transactions WHERE source='receipt' AND txn_date=? AND amount=? AND merged_into IS NULL",
        (txn_date, -amount)) if normalize(r["merchant"]) == key
        or (ids.get("account_id") is not None and r["account_id"] == ids.get("account_id"))
        or (ids.get("card_id") is not None and r["card_id"] == ids.get("card_id"))]
    if same and not allow_duplicate:
        return {"status": "possible_duplicate", "existing_id": same[0]["id"], "existing_merchant": same[0]["merchant"],
                "message": f"Sudah tercatat belanja dengan tanggal dan jumlah yang sama dari sumber yang sama ('{same[0]['merchant']}'). "
                           "Tanyakan ke pemilik; ulangi dengan allow_duplicate=true HANYA bila pemilik bilang memang dua pembelian."}
    rule = conn.execute("SELECT category FROM category_rules WHERE pattern=?", (key,)).fetchone()
    cat = clean_text(category, 40).lower() if category else (rule["category"] if rule else None)
    dedupe = hashlib.sha256(f"receipt|{txn_date}|{amount}|{key}|{len(same) + 1}".encode()).hexdigest()
    cur = conn.execute(
        "INSERT INTO transactions(account_id,card_id,txn_date,merchant,amount,category,status,source,dedupe_key)"
        " VALUES (?,?,?,?,?,?,?,'receipt',?)",
        (ids.get("account_id"), ids.get("card_id"), txn_date, merchant, -amount, cat,
         "verified" if rule and not category else "unverified", dedupe))
    conn.commit()
    return {"status": "stored", "id": cur.lastrowid, "category": cat,
            "alerts": alerts_for(conn, today, ("kartu:" + cat) if cat and card_alias else cat, d)}


def merge_receipt_into_mutation(conn, mutation_id: int, txn_date: str, amount: int) -> None:
    """Called when a mutation row is stored: an earlier receipt for the same money becomes part of it."""
    d = date.fromisoformat(txn_date)
    lo, hi = (d - timedelta(days=MATCH_DAYS)).isoformat(), (d + timedelta(days=MATCH_DAYS)).isoformat()
    r = conn.execute("SELECT id, category, status FROM transactions WHERE source='receipt' AND merged_into IS NULL"
                     " AND amount=? AND txn_date BETWEEN ? AND ? ORDER BY ABS(julianday(txn_date) - julianday(?)), id LIMIT 1",
                     (amount, lo, hi, txn_date)).fetchone()
    if r is None:
        return
    conn.execute("UPDATE transactions SET merged_into=? WHERE id=?", (mutation_id, r["id"]))
    if r["category"]:
        conn.execute("UPDATE transactions SET category=COALESCE(category, ?), status=? WHERE id=?",
                     (r["category"], r["status"], mutation_id))


def estimate_living_reserve(conn, before: date, salary: int | None = None) -> int:
    """Typical monthly day-to-day spending: the average of up to 3 earlier months, counting ONLY transactions the
    owner has categorized (verified) as non-obligation spending. Raw, unreviewed mutation rows would include
    school, loans and card bills and inflate the reserve, so they are left out. 0 when there is no such history.
    Rounded up to Rp 1.000 and capped at 60% of salary."""
    from statistics import median

    from .living import MIN_COVERAGE_PCT, monthly   # same coverage rule as living_cost_analysis
    months = [v["cash"] for _, v in monthly(conn, before).items()
              if v["total_out"] and v["coverage_pct"] >= MIN_COVERAGE_PCT][-3:]
    if len(months) < 2:                    # one tidy month is not a pattern; half-categorized months mislead
        return 0
    base = -(-int(median(months)) // 1000) * 1000
    return min(base, salary * 60 // 100) if salary else base


# ---- budgets and pace --------------------------------------------------------------------

def set_budget(conn, category: str, monthly_amount: int) -> str:
    check_idr(monthly_amount)
    cat = clean_text(category, 40).lower()
    if not cat or monthly_amount < 0:
        raise ValueError("category wajib dan jumlah >= 0")
    conn.execute("INSERT INTO thresholds(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                 (f"budget:{cat}", monthly_amount))
    conn.commit()
    return f"anggaran {cat} = {format_idr(monthly_amount)} per bulan"


def _spent_by_category(conn, start: date, end: date) -> dict[str, int]:
    """Spend per category. Rows paid by a card count under 'kartu:<category>' (a card budget), all others under the plain
    category (cash budget): a Tokopedia payment from a bank account must not eat the card budget."""
    out: dict[str, int] = {}
    for r in conn.execute("SELECT category, amount, card_id FROM transactions WHERE amount < 0 AND merged_into IS NULL"
                          " AND txn_date BETWEEN ? AND ?", (start.isoformat(), end.isoformat())):
        key = r["category"] or "belum dikategorikan"
        if r["card_id"] is not None:
            key = "kartu:" + key
        out[key] = out.get(key, 0) - r["amount"]
    return out


def budget_status(conn, month: str) -> list[dict]:
    y, m = int(month[:4]), int(month[5:7])
    start = date(y, m, 1)
    end = (date(y + (m == 12), m % 12 + 1, 1)) - timedelta(days=1)
    spent = _spent_by_category(conn, start, end)
    out = []
    for r in conn.execute("SELECT key, value FROM thresholds WHERE key LIKE 'budget:%' ORDER BY key"):
        cat, budget = r["key"][7:], r["value"]
        used = spent.get(cat, 0)
        pct = used * 100 // budget if budget else (100 if used else 0)
        out.append({"category": cat, "budget": budget, "spent": used, "pct": pct,
                    "status": "over" if used > budget else "watch" if pct >= WATCH_PCT else "ok"})
    return out


def spending_pace(conn, today: date) -> dict | None:
    """Day-to-day spending since the last payday against the cash the plan left for daily life."""
    row = conn.execute("SELECT snapshot_json FROM plans ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return None
    snap = json.loads(row["snapshot_json"])
    payday, nxt = date.fromisoformat(snap["payday"]), date.fromisoformat(snap["next_payday"])
    if not payday <= today < nxt:
        return None                                   # the plan is for another window
    allowance = snap["cash_to_hold"]
    spent = sum(v for c, v in _spent_by_category(conn, payday, today).items() if is_discretionary(c))
    window, elapsed = (nxt - payday).days, (today - payday).days + 1
    elapsed_pct = elapsed * 100 // window
    pct = spent * 100 // allowance if allowance > 0 else (OVER_PCT if spent else 0)
    status = ("over" if spent > allowance else
              "watch" if pct >= WATCH_PCT or pct > elapsed_pct + PACE_SLACK else "ok")
    return {"payday": payday.isoformat(), "next_payday": nxt.isoformat(), "allowance": allowance, "spent": spent,
            "remaining": allowance - spent, "pct_used": pct, "elapsed_pct": elapsed_pct, "status": status,
            "days_left": window - elapsed, "safe_per_day": (allowance - spent) // max(1, window - elapsed) if allowance > spent else 0}


def alerts_for(conn, today: date, category: str | None, txn_date: date | None = None) -> list[str]:
    """Warnings worth saying right after a purchase is recorded."""
    out = []
    pace = spending_pace(conn, today)
    if pace and pace["status"] == "over":
        out.append(f"PENGELUARAN HARIAN MELEBIHI JATAH: terpakai {format_idr(pace['spent'])} dari {format_idr(pace['allowance'])} "
                   f"sebelum gajian {pace['next_payday']}.")
    elif pace and pace["status"] == "watch":
        out.append(f"Waspada: {pace['pct_used']}% jatah harian terpakai padahal baru {pace['elapsed_pct']}% waktu berlalu. "
                   f"Sisa {format_idr(pace['remaining'])} untuk {pace['days_left']} hari (sekitar {format_idr(pace['safe_per_day'])}/hari).")
    if category:
        d = txn_date or today
        for b in budget_status(conn, f"{d.year}-{d.month:02d}"):
            if b["category"] == category and b["status"] != "ok":
                out.append(f"Anggaran {category}: {format_idr(b['spent'])} dari {format_idr(b['budget'])} ({b['pct']}%)"
                           + (" - SUDAH LEWAT." if b["status"] == "over" else "."))
    return out


# ---- debt load, balances, snapshots -----------------------------------------------------

def debt_load(conn) -> dict:
    installments = conn.execute("SELECT COALESCE(SUM(installment),0) FROM debts WHERE tenor_left > 0").fetchone()[0]
    cards = conn.execute(
        "SELECT COALESCE(SUM(MAX(0, s.minimum_due - s.paid_amount)),0), COALESCE(SUM(s.total_due - s.paid_amount),0)"
        " FROM statements s WHERE s.paid_at IS NULL"
        " AND s.id = (SELECT id FROM statements WHERE card_id = s.card_id ORDER BY statement_date DESC, id DESC LIMIT 1)").fetchone()
    outstanding = conn.execute("SELECT COALESCE(SUM(outstanding),0) FROM debts WHERE tenor_left > 0").fetchone()[0]
    salary = _th(conn, "net_salary")
    monthly = installments + cards[0]
    return {"monthly_payments": monthly, "total_debt": outstanding + cards[1],
            "dsr_bp": monthly * 10_000 // salary if salary else None,
            "dsr_max_bp": _th(conn, "dsr_max_bp", DEFAULT_DSR_MAX_BP)}


def account_balances(conn) -> dict[str, list[tuple[str, int]]]:
    """Closing balance per period for each own (non-pool) account, oldest first."""
    out: dict[str, list[tuple[str, int]]] = {}
    for r in conn.execute(
            "SELECT a.alias, m.period_end, m.closing_balance FROM mutation_files m JOIN accounts a ON a.id = m.account_id"
            " WHERE a.kind != 'pool' AND m.closing_balance IS NOT NULL ORDER BY m.period_end"):
        out.setdefault(r["alias"], []).append((r["period_end"], r["closing_balance"]))
    return out


def snapshot(conn, today: date) -> dict:
    """Record this month's debt and balance picture (one row per month, overwritten while the month runs)."""
    month = f"{today.year}-{today.month:02d}"
    dl = debt_load(conn)
    bal = account_balances(conn)
    total_bal = sum(v[-1][1] for v in bal.values()) if bal else None
    saved = sum(conn.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE amount>0 AND category=?",
                             (f"sinking:{f['alias']}",)).fetchone()[0] + f["saved_so_far"]
                for f in conn.execute("SELECT alias, saved_so_far FROM sinking_funds").fetchall())
    conn.execute("INSERT INTO net_snapshots VALUES (?,?,?,?,?) ON CONFLICT(month) DO UPDATE SET total_debt=excluded.total_debt,"
                 "accounts_balance=excluded.accounts_balance, saved_funds=excluded.saved_funds, created_at=excluded.created_at",
                 (month, dl["total_debt"], total_bal, saved, datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return {"month": month, "total_debt": dl["total_debt"], "accounts_balance": total_bal, "saved_funds": saved}


# ---- the health check --------------------------------------------------------------------

def health_check(conn, today: date, month: str | None = None) -> dict:
    """Findings as a list of (severity, text); severity is 'info', 'warn' or 'bad'. Verdict by fixed rules."""
    month = month or f"{today.year}-{today.month:02d}"
    findings: list[tuple[str, str]] = []
    cf = cashflow(conn, month)
    y, m = int(month[:4]), int(month[5:7])
    from .tools import id_holidays
    from .payday import last_working_day
    month_payday = last_working_day(y, m, id_holidays(y))
    if cf["rows"] == 0:
        findings.append(("info", f"Belum ada mutasi untuk {month}; rasio tabung belum bisa dihitung."))
    elif ((cf["income"] == 0 or (_th(conn, "net_salary") and cf["income"] < _th(conn, "net_salary") // 2))
          and today <= month_payday and f"{today.year}-{today.month:02d}" == month):
        # the salary has not arrived yet: a half-finished month would look like a huge deficit
        findings.append(("info", f"{month} belum lengkap: gaji baru masuk sekitar {month_payday.isoformat()}. "
                                 f"Pengeluaran sejauh ini {format_idr(cf['expenses'])}; rasio tabung dinilai setelah gaji masuk "
                                 f"(lihat bulan lalu untuk gambaran penuh)."))
    else:
        rate = cf["savings_rate_bp"]
        floor = _th(conn, "min_savings_rate_bp", DEFAULT_MIN_SAVINGS_BP)
        if cf["net"] < 0:
            findings.append(("bad", f"{month}: pengeluaran {format_idr(cf['expenses'])} LEBIH BESAR dari pemasukan "
                                    f"{format_idr(cf['income'])} (defisit {format_idr(-cf['net'])}). Saldo menggerus."))
        elif rate is not None and rate < floor:
            findings.append(("warn", f"{month}: rasio tabung {rate / 100:.1f}% di bawah target {floor / 100:.1f}%."))
        target = _th(conn, "monthly_savings_target")
        if target and cf["net"] < target:
            findings.append(("warn", f"{month}: selisih bulan ini {format_idr(cf['net'])} belum mencapai target tabungan {format_idr(target)}."))
        if cf["unverified"]:
            findings.append(("info", f"{cf['unverified']} transaksi {month} belum diverifikasi kategorinya; angka bisa bergeser."))
        if cf["unreconciled_files"]:
            findings.append(("warn", f"{cf['unreconciled_files']} file mutasi belum cocok saat rekonsiliasi; angka mungkin tidak lengkap."))
    dl = debt_load(conn)
    if dl["dsr_bp"] is None:
        findings.append(("info", "net_salary belum diset; beban utang (DSR) belum bisa dihitung."))
    elif dl["dsr_bp"] > dl["dsr_max_bp"]:
        findings.append(("bad", f"Beban utang {dl['dsr_bp'] / 100:.1f}% dari gaji melewati batas {dl['dsr_max_bp'] / 100:.1f}% "
                                f"(cicilan + minimum kartu {format_idr(dl['monthly_payments'])}/bulan)."))
    prev = conn.execute("SELECT * FROM net_snapshots WHERE month < ? ORDER BY month DESC LIMIT 1", (month,)).fetchone()
    now = snapshot(conn, today)
    if prev and now["total_debt"] > prev["total_debt"]:
        findings.append(("bad", f"Total utang naik dari {format_idr(prev['total_debt'])} ({prev['month']}) menjadi "
                                f"{format_idr(now['total_debt'])}. Utang bertambah, bukan berkurang."))
    for alias, series in account_balances(conn).items():
        last3 = [v for _, v in series[-3:]]
        if len(last3) >= 2 and all(b < a for a, b in zip(last3, last3[1:])):
            findings.append(("warn", f"Saldo {alias} turun {len(last3) - 1} periode berturut-turut "
                                     f"({' -> '.join(format_idr(v) for v in last3)})."))
        buf = _th(conn, "cash_buffer", 0)
        if buf and series[-1][1] < buf:
            findings.append(("bad", f"Saldo {alias} {format_idr(series[-1][1])} di bawah buffer {format_idr(buf)}."))
    pace = spending_pace(conn, today)
    if pace and pace["status"] != "ok":
        findings.append(("bad" if pace["status"] == "over" else "warn",
                         f"Pengeluaran harian: {format_idr(pace['spent'])} dari jatah {format_idr(pace['allowance'])} "
                         f"({pace['pct_used']}%, waktu berlalu {pace['elapsed_pct']}%)."))
    for b in budget_status(conn, month):
        if b["status"] != "ok":
            findings.append(("bad" if b["status"] == "over" else "warn",
                             f"Anggaran {b['category']}: {format_idr(b['spent'])} dari {format_idr(b['budget'])} ({b['pct']}%)."))
    verdict = "BURUK" if any(s == "bad" for s, _ in findings) else "WASPADA" if any(s == "warn" for s, _ in findings) else "SEHAT"
    return {"month": month, "verdict": verdict, "findings": findings, "snapshot": now,
            "savings": {"income": cf["income"], "expenses": cf["expenses"], "net": cf["net"], "rate_bp": cf["savings_rate_bp"]},
            "debt": dl, "pace": pace}


def format_health(h: dict) -> str:
    lines = [f"Penilaian keuangan {h['month']}: {h['verdict']}"]
    s = h["savings"]
    if s["income"] or s["expenses"]:
        rate = "-" if s["rate_bp"] is None else f"{s['rate_bp'] / 100:.1f}%"
        lines.append(f"Pemasukan {format_idr(s['income'])}; pengeluaran {format_idr(s['expenses'])}; "
                     f"selisih {format_idr(s['net'])}; rasio tabung {rate}")
    d = h["debt"]
    lines.append(f"Total utang {format_idr(d['total_debt'])}; cicilan + minimum kartu {format_idr(d['monthly_payments'])}/bulan"
                 + (f" ({d['dsr_bp'] / 100:.1f}% gaji)" if d["dsr_bp"] is not None else ""))
    tag = {"bad": "!!", "warn": "!", "info": "-"}
    lines += [f"{tag[sev]} {text}" for sev, text in h["findings"]]
    if not h["findings"]:
        lines.append("Tidak ada peringatan.")
    return "\n".join(lines)
