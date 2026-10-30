"""Expense capture, budgets and the financial health check. Deterministic: the model reads a
screenshot and passes the fields; every threshold, ratio and verdict is computed here.

Conventions
- Amounts are integer Rupiah; money out is negative in `transactions`.
- Categories that are NOT discretionary spending: 'transfer_internal', anything starting with
  'wajib:' (obligations such as school, lessons, loans, card bills) or 'sinking:' (pot deposits).
  Everything else (including uncategorized) counts as day-to-day spending.
- A receipt for money a mutation of the same bank shows is merged into it (`merged_into`), so it is never counted twice:
  when the statement is stored, or when the receipt is recorded or corrected after that bank's statements reach its day.
  A card purchase never is (it is on the card statement), nor a cash one (no bank shows it). A merged receipt can still be
  corrected, deleted or taken out of a row it is not (ubah_belanja lepas=true).
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import date, datetime, timedelta, timezone

from . import changelog
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
    unless allow_duplicate=True (two identical purchases in a day do happen). Money a stored statement of its bank
    already shows merges into that row at once (merge_receipts). Without an account or a card it is cash, which no
    statement shows."""
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
    # describes a re-sent screenshot in other words ("Isi saldo Flazz" vs "Isi Flazz BCA"), and it remembers nothing.
    # Merged records too (2026-10-30): one inside its bank row is still recorded; skipped, the screenshot sent again was
    # stored a second time or hit the unique key
    same = [r for r in conn.execute(
        "SELECT id, merchant, account_id, card_id, merged_into FROM transactions WHERE source='receipt' AND txn_date=? AND amount=?"
        " ORDER BY id", (txn_date, -amount)) if normalize(r["merchant"]) == key
        or (ids.get("account_id") is not None and r["account_id"] == ids.get("account_id"))
        or (ids.get("card_id") is not None and r["card_id"] == ids.get("card_id"))]
    if same and not allow_duplicate:
        inside = f", dan sudah digabung dengan {_merged_target(conn, same[0]['merged_into'])}" if same[0]["merged_into"] else ""
        return {"status": "possible_duplicate", "existing_id": same[0]["id"], "existing_merchant": same[0]["merchant"],
                "message": f"Sudah tercatat belanja dengan tanggal dan jumlah yang sama dari sumber yang sama ('{same[0]['merchant']}'){inside}. "
                           "Tanyakan ke pemilik; ulangi dengan allow_duplicate=true HANYA bila pemilik bilang memang dua pembelian."}
    rule = conn.execute("SELECT category FROM category_rules WHERE pattern=?", (key,)).fetchone()
    cat = clean_text(category, 40).lower() if category else (rule["category"] if rule else None)
    n = len(same) + 1                                           # the next free one: a deleted twin leaves its number taken
    while conn.execute("SELECT 1 FROM transactions WHERE dedupe_key=?", (_receipt_key(txn_date, amount, key, n),)).fetchone():
        n += 1
    cur = conn.execute(
        "INSERT INTO transactions(account_id,card_id,txn_date,merchant,amount,category,status,source,dedupe_key)"
        " VALUES (?,?,?,?,?,?,?,'receipt',?)",
        (ids.get("account_id"), ids.get("card_id"), txn_date, merchant, -amount, cat,
         "verified" if rule and not category else "unverified", _receipt_key(txn_date, amount, key, n)))
    # sent after its statement was stored: the row is already there, so it merges now instead of counting twice
    merged = merge_receipts(conn, receipt_id=cur.lastrowid)
    conn.commit()
    out = {"status": "stored", "id": cur.lastrowid, "category": cat,
           "alerts": alerts_for(conn, today, ("kartu:" + cat) if cat and card_alias else cat, d)}
    if merged:                  # in alerts, which the bot relays as they are: the owner sees the row and can say it is not it
        out["merged_into"] = merged[0][1]
        out["alerts"].insert(0, "Belanja ini sudah ada di " + _merged_note(conn, merged[0][1], cat))
    return out


def _receipt_key(txn_date: str, amount: int, key: str, n: int) -> str:
    return hashlib.sha256(f"receipt|{txn_date}|{amount}|{key}|{n}".encode()).hexdigest()


def _window(day: str) -> tuple[str, str]:
    d = date.fromisoformat(day)
    return (d - timedelta(days=MATCH_DAYS)).isoformat(), (d + timedelta(days=MATCH_DAYS)).isoformat()


