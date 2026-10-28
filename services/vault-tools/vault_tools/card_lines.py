"""Card statement lines: every transaction line of a stored card statement, read by code (no model), classified, and
checked against the statement itself (previous balance - payments + new charges + fees = total due, so the lines must
add up to total - previous). This is what the stored totals hide: what was bought, and what is an instalment, a
subscription, interest or a fee. Parsed once per statement; the owner's questions are then answered from the table."""
from __future__ import annotations

import hashlib
import os
import re
import sqlite3
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from . import card_installments, statement_pdf
from .money import format_idr

KINDS = ("belanja", "langganan", "cicilan", "bunga", "biaya", "pembayaran", "refund")
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "mei": 5, "jun": 6, "jul": 7, "aug": 8, "agu": 8, "agt": 8,
           "sep": 9, "oct": 10, "okt": 10, "nov": 11, "dec": 12, "des": 12}
_DATE = r"(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|\d{1,2}-[A-Za-z]{3}(?:-\d{2,4})?|\d{1,2}\s?[A-Za-z]{3}(?:\s\d{4})?)"
_LINE = re.compile(rf"^\s*(?P<d1>{_DATE})\s+(?P<d2>{_DATE})\s+(?P<desc>.+?)\s+(?:Rp\.?\s*)?"
                   r"(?P<amt>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(?P<cr>CR)?\s*$", re.I)
ONE_OFF_FROM = 1_500_000            # a single purchase this big is shown apart: it distorts any monthly average

# card merchants -> category. The owner's own words (category_keywords) are checked before these.
CARD_RULES: list[tuple[str, str]] = [
    ("langganan", r"netflix|spotify|youtube|disney|apple\.com|itunes|google ?(one|g1)|icloud|canva|openai|chatgpt|anthropic|"
                  r"claude|microsoft|msbill|catchplay|gopro|sqsp|squarespace|\baws\b|amazon web|rockstar ?gym|coway|telkomsel"),
    ("game-digital", r"steam|playstation|\bpsn\b|nintendo|xbox|google ?play|garena|codashop|unipin|mobile ?legends"),
    ("top-up e-wallet", r"gopay|\bovo\b|\bdana\b|shopeepay|linkaja"),
    ("belanja-online", r"tokopedia|shopee|lazada|blibli|bukalapak|tiktok|zalora"),
    ("kesehatan", r"halodoc|apotek|apotik|klinik|rumah ?sakit|hospital|siloam|mandaya|hermina|kimia ?farma|guardian"),
    ("makan", r"restaurant|resto|\besb\b|cafe|coffee|kopi|boost ?juice|food|bakery|starbucks|mcdonald|\bkfc\b|chagee|"
              r"janji ?jiwa|pizza|burger|sushi|bakmi|warung|warteg"),
    ("transport", r"\bgrab\b|gojek|pertamina|\bshell\b|\btol\b|parkir|bluebird|\bmrt\b|\bkrl\b|kai ?access|petado"),
    ("belanja-harian", r"indomaret|\bidm\b|alfamart|alfamidi|superindo|hypermart|lotte ?mart|ranch ?market|aeon"),
    ("liburan", r"traveloka|tiket\.com|agoda|booking\.com|airbnb|garuda|lion ?air|airasia|citilink"),
    ("telepon-internet", r"xl ?axiata|indosat|\bsmartfren\b|\bby\.u\b|biznet|indihome|first ?media"),
]
_PAYMENT = re.compile(r"pembayaran|payment|\bpmt\b|bayar|bi-?fast|transfer|autodebet|cash ?management|livin", re.I)
_INSTALMENT = re.compile(r"cicilan|instal{1,2}ment|instlmnt|\b\d{1,3}\s*(?:of|dari)\s*\d{1,3}\b|\(\d{3}/\d{3}\)|\bke \d+ dari \d+", re.I)
_INTEREST = re.compile(r"bunga|interest|finance ?charge", re.I)
_FEE = re.compile(r"biaya|(?<!cof)fee|materai|meterai|stamp|iuran|overlimit|terlambat|late ?charge|chrge|charge|administration|"
                  r"notifikasi|notification|annual", re.I)


