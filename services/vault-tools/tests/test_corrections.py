"""Correcting what the owner recorded himself (usulan #3, 2026-10-29: PHO STREET Rp 156.541 was recorded from Jenius, it was
paid from the Jago daily account), and the change log that keeps every row as it was."""
import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import health, mutations, subscriptions, tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402

try:
    from vault_tools.server import MCP_TOOL_NAMES, create_app
    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False

TODAY = date(2026, 10, 30)


def world():
    conn = connect(":memory:")
    for alias, bank in (("jenius-akun", "Jenius"), ("jago-harian", "Jago"), ("mandiri-utama", "Mandiri")):
        conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES (?,?,'main')", (alias, bank))
    conn.commit()
    tools.upsert_card(conn, "cimb-1", "CIMB", "2222", 5, 5, 10_000_000)
    return conn


def pho(conn):
    return health.record_expense(conn, TODAY, 156_541, "PHO STREET Jakarta Barat", "2026-10-29", "makan",
                                 account_alias="jenius-akun")["id"]


def log(conn):
    return conn.execute("SELECT * FROM change_log ORDER BY id").fetchall()


class Edit(unittest.TestCase):
    def setUp(self):
        self.conn = world()
        self.id = pho(self.conn)

    def test_the_list_gives_ids_and_where_it_was_paid_from(self):
        self.assertEqual(health.list_expenses(self.conn, TODAY)[0],
                         f"#{self.id} | PHO STREET Jakarta Barat | 2026-10-29 | Rp 156.541 | rekening jenius-akun | makan")

    def test_the_wrong_account_is_corrected_and_the_row_before_is_kept(self):
        out = health.edit_expense(self.conn, TODAY, self.id, 156_541, "salah sumber, sebenarnya dari Jago harian",
                                  account_alias="jago-harian")
        self.assertIn("sumber rekening jenius-akun -> rekening jago-harian", out)
        self.assertEqual(self.conn.execute("SELECT a.alias FROM transactions t JOIN accounts a ON a.id = t.account_id WHERE t.id=?",
                                           (self.id,)).fetchone()[0], "jago-harian")
        (row,) = log(self.conn)
        self.assertEqual((row["tbl"], row["row_key"], row["action"]), ("transactions", str(self.id), "ubah"))
        self.assertEqual(json.loads(row["before_json"])["account_alias"], "jenius-akun")
        self.assertEqual(json.loads(row["after_json"])["account_alias"], "jago-harian")
        self.assertIn("Jago harian", row["reason"])

    def test_a_wrong_id_is_refused_by_the_recorded_amount(self):
        with self.assertRaisesRegex(ValueError, "Rp 156.541"):
            health.edit_expense(self.conn, TODAY, self.id, 156_000, "salah sumber", account_alias="jago-harian")
        with self.assertRaisesRegex(ValueError, "tidak ditemukan"):
            health.edit_expense(self.conn, TODAY, self.id + 99, 156_541, "salah sumber", account_alias="jago-harian")
        self.assertEqual(log(self.conn), [])

    def test_what_was_asked_is_checked(self):
        with self.assertRaisesRegex(ValueError, "alasan"):
            health.edit_expense(self.conn, TODAY, self.id, 156_541, "  ", account_alias="jago-harian")
        with self.assertRaisesRegex(ValueError, "bukan keduanya"):
            health.edit_expense(self.conn, TODAY, self.id, 156_541, "x", account_alias="jago-harian", card_alias="cimb-1")
        with self.assertRaisesRegex(ValueError, "tidak ada yang berubah"):
            health.edit_expense(self.conn, TODAY, self.id, 156_541, "x", account_alias="jenius-akun")
        with self.assertRaisesRegex(ValueError, "belum terdaftar"):
            health.edit_expense(self.conn, TODAY, self.id, 156_541, "x", account_alias="ghost")
        with self.assertRaisesRegex(ValueError, "masa depan"):
            health.edit_expense(self.conn, TODAY, self.id, 156_541, "x", txn_date="2026-11-05")
        with self.assertRaisesRegex(ValueError, "> 0"):
            health.edit_expense(self.conn, TODAY, self.id, 156_541, "x", amount=-5)
        self.assertEqual(log(self.conn), [])

    def test_moving_to_a_card_with_the_owners_category(self):
        out = health.edit_expense(self.conn, TODAY, self.id, 156_541, "pakai kartu CIMB", card_alias="cimb-1", category="Makan-Keluarga")
        r = self.conn.execute("SELECT account_id, card_id, category, status FROM transactions WHERE id=?", (self.id,)).fetchone()
        self.assertEqual((r["account_id"], r["category"], r["status"]), (None, "makan-keluarga", "verified"))
        self.assertIsNotNone(r["card_id"])
        self.assertIn("kartu cimb-1", out)

    def test_an_edited_row_never_blocks_a_later_record_of_its_old_values(self):
        health.edit_expense(self.conn, TODAY, self.id, 156_541, "struk salah baca", amount=150_000)
        again = health.record_expense(self.conn, TODAY, 156_541, "PHO STREET Jakarta Barat", "2026-10-29", "makan",
                                      account_alias="jenius-akun")
        self.assertEqual(again["status"], "stored")                    # the old key would have hit the UNIQUE index

    def test_long_numbers_are_masked_and_twins_flagged(self):
        health.record_expense(self.conn, TODAY, 50_000, "TRANSFER 1234567890 BUDI", "2026-10-28", account_alias="jago-harian")
        health.record_expense(self.conn, TODAY, 50_000, "Transfer Budi", "2026-10-28", account_alias="jago-harian",
                              allow_duplicate=True)
        text = "\n".join(health.list_expenses(self.conn, TODAY))
        self.assertNotIn("1234567890", text)
        self.assertIn("TRANSFER [angka] BUDI", text)
        self.assertEqual(text.count("ada catatan lain dengan tanggal, jumlah, dan sumber yang sama"), 2)


