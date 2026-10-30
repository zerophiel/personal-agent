"""Owner-facing reports for the Telegram slash commands, as Telegram HTML (bold headings, bullets, spacing, status emoji).
Rendered by code from the ledger (no model): aliases, bank names, last digits and amounts only. Every paragraph is
self-contained (balanced tags) so the plugin can split a long report on blank lines."""
from __future__ import annotations

import html
import re
from datetime import date

from . import card_installments, card_lines, health, roadmap, subscriptions, tools
from .money import format_idr

NAMES = ("bantuan", "rencana", "tagihan", "belanja", "cicilan", "anggaran", "peta", "kondisi", "data", "periksa", "usulan")

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des")


def e(text) -> str:
    return html.escape(str(text), quote=False)


def b(text) -> str:
    return f"<b>{e(text)}</b>"


def tgl(iso: str) -> str:
    d = date.fromisoformat(iso[:10])
    return f"{d.day} {_MONTHS[d.month - 1]}"


def bln(iso: str) -> str:
    d = date.fromisoformat(iso[:10] if len(iso) > 7 else iso + "-01")
    return f"{_MONTHS[d.month - 1]} {d.year}"


def _banks(conn) -> dict[str, str]:
    show = {"bca": "BCA", "hsbc": "HSBC", "cimb": "CIMB", "dbs": "DBS", "mega": "Mega", "mandiri": "Mandiri", "jenius": "Jenius"}
    return {r["alias"]: f"{show.get(r['bank'].lower(), r['bank'].title())} …{r['last4']}" for r in conn.execute("SELECT alias, bank, last4 FROM cards")}


_WORDS = {"ipl": "IPL", "va": "VA", "spaylater": "SPayLater", "mtf": "MTF"}


def _nice(alias: str) -> str:
    return " ".join(_WORDS.get(w, w.capitalize()) for w in alias.replace("-", " ").split())


def label(alias: str, banks: dict[str, str]) -> str:
    return banks[alias] if alias in banks else _nice(alias)


_ISO = re.compile(r"\b(20\d\d-\d\d-\d\d)\b")


def pretty(text: str, conn, banks: dict[str, str]) -> str:
    """Engine sentences carry technical aliases and ISO dates; show them the way the owner talks."""
    names = dict(banks)
    for r in conn.execute("SELECT alias, bank FROM accounts"):
        names.setdefault(r["alias"], r["bank"].title())
    for tbl in ("debts", "fixed_expenses", "sinking_funds"):
        for r in conn.execute(f"SELECT alias FROM {tbl}"):
            names.setdefault(r["alias"], _nice(r["alias"]))
    for alias in sorted(names, key=len, reverse=True):
        text = re.sub(rf"(?<![\w-]){re.escape(alias)}(?![\w-])", names[alias], text)
    return _ISO.sub(lambda m: tgl(m.group(1)), text)


def _note(t: dict) -> str:
    reason = t["reason"]
    if t.get("method") == "autodebit":
        return f"autodebet, saldo harus cukup sebelum {tgl(t['due'])}"
    if t.get("method") == "app_menu":
        return "lewat menu aplikasi" + (", minimum" if "minimum" in reason else ", bayar penuh" if "penuh" in reason else "")
    if "minimum" in reason:
        return "minimum"
    if "penuh" in reason:
        return "bayar penuh"
    return {"transfer pool": "setoran pot", "pengeluaran tetap": ""}.get(reason, reason)


