"""Ledger-facing operations behind the MCP tools. No secrets and no full numbers here:
payees are referred to by alias only."""
from __future__ import annotations

import calendar
import json
import os
import sqlite3
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone

import holidays as _holidays

from . import names
from .money import check_idr, format_idr
from .payday import Obligation, Plan, build_plan, last_working_day, next_payday


def _cuti_bersama() -> frozenset[date]:
    """Joint-leave days from data/cuti_bersama.json (not in python-holidays); owner chose to
    treat them as non-working days for payday. Years missing from the file add nothing."""
    def load(path):
        try:
            with open(path) as f:
                return {k: v for k, v in json.load(f).items() if not k.startswith("_")}
        except FileNotFoundError:
            return {}

    data = load(os.path.join(os.path.dirname(__file__), "data", "cuti_bersama.json"))
    # monthly host job (scripts/fetch-cuti.py) writes the override; it wins for years it covers
    data.update(load(os.environ.get("CUTI_OVERRIDE", "/data/cuti_bersama.json")))
    return frozenset(date.fromisoformat(d) for v in data.values() for d in v)


def id_holidays(year: int) -> frozenset[date]:
    """Indonesian national holidays (python-holidays) plus cuti bersama (local data file)."""
    h = _holidays.country_holidays("ID", years=[year - 1, year, year + 1])
    return frozenset(h.keys()) | _cuti_bersama()


