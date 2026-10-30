"""Cross-source data audit: code compares sources that must agree, so a wrong or stale number surfaces instead of
quietly flowing into a plan. No model judgement: each finding is a fixed rule over the ledger.

- a statement whose totals do not reconcile, or whose lines (read by code from the PDF) do not add up to them;
- a card whose next statement should already be here;
- a bill past its due date whose minimum is not recorded as paid (a rest carried after the minimum only earns interest);
- a subscription whose recorded monthly amount differs from what the cards actually charged, or that was not charged;
- a charge that repeats every month but is not recorded as a subscription;
- a card instalment that no longer appears on the card's latest statement;
- a pot whose balance has not been reported for a while (the projection then runs on an old figure)."""
from __future__ import annotations

import re
from datetime import date, timedelta

from .money import format_idr

STATEMENT_EVERY_DAYS = 35      # a card prints a statement about every 30 days; later than this, the newest one is missing
POT_STALE_DAYS = 40
_GENERIC = {"one", "plan", "unit", "cs", "domain", "workspace", "langganan", "premium", "family", "dan", "the", "email", "sewa",
            "paket", "termasuk", "perawatan", "kontrak", "via"}
_SYNONYMS = {"squarespace": r"sqsp|squarespace", "microsoft": r"microsoft|msbill", "anthropic": r"anthropic|claude",
             "rockstar": r"rockstar", "google": r"google ?(one|g1)", "apple": r"apple\.com|itunes"}


def _keyword(alias: str, name: str) -> str | None:
    """The merchant pattern of a subscription: a known merchant anywhere in its name wins (so "Email domain (Workspace via
    Squarespace)" and "Domain (Squarespace)" both mean Squarespace), else its first distinctive word."""
    toks = re.findall(r"[a-z0-9]+", f"{name} {alias}".lower())
    for tok in toks:
        if tok in _SYNONYMS:
            return _SYNONYMS[tok]
    for tok in toks:
        if len(tok) >= 4 and tok not in _GENERIC and not tok.isdigit():
            return re.escape(tok)
    return None


def _latest_cycle(conn) -> str | None:
    row = conn.execute("SELECT max(substr(cycle,1,7)) FROM card_lines").fetchone()
    return row[0] if row else None


