"""Owner-facing reports for the Telegram slash commands. Rendered by code from the ledger (no model): aliases, bank names,
last digits and amounts only. The plugin sends the text straight to the owner."""
from __future__ import annotations

from datetime import date

from . import card_installments, health, roadmap, subscriptions, tools
from .money import format_idr

NAMES = ("bantuan", "rencana", "tagihan", "cicilan", "anggaran", "peta", "kondisi", "data")

HELP = """Saya asisten keuangan pribadi Anda. Tujuan kita: bebas pinjaman dan keuangan yang membaik bertahap.

TANPA PERINTAH, cukup kirim:
- Screenshot belanja: saya catat dan cek anggaran.
- PDF tagihan kartu, mutasi rekening, atau CSV: saya baca dan catat.
- Nomor kartu (16 digit, satu per pesan, tanpa CVV): disimpan terenkripsi, pesan Anda dihapus.
- Kabar pembayaran, mis. "sudah bayar kartu HSBC 2 juta": saya catat dan hitung ulang sisanya.
- Pertanyaan, mis. "berapa yang harus saya bayar tanggal 30?", "kapan kartu lunas?", "kalau saya bayar lebih ke Jenius bagaimana?".

PERINTAH:
/rencana  rencana gajian dan pembayaran terdekat
/tagihan  tagihan kartu terbuka dan jatuh tempo
/cicilan  cicilan kartu dan langganan
/anggaran anggaran bulan ini dan pemakaiannya
/peta     peta jalan bebas utang
/kondisi  penilaian kesehatan keuangan
/data     ringkasan semua data yang tersimpan
/rincian  nomor tujuan transfer lengkap (terhapus otomatis 24 jam)
/rekening simpan nomor rekening: /rekening alias bank nomor
/va       simpan nomor virtual account: /va alias bank nomor
/new      mulai percakapan baru (data tidak hilang)
/stop     hentikan proses yang sedang berjalan

Angka dihitung oleh kode, bukan ditebak model. Nomor lengkap tidak pernah saya lihat."""


def _tagihan(conn, today: date) -> str:
    rows = conn.execute(
        "SELECT k.alias, k.bank, k.last4, s.due_date, s.total_due - s.paid_amount AS owed, MAX(0, s.minimum_due - s.paid_amount) AS minimum"
        " FROM cards k JOIN statements s ON s.card_id = k.id WHERE s.id = (SELECT id FROM statements WHERE card_id = k.id"
        " ORDER BY statement_date DESC, id DESC LIMIT 1) ORDER BY s.due_date").fetchall()
    lines, total = ["Tagihan kartu terbuka (urut jatuh tempo):"], 0
    for r in rows:
        owed = max(0, r["owed"])
        if owed == 0:
            lines.append(f"- {r['bank']} ...{r['last4']}: LUNAS")
            continue
        total += owed
        days = (date.fromisoformat(r["due_date"]) - today).days
        when = f"{r['due_date']} ({days} hari lagi)" if days >= 0 else f"{r['due_date']} (LEWAT {-days} hari)"
        lines.append(f"- {r['bank']} ...{r['last4']}: sisa {format_idr(owed)}, minimum {format_idr(r['minimum'])}, jatuh tempo {when}")
    lines.append(f"Total sisa: {format_idr(total)}")
    return "\n".join(lines)


def _anggaran(conn, today: date) -> str:
    month = f"{today.year}-{today.month:02d}"
    rows = health.budget_status(conn, month)
    lines = [f"Anggaran {month} (kartu: hanya belanja yang dibayar kartu):"]
    for b in rows:
        mark = {"over": "LEWAT", "watch": "waspada", "ok": "aman"}[b["status"]]
        lines.append(f"- {b['category']}: {format_idr(b['spent'])} dari {format_idr(b['budget'])} ({b['pct']}%) {mark}")
    if not rows:
        lines.append("Belum ada anggaran.")
    pace = health.spending_pace(conn, today)
    if pace:
        lines.append(f"Jatah harian sampai gajian {pace['next_payday']}: terpakai {format_idr(pace['spent'])} dari {format_idr(pace['allowance'])}.")
    return "\n".join(lines)


def _kondisi(conn, today: date) -> str:
    h = health.health_check(conn, today)
    tag = {"bad": "BURUK", "warn": "Waspada", "info": "Info"}
    return "\n".join([f"Penilaian keuangan {h['month']}: {h['verdict']}"] + [f"- [{tag.get(sev, sev)}] {text}" for sev, text in h["findings"]])


def build(conn, name: str, today: date) -> str:
    if name == "bantuan":
        return HELP
    if name == "rencana":
        return tools.summarize_plan(tools.generate_payday_plan(conn, today))
    if name == "tagihan":
        return _tagihan(conn, today)
    if name == "cicilan":
        return card_installments.format_list(conn) + "\n\nLANGGANAN\n" + subscriptions.format_list(conn)
    if name == "anggaran":
        return _anggaran(conn, today)
    if name == "peta":
        return roadmap.format_roadmap(roadmap.roadmap(conn, today))
    if name == "kondisi":
        return _kondisi(conn, today)
    if name == "data":
        return tools.data_overview(conn, today)
    raise ValueError("laporan tidak dikenal")
