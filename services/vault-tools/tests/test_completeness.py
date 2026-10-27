import asyncio
import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import mutations as mu  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402

try:
    from reportlab.pdfgen import canvas
    from vault_tools import statement_pdf as sp
    HAVE_PDF = True
except ImportError:
    HAVE_PDF = False

H = "a" * 64
BCA_LIKE = """KLIK BCA statement
01/01 SALDO AWAL 10,000,000.00
05/01 TRSF E-BANKING DB 0501/FTSCY 1,000,000.00 DB
   BUDI SANTOSO
05/01 TRSF E-BANKING CR 0501/FTSAI 1,000,000.00
28/01 BYR VIA E-BANKING 250,000.00 DB
SALDO AKHIR 9,750,000.00
Tgl. 02 Feb 2026 ringkasan
"""


@unittest.skipUnless(HAVE_PDF, "pdf libs not installed")
class Counting(unittest.TestCase):
    def test_counts_only_dated_transaction_lines(self):
        self.assertEqual(sp.count_dated_lines([BCA_LIKE]), 3)        # saldo awal/akhir, wrapped line and header excluded

    def test_other_date_styles_and_spanning_parts(self):
        a = "27 Okt 2026 Pembayaran QR 20,000\n28 Okt 2026 Transfer 500,000\n"
        b = "29-10-2026 Biaya admin 2,500\n2026-10-30 tidak dihitung (format lain)\n"
        self.assertEqual(sp.count_dated_lines([a, b]), 3)
        self.assertEqual(sp.count_dated_lines(["tidak ada tanggal di sini"]), 0)

    def test_opening_and_closing_balance_lines_never_count(self):
        t = "01/10 Saldo Awal 5,000.00\n31/10 Saldo Akhir 6,000.00\n15/10 Opening Balance\n"
        self.assertEqual(sp.count_dated_lines([t]), 0)


def acct_db():
    conn = connect(":memory:")
    conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('bca-utama','BCA','main')")
    conn.commit()
    return conn


def r(day, desc, amount):
    return {"date": f"2026-01-{day:02d}", "description": desc, "amount": amount}


class Completeness(unittest.TestCase):
    def check(self, conn, lines):
        conn.execute("INSERT OR REPLACE INTO ingest_checks VALUES (?,?,?,'t')", (H, lines, 1))
        conn.commit()

    def full_rows(self):
        return [r(5, "TRSF DB", -1_000_000), r(5, "TRSF CR", 1_000_000), r(28, "BYR", -250_000)]

    def test_missing_cancelling_pair_is_caught_even_though_the_balance_matches(self):
        conn = acct_db()
        self.check(conn, 3)
        res = mu.record_mutations(conn, "bca-utama", H, "2026-01-01", "2026-01-31", 10_000_000, 9_750_000,
                                  [r(28, "BYR", -250_000)])           # the DB/CR pair of 1,000,000 was forgotten
        self.assertFalse(res["reconciled"])
        self.assertEqual(res["missing_rows"], 2)
        self.assertIn("BARIS KURANG: dokumen memuat 3 baris bertanggal, hanya 1 yang dikirim (kurang 2)", res["warning"])
        self.assertNotIn("REKONSILIASI TIDAK COCOK", res["warning"])        # the balance itself is fine
        self.assertEqual(conn.execute("SELECT reconciled FROM mutation_files").fetchone()[0], 0)

    def test_complete_rows_pass(self):
        conn = acct_db()
        self.check(conn, 3)
        res = mu.record_mutations(conn, "bca-utama", H, "2026-01-01", "2026-01-31", 10_000_000, 9_750_000, self.full_rows())
        self.assertEqual((res["status"], res["reconciled"]), ("stored", True))
        self.assertNotIn("warning", res)

    def test_without_a_recorded_count_nothing_is_flagged(self):
        conn = acct_db()                                                 # e.g. a CSV or an unknown layout: count was 0
        res = mu.record_mutations(conn, "bca-utama", H, "2026-01-01", "2026-01-31", None, None, [r(28, "BYR", -250_000)])
        self.assertTrue(res["reconciled"])
        self.check(conn, 0)
        res = mu.record_mutations(conn, "bca-utama", "b" * 64, "2026-01-01", "2026-01-31", None, None, [r(28, "X", -1)])
        self.assertTrue(res["reconciled"])

    def test_more_rows_than_lines_is_not_an_error(self):
        conn = acct_db()
        self.check(conn, 2)
        res = mu.record_mutations(conn, "bca-utama", H, "2026-01-01", "2026-01-31", None, None, self.full_rows())
        self.assertTrue(res["reconciled"])

    def test_replace_fixes_an_incomplete_recording(self):
        conn = acct_db()
        self.check(conn, 3)
        mu.record_mutations(conn, "bca-utama", H, "2026-01-01", "2026-01-31", 10_000_000, 9_750_000, [r(28, "BYR", -250_000)])
        again = mu.record_mutations(conn, "bca-utama", H, "2026-01-01", "2026-01-31", 10_000_000, 9_750_000, self.full_rows())
        self.assertEqual(again["status"], "duplicate")                    # without replace nothing changes
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 1)
        fixed = mu.record_mutations(conn, "bca-utama", H, "2026-01-01", "2026-01-31", 10_000_000, 9_750_000, self.full_rows(), replace=True)
        self.assertEqual((fixed["status"], fixed["reconciled"], fixed["rows"], fixed["new_rows"]), ("replaced", True, 3, 3))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 3)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM mutation_files").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT reconciled FROM mutation_files").fetchone()[0], 1)
        self.assertNotIn("lost_categories", fixed)

    def test_replace_reports_manual_categories_that_were_lost_and_unmerges_receipts(self):
        conn = acct_db()
        mu.record_mutations(conn, "bca-utama", H, "2026-01-01", "2026-01-31", None, None, [r(28, "BYR", -250_000)])
        conn.execute("UPDATE transactions SET category='makan', status='verified'")
        conn.execute("INSERT INTO transactions(txn_date,merchant,amount,category,status,source,merged_into) "
                     "VALUES ('2026-01-27','KOPI',-250000,'makan','unverified','receipt',1)")
        conn.commit()
        res = mu.record_mutations(conn, "bca-utama", H, "2026-01-01", "2026-01-31", None, None, self.full_rows(), replace=True)
        self.assertEqual(res["lost_categories"], 1)
        # the receipt was un-merged, then merged again into the freshly stored 250,000 row
        merged_to = conn.execute("SELECT merged_into FROM transactions WHERE source='receipt'").fetchone()[0]
        self.assertEqual(conn.execute("SELECT amount FROM transactions WHERE id=?", (merged_to,)).fetchone()[0], -250_000)

    def test_rounding_tolerance(self):
        for diff, ok in ((0, True), (1, True), (3, True), (-3, True), (4, False), (-4, False)):
            conn = acct_db()
            res = mu.record_mutations(conn, "bca-utama", str(abs(diff)) * 64 if diff else "9" * 64, "2026-01-01", "2026-01-31",
                                      1_000_000, 1_000_000 - 500 + diff, [r(5, "X", -500)])
            self.assertEqual(res["reconciled"], ok, diff)
            if 0 < abs(diff) <= 3:
                self.assertIn("pembulatan sen", res["note"])
            if not ok:
                self.assertIn("REKONSILIASI TIDAK COCOK", res["warning"])