HELP = f"""🤖 {b("Asisten keuangan pribadi Anda")}
Tujuan kita: bebas pinjaman dan keuangan yang membaik bertahap.

{b("📨 Tanpa perintah, cukup kirim:")}
• {b("Screenshot belanja")}: saya catat dan cek anggaran
• {b("PDF tagihan, mutasi, atau CSV")}: saya baca dan catat
• {b("Nomor kartu")} (16 digit, satu per pesan, tanpa CVV): disimpan aman, pesan Anda dihapus
• {b("Kabar bayar")}, mis. "sudah bayar HSBC 2 juta": saya catat dan hitung ulang sisanya
• {b("Pertanyaan")}, mis. "berapa yang harus saya bayar tanggal 30?" atau "kapan kartu lunas?"

{b("⌨️ Perintah:")}
<code>/rencana</code> rencana gajian dan pembayaran terdekat
<code>/tagihan</code> tagihan kartu dan jatuh tempo
<code>/belanja</code> isi tagihan kartu: belanja, langganan, cicilan, bunga
<code>/cicilan</code> cicilan kartu dan langganan
<code>/anggaran</code> anggaran bulan ini
<code>/peta</code> peta jalan bebas utang
<code>/kondisi</code> penilaian kesehatan keuangan
<code>/data</code> semua data yang tersimpan
<code>/usulan</code> kemampuan baru yang saya minta dibuatkan
<code>/rincian</code> nomor tujuan transfer lengkap (terhapus 24 jam)
<code>/rekening</code> dan <code>/va</code> simpan nomor: <code>/rekening alias bank nomor</code>
<code>/new</code> percakapan baru (data tidak hilang)
<code>/stop</code> hentikan proses

🔒 Angka dihitung oleh kode, bukan ditebak model. Nomor lengkap tidak pernah saya lihat."""


def _rencana(conn, today: date) -> str:
    snap = tools.generate_payday_plan(conn, today)
    banks = _banks(conn)
    out = [f"📅 {b('Rencana gajian ' + tgl(snap['payday']) + ' ' + str(date.fromisoformat(snap['payday']).year))}\n"
           f"Gaji {b(format_idr(snap['salary']))} · berlaku sampai {tgl(snap['next_payday'])}"]
    by_date: dict[str, dict[str, dict]] = {}
    for t in snap["transfers"]:
        row = by_date.setdefault(t["date"], {}).setdefault(t["to_alias"], {"amount": 0, "notes": []})
        row["amount"] += t["amount"]
        if _note(t) and _note(t) not in row["notes"]:
            row["notes"].append(_note(t))
    short = {u["to_alias"] for u in snap["unfunded"]}
    for d in sorted(by_date):
        head = f"💰 {b('Bayar ' + tgl(d))}" + (" (hari gajian)" if d == snap["payday"] else "")
        rows = []
        for alias, r in by_date[d].items():
            notes = list(r["notes"])
            joined, partly = " ".join(notes), alias in short       # "bayar penuh" is the plan's target; it may be funded only in part
            if "minimum" in joined and "bayar penuh" in joined:
                notes = ["minimum + tambahan, BELUM lunas"] if partly else ["minimum + sisa tagihan, lunas"]
            elif "bayar penuh" in joined and partly:
                notes = ["sebagian, BELUM lunas"]
            note = "; ".join(notes)
            rows.append(f"• {e(label(alias, banks))}: {b(format_idr(r['amount']))}" + (f" <i>({e(note)})</i>" if note else ""))
        out.append(head + "\n" + "\n".join(rows))
    if snap["unfunded"]:
        rows = [f"• {e(label(u['to_alias'], banks))}: {b(format_idr(u['amount']))} <i>(bunga ± {e(format_idr(u['est_delay_cost']))}/bulan)</i>" for u in snap["unfunded"]]
        out.append(f"⚠️ {b('Belum terdanai: sisa tagihan yang belum terbayar')}\n" + "\n".join(rows))
    if snap.get("reminders"):
        out.append(f"📌 {b('Pengingat')}\n" + "\n".join(f"• {e(pretty(r, conn, banks))}" for r in snap["reminders"]))
    choices = [a for a in snap.get("advice", []) if a.startswith(("Opsi", "Jika tidak"))]
    if choices:
        out.append(f"💡 {b('Pilihan')}\n" + "\n".join(f"• {e(pretty(a, conn, banks))}" for a in choices))
    normal = tools.get_threshold(conn, "living_reserve")
    if str(snap.get("reserve_source", "")).startswith("sementara") and normal and snap["daily_allowance"]:
        days = max(1, round(snap["cash_to_hold"] / snap["daily_allowance"]))
        foot = (f"💵 {b('Uang tunai harian')}: {b(format_idr(normal))} (sekitar {b(format_idr(normal // days))} per hari)\n"
                f"    {e(format_idr(snap['cash_to_hold']))} dari gaji + saldo yang sudah Anda pegang")
    else:
        foot = f"💵 Kas ditahan {b(format_idr(snap['cash_to_hold']))} · jatah harian {b(format_idr(snap['daily_allowance']))}"
    out.append(foot)
    return "\n\n".join(out)


