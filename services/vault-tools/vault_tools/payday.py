"""Deterministic payday plan. Pure functions, integer Rupiah, no I/O.

Rules (docs/payday.md):
- Payday = last working day (Mon-Fri, not in `holidays`) of the month, WIB dates.
- Window = [payday, next_payday).
- Obligations are funded in priority order; allocation is sequential, so once one item is
  not fully funded every later item gets 0. Nothing is dropped silently: unfunded amounts
  are reported with an estimated cost of delay.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable

from .money import bp_of, check_idr

# Lower number = funded first.
P_OVERDUE, P_MIN_DUE, P_ESSENTIAL, P_INSTALLMENT, P_CARD_REST, P_SAVING = 0, 1, 2, 3, 4, 5
KINDS = {"card", "fixed", "debt", "pool", "saving"}


def is_working_day(d: date, holidays: frozenset[date]) -> bool:
    return d.weekday() < 5 and d not in holidays


def last_working_day(year: int, month: int, holidays: Iterable[date] = ()) -> date:
    hol = frozenset(holidays)
    d = date(year, month, calendar.monthrange(year, month)[1])
    while not is_working_day(d, hol):
        d -= timedelta(days=1)
    return d


def next_payday(after: date, holidays: Iterable[date] = ()) -> date:
    """Payday of the month following `after`'s month."""
    y, m = (after.year + 1, 1) if after.month == 12 else (after.year, after.month + 1)
    return last_working_day(y, m, holidays)


@dataclass(frozen=True)
class Obligation:
    kind: str                 # card | fixed | debt | pool | saving
    payee_alias: str          # alias + last4 only, never a full number
    due: date
    amount: int               # full amount; for cards the full statement balance
    minimum: int = 0          # cards only: minimum due
    from_account: str = "main"
    late_cost_bp: int = 0     # est. monthly interest/penalty on unpaid amount, basis points
    method: str = "transfer"  # transfer | app_menu (pay from the bank's app menu)
    pay_to: str | None = None  # vault alias of the number to pay (shown only by /rincian)

    def __post_init__(self):
        if self.method not in ("transfer", "app_menu"):
            raise ValueError(f"unknown method {self.method}")
        if self.kind not in KINDS:
            raise ValueError(f"unknown kind {self.kind}")
        check_idr(self.amount)
        check_idr(self.minimum)
        if self.amount < 0 or self.minimum < 0 or self.minimum > self.amount:
            raise ValueError("require 0 <= minimum <= amount")


@dataclass(frozen=True)
class Transfer:
    date: date
    from_account: str
    to_alias: str
    amount: int
    reason: str
    method: str = "transfer"
    pay_to: str | None = None


@dataclass(frozen=True)
class Unfunded:
    to_alias: str
    amount: int
    reason: str
    est_delay_cost: int


@dataclass(frozen=True)
class Plan:
    payday: date
    next_payday: date
    salary: int
    transfers: tuple[Transfer, ...]
    unfunded: tuple[Unfunded, ...]
    cash_to_hold: int
    daily_allowance: int
    warnings: tuple[str, ...] = field(default_factory=tuple)


def _items(payday: date, obligations: Iterable[Obligation], horizon: date):
    """Expand obligations into (priority, due, alias, amount, reason, from_account, late_bp)."""
    out = []
    for o in obligations:
        if o.due >= horizon:
            continue  # belongs to a later window
        overdue = o.due < payday
        if o.kind == "card":
            minimum = o.minimum
            out.append((P_OVERDUE if overdue else P_MIN_DUE, o.due, o.payee_alias, minimum,
                        "tagihan kartu - minimum", o.from_account, o.late_cost_bp, o.method, o.pay_to))
            rest = o.amount - minimum
            if rest:
                out.append((P_OVERDUE if overdue else P_CARD_REST, o.due, o.payee_alias, rest,
                            "tagihan kartu - sisa saldo (bayar penuh)", o.from_account, o.late_cost_bp,
                            o.method, o.pay_to))
            continue
        prio = {"fixed": P_ESSENTIAL, "debt": P_INSTALLMENT, "pool": P_INSTALLMENT,
                "saving": P_SAVING}[o.kind]
        out.append((P_OVERDUE if overdue else prio, o.due, o.payee_alias, o.amount,
                    {"fixed": "pengeluaran tetap", "debt": "cicilan", "pool": "transfer pool",
                     "saving": "tabungan"}[o.kind], o.from_account, o.late_cost_bp, o.method, o.pay_to))
    # stable total order: priority, due date, alias, reason
    out.sort(key=lambda t: (t[0], t[1], t[2], t[4]))
    return [t for t in out if t[3] > 0]


def build_plan(payday: date, salary: int, obligations: Iterable[Obligation],
               holidays: Iterable[date] = (), buffer: int = 0) -> Plan:
    check_idr(salary)
    check_idr(buffer)
    if salary < 0 or buffer < 0:
        raise ValueError("salary and buffer must be >= 0")
    nxt = next_payday(payday, holidays)
    remaining = salary
    transfers: list[Transfer] = []
    unfunded: list[Unfunded] = []
    for prio, due, alias, amount, reason, acct, late_bp, method, pay_to in _items(payday, obligations, nxt):
        pay = min(amount, remaining)
        remaining -= pay
        if pay:
            tdate = payday if prio == P_OVERDUE else max(payday, due - timedelta(days=3))
            transfers.append(Transfer(tdate, acct, alias, pay, reason, method, pay_to))
        short = amount - pay
        if short:
            unfunded.append(Unfunded(alias, short, reason, bp_of(short, late_bp)))
    days = (nxt - payday).days
    warnings = []
    if unfunded:
        warnings.append("Gaji tidak cukup untuk semua kewajiban; lihat daftar belum terdanai.")
    if remaining < buffer:
        warnings.append("Sisa kas di bawah buffer yang Anda tetapkan.")
    return Plan(payday, nxt, salary, tuple(transfers), tuple(unfunded), remaining,
                remaining // days if days else 0, tuple(warnings))