class OnlyTheOwnersRecords(unittest.TestCase):
    def setUp(self):
        self.conn = world()
        self.id = pho(self.conn)
        self.mut = self.conn.execute("INSERT INTO transactions(account_id, txn_date, merchant, amount, status, source)"
                                     " VALUES (1, '2026-10-29', 'QRIS PHO STREET', -156541, 'unverified', 'mutation')").lastrowid
        self.conn.commit()

    def test_bank_mutations_are_corrected_by_uploading_again(self):
        with self.assertRaisesRegex(ValueError, "mutasi bank"):
            health.edit_expense(self.conn, TODAY, self.mut, 156_541, "x", amount=150_000)
        with self.assertRaisesRegex(ValueError, "mutasi bank"):
            health.delete_expense(self.conn, self.mut, 156_541, "x")

    def test_a_record_merged_into_a_mutation_is_left_alone(self):
        self.conn.execute("UPDATE transactions SET merged_into=? WHERE id=?", (self.mut, self.id))
        with self.assertRaisesRegex(ValueError, "sudah digabung"):
            health.edit_expense(self.conn, TODAY, self.id, 156_541, "x", account_alias="jago-harian")
        self.assertIn("sudah digabung dengan mutasi bank", "\n".join(health.list_expenses(self.conn, TODAY)))

    def test_a_screenshot_sent_twice_and_merged_is_neither_a_twin_nor_called_a_mutation(self):
        """Live 2026-10-28: 'Isi Flazz BCA' was merged into the earlier 'Isi saldo Flazz' record, not into a mutation."""
        first = health.record_expense(self.conn, TODAY, 100_000, "Isi saldo Flazz", "2026-10-28", account_alias="mandiri-utama")["id"]
        second = health.record_expense(self.conn, TODAY, 100_000, "Isi Flazz BCA", "2026-10-28", account_alias="mandiri-utama",
                                       allow_duplicate=True)["id"]
        self.conn.execute("UPDATE transactions SET merged_into=? WHERE id=?", (first, second))
        lines = {l.split(" | ")[0]: l for l in health.list_expenses(self.conn, TODAY)}
        self.assertIn(f"sudah digabung dengan catatan #{first}", lines[f"#{second}"])
        self.assertNotIn("ada catatan lain", lines[f"#{first}"])
        with self.assertRaisesRegex(ValueError, f"catatan #{first}"):
            health.edit_expense(self.conn, TODAY, second, 100_000, "x", amount=90_000)
        with self.assertRaisesRegex(ValueError, "merujuk"):
            health.delete_expense(self.conn, first, 100_000, "x")

    def test_a_row_another_points_at_is_not_deleted(self):
        other = health.record_expense(self.conn, TODAY, 20_000, "Parkir", "2026-10-29", account_alias="jago-harian")["id"]
        self.conn.execute("UPDATE transactions SET merged_into=? WHERE id=?", (self.id, other))
        with self.assertRaisesRegex(ValueError, "merujuk"):
            health.delete_expense(self.conn, self.id, 156_541, "dobel")

    def test_delete_keeps_the_whole_row_in_the_log(self):
        out = health.delete_expense(self.conn, self.id, 156_541, "tercatat dua kali")
        self.assertIn("dihapus", out)
        self.assertIsNone(self.conn.execute("SELECT 1 FROM transactions WHERE id=?", (self.id,)).fetchone())
        (row,) = log(self.conn)
        before = json.loads(row["before_json"])
        self.assertEqual((row["action"], row["after_json"], before["amount"], before["source"], before["account_alias"]),
                         ("hapus", None, -156_541, "receipt", "jenius-akun"))
        self.assertTrue(before["dedupe_key"])                         # every column, not only what was shown