def merge_receipts(conn, mutation_ids: list[int] | None = None, receipt_id: int | None = None) -> list[tuple[int, int]]:
    """A receipt for money a bank mutation also shows becomes part of that mutation (`merged_into`), so it counts once.

    The same money is the same amount within MATCH_DAYS at the same bank: one statement can carry several of the owner's
    accounts (the Jago statement lists every pocket). Never merged: a card purchase, which is on the card statement; a cash
    purchase (no account; until 2026-10-30 it could take any bank's debit of that size), which no statement shows; a
    purchase with a move between the owner's own accounts or the other way round (the Jago statement is full of round
    pocket moves); a receipt and a row the owner said it is not (ubah_belanja lepas=true). Closest dates pair first and
    each mutation takes one receipt, so of two equal debits a day apart the one on the receipt's date gets it. A row with
    no category takes the receipt's, logged so that taking the receipt out gives it back; a row that has one keeps it and
    its status. Runs over the new rows of a mutation file, for one receipt just recorded or corrected, or for one
    corrected receipt and the row it came from (both ids given: no coverage gate, that row was already its money). The
    caller commits. Returns the (receipt, mutation) pairs merged."""
    only, one = "", ()
    if receipt_id is not None:
        if mutation_ids is None:
            r = conn.execute("SELECT txn_date, amount FROM transactions WHERE id=?", (receipt_id,)).fetchone()
            # only a bank whose stored statements already reach the receipt's day: before that its own row is not in yet,
            # and the window would hand it to another payment of the same size (it merges when that statement is stored)
            mutation_ids = [m["id"] for m in conn.execute(
                "SELECT t.id FROM transactions t JOIN accounts a ON a.id = t.account_id WHERE t.source='mutation' AND t.amount=?"
                " AND t.txn_date BETWEEN ? AND ? AND EXISTS (SELECT 1 FROM mutation_files f JOIN accounts b ON b.id = f.account_id"
                " WHERE LOWER(TRIM(b.bank)) = LOWER(TRIM(a.bank)) AND ? BETWEEN f.period_start AND f.period_end)",
                (r["amount"], *_window(r["txn_date"]), r["txn_date"]))]
        only, one = " AND t.id=?", (receipt_id,)
    refused = _refused(conn)
    pairs = []
    for mid in mutation_ids or ():
        m = conn.execute("SELECT t.id, t.account_id, t.txn_date, t.amount, t.category, t.status, t.dedupe_key, a.bank"
                         " FROM transactions t JOIN accounts a ON a.id = t.account_id WHERE t.id=? AND t.source='mutation'"
                         " AND t.amount < 0 AND NOT EXISTS (SELECT 1 FROM transactions x WHERE x.merged_into = t.id)",
                         (mid,)).fetchone()
        if m is None:
            continue
        # JOIN, not LEFT JOIN: a receipt with no account is cash
        for r in conn.execute("SELECT t.id, t.account_id, t.txn_date, t.category, t.status, a.bank FROM transactions t"
                              " JOIN accounts a ON a.id = t.account_id WHERE t.source='receipt' AND t.merged_into IS NULL"
                              " AND t.card_id IS NULL AND t.amount=? AND t.txn_date BETWEEN ? AND ?" + only,
                              (m["amount"], *_window(m["txn_date"]), *one)):
            if (r["bank"] or "").strip().lower() != (m["bank"] or "").strip().lower():
                continue                                    # another bank's money ('Jago' and 'jago' are one bank)
            if m["category"] is not None and (m["category"] == INTERNAL) != (r["category"] == INTERNAL):
                continue
            if (r["id"], m["dedupe_key"] or f"id{m['id']}") in refused:
                continue
            days = abs((date.fromisoformat(r["txn_date"]) - date.fromisoformat(m["txn_date"])).days)
            pairs.append((days, 0 if r["account_id"] == m["account_id"] else 1, r["id"], m["id"], r, m))
    taken, merged = set(), []                               # receipt and mutation ids never collide: one table
    for _, _, rid, mid, r, m in sorted(pairs, key=lambda p: p[:4]):
        if rid in taken or mid in taken:
            continue
        taken.update((rid, mid))
        conn.execute("UPDATE transactions SET merged_into=? WHERE id=?", (mid, rid))
        if r["category"] and m["category"] is None:         # a row a rule or the owner already sorted keeps both
            _give(conn, mid, rid, m, r["category"], r["status"])
        merged.append((rid, mid))
    return merged


