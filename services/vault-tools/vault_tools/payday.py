"""Deterministic payday plan. Pure functions, integer Rupiah, no I/O.

Rules (docs/payday.md):
- Payday = last working day (Mon-Fri, not in `holidays`) of the month, WIB dates.
- Window = [payday, next_payday).
- Obligations are funded in priority order; allocation is sequential, so once one item is
  not fully funded every later item gets 0. Nothing is dropped silently: unfunded amounts
  are reported with an estimated cost of delay.
- The living reserve is kept before anything that is saving rather than a bill: the emergency
  fund, the pot and card balances beyond the minimum are paid only from what is above it, so a
  pot deposit can never squeeze the money for daily life.
- A 'pool_rest' pot (pattern "sisa") is paid after the card balances and takes what is left; it
  is open-ended, so an unpaid part is not a shortfall.
- The bank's admin fee of a payment (`Obligation.fee`, estimated) is paid with it, from the same money, once per
  destination: the owner pays everything at once, so a card's minimum and the rest are one transfer. The fee for moving
  the living money to the daily account (`reserve_fee`) is kept with the reserve. Fees are listed apart (`Plan.fees`):
  transfers + fees + cash kept = salary.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable

from .money import bp_of, check_idr

# Lower number = funded first. From P_EMERGENCY on, only money above the living reserve is used.
P_OVERDUE, P_MIN_DUE, P_ESSENTIAL, P_INSTALLMENT, P_EMERGENCY, P_POT, P_CARD_REST, P_POT_REST, P_SAVING = range(9)
ABOVE_RESERVE = P_EMERGENCY
KINDS = {"card", "fixed", "debt", "pool", "pool_rest", "emergency", "saving", "oneoff"}


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


def window_payday(d: date, holidays: Iterable[date] = ()) -> date:
    """The payday whose window [payday, next payday) holds `d`."""
    p = last_working_day(d.year, d.month, holidays)
    if p <= d:
        return p
    y, m = (d.year - 1, 12) if d.month == 1 else (d.year, d.month - 1)
    return last_working_day(y, m, holidays)


@dataclass(frozen=True)
class Obligation:
    kind: str                 # card | fixed | debt | pool | pool_rest | emergency | saving | oneoff (a bill paid once)
    payee_alias: str          # alias + last4 only, never a full number
    due: date
    amount: int               # full amount; for cards the full statement balance
    minimum: int = 0          # cards only: minimum due
    from_account: str = "main"
    late_cost_bp: int = 0     # est. monthly interest/penalty on unpaid amount, basis points
    method: str = "transfer"  # transfer | app_menu (bank app menu) | autodebit (creditor debits the owner's account)
    pay_to: str | None = None  # transfer/app_menu: vault alias of the number to pay (shown only by /rincian);
                               # autodebit: accounts.alias of the account that gets debited
    fee: int = 0              # the bank's admin fee for paying it (estimated)
    fee_kind: str = "transfer"   # kartu (a payment to a card number) | transfer: what the fee line calls it

    def __post_init__(self):
        if self.method not in ("transfer", "app_menu", "autodebit"):
            raise ValueError(f"unknown method {self.method}")
        if self.kind not in KINDS:
            raise ValueError(f"unknown kind {self.kind}")
        if self.fee_kind not in ("kartu", "transfer"):
            raise ValueError(f"unknown fee kind {self.fee_kind}")
        check_idr(self.amount)
        check_idr(self.minimum)
        check_idr(self.fee)
        if self.amount < 0 or self.minimum < 0 or self.minimum > self.amount:
            raise ValueError("require 0 <= minimum <= amount")
        if self.fee < 0:
            raise ValueError("require fee >= 0")


@dataclass(frozen=True)
class Transfer:
    date: date
    from_account: str
    to_alias: str
    amount: int
    reason: str
    method: str = "transfer"
    pay_to: str | None = None
    due: date | None = None


@dataclass(frozen=True)
class Unfunded:
    to_alias: str
    amount: int
    reason: str
    est_delay_cost: int


@dataclass(frozen=True)
class Fee:
    date: date
    to_alias: str             # the plan item paid with it (the living money: its payee alias)
    amount: int
    kind: str                 # kartu | transfer


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
    reserve: int = 0
    fees: tuple[Fee, ...] = field(default_factory=tuple)


def _items(payday: date, obligations: Iterable[Obligation], horizon: date):
    """Expand obligations into (priority, due, alias, amount, reason, from_account, late_bp, method, pay_to, fee,
    fee_kind)."""
    out = []
    for o in obligations:
        if o.due >= horizon:
            continue  # belongs to a later window
        overdue = o.due < payday
        if o.kind == "card":
            minimum = o.minimum
            out.append((P_OVERDUE if overdue else P_MIN_DUE, o.due, o.payee_alias, minimum,
                        "tagihan kartu - minimum", o.from_account, o.late_cost_bp, o.method, o.pay_to, o.fee,
                        o.fee_kind))
            rest = o.amount - minimum
            if rest:
                # only the minimum of an overdue card is urgent (late fee); the rest is interest, paid above the living money
                out.append((P_CARD_REST, o.due, o.payee_alias, rest,
                            "tagihan kartu - sisa saldo (bayar penuh)", o.from_account, o.late_cost_bp,
                            o.method, o.pay_to, o.fee, o.fee_kind))
            continue
        prio = {"fixed": P_ESSENTIAL, "debt": P_INSTALLMENT, "emergency": P_EMERGENCY, "pool": P_POT,
                "pool_rest": P_POT_REST, "saving": P_SAVING, "oneoff": P_ESSENTIAL}[o.kind]
        if overdue and o.kind in ("fixed", "debt", "oneoff"):
            prio = P_OVERDUE
        out.append((prio, o.due, o.payee_alias, o.amount,
                    {"fixed": "pengeluaran tetap", "debt": "cicilan", "pool": "transfer pool", "emergency": "dana darurat",
                     "pool_rest": "setoran pot (sisa setelah kartu)", "saving": "tabungan",
                     "oneoff": "tagihan sekali bayar"}[o.kind],
                    o.from_account, o.late_cost_bp, o.method, o.pay_to, o.fee, o.fee_kind))
    # stable total order: priority, due date, alias, reason
    # card balances beyond the minimum: highest interest first (avalanche), then earliest due
    out.sort(key=lambda t: (t[0], -t[6] if t[0] == P_CARD_REST else 0, t[1], t[2], t[4]))
    return [t for t in out if t[3] > 0]


def build_plan(payday: date, salary: int, obligations: Iterable[Obligation],
               holidays: Iterable[date] = (), buffer: int = 0, reserve: int = 0, reserve_fee: int = 0,
               reserve_to: str = "uang-harian") -> Plan:
    """`reserve` is cash kept for day-to-day living: obligations and card minimums are paid before it; the emergency
    fund, the pot, card balances beyond the minimum and savings only from what is left above it. `reserve_fee` is the
    admin fee of moving the reserve to the daily account `reserve_to`: it is kept with the reserve and charged once the
    reserve is moved, so the cash kept is the living money itself."""
    check_idr(salary)
    check_idr(buffer)
    check_idr(reserve)
    check_idr(reserve_fee)
    if salary < 0 or buffer < 0 or reserve < 0 or reserve_fee < 0:
        raise ValueError("salary, buffer, reserve and reserve_fee must be >= 0")
    nxt = next_payday(payday, holidays)
    remaining = salary
    hold = reserve + reserve_fee if reserve else 0
    transfers: list[Transfer] = []
    unfunded: list[Unfunded] = []
    fees: list[Fee] = []
    charged: set[str] = set()        # destinations whose fee is taken: one transfer each, a card's minimum and rest together
    kept_by_reserve = False
    for prio, due, alias, amount, reason, acct, late_bp, method, pay_to, fee, fee_kind in _items(payday, obligations, nxt):
        key = pay_to or alias
        fee = 0 if key in charged else fee
        limit = remaining - hold if prio >= ABOVE_RESERVE else remaining
        pay = min(amount, max(0, limit - fee))
        remaining -= pay
        if pay:
            tdate = payday if prio == P_OVERDUE else max(payday, due - timedelta(days=3))
            transfers.append(Transfer(tdate, acct, alias, pay, reason, method, pay_to, due))
            if fee:
                fees.append(Fee(tdate, alias, fee, fee_kind))
                charged.add(key)
                remaining -= fee
        short = amount - pay
        if short and prio != P_POT_REST:          # the pot after the cards takes what is left: the rest is not a shortfall
            if prio >= ABOVE_RESERVE and reserve and remaining <= hold:
                kept_by_reserve = True       # held back by the living reserve, not by an empty account
            unfunded.append(Unfunded(alias, short, reason, bp_of(short, late_bp)))
    if reserve and reserve_fee and remaining > reserve_fee:
        fees.append(Fee(payday, reserve_to, reserve_fee, "transfer"))
        remaining -= reserve_fee
    days = (nxt - payday).days
    warnings = []
    if unfunded:
        if kept_by_reserve and reserve:
            warnings.append(f"Sebagian saldo kartu/pot/tabungan belum dibayar karena kas Rp {reserve:,} ".replace(",", ".")
                            + "dicadangkan untuk hidup harian; lihat daftar belum terdanai dan saran.")
        else:
            warnings.append("Gaji tidak cukup untuk semua kewajiban; lihat daftar belum terdanai.")
    if remaining < buffer:
        warnings.append("Sisa kas di bawah buffer yang Anda tetapkan.")
    return Plan(payday, nxt, salary, tuple(transfers), tuple(unfunded), remaining,
                remaining // days if days else 0, tuple(warnings), reserve, tuple(fees))


def living_money(snap: dict) -> int:
    """A stored plan's whole month of daily money: what it keeps from the salary (the top-up) plus last cycle's leftover
    the owner still held. Never the salary part alone: on 2026-10-31 the pace warning read 22% used of the 2.827.889
    top-up while the owner had 2.827.889 + 4.718.116 = 7.546.005 for the month."""
    return snap["cash_to_hold"] + (snap.get("living_leftover") or 0)
