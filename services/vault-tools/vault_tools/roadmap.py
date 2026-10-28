"""Debt-free roadmap: when each liability ends, how the cards get cleared, the debt-free date, and the cash
that is freed after each liability ends. Pure arithmetic over the ledger; assumptions are stated in the output:
no new card spending or new loans, salary unchanged, cards paid by avalanche (highest interest first)."""
from __future__ import annotations

import calendar
from datetime import date

from . import card_installments, subscriptions
from .money import format_idr
from .tools import (DEFAULT_CARD_INTEREST_BP, bp_of_idr, get_threshold, id_holidays, next_payday,
                    last_working_day, sinking_required)

MAX_MONTHS = 60


def _clamp(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def add_months(d: date, n: int, day: int | None = None) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    return _clamp(y, m + 1, day or d.day)


def next_due(due_day: int, today: date) -> date:
    d = _clamp(today.year, today.month, due_day)
    return d if d >= today else add_months(d, 1, due_day)


def clear_cards(balances: list[tuple[str, int, int]], capacity: int) -> dict:
    """balances: [(alias, outstanding, monthly_interest_bp)]. Each month: pay by highest interest first with
    `capacity`, then interest accrues on what is left. Returns months needed (None if it never clears) and
    the total interest paid along the way."""
    bal = {a: b for a, b, _ in balances if b > 0}
    rate = {a: r for a, _, r in balances}
    interest = months = 0
    while bal and months < MAX_MONTHS:
        months += 1
        cap = max(0, capacity)
        for a in sorted(bal, key=lambda k: -rate[k]):
            pay = min(bal[a], cap)
            bal[a] -= pay
            cap -= pay
        for a in list(bal):
            if bal[a] <= 0:
                del bal[a]
            else:
                i = bp_of_idr(bal[a], rate[a])
                bal[a] += i
                interest += i
        if capacity <= 0:
            break
    return {"months": months if not bal else None, "interest": interest, "left": sum(bal.values())}


def roadmap(conn, today: date) -> dict:
    hol = id_holidays(today.year) | id_holidays(today.year + 1) | id_holidays(today.year + 2)
    payday = last_working_day(today.year, today.month, hol)
    if payday < today:
        payday = next_payday(payday, hol)
    items, freed = [], []

    for d in conn.execute("SELECT * FROM debts WHERE tenor_left > 0 ORDER BY alias"):
        first = next_due(d["due_day"], today)
        last = add_months(first, d["tenor_left"] - 1, d["due_day"])
        items.append({"kind": "cicilan", "alias": d["alias"], "remaining": d["tenor_left"] * d["installment"],
                      "ends": last.isoformat(), "per_month": d["installment"], "detail": f"{d['tenor_left']} angsuran lagi"})
        freed.append((last, d["installment"], d["alias"]))

    for f in conn.execute("SELECT * FROM sinking_funds ORDER BY alias"):
        s = sinking_required(conn, f, payday, hol)
        items.append({"kind": "dana terikat", "alias": f["alias"], "remaining": s["remaining"], "ends": f["due_date"],
                      "per_month": s["per_month"], "detail": f"terkumpul {format_idr(s['saved'])} dari {format_idr(f['target'])}"})
        if s["per_month"]:
            freed.append((date.fromisoformat(f["due_date"]), s["per_month"], f["alias"]))

    card_inst = card_installments.active(conn)
    for a in card_inst:
        items.append({"kind": "cicilan kartu", "alias": f"{a['card']}: {a['description']}", "remaining": a["remaining"],
                      "ends": a["ends"], "per_month": a["per_month"], "detail": f"{a['seq']}/{a['total']}, {a['left']} bulan lagi"})
        freed.append((date.fromisoformat(a["ends"]), a["per_month"], a["description"]))

    default_rate = get_threshold(conn, "default_card_interest_bp", DEFAULT_CARD_INTEREST_BP)
    cards = [(r["alias"], r["owed"], r["rate"] if r["rate"] is not None else default_rate) for r in conn.execute(
        "SELECT c.alias, s.total_due - s.paid_amount AS owed, c.interest_bp_month AS rate FROM statements s"
        " JOIN cards c ON c.id = s.card_id WHERE s.paid_at IS NULL AND s.total_due - s.paid_amount > 0"
        " AND s.id = (SELECT id FROM statements WHERE card_id = s.card_id ORDER BY statement_date DESC, id DESC LIMIT 1)")]

    salary = get_threshold(conn, "net_salary")
    capacity = None
    if salary:
        fixed = conn.execute("SELECT COALESCE(SUM(amount),0) FROM fixed_expenses").fetchone()[0]
        inst = conn.execute("SELECT COALESCE(SUM(installment),0) FROM debts WHERE tenor_left > 0").fetchone()[0]
        pot = sum(sinking_required(conn, f, payday, hol)["per_month"] for f in conn.execute("SELECT * FROM sinking_funds"))
        reserve = get_threshold(conn, "living_reserve")
        if reserve is None:
            from .health import estimate_living_reserve
            reserve = estimate_living_reserve(conn, payday, salary)
        recurring = subscriptions.active_total(conn)      # subscriptions and the like keep landing on the cards every month
        capacity = salary - fixed - inst - pot - reserve - sum(a["per_month"] for a in card_inst) - recurring   # next bills already carry them
    card_total = sum(b for _, b, _ in cards)
    card_result = clear_cards(cards, capacity) if cards and capacity is not None else None
    card_end = None
    if card_result and card_result["months"]:
        card_end = add_months(date(payday.year, payday.month, 1), card_result["months"] - 1).strftime("%Y-%m")
    ends = [date.fromisoformat(i["ends"]) for i in items]
    free_date = max(ends) if ends else None
    if card_result and card_result["months"] and card_end:
        end_cards = add_months(payday, card_result["months"] - 1)
        free_date = max(free_date, end_cards) if free_date else end_cards
    if cards and (card_result is None or card_result["months"] is None):
        free_date = None          # cards cannot be cleared (or capacity unknown): no honest debt-free date
    return {"today": today.isoformat(), "items": sorted(items, key=lambda i: i["ends"]), "cards": cards,
            "card_total": card_total, "card_result": card_result, "card_end": card_end, "capacity": capacity,
            "debt_free_date": free_date.isoformat() if free_date else None,
            "freed": sorted((d.isoformat(), amt, a) for d, amt, a in freed),
            "total_remaining": sum(i["remaining"] for i in items) + card_total}


def format_roadmap(r: dict) -> str:
    lines = [f"Peta jalan bebas utang (per {r['today']})",
             f"Total sisa kewajiban: {format_idr(r['total_remaining'])}"]
    for i in r["items"]:
        lines.append(f"- {i['alias']} ({i['kind']}): sisa {format_idr(i['remaining'])}, {i['detail']}, "
                     f"selesai {i['ends']}; {format_idr(i['per_month'])}/bulan")
    if r["cards"]:
        res = r["card_result"]
        base = f"- Kartu: saldo {format_idr(r['card_total'])} ({', '.join(a for a, _, _ in r['cards'])})"
        if r["capacity"] is None:
            lines.append(base + "; kapasitas bayar belum bisa dihitung (net_salary belum diset)")
        elif res and res["months"]:
            lines.append(f"{base}; dengan kapasitas {format_idr(r['capacity'])}/bulan lunas dalam {res['months']} bulan "
                         f"(sekitar {r['card_end']}), bunga yang terbayar sekitar {format_idr(res['interest'])}")
        else:
            lines.append(f"{base}; kapasitas {format_idr(max(0, r['capacity']))}/bulan TIDAK cukup untuk melunasi dalam "
                         f"{MAX_MONTHS} bulan (sisa {format_idr(res['left'] if res else r['card_total'])}). Pengeluaran harus turun.")
    if r["debt_free_date"]:
        lines.append(f"Perkiraan bebas utang: {r['debt_free_date']}")
    else:
        lines.append("Perkiraan bebas utang: belum bisa ditentukan (saldo kartu belum bisa dilunasi dengan kapasitas saat ini).")
    if r["freed"]:
        running = 0
        lines.append("Arus kas yang terbebas:")
        for d, amt, alias in r["freed"]:
            running += amt
            lines.append(f"- {d}: {alias} selesai, bebas {format_idr(amt)}/bulan (total terbebas {format_idr(running)}/bulan)")
    lines.append("Asumsi: tidak ada pembelian kartu atau pinjaman baru di luar cicilan dan langganan yang tercatat, gaji tetap, kartu dilunasi dari bunga tertinggi.")
    return "\n".join(lines)
