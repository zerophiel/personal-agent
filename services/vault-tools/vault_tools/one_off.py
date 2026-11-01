"""One-off bills (usulan #6, 31 Oct 2026): a bill paid once, outside the subscriptions and the fixed costs, such as two months
of arrears. One recorded before a payday is in that payday's plan when it falls due before the next payday, and stays there
as done once paid. One recorded on or after the payday leaves the running plan as it is (its money may already be spent): it
is paid from the balance on hand, or, still open at the next payday, planned there first. A bill already paid by the time the
owner mentions it is an expense (record_expense, category sekali:<name>), not a bill."""
from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timedelta, timezone

from . import changelog
from .money import check_idr, format_idr
from .payday import next_payday, window_payday

WIB = timezone(timedelta(hours=7))
NAME_MAX, NOTE_MAX = 80, 300
_LONG_DIGITS = re.compile(r"\d{9,}")      # an account or VA number typed into a name or note is never stored
# names the plan already gives other items: a bill under one of them would merge with that item in the plan's progress
_TAKEN = ("SELECT alias FROM cards UNION SELECT alias FROM debts UNION SELECT alias FROM fixed_expenses"
          " UNION SELECT payee_alias FROM fixed_expenses UNION SELECT alias FROM sinking_funds")
_RESERVED = ("dana-darurat", "uang-harian", "tabungan")


def _row(conn, alias: str):
    return conn.execute("SELECT * FROM one_off_bills WHERE alias=?", (alias,)).fetchone()


def _log(conn, alias: str, before, reason: str | None = None) -> None:
    changelog.log(conn, "one_off_bills", alias, "ubah" if before else "baru", dict(before) if before else None,
                  dict(_row(conn, alias)), reason)


def for_plan(conn, payday: date, nxt: date) -> list[sqlite3.Row]:
    """The bills the plan of `payday` covers: recorded before it, due before the next payday, open or paid from the payday on
    (a bill paid during the cycle is the plan carried out, not a plan without it)."""
    p = payday.isoformat()
    return conn.execute("SELECT * FROM one_off_bills WHERE recorded_on < ? AND due_date < ?"
                        " AND (status = 'terbuka' OR (status = 'lunas' AND paid_on >= ?)) ORDER BY due_date, alias",
                        (p, nxt.isoformat(), p)).fetchall()


def first_plan(b, holidays) -> date:
    """The payday of the first plan that has bill `b` (for_plan's rule): the first payday after the day it was recorded whose
    window reaches its due date. An open bill stays in every plan from there on."""
    return max(window_payday(date.fromisoformat(b["due_date"]), holidays),
               next_payday(window_payday(date.fromisoformat(b["recorded_on"]), holidays), holidays))


def outside_plan(conn, payday: date, nxt: date) -> list[sqlite3.Row]:
    """Open bills recorded on or after `payday` that fall due before the next one: the running plan does not have them."""
    return conn.execute("SELECT * FROM one_off_bills WHERE status = 'terbuka' AND recorded_on >= ?"
                        " AND due_date < ? ORDER BY due_date, alias", (payday.isoformat(), nxt.isoformat())).fetchall()


