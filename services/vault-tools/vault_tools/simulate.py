"""What-if simulator: how the card bills, the pot and the emergency fund move over the coming pay cycles.

Pure arithmetic over the ledger (no model). One row per pay cycle; cycle 1 is the payday a plan made today belongs to
(the one just passed when the owner asks on the 1st). It works from the card STATEMENTS, so nothing is counted twice:
- cycle 1 pays the statements that are open now; they already hold this month's card instalments, subscriptions,
  purchases and interest;
- each later cycle's statements = what was carried (+ interest) + that month's new charges: card instalments and
  subscriptions, plus card spending ON TOP of the living money (`belanja_kartu`). Card spending inside the living money is
  paid from it and nets out.
Cash per cycle = salary - fixed costs - loan instalments - living money. It goes, in order, to the emergency fund, a set pot
deposit (pattern 'rata'), the card statements (highest interest first), then the pot (pattern 'sisa': what is left). A cycle
that cannot cover its bills leaves the rest on the cards, with interest. Interest is charged only on what is carried; a
bank usually also charges it on new purchases while a balance is carried, so the real cost of carrying is higher."""
from __future__ import annotations

from datetime import date

from . import card_installments, subscriptions
from .money import format_idr
from .roadmap import add_months
from .tools import (DEFAULT_CARD_INTEREST_BP, SINKING_BUFFER_DAYS, _low_cycles, _round_up, bp_of_idr, current_payday,
                    emergency_status, get_threshold, id_holidays, reserve_for, sinking_paydays_left, sinking_saved)

NEW_CHARGES = "tagihan-baru"     # the next statements' new charges: paid before any older carried balance