def make_pdf(lines):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    y = 800
    for line in lines:
        c.drawString(40, y, line)
        y -= 14
    c.showPage()
    c.save()
    return buf.getvalue()


try:
    from starlette.testclient import TestClient  # noqa: F401
    from vault_tools.server import create_app
    HAVE_SERVER = HAVE_PDF
except ImportError:
    HAVE_SERVER = False


@unittest.skipUnless(HAVE_SERVER, "server/pdf libs not installed")
class ThroughTheTools(unittest.TestCase):
    def test_ingest_reports_the_line_count_and_record_enforces_it(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "telegram"))
            lines = ["BCA KlikBCA", "01/01 SALDO AWAL 10,000,000.00"] + [f"{i:02d}/01 BAYAR WARUNG {i} {i * 1000}.00 DB" for i in range(2, 12)]
            with open(os.path.join(d, "telegram", "3195122941_JAN_2026.pdf"), "wb") as f:
                f.write(make_pdf(lines))
            app = create_app(os.path.join(d, "l.db"), bytes(range(32)), "m" * 40, "i" * 40, allowed_hosts=["testserver"],
                             ingest_dir=d, passwords_path=None)
            call = lambda n, a: asyncio.run(app.state.mcp.call_tool(n, a))  # noqa: E731
            out = str(call("ingest_statement", {"file_ref": "telegram/3195122941_JAN_2026.pdf", "bank_hint": "bca"}))
            self.assertIn("baris_bertanggal=10", out)
            h = out.split("file_hash=")[1][:64]
            call("upsert_account", {"alias": "bca-utama", "bank": "BCA", "kind": "main"})
            few = [{"date": f"2026-01-{i:02d}", "description": f"BAYAR WARUNG {i}", "amount": -i * 1000} for i in range(2, 8)]
            res = str(call("record_mutations", {"account_alias": "bca-utama", "file_hash": h, "period_start": "2026-01-01",
                                                "period_end": "2026-01-31", "rows": few}))
            self.assertIn("BARIS KURANG", res)
            self.assertIn("kurang 4", res)
            allrows = [{"date": f"2026-01-{i:02d}", "description": f"BAYAR WARUNG {i}", "amount": -i * 1000} for i in range(2, 12)]
            ok = str(call("record_mutations", {"account_alias": "bca-utama", "file_hash": h, "period_start": "2026-01-01",
                                               "period_end": "2026-01-31", "rows": allrows, "replace": True}))
            self.assertIn("replaced", ok)
            self.assertIn('"reconciled": true', ok)


if __name__ == "__main__":
    unittest.main()
