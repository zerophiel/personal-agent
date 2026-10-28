"""What-if simulator: how the monthly free cash and the card balance move over the next months.

Pure arithmetic over the ledger (no model). One row per pay cycle. Month 1 is the cycle of the coming payday.
Free cash = salary - fixed costs - loan installments - pot deposit - daily cash reserve - card installments
            - recurring card charges (subscriptions) - new card spending + savings from cuts.
Free cash pays the card balances (highest interest first); a negative month adds to the balance instead."""
from __future__ import annotations

from datetime import date

from . import card_installments, subscriptions
from .money import format_idr
from .payday import last_working_day, next_payday
from .roadmap import add_months
from .tools import DEFAULT_CARD_INTEREST_BP, bp_of_idr, get_threshold, id_holidays, sinking_required


def _up_to_1000(x: int) -> int:
    return -(-x // 1000) * 1000


def _first_cycle(today: date) -> date:
    hol = id_holidays(today.year) | id_holidays(today.year + 1)
    p = last_working_day(today.year, today.month, hol)
    return p if p >= today else next_payday(p, hol)


def simulate(conn, today: date, *, belanja_kartu: int = 0, tunda_pot: int = 0, ekstra_sekarang: int = 0,
             hemat: int = 0, reserve: int | None = None, months: int = 12) -> dict:
    salary = get_threshold(conn, "net_salary")
    if not salary:
        raise ValueError("net_salary belum diset")
    months = max(1, min(int(months), 36))
    payday = _first_cycle(today)
    hol = id_holidays(payday.year) | id_holidays(payday.year + 1) | id_holidays(payday.year + 2)
    fixed = conn.execute("SELECT COALESCE(SUM(amount),0) FROM fixed_expenses").fetchone()[0]
    res = reserve if reserve is not None else (get_threshold(conn, "living_reserve") or 0)
    recurring = subscriptions.active_total(conn)
    debts = conn.execute("SELECT installment, tenor_left FROM debts WHERE tenor_left > 0").fetchall()
    inst = card_installments.active(conn)
    funds = conn.execute("SELECT * FROM sinking_funds").fetchall()
    pot_plan = []                       # per fund: (normal per month, number of deposits)
    for f in funds:
        s = sinking_required(conn, f, payday, hol)
        left = max(0, s["remaining"])
        n = -(-left // s["per_month"]) if s["per_month"] else 0
        pot_plan.append((left, s["per_month"], n))
    default_rate = get_threshold(conn, "default_card_interest_bp", DEFAULT_CARD_INTEREST_BP)
    bal, rate = {}, {}
    for r in conn.execute(
            "SELECT c.alias, s.total_due - s.paid_amount AS owed, c.interest_bp_month AS rate FROM statements s JOIN cards c ON c.id = s.card_id"
            " WHERE s.id = (SELECT id FROM statements WHERE card_id = s.card_id ORDER BY statement_date DESC, id DESC LIMIT 1)"):
        if r["owed"] > 0:
            bal[r["alias"]] = r["owed"]
            rate[r["alias"]] = r["rate"] if r["rate"] is not None else default_rate
    start_balance = sum(bal.values())
    first_month = date(payday.year, payday.month, 1)
    rows, interest_total, paid_off = [], 0, None
    for k in range(1, months + 1):
        start = add_months(first_month, k)                      # the month whose dues this cycle pays
        loans = sum(d["installment"] for d in debts if k <= d["tenor_left"])
        cards_inst = sum(a["per_month"] for a in inst if date.fromisoformat(a["ends"]) >= start)
        pot = 0
        for left, per, n in pot_plan:
            if n == 0 or k > n:
                continue                                         # no deposits needed, or the due date has passed
            if tunda_pot == 0:
                pot += per
            elif k > tunda_pot and n > tunda_pot:                # deferred: the same target is spread over fewer deposits
                pot += _up_to_1000(-(-left // (n - tunda_pot)))
        free = salary - fixed - loans - pot - res - cards_inst - recurring - belanja_kartu + hemat
        cap = free + (ekstra_sekarang if k == 1 else 0)
        short = 0
        if cap >= 0:
            pay = cap
            for a in sorted(bal, key=lambda x: -rate[x]):
                take = min(bal[a], pay)
                bal[a] -= take
                pay -= take
        else:
            short = -cap
            if bal:
                top = max(bal, key=lambda x: rate[x])
                bal[top] += short
            else:
                bal["tambahan"] = short
                rate["tambahan"] = default_rate
        month_interest = 0
        for a in list(bal):
            if bal[a] <= 0:
                del bal[a]
            else:
                i = bp_of_idr(bal[a], rate[a])
                bal[a] += i
                month_interest += i
        interest_total += month_interest
        total = sum(bal.values())
        if total == 0 and paid_off is None:
            paid_off = k
        rows.append({"k": k, "month": start.strftime("%Y-%m"), "free": free, "balance": total, "interest": month_interest, "pot": pot, "loans": loans, "inst": cards_inst})
    return {"start_balance": start_balance, "rows": rows, "interest": interest_total, "paid_off_month": rows[paid_off - 1]["month"] if paid_off else None,
            "salary": salary, "params": dict(belanja_kartu=belanja_kartu, tunda_pot=tunda_pot, ekstra_sekarang=ekstra_sekarang, hemat=hemat, reserve=res)}


def _bln(ym: str) -> str:
    names = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")
    return f"{names[int(ym[5:7]) - 1]} {ym[:4]}"


def format_result(base: dict, sc: dict) -> str:
    """Plain facts for the model to explain (it must not recompute): baseline vs scenario, and the monthly path."""
    p = sc["params"]
    changed = [f"belanja kartu baru {format_idr(p['belanja_kartu'])}/bulan" if p["belanja_kartu"] else "",
               f"setoran pot ditunda {p['tunda_pot']} bulan" if p["tunda_pot"] else "",
               f"bayar ekstra sekarang {format_idr(p['ekstra_sekarang'])}" if p["ekstra_sekarang"] else "",
               f"penghematan {format_idr(p['hemat'])}/bulan" if p["hemat"] else ""]
    changed = [c for c in changed if c]
    lines = ["SKENARIO: " + ("; ".join(changed) if changed else "tanpa perubahan (kondisi sekarang)"),
             f"Saldo kartu sekarang: {format_idr(sc['start_balance'])}"]

    def verdict(r):
        end = r["rows"][-1]["balance"]
        lunas = f"lunas {_bln(r['paid_off_month'])}" if r["paid_off_month"] else f"BELUM lunas dalam {len(r['rows'])} bulan (sisa {format_idr(end)})"
        return f"{lunas}; total bunga {format_idr(r['interest'])}"
    lines.append("Tanpa perubahan: " + verdict(base))
    lines.append("Dengan skenario: " + verdict(sc))
    if changed:
        d = base["interest"] - sc["interest"]
        lines.append(f"Selisih bunga: {'hemat' if d >= 0 else 'tambah'} {format_idr(abs(d))}")
    first_pos = next((r for r in sc["rows"] if r["free"] > 0), None)
    lines.append("Sisa bulanan (setelah semua komitmen, sebelum membayar saldo kartu):")
    for r in sc["rows"]:
        lines.append(f"- {_bln(r['month'])}: sisa {format_idr(r['free'])}" + (f" (kurang; menambah saldo kartu)" if r["free"] < 0 else "") + f"; saldo kartu akhir bulan {format_idr(r['balance'])}")
    if first_pos is None:
        lines.append("Sisa bulanan negatif sepanjang periode: saldo kartu NAIK.")
    direction = "turun" if sc["rows"][-1]["balance"] < sc["start_balance"] else "naik"
    lines.append(f"Arah saldo kartu setelah {len(sc['rows'])} bulan: {direction}.")
    lines.append("Catatan: perhitungan kode dari data tersimpan; belanja kartu baru dihitung sebagai pengurang sisa bulanan.")
    return "\n".join(lines)
