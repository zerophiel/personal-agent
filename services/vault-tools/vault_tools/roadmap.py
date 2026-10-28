"""Debt-free roadmap: when each liability ends, how the cards get cleared, the debt-free date, and the cash
that is freed after each liability ends. Pure arithmetic over the ledger; the cards and the pot come from the same
statement-based simulator as simulasi_skenario, so the two never disagree. Assumptions are stated in the output:
no card spending beyond the living money and no new loans, salary unchanged, cards paid highest interest first."""
from __future__ import annotations

import calendar
from datetime import date

from . import card_installments
from .money import format_idr
from .tools import current_payday, get_threshold, id_holidays, sinking_required

MAX_MONTHS = 36


def _clamp(year: int, month: int, day: int) -> date:
    return date(year, month, min(day, calendar.monthrange(year, month)[1]))


def add_months(d: date, n: int, day: int | None = None) -> date:
    y, m = divmod(d.year * 12 + d.month - 1 + n, 12)
    return _clamp(y, m + 1, day or d.day)


def next_due(due_day: int, today: date) -> date:
    d = _clamp(today.year, today.month, due_day)
    return d if d >= today else add_months(d, 1, due_day)


def roadmap(conn, today: date) -> dict:
    hol = id_holidays(today.year) | id_holidays(today.year + 1) | id_holidays(today.year + 2)
    payday = current_payday(today, hol)
    items, freed, fund_aliases = [], [], set()

    for d in conn.execute("SELECT * FROM debts WHERE tenor_left > 0 ORDER BY alias"):
        first = next_due(d["due_day"], today)
        last = add_months(first, d["tenor_left"] - 1, d["due_day"])
        items.append({"kind": "cicilan", "alias": d["alias"], "remaining": d["tenor_left"] * d["installment"],
                      "ends": last.isoformat(), "per_month": d["installment"], "detail": f"{d['tenor_left']} angsuran lagi"})
        freed.append((last, d["installment"], d["alias"]))

    card_inst = card_installments.active(conn)
    for a in card_inst:
        items.append({"kind": "cicilan kartu", "alias": f"{a['card']}: {a['description']}", "remaining": a["remaining"],
                      "ends": a["ends"], "per_month": a["per_month"], "detail": f"{a['seq']}/{a['total']}, {a['left']} bulan lagi"})
        freed.append((date.fromisoformat(a["ends"]), a["per_month"], a["description"]))

    cards = [(r["alias"], r["owed"]) for r in conn.execute(
        "SELECT c.alias, s.total_due - s.paid_amount AS owed FROM statements s"
        " JOIN cards c ON c.id = s.card_id WHERE s.paid_at IS NULL AND s.total_due - s.paid_amount > 0"
        " AND s.id = (SELECT id FROM statements WHERE card_id = s.card_id ORDER BY statement_date DESC, id DESC LIMIT 1)")]
    card_total = sum(b for _, b in cards)

    sim = None
    if get_threshold(conn, "net_salary"):
        from . import simulate      # local import: simulate -> roadmap
        sim = simulate.simulate(conn, today, months=MAX_MONTHS)
    sim_funds = {f["alias"]: f for f in sim["funds"]} if sim else {}
    for f in conn.execute("SELECT * FROM sinking_funds ORDER BY alias"):
        s = sinking_required(conn, f, payday, hol)
        fund_aliases.add(f["alias"])
        sf = sim_funds.get(f["alias"])
        now = sf["deposits"][0] if sf and sf["deposits"] else s["per_month"]
        last = sf["deposits"][-1] if sf and sf["deposits"] else s["per_month"]
        detail = f"terkumpul {format_idr(s['saved'])} dari {format_idr(f['target'])}"
        if s["pace"] == "sisa":
            detail += "; pola kartu dulu: setoran = sisa setelah kartu"
        if sf and sf["at_due"] is not None:
            detail += f"; perkiraan pada tenggat {format_idr(sf['at_due'])}" + (f" (KURANG {format_idr(sf['gap'])})" if sf["gap"] > 0 else "")
        items.append({"kind": "dana terikat", "alias": f["alias"], "remaining": s["remaining"], "ends": f["due_date"],
                      "per_month": now, "detail": detail})
        if last:
            freed.append((date.fromisoformat(f["due_date"]), last, f["alias"]))

    card_result = card_end = capacity = None
    if sim:
        capacity = sim["rows"][0]["cash"]
        if cards:
            k = next((r["k"] for r in sim["rows"] if r["balance"] == 0), None)
            upto = sim["rows"][:k] if k else sim["rows"]
            card_result = {"months": k, "interest": sum(r["interest"] for r in upto), "left": sim["rows"][-1]["balance"],
                           "first_paid": sim["rows"][0]["paid"]}
            card_end = sim["paid_off_month"]
    ends = [date.fromisoformat(i["ends"]) for i in items]
    free_date = max(ends) if ends else None
    if card_result and card_result["months"]:
        end_cards = add_months(payday, card_result["months"] - 1)
        free_date = max(free_date, end_cards) if free_date else end_cards
    if cards and (card_result is None or card_result["months"] is None):
        free_date = None          # cards cannot be cleared (or salary unknown): no honest debt-free date
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
        base = f"- Kartu: tagihan terbuka {format_idr(r['card_total'])} ({', '.join(a for a, _ in r['cards'])})"
        if r["capacity"] is None:
            lines.append(base + "; kapasitas bayar belum bisa dihitung (net_salary belum diset)")
        elif res and res["months"]:
            lines.append(f"{base}; kas gajian ini setelah tagihan tetap, cicilan dan uang harian {format_idr(r['capacity'])}; "
                         f"lunas penuh dalam {res['months']} gajian (bulan tagihan {r['card_end']}), bunga yang terbayar sekitar {format_idr(res['interest'])}")
        else:
            lines.append(f"{base}; kas setelah kewajiban TIDAK cukup untuk melunasi dalam {MAX_MONTHS} bulan "
                         f"(sisa {format_idr(res['left'] if res else r['card_total'])}). Pengeluaran harus turun.")
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
    lines.append("Asumsi: gaji tetap; tidak ada belanja kartu di luar uang harian dan tidak ada pinjaman baru; tagihan kartu berikutnya = cicilan kartu + "
                 "langganan; kartu dilunasi dari bunga tertinggi; pot mengikuti polanya (simulasi yang sama dengan simulasi_skenario).")
    return "\n".join(lines)
