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
_DATES_ONLY = re.compile(rf"^\s*(?P<d1>{_DATE})\s+(?P<d2>{_DATE})\s*$")
# a line whose amount the number masking swallowed: "13-Feb-26 13-Feb-26 Telkomsel [[NUM:****8223]],514.00"
_MASKED = re.compile(rf"^\s*(?P<d1>{_DATE})\s+(?P<d2>{_DATE})\s+(?P<desc>.+?)\s*\[\[NUM:\*+\d{{4}}\]\],(?P<tail>\d{{3}})(?:\.\d{{2}})?\s*(?P<cr>CR)?\s*$", re.I)
# foreign purchases on some cards: "ANTHROPIC* CLAUDE SUB ANTHROPIC.COMUSA 364,119" with the dates on the next line
_NODATE = re.compile(r"^\s*(?P<desc>[A-Za-z].*?)\s+(?:Rp\.?\s*)?(?P<amt>\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s*(?P<cr>CR)?\s*$", re.I)
_SUMMARY = re.compile(r"total|sub ?-?t ?o ?t ?a ?l|tagihan|sebelumnya|batas|limit|minimum|saldo|poin|pagu|payments", re.I)
ONE_OFF_FROM = 1_500_000            # a single purchase this big is shown apart: it distorts any monthly average

