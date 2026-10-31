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
from .health import LIVING_ACCOUNT, cash_spent, spending_pace
from .payday import Obligation, Plan, build_plan, last_working_day, living_money, next_payday


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


PAYDAY_LOOKBACK_DAYS = 7   # the owner pays everything on the 1st, a day or two AFTER the salary (last working day)


def current_payday(today: date, holidays=None) -> date:
    """The payday a plan made today belongs to. Up to PAYDAY_LOOKBACK_DAYS after a payday it is still the current one
    (asked on Nov 1, the plan is the Oct 30 salary's and pays the bills due in early November); otherwise the coming one."""
    hol = frozenset(holidays) if holidays is not None else id_holidays(today.year)
    p = last_working_day(today.year, today.month, hol)
    if p > today:
        y, m = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        prev = last_working_day(y, m, hol)
        return prev if (today - prev).days <= PAYDAY_LOOKBACK_DAYS else p
    return p if (today - p).days <= PAYDAY_LOOKBACK_DAYS else next_payday(p, hol)


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
    twin = conn.execute("SELECT alias FROM cards WHERE lower(bank)=lower(?) AND last4=? AND alias != ?", (bank, last4, alias)).fetchone()
    if twin:      # the same physical card under a second alias would count its bill and installments twice
        raise ValueError(f"kartu {bank} berakhiran {last4} sudah terdaftar sebagai {twin['alias']}; pakai alias itu")
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


def card_rate(conn, interest_bp_month: int | None) -> int:
    return interest_bp_month if interest_bp_month is not None else get_threshold(conn, "default_card_interest_bp", DEFAULT_CARD_INTEREST_BP)


def bill_status(owed: int, minimum_left: int, rate_bp: int, due: str | None = None) -> str:
    """One wording everywhere for where a card bill stands. Once the minimum is paid there is no late fee and nothing is
    "due" any more: the rest simply moves to the next statement with interest (the owner's rule, 30 Oct 2026)."""
    if owed <= 0:
        return "LUNAS"
    if minimum_left <= 0:
        return (f"minimum sudah terpenuhi: tidak telat, tidak ada denda. Sisa {format_idr(owed)} dibawa ke tagihan berikutnya "
                f"dan berbunga ±{format_idr(bp_of_idr(owed, rate_bp))}/bulan")
    return (f"minimum belum terpenuhi: kurang {format_idr(minimum_left)}" + (f" sebelum {due}" if due else "")
            + f" agar tidak telat; sisa tagihan {format_idr(owed)}")


def record_card_payment(conn, today: date, card_alias: str, amount: int, again: bool = False) -> str:
    """The owner paid `amount` towards the card's latest statement (full or partial). A partial payment leaves
    the rest to be planned (and to accrue interest); a full one closes the statement. Each payment is kept with its date:
    a payday's plan counts only those made before the payday, so paying from the salary never shrinks that plan.
    The same amount on the same bill on the same day is refused unless `again` (a repeated call is the usual cause)."""
    check_idr(amount)
    if amount <= 0:
        raise ValueError("amount harus > 0")
    s = conn.execute("SELECT s.id, s.total_due, s.minimum_due, s.paid_amount, s.due_date, c.interest_bp_month FROM statements s"
                     " JOIN cards c ON c.id = s.card_id WHERE c.alias=? AND s.paid_at IS NULL"
                     " ORDER BY s.statement_date DESC, s.id DESC LIMIT 1", (card_alias,)).fetchone()
    if s is None:
        raise ValueError(f"tidak ada tagihan {card_alias} yang belum dibayar")
    if not again and conn.execute("SELECT 1 FROM card_payments WHERE statement_id=? AND amount=? AND paid_on=?",
                                  (s["id"], amount, today.isoformat())).fetchone():
        raise ValueError(f"pembayaran {card_alias} {format_idr(amount)} hari ini sudah tercatat; jangan dicatat dua kali. "
                         "Hanya bila pemilik memang membayar dua kali dengan jumlah yang sama, panggil lagi dengan ulang=true")
    paid = s["paid_amount"] + amount
    closed = paid >= s["total_due"]
    conn.execute("INSERT INTO card_payments(statement_id, paid_on, amount, created_at) VALUES (?,?,?,?)",
                 (s["id"], today.isoformat(), amount, datetime.now(WIB).isoformat(timespec="seconds")))
    conn.execute("UPDATE statements SET paid_amount=?, paid_at=? WHERE id=?",
                 (paid, today.isoformat() if closed else None, s["id"]))
    conn.commit()
    over = f" (kelebihan {format_idr(paid - s['total_due'])}: cek apakah ada salah ketik)" if paid > s["total_due"] else ""
    if closed:
        return f"{card_alias}: LUNAS{over}."
    return (f"{card_alias}: dibayar {format_idr(paid)} dari {format_idr(s['total_due'])} (minimum {format_idr(s['minimum_due'])}); "
            + bill_status(s["total_due"] - paid, s["minimum_due"] - paid, card_rate(conn, s["interest_bp_month"]), s["due_date"]) + ".")


def data_overview(conn, today: date) -> str:
    """Everything the ledger holds about cards, debts and commitments, as aliases, last 4 digits and amounts. The bot
    reads this before asking the owner anything, so it never asks for what is already recorded or invents a duplicate."""
    from . import card_installments, subscriptions
    L = ["KARTU (alias | bank | 4 digit | limit | cara bayar | tujuan bayar | tagihan terbaru: cetak, jatuh tempo, total, dibayar, status)"]
    for c in conn.execute("SELECT * FROM cards ORDER BY alias"):
        s = conn.execute("SELECT * FROM statements WHERE card_id=? ORDER BY statement_date DESC, id DESC LIMIT 1", (c["id"],)).fetchone()
        bill = (f"{s['statement_date']}, {s['due_date']}, {format_idr(s['total_due'])}, dibayar {format_idr(s['paid_amount'])}, "
                + bill_status(s["total_due"] - s["paid_amount"], s["minimum_due"] - s["paid_amount"],
                              card_rate(conn, c["interest_bp_month"]), s["due_date"])) if s else "belum ada tagihan"
        L.append(f"- {c['alias']} | {c['bank']} | {c['last4']} | {format_idr(c['credit_limit'])} | "
                 f"{'menu aplikasi' if c['pay_method'] == 'app_menu' else 'transfer'} | {c['pay_to_alias'] or 'belum terhubung'} | {bill}")
    L.append("UTANG / CICILAN BIASA (alias | pemberi | per bulan | sisa angsuran | cara bayar | rekening debet | angsuran yang sudah "
             "tercatat dibayar, jatuh tempo 40 hari terakhir dan sesudahnya)")
    recent = (today - timedelta(days=40)).isoformat()
    for d in conn.execute("SELECT * FROM debts ORDER BY alias"):
        done = "; ".join(f"jatuh tempo {p['due_date']} dibayar {'manual' if p['how'] == 'manual' else 'lewat autodebet'} {p['paid_on']}"
                         for p in conn.execute("SELECT * FROM debt_payments WHERE debt_alias=? AND due_date >= ? ORDER BY due_date",
                                               (d["alias"], recent)))
        L.append(f"- {d['alias']} | {d['lender']} | {format_idr(d['installment'])} | {d['tenor_left']} | {d['pay_method']} | "
                 f"{d['debit_account_alias'] or d['pay_to_alias'] or '-'} | {done or 'belum ada'}")
    L.append("DANA TERIKAT (pot)")
    for f in conn.execute("SELECT * FROM sinking_funds ORDER BY alias"):
        L.append(f"- {f['alias']} | target {format_idr(f['target'])} | jatuh tempo {f['due_date']} | terkumpul {format_idr(sinking_saved(conn, f))} | "
                 f"pola {'kartu dulu, pot dari sisa' if f['pace'] == 'sisa' else 'setoran tetap (rata)'}"
                 + (" | gaji di hari tenggat ikut dihitung" if f["due_payday"] else ""))
    e = emergency_status(conn)
    dest = conn.execute("SELECT bank, last4 FROM payee_secrets WHERE alias=?", (EMERGENCY_PAYEE,)).fetchone()
    where = (f"; disetor ke {EMERGENCY_PAYEE} ({dest['bank']} {dest['last4']})" if dest
             else f"; nomor tujuan belum didaftarkan (/rekening {EMERGENCY_PAYEE} <bank> <nomor>)")
    L.append("DANA DARURAT: " + (f"{format_idr(e['saved'])} dari {format_idr(e['target'])}, {format_idr(e['monthly'])} per gajian{where}" if e else "belum diatur"))
    daily = conn.execute("SELECT bank, last4 FROM payee_secrets WHERE alias=?", (LIVING_PAYEE,)).fetchone()
    L.append("REKENING UANG HARIAN: " + (f"{LIVING_PAYEE} ({daily['bank']} {daily['last4']}); uang harian tiap gajian ditransfer ke sini dan belanja harian "
                                          "hanya dari rekening ini" if daily else f"belum didaftarkan (/rekening {LIVING_PAYEE} <bank> <nomor>)"))
    L.append("PENGELUARAN TETAP")
    for e in conn.execute("SELECT alias, amount, due_day FROM fixed_expenses ORDER BY alias"):
        L.append(f"- {e['alias']} | {format_idr(e['amount'])} | tanggal {e['due_day']}")
    L.append("REKENING MILIK PEMILIK (alias | bank | jenis | 4 digit | saldo minimum yang ditahan bank | saldo terakhir yang "
             "dilaporkan pemilik)")
    for a in conn.execute("SELECT alias, bank, kind, last4 FROM accounts ORDER BY alias"):
        held = get_threshold(conn, f"saldo_ditahan:{a['alias']}", 0) or 0
        rep = latest_balance(conn, a["alias"])
        L.append(f"- {a['alias']} | {a['bank']} | {a['kind']} | {a['last4'] or '-'} | {format_idr(held) if held else '-'} | "
                 + (_reported(rep) if rep else "-"))
    L.append(f"CICILAN KARTU AKTIF: {format_idr(card_installments.monthly_total(conn))} per bulan | "
             f"LANGGANAN AKTIF: {format_idr(subscriptions.active_total(conn))} per bulan")
    th = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM thresholds")}
    L.append(f"GAJI: {format_idr(th['net_salary']) if 'net_salary' in th else 'belum diset'} | UANG HARIAN SEBULAN (living_reserve, "
             f"dilindungi): {format_idr(th['living_reserve']) if 'living_reserve' in th else 'belum diset'}")
    if "living_leftover" in th and "living_leftover_payday" in th:
        L.append(f"SISA UANG HARIAN TERCATAT: {format_idr(th['living_leftover'])} untuk gajian {_ymd(th['living_leftover_payday'])}"
                 + (f" (dicatat {_ymd(th['living_leftover_at'])})" if th.get("living_leftover_at") else "")
                 + (f"; belanja tunai sejak gajian sebelum laporan itu {format_idr(th['living_leftover_spent'])} sudah keluar "
                    "dari sisa ini (tidak dihitung lagi di uang harian)" if th.get("living_leftover_spent") else ""))
    pace = spending_pace(conn, today)
    if pace:        # the figure the owner asks for ("sisa uang harian berapa"): from the code, never worked out in chat
        rd = pace["reading"]
        L.append(f"UANG HARIAN BULAN INI (sampai gajian {pace['next_payday']}): terpakai {format_idr(pace['spent'])} dari "
                 f"{format_idr(pace['allowance'])} ({pace['pct_used']}%), "
                 + (f"sisa {format_idr(pace['remaining'])}" if pace["remaining"] >= 0 else f"lewat {format_idr(-pace['remaining'])}")
                 + (f"; mengikuti saldo {rd['alias']} {format_idr(rd['balance'])} yang dilaporkan {rd['as_of']} pukul {rd['at']} WIB"
                    + (f", selisih dengan catatan {'+' if pace['correction'] > 0 else '-'}{format_idr(abs(pace['correction']))}"
                       if pace["correction"] else "") if rd else "")
                 + ". Jangan dibagi per hari (uang harian juga membayar listrik, telepon, air)")
    L.append("ANGGARAN: " + ("; ".join(f"{k[7:]} {format_idr(v)}" for k, v in sorted(th.items()) if k.startswith("budget:")) or "belum ada"))
    return "\n".join(L)


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