# change_log rows of what merging does to a bank row's category and what the owner refused: all 'ubah' (the action is
# checked to baru/ubah/hapus), told apart by a key in after_json: "catatan" (given by that record), "kembali" (given back
# when it was taken out, or gone with the row when its file was recorded again), "bukan" (on the record: the owner said
# it is not that row)

def _give(conn, mutation_id: int, receipt_id: int, was, category: str, status: str) -> None:
    """A bank row takes the category of the record merged into it; logged, so taking the record out gives it back."""
    conn.execute("UPDATE transactions SET category=?, status=? WHERE id=?", (category, status, mutation_id))
    changelog.log(conn, "transactions", mutation_id, "ubah", {"category": was["category"], "status": was["status"]},
                  {"category": category, "status": status, "catatan": receipt_id}, f"kategori dari catatan #{receipt_id}")


def _given(conn, mutation_id: int, receipt_id: int):
    """(before, after) of the category this record gave the row, while the row still has it as given; else None. Not when
    a record deleted since gave it: the last ids are used again, and a new record with that id gave nothing."""
    for row in conn.execute("SELECT id, before_json, after_json FROM change_log WHERE tbl='transactions' AND row_key=?"
                            " AND action='ubah' ORDER BY id DESC", (str(mutation_id),)):
        after = json.loads(row["after_json"] or "{}")
        if "catatan" not in after and "kembali" not in after:
            continue
        now = conn.execute("SELECT category, status FROM transactions WHERE id=?", (mutation_id,)).fetchone()
        if after.get("catatan") != receipt_id or now is None or (now["category"], now["status"]) != (after.get("category"),
                                                                                                    after.get("status")):
            return None
        if conn.execute("SELECT 1 FROM change_log WHERE tbl='transactions' AND row_key=? AND action='hapus' AND id > ?",
                        (str(receipt_id), row["id"])).fetchone():
            return None
        return json.loads(row["before_json"]), after
    return None


def _refused(conn) -> set[tuple[int, str]]:
    """(record, bank row key) pairs the owner said are not the same money (ubah_belanja lepas=true). By the row's key, not
    its id: a statement stored again gives its rows new ids. Not for a record deleted since: a new one may get its id."""
    out = set()
    for r in conn.execute("SELECT c.row_key, c.after_json FROM change_log c WHERE c.tbl='transactions' AND c.action='ubah'"
                          " AND c.after_json LIKE '%\"bukan\"%' AND NOT EXISTS (SELECT 1 FROM change_log h"
                          " WHERE h.tbl='transactions' AND h.row_key = c.row_key AND h.action='hapus' AND h.id > c.id)"):
        after = json.loads(r["after_json"])
        if "bukan" in after:
            out.add((int(r["row_key"]), after["bukan"]))
    return out


# ---- corrections: only what the owner recorded ------------------------------------------------
# Bank mutations and card statement lines come from documents and are corrected by uploading the document again.

OWN_SOURCES = ("receipt", "manual")
_LONG_DIGITS = re.compile(r"\d{6,}")


def _with_aliases(conn, txn_id: int):
    return conn.execute("SELECT t.*, a.alias AS account_alias, c.alias AS card_alias FROM transactions t"
                        " LEFT JOIN accounts a ON a.id = t.account_id LEFT JOIN cards c ON c.id = t.card_id WHERE t.id=?",
                        (txn_id,)).fetchone()


def _paid_from(r) -> str:
    return (f"kartu {r['card_alias']}" if r["card_alias"] else f"rekening {r['account_alias']}" if r["account_alias"]
            else "tunai")


def _merged_target(conn, txn_id: int) -> str:
    """What a merged row points at: usually the bank mutation that showed the same money, sometimes an earlier record of
    the owner's (a screenshot sent twice, 2026-10-28)."""
    t = conn.execute("SELECT source FROM transactions WHERE id=?", (txn_id,)).fetchone()
    return f"mutasi bank #{txn_id}" if t and t["source"] == "mutation" else f"catatan #{txn_id}"


def _shown(r, sep: str = ", ") -> str:
    return sep.join((_LONG_DIGITS.sub("[angka]", r["merchant"]), r["txn_date"], format_idr(-r["amount"]), _paid_from(r)))