def _tagihan(conn, today: date) -> str:
    rows = conn.execute(
        "SELECT k.alias, s.due_date, s.total_due - s.paid_amount AS owed, MAX(0, s.minimum_due - s.paid_amount) AS minimum"
        " FROM cards k JOIN statements s ON s.card_id = k.id WHERE s.id = (SELECT id FROM statements WHERE card_id = k.id"
        " ORDER BY statement_date DESC, id DESC LIMIT 1) ORDER BY s.due_date").fetchall()
    banks = _banks(conn)
    out, total = [f"💳 {b('Tagihan kartu terbuka')} <i>(urut jatuh tempo)</i>"], 0
    for r in rows:
        name = label(r["alias"], banks)
        owed = max(0, r["owed"])
        if owed == 0:
            out.append(f"✅ {b(name)}\n    Lunas")
            continue
        total += owed
        days = (date.fromisoformat(r["due_date"]) - today).days
        icon = "🔴" if days <= 3 else "🟡" if days <= 10 else "🟢"
        when = f"{tgl(r['due_date'])} ({days} hari lagi)" if days >= 0 else f"{tgl(r['due_date'])} (LEWAT {-days} hari)"
        out.append(f"{icon} {b(name)}\n    Sisa {b(format_idr(owed))} · minimum {e(format_idr(r['minimum']))}\n    Jatuh tempo {e(when)}")
    out.append(f"🧾 {b('Total sisa: ' + format_idr(total))}\n<i>🔴 ≤ 3 hari · 🟡 ≤ 10 hari · 🟢 lebih lama</i>")
    return "\n\n".join(out)


def _cicilan(conn, today: date) -> str:
    banks = _banks(conn)
    inst = card_installments.active(conn)
    out = [f"🔁 {b('Cicilan kartu')}"]
    out += [f"• {e(label(a['card'], banks))}: {e(a['description'])} {a['seq']}/{a['total']}\n    {b(format_idr(a['per_month']))}/bulan · sisa {a['left']} bulan · selesai {e(bln(a['ends']))}" for a in inst] or ["Tidak ada cicilan kartu aktif."]
    out.append(f"{b('Total: ' + format_idr(card_installments.monthly_total(conn)) + ' per bulan')}\nSisa seluruhnya {e(format_idr(sum(a['remaining'] for a in inst)))}. <i>Sudah termasuk di tagihan kartu, bukan pengeluaran baru.</i>")
    subs = conn.execute("SELECT * FROM subscriptions ORDER BY status, name").fetchall()
    active = [f"• {e(r['name'])} ({e(label(r['source'], banks))}): {b(format_idr(r['amount']))}/bulan" for r in subs if r["status"] == "active"]
    maybe = [f"• {e(r['name'])}: {e(format_idr(r['amount']))}/bulan" + (f" <i>({e(r['note'])})</i>" if r["note"] else "") for r in subs if r["status"] == "unsure"]
    out.append(f"📺 {b('Langganan aktif')}\n" + ("\n".join(active) or "Belum ada.") + f"\n{b('Total: ' + format_idr(subscriptions.active_total(conn)) + ' per bulan')}")
    if maybe:
        out.append(f"❓ {b('Belum pasti')}\n" + "\n".join(maybe))
    return "\n\n".join(out)


