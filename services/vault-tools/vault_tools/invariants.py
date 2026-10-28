"""Self-checks on every payday plan and simulation: properties that hold for ANY input when the arithmetic is right.
A violation can only be a bug, so the numbers are refused (CalculationError) instead of being shown to the owner.

Plan: what is transferred plus the cash kept equals the salary; every amount is a positive whole rupiah; nothing is paid
above a bill; the living money is never used for saving-type items (emergency fund, pot, card balance above the minimum,
savings); a shortfall is never reported for money that was paid.
Simulation: per cycle nothing is negative and no more than the bill is paid; the card balances add up over the whole run
(open bills + new charges + gaps + interest - payments = what is left); a pot never exceeds its target."""
from __future__ import annotations

ABOVE_RESERVE_REASONS = ("dana darurat", "transfer pool", "setoran pot (sisa setelah kartu)",
                         "tagihan kartu - sisa saldo (bayar penuh)", "tabungan")


class CalculationError(ValueError):
    """The arithmetic broke one of its own rules: never show these numbers."""


def _whole(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def plan_errors(snap: dict, bills: dict[str, int] | None = None) -> list[str]:
    errs = []
    paid = sum(t["amount"] for t in snap["transfers"])
    if paid + snap["cash_to_hold"] != snap["salary"]:
        errs.append(f"transfer {paid} + kas {snap['cash_to_hold']} != gaji {snap['salary']}")
    if snap["cash_to_hold"] < 0:
        errs.append("kas ditahan negatif")
    for t in snap["transfers"]:
        if not _whole(t["amount"]) or t["amount"] <= 0:
            errs.append(f"transfer {t['to_alias']} tidak valid: {t['amount']!r}")
    for u in snap["unfunded"]:
        if not _whole(u["amount"]) or u["amount"] <= 0:
            errs.append(f"belum terdanai {u['to_alias']} tidak valid: {u['amount']!r}")
    reserve = snap.get("reserve") or 0
    if reserve and any(t["reason"] in ABOVE_RESERVE_REASONS for t in snap["transfers"]) and snap["cash_to_hold"] < reserve:
        errs.append(f"uang harian terpotong: ditahan {snap['cash_to_hold']} < {reserve}")
    for alias, owed in (bills or {}).items():
        got = sum(t["amount"] for t in snap["transfers"] if t["to_alias"] == alias)
        short = sum(u["amount"] for u in snap["unfunded"] if u["to_alias"] == alias)
        if got > owed:
            errs.append(f"{alias} dibayar {got} melebihi tagihan {owed}")
        if got + short != owed:
            errs.append(f"{alias}: dibayar {got} + belum terdanai {short} != tagihan {owed}")
    return errs


def simulation_errors(r: dict) -> list[str]:
    errs = []
    for row in r["rows"]:
        for key in ("cash", "due", "paid", "balance", "interest", "ef", "pot", "free", "short", "new"):
            if not _whole(row[key]) or row[key] < 0:
                errs.append(f"{row['month']}: {key} tidak valid: {row[key]!r}")
        if row["paid"] > row["due"]:
            errs.append(f"{row['month']}: kartu dibayar {row['paid']} > tagihan {row['due']}")
        if row["cash"] != row["ef"] + row["pot"] + row["paid"] + row["free"]:
            errs.append(f"{row['month']}: kas tidak habis terbagi")
    left = r["start_balance"] + sum(x["new"] + x["short"] + x["interest"] - x["paid"] for x in r["rows"])
    if r["rows"] and left != r["rows"][-1]["balance"]:
        errs.append(f"saldo kartu tidak seimbang: {left} != {r['rows'][-1]['balance']}")
    for f in r["funds"]:
        total = f["start"] + sum(f["deposits"])
        if total > max(f["target"], f["start"]):
            errs.append(f"pot {f['alias']} melebihi target")
        if f["at_due"] is not None and f["at_due"] > total:
            errs.append(f"pot {f['alias']}: isi pada tenggat melebihi setoran")
    e = r.get("emergency")
    if e and e["saved_end"] > max(e["target"], 0) and r["rows"] and any(x["ef"] for x in r["rows"]):
        errs.append("dana darurat melebihi target")
    return errs


def require(errs: list[str], what: str) -> None:
    if errs:
        raise CalculationError(f"PEMERIKSAAN HITUNGAN GAGAL ({what}); angka tidak ditampilkan. Rincian: " + "; ".join(errs[:5]))