def _merged_note(conn, mutation_id: int, category: str | None) -> str:
    """The bank row a record turned out to be, and the category that counts: the row's own when it had one."""
    m = _with_aliases(conn, mutation_id)
    note = f"mutasi bank #{m['id']} ({_shown(m)}) dan digabung ke sana: yang itu yang dihitung, tidak dobel"
    if category and m["category"] != category:
        return note + (f"; kategori yang dihitung {m['category']} (dari mutasi), bukan {category}; bila pemilik mau {category},"
                       f" ubah dengan set_category untuk #{m['id']}.")
    return note + (f"; kategori {m['category']}." if m["category"] else ".")


def list_expenses(conn, today: date, days: int = 14) -> list[str]:
    """Purchases the owner recorded (screenshots, the owner's words) in the last `days` days, newest first, each with its id: a
    new chat session remembers no ids, and a correction must name the right row."""
    since = (today - timedelta(days=max(1, min(days, 120)))).isoformat()
    rows = conn.execute("SELECT t.*, a.alias AS account_alias, c.alias AS card_alias FROM transactions t"
                        " LEFT JOIN accounts a ON a.id = t.account_id LEFT JOIN cards c ON c.id = t.card_id"
                        " WHERE t.source IN ('receipt','manual') AND t.txn_date >= ? ORDER BY t.txn_date DESC, t.id DESC LIMIT 60",
                        (since,)).fetchall()
    twins: dict[tuple, int] = {}
    for r in rows:
        if r["merged_into"] is None:             # a merged row is already settled, it is nobody's twin
            k = (r["txn_date"], r["amount"], r["account_id"], r["card_id"])
            twins[k] = twins.get(k, 0) + 1
    out = []
    for r in rows:
        line = f"#{r['id']} | {_shown(r, ' | ')} | {r['category'] or 'belum dikategorikan'}"
        if r["merged_into"] is not None:                 # the row it is in, so the owner can tell a wrong match
            t = _with_aliases(conn, r["merged_into"])
            line += (f" | sudah digabung dengan mutasi bank #{t['id']} ({_shown(t)}): yang itu yang dihitung"
                     if t is not None and t["source"] == "mutation" else
                     f" | sudah digabung dengan catatan #{r['merged_into']} (screenshot yang sama): yang itu yang dihitung")
        elif twins[(r["txn_date"], r["amount"], r["account_id"], r["card_id"])] > 1:
            line += " | ada catatan lain dengan tanggal, jumlah, dan sumber yang sama"
        out.append(line)
    return out or [f"Tidak ada belanja yang dicatat dari screenshot atau ucapan pemilik sejak {since}."]


def _own_row(conn, txn_id: int, recorded: int):
    """The row to correct, after the guards: it exists, the owner recorded it, and `recorded` (the positive size the bot
    read from daftar_belanja) matches what is stored, so a wrong id is refused rather than corrected. A merged record passes
    (2026-10-30, owner: "ya betulkan dua-duanya"; a wrong match had no way back): edit_expense and delete_expense say what
    happens to the row it was merged into."""
    check_idr(recorded)
    r = _with_aliases(conn, txn_id)
    if r is None:
        raise ValueError(f"belanja #{txn_id} tidak ditemukan; cari id-nya dengan daftar_belanja")
    if r["source"] not in OWN_SOURCES:
        raise ValueError(f"#{txn_id} berasal dari {'mutasi bank' if r['source'] == 'mutation' else 'tagihan kartu'}, bukan catatan "
                         "pemilik; perbaiki dengan mengunggah ulang berkasnya")
    if -r["amount"] != recorded:
        raise ValueError(f"#{txn_id} adalah {_shown(r)}, bukan belanja {format_idr(recorded)}: id-nya salah? cek daftar_belanja")
    return r


def _reason(text: str) -> str:
    why = clean_text(text, 200)
    if not why:
        raise ValueError("alasan wajib: kata-kata pemilik (mis. 'salah sumber, sebenarnya dari Jago')")
    return why


def _take_out(conn, rid: int, target: int, why: str):
    """Undo a merge: the record counts on its own again, and the row gets back the category it had before it took the
    record's, unless that was changed since. Returns (category given back, category taken back) or None."""
    conn.execute("UPDATE transactions SET merged_into=NULL WHERE id=?", (rid,))
    given = _given(conn, target, rid)
    if given is None:
        return None
    before, after = given
    conn.execute("UPDATE transactions SET category=?, status=? WHERE id=?", (before["category"], before["status"], target))
    changelog.log(conn, "transactions", target, "ubah", {"category": after["category"], "status": after["status"]},
                  {**before, "kembali": rid}, why)
    return before["category"], after["category"]