class CorrectedSourceFindsItsStatementRow(unittest.TestCase):
    """A record with the wrong bank stays out of the statement row of the bank that really paid (2026-10-30); once the owner
    corrects the source it is merged, and the change log shows it."""

    def setUp(self):
        self.conn = world()
        self.conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('jago-utama','jago','main')")
        self.conn.commit()
        self.id = pho(self.conn)
        mutations.record_mutations(self.conn, "jago-utama", "a" * 64, "2026-10-01", "2026-10-31", None, None,
                                   [{"date": "2026-10-29", "description": "Monthly spending: PHO STREET POS Transaction",
                                     "amount": -156_541}])
        self.mut = self.conn.execute("SELECT id FROM transactions WHERE source='mutation'").fetchone()[0]

    def merged(self):
        return self.conn.execute("SELECT merged_into FROM transactions WHERE id=?", (self.id,)).fetchone()[0]

    def test_the_corrected_bank_merges_it_and_the_log_shows_it(self):
        self.assertIsNone(self.merged())                          # Jenius is another bank: counted twice until corrected
        out = health.edit_expense(self.conn, TODAY, self.id, 156_541, "dari Jago harian", account_alias="jago-harian")
        self.assertIn(f"Sekarang cocok dengan mutasi bank #{self.mut} (Monthly spending: PHO STREET POS Transaction, 2026-10-29,"
                      " Rp 156.541, rekening jago-utama)", out)
        self.assertEqual(self.merged(), self.mut)
        self.assertEqual(json.loads(log(self.conn)[-1]["after_json"])["merged_into"], self.mut)
        self.assertEqual(self.conn.execute("SELECT category FROM transactions WHERE id=?", (self.mut,)).fetchone()[0], "makan")
        with self.assertRaisesRegex(ValueError, "sudah digabung"):
            health.edit_expense(self.conn, TODAY, self.id, 156_541, "lagi", category="jajan")

    def test_another_bank_still_does_not_merge(self):
        out = health.edit_expense(self.conn, TODAY, self.id, 156_541, "dari Mandiri", account_alias="mandiri-utama")
        self.assertNotIn("Sekarang cocok", out)
        self.assertIsNone(self.merged())


