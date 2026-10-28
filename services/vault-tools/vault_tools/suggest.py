"""Category suggestions for bank mutation rows: transparent keyword rules, nothing applied without the owner's
approval. Rows are grouped by their normalized descriptor, so one decision covers every repeat of it.

Categories used by the planner: 'wajib:<x>' obligations, 'sinking:<fund>' pot deposits, 'sekali:<x>' one-offs,
'transfer_internal' moves between the owner's own accounts, anything else is day-to-day spending."""
from __future__ import annotations

import re
import sqlite3
from collections import defaultdict

from .money import format_idr
from .mutations import normalize, set_category_rule

# (category, regex on the normalized descriptor). First match wins, so order matters.
DEBIT_RULES: list[tuple[str, str]] = [
    # bank fees first: "Biaya transaksi bank Pembayaran HSBC" must not be read as a card payment
    ("biaya-bank", r"biaya (transaksi|txn|transfer|admin|adm|layanan|materai)|pajak bunga|admin fee"),
    ("wajib:kartu", r"pembayaran (kartu kredit|hsbc|dbs|ex ?- ?anz|anz|mega|cimb|citibank|uob|bni|bri kartu|kartu)\b|bayar kartu|"
                    r"kartu kredit/pl|\bbca card\b|credit card payment"),
    ("wajib:spaylater", r"spaylater|shopee ?pay ?later|paylater|kredivo|akulaku"),
    ("wajib:cicilan", r"pendebitan otomatis|auto ?coll|autodebet|autodebit|angsuran|cicilan"),
    ("wajib:ipl", r"riviera|\bipl\b"),
    ("wajib:sekolah", r"ipeka|sekolah|\bschool\b"),
    ("wajib:asuransi", r"avrist|allianz|prudential|manulife|\baxa\b|asuransi|\bpremi\b"),   # debits only; credits are payouts/commission
    ("liburan", r"traveloka|tiket\.com|agoda|booking\.com|airbnb|garuda|lion air|airasia"),
    ("belanja-online", r"tokopedia|shopee|lazada|bukalapak|blibli|tiktok ?shop"),
    ("transport", r"\bgrab\b|gojek|go-?jek|pertamina|spbu|\bshell\b|e-?toll|\btol\b|parkir|kai access|transjakarta|\bmrt\b|bluebird|"
                  r"flazz|e-?money|brizzi|tapcash"),
    ("makan", r"restaurant|restoran|\bresto\b|\bcafe\b|kafe|coffee|kopi|bakmi|warung|gado|mcdonald|\bkfc\b|starbucks|"
              r"yakiniku|sushi|ayam|bakso|pizza|burger|bakery|roti|\bfood\b|kantin|mie "),
    ("langganan", r"netflix|spotify|youtube|disney|apple\.com|google (one|play)|icloud|canva|openai|chatgpt"),
    ("belanja-harian", r"indomaret|alfamart|alfamidi|superindo|hypermart|lotte ?mart|ranch market|farmers"),
    ("kesehatan", r"apotek|apotik|klinik|rumah sakit|\brs\b|\bhos(pital)?\b|siloam|mandaya|hermina|kimia farma|guardian|halodoc"),
    ("donasi", r"kolekt|katedral|gereja|paroki|\bpgdp\b|persembahan|zakat|infaq"),
    ("utilitas", r"\bpln\b|listrik|pdam|indihome|telkom|biznet|pulsa|paket data"),
]
CREDIT_RULES: list[tuple[str, str]] = [
    ("gaji", r"gaji|payroll|salary"),
    ("bunga", r"\bbunga\b"),
    ("sekali:jht", r"\bjht\b|bpjs ketenagakerjaan"),
]


def add_owner_name(conn: sqlite3.Connection, name: str) -> str:
    n = " ".join(name.lower().split())
    if len(n) < 4:
        raise ValueError("nama terlalu pendek (minimal 4 huruf)")
    conn.execute("INSERT OR IGNORE INTO owner_names(name) VALUES (?)", (n,))
    conn.commit()
    return f"nama pemilik '{n}' tersimpan; transfer ke nama ini diusulkan sebagai transfer_internal"


def owner_names(conn) -> list[str]:
    return [r["name"] for r in conn.execute("SELECT name FROM owner_names")]


