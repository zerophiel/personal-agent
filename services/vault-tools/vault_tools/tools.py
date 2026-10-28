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


WIB = timezone(timedelta(hours=7))   # Indonesia West time: fixed offset, no DST


def wib_today() -> date:
    """Today's date in WIB. The container clock is UTC, which lags a day between 00:00 and 07:00 WIB."""
    return datetime.now(WIB).date()


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
                pay_method: str | None = None, pay_to_alias: str | None = None,
                interest_bp_month: int | None = None) -> str:
    """interest_bp_month: the card's monthly interest on an unpaid balance in basis points (2,25% = 225),
    as printed on the statement. Left out = keep the stored value (or the default of 2,25%)."""
    check_idr(credit_limit)
    if interest_bp_month is not None:
        check_idr(interest_bp_month)
        if not 0 <= interest_bp_month <= 1000:
            raise ValueError("interest_bp_month harus 0..1000 (basis poin per bulan, mis. 225 = 2,25%)")
    method, pay_to = resolve_pay(conn, bank, pay_method, pay_to_alias)
    conn.execute(
        "INSERT INTO cards(alias,bank,last4,statement_day,due_day,credit_limit,pay_method,pay_to_alias,interest_bp_month)"
        " VALUES (?,?,?,?,?,?,?,?,?)"
        " ON CONFLICT(alias) DO UPDATE SET bank=excluded.bank,last4=excluded.last4,"
        "statement_day=excluded.statement_day,due_day=excluded.due_day,credit_limit=excluded.credit_limit,"
        "pay_method=excluded.pay_method,pay_to_alias=COALESCE(excluded.pay_to_alias,cards.pay_to_alias),"
        "interest_bp_month=COALESCE(excluded.interest_bp_month,cards.interest_bp_month)",
        (alias, bank, last4, statement_day, due_day, credit_limit, method, pay_to, interest_bp_month))
    conn.commit()
    how = "lewat menu aplikasi" if method == "app_menu" else "transfer"
    note = "" if pay_to or conn.execute("SELECT pay_to_alias FROM cards WHERE alias=?", (alias,)).fetchone()[0] \
        else f"; tujuan bayar belum diset ({how})"
    return f"kartu {alias} ****{last4} tersimpan, bayar {how}{note}"


def record_card_payment(conn, today: date, card_alias: str, amount: int) -> str:
    """The owner paid `amount` towards the card's latest statement (full or partial). A partial payment leaves
    the rest to be planned (and to accrue interest); a full one closes the statement."""
    check_idr(amount)
    if amount <= 0:
        raise ValueError("amount harus > 0")
    s = conn.execute("SELECT s.id, s.total_due, s.paid_amount FROM statements s JOIN cards c ON c.id = s.card_id"
                     " WHERE c.alias=? AND s.paid_at IS NULL ORDER BY s.statement_date DESC, s.id DESC LIMIT 1", (card_alias,)).fetchone()
    if s is None:
        raise ValueError(f"tidak ada tagihan {card_alias} yang belum dibayar")
    paid = s["paid_amount"] + amount
    closed = paid >= s["total_due"]
    conn.execute("UPDATE statements SET paid_amount=?, paid_at=? WHERE id=?",
                 (paid, today.isoformat() if closed else None, s["id"]))
    conn.commit()
    left = max(0, s["total_due"] - paid)
    over = f" (kelebihan {format_idr(paid - s['total_due'])}: cek apakah ada salah ketik)" if paid > s["total_due"] else ""
    return (f"{card_alias}: LUNAS{over}." if closed else
            f"{card_alias}: dibayar {format_idr(paid)} dari {format_idr(s['total_due'])}; sisa {format_idr(left)}.")


def link_card_payees(conn) -> list[str]:
    """Point each transfer-paid card at the payee the owner has registered for it: a stored card number with the same
    last 4 digits, and for Jenius the owner's Jenius account. Cards already linked are left alone."""
    out = []
    for c in conn.execute("SELECT alias, bank, last4 FROM cards WHERE pay_method='transfer' AND pay_to_alias IS NULL").fetchall():
        if c["bank"].lower().startswith("jenius"):
            hit = conn.execute("SELECT alias FROM payee_secrets WHERE kind='account' AND lower(bank) IN ('jenius','btpn','smbc')"
                               " ORDER BY created_at DESC LIMIT 1").fetchone()
        else:
            hit = conn.execute("SELECT alias FROM payee_secrets WHERE kind='card' AND last4=? ORDER BY created_at DESC LIMIT 1", (c["last4"],)).fetchone()
        if hit:
            conn.execute("UPDATE cards SET pay_to_alias=? WHERE alias=?", (hit["alias"], c["alias"]))
            out.append(f"{c['alias']} -> {hit['alias']}")
    conn.commit()
    return out or ["Tidak ada kartu yang bisa dihubungkan: nomor kartu atau rekening tujuan belum didaftarkan."]