def edit_expense(conn, today: date, txn_id: int, recorded: int, reason: str, account_alias: str | None = None,
                 card_alias: str | None = None, amount: int | None = None, txn_date: str | None = None,
                 merchant: str | None = None, category: str | None = None, cash: bool = False,
                 unmerge: bool = False) -> str:
    """Correct one purchase the owner recorded. Fields left out keep their value; the source is an account, a card or cash.
    A merged record goes back into its bank row while it is still that money (same amount, bank and kind), else it is
    matched again; a category the owner names here is the one that counts, on that row too. `unmerge` (the owner: it is not
    that row) keeps it out of that row for good. The rows before and after go to change_log with the owner's reason."""
    why = _reason(reason)
    if sum(map(bool, (account_alias, card_alias, cash))) > 1:
        raise ValueError("isi rekening ATAU kartu ATAU tunai, bukan lebih dari satu")
    r = _own_row(conn, txn_id, recorded)
    target = r["merged_into"]
    into = conn.execute("SELECT source, category, dedupe_key FROM transactions WHERE id=?", (target,)).fetchone() if target else None
    if unmerge and into is None:
        raise ValueError(f"#{txn_id} tidak digabung dengan apa pun; tidak ada yang dilepas")
    if into is not None and into["source"] != "mutation" and not unmerge:
        raise ValueError(f"#{txn_id} adalah screenshot yang sama dengan catatan #{target}, dan yang itu yang dihitung: ubah #{target}"
                         f" atau hapus #{txn_id}; lepas=true HANYA bila pemilik bilang memang dua pembelian")
    new = {k: r[k] for k in ("account_id", "card_id", "txn_date", "merchant", "amount", "category", "status")}
    if account_alias or card_alias:
        table, alias = ("accounts", account_alias) if account_alias else ("cards", card_alias)
        row = conn.execute(f"SELECT id FROM {table} WHERE alias=?", (alias,)).fetchone()
        if row is None:
            raise ValueError(f"{'rekening' if account_alias else 'kartu'} {alias} belum terdaftar (lihat ringkasan_data)")
        new["account_id"], new["card_id"] = (row["id"], None) if account_alias else (None, row["id"])
    if cash:
        new["account_id"], new["card_id"] = None, None
    if amount is not None:
        check_idr(amount)
        if amount <= 0:
            raise ValueError("jumlah harus > 0 (besar pengeluaran)")
        new["amount"] = -amount
    if txn_date is not None:
        if date.fromisoformat(txn_date) > today + timedelta(days=1):
            raise ValueError("tanggal transaksi di masa depan")
        new["txn_date"] = txn_date
    if merchant is not None:
        new["merchant"] = clean_text(merchant, 120)
        if not new["merchant"]:
            raise ValueError("merchant kosong")
    if category is not None:
        new["category"] = clean_text(category, 40).lower() or None
        new["status"] = "verified"                          # the owner said it, as with set_category
    # a category the owner names for a merged record is meant for the row that counts, even when the record has it already
    for_row = into is not None and into["source"] == "mutation" and category is not None and into["category"] != new["category"]
    if all(new[k] == r[k] for k in new) and not unmerge and not for_row:
        raise ValueError("tidak ada yang berubah")
    # an id-based key: record_expense's keys end in a count, so a later record of the old values can never collide
    new["dedupe_key"] = hashlib.sha256(f"receipt|{new['txn_date']}|{-new['amount']}|{normalize(new['merchant'])}|id{txn_id}"
                                       .encode()).hexdigest()
    before = dict(r)
    back = _take_out(conn, txn_id, target, why) if into is not None else None
    if unmerge:          # the owner's word, kept by the row's content: a statement stored again (new ids) does not hand it back
        changelog.log(conn, "transactions", txn_id, "ubah", {"merged_into": target},
                      {"merged_into": None, "bukan": into["dedupe_key"] or f"id{target}"}, why)
    conn.execute("UPDATE transactions SET account_id=?, card_id=?, txn_date=?, merchant=?, amount=?, category=?, status=?,"
                 " dedupe_key=? WHERE id=?", (*new.values(), txn_id))
    # back into the row it came from while it is still that money: an upload merges without the coverage gate, so matching
    # afresh could leave a correctly merged purchase counted twice. Otherwise, or once let go, matched afresh: a record
    # with the wrong bank stays out of that bank's statement row; corrected, it finds the row it belongs to
    back_in = into is not None and into["source"] == "mutation" and not unmerge
    merged = (merge_receipts(conn, [target], receipt_id=txn_id) if back_in else []) or merge_receipts(conn, receipt_id=txn_id)
    if merged and category is not None and new["category"]:
        m = conn.execute("SELECT category, status FROM transactions WHERE id=?", (merged[0][1],)).fetchone()
        if (m["category"], m["status"]) != (new["category"], "verified"):
            _give(conn, merged[0][1], txn_id, m, new["category"], "verified")
    after = _with_aliases(conn, txn_id)
    changelog.log(conn, "transactions", txn_id, "ubah", before, dict(after), why)
    conn.commit()
    names = {"sumber": _paid_from, "tanggal": lambda x: x["txn_date"], "merchant": lambda x: _LONG_DIGITS.sub("[angka]", x["merchant"]),
             "jumlah": lambda x: format_idr(-x["amount"]), "kategori": lambda x: x["category"] or "belum dikategorikan"}
    diff = [f"{n} {f(before)} -> {f(after)}" for n, f in names.items() if f(before) != f(after)]
    head = "; ".join(diff) or ("kategori dipastikan pemilik" if category is not None else "")
    out = (f"Belanja #{txn_id} " + (f"diubah: {head}" if head else "dilepas") + f". Alasan: {why}."
           " Sebelum dan sesudahnya tersimpan di catatan perubahan.")
    if target is not None and after["merged_into"] == target:
        out += " Masih cocok dengan " + _merged_note(conn, target, after["category"])
    else:
        if target is not None:
            out += f" Dilepas dari {_merged_target(conn, target)}"
            if into["source"] == "mutation":
                out += f" ({_shown(_with_aliases(conn, target))})"
            if back:
                out += f"; kategori mutasi itu kembali {back[0] or 'belum dikategorikan'} (tadinya {back[1]}, dari catatan ini)"
            out += "."
        if merged:
            out += " Sekarang cocok dengan " + _merged_note(conn, merged[0][1], after["category"])
        elif target is not None:
            out += " Sekarang dihitung sendiri" + ("; tidak digabung lagi ke baris itu." if unmerge else ".")
    cat = after["category"]
    alerts = alerts_for(conn, today, ("kartu:" + cat) if cat and after["card_id"] else cat, date.fromisoformat(after["txn_date"]))
    return out + "".join(f"\nPeringatan: {a}" for a in alerts)