def _day_in_month(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def due_dates_in_window(due_day: int, start: date, end: date) -> list[date]:
    """Dates in [start, end) that fall on `due_day` (clamped to month length)."""
    out, y, m = [], start.year, start.month
    for _ in range(3):
        d = _day_in_month(y, m, due_day)
        if start <= d < end:
            out.append(d)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


# ---- upserts (aliases + last4 only) -------------------------------------------------

# How each bank's card bill is paid: (method, allowed payee kinds). Owner's rules:
# Jenius/BCA -> transfer to an ACCOUNT number (never the card number); Mandiri -> pay from the
# bank app's menu, the card number is kept only to be shown in the reminder.
PAY_RULES = {
    "jenius":  ("transfer", ("account", "va")),
    "bca":     ("transfer", ("account", "va")),
    "mandiri": ("app_menu", ("card",)),
}
DEFAULT_RULE = ("transfer", ("card", "account", "va"))


def resolve_pay(conn, bank: str, pay_method: str | None, pay_to_alias: str | None) -> tuple[str, str | None]:
    """Validate how a card is paid. Returns (method, pay_to_alias)."""
    rule_method, kinds = PAY_RULES.get(bank.lower(), DEFAULT_RULE)
    method = pay_method or rule_method
    if bank.lower() in PAY_RULES and method != rule_method:
        raise ValueError(f"{bank}: metode bayar harus {rule_method}")
    if pay_to_alias is None:
        return method, None
    row = conn.execute("SELECT kind FROM payee_secrets WHERE alias=?", (pay_to_alias,)).fetchone()
    if row is None:
        raise ValueError(f"penerima {pay_to_alias} belum tersimpan (kirim nomornya dulu: kartu langsung, "
                         "rekening dengan /rekening, VA dengan /va)")
    if row["kind"] not in kinds:
        want = "nomor REKENING (/rekening)" if "card" not in kinds else "nomor kartu"
        raise ValueError(f"{bank}: tujuan bayar harus {want}, bukan {row['kind']}")
    return method, pay_to_alias


def upsert_card(conn: sqlite3.Connection, alias: str, bank: str, last4: str,
                statement_day: int, due_day: int, credit_limit: int,
                pay_method: str | None = None, pay_to_alias: str | None = None) -> str:
    check_idr(credit_limit)
    method, pay_to = resolve_pay(conn, bank, pay_method, pay_to_alias)
    conn.execute(
        "INSERT INTO cards(alias,bank,last4,statement_day,due_day,credit_limit,pay_method,pay_to_alias)"
        " VALUES (?,?,?,?,?,?,?,?)"
        " ON CONFLICT(alias) DO UPDATE SET bank=excluded.bank,last4=excluded.last4,"
        "statement_day=excluded.statement_day,due_day=excluded.due_day,credit_limit=excluded.credit_limit,"
        "pay_method=excluded.pay_method,pay_to_alias=COALESCE(excluded.pay_to_alias,cards.pay_to_alias)",
        (alias, bank, last4, statement_day, due_day, credit_limit, method, pay_to))
    conn.commit()
    how = "lewat menu aplikasi" if method == "app_menu" else "transfer"
    note = "" if pay_to or conn.execute("SELECT pay_to_alias FROM cards WHERE alias=?", (alias,)).fetchone()[0] \
        else f"; tujuan bayar belum diset ({how})"
    return f"kartu {alias} ****{last4} tersimpan, bayar {how}{note}"


def upsert_debt(conn, alias: str, lender: str, outstanding: int, installment: int,
                tenor_left: int, due_day: int, rate_bp: int | None = None) -> str:
    check_idr(outstanding), check_idr(installment)
    conn.execute(
        "INSERT INTO debts(alias,lender,outstanding,installment,tenor_left,rate_bp,due_day)"
        " VALUES (?,?,?,?,?,?,?) ON CONFLICT(alias) DO UPDATE SET lender=excluded.lender,"
        "outstanding=excluded.outstanding,installment=excluded.installment,"
        "tenor_left=excluded.tenor_left,rate_bp=excluded.rate_bp,due_day=excluded.due_day",
        (alias, lender, outstanding, installment, tenor_left, rate_bp, due_day))
    conn.commit()
    return f"utang {alias} tersimpan"


def upsert_expense(conn, alias: str, payee_alias: str, amount: int, due_day: int) -> str:
    check_idr(amount)
    conn.execute(
        "INSERT INTO fixed_expenses(alias,payee_alias,amount,due_day) VALUES (?,?,?,?)"
        " ON CONFLICT(alias) DO UPDATE SET payee_alias=excluded.payee_alias,"
        "amount=excluded.amount,due_day=excluded.due_day", (alias, payee_alias, amount, due_day))
    conn.commit()
    return f"pengeluaran tetap {alias} tersimpan"


def set_threshold(conn, key: str, value: int) -> str:
    check_idr(value)
    conn.execute("INSERT INTO thresholds(key,value) VALUES (?,?)"
                 " ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
    conn.commit()
    return f"{key} = {value}"


def get_threshold(conn, key: str, default: int | None = None) -> int | None:
    row = conn.execute("SELECT value FROM thresholds WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def list_uploads(upload_dir: str, limit: int = 10) -> list[str]:
    """Newest files the owner uploaded in Telegram (Hermes document cache), as `telegram/<name>`
    refs for ingest_statement. Names are reduced to a safe charset (they are untrusted)."""
    try:
        entries = [e for e in os.scandir(upload_dir) if e.is_file(follow_symlinks=False)]
    except FileNotFoundError:
        return []
    entries.sort(key=lambda e: e.stat().st_mtime, reverse=True)
    return [names.UPLOAD_PREFIX + names.safe_name(e.name) for e in entries[:limit]]


_EVENT_KEYS = ("type", "reason", "bank", "file_ref", "from")


def read_new_events(conn, path: str, limit: int = 20) -> list[str]:
    """New ingest-gmail events since the last call (cursor kept in `thresholds`). Only a fixed
    set of short fields is passed on, so nothing free-form from an email can reach the model."""
    cursor = get_threshold(conn, "ingest_events_cursor", 0)
    try:
        with open(path) as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return []
    out = []
    for line in lines[cursor:cursor + limit]:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        out.append("; ".join(f"{k}={str(ev[k])[:80]}" for k in _EVENT_KEYS if k in ev))
    set_threshold(conn, "ingest_events_cursor", cursor + min(limit, len(lines) - cursor))
    return out


# ---- obligations and plan -----------------------------------------------------------

# ---- sinking funds: a lump sum owed on a date, saved up in the owner's pool account ----------

SINKING_BUFFER_DAYS = 3        # the last contribution must land this many days before the due date
ROUND_UP_TO = 1_000            # contributions are rounded up to a neat Rp 1.000


def _round_up(value: int, step: int = ROUND_UP_TO) -> int:
    return -(-value // step) * step


def upsert_sinking_fund(conn, alias: str, target: int, due_date: str, pool_alias: str,
                        pool_pay_to_alias: str, creditor_pay_to_alias: str | None = None,
                        saved_so_far: int = 0, today: date | None = None, note: str | None = None) -> str:
    check_idr(target), check_idr(saved_so_far)
    if target <= 0 or saved_so_far < 0:
        raise ValueError("target harus > 0 dan saved_so_far >= 0")
    due = date.fromisoformat(due_date)
    today = today or date.today()
    if due <= today:
        raise ValueError("due_date harus di masa depan")
    acct = conn.execute("SELECT kind FROM accounts WHERE alias=?", (pool_alias,)).fetchone()
    if acct is None or acct["kind"] != "pool":
        raise ValueError(f"{pool_alias} belum terdaftar sebagai rekening pot (upsert_account kind=pool)")
    for label, a in (("rekening pot", pool_pay_to_alias), ("penerima", creditor_pay_to_alias)):
        if a is None:
            continue
        row = conn.execute("SELECT kind FROM payee_secrets WHERE alias=?", (a,)).fetchone()
        if row is None or row["kind"] not in ("account", "va"):
            raise ValueError(f"{label}: {a} belum tersimpan sebagai nomor rekening/VA (kirim dengan /rekening atau /va)")
    asof = conn.execute("SELECT saved_asof FROM sinking_funds WHERE alias=?", (alias,)).fetchone()
    conn.execute(
        "INSERT INTO sinking_funds(alias,target,due_date,pool_alias,pool_pay_to,creditor_pay_to,saved_so_far,saved_asof,note)"
        " VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(alias) DO UPDATE SET target=excluded.target,"
        "due_date=excluded.due_date,pool_alias=excluded.pool_alias,pool_pay_to=excluded.pool_pay_to,"
        "creditor_pay_to=COALESCE(excluded.creditor_pay_to,sinking_funds.creditor_pay_to),"
        "saved_so_far=excluded.saved_so_far,saved_asof=excluded.saved_asof,note=excluded.note",
        (alias, target, due_date, pool_alias, pool_pay_to_alias, creditor_pay_to_alias, saved_so_far,
         today.isoformat(), note))
    conn.commit()
    _ = asof
    return (f"dana terikat {alias}: {format_idr(target)} jatuh tempo {due_date}, terkumpul awal "
            f"{format_idr(saved_so_far)} per {today.isoformat()}")


def sinking_saved(conn, fund) -> int:
    """Saved so far = stated amount + deposits seen on the pool account since then
    (credits categorized 'sinking:<alias>' in the uploaded mutations)."""
    row = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE source='mutation' AND amount > 0"
        " AND category=? AND txn_date >= ?", (f"sinking:{fund['alias']}", fund["saved_asof"])).fetchone()
    return fund["saved_so_far"] + row[0]


def sinking_paydays_left(payday: date, due: date, holidays) -> int:
    """Paydays from `payday` on which a contribution can still land before the due date."""
    holidays = frozenset(holidays) | id_holidays(due.year) | id_holidays(due.year - 1)   # cover the whole horizon
    last, n, p = due - timedelta(days=SINKING_BUFFER_DAYS), 0, payday
    while p <= last:
        n += 1
        p = next_payday(p, holidays)
    return n


def sinking_required(conn, fund, payday: date, holidays) -> dict:
    saved = sinking_saved(conn, fund)
    remaining = max(0, fund["target"] - saved)
    left = sinking_paydays_left(payday, date.fromisoformat(fund["due_date"]), holidays)
    return {"saved": saved, "remaining": remaining, "paydays_left": left,
            "per_month": _round_up(-(-remaining // left)) if left and remaining else 0}


def sinking_status(conn, today: date, alias: str | None = None) -> str:
    funds = conn.execute("SELECT * FROM sinking_funds" + (" WHERE alias=?" if alias else ""),
                         (alias,) if alias else ()).fetchall()
    if not funds:
        return "Belum ada dana terikat."
    hol = id_holidays(today.year) | id_holidays(today.year + 1) | id_holidays(today.year + 2)
    out = []
    for f in funds:
        p = last_working_day(today.year, today.month, hol)
        if p < today:
            p = next_payday(p, hol)
        s = sinking_required(conn, f, p, hol)
        pct = min(100, s["saved"] * 100 // f["target"])
        line = (f"{f['alias']}: target {format_idr(f['target'])} jatuh tempo {f['due_date']}; terkumpul "
                f"{format_idr(s['saved'])} ({pct}%); kurang {format_idr(s['remaining'])}")
        if s["remaining"] and s["paydays_left"]:
            line += f"; setoran {format_idr(s['per_month'])}/bulan selama {s['paydays_left']} gajian"
        elif s["remaining"]:
            line += "; TIDAK ADA gajian tersisa sebelum jatuh tempo"
        out.append(line)
    return "\n".join(out)


def collect_obligations(conn, payday: date, nxt: date, holidays=()) -> list[Obligation]:
    obs: list[Obligation] = []
    for f in conn.execute("SELECT * FROM sinking_funds"):
        s = sinking_required(conn, f, payday, holidays)
        if s["per_month"]:
            obs.append(Obligation("pool", f["alias"], payday, s["per_month"], from_account="main",
                                  pay_to=f["pool_pay_to"]))
    # cards: latest unpaid statement per card (overdue if due before payday)
    for r in conn.execute(
            "SELECT c.alias, c.pay_method, c.pay_to_alias, s.due_date, s.total_due, s.minimum_due"
            " FROM statements s JOIN cards c ON c.id = s.card_id"
            " WHERE s.paid_at IS NULL AND s.total_due > 0"
            " AND s.id = (SELECT MAX(id) FROM statements WHERE card_id = s.card_id)"):
        obs.append(Obligation("card", r["alias"], date.fromisoformat(r["due_date"]),
                              r["total_due"], r["minimum_due"], late_cost_bp=300,
                              method=r["pay_method"], pay_to=r["pay_to_alias"]))
    for r in conn.execute("SELECT alias, installment, due_day, rate_bp FROM debts WHERE tenor_left > 0"):
        for d in due_dates_in_window(r["due_day"], payday, nxt):
            obs.append(Obligation("debt", r["alias"], d, r["installment"],
                                  late_cost_bp=r["rate_bp"] or 0))
    for r in conn.execute("SELECT payee_alias, amount, due_day FROM fixed_expenses"):
        for d in due_dates_in_window(r["due_day"], payday, nxt):
            obs.append(Obligation("fixed", r["payee_alias"], d, r["amount"], pay_to=r["payee_alias"]))
    return obs


def plan_to_dict(plan: Plan) -> dict:
    def conv(o):
        return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in o.items()}
    d = asdict(plan)
    d["payday"], d["next_payday"] = plan.payday.isoformat(), plan.next_payday.isoformat()
    d["transfers"] = [conv(t) for t in d["transfers"]]
    d["unfunded"] = [conv(u) for u in d["unfunded"]]
    d["warnings"] = list(plan.warnings)
    return d


def generate_payday_plan(conn, today: date, payday: date | None = None,
                         salary: int | None = None) -> dict:
    hol = id_holidays(today.year) | id_holidays(today.year + 1)
    if payday is None:
        payday = last_working_day(today.year, today.month, hol)
        if payday < today:  # this month's payday already passed -> plan the next one
            payday = next_payday(payday, hol)
    if salary is None:
        salary = get_threshold(conn, "net_salary")
        if salary is None:
            raise ValueError("net_salary belum diset (set_threshold net_salary)")
    nxt = next_payday(payday, hol)
    plan = build_plan(payday, salary, collect_obligations(conn, payday, nxt, hol), hol,
                      buffer=get_threshold(conn, "cash_buffer", 0))
    snap = plan_to_dict(plan)
    snap["reminders"] = []
    for f in conn.execute("SELECT * FROM sinking_funds"):
        due = date.fromisoformat(f["due_date"])
        s = sinking_required(conn, f, payday, hol)
        planned = sum(t["amount"] for t in snap["transfers"] if t["to_alias"] == f["alias"])  # this payday's deposit
        if payday <= due < nxt:   # due inside this window: pay from the pool, not from salary
            who = f["creditor_pay_to"] or "(penerima belum diset)"
            extra = f" + setoran gajian ini {format_idr(planned)}" if planned else ""
            snap["reminders"].append(
                f"JATUH TEMPO {f['due_date']}: bayar {format_idr(f['target'])} untuk {f['alias']} dari rekening "
                f"pot {f['pool_alias']} ke {who} (ketik /rincian untuk nomor tujuan). "
                f"Terkumpul {format_idr(s['saved'])}{extra}.")
            if s["saved"] + planned < f["target"]:
                snap["warnings"].append(f"{f['alias']}: pot baru {format_idr(s['saved'] + planned)} dari "
                                        f"{format_idr(f['target'])}; kurang {format_idr(f['target'] - s['saved'] - planned)}.")
        elif due >= nxt and s["paydays_left"] == 0 and s["remaining"]:
            snap["warnings"].append(f"{f['alias']}: tidak ada gajian tersisa sebelum jatuh tempo; kurang {format_idr(s['remaining'])}.")
    for r in conn.execute(
            "SELECT c.alias FROM statements s JOIN cards c ON c.id = s.card_id WHERE s.reconciled = 0"
            " AND s.paid_at IS NULL AND s.id = (SELECT MAX(id) FROM statements WHERE card_id = s.card_id)"):
        snap["warnings"].append(f"Statement {r['alias']} belum cocok saat rekonsiliasi; angka tagihan perlu diperiksa.")
    conn.execute("INSERT INTO plans(payday,snapshot_json,created_at) VALUES (?,?,?)",
                 (payday.isoformat(), json.dumps(snap), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return snap


def summarize_plan(snap: dict) -> str:
    """Telegram-safe summary: aliases and amounts only, never full numbers, no URLs."""
    lines = [f"Rencana gajian {snap['payday']} (sampai {snap['next_payday']})",
             f"Gaji: {format_idr(snap['salary'])}"]
    for t in snap["transfers"]:
        how = " via menu aplikasi bank" if t.get("method") == "app_menu" else ""
        lines.append(f"- {t['date']} {t['to_alias']}: {format_idr(t['amount'])} ({t['reason']}){how}")
    for u in snap["unfunded"]:
        lines.append(f"! BELUM TERDANAI {u['to_alias']}: {format_idr(u['amount'])} "
                     f"({u['reason']}), estimasi biaya {format_idr(u['est_delay_cost'])}")
    lines += [f"* {r}" for r in snap.get("reminders", [])]
    lines.append(f"Kas ditahan: {format_idr(snap['cash_to_hold'])}; jatah harian {format_idr(snap['daily_allowance'])}")
    lines += [f"Peringatan: {w}" for w in snap["warnings"]]
    return "\n".join(lines)