def parse_amount(text: str) -> int:
    """'125.000' / '304,140.01' / '7,000.00' / '2,274,554' / '1.234,56' -> whole Rupiah (half up)."""
    s = text.strip()
    last = max(s.rfind("."), s.rfind(","))
    if last >= 0 and len(s) - last - 1 in (1, 2):              # a decimal part
        whole, frac = re.sub(r"[.,]", "", s[:last]), s[last + 1:]
        value = Decimal(f"{whole or '0'}.{frac}")
    else:
        value = Decimal(re.sub(r"[.,]", "", s))
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _date(token: str, cycle: date, month_first: bool) -> str | None:
    """Best-effort transaction date; the statement date gives the year. None when it cannot be read safely."""
    t = token.strip().lower()
    m = re.match(r"^(\d{1,2})[\s-]?([a-z]{3})(?:[\s-](\d{2,4}))?$", t)
    if m and m.group(2) in _MONTHS:
        day, mon, y = int(m.group(1)), _MONTHS[m.group(2)], m.group(3)
    else:
        m = re.match(r"^(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?$", t)
        if not m:
            return None
        a, b, y = int(m.group(1)), int(m.group(2)), m.group(3)
        day, mon = (b, a) if month_first else (a, b)
    year = int(y) + (2000 if y and len(y) == 2 else 0) if y else (cycle.year - (1 if mon > cycle.month else 0))
    try:
        return date(year, mon, day).isoformat()
    except ValueError:
        return None


def parse_text(text: str, cycle: date, month_first: bool = False) -> list[dict]:
    out = []
    for raw in text.splitlines():
        m = _LINE.match(raw)
        if not m:
            continue
        desc = " ".join(m.group("desc").split())
        if len(re.findall(r"[A-Za-z]", desc)) < 2 or desc.lower().startswith("rp"):
            continue                                           # summary rows ("Rp. 2,386,662 Rp. 201,221"), page markers
        amount = parse_amount(m.group("amt"))
        if amount == 0:
            continue
        out.append({"txn_date": _date(m.group("d1"), cycle, month_first), "description": desc[:120],
                    "amount": -amount if m.group("cr") else amount})
    return out


def classify(desc: str, amount: int) -> str:
    if amount < 0:
        return "pembayaran" if _PAYMENT.search(desc) else "refund"
    if _INSTALMENT.search(desc):
        return "cicilan"
    if _INTEREST.search(desc):
        return "bunga"
    if _FEE.search(desc):
        return "biaya"
    return "belanja"


def categorize(conn, desc: str) -> str:
    low = desc.lower()
    for kw, cat in conn.execute("SELECT keyword, category FROM category_keywords"):
        if kw in low:
            return cat
    for cat, rx in CARD_RULES:
        if re.search(rx, low):
            return cat
    return "lain-lain"


def reconcile(lines: list[dict], st) -> int:
    """Lines minus what the statement says they should add up to (0 = every line was read)."""
    return sum(x["amount"] for x in lines) - (st["total_due"] - st["previous_balance"])


def _tolerance(lines: list[dict]) -> int:
    return max(5, len(lines))                                 # cents rounding: at most Rp 1 per line


