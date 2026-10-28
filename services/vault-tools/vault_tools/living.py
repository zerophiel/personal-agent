"""Living-cost analysis: what the owner really spends day to day, and a `living_reserve` to plan with.

Counts, per complete month and summed across ALL own accounts (the main account moved from BCA to Mandiri), the
categorized day-to-day outflows. Excluded: obligations ('wajib:'), pot deposits ('sinking:'), one-offs ('sekali:')
and moves between own accounts ('transfer_internal'). Credit-card spending is not in the account mutations (only its
repayment is), so it is shown separately from the stored card statements. A month counts only if enough of its money
out is categorized; otherwise it is listed but left out, and the output says so."""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import median

from .health import is_discretionary
from .money import format_idr
from .tools import get_threshold, id_holidays, last_working_day, sinking_required

MIN_COVERAGE_PCT = 80      # share of a month's money out that must be categorized for the month to count
MARGIN_PCT = 10            # recommended reserve = median + 10%
DEFAULT_MONTHS = 6


def _round_up(value: int, step: int = 1000) -> int:
    return -(-value // step) * step


def monthly(conn, today: date) -> dict[str, dict]:
    """{month: {cash, excluded, uncategorized, total_out, coverage_pct, income_salary}} for complete months only."""
    this_month = f"{today.year}-{today.month:02d}"
    out: dict[str, dict] = defaultdict(lambda: {"cash": 0, "excluded": 0, "ended": 0, "uncategorized": 0, "total_out": 0, "salary_in": 0})
    for r in conn.execute("SELECT substr(txn_date,1,7) m, category, amount FROM transactions"
                          " WHERE source IN ('mutation','receipt') AND merged_into IS NULL AND substr(txn_date,1,7) < ?", (this_month,)):
        row = out[r["m"]]
        if r["amount"] < 0:
            v = -r["amount"]
            row["total_out"] += v
            if r["category"] is None:
                row["uncategorized"] += v
            elif r["category"].startswith("berhenti:"):
                row["ended"] += v         # a recurring cost that no longer exists: out of the forward-looking reserve
            elif is_discretionary(r["category"]):
                row["cash"] += v
            else:
                row["excluded"] += v
        elif r["category"] == "gaji":
            row["salary_in"] += r["amount"]
    for row in out.values():
        row["coverage_pct"] = 100 if not row["total_out"] else (row["total_out"] - row["uncategorized"]) * 100 // row["total_out"]
    return dict(sorted(out.items()))


def card_charges(conn) -> dict[str, int]:
    """New card spending per statement month, from the stored statements (the 'charges' line)."""
    out: dict[str, int] = defaultdict(int)
    for r in conn.execute("SELECT substr(statement_date,1,7) m, charges FROM statements"):
        out[r["m"]] += r["charges"]
    return dict(sorted(out.items()))


def commitments(conn, today: date) -> dict:
    hol = id_holidays(today.year) | id_holidays(today.year + 1) | id_holidays(today.year + 2)
    payday = last_working_day(today.year, today.month, hol)
    fixed = conn.execute("SELECT COALESCE(SUM(amount),0) FROM fixed_expenses").fetchone()[0]
    inst = conn.execute("SELECT COALESCE(SUM(installment),0) FROM debts WHERE tenor_left > 0").fetchone()[0]
    pot = sum(sinking_required(conn, f, payday, hol)["per_month"] for f in conn.execute("SELECT * FROM sinking_funds"))
    return {"fixed": fixed, "installments": inst, "pot": pot, "total": fixed + inst + pot}


def analyse(conn, today: date, from_month: str | None = None, months: int = DEFAULT_MONTHS) -> dict:
    data = monthly(conn, today)
    if from_month:
        data = {m: v for m, v in data.items() if m >= from_month}
    else:
        data = dict(list(data.items())[-months:])
    counted = {m: v for m, v in data.items() if v["total_out"] and v["coverage_pct"] >= MIN_COVERAGE_PCT}
    skipped = {m: v for m, v in data.items() if m not in counted}
    values = [v["cash"] for v in counted.values()]
    res = {"months": data, "counted": sorted(counted), "skipped": sorted(skipped), "cards": card_charges(conn),
           "enough": len(values) >= 2, "tight": None, "recommended": None, "loose": None}
    if values:
        base = int(median(values))
        res.update({"tight": _round_up(base), "recommended": _round_up(base * (100 + MARGIN_PCT) // 100), "loose": _round_up(max(values))})
    res["salary"] = get_threshold(conn, "net_salary")
    res["commitments"] = commitments(conn, today)
    from . import card_lines
    res["card_lines"] = card_lines.summary(conn, 3)
    # No "monthly free" here any more: subtracting total card charges (which already hold instalments, subscriptions,
    # interest and one-off purchases such as a school fee) from the salary next to the commitments double counted and
    # produced a false deficit. The simulator computes the monthly picture from its parts.
    res["current_reserve"] = get_threshold(conn, "living_reserve")
    return res


def format_analysis(a: dict) -> str:
    lines = ["Analisis biaya hidup (belanja harian dari semua rekening milik sendiri)"]
    if not a["months"]:
        return lines[0] + "\nBelum ada mutasi bulan penuh. Unggah mutasi (mis. Januari sampai bulan lalu) lalu kategorikan."
    for m, v in a["months"].items():
        mark = "dihitung" if m in a["counted"] else f"DILEWATI (baru {v['coverage_pct']}% dikategorikan)"
        sal = f"; gaji masuk {format_idr(v['salary_in'])}" if v["salary_in"] else ""
        if v["ended"]:
            sal += f"; biaya yang sudah berhenti {format_idr(v['ended'])} (tidak dihitung)"
        lines.append(f"- {m}: biaya hidup kas {format_idr(v['cash'])}; kewajiban/sekali/antar-rekening {format_idr(v['excluded'])}; "
                     f"belum dikategorikan {format_idr(v['uncategorized'])}{sal}; {mark}")
    if a["skipped"]:
        lines.append(f"Catatan: {len(a['skipped'])} bulan belum cukup rapi dikategorikan (minimal {MIN_COVERAGE_PCT}%): "
                     f"{', '.join(a['skipped'])}. Kategorikan dulu agar hasilnya lebih akurat.")
    if a["recommended"] is None:
        lines.append("Belum bisa merekomendasikan living_reserve: belum ada bulan yang cukup dikategorikan.")
    else:
        flag = "" if a["enough"] else " (BARU 1 BULAN DATA: anggap sementara)"
        lines.append(f"Biaya hidup kas per bulan, dari {len(a['counted'])} bulan{flag}: ketat {format_idr(a['tight'])} (median), "
                     f"disarankan {format_idr(a['recommended'])} (median + {MARGIN_PCT}%), longgar {format_idr(a['loose'])} (bulan tertinggi)")
    cl = a.get("card_lines") or {"months": []}
    if cl["months"]:
        parts = []
        for m in cl["months"]:
            k = cl["by_month"][m]["kinds"]
            parts.append(f"{m}: belanja {format_idr(k.get('belanja', 0))}, langganan {format_idr(k.get('langganan', 0))}, "
                         f"cicilan {format_idr(k.get('cicilan', 0))}, bunga+biaya {format_idr(k.get('bunga', 0) + k.get('biaya', 0))}")
        lines.append("Kartu kredit per siklus (dari baris tagihan): " + "; ".join(parts) + ". Rincian: belanja_kartu.")
    elif a["cards"]:
        lines.append("Total tagihan baru kartu per siklus (SUDAH termasuk cicilan, langganan, bunga dan pembelian sekali; "
                     "jangan dikurangkan dari gaji): " + "; ".join(f"{m} {format_idr(v)}" for m, v in list(a["cards"].items())[-6:]))
    lines.append("Sisa bulanan dan arah utang kartu: pakai simulasi_skenario (dihitung dari komponennya, tanpa hitung ganda).")
    if a["salary"] is None:
        lines.append("net_salary belum diset.")
    if a["current_reserve"] is not None:
        lines.append(f"living_reserve yang berlaku sekarang: {format_idr(a['current_reserve'])}")
    if a["recommended"] is not None:
        lines.append("Untuk memakai angka ini, minta persetujuan pemilik lalu set_threshold living_reserve.")
    return "\n".join(lines)