def _ymd(n: int) -> str:
    """20261028 -> '2026-10-28' (dates kept in `thresholds` as YYYYMMDD integers)."""
    s = str(n)
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def living_leftover(conn, payday: date) -> tuple[int, int | None] | None:
    """Last cycle's living money the owner still held at this payday, as he reported it: (amount, YYYYMMDD recorded).
    The owner's own figure is stored, never a top-up derived from it, so a later change of living_reserve cannot skew it
    (regression 2026-10-28: a stored top-up made the plan ask him to move money he never had)."""
    amount, for_payday = get_threshold(conn, "living_leftover"), get_threshold(conn, "living_leftover_payday")
    if amount is None or for_payday != int(payday.strftime("%Y%m%d")):
        return None
    return amount, get_threshold(conn, "living_leftover_at")


def reserve_for(conn, payday: date) -> tuple[int | None, str]:
    """The living money this payday's plan takes from the salary: living_reserve, less last cycle's leftover when the
    owner reported one for this payday. Both are read now, so the split always adds up to the current living_reserve."""
    normal = get_threshold(conn, "living_reserve")
    left = living_leftover(conn, payday)
    if normal and left and left[0] > 0:
        held = min(left[0], normal)
        when = f" (dicatat {_ymd(left[1])})" if left[1] else ""
        return normal - held, (f"sementara: pemilik masih memegang sisa uang harian {format_idr(held)}{when}, jadi dari gaji ini "
                               f"diambil {format_idr(normal - held)}; total uang harian tetap {format_idr(normal)}; hanya untuk "
                               f"gajian {payday.isoformat()}")
    return normal, "diset pemilik"


def set_leftover_living_cash(conn, amount: int, today: date, other: int = 0) -> str:
    """On payday the owner still holds `amount` (+ `other`, a second account) of last cycle's living money, counted
    BEFORE the salary came in. This payday's plan then takes only the top-up to living_reserve from the salary; the next
    payday is planned normally again. More than a month of living money is refused: it almost always means the salary
    was counted in, and taking it as leftover would leave the owner short all month."""
    check_idr(amount)
    check_idr(other)
    normal = get_threshold(conn, "living_reserve")
    if not normal:
        raise ValueError("living_reserve belum diset")
    if amount < 0 or other < 0:
        raise ValueError("jumlah harus >= 0")
    total = amount + other
    if total > normal:
        raise ValueError(f"sisa {format_idr(total)} lebih besar dari uang harian sebulan {format_idr(normal)}. Bila gaji sudah masuk, "
                         "minta saldo SEBELUM gaji masuk. Bila memang ada lebih, catat paling banyak "
                         f"{format_idr(normal)}; kelebihannya bukan uang harian")
    payday = current_payday(today)
    if conn.execute("SELECT 1 FROM plan_progress WHERE payday=? AND item=?", (payday.isoformat(), LIVING_PAYEE)).fetchone():
        # after the top-up the account holds leftover and salary together: a balance read now taken as the leftover would
        # count the top-up twice (2.8M + 7.0M instead of 7.5M); the current balance corrects the month instead
        raise ValueError(f"transfer uang harian gajian {payday.isoformat()} sudah tercatat selesai, jadi sisa sebelum gaji tidak "
                         f"diubah lagi. Untuk saldo rekening harian SEKARANG pakai saldo_rekening(rekening='{LIVING_ACCOUNT}', "
                         "saldo=...): uang harian bulan ini dikoreksi ke saldo itu")
    key = int(payday.strftime("%Y%m%d"))
    # Cash spent from the payday until the first reading on or after it is already out of the leftover: the spending pace
    # must not count it again. The bot does not ask twice, so a later figure for the same payday corrects that reading and
    # the count made then stands; counting again would take every purchase since the payday as already out of it.
    counted = (get_threshold(conn, "living_leftover_payday") == key and (get_threshold(conn, "living_leftover_at") or 0) >= key
               and get_threshold(conn, "living_leftover_spent") is not None)
    set_threshold(conn, "living_leftover", total)
    set_threshold(conn, "living_leftover_payday", key)
    if not counted:
        set_threshold(conn, "living_leftover_at", int(today.strftime("%Y%m%d")))
        set_threshold(conn, "living_leftover_spent", cash_spent(conn, payday, today))
    conn.execute("DELETE FROM thresholds WHERE key IN ('living_reserve_override', 'living_reserve_override_until')")
    conn.commit()
    parts = f" ({format_idr(amount)} + {format_idr(other)})" if other else ""
    spent = get_threshold(conn, "living_leftover_spent") or 0
    report = f"laporan sisa pertama {_ymd(get_threshold(conn, 'living_leftover_at'))}" if counted else "laporan ini"
    return (f"Sisa uang harian {format_idr(total)}{parts} dicatat untuk gajian {payday.isoformat()}: uang harian yang diambil dari "
            f"gaji ini {format_idr(normal - total)}, jadi total uang harian tetap {format_idr(normal)}."
            + (f" Belanja tunai sejak gajian yang sudah tercatat sebelum {report} ({format_idr(spent)}) sudah keluar dari sisa "
               "ini, jadi tidak dihitung lagi di uang harian." if spent else ""))


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
    cards = sorted((b for b in card_bills(conn, payday) if b["owed"] > 0), key=lambda b: (-card_rate(conn, b["interest_bp_month"]), b["alias"]))
    carried, carried_cost = 0, 0
    for c in cards:
        paid = sum(t["amount"] for t in snap["transfers"] if t["to_alias"] == c["alias"])
        rate = card_rate(conn, c["interest_bp_month"])
        if paid >= c["owed"]:
            advice.append(f"{c['alias']}: LUNASI {format_idr(c['owed'])}. Tidak ada bunga.")
            continue
        how = ("hanya minimum" if paid <= c["minimum"] else "bayar sebagian")
        line = f"{c['alias']}: {how} {format_idr(paid)} dari {format_idr(c['owed'])} (minimum {format_idr(c['minimum'])})."
        extra = c["paid_since"] - paid
        if extra > 0:     # the owner paid more than planned, from money outside this plan: it covers the card, nothing else
            line += f" Sudah dibayar {format_idr(c['paid_since'])} sejak gajian, {format_idr(extra)} di luar rencana."
        rest = c["owed"] - max(paid, c["paid_since"])
        if rest <= 0:
            advice.append(line + " Lunas, tidak ada bunga.")
            continue
        cost = bp_of_idr(rest, rate)
        carried += rest
        carried_cost += cost
        advice.append(line + f" Sisa {format_idr(rest)} berbunga sekitar {format_idr(cost)} bulan depan ({rate / 100:.2f}%/bulan).")
    if carried:
        # Cutting the living money to pay a card faster is never offered: the owner's rule (the living money is protected)
        for f in conn.execute("SELECT * FROM sinking_funds").fetchall():
            planned = sum(t["amount"] for t in snap["transfers"] if t["to_alias"] == f["alias"])
            s = sinking_required(conn, f, payday, holidays, as_of=True)
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
    if keep_asof is None:       # a stated balance: deposits from today on add to it, so it is the balance of yesterday
        _fund_report(conn, "pot:" + alias, today - timedelta(days=1), saved_so_far)
    conn.commit()
    return (f"dana terikat {alias}: {format_idr(target)} jatuh tempo {due_date}, terkumpul awal "
            f"{format_idr(saved_so_far)} per {today.isoformat()}")


def sinking_saved(conn, fund, payday: date | None = None) -> int:
    """Saved so far = stated amount + deposits seen on the pool account since then
    (credits categorized 'sinking:<alias>' in the uploaded mutations). With `payday`: as it stood before that payday, so a
    balance reported after depositing from that salary does not change that payday's plan."""
    base, since, until = fund["saved_so_far"], fund["saved_asof"], None
    if payday is not None:
        until = payday.isoformat()
        if since > until:       # the current figure was reported after the payday: take the last report made before it
            r = conn.execute("SELECT balance, reported_on FROM fund_reports WHERE fund=? AND reported_on < ?"
                             " ORDER BY reported_on DESC, id DESC LIMIT 1", ("pot:" + fund["alias"], until)).fetchone()
            if r is None:
                return base     # tracked only since after the payday
            base, since = r["balance"], (date.fromisoformat(r["reported_on"]) + timedelta(days=1)).isoformat()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM transactions WHERE source='mutation' AND amount > 0"
        " AND category=? AND txn_date >= ? AND (? IS NULL OR txn_date < ?)",
        (f"sinking:{fund['alias']}", since, until, until)).fetchone()
    return base + row[0]