def store(conn, statement_id: int, lines: list[dict]) -> dict:
    st = conn.execute("SELECT s.*, c.alias AS card FROM statements s JOIN cards c ON c.id = s.card_id WHERE s.id=?", (statement_id,)).fetchone()
    diff = reconcile(lines, st)
    note = ""
    if abs(diff) > _tolerance(lines) and diff < 0:
        # a line whose amount the number-masking swallowed: fill it from the card's known instalments when it fits exactly
        for a in card_installments.active(conn) + _all_instalments(conn, st["card_id"]):
            if a["card"] == st["card"] and abs(-diff - a["per_month"]) <= _tolerance(lines):
                lines = lines + [{"txn_date": None, "description": f"{a['description']} (dari daftar cicilan)", "amount": a["per_month"]}]
                diff, note = reconcile(lines, st), "satu baris cicilan diisi dari daftar cicilan"
                break
    ok = abs(diff) <= _tolerance(lines)
    conn.execute("DELETE FROM card_lines WHERE statement_id=?", (statement_id,))
    for x in lines:
        kind = classify(x["description"], x["amount"])
        cat = categorize(conn, x["description"]) if kind == "belanja" else kind
        if kind == "belanja" and cat == "langganan":
            kind = "langganan"
        conn.execute("INSERT INTO card_lines(statement_id,card_id,cycle,txn_date,description,amount,kind,category) VALUES (?,?,?,?,?,?,?,?)",
                     (statement_id, st["card_id"], st["statement_date"], x["txn_date"], x["description"], x["amount"], kind, cat))
    conn.execute("UPDATE statements SET lines_status=?, lines_diff=? WHERE id=?", ("cocok" if ok else "selisih", diff, statement_id))
    conn.commit()
    return {"lines": len(lines), "status": "cocok" if ok else "selisih", "diff": diff, "note": note}


def _all_instalments(conn, card_id: int) -> list[dict]:
    rows = conn.execute("SELECT i.*, c.alias AS card FROM card_installments i JOIN cards c ON c.id=i.card_id WHERE i.card_id=?", (card_id,)).fetchall()
    return [{"card": r["card"], "description": r["description"], "per_month": r["per_month"]} for r in rows]


# ---- files ---------------------------------------------------------------------------------------------------

def remember_file(conn, file_hash: str, path: str) -> None:
    conn.execute("INSERT OR REPLACE INTO doc_files(hash, path) VALUES (?,?)", (file_hash, path))
    conn.commit()


def find_file(conn, file_hash: str, ingest_dir: str) -> str | None:
    row = conn.execute("SELECT path FROM doc_files WHERE hash=?", (file_hash,)).fetchone()
    if row and os.path.isfile(row["path"]):
        return row["path"]
    direct = os.path.join(ingest_dir, file_hash + ".pdf")
    if os.path.isfile(direct):
        return direct
    for root in (ingest_dir, os.path.join(ingest_dir, "telegram")):
        for n in os.listdir(root) if os.path.isdir(root) else ():
            p = os.path.join(root, n)
            if os.path.isfile(p) and n.lower().endswith((".pdf", ".csv", ".txt")):
                with open(p, "rb") as f:
                    h = hashlib.sha256(f.read()).hexdigest()
                remember_file(conn, h, p)
                if h == file_hash:
                    return p
    return None


def process_statement(conn, statement_id: int, ingest_dir: str, passwords: dict) -> dict:
    st = conn.execute("SELECT s.*, c.bank FROM statements s JOIN cards c ON c.id = s.card_id WHERE s.id=?", (statement_id,)).fetchone()
    path = find_file(conn, st["file_hash"], ingest_dir)
    if path is None:
        conn.execute("UPDATE statements SET lines_status='tanpa-berkas' WHERE id=?", (statement_id,))
        conn.commit()
        return {"lines": 0, "status": "tanpa-berkas", "diff": None, "note": ""}
    cands = passwords.get(st["bank"].lower()) or [p for v in passwords.values() for p in v]
    with open(path, "rb") as f:
        _, parts = statement_pdf.ingest_file_parts(f.read(), os.path.basename(path), cands)
    lines = parse_text("\n".join(parts), date.fromisoformat(st["statement_date"]), month_first=st["bank"].lower() == "dbs")
    return store(conn, statement_id, lines)


# ---- answers ---------------------------------------------------------------------------------------------------

