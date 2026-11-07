"""Self-checks on every payday plan and simulation: properties that hold for ANY input when the arithmetic is right.
A violation can only be a bug, so the numbers are refused (CalculationError) instead of being shown to the owner.

Plan: what is transferred plus the bank's admin fees plus the cash kept equals the salary; every amount is a positive whole
rupiah; a fee belongs to one paid item (or the living money moved), once; nothing is paid above a bill; the living money is
never used for saving-type items (emergency fund, pot, card balance above the minimum, savings); with a leftover the owner
reported, salary part + leftover = the living money; a shortfall is never reported for money that was paid.
Simulation: per cycle nothing is negative and no more than the bill is paid; the card balances add up over the whole run
(open bills + new charges + gaps + interest - payments - payments from outside the salary = what is left); a pot never
exceeds its target."""
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
    fees = snap.get("fees") or []      # plans stored before admin fees were counted have none
    fee = sum(f["amount"] for f in fees)
    if paid + fee + snap["cash_to_hold"] != snap["salary"]:
        errs.append(f"transfer {paid} + biaya admin {fee} + kas {snap['cash_to_hold']} != gaji {snap['salary']}")
    if snap["cash_to_hold"] < 0:
        errs.append("kas ditahan negatif")
    for t in snap["transfers"]:
        if not _whole(t["amount"]) or t["amount"] <= 0:
            errs.append(f"transfer {t['to_alias']} tidak valid: {t['amount']!r}")
    lt = snap.get("living_transfer") or {}
    paid_to = {t["to_alias"] for t in snap["transfers"]} | ({lt.get("to_alias")} if lt.get("amount") else set())
    for f in fees:
        if not _whole(f["amount"]) or f["amount"] <= 0:
            errs.append(f"biaya admin {f['to_alias']} tidak valid: {f['amount']!r}")
        if f["to_alias"] not in paid_to:
            errs.append(f"biaya admin {f['to_alias']} tanpa transfer")
    if len({f["to_alias"] for f in fees}) != len(fees):
        errs.append("biaya admin tercatat dua kali untuk satu tujuan")
    for u in snap["unfunded"]:
        if not _whole(u["amount"]) or u["amount"] <= 0:
            errs.append(f"belum terdanai {u['to_alias']} tidak valid: {u['amount']!r}")
    reserve = snap.get("reserve") or 0
    if reserve and any(t["reason"] in ABOVE_RESERVE_REASONS for t in snap["transfers"]) and snap["cash_to_hold"] < reserve:
        errs.append(f"uang harian terpotong: ditahan {snap['cash_to_hold']} < {reserve}")
    held = snap.get("living_leftover") or 0
    if held:     # the owner's leftover + what the salary gives = the living money, and he is told to move his own figure
        if reserve + held != snap.get("living_normal"):
            errs.append(f"uang harian: dari gaji {reserve} + sisa {held} != {snap.get('living_normal')}")
        lt = snap.get("living_transfer")
        if lt and lt.get("also_move") != held:
            errs.append(f"sisa uang harian yang dipindah {lt.get('also_move')} != sisa yang dicatat {held}")
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
        for key in ("cash", "due", "paid", "balance", "interest", "ef", "pot", "free", "short", "new", "outside", "fees", "once"):
            if not _whole(row[key]) or row[key] < 0:
                errs.append(f"{row['month']}: {key} tidak valid: {row[key]!r}")
        if row["paid"] > row["due"]:
            errs.append(f"{row['month']}: kartu dibayar {row['paid']} > tagihan {row['due']}")
        if row["cash"] != row["ef"] + row["pot"] + row["paid"] + row["free"]:
            errs.append(f"{row['month']}: kas tidak habis terbagi")
    left = r["start_balance"] + sum(x["new"] + x["short"] + x["interest"] - x["paid"] - x["outside"] for x in r["rows"])
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