def run(conn, today: date) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    # 1. statements: totals and code-read lines
    for r in conn.execute("SELECT c.alias, s.statement_date, s.reconciled, s.recon_diff, s.lines_status, s.lines_diff FROM statements s"
                          " JOIN cards c ON c.id = s.card_id WHERE s.statement_date >= ? ORDER BY s.statement_date",
                          ((today - timedelta(days=200)).isoformat(),)):
        if not r["reconciled"]:
            out.append(("bad", f"Tagihan {r['alias']} {r['statement_date']}: total tidak rekonsiliasi (selisih {format_idr(abs(r['recon_diff']))}); "
                               "angka tagihan perlu dicek ulang dari PDF."))
        elif r["lines_status"] == "selisih":
            out.append(("warn", f"Tagihan {r['alias']} {r['statement_date']}: baris yang terbaca kode selisih {format_idr(abs(r['lines_diff'] or 0))} "
                                "dari total; rincian belanja bulan itu bisa kurang."))
        elif r["lines_status"] == "tanpa-berkas":
            out.append(("info", f"Tagihan {r['alias']} {r['statement_date']}: berkas PDF tidak ditemukan, barisnya belum terbaca."))
    # 2. and 3. per card: the newest statement is fresh, and a bill past due is paid
    for r in conn.execute("SELECT c.alias, s.statement_date, s.due_date, s.total_due, s.minimum_due, s.paid_amount, s.paid_at FROM cards c"
                          " JOIN statements s ON s.id = (SELECT id FROM statements WHERE card_id = c.id ORDER BY statement_date DESC, id DESC LIMIT 1)"):
        age = (today - date.fromisoformat(r["statement_date"])).days
        if age > STATEMENT_EVERY_DAYS:
            out.append(("warn", f"Kartu {r['alias']}: tagihan terbaru yang tercatat {r['statement_date']} ({age} hari lalu). Tagihan bulan ini "
                                "belum diunggah, jadi rencana memakai angka lama."))
        due = date.fromisoformat(r["due_date"])
        owed = r["total_due"] - r["paid_amount"]
        if due < today and owed > 0 and not r["paid_at"]:
            if r["paid_amount"] < r["minimum_due"]:
                out.append(("bad", f"Kartu {r['alias']}: tagihan jatuh tempo {r['due_date']} belum tercatat dibayar minimal "
                                   f"{format_idr(r['minimum_due'])}. Kalau sudah dibayar, catat dengan record_card_payment."))
            else:
                out.append(("info", f"Kartu {r['alias']}: minimum tagihan jatuh tempo {r['due_date']} sudah terpenuhi (tidak telat, "
                                    f"tidak ada denda); sisa {format_idr(owed)} dibawa ke tagihan berikutnya dan berbunga."))
    # 4. and 5. subscriptions against what the cards charged in the latest cycle
    cycle = _latest_cycle(conn)
    if cycle:
        lines = conn.execute("SELECT substr(cycle,1,7) m, description d, amount a, kind FROM card_lines WHERE kind IN ('belanja','langganan','refund')"
                             " AND substr(cycle,1,7) >= ?", ((date.fromisoformat(cycle + "-01") - timedelta(days=62)).strftime("%Y-%m"),)).fetchall()
        bill_date = conn.execute("SELECT max(statement_date) FROM statements WHERE substr(statement_date,1,7)=?", (cycle,)).fetchone()[0]
        groups: dict[str, list] = {}
        stopped: dict[str, list] = {}
        for s in conn.execute("SELECT * FROM subscriptions WHERE status IN ('active','ended')"):
            kw = _keyword(s["alias"], s["name"])
            if not kw:
                continue
            if s["status"] == "active" and (s["ends"] is None or s["ends"] >= cycle):
                groups.setdefault(kw, []).append(s)
            elif s["status"] == "ended":
                stopped.setdefault(kw, []).append(s)

        def after_bill(subs) -> bool:      # the owner's latest word on these came after the bill: the bill is old news
            return bool(bill_date) and all((s["updated_at"] or "")[:10] > bill_date for s in subs)
        for kw, subs in groups.items():
            expected = sum(s["amount"] for s in subs)
            actual = sum(x["a"] for x in lines if x["m"] == cycle and re.search(kw, x["d"], re.I))
            names = ", ".join(s["alias"] for s in subs)
            if actual == 0:
                out.append(("info", f"Langganan {names} (tercatat {format_idr(expected)}/bulan) tidak terlihat di tagihan kartu siklus {cycle}: "
                                    "pindah kartu, dibayar dari rekening, atau sudah berhenti?"))
            elif actual > expected + max(50_000, expected // 10):
                newer = after_bill(subs)
                out.append(("info" if newer else "warn",
                            f"Langganan {names}: tercatat {format_idr(expected)}/bulan, tetapi kartu menagih {format_idr(actual)} di siklus {cycle} "
                            "(bisa termasuk pembelian satu kali di merchant yang sama). "
                            + ("Catatan sudah diperbarui pemilik setelah tagihan itu; cek lagi di tagihan berikutnya." if newer
                               else "Perbarui catatan atau cek tagihan ganda.")))
            elif actual < expected - max(50_000, expected // 10):
                out.append(("info", f"Langganan {names}: tercatat {format_idr(expected)}/bulan, kartu menagih {format_idr(actual)} di siklus {cycle}."))
        for kw, subs in stopped.items():
            if kw in groups:
                continue
            actual = sum(x["a"] for x in lines if x["m"] == cycle and re.search(kw, x["d"], re.I))
            if actual > 0 and not after_bill(subs):
                out.append(("warn", f"Langganan {', '.join(s['alias'] for s in subs)} tercatat BERHENTI, tetapi kartu masih menagih "
                                    f"{format_idr(actual)} di siklus {cycle}. Pastikan benar sudah dibatalkan."))
        seen: dict[str, set] = {}
        for x in lines:
            if x["kind"] != "langganan" or any(re.search(kw, x["d"], re.I) for kw in list(groups) + list(stopped)):
                continue
            key = " ".join(re.sub(r"[^A-Za-z ]+", " ", x["d"]).split()[:2]).upper()
            if key:
                seen.setdefault(key, set()).add(x["m"])
        for key, months in sorted(seen.items()):
            if len(months) >= 2:
                out.append(("info", f"Tagihan berulang '{key.title()}' muncul di {len(months)} siklus terakhir tetapi belum tercatat sebagai langganan."))
    # 6. card instalments still printed on the card's newest statement
    from . import card_installments
    for a in card_installments.active(conn):
        latest = conn.execute("SELECT s.id, s.statement_date FROM statements s JOIN cards c ON c.id = s.card_id WHERE c.alias=?"
                              " ORDER BY s.statement_date DESC, s.id DESC LIMIT 1", (a["card"],)).fetchone()
        if not latest or latest["statement_date"] <= a.get("as_of", ""):
            continue
        hit = conn.execute("SELECT 1 FROM card_lines WHERE statement_id=? AND amount=?", (latest["id"], a["per_month"])).fetchone()
        has_lines = conn.execute("SELECT 1 FROM card_lines WHERE statement_id=?", (latest["id"],)).fetchone()
        if has_lines and not hit:
            out.append(("warn", f"Cicilan kartu {a['card']} '{a['description']}' {format_idr(a['per_month'])} tidak terlihat di tagihan "
                                f"{latest['statement_date']}: sudah lunas, dipercepat, atau berubah? Catat ulang cicilan dari tagihan itu."))
    # 7. pots whose balance is old
    for f in conn.execute("SELECT alias, saved_asof FROM sinking_funds"):
        age = (today - date.fromisoformat(f["saved_asof"])).days
        if age > POT_STALE_DAYS:
            out.append(("info", f"Saldo pot {f['alias']} terakhir diperbarui {f['saved_asof']} ({age} hari lalu). Laporkan saldo di aplikasi bank "
                                "(saldo_pot) supaya proyeksi memakai angka nyata."))
    return out


def format_audit(findings: list[tuple[str, str]]) -> str:
    if not findings:
        return "PERIKSA DATA: semua sumber cocok (tagihan, baris tagihan, pembayaran, langganan, cicilan, pot)."
    mark = {"bad": "MASALAH", "warn": "PERHATIAN", "info": "INFO"}
    order = {"bad": 0, "warn": 1, "info": 2}
    lines = [f"PERIKSA DATA: {sum(1 for s, _ in findings if s == 'bad')} masalah, {sum(1 for s, _ in findings if s == 'warn')} perhatian, "
             f"{sum(1 for s, _ in findings if s == 'info')} info. Dihitung kode dengan aturan tetap."]
    lines += [f"- {mark[s]}: {t}" for s, t in sorted(findings, key=lambda f: order[f[0]])]
    return "\n".join(lines)