# card merchants -> category. The owner's own words (category_keywords) are checked before these.
CARD_RULES: list[tuple[str, str]] = [
    ("langganan", r"netflix|spotify|youtube|disney|apple\.com|itunes|google ?(one|g1)|icloud|canva|openai|chatgpt|anthropic|"
                  r"claude|microsoft|msbill|catchplay|gopro|sqsp|squarespace|\baws\b|amazon web|rockstar ?gym|coway|telkomsel|cursor"),
    ("game-digital", r"steam|playstation|\bpsn\b|nintendo|xbox|google ?play|garena|codashop|unipin|mobile ?legends"),
    ("top-up e-wallet", r"gopay|\bovo\b|\bdana\b|shopeepay|linkaja"),
    ("belanja-online", r"tokopedia|shopee|lazada|blibli|bukalapak|tiktok|zalora|alp\*|alipay|aliexpress|amazon(?! web)|\btemu\b"),
    ("kesehatan", r"halodoc|apotek|apotik|klinik|rumah ?sakit|hospital|siloam|mandaya|hermina|kimia ?farma|guardian|watsons|century"),
    ("makan", r"restaurant|resto|\besb\b|cafe|coffee|kopi|boost ?juice|food|bakery|starbucks|mcdonald|\bkfc\b|chagee|"
              r"janji ?jiwa|pizza|burger|sushi|bakmi|warung|warteg|soto|steak|sate|\bnasi\b|ayam|bebek|ramen|padang|chatime|fore ?coffee"),
    ("transport", r"\bgrab\b|gojek|pertamina|\bshell\b|\bspbu\b|\bbp\b|vivo ?energy|\btol\b|parkir|bluebird|\bmrt\b|\bkrl\b|kai ?access|petado|\bdidi\b"),
    ("otomotif", r"\bban\b|bengkel|auto ?2000|astra|oli |car ?wash|cuci ?mobil|spare ?part|cemara ?jaya"),
    ("listrik", r"\bpln\b|token ?listrik"),
    ("belanja-harian", r"indomaret|\bidm\b|alfamart|alfamidi|superindo|hypermart|lotte ?mart|ranch ?market|aeon|\bhero\b|grand ?lucky|"
                       r"farmers ?market|transmart|carrefour|\bgiant\b|total ?buah"),
    ("liburan", r"traveloka|tiket\.com|agoda|booking\.com|airbnb|garuda|lion ?air|airasia|citilink|cathay|singapore ?air|scoot|jetstar|"
                r"klook|trip\.com|hotel|airport|weixin|wechat"),
    ("elektronik", r"samsung|erafone|\bibox\b|digimap|electronic ?city|best ?denki|xiaomi|apple ?store"),
    ("pakaian-perawatan", r"adidas|\bnike\b|uniqlo|\bh&m\b|\bzara\b|sociolla|body ?shop|\btbs\b|decathlon|sephora|matahari"),
    ("hobi", r"pop ?mart|gramedia|\blego\b|toys|hobby"),
    ("telepon-internet", r"xl ?axiata|indosat|\bsmartfren\b|\bby\.u\b|biznet|indihome|first ?media"),
]
_PAYMENT = re.compile(r"pembayaran|payment|\bpmt\b|bayar|bi-?fast|transfer|autodebet|cash ?management|livin|m-?bca|klik ?bca", re.I)
CONVERSION_DAYS = 62     # a purchase credited back in full on the same card within this many days: cancelled or turned into instalments
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
    raw = [ln for ln in text.splitlines() if ln.strip()]
    out = []
    for i, line in enumerate(raw):
        m = _LINE.match(line)
        if m:
            desc = " ".join(m.group("desc").split())
            if len(re.findall(r"[A-Za-z]", desc)) < 2 or desc.lower().startswith("rp"):
                continue                                       # summary rows ("Rp. 2,386,662 Rp. 201,221"), page markers
            amount = parse_amount(m.group("amt"))
            if amount:
                out.append({"txn_date": _date(m.group("d1"), cycle, month_first), "description": desc[:120],
                            "amount": -amount if m.group("cr") else amount})
            continue
        m = _MASKED.match(line)
        if m:
            out.append({"txn_date": _date(m.group("d1"), cycle, month_first), "description": " ".join(m.group("desc").split())[:120],
                        "amount": None, "tail": m.group("tail"), "credit": bool(m.group("cr"))})
            continue
        m = _NODATE.match(line)
        if m and not _SUMMARY.search(m.group("desc")):
            nxt = _DATES_ONLY.match(raw[i + 1]) if i + 1 < len(raw) else None
            if nxt:
                amount = parse_amount(m.group("amt"))
                if amount:
                    out.append({"txn_date": _date(nxt.group("d1"), cycle, month_first), "description": " ".join(m.group("desc").split())[:120],
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
    masked = [x for x in lines if x.get("amount") is None]
    lines = [x for x in lines if x.get("amount") is not None]
    notes = []
    diff = reconcile(lines, st)
    tol = _tolerance(lines)
    # 1. one line whose amount the masking swallowed: the gap IS its amount, when the visible last digits agree
    if len(masked) == 1 and abs(diff) > tol:
        x, gap = masked[0], -diff
        if (gap < 0) == x["credit"] and f"{abs(gap):d}".endswith(x["tail"]):
            lines.append({"txn_date": x["txn_date"], "description": x["description"], "amount": gap})
            diff, notes = reconcile(lines, st), notes + ["satu nominal yang tersamar dipulihkan dari selisih total"]
    # 2. payments the card only shows as a summary ("TOTAL PAYMENTS"): take them from the statement itself
    paid_lines = -sum(x["amount"] for x in lines if x["amount"] < 0 and classify(x["description"], x["amount"]) == "pembayaran")
    missing_paid = st["payments"] - paid_lines
    if missing_paid > 0 and abs(diff - missing_paid) <= tol:
        lines.append({"txn_date": None, "description": "Pembayaran (dari ringkasan tagihan)", "amount": -missing_paid})
        diff, notes = reconcile(lines, st), notes + ["pembayaran diambil dari ringkasan tagihan"]
    # 3. an instalment line that cannot be read: fill it from the card's known instalments when it fits exactly
    if abs(diff) > tol and diff < 0:
        for a in card_installments.active(conn) + _all_instalments(conn, st["card_id"]):
            if a["card"] == st["card"] and abs(-diff - a["per_month"]) <= tol:
                lines.append({"txn_date": None, "description": f"{a['description']} (dari daftar cicilan)", "amount": a["per_month"]})
                diff, notes = reconcile(lines, st), notes + ["satu baris cicilan diisi dari daftar cicilan"]
                break
    ok = abs(diff) <= _tolerance(lines)
    conn.execute("DELETE FROM card_lines WHERE statement_id=?", (statement_id,))
    # an instalment printed without the words "cicilan" or "x/y" (e.g. "MID*Tokopedia", "IPREG...") is recognised by its exact
    # amount: the same card, the same rupiah as one of its recorded instalments; each instalment matches one line at most
    plans = [a["per_month"] for a in _all_instalments(conn, st["card_id"]) if a["per_month"] >= 50_000]
    kinds = [classify(x["description"], x["amount"]) for x in lines]
    for x, kind in zip(lines, kinds):
        if kind == "cicilan" and x["amount"] in plans:
            plans.remove(x["amount"])          # printed as an instalment already: it cannot also claim a purchase
    for x, kind in zip(lines, kinds):
        if kind == "belanja" and x["amount"] in plans:
            plans.remove(x["amount"])
            kind = "cicilan"
        cat = categorize(conn, x["description"]) if kind == "belanja" else kind
        if kind == "belanja" and cat == "langganan":
            kind = "langganan"
        conn.execute("INSERT INTO card_lines(statement_id,card_id,cycle,txn_date,description,amount,kind,category) VALUES (?,?,?,?,?,?,?,?)",
                     (statement_id, st["card_id"], st["statement_date"], x["txn_date"], x["description"], x["amount"], kind, cat))
    conn.execute("UPDATE statements SET lines_status=?, lines_diff=? WHERE id=?", ("cocok" if ok else "selisih", diff, statement_id))
    conn.commit()
    return {"lines": len(lines), "status": "cocok" if ok else "selisih", "diff": diff, "note": "; ".join(notes)}


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

def _netted(conn) -> set[int]:
    """Ids of purchases credited back in full on the same card within CONVERSION_DAYS (cancelled, returned or converted
    into instalments), and of those credits. Counting both would inflate purchases and refunds alike."""
    rows = conn.execute("SELECT id, card_id, amount, kind, COALESCE(txn_date, cycle) d FROM card_lines"
                        " WHERE kind IN ('belanja','langganan','refund') ORDER BY d, id").fetchall()
    credits = [r for r in rows if r["kind"] == "refund"]
    out: set[int] = set()
    for b in (r for r in rows if r["amount"] > 0):
        for c in credits:
            if c["id"] in out or c["card_id"] != b["card_id"] or c["amount"] != -b["amount"]:
                continue
            gap = (date.fromisoformat(c["d"][:10]) - date.fromisoformat(b["d"][:10])).days
            if 0 <= gap <= CONVERSION_DAYS:
                out.update((b["id"], c["id"]))
                break
    return out


def _card(conn, card_alias: str):
    row = conn.execute("SELECT id, alias, bank, last4 FROM cards WHERE alias=?", (card_alias,)).fetchone()
    if row is None:
        raise ValueError(f"kartu {card_alias} belum terdaftar (lihat ringkasan_data)")
    return row


def summary(conn, cycles: int = 3, card_alias: str | None = None) -> dict:
    """Per statement cycle, all cards together, or one card with `card_alias`."""
    if card_alias is not None:
        _card(conn, card_alias)
    where, args = ("", ()) if card_alias is None else (" AND c.alias = ?", (card_alias,))
    months = [r[0] for r in conn.execute("SELECT DISTINCT substr(l.cycle,1,7) m FROM card_lines l JOIN cards c ON c.id = l.card_id"
                                         f" WHERE 1=1{where} ORDER BY m DESC LIMIT ?", (*args, max(1, cycles)))]
    months.sort()
    out = {"months": months, "by_month": {}, "missing": [], "mismatch": [], "card": card_alias}
    netted = _netted(conn)
    for m in months:
        rows = conn.execute("SELECT l.*, c.alias AS card FROM card_lines l JOIN cards c ON c.id = l.card_id WHERE substr(l.cycle,1,7)=?"
                            + where, (m, *args)).fetchall()
        kinds, cats, merchants, big = defaultdict(int), defaultdict(int), defaultdict(int), []
        cancelled = 0
        for r in rows:
            if r["id"] in netted:
                cancelled += max(0, r["amount"])
                continue
            kinds[r["kind"]] += r["amount"]
            if r["kind"] == "belanja":
                cats[r["category"]] += r["amount"]
                key = re.sub(r"[\d#*\[\]:]+", " ", r["description"]).split()
                merchants[" ".join(key[:3]).upper()] += r["amount"]
                if r["amount"] >= ONE_OFF_FROM:
                    big.append((r["description"], r["amount"], r["card"]))
        cards = [r[0] for r in conn.execute("SELECT DISTINCT c.alias FROM card_lines l JOIN cards c ON c.id=l.card_id WHERE substr(l.cycle,1,7)=?"
                                            + where, (m, *args))]
        out["by_month"][m] = {"kinds": dict(kinds), "categories": dict(sorted(cats.items(), key=lambda kv: -kv[1])),
                              "merchants": sorted(merchants.items(), key=lambda kv: -kv[1])[:6], "big": big, "cards": cards,
                              "cancelled": cancelled}
    for r in conn.execute("SELECT c.alias, s.statement_date, s.lines_status, s.lines_diff FROM statements s JOIN cards c ON c.id = s.card_id"
                          f" WHERE s.statement_date >= ? AND IFNULL(s.lines_status,'') != 'cocok'{where} ORDER BY s.statement_date",
                          ((months[0] + "-01") if months else "0000", *args)):
        (out["missing"] if r["lines_status"] in (None, "tanpa-berkas") else out["mismatch"]).append((r["alias"], r["statement_date"], r["lines_diff"]))
    return out


def format_summary(s: dict) -> str:
    if not s["months"]:
        return "Belum ada baris tagihan kartu yang terbaca" + (f" untuk {s['card']}." if s.get("card") else ".")
    lines = []
    for m in s["months"]:
        d = s["by_month"][m]
        k = d["kinds"]
        lines.append(f"SIKLUS {m} ({len(d['cards'])} kartu): belanja {format_idr(k.get('belanja', 0))}; langganan {format_idr(k.get('langganan', 0))}; "
                     f"cicilan {format_idr(k.get('cicilan', 0))}; bunga {format_idr(k.get('bunga', 0))}; biaya {format_idr(k.get('biaya', 0))}; "
                     f"refund {format_idr(-k.get('refund', 0))}; dibayar {format_idr(-k.get('pembayaran', 0))}")
        if d.get("cancelled"):
            lines.append(f"  dibatalkan/dikonversi ke cicilan (belanja yang dikreditkan balik, tidak dihitung): {format_idr(d['cancelled'])}")
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


DETAIL_MAX = 60                      # lines listed for one statement; the rest is summed
_LONG_DIGITS = re.compile(r"\d{6,}")
_KIND_ORDER = ("belanja", "langganan", "cicilan", "bunga", "biaya", "refund", "pembayaran")


def card_detail(conn, card_alias: str, month: str | None = None) -> dict:
    """Every line of one card's statement: the latest one, or the one printed in `month` (YYYY-MM)."""
    card = _card(conn, card_alias)
    if month is not None and not re.fullmatch(r"20\d\d-(0[1-9]|1[0-2])", month):
        raise ValueError("bulan: format YYYY-MM (bulan cetak tagihan)")
    st = conn.execute("SELECT * FROM statements WHERE card_id=? AND (? IS NULL OR substr(statement_date,1,7) = ?)"
                      " ORDER BY statement_date DESC, id DESC LIMIT 1", (card["id"], month, month)).fetchone()
    if st is None:
        return {"card": dict(card), "statement": None, "lines": [], "month": month}
    netted = _netted(conn)
    rows = conn.execute("SELECT * FROM card_lines WHERE statement_id=? ORDER BY COALESCE(txn_date, cycle), id", (st["id"],)).fetchall()
    return {"card": dict(card), "statement": dict(st), "month": month,
            "lines": [{"date": r["txn_date"], "description": _LONG_DIGITS.sub("[angka]", r["description"])[:50], "amount": r["amount"],
                       "kind": r["kind"], "category": r["category"], "netted": r["id"] in netted} for r in rows]}


def format_detail(d: dict) -> str:
    c, st = d["card"], d["statement"]
    name = f"{c['bank']} …{c['last4']} ({c['alias']})"
    if st is None:
        return f"{name}: belum ada tagihan tersimpan" + (f" yang dicetak {d['month']}." if d["month"] else ".")
    read = {"cocok": "semua baris terbaca dan cocok dengan total tagihan",
            "selisih": f"baris BELUM cocok dengan total (selisih {format_idr(abs(st['lines_diff'] or 0))}): daftar ini bisa kurang",
            "tanpa-berkas": "berkas tagihan tidak ada, baris tidak terbaca"}.get(st["lines_status"] or "", "baris belum dibaca")
    out = [f"TAGIHAN {name}: cetak {st['statement_date']}, jatuh tempo {st['due_date']}, total {format_idr(st['total_due'])}, "
           f"minimum {format_idr(st['minimum_due'])}" + (f", sudah dibayar {format_idr(st['paid_amount'])}" if st["paid_amount"] else "")
           + f"; {read}."]
    kinds: dict[str, int] = defaultdict(int)
    for x in d["lines"]:
        if not x["netted"]:
            kinds[x["kind"]] += x["amount"]
    if kinds:
        out.append("Per jenis: " + "; ".join(f"{'dibayar' if k == 'pembayaran' else k} {format_idr(abs(kinds[k]))}"
                                              for k in _KIND_ORDER if kinds.get(k)))
    for x in d["lines"][:DETAIL_MAX]:
        out.append(f"- {x['date'] or 'tanpa tanggal'} | {x['description']} | {format_idr(abs(x['amount']))}"
                   + (" kredit" if x["amount"] < 0 else "") + f" | {x['kind']}" + (f" ({x['category']})" if x["kind"] == "belanja" else "")
                   + (" | dibatalkan/dikonversi ke cicilan, tidak dihitung" if x["netted"] else ""))
    rest = d["lines"][DETAIL_MAX:]
    if rest:
        out.append(f"... dan {len(rest)} baris lain: tagihan {format_idr(sum(x['amount'] for x in rest if x['amount'] > 0))}, "
                   f"kredit {format_idr(-sum(x['amount'] for x in rest if x['amount'] < 0))}")
    out.append("Angka dibaca kode dari baris tagihan; nomor panjang disamarkan.")
    return "\n".join(out)