def upsert_debt(conn, alias: str, lender: str, outstanding: int, installment: int,
                tenor_left: int, due_day: int, rate_bp: int | None = None,
                pay_method: str | None = None, pay_to_alias: str | None = None,
                debit_account_alias: str | None = None) -> str:
    """pay_method 'autodebit': the creditor debits `debit_account_alias` (an account of the owner) on the due
    day, so the plan only reminds to keep that balance. 'transfer': pay to `pay_to_alias` (account/VA payee).
    Fields left out on an existing debt keep their stored value."""
    check_idr(outstanding), check_idr(installment)
    old = conn.execute("SELECT pay_method, pay_to_alias, debit_account_alias FROM debts WHERE alias=?",
                       (alias,)).fetchone()
    method = pay_method or (old["pay_method"] if old else "transfer")
    if method not in ("transfer", "autodebit"):
        raise ValueError("pay_method harus transfer atau autodebit")
    pay_to = pay_to_alias if pay_to_alias is not None else (old["pay_to_alias"] if old else None)
    debit = debit_account_alias if debit_account_alias is not None else (old["debit_account_alias"] if old else None)
    if method == "autodebit":
        if debit is None:
            raise ValueError("autodebit butuh debit_account_alias (rekening yang didebet)")
        if conn.execute("SELECT 1 FROM accounts WHERE alias=?", (debit,)).fetchone() is None:
            raise ValueError(f"rekening {debit} belum terdaftar (upsert_account dulu)")
        pay_to = None
    else:
        debit = None
        if pay_to is not None:
            row = conn.execute("SELECT kind FROM payee_secrets WHERE alias=?", (pay_to,)).fetchone()
            if row is None or row["kind"] not in ("account", "va"):
                raise ValueError(f"{pay_to} belum tersimpan sebagai nomor rekening/VA (/rekening atau /va)")
    conn.execute(
        "INSERT INTO debts(alias,lender,outstanding,installment,tenor_left,rate_bp,due_day,pay_method,pay_to_alias,"
        "debit_account_alias) VALUES (?,?,?,?,?,?,?,?,?,?) ON CONFLICT(alias) DO UPDATE SET lender=excluded.lender,"
        "outstanding=excluded.outstanding,installment=excluded.installment,"
        "tenor_left=excluded.tenor_left,rate_bp=excluded.rate_bp,due_day=excluded.due_day,"
        "pay_method=excluded.pay_method,pay_to_alias=excluded.pay_to_alias,"
        "debit_account_alias=excluded.debit_account_alias",
        (alias, lender, outstanding, installment, tenor_left, rate_bp, due_day, method, pay_to, debit))
    conn.commit()
    how = f"autodebet dari {debit}" if method == "autodebit" else "transfer"
    return f"utang {alias} tersimpan, bayar {how}"


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


def reserve_for(conn, payday: date) -> tuple[int | None, str]:
    """The daily-cash reserve this payday's plan holds back. A one-off override (the owner already holds cash from the
    last cycle) applies only to paydays up to `living_reserve_override_until` (YYYYMMDD); later plans use the normal one."""
    ov, until = get_threshold(conn, "living_reserve_override"), get_threshold(conn, "living_reserve_override_until")
    if ov is not None and until and int(payday.strftime("%Y%m%d")) <= until:
        return ov, f"sementara (saldo awal ikut dipakai), berlaku sampai {str(until)[:4]}-{str(until)[4:6]}-{str(until)[6:]}"
    return get_threshold(conn, "living_reserve"), "diset pemilik"


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