def delete_expense(conn, txn_id: int, recorded: int, reason: str) -> str:
    """Remove one purchase the owner recorded (e.g. recorded twice). The whole row is kept in change_log. A merged record
    can go too: the bank row it was part of still counts and keeps its category; the text says when that category came
    from the record, so a wrong one can be fixed."""
    why = _reason(reason)
    r = _own_row(conn, txn_id, recorded)
    ref = conn.execute("SELECT id FROM transactions WHERE merged_into=?", (txn_id,)).fetchone()
    if ref:
        raise ValueError(f"#{ref['id']} merujuk ke #{txn_id}; tidak bisa dihapus (hapus atau lepas #{ref['id']} dulu)")
    given = _given(conn, r["merged_into"], txn_id) if r["merged_into"] is not None else None   # before the delete is logged
    changelog.log(conn, "transactions", txn_id, "hapus", dict(r), None, why)
    conn.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
    conn.commit()
    out = f"Belanja #{txn_id} dihapus: {_shown(r)}. Alasan: {why}. Isinya tetap tersimpan di catatan perubahan."
    m = _with_aliases(conn, r["merged_into"]) if r["merged_into"] is not None else None
    if m is not None and m["source"] == "mutation":
        out += f" Mutasi bank #{m['id']} ({_shown(m)}) tetap dihitung: uangnya memang keluar"
        if given:
            out += (f"; kategorinya {m['category']} diambil dari catatan ini: bila mutasi itu bukan belanja ini, ubah dengan"
                    f" set_category untuk #{m['id']}.")
        else:
            out += f"; kategori {m['category']}." if m["category"] else "; belum dikategorikan."
    elif m is not None:
        out += f" Catatan #{m['id']} (screenshot yang sama) tetap dihitung."
    return out


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
