"""Data fix for Deploy 2 (admin fees, bills paid once, undoing an instalment), run by deploy.sh in the vault-tools container
AFTER the new code is built. Three modes, each safe to run again:
  DRY=1    every step on an in-memory copy of the ledger, nothing written to /data; with VT=/tmp/dry it runs a copy of the
           new code before the deploy (docker exec -e DRY=1 -e VT=/tmp/dry ...)
  CHECK=1  read only: the report at the end, on a copy of the ledger (deploy.sh's last step)
  default  checks, then only the writes still missing, then the report
The writes, in this order:
1. the owner's fee estimates (usulan #4): Rp 7.500 per card payment, Rp 6.500 per other transfer, counted from the 30 Nov
   payday. biaya_admin_mulai goes first, so the 30 Oct plan, already carried out, never has them, not even for a moment.
2. the Coway arrears of Rp 540.000 (usulan #6), paid 30 Oct from the Mandiri balance (the owner to the bot on 30 Oct and in
   the Claude Code session on 1 Nov): an expense like the 13 Oct ones (sekali:coway-tunggakan), not a bill, so no plan
   pays it again. It merges into its Mandiri row when that statement is stored.
3. usulan #4 and #6 selesai, with what was built.
4. the running plan made again by the new code, after a copy showed its allocation is still the 30 Oct plan's (#62).
"""
import json, os, re, sqlite3, sys
from datetime import date

sys.path.insert(0, os.environ.get("VT", "/app"))
from vault_tools import health, ledger, simulate, tools  # noqa: E402

DRY, CHECK = os.environ.get("DRY") == "1", os.environ.get("CHECK") == "1"
DB, BAK = "/data/ledger.db", "/data/ledger.db.bak-pre-deploy2"
DAY, PAYDAY, BASE, NEXT = date(2026, 11, 1), "2026-10-30", 62, date(2026, 11, 30)
FEES = (("biaya_admin_mulai", 20261130), ("biaya_admin_kartu", 7_500), ("biaya_admin_transfer", 6_500))
COWAY = dict(amount=540_000, merchant="Coway tunggakan 2 bulan", txn_date="2026-10-30", category="sekali:coway-tunggakan",
             account_alias="mandiri-utama")
DONE = {
    4: "Selesai 1 Nov (Deploy 2): biaya admin perkiraan kini dihitung kode, Rp 7.500 per bayar kartu dan Rp 6.500 per "
       "transfer lain, sekali per tujuan, dibayar bersama pembayarannya dari rekening gaji. Berlaku mulai rencana gajian "
       "30 Nov; rencana 30 Okt sudah dijalankan, jadi angkanya tetap. Tampil di status_gajian, cek saldo, /rincian, laporan "
       "dan Notion.",
    6: "Selesai 1 Nov (Deploy 2): alat tagihan_sekali mencatat tagihan sekali bayar (tunggakan, perbaikan) dan memasukkannya "
       "ke rencana gajian berikutnya sampai lunas. Tunggakan Coway Rp 540.000 sudah dibayar 30 Okt dari Mandiri, jadi "
       "dicatat sebagai pengeluaran sekali (sekali:coway-tunggakan), bukan tagihan baru.",
}

assert hasattr(tools, "admin_fee") and ledger.SCHEMA_VERSION == 14, "the old code is still running: rebuild vault-tools first"


def say(*parts) -> None:
    print(re.sub(r"\d{9,}", "[angka]", " ".join(str(p) for p in parts)))


def copy() -> sqlite3.Connection:
    """The ledger in memory, brought to this code's schema the way ledger.connect does."""
    src = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    mem = sqlite3.connect(":memory:", check_same_thread=False)
    src.backup(mem)
    src.close()
    mem.row_factory = sqlite3.Row
    mem.execute("PRAGMA foreign_keys = ON")
    mem.executescript(ledger.DDL)
    ledger._migrate(mem)
    return mem


def allocation(snap: dict) -> dict:
    """What a plan moves, reminders and progress aside."""
    lt = snap.get("living_transfer") or {}
    return {"salary": snap["salary"], "cash_to_hold": snap["cash_to_hold"], "reserve": snap["reserve"],
            "transfers": [(t["to_alias"], t["amount"], t["date"]) for t in snap["transfers"]],
            "fees": [(f["to_alias"], f["amount"]) for f in snap.get("fees") or []],
            "living": (lt.get("amount"), lt.get("also_move")),
            "unfunded": [(u["to_alias"], u["amount"]) for u in snap["unfunded"]]}


def plan(conn, plan_id=None) -> tuple[int, dict]:
    q = "SELECT id, snapshot_json FROM plans WHERE " + ("id=?" if plan_id else "payday=? ORDER BY id DESC LIMIT 1")
    r = conn.execute(q, (plan_id or PAYDAY,)).fetchone()
    return r["id"], json.loads(r["snapshot_json"])