def pending_statements(conn, events_path: str, ingest_dir: str, limit: int = 8) -> list[str]:
    """Statement files from ingest-gmail that are not recorded (or skipped) yet, oldest first. Derived from the
    ledger every call, so it does not depend on the events cursor and never "loses" work the model left unfinished."""
    try:
        with open(events_path) as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return []
    done = {r[0] for r in conn.execute("SELECT file_hash FROM statements")} | \
           {r[0] for r in conn.execute("SELECT file_ref FROM skipped_files")}
    seen: dict[str, dict] = {}
    for line in lines:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        ref = str(ev.get("file_ref", ""))
        if ev.get("type") != "new_statement" or not ref or ref in seen:
            continue
        if ref.removesuffix(".pdf") in done or ref in done or not os.path.isfile(os.path.join(ingest_dir, ref)):
            continue
        seen[ref] = ev
    todo = sorted(seen.values(), key=lambda e: (e.get("received_ms", 0), e.get("file_ref", "")))
    out = [f"belum diproses: {len(todo)} berkas"]
    out += [f"bank={str(e.get('bank'))[:12]}; file_ref={e['file_ref'][:80]}" for e in todo[:max(1, min(limit, 20))]]
    return out


def skip_statement_file(conn, file_ref: str, reason: str) -> str:
    if not file_ref or len(file_ref) > 120 or "/" in file_ref:
        raise ValueError("file_ref tidak valid")
    conn.execute("INSERT OR REPLACE INTO skipped_files(file_ref, reason, created_at) VALUES (?,?,?)",
                 (file_ref, reason[:120], datetime.now(timezone.utc).isoformat()))
    conn.commit()
    return f"{file_ref[:16]}...: dilewati ({reason[:60]})"


# ---- obligations and plan -----------------------------------------------------------

# ---- sinking funds: a lump sum owed on a date, saved up in the owner's pool account ----------

SINKING_BUFFER_DAYS = 3        # the last contribution must land this many days before the due date
ROUND_UP_TO = 1_000            # contributions are rounded up to a neat Rp 1.000


DEFAULT_CARD_INTEREST_BP = 225   # 2.25% a month until the owner/statement gives the card's own rate