def _anggaran(conn, today: date) -> str:
    month = f"{today.year}-{today.month:02d}"
    rows = health.budget_status(conn, month)
    out = [f"💰 {b('Anggaran ' + bln(month))}\n<i>\"kartu\" = hanya belanja yang dibayar kartu</i>"]
    lines = []
    for r in rows:
        icon = {"over": "🔴", "watch": "🟡", "ok": "✅"}[r["status"]]
        name = (r["category"].split(":", 1)[1].replace("-", " ").capitalize() + " (kartu)") if r["category"].startswith("kartu:") else r["category"].replace("-", " ").capitalize()
        lines.append(f"{icon} {b(name)}\n    {e(format_idr(r['spent']))} dari {e(format_idr(r['budget']))} ({r['pct']}%)")
    out.append("\n\n".join(lines) if lines else "Belum ada anggaran.")
    pace = health.spending_pace(conn, today)
    if pace:
        out.append(f"🗓️ {b('Jatah harian')} sampai gajian {e(tgl(pace['next_payday']))}\nTerpakai {b(format_idr(pace['spent']))} dari {e(format_idr(pace['allowance']))}")
    return "\n\n".join(out)


def _kondisi(conn, today: date) -> str:
    h = health.health_check(conn, today)
    icon = {"SEHAT": "🟢", "WASPADA": "🟡", "BURUK": "🔴"}.get(h["verdict"], "ℹ️")
    mark = {"bad": "🔴", "warn": "🟡", "info": "ℹ️"}
    rows = [f"{mark.get(sev, '•')} {e(text)}" for sev, text in h["findings"]]
    return f"🩺 {b('Kondisi keuangan ' + bln(h['month']))}\n{icon} {b(h['verdict'])}\n\n" + "\n\n".join(rows)


def _peta(conn, today: date) -> str:
    lines = roadmap.format_roadmap(roadmap.roadmap(conn, today)).splitlines()
    out, bucket, head = [], [], f"🛣️ {b('Peta jalan bebas utang')}"
    for ln in lines[1:]:
        if ln.startswith("- "):
            bucket.append(f"• {e(ln[2:])}")
        elif ln.startswith("Perkiraan bebas utang"):
            out.append(f"🏁 {b(ln)}")
        elif ln.endswith(":"):
            if bucket:
                out.append("\n".join(bucket)); bucket = []
            out.append(f"{b(ln.rstrip(':'))}")
        else:
            out.append(f"<i>{e(ln)}</i>" if ln.startswith("Asumsi") else e(ln))
    if bucket:
        out.append("\n".join(bucket))
    return head + "\n\n" + "\n\n".join(out)


def _data(conn, today: date) -> str:
    text = tools.data_overview(conn, today)
    out, bucket = [f"🗂️ {b('Data yang tersimpan')}"], []
    for ln in text.splitlines():
        if ln.startswith("- "):
            bucket.append("• " + e(ln[2:].replace(" | ", " · ")))
        else:
            if bucket:
                out.append("\n".join(bucket)); bucket = []
            out.append(b(ln.split(" (")[0].capitalize()) if ln.split(" (")[0].replace(" ", "").replace("/", "").isupper() else e(ln))
    if bucket:
        out.append("\n".join(bucket))
    return "\n\n".join(out)