def report(conn) -> bool:
    """Read back what the fix wrote, and what the new code makes of it; `conn` is always a copy (plans get made here)."""
    ok = True
    say("schema", conn.execute("PRAGMA user_version").fetchone()[0], "| fees", {k: tools.get_threshold(conn, k) for k, _ in FEES})
    rows = conn.execute("SELECT t.id, t.source, a.alias, t.category, t.merged_into, t.merchant FROM transactions t LEFT JOIN"
                        " accounts a ON a.id = t.account_id WHERE t.txn_date=? AND t.amount=?",
                        (COWAY["txn_date"], -COWAY["amount"])).fetchall()
    for r in rows:
        say("coway row", tuple(r))
    ok &= len(rows) == 1 and (rows[0]["alias"], rows[0]["category"]) == (COWAY["account_alias"], COWAY["category"])
    for r in conn.execute("SELECT id, status, resolution FROM feature_requests WHERE id IN (4, 6) ORDER BY id"):
        say(f"usulan #{r['id']}", r["status"], "|", (r["resolution"] or "")[:70])
        ok &= r["status"] == "selesai"
    ids = [r[0] for r in conn.execute("SELECT id FROM plans WHERE payday=? ORDER BY id", (PAYDAY,))]
    (_, base), (last_id, last) = plan(conn, BASE), plan(conn)
    same = allocation(base) == allocation(last)
    ok &= same
    say(f"plans {PAYDAY}: {ids}; #{last_id} differs from #{BASE} in", sorted(k for k in set(base) | set(last) if base.get(k) != last.get(k)),
        "| allocation the same:", same)
    for line in tools.payday_status(conn, DAY).splitlines():     # makes the plan again, on this copy
        if line.startswith(("⏳", "◐")) or "BIAYA" in line or "TAGIHAN SEKALI" in line:
            say("  status:", line[:170])
    nxt = tools.generate_payday_plan(conn, DAY, payday=NEXT)     # a preview from today's data: the November bills are not in
    fees = nxt.get("fees") or []
    kinds = {}
    for f in fees:
        kinds.setdefault(f.get("kind"), []).append((f["to_alias"], f["amount"]))
    paid, fee = sum(t["amount"] for t in nxt["transfers"]), sum(f["amount"] for f in fees)
    say(f"plan {NEXT} preview: fees {fee}", kinds)
    say(f"  transfers {paid} + fees {fee} + cash {nxt['cash_to_hold']} = {paid + fee + nxt['cash_to_hold']} | salary {nxt['salary']}")
    ok &= paid + fee + nxt["cash_to_hold"] == nxt["salary"] and fee > 0
    sim = simulate.simulate(conn, DAY)
    say("fee_estimate", tools.fee_estimate(conn), "| simulation (month, fees, once):",
        [(r["month"], r["fees"], r["once"]) for r in sim["rows"][:4]])
    say("REPORT OK" if ok else "REPORT NOT OK")
    return ok


if CHECK:
    sys.exit(0 if report(copy()) else 1)

# 1. read only: values that differ from these, or a row of the Coway day and amount that is not this one, stop the fix
ro = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
ro.row_factory = sqlite3.Row
for k, v in FEES:
    if tools.get_threshold(ro, k) not in (None, v):
        sys.exit(f"STOP: {k} is {tools.get_threshold(ro, k)}, not {v}; look before writing")
seen = ro.execute("SELECT id, source, account_id, category FROM transactions WHERE txn_date=? AND amount=?",
                  (COWAY["txn_date"], -COWAY["amount"])).fetchall()
if len(seen) > 1 or (seen and seen[0]["category"] != COWAY["category"]):
    sys.exit(f"STOP: rows of that day and amount: {[tuple(r) for r in seen]}; look before writing")
ro.close()

if DRY:
    conn = copy()
else:
    assert os.path.exists(BAK), "no backup: run backup.py first"
    conn = ledger.connect(DB)

# 2. the writes still missing, in order; each tool commits its own
for k, v in FEES:                                  # biaya_admin_mulai first: the amounts never reach the 30 Oct plan
    if tools.get_threshold(conn, k) != v:
        say(tools.set_threshold(conn, k, v))
if not conn.execute("SELECT 1 FROM transactions WHERE txn_date=? AND amount=? AND category=?",
                    (COWAY["txn_date"], -COWAY["amount"], COWAY["category"])).fetchone():
    out = health.record_expense(conn, DAY, **COWAY)
    say("coway:", out["status"], "|", out.get("recorded"), "| merged into", out.get("merged_into"), "| alerts", out.get("alerts"))
    assert out["status"] == "stored", out
for i, text in DONE.items():
    conn.execute("UPDATE feature_requests SET status='selesai', resolution=? WHERE id=? AND status <> 'selesai'", (text, i))
conn.commit()

# 3. the running plan, made again: first on a copy, and only when its allocation is still plan #62's
probe = conn if DRY else copy()
pid, snap = plan(probe, BASE)
made = tools.generate_payday_plan(probe, DAY)
if allocation(made) != allocation(snap):
    sys.exit(f"STOP: the new code moves the {PAYDAY} plan: {allocation(snap)} -> {allocation(made)}")
if not DRY:
    tools.generate_payday_plan(conn, DAY)
    conn.commit()
say("plan", PAYDAY, "made again, allocation unchanged; latest row", plan(conn)[0])

# 4. read back
sys.exit(0 if report(conn if DRY else copy()) else 1)