def record(conn, today: date, alias: str, name: str | None, amount: int, due: str, pay_to: str | None = None,
           method: str | None = None, note: str | None = None) -> sqlite3.Row:
    """A bill to pay once, recorded on the server's `today` (which plans have it), or a change to one still open under the same
    alias (logged; it keeps its day). On a change, an empty name, payee, method or note keeps the stored one (a model sends
    unused fields empty)."""
    check_idr(amount)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,40}", alias or ""):
        raise ValueError("alias: huruf kecil/angka/strip, 2-41 karakter")
    if amount <= 0:
        raise ValueError("jumlah harus lebih dari 0")
    try:
        when = date.fromisoformat(due or "")
    except ValueError:
        raise ValueError("jatuh_tempo: tanggal YYYY-MM-DD") from None
    row = _row(conn, alias)
    if row is not None and row["status"] != "terbuka":
        raise ValueError(f"tagihan {alias} sudah {row['status']}; tagihan baru memakai alias lain")
    if row is None and (alias in _RESERVED or conn.execute(f"SELECT 1 FROM ({_TAKEN}) WHERE alias=?", (alias,)).fetchone()):
        raise ValueError(f"alias {alias} sudah dipakai pos lain di rencana gajian; pakai alias lain (mis. {alias}-tunggakan)")
    name = _LONG_DIGITS.sub("[angka]", name.strip()) if name else (row["name"] if row else "")
    if not name or len(name) > NAME_MAX:
        raise ValueError(f"nama wajib, maksimal {NAME_MAX} karakter")
    note = _LONG_DIGITS.sub("[angka]", note.strip()) if note and note.strip() else (row["note"] if row else None)
    if note and len(note) > NOTE_MAX:
        raise ValueError(f"catatan maksimal {NOTE_MAX} karakter")
    method = method or (row["method"] if row else "transfer")
    if method not in ("transfer", "app_menu"):
        raise ValueError("cara: 'transfer' atau 'app_menu' (lewat menu aplikasi bank)")
    pay_to = pay_to or (row["pay_to_alias"] if row else None)
    if pay_to and not conn.execute("SELECT 1 FROM payee_secrets WHERE alias=?", (pay_to,)).fetchone():
        raise ValueError(f"tujuan {pay_to} belum terdaftar: pemilik mendaftarkan nomornya dengan /rekening atau /va (nomor tidak "
                         "lewat chat ini), atau bayar_ke dikosongkan")
    stamp = datetime.now(WIB).isoformat(timespec="seconds")
    if row is None:
        conn.execute("INSERT INTO one_off_bills(alias, name, amount, due_date, method, pay_to_alias, status, note, recorded_on,"
                     " created_at, updated_at) VALUES (?,?,?,?,?,?,'terbuka',?,?,?,?)",
                     (alias, name, amount, when.isoformat(), method, pay_to, note, today.isoformat(), stamp, stamp))
    else:
        conn.execute("UPDATE one_off_bills SET name=?, amount=?, due_date=?, method=?, pay_to_alias=?, note=?, updated_at=?"
                     " WHERE alias=?", (name, amount, when.isoformat(), method, pay_to, note, stamp, alias))
    _log(conn, alias, row)
    conn.commit()
    return _row(conn, alias)


def _open(conn, alias: str, status: tuple[str, ...]):
    row = _row(conn, alias or "")
    if row is None:
        raise ValueError(f"tagihan sekali bayar {alias} tidak ada (lihat tagihan_sekali aksi=daftar)")
    if row["status"] not in status:
        raise ValueError(f"tagihan {alias} berstatus {row['status']}")
    return row


def settle(conn, today: date, alias: str, paid_on: str | None = None) -> sqlite3.Row:
    """Paid (lunas) on `paid_on` (default today)."""
    row = _open(conn, alias, ("terbuka",))
    when = date.fromisoformat(paid_on) if paid_on else today
    if when > today:
        raise ValueError("tanggal bayar tidak boleh setelah hari ini")
    conn.execute("UPDATE one_off_bills SET status='lunas', paid_on=?, updated_at=? WHERE alias=?",
                 (when.isoformat(), datetime.now(WIB).isoformat(timespec="seconds"), alias))
    _log(conn, alias, row, "lunas")
    conn.commit()
    return _row(conn, alias)


def reopen(conn, alias: str) -> sqlite3.Row:
    """Back to open: a bill marked paid or cancelled by mistake."""
    row = _open(conn, alias, ("lunas", "batal"))
    conn.execute("UPDATE one_off_bills SET status='terbuka', paid_on=NULL, updated_at=? WHERE alias=?",
                 (datetime.now(WIB).isoformat(timespec="seconds"), alias))
    _log(conn, alias, row, "dibuka lagi")
    conn.commit()
    return _row(conn, alias)


def cancel(conn, alias: str, reason: str | None = None) -> sqlite3.Row:
    """Not to be paid after all (batal): it leaves every plan."""
    row = _open(conn, alias, ("terbuka",))
    conn.execute("UPDATE one_off_bills SET status='batal', updated_at=? WHERE alias=?",
                 (datetime.now(WIB).isoformat(timespec="seconds"), alias))
    _log(conn, alias, row, reason or "batal")
    conn.commit()
    return _row(conn, alias)


def describe(r) -> str:
    out = f"{r['alias']} ({r['name']}) {format_idr(r['amount'])}, jatuh tempo {r['due_date']}"
    if r["status"] == "lunas":
        out += f", LUNAS {r['paid_on']}"
    elif r["status"] == "batal":
        out += ", BATAL"
    if r["method"] == "app_menu":
        out += ", lewat menu aplikasi"
    elif r["pay_to_alias"]:
        out += f", bayar ke {r['pay_to_alias']}"
    else:
        out += ", nomor tujuan belum didaftarkan"
    return out + (f"; catatan: {r['note']}" if r["note"] else "")


def listing(conn, today: date) -> list[sqlite3.Row]:
    """Open bills, and those closed in the last 60 days."""
    since = (today - timedelta(days=60)).isoformat()
    return conn.execute("SELECT * FROM one_off_bills WHERE status = 'terbuka' OR substr(updated_at, 1, 10) >= ?"
                        " ORDER BY status != 'terbuka', due_date, alias", (since,)).fetchall()
