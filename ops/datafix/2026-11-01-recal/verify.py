"""Read only, after the deploy: the recalibration code runs in vault-tools. Every call that stores a row runs on an
in-memory copy, never on the live ledger."""
import sqlite3, sys
sys.path.insert(0, "/app")
from vault_tools import health, tools

assert hasattr(tools, "_unfunded_total") and hasattr(tools, "_open_transfers"), "the old code is still running"
src = sqlite3.connect("file:/data/ledger.db?mode=ro", uri=True)
mem = sqlite3.connect(":memory:")
src.backup(mem)
src.close()
mem.row_factory = sqlite3.Row
mem.execute("PRAGMA foreign_keys = ON")
today = tools.wib_today()
p = health.spending_pace(mem, today)
print("pace", today, {k: p[k] for k in ("allowance", "spent", "remaining", "pct_used", "status", "correction")})
print("plans", mem.execute("SELECT COUNT(*) FROM plans").fetchone()[0])

# 30 Oct 15:27: the unfunded total, added up by the code
total = [x for x in tools.payday_status(mem, today).splitlines() if x.startswith("JUMLAH")]
print("status_gajian:", total)
assert total and "dibawa ke tagihan berikutnya (minimum terpenuhi, berbunga) Rp 872.061" in total[0], total

# 30 Oct 16:08: what can be used, and the salary transfers still open (les Mandarin on 1 Nov)
bal = tools.record_account_balance(mem, today, "mandiri-utama", 293_913)
print("saldo_rekening 293.913 on the copy:", bal[bal.index("Yang bisa"):])
assert "Yang bisa dipakai Rp 193.913: saldo Rp 293.913 dikurangi saldo minimum yang ditahan bank Rp 100.000." in bal
todo = tools._open_transfers(mem, today, "mandiri-utama")
print("open salary transfers:", todo)
if todo == [("les-mandarin-manuel", 800_000)]:
    assert "saldonya KURANG Rp 606.087 untuk itu" in bal, bal

# 31 Oct 20:20: the confirmation from the stored row
r = health.record_expense(mem, today, 12_345, "UJI VERIFIKASI", today.isoformat(), "makan", "jago-harian", None)
print("record_expense on the copy:", r["recorded"])
assert r["recorded"].endswith(f" UJI VERIFIKASI Rp 12.345, {today.isoformat()}, dari jago-harian, kategori makan"), r
print("VERIFIED")