def summary(conn, cycles: int = 3) -> dict:
    months = [r[0] for r in conn.execute("SELECT DISTINCT substr(cycle,1,7) m FROM card_lines ORDER BY m DESC LIMIT ?", (max(1, cycles),))]
    months.sort()
    out = {"months": months, "by_month": {}, "missing": [], "mismatch": []}
    for m in months:
        rows = conn.execute("SELECT l.*, c.alias AS card FROM card_lines l JOIN cards c ON c.id = l.card_id WHERE substr(l.cycle,1,7)=?", (m,)).fetchall()
        kinds, cats, merchants, big = defaultdict(int), defaultdict(int), defaultdict(int), []
        for r in rows:
            kinds[r["kind"]] += r["amount"]
            if r["kind"] == "belanja":
                cats[r["category"]] += r["amount"]
                key = re.sub(r"[\d#*\[\]:]+", " ", r["description"]).split()
                merchants[" ".join(key[:3]).upper()] += r["amount"]
                if r["amount"] >= ONE_OFF_FROM:
                    big.append((r["description"], r["amount"], r["card"]))
        cards = [r[0] for r in conn.execute("SELECT DISTINCT c.alias FROM card_lines l JOIN cards c ON c.id=l.card_id WHERE substr(l.cycle,1,7)=?", (m,))]
        out["by_month"][m] = {"kinds": dict(kinds), "categories": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
                              "merchants": sorted(merchants.items(), key=lambda kv: -kv[1])[:6], "big": big, "cards": cards}
    for r in conn.execute("SELECT c.alias, s.statement_date, s.lines_status, s.lines_diff FROM statements s JOIN cards c ON c.id = s.card_id"
                          " WHERE s.statement_date >= ? AND IFNULL(s.lines_status,'') != 'cocok' ORDER BY s.statement_date",
                          ((months[0] + "-01") if months else "0000",)):
        (out["missing"] if r["lines_status"] in (None, "tanpa-berkas") else out["mismatch"]).append((r["alias"], r["statement_date"], r["lines_diff"]))
    return out


def format_summary(s: dict) -> str:
    if not s["months"]:
        return "Belum ada baris tagihan kartu yang terbaca."
    lines = []
    for m in s["months"]:
        d = s["by_month"][m]
        k = d["kinds"]
        lines.append(f"SIKLUS {m} ({len(d['cards'])} kartu): belanja {format_idr(k.get('belanja', 0))}; langganan {format_idr(k.get('langganan', 0))}; "
                     f"cicilan {format_idr(k.get('cicilan', 0))}; bunga {format_idr(k.get('bunga', 0))}; biaya {format_idr(k.get('biaya', 0))}; "
                     f"refund {format_idr(-k.get('refund', 0))}; dibayar {format_idr(-k.get('pembayaran', 0))}")
        if d["categories"]:
            lines.append("  belanja per kategori: " + "; ".join(f"{c} {format_idr(v)}" for c, v in d["categories"].items()))
        if d["merchants"]:
            lines.append("  merchant terbesar: " + "; ".join(f"{n.title()} {format_idr(v)}" for n, v in d["merchants"]))
        for desc, amt, card in d["big"]:
            lines.append(f"  pembelian besar sekali: {desc[:50]} {format_idr(amt)} ({card})")
    if s["missing"]:
        lines.append("Tagihan tanpa berkas (barisnya tidak terbaca): " + ", ".join(f"{a} {d}" for a, d, _ in s["missing"]))
    if s["mismatch"]:
        lines.append("Tagihan yang barisnya belum cocok dengan total (angka per kategori bisa kurang): "
                     + ", ".join(f"{a} {d} selisih {format_idr(abs(x or 0))}" for a, d, x in s["mismatch"]))
    lines.append("Arti: 'belanja' = pembelian yang bisa diatur; langganan, cicilan, bunga, dan biaya dipisah. Angka dihitung kode dari baris tagihan.")
    return "\n".join(lines)
