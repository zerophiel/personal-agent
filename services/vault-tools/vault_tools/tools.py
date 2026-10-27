"""Ledger-facing operations behind the MCP tools. No secrets and no full numbers here:
payees are referred to by alias only."""
from __future__ import annotations

import calendar
import json
import sqlite3
from dataclasses import asdict
from datetime import date, datetime, timezone

import holidays as _holidays

from .money import check_idr, format_idr
from .payday import Obligation, Plan, build_plan, last_working_day, next_payday


def id_holidays(year: int) -> frozenset[date]:
    """Indonesian national holidays (python-holidays). Excludes 'cuti bersama'."""
    h = _holidays.country_holidays("ID", years=[year - 1, year, year + 1])
    return frozenset(h.keys())


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

def upsert_card(conn: sqlite3.Connection, alias: str, bank: str, last4: str,
                statement_day: int, due_day: int, credit_limit: int) -> str:
    check_idr(credit_limit)
    conn.execute(
        "INSERT INTO cards(alias,bank,last4,statement_day,due_day,credit_limit) VALUES (?,?,?,?,?,?)"
        " ON CONFLICT(alias) DO UPDATE SET bank=excluded.bank,last4=excluded.last4,"
        "statement_day=excluded.statement_day,due_day=excluded.due_day,credit_limit=excluded.credit_limit",
        (alias, bank, last4, statement_day, due_day, credit_limit))
    conn.commit()
    return f"kartu {alias} ****{last4} tersimpan"


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


# ---- obligations and plan -----------------------------------------------------------

def collect_obligations(conn, payday: date, nxt: date) -> list[Obligation]:
    obs: list[Obligation] = []
    # cards: latest unpaid statement per card (overdue if due before payday)
    for r in conn.execute(
            "SELECT c.alias, s.due_date, s.total_due, s.minimum_due FROM statements s"
            " JOIN cards c ON c.id = s.card_id WHERE s.paid_at IS NULL AND s.total_due > 0"
            " AND s.id = (SELECT MAX(id) FROM statements WHERE card_id = s.card_id)"):
        obs.append(Obligation("card", r["alias"], date.fromisoformat(r["due_date"]),
                              r["total_due"], r["minimum_due"], late_cost_bp=300))
    for r in conn.execute("SELECT alias, installment, due_day, rate_bp FROM debts WHERE tenor_left > 0"):
        for d in due_dates_in_window(r["due_day"], payday, nxt):
            obs.append(Obligation("debt", r["alias"], d, r["installment"],
                                  late_cost_bp=r["rate_bp"] or 0))
    for r in conn.execute("SELECT payee_alias, amount, due_day FROM fixed_expenses"):
        for d in due_dates_in_window(r["due_day"], payday, nxt):
            obs.append(Obligation("fixed", r["payee_alias"], d, r["amount"]))
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
    plan = build_plan(payday, salary, collect_obligations(conn, payday, nxt), hol,
                      buffer=get_threshold(conn, "cash_buffer", 0))
    snap = plan_to_dict(plan)
    conn.execute("INSERT INTO plans(payday,snapshot_json,created_at) VALUES (?,?,?)",
                 (payday.isoformat(), json.dumps(snap), datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return snap


def summarize_plan(snap: dict) -> str:
    """Telegram-safe summary: aliases and amounts only, never full numbers, no URLs."""
    lines = [f"Rencana gajian {snap['payday']} (sampai {snap['next_payday']})",
             f"Gaji: {format_idr(snap['salary'])}"]
    for t in snap["transfers"]:
        lines.append(f"- {t['date']} {t['to_alias']}: {format_idr(t['amount'])} ({t['reason']})")
    for u in snap["unfunded"]:
        lines.append(f"! BELUM TERDANAI {u['to_alias']}: {format_idr(u['amount'])} "
                     f"({u['reason']}), estimasi biaya {format_idr(u['est_delay_cost'])}")
    lines.append(f"Kas ditahan: {format_idr(snap['cash_to_hold'])}; jatah harian {format_idr(snap['daily_allowance'])}")
    lines += [f"Peringatan: {w}" for w in snap["warnings"]]
    return "\n".join(lines)