def card_advice(conn, snap: dict, payday: date, holidays) -> list[str]:
    """Numbers-only guidance for each card: pay in full, partly, or minimum, what an unpaid balance costs
    next month, and what could be traded to pay it off. Pure arithmetic over the plan; the owner decides."""
    advice = []
    cards = conn.execute(
        "SELECT c.alias, c.interest_bp_month, s.total_due - s.paid_amount AS total_due,"
        " MAX(0, s.minimum_due - s.paid_amount) AS minimum_due FROM statements s JOIN cards c ON c.id = s.card_id"
        " WHERE s.paid_at IS NULL AND s.total_due - s.paid_amount > 0"
        " AND s.id = (SELECT id FROM statements WHERE card_id = s.card_id ORDER BY statement_date DESC, id DESC LIMIT 1)"
        " ORDER BY COALESCE(c.interest_bp_month, ?) DESC", (get_threshold(conn, "default_card_interest_bp", DEFAULT_CARD_INTEREST_BP),)).fetchall()
    default_rate = get_threshold(conn, "default_card_interest_bp", DEFAULT_CARD_INTEREST_BP)
    carried, carried_cost = 0, 0
    for c in cards:
        paid = sum(t["amount"] for t in snap["transfers"] if t["to_alias"] == c["alias"])
        rate = c["interest_bp_month"] if c["interest_bp_month"] is not None else default_rate
        rest = max(0, c["total_due"] - paid)
        if paid >= c["total_due"]:
            advice.append(f"{c['alias']}: LUNASI {format_idr(c['total_due'])}. Tidak ada bunga.")
            continue
        cost = bp_of_idr(rest, rate)
        carried += rest
        carried_cost += cost
        how = ("hanya minimum" if paid <= c["minimum_due"] else "bayar sebagian")
        advice.append(f"{c['alias']}: {how} {format_idr(paid)} dari {format_idr(c['total_due'])} (minimum {format_idr(c['minimum_due'])}). "
                      f"Sisa {format_idr(rest)} berbunga sekitar {format_idr(cost)} bulan depan ({rate / 100:.2f}%/bulan).")
    if carried:
        reserve = snap.get("reserve", 0)
        if reserve:
            advice.append(f"Opsi A: kurangi cadangan harian {format_idr(min(reserve, carried))} untuk melunasi lebih banyak "
                          f"(hemat bunga sekitar {format_idr(carried_cost * min(reserve, carried) // carried)}); risikonya kas harian lebih tipis.")
        for f in conn.execute("SELECT * FROM sinking_funds").fetchall():
            planned = sum(t["amount"] for t in snap["transfers"] if t["to_alias"] == f["alias"])
            s = sinking_required(conn, f, payday, holidays)
            delta = min(carried, planned)
            if delta and s["paydays_left"] > 1:
                base = _round_up(-(-(s["remaining"] - planned) // (s["paydays_left"] - 1)))
                new = _round_up(-(-(s["remaining"] - planned + delta) // (s["paydays_left"] - 1)))
                saved = carried_cost * delta // carried
                advice.append(f"Opsi B: tunda {format_idr(delta)} dari setoran pot {f['alias']} untuk melunasi kartu "
                              f"(hemat bunga sekitar {format_idr(saved)}); setoran bulan depan naik dari {format_idr(base)} "
                              f"menjadi {format_idr(new)}. Pot tidak berbunga, jadi menunda tidak menambah biaya selama sisa gajian masih cukup.")
        advice.append(f"Jika tidak ada yang diubah, total bunga kartu bulan depan sekitar {format_idr(carried_cost)}.")
    target = get_threshold(conn, "monthly_savings_target", 0)
    if target:
        got = sum(t["amount"] for t in snap["transfers"] if t["to_alias"] == "tabungan")
        advice.append(f"Tabungan: {format_idr(got)} dari target {format_idr(target)}."
                      + ("" if got >= target else " Target belum tercapai bulan ini."))
    return advice


def bp_of_idr(amount: int, bp: int) -> int:
    return (amount * bp + 5_000) // 10_000


def _round_up(value: int, step: int = ROUND_UP_TO) -> int:
    return -(-value // step) * step


def upsert_sinking_fund(conn, alias: str, target: int, due_date: str, pool_alias: str,
                        pool_pay_to_alias: str, creditor_pay_to_alias: str | None = None,
                        saved_so_far: int | None = None, today: date | None = None, note: str | None = None) -> str:
    """Create or update a fund. `saved_so_far=None` on an existing fund keeps the tracked balance and
    its start date (attaching a creditor never resets progress); a number restarts tracking from today."""
    existing = conn.execute("SELECT saved_so_far, saved_asof FROM sinking_funds WHERE alias=?", (alias,)).fetchone()
    if saved_so_far is None:
        saved_so_far = existing["saved_so_far"] if existing else 0
        keep_asof = existing["saved_asof"] if existing else None
    else:
        keep_asof = None
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
    conn.execute(
        "INSERT INTO sinking_funds(alias,target,due_date,pool_alias,pool_pay_to,creditor_pay_to,saved_so_far,saved_asof,note)"
        " VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(alias) DO UPDATE SET target=excluded.target,"
        "due_date=excluded.due_date,pool_alias=excluded.pool_alias,pool_pay_to=excluded.pool_pay_to,"
        "creditor_pay_to=COALESCE(excluded.creditor_pay_to,sinking_funds.creditor_pay_to),"
        "saved_so_far=excluded.saved_so_far,saved_asof=excluded.saved_asof,"
        "note=COALESCE(excluded.note,sinking_funds.note)",
        (alias, target, due_date, pool_alias, pool_pay_to_alias, creditor_pay_to_alias, saved_so_far,
         keep_asof or today.isoformat(), note))
    conn.commit()
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
    default_rate = get_threshold(conn, "default_card_interest_bp", DEFAULT_CARD_INTEREST_BP)
    for r in conn.execute(
            "SELECT c.alias, c.pay_method, c.pay_to_alias, c.interest_bp_month, s.due_date,"
            " s.total_due - s.paid_amount AS total_due, MAX(0, s.minimum_due - s.paid_amount) AS minimum_due"
            " FROM statements s JOIN cards c ON c.id = s.card_id"
            " WHERE s.paid_at IS NULL AND s.total_due - s.paid_amount > 0"
            " AND s.id = (SELECT id FROM statements WHERE card_id = s.card_id ORDER BY statement_date DESC, id DESC LIMIT 1)"):
        obs.append(Obligation("card", r["alias"], date.fromisoformat(r["due_date"]),
                              r["total_due"], r["minimum_due"],
                              late_cost_bp=r["interest_bp_month"] if r["interest_bp_month"] is not None else default_rate,
                              method=r["pay_method"], pay_to=r["pay_to_alias"]))
    target = get_threshold(conn, "monthly_savings_target", 0)
    if target and target > 0:     # savings come after card balances: card interest (about 2-3% a month) beats any savings yield
        obs.append(Obligation("saving", "tabungan", payday, target))
    for r in conn.execute("SELECT alias, installment, due_day, rate_bp, pay_method, pay_to_alias, debit_account_alias"
                          " FROM debts WHERE tenor_left > 0"):
        auto = r["pay_method"] == "autodebit"
        for d in due_dates_in_window(r["due_day"], payday, nxt):
            # rate_bp is the ANNUAL rate; the delay cost estimate is per month
            obs.append(Obligation("debt", r["alias"], d, r["installment"],
                                  late_cost_bp=(r["rate_bp"] or 0) // 12,
                                  method="autodebit" if auto else "transfer",
                                  pay_to=r["debit_account_alias"] if auto else r["pay_to_alias"]))
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
    from . import health   # local import: health -> mutations -> (lazy) health
    reserve, reserve_source = reserve_for(conn, payday)
    if reserve is None:
        reserve = health.estimate_living_reserve(conn, payday, salary)
        reserve_source = "estimasi dari transaksi yang sudah diverifikasi" if reserve else "belum diset"
    obs = collect_obligations(conn, payday, nxt, hol)
    plan = build_plan(payday, salary, obs, hol, buffer=get_threshold(conn, "cash_buffer", 0), reserve=reserve)
    snap = plan_to_dict(plan)
    snap["reserve_source"] = reserve_source
    snap["reminders"] = []
    # A card bill that falls due BEFORE this payday cannot wait for the salary: it must be paid from the balance
    # on hand. Shown first, because a late payment costs a fee and may hurt the credit record.
    for o in sorted((o for o in obs if o.kind == "card" and o.due < payday), key=lambda o: o.due):
        if o.minimum <= 0:   # the owner already paid at least the minimum: no late fee risk, only interest on the rest
            snap["reminders"].append(
                f"INFO: tagihan {o.payee_alias} sudah memenuhi minimum; sisa {format_idr(o.amount)} jatuh tempo "
                f"{o.due.isoformat()} (sebelum gajian {payday.isoformat()}). Melunasinya sebelum tanggal itu menghindari bunga.")
            continue
        gone = o.due < today
        snap["reminders"].append(
            f"{'SUDAH LEWAT' if gone else 'MENDESAK'}: tagihan {o.payee_alias} jatuh tempo {o.due.isoformat()}, "
            f"sebelum gajian {payday.isoformat()}. Bayar minimal {format_idr(o.minimum)} (penuh {format_idr(o.amount)}) "
            f"dari saldo yang ada sekarang"
            + (" agar tidak kena denda; sisanya bisa setelah gajian." if o.amount > o.minimum else "."))
    for t in snap["transfers"]:
        if t.get("method") == "autodebit":
            snap["reminders"].append(
                f"AUTODEBET {t['to_alias']}: pastikan saldo rekening {t.get('pay_to') or '(rekening belum diset)'} "
                f"minimal {format_idr(t['amount'])} sebelum {t.get('due') or 'jatuh tempo'}; tidak perlu transfer ke kreditur.")
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
    snap["advice"] = card_advice(conn, snap, payday, hol)
    if reserve_source == "belum diset" and snap["advice"]:     # only matters when cards or savings are in play
        snap["warnings"].append("Cadangan hidup harian belum diset: set_threshold living_reserve (atau verifikasi kategori "
                                "transaksi agar bisa diestimasi). Tanpa itu, seluruh sisa gaji dianggap boleh dipakai melunasi kartu.")
    for r in conn.execute(
            "SELECT c.alias FROM statements s JOIN cards c ON c.id = s.card_id WHERE s.reconciled = 0"
            " AND s.paid_at IS NULL AND s.id = (SELECT id FROM statements WHERE card_id = s.card_id ORDER BY statement_date DESC, id DESC LIMIT 1)"):
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
        how = {"app_menu": " via menu aplikasi bank",
               "autodebit": f" autodebet, saldo harus cukup sebelum {t.get('due')}"}.get(t.get("method"), "")
        lines.append(f"- {t['date']} {t['to_alias']}: {format_idr(t['amount'])} ({t['reason']}){how}")
    for u in snap["unfunded"]:
        lines.append(f"! BELUM TERDANAI {u['to_alias']}: {format_idr(u['amount'])} "
                     f"({u['reason']}), estimasi biaya {format_idr(u['est_delay_cost'])}")
    lines += [f"* {r}" for r in snap.get("reminders", [])]
    if snap.get("reserve"):
        lines.append(f"Cadangan hidup harian: {format_idr(snap['reserve'])} ({snap.get('reserve_source')})")
    lines += [f"> {a}" for a in snap.get("advice", [])]
    lines.append(f"Kas ditahan: {format_idr(snap['cash_to_hold'])}; jatah harian {format_idr(snap['daily_allowance'])}")
    lines += [f"Peringatan: {w}" for w in snap["warnings"]]
    return "\n".join(lines)