_FEE = re.compile(r"biaya (transaksi|txn|transfer|admin|adm|layanan|materai)|pajak bunga|admin fee|"
                  r"transfer fee|tax on interest")
_INTEREST = re.compile(r"\binterest\b|\bbunga\b")
_CARD_WORDS = re.compile(r"kartu kredit|credit card|\bbca card\b|\bcard\b")
_POCKET_MOVE = re.compile(r"pocket.*(movement|money in|money out|main pocket|between pockets)|movement between|main pocket|"
                          r"top ?up poket|pindahkan poket|\bpoket \d+")


def suggest_category(normalized: str, amount: int, owners: list[str], own_last4: list[str] = ()) -> str | None:
    if _FEE.search(normalized):
        return "biaya-bank"                             # a fee line that mentions a payee is still just a fee
    if _POCKET_MOVE.search(normalized):
        return "transfer_internal"                      # checked before any keyword rule: a pocket NAME ("Gaji Pak Darja") is not the event
    if _INTEREST.search(normalized) and amount > 0:
        return "bunga"                                  # bank interest, tiny and not income from work
    if any(o in normalized for o in owners) and not _CARD_WORDS.search(normalized):
        return "transfer_internal"                      # money to/from the owner's own name (any channel: trsf, switching, BI-Fast)
    if _POCKET_MOVE.search(normalized):
        return "transfer_internal"                      # moves between the owner's Jago pockets
    if any(f"****{l4}" in normalized for l4 in own_last4) and re.search(r"transfer|trsf|switching|bi-?fast|kliring", normalized):
        return "transfer_internal"                      # to/from one of the owner's own accounts, identified by its number
    for cat, rx in (CREDIT_RULES if amount > 0 else DEBIT_RULES):
        if re.search(rx, normalized):
            return cat
    return None


def groups(conn) -> dict[str, dict]:
    """Uncategorized rows grouped by normalized descriptor: count, total in/out, and the suggestion."""
    owners = owner_names(conn)
    own_last4 = [r[0] for r in conn.execute("SELECT last4 FROM accounts WHERE last4 IS NOT NULL AND kind != 'pool' UNION SELECT last4 FROM cards")]   # own accounts and own cards
    out: dict[str, dict] = defaultdict(lambda: {"n": 0, "out": 0, "in": 0, "cats": defaultdict(int)})
    for r in conn.execute("SELECT merchant, amount FROM transactions WHERE source IN ('mutation','receipt')"
                          " AND category IS NULL AND merged_into IS NULL"):
        key = normalize(r["merchant"])
        g = out[key]
        g["n"] += 1
        g["out" if r["amount"] < 0 else "in"] += abs(r["amount"])
        cat = suggest_category(key, r["amount"], owners, own_last4)
        if cat:
            g["cats"][cat] += 1
    for g in out.values():
        g["suggestion"] = max(g["cats"], key=g["cats"].get) if g["cats"] else None
    return out


def suggestions(conn, limit: int = 40) -> list[str]:
    gs = groups(conn)
    with_s = sorted(((k, g) for k, g in gs.items() if g["suggestion"]), key=lambda kv: -(kv[1]["out"] + kv[1]["in"]))
    lines = [f"{k} | {g['n']}x | {format_idr(g['out'] or g['in'])} | usulan: {g['suggestion']}" for k, g in with_s[:limit]]
    rest = [g for g in gs.values() if not g["suggestion"]]
    if rest:
        lines.append(f"({len(rest)} kelompok lain tanpa usulan, total {format_idr(sum(g['out'] + g['in'] for g in rest))}; "
                     f"lihat list_uncategorized dan tanyakan ke pemilik)")
    return lines or ["Tidak ada usulan: semua transaksi sudah dikategorikan atau tidak cocok aturan."]


def apply_suggestions(conn, patterns: list[str] | None = None) -> str:
    """Apply the suggested category for the listed descriptors (None = every suggested group). Only call this
    after the owner has seen the list and agreed."""
    gs = groups(conn)
    wanted = {normalize(p) for p in patterns} if patterns else None
    done = rows = 0
    for key, g in gs.items():
        if not g["suggestion"] or (wanted is not None and key not in wanted):
            continue
        set_category_rule(conn, key, g["suggestion"])
        done += 1
        rows += g["n"]
    return f"{done} kelompok dikategorikan ({rows} transaksi)"