def _rata_deposit(f: dict, k: int) -> int:
    """The set deposit of a 'rata' pot on cycle k, recomputed from what is still missing (as the monthly plan does)."""
    rem = max(0, f["target"] - f["saved"])
    left_i = f["left"] - (k - 1)
    if rem <= 0 or left_i <= 0:
        return 0
    low_amount, low_n = f["low"]
    if low_amount is not None and 0 < low_n < f["left"] and k <= low_n:
        return min(low_amount, rem)
    return min(rem, _round_up(-(-rem // left_i)))


def simulate(conn, today: date, *, belanja_kartu: int = 0, tunda_pot: int = 0, ekstra_sekarang: int = 0,
             hemat: int = 0, reserve: int | None = None, months: int = 12, pot_awal: int | None = None, pot_awal_bulan: int = 0,
             pola_pot: str | None = None, gaji_hari_tenggat: bool | None = None) -> dict:
    salary = get_threshold(conn, "net_salary")
    if not salary:
        raise ValueError("net_salary belum diset")
    if pola_pot not in (None, "rata", "sisa"):
        raise ValueError("pola_pot: 'sisa' (kartu dulu, pot dari sisa) atau 'rata' (setoran tetap)")
    months = max(1, min(int(months), 36))
    hol = id_holidays(today.year) | id_holidays(today.year + 2)     # each call covers the year before and after
    payday = current_payday(today, hol)
    fixed = conn.execute("SELECT COALESCE(SUM(amount),0) FROM fixed_expenses").fetchone()[0]
    normal = reserve if reserve is not None else (get_threshold(conn, "living_reserve") or 0)
    first = reserve
    if first is None:
        first = reserve_for(conn, payday)[0]          # the one-off override when the owner already holds last cycle's cash
        first = normal if first is None else first
    debts = conn.execute("SELECT installment, tenor_left FROM debts WHERE tenor_left > 0").fetchall()
    inst = card_installments.active(conn)
    ef = emergency_status(conn)
    funds = []
    for f in conn.execute("SELECT * FROM sinking_funds ORDER BY due_date, alias").fetchall():
        on_due = f["due_payday"] if gaji_hari_tenggat is None else int(bool(gaji_hari_tenggat))
        low = (f["low_amount"], _low_cycles(f, payday))
        if pot_awal is not None:
            low = (pot_awal, pot_awal_bulan)
        elif tunda_pot:
            low = (0, tunda_pot)
        saved = sinking_saved(conn, f)
        funds.append({"alias": f["alias"], "target": f["target"], "due": f["due_date"], "pace": pola_pot or f["pace"], "low": low,
                      "left": sinking_paydays_left(payday, date.fromisoformat(f["due_date"]), hol, 0 if on_due else SINKING_BUFFER_DAYS),
                      "saved": saved, "start": saved, "at_due": None, "deposits": []})
    for f in funds:
        if f["left"] == 0:
            f["at_due"] = f["saved"]
    default_rate = get_threshold(conn, "default_card_interest_bp", DEFAULT_CARD_INTEREST_BP)
    bal, rate = {}, {}
    for r in conn.execute(
            "SELECT c.alias, s.total_due - s.paid_amount AS owed, c.interest_bp_month AS rate FROM statements s JOIN cards c ON c.id = s.card_id"
            " WHERE s.id = (SELECT id FROM statements WHERE card_id = s.card_id ORDER BY statement_date DESC, id DESC LIMIT 1)"):
        if r["owed"] > 0:
            bal[r["alias"]] = r["owed"]
            rate[r["alias"]] = r["rate"] if r["rate"] is not None else default_rate
    rate[NEW_CHARGES] = max(list(rate.values()) + [default_rate])
    start_balance = sum(bal.values())
    first_month = date(payday.year, payday.month, 1)
    ef_saved = ef["saved"] if ef else 0
    rows, interest_total, paid_off = [], 0, None
    for k in range(1, months + 1):
        month = add_months(first_month, k)                        # the month whose dues this cycle pays
        stmt = add_months(first_month, k - 1)                     # ... printed on the statements of the month before
        loans = sum(d["installment"] for d in debts if k <= d["tenor_left"])
        cash = salary - fixed - loans - (first if k == 1 else normal) + (ekstra_sekarang if k == 1 else 0)
        new = 0
        if k > 1:                                                 # the statements of this cycle: what was carried + new charges
            new = (subscriptions.active_total(conn, stmt.strftime("%Y-%m"))
                   + sum(a["per_month"] for a in inst if date.fromisoformat(a["ends"]) >= stmt) + belanja_kartu - hemat)
            if new > 0:
                bal[NEW_CHARGES] = bal.get(NEW_CHARGES, 0) + new
            else:
                cash -= new                                       # savings beyond the new charges stay as cash
        short = 0
        if cash < 0:                                              # the bills outrun the salary: the gap lands on a card
            short = -cash
            bal[NEW_CHARGES] = bal.get(NEW_CHARGES, 0) + short
            cash = 0
        due = sum(bal.values())
        ef_dep = 0
        if ef and ef_saved < ef["target"] and cash > 0:
            ef_dep = min(ef["monthly"], ef["target"] - ef_saved, cash)
            ef_saved += ef_dep
            cash -= ef_dep
        pot = 0
        for f in funds:                                           # 'rata': the set deposit comes before the card balances
            if f["pace"] == "rata" and k <= f["left"]:
                d = min(_rata_deposit(f, k), cash)
                f["saved"] += d
                cash -= d
                pot += d
                f["deposits"].append(d)
        paid = 0
        for a in sorted(bal, key=lambda x: (-rate[x], x)):
            take = min(bal[a], cash)
            bal[a] -= take
            cash -= take
            paid += take
        for f in funds:                                           # 'sisa': cards first, the pot takes what is left
            if f["pace"] == "sisa" and k <= f["left"]:
                d = min(max(0, f["target"] - f["saved"]), cash)
                f["saved"] += d
                cash -= d
                pot += d
                f["deposits"].append(d)
        for f in funds:
            if k == f["left"]:
                f["at_due"] = f["saved"]
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
        rows.append({"k": k, "month": month.strftime("%Y-%m"), "cash": cash + ef_dep + pot + paid, "due": due, "paid": paid,
                     "balance": total, "interest": month_interest, "ef": ef_dep, "pot": pot,
                     "pot_total": sum(f["saved"] for f in funds), "free": cash, "short": short, "new": max(0, new), "loans": loans})
    out_funds = [{"alias": f["alias"], "target": f["target"], "due": f["due"], "pace": f["pace"], "paydays": f["left"],
                  "start": f["start"], "at_due": f["at_due"], "gap": (f["target"] - f["at_due"]) if f["at_due"] is not None else None,
                  "deposits": f["deposits"]} for f in funds]
    return {"payday": payday.isoformat(), "start_balance": start_balance, "rows": rows, "interest": interest_total,
            "paid_off_month": rows[paid_off - 1]["month"] if paid_off else None, "salary": salary, "funds": out_funds,
            "emergency": {"target": ef["target"], "saved_end": ef_saved} if ef else None,
            "params": dict(belanja_kartu=belanja_kartu, tunda_pot=tunda_pot, ekstra_sekarang=ekstra_sekarang, hemat=hemat,
                           reserve=reserve, pot_awal=pot_awal, pot_awal_bulan=pot_awal_bulan, pola_pot=pola_pot,
                           gaji_hari_tenggat=gaji_hari_tenggat)}


def horizon(conn, today: date, at_least: int = 12) -> int:
    """Enough cycles to reach every pot's due date (capped at 36)."""
    hol = id_holidays(today.year) | id_holidays(today.year + 2)
    payday = current_payday(today, hol)
    left = [sinking_paydays_left(payday, date.fromisoformat(f["due_date"]), hol, 0) for f in conn.execute("SELECT due_date FROM sinking_funds")]
    return max([at_least] + [n + 1 for n in left])


def pot_projection(conn, today: date) -> dict:
    """Per pot: what it is expected to hold on its due date if every coming payday goes as planned."""
    if not get_threshold(conn, "net_salary"):
        return {}
    r = simulate(conn, today, months=min(36, horizon(conn, today, 1)))
    return {f["alias"]: f for f in r["funds"]}


def _bln(ym: str) -> str:
    names = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")
    return f"{names[int(ym[5:7]) - 1]} {ym[:4]}"


def _jt(n: int) -> str:
    """Compact millions for the monthly path, e.g. 4,25 jt."""
    if abs(n) < 1_000_000:
        return format_idr(n)
    return f"{n / 1_000_000:.2f}".replace(".", ",") + " jt"


def format_result(base: dict, sc: dict) -> str:
    """Plain facts for the model to explain (it must not recompute): baseline vs scenario, and the path per payday."""
    p = sc["params"]
    pola = {"sisa": "pola pot KARTU DULU (pot mendapat sisa)", "rata": "pola pot setoran tetap (rata)"}
    changed = [f"belanja kartu di luar uang harian {format_idr(p['belanja_kartu'])}/bulan" if p["belanja_kartu"] else "",
               f"setoran pot ditunda {p['tunda_pot']} bulan" if p["tunda_pot"] else "",
               f"setoran pot awal {format_idr(p['pot_awal'])}/bulan selama {p['pot_awal_bulan']} bulan, lalu mengejar target" if p["pot_awal"] is not None else "",
               f"bayar ekstra sekarang {format_idr(p['ekstra_sekarang'])}" if p["ekstra_sekarang"] else "",
               f"penghematan {format_idr(p['hemat'])}/bulan mulai tagihan berikutnya" if p["hemat"] else "",
               f"uang harian {format_idr(p['reserve'])}/bulan" if p["reserve"] is not None else "",
               pola.get(p["pola_pot"] or "", ""),
               ("gaji yang masuk di hari tenggat IKUT dipakai" if p["gaji_hari_tenggat"] else "gaji di hari tenggat TIDAK dipakai")
               if p["gaji_hari_tenggat"] is not None else ""]
    changed = [c for c in changed if c]
    lines = ["SKENARIO: " + ("; ".join(changed) if changed else "tanpa perubahan (kondisi sekarang)"),
             f"Gajian pertama: {sc['payday']}; tagihan kartu terbuka yang dibayar dari gaji itu: {format_idr(sc['start_balance'])}"]

    def verdict(r):
        end = r["rows"][-1]["balance"]
        cards = (f"kartu lunas penuh {_bln(r['paid_off_month'])}" if r["paid_off_month"]
                 else f"kartu BELUM lunas dalam {len(r['rows'])} bulan (sisa {format_idr(end)})")
        out = f"{cards}; total bunga {format_idr(r['interest'])}"
        for f in r["funds"]:
            if f["at_due"] is None:
                out += f"; pot {f['alias']}: tenggat {f['due']} di luar {len(r['rows'])} bulan simulasi"
            else:
                state = f"KURANG {format_idr(f['gap'])}" if f["gap"] > 0 else "cukup"
                out += (f"; pot {f['alias']} terkumpul {format_idr(f['at_due'])} dari {format_idr(f['target'])} pada {f['due']} "
                        f"({f['paydays']} gajian, {state})")
        return out
    lines.append("Tanpa perubahan: " + verdict(base))
    lines.append("Dengan skenario: " + verdict(sc))
    if changed:
        d = base["interest"] - sc["interest"]
        lines.append(f"Selisih bunga: {'hemat' if d >= 0 else 'tambah'} {format_idr(abs(d))}")
        for fb, fs in zip(base["funds"], sc["funds"]):
            if fb["at_due"] is not None and fs["at_due"] is not None and fb["at_due"] != fs["at_due"]:
                d = fs["at_due"] - fb["at_due"]
                lines.append(f"Pot {fs['alias']} pada tenggat: {'lebih' if d > 0 else 'kurang'} {format_idr(abs(d))} dibanding tanpa perubahan")
    if sc.get("emergency"):
        lines.append(f"Dana darurat di akhir simulasi: {format_idr(sc['emergency']['saved_end'])} dari {format_idr(sc['emergency']['target'])}")
    lines.append("Per gajian (bulan tagihan): kas setelah tagihan tetap, cicilan dan uang harian -> tagihan kartu dibayar | dana darurat | "
                 "pot | sisa bebas; saldo kartu yang terbawa")
    for r in sc["rows"]:
        lines.append(f"- {_bln(r['month'])}: kas {_jt(r['cash'])}; kartu {_jt(r['paid'])} dari {_jt(r['due'])}"
                     + (f"; darurat {_jt(r['ef'])}" if r["ef"] else "") + f"; pot {_jt(r['pot'])} (terkumpul {_jt(r['pot_total'])})"
                     + (f"; sisa bebas {_jt(r['free'])}" if r["free"] else "")
                     + (f"; terbawa {_jt(r['balance'])}" if r["balance"] else "")
                     + (f"; KURANG {_jt(r['short'])} ditalangi kartu" if r["short"] else ""))
    lines.append("Catatan: dihitung kode dari data tersimpan. Tagihan berikutnya = cicilan kartu + langganan bulan itu (+ belanja kartu di luar uang "
                 "harian bila diisi); belanja kartu di dalam uang harian dibayar dari uang harian itu. Bunga dihitung dari saldo yang terbawa; "
                 "bank biasanya juga membungakan transaksi baru selama ada saldo terbawa.")
    return "\n".join(lines)