def _fund_report(conn, fund: str, on: date, balance: int) -> None:
    conn.execute("INSERT INTO fund_reports(fund, reported_on, balance, created_at) VALUES (?,?,?,?)",
                 (fund, on.isoformat(), balance, datetime.now(WIB).isoformat(timespec="seconds")))


def sinking_paydays_left(payday: date, due: date, holidays, buffer_days: int = SINKING_BUFFER_DAYS) -> int:
    """Paydays from `payday` on which a contribution can still land before the due date (`buffer_days` before it;
    0 when the owner counts a salary that arrives on the due date itself)."""
    holidays = frozenset(holidays) | id_holidays(due.year) | id_holidays(due.year - 1)   # cover the whole horizon
    last, n, p = due - timedelta(days=buffer_days), 0, payday
    while p <= last:
        n += 1
        p = next_payday(p, holidays)
    return n


def _low_cycles(fund, payday: date) -> int:
    """Pay cycles from `payday` through the fund's low-phase month (0 when there is no low phase)."""
    if fund["low_amount"] is None or not fund["low_until"]:
        return 0
    y, m = int(fund["low_until"][:4]), int(fund["low_until"][5:7])
    return max(0, (y * 12 + m) - (payday.year * 12 + payday.month) + 1)


def pot_schedule(remaining: int, left: int, low_amount: int | None = None, low_cycles: int = 0) -> list[int]:
    """Deposits for each remaining payday. Even split by default (rounded up to Rp 1.000). With a low phase: `low_amount`
    for the first `low_cycles` paydays, then whatever is still missing spread evenly over the rest, so the TARGET is still
    met on the due date. A low phase can never swallow every payday: the last ones always carry the catch-up."""
    out, rem = [], max(0, remaining)
    low_on = low_amount is not None and 0 < low_cycles < left
    for i in range(left):
        left_i = left - i
        if rem <= 0:
            out.append(0)
            continue
        d = min(low_amount, rem) if low_on and i < low_cycles else _round_up(-(-rem // left_i))
        out.append(d)
        rem = max(0, rem - d)
    return out


def fund_buffer_days(fund) -> int:
    return 0 if fund["due_payday"] else SINKING_BUFFER_DAYS


def sinking_required(conn, fund, payday: date, holidays, as_of: bool = False) -> dict:
    """as_of: the pot as it stood before `payday` (that payday's plan); otherwise as it is now."""
    saved = sinking_saved(conn, fund, payday if as_of else None)
    remaining = max(0, fund["target"] - saved)
    left = sinking_paydays_left(payday, date.fromisoformat(fund["due_date"]), holidays, fund_buffer_days(fund))
    if fund["pace"] == "sisa":     # no set amount: on each payday the pot takes what is left after the card bills
        return {"saved": saved, "remaining": remaining, "paydays_left": left, "schedule": [], "per_month": 0,
                "low_cycles": 0, "later_per_month": None, "pace": "sisa"}
    low = _low_cycles(fund, payday)
    sched = pot_schedule(remaining, left, fund["low_amount"], low) if left else []
    low_on = fund["low_amount"] is not None and 0 < low < left
    return {"saved": saved, "remaining": remaining, "paydays_left": left, "schedule": sched,
            "per_month": sched[0] if sched and remaining else 0,
            "low_cycles": low if low_on else 0, "later_per_month": sched[low] if low_on and remaining else None, "pace": "rata"}


def set_pot_schedule(conn, alias: str, amount: int | None, until_month: str | None, today: date,
                     pace: str | None = None, due_payday: bool | None = None) -> str:
    """Owner's choice of how the pot is filled.
    pace='sisa': cards first, the pot takes what is left on each payday (no set amount).
    amount + until_month: a set deposit `amount` per payday until `until_month` (YYYY-MM), then the catch-up ('rata').
    Neither: back to an even split ('rata'). `due_payday` alone only changes whether a salary arriving on the due date counts."""
    fund = conn.execute("SELECT * FROM sinking_funds WHERE alias=?", (alias,)).fetchone()
    if fund is None:
        raise ValueError(f"dana terikat {alias} tidak ada")
    if pace not in (None, "rata", "sisa"):
        raise ValueError("pola: 'sisa' (kartu dulu, pot dari sisa) atau 'rata' (setoran tetap)")
    if due_payday is not None:
        conn.execute("UPDATE sinking_funds SET due_payday=? WHERE alias=?", (1 if due_payday else 0, alias))
        if pace is None and amount is None:
            conn.commit()
            return (f"{alias}: gaji yang masuk pada hari tenggat {'IKUT' if due_payday else 'TIDAK'} dihitung. "
                    + sinking_status(conn, today, alias))
    if pace == "sisa":
        if amount is not None:
            raise ValueError("pola sisa tidak memakai setoran_awal: pot mendapat sisa setelah kartu tiap gajian")
        conn.execute("UPDATE sinking_funds SET pace='sisa', low_amount=NULL, low_until=NULL WHERE alias=?", (alias,))
        conn.commit()
        return f"{alias}: pola KARTU DULU disimpan (tiap gajian kartu dilunasi dulu, pot mendapat sisanya). " + sinking_status(conn, today, alias)
    if amount is None:
        conn.execute("UPDATE sinking_funds SET pace='rata', low_amount=NULL, low_until=NULL WHERE alias=?", (alias,))
        conn.commit()
        return f"{alias}: jadwal kembali rata. " + sinking_status(conn, today, alias)
    check_idr(amount)
    if amount < 0 or not until_month or len(until_month) != 7 or until_month[4] != "-":
        raise ValueError("setoran_awal >= 0 dan sampai_bulan format YYYY-MM")
    hol = id_holidays(today.year) | id_holidays(today.year + 1) | id_holidays(today.year + 2)
    payday = current_payday(today, hol)
    probe = dict(fund)
    probe["pace"] = "rata"
    probe["low_amount"], probe["low_until"] = amount, until_month
    s = sinking_required(conn, probe, payday, hol)
    low = _low_cycles(probe, payday)
    if low <= 0:
        raise ValueError("sampai_bulan sudah lewat")
    if low >= s["paydays_left"]:
        raise ValueError("fase awal tidak boleh menutup semua gajian: sisakan bulan untuk mengejar target sebelum jatuh tempo")
    conn.execute("UPDATE sinking_funds SET pace='rata', low_amount=?, low_until=? WHERE alias=?", (amount, until_month, alias))
    conn.commit()
    return f"{alias}: jadwal disimpan. " + sinking_status(conn, today, alias)


def set_pot_balance(conn, alias: str, balance: int, today: date) -> str:
    """The owner read the pot's balance in the bank app: it is the truth from today on. Deposits categorized
    'sinking:<alias>' in mutations dated after today still add to it."""
    check_idr(balance)
    if balance < 0:
        raise ValueError("saldo harus >= 0")
    if conn.execute("SELECT 1 FROM sinking_funds WHERE alias=?", (alias,)).fetchone() is None:
        raise ValueError(f"dana terikat {alias} tidak ada")
    conn.execute("UPDATE sinking_funds SET saved_so_far=?, saved_asof=? WHERE alias=?",
                 (balance, (today + timedelta(days=1)).isoformat(), alias))
    _fund_report(conn, "pot:" + alias, today, balance)
    conn.commit()
    return f"{alias}: saldo pot dicatat {format_idr(balance)} per {today.isoformat()}. " + sinking_status(conn, today, alias)


# ---- emergency fund: a small buffer so a surprise lands here, not on a credit card ----------

EMERGENCY_PAYEE = "dana-darurat"     # payee alias of the emergency pocket's account number (sent by the owner with /rekening)
LIVING_PAYEE = "uang-harian"         # payee alias of the account the owner spends daily from (living money only)


def _payee(conn, alias: str) -> str | None:
    row = conn.execute("SELECT alias FROM payee_secrets WHERE alias=? AND kind IN ('account','va')", (alias,)).fetchone()
    return row["alias"] if row else None


def emergency_destination(conn) -> str | None:
    return _payee(conn, EMERGENCY_PAYEE)


def emergency_saved(conn, payday: date | None = None) -> int:
    """The emergency fund as the owner last reported it. With `payday`: as it stood before that payday (the last report made
    before it, or the earliest report when none is that old), so a deposit from that salary does not change its plan."""
    if payday is not None:
        r = (conn.execute("SELECT balance FROM fund_reports WHERE fund='darurat' AND reported_on < ?"
                          " ORDER BY reported_on DESC, id DESC LIMIT 1", (payday.isoformat(),)).fetchone()
             or conn.execute("SELECT balance FROM fund_reports WHERE fund='darurat' ORDER BY reported_on, id LIMIT 1").fetchone())
        if r is not None:
            return r["balance"]
    return get_threshold(conn, "emergency_saved", 0) or 0


def emergency_status(conn, payday: date | None = None) -> dict | None:
    target = get_threshold(conn, "emergency_target")
    if not target:
        return None
    saved = emergency_saved(conn, payday)
    monthly = get_threshold(conn, "emergency_monthly") or target
    return {"target": target, "monthly": monthly, "saved": saved, "next": max(0, min(monthly, target - saved))}


def set_emergency_balance(conn, balance: int, today: date | None = None) -> str:
    """Record the balance the owner read. Read on or after a payday, it is compared with the last report before that payday and
    that payday's planned deposit, so the reply says whether the deposit arrived (30 Oct 2026: 600.048 then 600.000, both after
    the deposit, made the bot ask for another 500.000)."""
    check_idr(balance)
    if balance < 0:
        raise ValueError("saldo harus >= 0")
    today = today or wib_today()
    payday = current_payday(today)
    before = None
    if today >= payday:
        before = conn.execute("SELECT balance FROM fund_reports WHERE fund='darurat' AND reported_on < ?"
                              " ORDER BY reported_on DESC, id DESC LIMIT 1", (payday.isoformat(),)).fetchone()
    set_threshold(conn, "emergency_saved", balance)
    _fund_report(conn, "darurat", today, balance)
    conn.commit()
    text = format_emergency(conn)
    plan = emergency_status(conn, payday)
    if before is None or plan is None or not plan["next"]:
        return text
    expected = before["balance"] + plan["next"]
    if balance >= expected:
        return (text + f" Dibanding sebelum gajian {payday} ({format_idr(before['balance'])}): setoran gajian ini "
                f"{format_idr(plan['next'])} sudah masuk.")
    return (text + f" Sebelum gajian {payday}: {format_idr(before['balance'])}; dengan setoran gajian ini {format_idr(plan['next'])} "
            f"mestinya {format_idr(expected)}; kurang {format_idr(expected - balance)} (belum disetor atau ada yang dipakai: "
            "tanyakan, jangan menyimpulkan).")


def format_emergency(conn) -> str:
    e = emergency_status(conn)
    if e is None:
        return "Dana darurat belum diatur (emergency_target dan emergency_monthly, setelah pemilik setuju)."
    head = f"Dana darurat: {format_idr(e['saved'])} dari {format_idr(e['target'])}"
    head += " (PENUH)." if e["saved"] >= e["target"] else f"; setoran berikutnya {format_idr(e['next'])} per gajian, sebelum pot dan pelunasan sisa kartu."
    return (head + " Hanya untuk kejadian tak terduga (sakit, servis mobil, kebutuhan sekolah mendadak), bukan untuk menutup belanja"
            " kartu. Setelah dipakai, laporkan saldo barunya; rencana gajian berikutnya mengisinya lagi.")


def sinking_status(conn, today: date, alias: str | None = None) -> str:
    funds = conn.execute("SELECT * FROM sinking_funds" + (" WHERE alias=?" if alias else ""),
                         (alias,) if alias else ()).fetchall()
    if not funds:
        return "Belum ada dana terikat."
    hol = id_holidays(today.year) | id_holidays(today.year + 1) | id_holidays(today.year + 2)
    out = []
    p = current_payday(today, hol)
    proj = None
    for f in funds:
        s = sinking_required(conn, f, p, hol)
        pct = min(100, s["saved"] * 100 // f["target"])
        line = (f"{f['alias']}: target {format_idr(f['target'])} jatuh tempo {f['due_date']}; terkumpul "
                f"{format_idr(s['saved'])} ({pct}%); kurang {format_idr(s['remaining'])}")
        if s["pace"] == "sisa" and s["remaining"]:
            if proj is None:
                from . import simulate   # local import: simulate -> tools
                proj = simulate.pot_projection(conn, today)
            pr = proj.get(f["alias"])
            line += (f"; pola KARTU DULU: tiap gajian kartu dilunasi dulu, pot mendapat sisanya ({s['paydays_left']} gajian tersisa"
                     + (", termasuk gaji di hari tenggat" if f["due_payday"] else "") + ")")
            if pr and pr["at_due"] is not None:
                line += (f"; perkiraan terkumpul {format_idr(pr['at_due'])} pada tenggat"
                         + (f", KURANG {format_idr(pr['gap'])}" if pr["gap"] > 0 else ", cukup"))
        elif s["low_cycles"] and s["later_per_month"] is not None:
            line += (f"; setoran fase awal {format_idr(s['per_month'])}/bulan sampai {f['low_until']} ({s['low_cycles']} gajian), "
                     f"lalu sekitar {format_idr(s['later_per_month'])}/bulan sampai jatuh tempo ({s['paydays_left']} gajian tersisa)")
        elif s["remaining"] and s["paydays_left"]:
            line += f"; setoran {format_idr(s['per_month'])}/bulan selama {s['paydays_left']} gajian"
        elif s["remaining"]:
            line += "; TIDAK ADA gajian tersisa sebelum jatuh tempo"
        out.append(line)
    return "\n".join(out)


# ---- the ledger as it stood before a payday --------------------------------------------------------------------------
# A payday's plan is made from the ledger as it stood BEFORE that payday. What the owner pays out of that salary (card bills,
# instalments paid ahead of time, deposits) is the plan being carried out: it shows as progress against the same plan, never
# as a new plan that spends the same, still whole, salary a second time (30 Oct 2026: once every bill was paid, the plan
# found Rp 20,7 juta "free" for the pot and the simulation said the pot would reach its target).

def card_bills(conn, payday: date) -> list[dict]:
    """Per card, the latest statement printed by `payday`: `owed` and `minimum` as they stood before the payday (payments
    made before it subtracted), and `paid_since` = paid towards it from the payday on."""
    p = payday.isoformat()
    rows = conn.execute(
        "SELECT c.alias, c.pay_method, c.pay_to_alias, c.interest_bp_month, s.id AS statement_id, s.statement_date, s.due_date,"
        " s.total_due, s.minimum_due, s.reconciled, s.paid_at,"
        " COALESCE((SELECT SUM(amount) FROM card_payments WHERE statement_id = s.id AND paid_on < ?), 0) AS paid_before,"
        " COALESCE((SELECT SUM(amount) FROM card_payments WHERE statement_id = s.id AND paid_on >= ?), 0) AS paid_since,"
        " (SELECT MAX(paid_on) FROM card_payments WHERE statement_id = s.id AND paid_on >= ?) AS last_paid"
        " FROM statements s JOIN cards c ON c.id = s.card_id"
        " WHERE s.id = (SELECT id FROM statements WHERE card_id = s.card_id AND statement_date <= ?"
        "               ORDER BY statement_date DESC, id DESC LIMIT 1) ORDER BY c.alias", (p, p, p, p)).fetchall()
    out = []
    for r in rows:
        b = dict(r)
        # a bill marked paid is closed even where no amounts were recorded (bills paid before v8 kept paid_amount 0)
        if r["paid_at"] and r["paid_at"][:10] < p:
            b["paid_before"], b["paid_since"], b["last_paid"] = r["total_due"], 0, None
        elif r["paid_at"]:
            b["paid_since"] = max(r["paid_since"], r["total_due"] - r["paid_before"])
            b["last_paid"] = r["last_paid"] or r["paid_at"][:10]
        b["owed"], b["minimum"] = b["total_due"] - b["paid_before"], max(0, b["minimum_due"] - b["paid_before"])
        out.append(b)
    return out


def debts_paid(conn) -> dict[str, dict[str, sqlite3.Row]]:
    """Instalments recorded as paid: debt alias -> {due date: the payment}."""
    out: dict[str, dict] = {}
    for r in conn.execute("SELECT * FROM debt_payments ORDER BY due_date"):
        out.setdefault(r["debt_alias"], {})[r["due_date"]] = r
    return out


def collect_obligations(conn, payday: date, nxt: date, holidays=()) -> list[Obligation]:
    """Everything the salary of `payday` has to cover, from the ledger as it stood before that payday."""
    obs: list[Obligation] = []
    e = emergency_status(conn, payday)
    if e and e["next"]:      # paid to the owner's own emergency pocket once its number is registered (/rekening dana-darurat ...)
        obs.append(Obligation("emergency", EMERGENCY_PAYEE, payday, e["next"], pay_to=emergency_destination(conn)))
    for f in conn.execute("SELECT * FROM sinking_funds"):
        s = sinking_required(conn, f, payday, holidays, as_of=True)
        if s["pace"] == "sisa":
            if s["remaining"] and s["paydays_left"]:
                obs.append(Obligation("pool_rest", f["alias"], payday, s["remaining"], from_account="main", pay_to=f["pool_pay_to"]))
        elif s["per_month"]:
            obs.append(Obligation("pool", f["alias"], payday, s["per_month"], from_account="main",
                                  pay_to=f["pool_pay_to"]))
    # cards: the latest statement of each card with what was still owed before the payday (overdue if due before it)
    for b in card_bills(conn, payday):
        if b["owed"] > 0:
            obs.append(Obligation("card", b["alias"], date.fromisoformat(b["due_date"]), b["owed"], min(b["minimum"], b["owed"]),
                                  late_cost_bp=card_rate(conn, b["interest_bp_month"]), method=b["pay_method"], pay_to=b["pay_to_alias"]))
    target = get_threshold(conn, "monthly_savings_target", 0)
    if target and target > 0:     # savings come after card balances: card interest (about 2-3% a month) beats any savings yield
        obs.append(Obligation("saving", "tabungan", payday, target))
    obs.extend(debt_obligations(conn, payday, nxt))
    for r in conn.execute("SELECT payee_alias, amount, due_day FROM fixed_expenses"):
        for d in due_dates_in_window(r["due_day"], payday, nxt):
            obs.append(Obligation("fixed", r["payee_alias"], d, r["amount"], pay_to=r["payee_alias"]))
    return obs


def debt_obligations(conn, start: date, end: date, as_of_start: bool = True) -> list[Obligation]:
    """Debt instalments due in [start, end); an auto-debited one names the debited account in `pay_to`.
    as_of_start (a payday's plan): as they stood before `start`: an instalment paid ahead of time before it is not due again,
    one paid on or after it still belongs to the plan (its progress shows in status_gajian). Otherwise: only the instalments
    not recorded as paid (what an account still has to cover)."""
    obs: list[Obligation] = []
    paid = debts_paid(conn)
    s = start.isoformat()
    for r in conn.execute("SELECT alias, installment, tenor_left, due_day, rate_bp, pay_method, pay_to_alias, debit_account_alias"
                          " FROM debts ORDER BY alias"):
        auto = r["pay_method"] == "autodebit"
        done = paid.get(r["alias"], {})
        left = r["tenor_left"] + (sum(1 for p in done.values() if p["paid_on"] >= s) if as_of_start else 0)
        for d in due_dates_in_window(r["due_day"], start, end):
            p = done.get(d.isoformat())
            if p is not None and (not as_of_start or p["paid_on"] < s):
                continue
            if left <= 0:
                break
            left -= 1
            # rate_bp is the ANNUAL rate; the delay cost estimate is per month
            obs.append(Obligation("debt", r["alias"], d, r["installment"],
                                  late_cost_bp=(r["rate_bp"] or 0) // 12,
                                  method="autodebit" if auto else "transfer",
                                  pay_to=r["debit_account_alias"] if auto else r["pay_to_alias"]))
    return obs


# ---- an account balance the owner read in the bank app, checked against the auto-debits that still have to go ----

def next_salary_after(today: date, holidays) -> date:
    """The next salary still to come (on a payday the salary has already arrived)."""
    p = last_working_day(today.year, today.month, holidays)
    return p if p > today else next_payday(p, holidays)


def autodebit_check(conn, alias: str, balance: int, as_of: date, holidays=None) -> dict:
    """Is `balance` (as shown in the bank app on `as_of`) enough for the auto-debits from `alias` due from `as_of` until the
    next salary, plus the minimum the bank holds back? A debit due on `as_of` itself may or may not have gone: both figures."""
    hol = frozenset(holidays) if holidays is not None else id_holidays(as_of.year)
    until = next_salary_after(as_of, hol)
    debits = sorted((o for o in debt_obligations(conn, as_of, until, as_of_start=False)     # instalments already paid: no debit
                     if o.method == "autodebit" and o.pay_to == alias), key=lambda o: o.due)
    held = get_threshold(conn, f"saldo_ditahan:{alias}", 0) or 0
    need = sum(o.amount for o in debits) + held
    due_today = sum(o.amount for o in debits if o.due == as_of)
    return {"alias": alias, "balance": balance, "held": held, "until": until, "debits": debits, "need": need,
            "need_if_debited": need - due_today, "due_today": due_today}


def format_autodebit_check(c: dict) -> str:
    def verdict(need: int) -> str:
        diff = c["balance"] - need
        return f"CUKUP (lebih {format_idr(diff)})" if diff >= 0 else f"KURANG {format_idr(-diff)}"
    held = f"; ditambah saldo minimum yang ditahan bank {format_idr(c['held'])}" if c["held"] else ""
    if not c["debits"]:
        out = f"Tidak ada autodebet dari {c['alias']} sampai gajian berikutnya ({c['until'].isoformat()})."
        if not c["held"]:
            return out
        # the free balance in the code's words: on 30 Oct the bot took the held part off itself
        free = c["balance"] - c["held"]
        return out + (f" Yang bisa dipakai {format_idr(free)}: saldo {format_idr(c['balance'])} dikurangi saldo minimum yang "
                      f"ditahan bank {format_idr(c['held'])}." if free >= 0 else
                      f" Saldo {format_idr(c['balance'])} di bawah saldo minimum yang ditahan bank {format_idr(c['held'])}: "
                      "tidak ada yang bisa dipakai.")
    head = (f"Autodebet dari {c['alias']} sampai gajian berikutnya ({c['until'].isoformat()}): "
            + "; ".join(f"{o.payee_alias} {format_idr(o.amount)} ({o.due.isoformat()})" for o in c["debits"]) + held)
    if c["due_today"]:
        return (head + f". Bila autodebet hari ini BELUM terpotong: butuh {format_idr(c['need'])}, saldo {verdict(c['need'])}. "
                f"Bila SUDAH terpotong: butuh {format_idr(c['need_if_debited'])}, saldo {verdict(c['need_if_debited'])}.")
    first = c["debits"][0].due.isoformat()
    return head + f". Butuh {format_idr(c['need'])} sebelum {first}: saldo {verdict(c['need'])}."


def latest_balance(conn, alias: str, since: date | None = None):
    return conn.execute("SELECT r.* FROM balance_reports r JOIN accounts a ON a.id = r.account_id WHERE a.alias=? AND r.as_of >= ?"
                        " ORDER BY r.as_of DESC, r.id DESC LIMIT 1", (alias, since.isoformat() if since else "")).fetchone()


def _reported(r) -> str:
    return f"{format_idr(r['balance'])}, dilaporkan {r['as_of']} pukul {r['at'][11:16]} WIB"


def _living_balance(conn, today: date, report_id: int) -> str:
    """A balance of the daily account becomes the month's anchor (health.living_anchor): the report, and the last
    transaction recorded at that moment, so what is recorded later is told apart from what the balance already shows."""
    row = conn.execute("SELECT snapshot_json FROM plans ORDER BY id DESC LIMIT 1").fetchone()
    snap = json.loads(row["snapshot_json"]) if row else None
    if snap is None or not snap["payday"] <= today.isoformat() < snap["next_payday"]:
        return "Belum ada rencana gajian yang berjalan, jadi uang harian belum dikoreksi dengan saldo ini."
    lt = snap.get("living_transfer") or {}
    if lt.get("amount") and not conn.execute("SELECT 1 FROM plan_progress WHERE payday=? AND item=?",
                                             (snap["payday"], lt["to_alias"])).fetchone():
        return (f"Transfer uang harian dari gaji {snap['payday']} ({format_idr(lt['amount'])}) belum tercatat selesai, jadi saldo ini "
                "belum dipakai untuk mengoreksi uang harian. Setelah transfer: transfer_selesai, lalu laporkan saldo lagi.")
    before = spending_pace(conn, today)          # what was counted just before this reading (an earlier one included)
    mark = conn.execute("SELECT COALESCE(MAX(id), 0) FROM transactions").fetchone()[0]
    set_threshold(conn, "living_balance_report", report_id)
    set_threshold(conn, "living_balance_mark", mark)
    pace = spending_pace(conn, today)
    diff = pace["remaining"] - before["remaining"]
    return (f"Uang harian sampai gajian {pace['next_payday']} sekarang mengikuti saldo ini: sisa {format_idr(pace['remaining'])} "
            f"(menurut catatan sebelum laporan ini {format_idr(before['remaining'])}; "
            + (f"selisih +{format_idr(diff)}: uang masuk yang tidak tercatat, mis. transfer yang lebih dari belanjanya" if diff > 0 else
               f"selisih -{format_idr(-diff)}: keluar dari rekening ini tanpa tercatat, dihitung sebagai terpakai; belanja yang "
               "teringat dicatat dengan tanggal sebenarnya (yang sebelum hari ini tidak terhitung dua kali)" if diff < 0
               else "sama") + ")."
            + (f" Belanja kartu sejak gajian {format_idr(pace['reading']['card'])} belum keluar dari rekening ini, jadi sudah "
               "dikurangkan." if pace["reading"]["card"] else "")
            + f" Terpakai {format_idr(pace['spent'])} dari {format_idr(pace['allowance'])} ({pace['pct_used']}%).")


def record_account_balance(conn, today: date, alias: str, balance: int) -> str:
    """Store a balance the owner read in the bank app (gross, as shown) and say whether the auto-debits still to come fit.
    A balance of the daily account also corrects the month's daily money (_living_balance)."""
    check_idr(balance)
    if balance < 0:
        raise ValueError("saldo tidak boleh negatif")
    acct = conn.execute("SELECT id FROM accounts WHERE alias=?", (alias,)).fetchone()
    if acct is None:
        raise ValueError(f"rekening {alias} belum terdaftar (lihat ringkasan_data)")
    cur = conn.execute("INSERT INTO balance_reports(account_id, as_of, at, balance) VALUES (?,?,?,?)",
                       (acct["id"], today.isoformat(), datetime.now(WIB).isoformat(timespec="minutes"), balance))
    conn.commit()
    out = f"Saldo {alias} {_reported(latest_balance(conn, alias))}. "
    check = autodebit_check(conn, alias, balance, today)
    if alias == LIVING_ACCOUNT:
        return out + _living_balance(conn, today, cur.lastrowid) + (" " + format_autodebit_check(check) if check["debits"] else "")
    out += format_autodebit_check(check)
    if current_payday(today) <= today:   # the payday days: a balance read before the salary transfers still holds their money
        todo = _open_transfers(conn, today)
        if todo is None:
            out += " Angka ini hanya benar bila semua transfer gajian sudah dilakukan; bila belum, laporkan lagi setelah transfer."
        elif todo:   # named and counted, so the bot does not take them off itself (salary money sits in more than one account)
            total, free = sum(v for _, v in todo), check["balance"] - check["need"]
            out += (" Transfer gajian yang belum tercatat selesai: " + "; ".join(f"{a} {format_idr(v)}" for a, v in todo) + ". "
                    + (f"Bila dibayar dari rekening ini, sesudahnya yang bisa dipakai {format_idr(free - total)}." if free >= total else
                       f"Bila dibayar dari rekening ini, saldonya KURANG {format_idr(total - free)} untuk itu.")
                    + " Laporkan saldo lagi setelah transfer.")
    return out


def _open_transfers(conn, today: date) -> list[tuple[str, int]] | None:
    """The current payday plan's transfers not recorded as done (auto-debits apart: autodebit_check counts them); None
    without a plan for the current payday."""
    row = conn.execute("SELECT snapshot_json FROM plans ORDER BY id DESC LIMIT 1").fetchone()
    snap = json.loads(row["snapshot_json"]) if row else None
    if snap is None or snap["payday"] != current_payday(today).isoformat():
        return None
    return [(it["to"], it["planned"] - it["done"]) for it in payday_progress(conn, snap)["items"]
            if it["method"] != "autodebit" and it["planned"] > it["done"]]


def plan_to_dict(plan: Plan) -> dict:
    def conv(o):
        return {k: (v.isoformat() if isinstance(v, date) else v) for k, v in o.items()}
    d = asdict(plan)
    d["payday"], d["next_payday"] = plan.payday.isoformat(), plan.next_payday.isoformat()
    d["transfers"] = [conv(t) for t in d["transfers"]]
    d["unfunded"] = [conv(u) for u in d["unfunded"]]
    d["warnings"] = list(plan.warnings)
    return d


def payday_plan(conn, payday: date, hol, salary: int | None = None) -> tuple[Plan, list[Obligation], str]:
    """The allocation of `payday`'s salary, from the ledger as it stood before that payday (deterministic, nothing stored)."""
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
    return plan, obs, reserve_source


def generate_payday_plan(conn, today: date, payday: date | None = None,
                         salary: int | None = None) -> dict:
    hol = id_holidays(today.year) | id_holidays(today.year + 1)
    if payday is None:
        payday = current_payday(today, hol)   # asked on the 1st: the salary that came on the last working day
    plan, obs, reserve_source = payday_plan(conn, payday, hol, salary)
    nxt = plan.next_payday
    snap = plan_to_dict(plan)
    snap["reserve_source"] = reserve_source
    snap["reminders"] = []
    for f in conn.execute("SELECT * FROM sinking_funds WHERE low_amount IS NOT NULL"):
        sr = sinking_required(conn, f, payday, hol, as_of=True)
        if sr["low_cycles"] and sr["later_per_month"] is not None:
            snap["reminders"].append(
                f"Pot {f['alias']}: setoran fase awal {format_idr(sr['per_month'])} sampai {f['low_until']}, lalu sekitar "
                f"{format_idr(sr['later_per_month'])} per bulan agar tetap {format_idr(f['target'])} pada {f['due_date']}.")
    # A card bill that falls due BEFORE this payday cannot wait for the salary: it must be paid from the balance
    # on hand. Shown first, because a late payment costs a fee and may hurt the credit record. Read as it is NOW: a bill paid
    # since is not urgent any more, and once its minimum is paid nothing is "due" (only interest on the rest).
    now = {b["alias"]: b for b in card_bills(conn, payday)}
    for o in sorted((o for o in obs if o.kind == "card" and o.due < payday), key=lambda o: o.due):
        b = now[o.payee_alias]
        owed, min_left = b["owed"] - b["paid_since"], b["minimum"] - b["paid_since"]
        if owed <= 0:
            continue
        if min_left <= 0:
            snap["reminders"].append(f"INFO: tagihan {o.payee_alias}: {bill_status(owed, 0, o.late_cost_bp)}.")
            continue
        gone = o.due < today
        snap["reminders"].append(
            f"{'SUDAH LEWAT' if gone else 'MENDESAK'}: tagihan {o.payee_alias} jatuh tempo {o.due.isoformat()}, "
            f"sebelum gajian {payday.isoformat()}. Bayar minimal {format_idr(min_left)} (penuh {format_idr(owed)}) "
            f"dari saldo yang ada sekarang"
            + (" agar tidak kena denda; sisanya bisa setelah gajian." if owed > min_left else "."))
    # auto-debits from one account add up: the account must hold all of them (plus what the bank holds back as a minimum
    # balance) before the FIRST one, and keep it until the last one has gone; one figure per account, computed here.
    # An instalment recorded as paid (by hand ahead of time, or the debit already went through) is not debited again.
    paid_debts = debts_paid(conn)
    by_account: dict[str, list] = {}
    paid_ahead: dict[str, list[str]] = {}
    for t in snap["transfers"]:
        if t.get("method") == "autodebit":
            p = paid_debts.get(t["to_alias"], {}).get(t.get("due") or "")
            if p is not None:
                paid_ahead.setdefault(t.get("pay_to") or "", []).append(
                    f"{t['to_alias']} {format_idr(t['amount'])} (jatuh tempo {t['due']}) sudah dibayar "
                    f"{'manual' if p['how'] == 'manual' else 'lewat autodebet'} {p['paid_on']}")
            else:
                by_account.setdefault(t.get("pay_to") or "", []).append(t)
    snap["autodebit_need"] = {}
    for acct in list(by_account) + [a for a in paid_ahead if a not in by_account]:
        items = sorted(by_account.get(acct, []), key=lambda t: t.get("due") or "")
        done = "; ".join(paid_ahead.get(acct, []))
        if not items:
            snap["reminders"].append(f"AUTODEBET dari rekening {acct or '(rekening belum diset)'}: tidak ada yang akan didebet sampai "
                                     f"gajian {nxt.isoformat()}; {done}. Tidak perlu menahan saldo untuk cicilan ini.")
            continue
        held = get_threshold(conn, f"saldo_ditahan:{acct}", 0) or 0 if acct else 0
        total = sum(t["amount"] for t in items) + held
        parts = "; ".join(f"{t['to_alias']} {format_idr(t['amount'])} ({t.get('due') or 'jatuh tempo'})" for t in items)
        first, last = items[0].get("due") or "jatuh tempo", items[-1].get("due") or "jatuh tempo"
        if acct:
            snap["autodebit_need"][acct] = {"total": total, "held": held, "first": first, "last": last}
        snap["reminders"].append(
            f"AUTODEBET dari rekening {acct or '(rekening belum diset)'}: {parts}"
            + (f"; ditambah saldo minimum yang ditahan bank {format_idr(held)}" if held else "")
            + f". Pastikan saldo minimal {format_idr(total)} sebelum {first}"
            + (f" dan jangan dipakai sampai {last}" if last != first or held else "") + "; tidak perlu transfer ke kreditur."
            + (f" Tidak dihitung karena sudah dibayar: {done}." if done else ""))
        rep = latest_balance(conn, acct, since=payday) if acct else None
        if rep:     # a balance the owner read since this payday, checked by code; older ones say nothing about this window
            snap["reminders"].append(
                f"SALDO {acct} yang dilaporkan pemilik: {_reported(rep)} (benar bila dibaca setelah transfer gajian). "
                + format_autodebit_check(autodebit_check(conn, acct, rep["balance"], date.fromisoformat(rep["as_of"]), hol)))
    for f in conn.execute("SELECT * FROM sinking_funds"):
        due = date.fromisoformat(f["due_date"])
        s = sinking_required(conn, f, payday, hol, as_of=True)
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
    sisa = conn.execute("SELECT * FROM sinking_funds WHERE pace='sisa'").fetchall()
    if sisa:
        from . import simulate   # local import: simulate -> tools
        proj = simulate.pot_projection(conn, today)
        for f in sisa:
            pr = proj.get(f["alias"])
            if not pr or pr["at_due"] is None or date.fromisoformat(f["due_date"]) < nxt:
                continue
            planned = sum(t["amount"] for t in snap["transfers"] if t["to_alias"] == f["alias"])
            snap["reminders"].append(
                f"Pot {f['alias']} (kartu dulu, pot dari sisa): setoran gajian ini {format_idr(planned)}; perkiraan terkumpul "
                f"{format_idr(pr['at_due'])} dari {format_idr(f['target'])} pada {f['due_date']}.")
            if pr["gap"] > 0:
                snap["warnings"].append(
                    f"{f['alias']}: dengan pola ini pot diperkirakan KURANG {format_idr(pr['gap'])} pada {f['due_date']}. Pilihan: kurangi "
                    "langganan/belanja, tambah pemasukan, "
                    # once the salary on the due date is counted, suggesting it again would offer nothing new
                    + ("" if f["due_payday"] else "hitung gaji di hari tenggat, ") + "atau bicarakan jadwal dengan penerima.")
    # the living money goes to the owner's daily account (all daily spending comes from there); kept outside `transfers`,
    # which hold the salary's obligations, so the cash kept and the spending pace still read the living money as before
    normal = get_threshold(conn, "living_reserve") or 0
    left = living_leftover(conn, payday)
    snap["living_normal"] = normal
    snap["living_leftover"] = min(left[0], normal) if left and normal else 0     # the owner's figure; checked by invariants
    daily = _payee(conn, LIVING_PAYEE)
    amount = min(snap["reserve"] or 0, max(0, snap["cash_to_hold"]))
    elsewhere = snap["living_leftover"]
    if daily and (amount or elsewhere):
        snap["living_transfer"] = {"to_alias": LIVING_PAYEE, "amount": amount, "pay_to": daily, "date": payday.isoformat(),
                                   "also_move": elsewhere}
        # moving the leftover must never empty an account an auto-debit still needs: the figure comes from the code
        keep = "; ".join(f"saldo {a} jangan sampai di bawah {format_idr(n['total'])} sampai {n['last']} (autodebet)"
                         for a, n in snap["autodebit_need"].items())
        snap["reminders"].append(
            (f"UANG HARIAN: transfer {format_idr(amount)} dari gaji ke rekening harian ({LIVING_PAYEE})" if amount else
             f"UANG HARIAN: tidak ada yang diambil dari gaji ({LIVING_PAYEE})")
            + (f"; pindahkan juga sisa uang harian {format_idr(elsewhere)} bila masih di rekening lain, supaya seluruh "
               f"{format_idr(normal)} ada di rekening harian" + (f", tetapi {keep}" if keep else "") if elsewhere else "")
            + ". Belanja harian hanya dari rekening itu.")
    snap["advice"] = card_advice(conn, snap, payday, hol)
    if reserve_source == "belum diset" and snap["advice"]:     # only matters when cards or savings are in play
        snap["warnings"].append("Cadangan hidup harian belum diset: set_threshold living_reserve (atau verifikasi kategori "
                                "transaksi agar bisa diestimasi). Tanpa itu, seluruh sisa gaji dianggap boleh dipakai melunasi kartu.")
    for r in conn.execute(
            "SELECT c.alias FROM statements s JOIN cards c ON c.id = s.card_id WHERE s.reconciled = 0"
            " AND s.paid_at IS NULL AND s.id = (SELECT id FROM statements WHERE card_id = s.card_id ORDER BY statement_date DESC, id DESC LIMIT 1)"):
        snap["warnings"].append(f"Statement {r['alias']} belum cocok saat rekonsiliasi; angka tagihan perlu diperiksa.")
    from . import audit     # local import: audit -> card_installments
    try:                    # the audit is auxiliary: it must never take the owner's payday list down
        found = audit.run(conn, today)
    except Exception as e:  # noqa: BLE001
        found = [("warn", f"pemeriksaan silang gagal ({type(e).__name__}); jalankan /periksa")]
    for level, text in found:
        if level in ("bad", "warn") and "tidak rekonsiliasi" not in text:
            snap["warnings"].append("Data: " + text)
    from . import invariants   # every plan checks its own arithmetic before anyone sees it
    bills: dict[str, int] = {}
    for o in obs:
        if o.kind != "pool_rest" and o.due < nxt:
            bills[o.payee_alias] = bills.get(o.payee_alias, 0) + o.amount
    invariants.require(invariants.plan_errors(snap, bills), "rencana gajian")
    body = json.dumps(snap)
    last = conn.execute("SELECT snapshot_json FROM plans WHERE payday=? ORDER BY id DESC LIMIT 1", (payday.isoformat(),)).fetchone()
    if last is None or last["snapshot_json"] != body:     # one row per change, not per question
        conn.execute("INSERT INTO plans(payday,snapshot_json,created_at) VALUES (?,?,?)",
                     (payday.isoformat(), body, datetime.now(timezone.utc).isoformat()))
        conn.commit()
    snap["progress"] = payday_progress(conn, snap)     # what has been done so far: shown with the plan, never stored
    return snap


def payday_progress(conn, snap: dict) -> dict:
    """What has been done of the plan in `snap`, read from the ledger, never from the chat. Cards: payments recorded since the
    payday towards the bills the plan covers; instalments: those recorded as paid; everything else (fixed costs, deposits,
    the living money): marked done by the owner (transfer_selesai). A card paid beyond its planned amount is listed apart:
    it covers what the plan could not fund and never makes room for anything else."""
    payday, nxt = snap["payday"], snap["next_payday"]
    bills = {b["alias"]: b for b in card_bills(conn, date.fromisoformat(payday))}
    debts = {r["alias"] for r in conn.execute("SELECT alias FROM debts")}
    paid_debts = debts_paid(conn)
    marks = {r["item"]: r for r in conn.execute("SELECT * FROM plan_progress WHERE payday=?", (payday,))}
    items: dict[str, dict] = {}

    def item(alias: str, kind: str, method: str | None, due: str | None) -> dict:
        it = items.setdefault(alias, {"to": alias, "kind": kind, "method": method or "transfer", "planned": 0, "done": 0,
                                      "on": None, "how": None, "due": due})
        if due and (it["due"] is None or due < it["due"]):
            it["due"] = due
        return it

    for t in snap["transfers"]:
        a = t["to_alias"]
        item(a, "kartu" if a in bills else "cicilan" if a in debts else "transfer", t.get("method"), t.get("due"))["planned"] += t["amount"]
    lt = snap.get("living_transfer")
    if lt and lt.get("amount"):
        item(lt["to_alias"], "uang harian", "transfer", lt.get("date"))["planned"] += lt["amount"]
    beyond: dict[str, int] = {}
    for a, it in items.items():
        if it["kind"] == "kartu":
            b = bills[a]
            it["done"], it["on"] = min(it["planned"], b["paid_since"]), b["last_paid"]
            if b["paid_since"] > it["planned"]:
                beyond[a] = b["paid_since"] - it["planned"]
        elif it["kind"] == "cicilan":
            got = [p for d, p in paid_debts.get(a, {}).items() if payday <= d < nxt]
            if got:
                it["done"] = min(it["planned"], sum(p["amount"] for p in got))
                it["on"], it["how"] = max(p["paid_on"] for p in got), got[-1]["how"]
        elif a in marks:
            it["done"], it["on"] = min(it["planned"], marks[a]["amount"]), marks[a]["done_on"]
    for a, b in bills.items():      # a card the plan did not pay at all, paid anyway
        if a not in items and b["paid_since"] > 0:
            beyond[a] = b["paid_since"]
    spare = dict(beyond)
    unfunded = []
    for u in snap["unfunded"]:
        cov = min(u["amount"], spare.get(u["to_alias"], 0))
        if cov:
            spare[u["to_alias"]] -= cov
        b = bills.get(u["to_alias"])
        left = u["amount"] - cov
        unfunded.append({"to": u["to_alias"], "amount": u["amount"], "covered": cov, "left": left, "reason": u["reason"],
                         "cost": bp_of_idr(left, card_rate(conn, b["interest_bp_month"])) if b else u["est_delay_cost"]})
    cards_now = {a: {"owed": b["owed"] - b["paid_since"], "min_left": max(0, b["minimum"] - b["paid_since"]),
                     "rate": card_rate(conn, b["interest_bp_month"]), "due": b["due_date"]} for a, b in bills.items()}
    return {"items": list(items.values()), "beyond": beyond, "extra": {a: v for a, v in spare.items() if v > 0},
            "unfunded": unfunded, "cards_now": cards_now}


CARD_REST = "tagihan kartu - sisa saldo (bayar penuh)"


def _unfunded(snap: dict) -> list[dict]:
    prog = snap.get("progress") or {}
    return prog.get("unfunded") or [{"to": u["to_alias"], "amount": u["amount"], "covered": 0, "left": u["amount"],
                                     "reason": u["reason"], "cost": u["est_delay_cost"]} for u in snap["unfunded"]]


def _carried(u: dict, unf: list[dict]) -> bool:
    """A card's rest whose minimum is met: no late fee, it goes to the next bill with interest."""
    return u["reason"] == CARD_REST and not any(
        x["to"] == u["to"] and x["reason"] == "tagihan kartu - minimum" and x["left"] > 0 for x in unf)


def _unfunded_lines(snap: dict) -> list[str]:
    unf = _unfunded(snap)
    out = []
    for u in unf:
        line = f"{u['to']}: {format_idr(u['amount'])} ({u['reason']})"
        if u["covered"]:
            line += f"; sudah dibayar di luar rencana {format_idr(u['covered'])}"
        if u["left"] <= 0:
            line += ": tertutup, tidak ada sisa"
        elif _carried(u, unf):
            line += (f": minimum terpenuhi (tidak telat, tidak ada denda); sisa {format_idr(u['left'])} dibawa ke tagihan "
                     f"berikutnya dan berbunga ±{format_idr(u['cost'])}/bulan")
        else:
            line += f"; belum ada dananya {format_idr(u['left'])}, estimasi biaya {format_idr(u['cost'])}"
        out.append(line)
    return out


def _unfunded_total(snap: dict) -> str | None:
    """The sum of two or more items, so the bot never adds them up: on 30 Oct it summed a carried card rest and one already
    paid outside the plan into one wrong "belum terdanai" figure."""
    unf = _unfunded(snap)
    if len(unf) < 2:
        return None
    short = sum(u["left"] for u in unf if u["left"] > 0 and not _carried(u, unf))
    carried = sum(u["left"] for u in unf if u["left"] > 0 and _carried(u, unf))
    closed = sum(1 for u in unf if u["left"] <= 0)
    parts = ([f"belum ada dananya {format_idr(short)}"] if short else []) \
        + ([f"dibawa ke tagihan berikutnya (minimum terpenuhi, berbunga) {format_idr(carried)}"] if carried else []) \
        + ([f"{closed} pos sudah tertutup"] if closed else [])
    return "JUMLAH (dihitung kode, jangan menjumlah sendiri): " + "; ".join(parts)


def _progress_name(it: dict) -> str:
    if it["kind"] == "cicilan":
        how = {"manual": "dibayar manual", "autodebit": "lewat autodebet"}.get(it["how"] or "", "dibayar")
        return f"{it['to']} {format_idr(it['done'])} ({how} {it['on']})" if it["on"] else f"{it['to']} {format_idr(it['planned'])}"
    return f"{it['to']} {format_idr(it['done'] or it['planned'])}" + (f" ({it['on']})" if it["on"] else "")


def summarize_plan(snap: dict) -> str:
    """Telegram-safe summary: aliases and amounts only, never full numbers, no URLs."""
    lines = [f"Rencana gajian {snap['payday']} (sampai {snap['next_payday']}), dari data SEBELUM gaji masuk: pembayaran "
             "sesudahnya tidak mengubah rencana ini, hanya progresnya (status_gajian)",
             f"Gaji: {format_idr(snap['salary'])}"]
    for t in snap["transfers"]:
        how = {"app_menu": " via menu aplikasi bank",
               "autodebit": f" autodebet, saldo harus cukup sebelum {t.get('due')}"}.get(t.get("method"), "")
        lines.append(f"- {t['date']} {t['to_alias']}: {format_idr(t['amount'])} ({t['reason']}){how}")
    lines += [f"! BELUM TERDANAI {x}" for x in _unfunded_lines(snap)]
    lines += [f"! {t}" for t in [_unfunded_total(snap)] if t]
    lines += [f"* {r}" for r in snap.get("reminders", [])]
    if snap.get("reserve"):
        lines.append(f"Cadangan hidup harian: {format_idr(snap['reserve'])} ({snap.get('reserve_source')})")
    lines += [f"> {a}" for a in snap.get("advice", [])]
    lt = snap.get("living_transfer")
    if lt and lt["amount"]:
        lines.append(f"- {lt['date']} {lt['to_alias']}: {format_idr(lt['amount'])} (uang harian ke rekening harian)")
    held = snap.get("living_leftover") or 0
    lines.append(f"Kas ditahan: {format_idr(snap['cash_to_hold'])}"
                 + (f"; uang harian bulan ini {format_idr(living_money(snap))} = {format_idr(snap['cash_to_hold'])} dari gaji + "
                    f"sisa {format_idr(held)} yang sudah dipegang" if held else ""))
    prog = snap.get("progress") or {}
    items = prog.get("items") or []
    if any(it["done"] for it in items) or prog.get("beyond"):
        done = [it for it in items if it["done"] >= it["planned"]]
        todo = [it for it in items if it["done"] < it["planned"]]
        lines.append("PROGRES (dari ledger): sudah " + ("; ".join(_progress_name(it) for it in done) or "-")
                     + " | belum " + ("; ".join(f"{it['to']} {format_idr(it['planned'] - it['done'])}" for it in todo) or "-")
                     + ("" if not prog.get("beyond") else " | di luar rencana "
                        + "; ".join(f"{a} {format_idr(v)}" for a, v in sorted(prog["beyond"].items()))))
    lines += [f"Peringatan: {w}" for w in snap["warnings"]]
    return "\n".join(lines)


# ---- carrying out the plan: what the owner reports as done (never asked twice) -----------------------------------------

def record_debt_payment(conn, today: date, alias: str, amount: int, how: str = "manual", due: str | None = None) -> str:
    """cicilan_dibayar: an instalment was paid (by hand, often ahead of the auto-debit, or the auto-debit went through). It is
    recorded against one due date, so no plan asks for it again and the auto-debit check stops counting it; the debt's
    remaining instalments and balance go down by one instalment."""
    check_idr(amount)
    how, due = how or "manual", due or None          # a model sends unused fields empty
    if how not in ("manual", "autodebit"):
        raise ValueError("cara: 'manual' (pemilik membayar sendiri) atau 'autodebit' (sudah dipotong bank)")
    d = conn.execute("SELECT * FROM debts WHERE alias=?", (alias,)).fetchone()
    if d is None:
        raise ValueError(f"utang {alias} tidak ada (lihat ringkasan_data)")
    if amount != d["installment"]:
        raise ValueError(f"jumlah {format_idr(amount)} tidak sama dengan angsuran {alias} {format_idr(d['installment'])}; "
                         "pelunasan sebagian atau dipercepat diubah dengan upsert_debt, setelah pemilik setuju")
    if d["tenor_left"] <= 0:
        raise ValueError(f"{alias} sudah tidak punya sisa angsuran")
    paid = {r["due_date"] for r in conn.execute("SELECT due_date FROM debt_payments WHERE debt_alias=?", (alias,))}
    if due is not None:
        when = date.fromisoformat(due)
        if when != _day_in_month(when.year, when.month, d["due_day"]):
            raise ValueError(f"{alias} jatuh tempo tiap tanggal {d['due_day']}, bukan {due}")
    else:
        # by hand: the first instalment not yet recorded (an auto-debited loan: from today on, the bank took the earlier ones;
        # paid on the due day itself, it is that day's); an auto-debit that went through: the latest one due by today (up to
        # 25 days back)
        start = today if how == "manual" and d["pay_method"] == "autodebit" else today - timedelta(days=25)
        y, m, when = start.year, start.month, None
        for _ in range(d["tenor_left"] + 3):
            c = _day_in_month(y, m, d["due_day"])
            if how == "autodebit" and c > today:
                break
            if c >= start and c.isoformat() not in paid:
                when = c
                if how == "manual":
                    break
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
        if when is None:
            raise ValueError(f"tidak ketemu angsuran {alias} yang cocok; sebutkan jatuh_tempo (YYYY-MM-DD)")
    if when.isoformat() in paid:
        raise ValueError(f"angsuran {alias} jatuh tempo {when.isoformat()} sudah tercatat dibayar; jangan dicatat dua kali")
    conn.execute("INSERT INTO debt_payments(debt_alias, due_date, amount, paid_on, how, created_at) VALUES (?,?,?,?,?,?)",
                 (alias, when.isoformat(), amount, today.isoformat(), how, datetime.now(WIB).isoformat(timespec="seconds")))
    conn.execute("UPDATE debts SET tenor_left = tenor_left - 1, outstanding = MAX(0, outstanding - ?) WHERE alias=?", (amount, alias))
    conn.commit()
    r = conn.execute("SELECT tenor_left, outstanding FROM debts WHERE alias=?", (alias,)).fetchone()
    note = (" Autodebet untuk jatuh tempo itu tidak dihitung lagi; pastikan ke pemilik bahwa bank tidak akan memotong dua kali."
            if how == "manual" and d["pay_method"] == "autodebit" else "")
    return (f"{alias}: angsuran jatuh tempo {when.isoformat()} ({format_idr(amount)}) tercatat dibayar "
            f"{'manual' if how == 'manual' else 'lewat autodebet'} {today.isoformat()}. Sisa {r['tenor_left']} angsuran, "
            f"sisa utang {format_idr(r['outstanding'])}.{note}")


def mark_transfers_done(conn, today: date, items: list[str] | None = None, all_open: bool = False, undo: bool = False) -> str:
    """transfer_selesai: the owner made (or, with undo, did not make) transfers of the current payday's plan that are not card
    bills or instalments: fixed costs, deposits, the living money. Recorded per destination, so nobody asks again."""
    snap = generate_payday_plan(conn, today)
    payday = snap["payday"]
    prog = snap["progress"]
    own = {it["to"]: it for it in prog["items"] if it["kind"] in ("transfer", "uang harian")}
    names = {r["alias"]: r["payee_alias"] for r in conn.execute("SELECT alias, payee_alias FROM fixed_expenses")}
    if all_open == bool(items):
        raise ValueError("isi tujuan (alias dari status_gajian) ATAU semua=true, salah satu")
    if all_open:
        chosen = [a for a, it in own.items() if (it["done"] > 0 if undo else it["done"] < it["planned"])]
    else:
        chosen = []
        for x in items or []:
            a = names.get(x, x)
            if a not in own:
                other = next((it for it in prog["items"] if it["to"] == a), None)
                hint = {"kartu": " Kartu dicatat dengan record_card_payment (jumlahnya).",
                        "cicilan": " Cicilan dicatat dengan cicilan_dibayar."}.get(other["kind"], "") if other else ""
                raise ValueError(f"{x} bukan transfer rencana gajian {payday} yang ditandai dengan alat ini.{hint} "
                                 f"Pilihan: {', '.join(sorted(own)) or '-'}")
            chosen.append(a)
    stamp = datetime.now(WIB).isoformat(timespec="seconds")
    for a in chosen:
        if undo:
            conn.execute("DELETE FROM plan_progress WHERE payday=? AND item=?", (payday, a))
        else:
            conn.execute("INSERT INTO plan_progress(payday, item, amount, done_on, created_at) VALUES (?,?,?,?,?)"
                         " ON CONFLICT(payday, item) DO UPDATE SET amount=excluded.amount, done_on=excluded.done_on",
                         (payday, a, own[a]["planned"], today.isoformat(), stamp))
    conn.commit()
    if not chosen:
        return "Tidak ada yang diubah: " + ("tidak ada tanda selesai." if undo else "semua transfer itu sudah tercatat selesai.")
    left = [a for a, it in own.items() if a not in chosen and it["done"] < it["planned"]] if not undo else []
    return (("Tanda selesai dihapus: " if undo else f"Tercatat selesai (gajian {payday}): ")
            + "; ".join(f"{a} {format_idr(own[a]['planned'])}" for a in chosen) + "."
            + (f" Transfer lain yang belum ditandai: {', '.join(left)}." if left else ""))


def _kind_text(it: dict) -> str:
    if it["kind"] == "kartu":
        return "kartu" + (", menu aplikasi" if it["method"] == "app_menu" else "")
    if it["kind"] == "cicilan":
        return "cicilan" + (f", autodebet {it['due']}" if it["method"] == "autodebit" else f", jatuh tempo {it['due']}")
    return it["kind"] + (f", jatuh tempo {it['due']}" if it["kind"] == "transfer" and it["due"] else "")


def payday_status(conn, today: date) -> str:
    """status_gajian: the current payday's plan against what the ledger says was done, and what the owner already said."""
    snap = generate_payday_plan(conn, today)
    prog = snap["progress"]
    payday = snap["payday"]
    L = [f"STATUS GAJIAN {payday} (sampai {snap['next_payday']}), dari ledger. Rencananya tetap (dihitung dari data sebelum gaji "
         "masuk); yang berubah hanya progresnya."]
    items = prog["items"]
    done = [it for it in items if it["done"] >= it["planned"]]
    part = [it for it in items if 0 < it["done"] < it["planned"]]
    todo = [it for it in items if not it["done"]]
    L.append("SUDAH:" + ("" if done else " belum ada"))
    L += [f"✅ {_progress_name(it)} [{_kind_text(it)}]" for it in done]
    L += [f"◐ {it['to']} {format_idr(it['done'])} dari {format_idr(it['planned'])}; kurang {format_idr(it['planned'] - it['done'])} "
          f"[{_kind_text(it)}]" for it in part]
    L.append("BELUM MENURUT LEDGER:" + ("" if todo else " tidak ada"))
    for it in todo:
        if it["kind"] == "kartu":
            nxt_step = "setelah dibayar: record_card_payment"
        elif it["kind"] == "cicilan" and it["method"] == "autodebit":
            nxt_step = "dipotong bank otomatis; bila pemilik sudah membayar sendiri atau sudah terpotong: cicilan_dibayar"
        elif it["kind"] == "cicilan":
            nxt_step = "setelah ditransfer: cicilan_dibayar"
        else:
            nxt_step = "setelah ditransfer: transfer_selesai"
        L.append(f"⏳ {it['to']} {format_idr(it['planned'])} [{_kind_text(it)}] ({nxt_step})")
    if prog["beyond"]:
        L.append("DIBAYAR DI LUAR RENCANA (uang di luar gaji ini; tidak menambah ruang untuk pos lain):")
        L += [f"+ {a} {format_idr(v)}" for a, v in sorted(prog["beyond"].items())]
    unf = _unfunded_lines(snap)
    if unf:
        L.append("BELUM TERDANAI DARI GAJI INI:")
        L += [f"- {x}" for x in unf]
        L += [t for t in [_unfunded_total(snap)] if t]
    now = prog["cards_now"]
    L.append("STATUS KARTU SEKARANG (kalimat ini yang dipakai; minimum terpenuhi = tidak ada jatuh tempo lagi):")
    paid_off = sorted(a for a, c in now.items() if c["owed"] <= 0)
    for a, c in sorted(now.items()):
        if c["owed"] > 0:
            L.append(f"- {a}: {bill_status(c['owed'], c['min_left'], c['rate'], c['due'])}")
    if paid_off:
        L.append("- LUNAS: " + ", ".join(paid_off))
    L += [f"* {r}" for r in snap["reminders"] if r.startswith(("AUTODEBET", "SALDO", "INFO", "SUDAH LEWAT", "MENDESAK"))]
    known = []
    left = living_leftover(conn, date.fromisoformat(payday))
    if left:
        known.append(f"sisa uang harian sebelum gaji {format_idr(left[0])}" + (f" (dicatat {_ymd(left[1])})" if left[1] else ""))
    for r in conn.execute("SELECT a.alias, r.* FROM balance_reports r JOIN accounts a ON a.id = r.account_id WHERE r.as_of >= ?"
                          " AND r.id = (SELECT MAX(id) FROM balance_reports WHERE account_id = r.account_id) ORDER BY a.alias", (payday,)):
        known.append(f"saldo {r['alias']} {_reported(r)}")
    for r in conn.execute("SELECT * FROM fund_reports f WHERE reported_on >= ? AND id = (SELECT id FROM fund_reports WHERE fund = f.fund"
                          " ORDER BY reported_on DESC, id DESC LIMIT 1) ORDER BY fund", (payday,)):    # latest by date: one can be backdated
        what = "dana darurat" if r["fund"] == "darurat" else "pot " + r["fund"][4:]
        known.append(f"saldo {what} {format_idr(r['balance'])} (dilaporkan {r['reported_on']})")
    L.append("SUDAH TERCATAT, JANGAN DITANYAKAN ULANG: " + ("; ".join(known) if known else "-"))
    return "\n".join(L)