def _belanja(conn, today: date) -> str:
    s = card_lines.summary(conn, 2)
    if not s["months"]:
        return f"🧾 {b('Belanja kartu')}\nBelum ada baris tagihan yang terbaca."
    banks = _banks(conn)
    out = [f"🧾 {b('Isi tagihan kartu')}\n<i>Dibaca kode dari baris tagihan. \"Belanja\" = yang masih bisa kamu atur.</i>"]
    for m in s["months"]:
        d = s["by_month"][m]
        k = d["kinds"]
        rows = [f"🛒 Belanja: {b(format_idr(k.get('belanja', 0)))}", f"📺 Langganan: {e(format_idr(k.get('langganan', 0)))}",
                f"🔁 Cicilan: {e(format_idr(k.get('cicilan', 0)))}", f"💸 Bunga + biaya: {e(format_idr(k.get('bunga', 0) + k.get('biaya', 0)))}"]
        if k.get("refund"):
            rows.append(f"↩️ Refund: {e(format_idr(-k['refund']))}")
        cats = "\n".join(f"    • {e(c.replace('-', ' ').capitalize())}: {e(format_idr(v))}" for c, v in list(d["categories"].items())[:6])
        big = "\n".join(f"    ⚠️ sekali: {e(desc[:40])} {e(format_idr(amt))}" for desc, amt, _ in d["big"])
        out.append(f"📅 {b('Siklus tagihan ' + bln(m))} ({len(d['cards'])} kartu)\n" + "\n".join(rows)
                   + (f"\n{b('Belanja per kategori')}\n{cats}" if cats else "") + (f"\n{big}" if big else ""))
    if s["mismatch"] or s["missing"]:
        names = [label(a, banks) + " " + tgl(d) for a, d, _ in s["mismatch"] + s["missing"]]
        out.append("ℹ️ <i>Belum terbaca lengkap: " + e(", ".join(names)) + "</i>")
    return "\n\n".join(out)


def _periksa(conn, today: date) -> str:
    from . import audit
    found = audit.run(conn, today)
    if not found:
        return f"✅ {b('Periksa data')}\nSemua sumber cocok: tagihan, baris tagihan, pembayaran, langganan, cicilan, pot."
    icon = {"bad": "⛔", "warn": "⚠️", "info": "ℹ️"}
    order = {"bad": 0, "warn": 1, "info": 2}
    rows = [f"{icon[s]} {e(t)}" for s, t in sorted(found, key=lambda f: order[f[0]])]
    return f"🔎 {b('Periksa data')} <i>(aturan tetap, dihitung kode)</i>\n" + "\n".join(rows)


def _usulan(conn, today: date) -> str:
    rows = conn.execute("SELECT id, created_at, title, detail, status, resolution FROM feature_requests ORDER BY CASE status WHEN 'baru' THEN 0 WHEN 'dikerjakan' THEN 1 ELSE 2 END, id DESC LIMIT 15").fetchall()
    if not rows:
        return f"💡 {b('Usulan')}\nBelum ada. Kalau saya menabrak batas, saya catat di sini agar bisa dibuatkan."
    mark = {"baru": "🆕", "dikerjakan": "🔧", "selesai": "✅", "ditolak": "⛔"}
    out = [f"💡 {b('Usulan kemampuan baru')}\n<i>Saya tidak bisa mengubah alat sendiri; usulan ini menunggu dikerjakan manusia.</i>"]
    out += [f"{mark[r['status']]} {b('#' + str(r['id']) + ' ' + r['title'])}\n    {e(r['detail'][:200])}"
            + (f"\n    ➡️ {e(r['resolution'][:400])}" if r["resolution"] else "")
            + f"\n    <i>{e(r['status'])} · {e(tgl(r['created_at']))}</i>" for r in rows]
    return "\n\n".join(out)


def build(conn, name: str, today: date) -> str:
    fn = {"bantuan": lambda c, t: HELP, "rencana": _rencana, "tagihan": _tagihan, "belanja": _belanja, "cicilan": _cicilan,
          "anggaran": _anggaran, "peta": _peta, "kondisi": _kondisi, "data": _data, "periksa": _periksa, "usulan": _usulan}.get(name)
    if fn is None:
        raise ValueError("laporan tidak dikenal")
    return fn(conn, today)
