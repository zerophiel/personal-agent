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
    ("biaya-bank", r"biaya (transaksi|transfer|admin|adm|layanan|materai)|pajak bunga|admin fee"),
    ("wajib:kartu", r"pembayaran (kartu kredit|hsbc|dbs|ex ?- ?anz|anz|mega|cimb|citibank|uob|bni|bri kartu|kartu)\b|bayar kartu"),
    ("wajib:spaylater", r"spaylater|shopee ?pay ?later|paylater|kredivo|akulaku"),
    ("wajib:cicilan", r"pendebitan otomatis|auto ?coll|autodebet|autodebit|angsuran|cicilan"),
    ("belanja-online", r"tokopedia|shopee|lazada|bukalapak|blibli|tiktok ?shop"),
    ("transport", r"\bgrab\b|gojek|go-?jek|pertamina|spbu|\bshell\b|e-?toll|\btol\b|parkir|kai access|transjakarta|\bmrt\b|bluebird"),
    ("makan", r"restaurant|restoran|\bresto\b|\bcafe\b|kafe|coffee|kopi|bakmi|warung|gado|mcdonald|\bkfc\b|starbucks|"
              r"yakiniku|sushi|ayam|bakso|pizza|burger|bakery|roti|\bfood\b|kantin|mie "),
    ("langganan", r"netflix|spotify|youtube|disney|apple\.com|google (one|play)|icloud|canva|openai|chatgpt"),
    ("belanja-harian", r"indomaret|alfamart|alfamidi|superindo|hypermart|lotte ?mart|ranch market|farmers"),
    ("kesehatan", r"apotek|apotik|klinik|rumah sakit|kimia farma|guardian|halodoc"),
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


def suggest_category(normalized: str, amount: int, owners: list[str]) -> str | None:
    if "transfer" in normalized and any(o in normalized for o in owners):
        return "transfer_internal"                      # sent to the owner's own name
    for cat, rx in (CREDIT_RULES if amount > 0 else DEBIT_RULES):
        if re.search(rx, normalized):
            return cat
    return None


def groups(conn) -> dict[str, dict]:
    """Uncategorized rows grouped by normalized descriptor: count, total in/out, and the suggestion."""
    owners = owner_names(conn)
    out: dict[str, dict] = defaultdict(lambda: {"n": 0, "out": 0, "in": 0, "cats": defaultdict(int)})
    for r in conn.execute("SELECT merchant, amount FROM transactions WHERE source IN ('mutation','receipt')"
                          " AND category IS NULL AND merged_into IS NULL"):
        key = normalize(r["merchant"])
        g = out[key]
        g["n"] += 1
        g["out" if r["amount"] < 0 else "in"] += abs(r["amount"])
        cat = suggest_category(key, r["amount"], owners)
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