class SubscriptionLog(unittest.TestCase):
    def test_every_change_is_logged_and_a_repeat_is_not(self):
        conn = connect(":memory:")
        subscriptions.upsert(conn, "spotify", "Spotify", 54_990, "bca-1", note="keluarga")
        subscriptions.upsert(conn, "spotify", "Spotify", 59_990, "bca-1")
        subscriptions.upsert(conn, "spotify", "Spotify", 59_990, "bca-1")            # nothing new
        rows = conn.execute("SELECT * FROM change_log WHERE tbl='subscriptions' ORDER BY id").fetchall()
        self.assertEqual([r["action"] for r in rows], ["baru", "ubah"])
        before, after = json.loads(rows[1]["before_json"]), json.loads(rows[1]["after_json"])
        self.assertEqual((before["amount"], after["amount"], after["note"]), (54_990, 59_990, "keluarga"))


class Migration(unittest.TestCase):
    def test_a_v11_ledger_gets_the_new_tables_and_the_resolution_column(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "l.db")
            old = sqlite3.connect(path)
            old.executescript("CREATE TABLE feature_requests (id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, title TEXT NOT NULL,"
                              " detail TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'baru');"
                              " INSERT INTO feature_requests(created_at,title,detail) VALUES ('2026-10-28','x','y'); PRAGMA user_version = 11;")
            old.close()
            conn = connect(path)
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 12)
            self.assertEqual(conn.execute("SELECT title, resolution FROM feature_requests").fetchone()[:], ("x", None))
            for t in ("change_log", "balance_reports"):
                self.assertTrue(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (t,)).fetchone(), t)
            conn.close()
            connect(path).close()                                               # idempotent


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class ThroughTheTools(unittest.TestCase):
    def test_list_edit_and_delete_from_a_new_session(self):
        with tempfile.TemporaryDirectory() as d:
            app = create_app(os.path.join(d, "l.db"), bytes(range(32)), "m" * 40, "i" * 40, allowed_hosts=["testserver"],
                             today=lambda: TODAY, ingest_dir=d, passwords_path=None)
            call = lambda n, a=None: json.dumps(asyncio.run(app.state.mcp.call_tool(n, a or {})), default=str)  # noqa: E731
            self.assertTrue({"daftar_belanja", "ubah_belanja", "hapus_belanja"} <= set(MCP_TOOL_NAMES))
            for alias, bank in (("jenius-akun", "Jenius"), ("jago-harian", "Jago")):
                call("upsert_account", {"alias": alias, "bank": bank})
            call("record_expense", {"amount": 156_541, "merchant": "PHO STREET Jakarta Barat", "txn_date": "2026-10-29",
                                    "category": "makan", "account_alias": "jenius-akun"})
            self.assertIn("#1 | PHO STREET Jakarta Barat | 2026-10-29 | Rp 156.541 | rekening jenius-akun", call("daftar_belanja"))
            # unused fields sent empty, as a model tends to do, mean "unchanged"
            out = call("ubah_belanja", {"id": 1, "jumlah_tercatat": 156_541, "alasan": "dari Jago harian", "rekening": "jago-harian",
                                        "kartu": "", "jumlah": 0, "tanggal": "", "merchant": "", "kategori": ""})
            self.assertIn("rekening jenius-akun -> rekening jago-harian", out)
            with self.assertRaises(Exception):
                call("hapus_belanja", {"id": 1, "jumlah_tercatat": 150_000, "alasan": "dobel"})
            self.assertIn("dihapus", call("hapus_belanja", {"id": 1, "jumlah_tercatat": 156_541, "alasan": "dobel"}))
            self.assertIn("Tidak ada belanja", call("daftar_belanja"))


if __name__ == "__main__":
    unittest.main()
