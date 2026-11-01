"""Correcting what the owner recorded (usulan #3, 2026-10-29: PHO STREET Rp 156.541 was recorded from Jenius, it was
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
        with self.assertRaisesRegex(ValueError, "bukan lebih dari satu"):
            health.edit_expense(self.conn, TODAY, self.id, 156_541, "x", account_alias="jago-harian", card_alias="cimb-1")
        with self.assertRaisesRegex(ValueError, "bukan lebih dari satu"):
            health.edit_expense(self.conn, TODAY, self.id, 156_541, "x", account_alias="jago-harian", cash=True)
        with self.assertRaisesRegex(ValueError, "tidak digabung dengan apa pun"):
            health.edit_expense(self.conn, TODAY, self.id, 156_541, "x", unmerge=True)
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

    def test_a_record_merged_into_a_mutation_is_corrected_and_leaves_a_row_of_another_bank(self):
        self.conn.execute("UPDATE transactions SET merged_into=? WHERE id=?", (self.mut, self.id))
        self.assertIn(f"sudah digabung dengan mutasi bank #{self.mut} (QRIS PHO STREET, 2026-10-29, Rp 156.541, rekening"
                      " jenius-akun): yang itu yang dihitung", "\n".join(health.list_expenses(self.conn, TODAY)))
        out = health.edit_expense(self.conn, TODAY, self.id, 156_541, "dari Jago harian", account_alias="jago-harian")
        self.assertIn(f"Dilepas dari mutasi bank #{self.mut} (QRIS PHO STREET, 2026-10-29, Rp 156.541, rekening jenius-akun)."
                      " Sekarang dihitung sendiri.", out)
        self.assertIsNone(self.conn.execute("SELECT merged_into FROM transactions WHERE id=?", (self.id,)).fetchone()[0])

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
        # still that money: the owner's category is the one the row counts under
        out = health.edit_expense(self.conn, TODAY, self.id, 156_541, "lagi", category="jajan")
        self.assertIn(f"Masih cocok dengan mutasi bank #{self.mut}", out)
        self.assertEqual(self.merged(), self.mut)
        self.assertEqual(self.conn.execute("SELECT category, status FROM transactions WHERE id=?", (self.mut,)).fetchone()[:],
                         ("jajan", "verified"))

    def test_another_bank_still_does_not_merge(self):
        out = health.edit_expense(self.conn, TODAY, self.id, 156_541, "dari Mandiri", account_alias="mandiri-utama")
        self.assertNotIn("Sekarang cocok", out)
        self.assertIsNone(self.merged())


class MergedRecords(unittest.TestCase):
    """2026-10-30, owner: "ya betulkan dua-duanya". A record inside a bank row could not be corrected, deleted or taken out
    of a row it is not. Now it can; the row still counts, and gets back the category the record gave it."""

    def setUp(self):
        self.conn = world()
        self.conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('jago-utama','jago','main')")
        self.conn.commit()

    def upload(self, account, h, *rows, replace=False):
        """A statement of 1-28 Oct, as most are when the owner records a purchase of the last days."""
        mutations.record_mutations(self.conn, account, h * 64, "2026-10-01", "2026-10-28", None, None,
                                   [{"date": d, "description": desc, "amount": a} for d, desc, a in rows], replace=replace)
        return {r["merchant"]: r["id"] for r in self.conn.execute("SELECT id, merchant FROM transactions WHERE source='mutation'")}

    def record(self, amount, merchant, day, account="jago-harian", category="makan"):
        return health.record_expense(self.conn, TODAY, amount, merchant, day, category, account_alias=account)["id"]

    def row(self, i):
        return self.conn.execute("SELECT merged_into, category, status FROM transactions WHERE id=?", (i,)).fetchone()[:]

    def spent(self):
        return health._spent_by_category(self.conn, date(2026, 10, 1), date(2026, 10, 31))

    def test_a_record_in_another_banks_row_moves_to_its_own(self):
        rid = self.record(50_000, "KOPI KENANGAN", "2026-10-27", account="mandiri-utama")
        self.upload("mandiri-utama", "a", ("2026-10-27", "TRSF KE ANDI", -50_000))
        rows = self.upload("jago-utama", "b", ("2026-10-27", "QRIS KOPI KENANGAN", -50_000))
        trsf, kopi = rows["TRSF KE ANDI"], rows["QRIS KOPI KENANGAN"]
        self.assertEqual((self.row(rid)[0], self.row(trsf)[1]), (trsf, "makan"))      # in the transfer to Andi, as makan
        out = health.edit_expense(self.conn, TODAY, rid, 50_000, "bayarnya dari Jago harian", account_alias="jago-harian")
        self.assertIn(f"Dilepas dari mutasi bank #{trsf} (TRSF KE ANDI, 2026-10-27, Rp 50.000, rekening mandiri-utama); kategori"
                      " mutasi itu kembali belum dikategorikan (tadinya makan, dari catatan ini). Sekarang cocok dengan mutasi"
                      f" bank #{kopi} (QRIS KOPI KENANGAN, 2026-10-27, Rp 50.000, rekening jago-utama)", out)
        self.assertEqual((self.row(rid)[0], self.row(trsf)[1], self.row(kopi)[1]), (kopi, None, "makan"))
        self.assertEqual(self.spent(), {"belum dikategorikan": 50_000, "makan": 50_000})  # two payments, both once

    def test_lepas_keeps_it_out_of_that_row_for_good(self):
        rid = self.record(156_541, "PHO STREET", "2026-10-27")
        mid = self.upload("jago-utama", "c", ("2026-10-27", "Monthly spending: PHO STREET POS Transaction", -156_541))[
            "Monthly spending: PHO STREET POS Transaction"]
        out = health.edit_expense(self.conn, TODAY, rid, 156_541, "bukan yang itu, itu belanja lain", unmerge=True)
        self.assertIn(f"Belanja #{rid} dilepas. Alasan: bukan yang itu, itu belanja lain.", out)
        self.assertIn("kategori mutasi itu kembali belum dikategorikan (tadinya makan, dari catatan ini). Sekarang dihitung"
                      " sendiri; tidak digabung lagi ke baris itu.", out)
        self.assertEqual((self.row(rid), self.row(mid)[1]), ((None, "makan", "unverified"), None))
        self.assertEqual(self.spent(), {"makan": 156_541, "belum dikategorikan": 156_541})
        # not put back by a later correction, nor by the statement recorded again (its row gets another id)
        health.edit_expense(self.conn, TODAY, rid, 156_541, "nama lengkap", merchant="PHO STREET Jakarta Barat")
        rows = self.upload("jago-utama", "c", ("2026-10-26", "PARKIR", -5_000),
                           ("2026-10-27", "Monthly spending: PHO STREET POS Transaction", -156_541), replace=True)
        self.assertNotEqual(rows["Monthly spending: PHO STREET POS Transaction"], mid)
        self.assertIsNone(self.row(rid)[0])
        # another row of that money does take it
        rows = self.upload("jago-utama", "d", ("2026-10-28", "QRIS PHO STREET", -156_541))
        self.assertEqual(self.row(rid)[0], rows["QRIS PHO STREET"])

    def test_a_record_merged_past_its_statement_stays_in_its_row_when_corrected(self):
        """An upload merges without the coverage gate: the statement ends on the 28th, the purchase is of the 29th (the bank
        booked it a day earlier). Matched afresh after a merchant fix it would have been left out and counted twice."""
        rid = self.record(75_000, "GRAB", "2026-10-29", category="transport")
        mid = self.upload("jago-utama", "e", ("2026-10-28", "QRIS GRAB", -75_000))["QRIS GRAB"]
        self.assertEqual(self.row(rid)[0], mid)
        out = health.edit_expense(self.conn, TODAY, rid, 75_000, "nama merchant", merchant="Grab Car")
        self.assertIn(f"Masih cocok dengan mutasi bank #{mid}", out)
        self.assertEqual((self.row(rid)[0], self.spent()), (mid, {"transport": 75_000}))

    def test_the_owners_category_is_the_one_that_counts_and_lepas_gives_the_rules_back(self):
        mutations.set_category_rule(self.conn, "QRIS TOKO ABC", "belanja")
        rid = self.record(60_000, "TOKO ABC", "2026-10-27")
        mid = self.upload("jago-utama", "f", ("2026-10-27", "QRIS TOKO ABC", -60_000))["QRIS TOKO ABC"]
        self.assertEqual(self.row(mid)[1:], ("belanja", "verified"))                    # a rule's row keeps its own
        out = health.edit_expense(self.conn, TODAY, rid, 60_000, "itu makan siang", category="makan")
        self.assertIn("kategori dipastikan pemilik", out)
        self.assertIn(f"Masih cocok dengan mutasi bank #{mid}", out)
        self.assertEqual((self.row(mid)[1:], self.spent()), (("makan", "verified"), {"makan": 60_000}))
        health.edit_expense(self.conn, TODAY, rid, 60_000, "bukan yang itu", unmerge=True)
        self.assertEqual((self.row(mid)[1:], self.spent()), (("belanja", "verified"), {"belanja": 60_000, "makan": 60_000}))

    def test_an_internal_move_turned_purchase_goes_back_in_with_its_new_category(self):
        rid = self.record(100_000, "Isi saldo Flazz", "2026-10-27", category="transfer_internal")
        mid = self.upload("jago-utama", "g", ("2026-10-27", "FLAZZ TOPUP", -100_000))["FLAZZ TOPUP"]
        self.assertEqual(self.row(mid)[1], "transfer_internal")                          # given by the record
        health.edit_expense(self.conn, TODAY, rid, 100_000, "itu bayar parkir", category="transport")
        self.assertEqual((self.row(rid)[0], self.row(mid)[1:]), (mid, ("transport", "verified")))

    def test_paid_in_cash_leaves_the_bank_row(self):
        rid = self.record(156_541, "PHO STREET", "2026-10-27")
        mid = self.upload("jago-utama", "h", ("2026-10-27", "QRIS PHO STREET", -156_541))["QRIS PHO STREET"]
        out = health.edit_expense(self.conn, TODAY, rid, 156_541, "bayar tunai", cash=True)
        self.assertIn("sumber rekening jago-harian -> tunai", out)
        self.assertIn("kategori mutasi itu kembali belum dikategorikan (tadinya makan, dari catatan ini). Sekarang dihitung"
                      " sendiri.", out)
        self.assertEqual((self.row(rid), self.row(mid)[1]), ((None, "makan", "unverified"), None))
        self.assertIn(f"#{rid} | PHO STREET | 2026-10-27 | Rp 156.541 | tunai | makan", health.list_expenses(self.conn, TODAY))

    def test_a_merged_record_can_be_deleted_and_its_row_still_counts(self):
        rid = self.record(156_541, "PHO STREET", "2026-10-27")
        mid = self.upload("jago-utama", "i", ("2026-10-27", "QRIS PHO STREET", -156_541))["QRIS PHO STREET"]
        out = health.delete_expense(self.conn, rid, 156_541, "dicatat dobel")
        self.assertIn(f"Mutasi bank #{mid} (QRIS PHO STREET, 2026-10-27, Rp 156.541, rekening jago-utama) tetap dihitung: uangnya"
                      f" memang keluar; kategorinya makan diambil dari catatan ini: bila mutasi itu bukan belanja ini, ubah"
                      f" dengan set_category untuk #{mid}.", out)
        self.assertEqual(self.spent(), {"makan": 156_541})

    def test_what_a_record_gave_a_removed_row_is_not_taken_from_the_row_that_gets_its_id(self):
        """A file recorded again (replace) removes its rows, and the last ids are used again: the new row has the rule's
        category, which a later lepas must not take away as if the record had given it."""
        rid = self.record(60_000, "WARUNG X", "2026-10-27")
        health.edit_expense(self.conn, TODAY, rid, 60_000, "pasti makan", category="makan")
        mid = self.upload("jago-utama", "j", ("2026-10-27", "QRIS WARUNG X", -60_000))["QRIS WARUNG X"]
        self.assertEqual(self.row(mid)[1:], ("makan", "verified"))                      # given by the record
        mutations.set_category_rule(self.conn, "QRIS WARUNG X", "makan")
        again = self.upload("jago-utama", "j", ("2026-10-27", "QRIS WARUNG X", -60_000), replace=True)["QRIS WARUNG X"]
        self.assertEqual((again, self.row(rid)[0], self.row(again)[1:]), (mid, mid, ("makan", "verified")))  # the rule's now
        health.edit_expense(self.conn, TODAY, rid, 60_000, "bukan yang itu", unmerge=True)
        self.assertEqual(self.row(again)[1:], ("makan", "verified"))

    def test_a_deleted_records_id_used_again_carries_nothing_of_it(self):
        """The last ids are used again: a record let go from a row and then deleted, or one that gave a row its category
        and was deleted, says nothing about the new record that gets its id."""
        mid = self.upload("jago-utama", "k", ("2026-10-27", "QRIS PHO STREET", -156_541))["QRIS PHO STREET"]
        rid = self.record(156_541, "PHO STREET", "2026-10-27")
        health.edit_expense(self.conn, TODAY, rid, 156_541, "bukan yang itu", unmerge=True)
        health.delete_expense(self.conn, rid, 156_541, "salah catat")
        again = self.record(156_541, "PHO STREET", "2026-10-27")
        self.assertEqual((again, self.row(again)[0]), (rid, mid))             # the same id, and it is that row's money
        out = health.delete_expense(self.conn, again, 156_541, "dobel")
        self.assertIn("kategorinya makan diambil dari catatan ini", out)       # the row keeps what the record gave it
        third = self.record(156_541, "PHO STREET", "2026-10-27", category="jajan")
        self.assertEqual((third, self.row(third)[0], self.row(mid)[1]), (rid, mid, "makan"))
        health.edit_expense(self.conn, TODAY, third, 156_541, "bukan yang itu", unmerge=True)
        self.assertEqual(self.row(mid)[1], "makan")                              # not taken back: this record did not give it

    def test_a_screenshot_sent_twice(self):
        first = self.record(100_000, "Isi saldo Flazz", "2026-10-28", account="mandiri-utama", category="transport")
        second = health.record_expense(self.conn, TODAY, 100_000, "Isi Flazz BCA", "2026-10-28", "transport",
                                       account_alias="mandiri-utama", allow_duplicate=True)["id"]
        self.conn.execute("UPDATE transactions SET merged_into=? WHERE id=?", (first, second))
        with self.assertRaisesRegex(ValueError, f"ubah #{first} atau hapus #{second}"):
            health.edit_expense(self.conn, TODAY, second, 100_000, "x", category="makan")
        out = health.edit_expense(self.conn, TODAY, second, 100_000, "memang isi dua kali", unmerge=True)
        self.assertIn(f"Dilepas dari catatan #{first}. Sekarang dihitung sendiri", out)
        self.assertEqual((self.row(second)[0], self.spent()), (None, {"transport": 200_000}))
        self.conn.execute("UPDATE transactions SET merged_into=? WHERE id=?", (first, second))
        out = health.delete_expense(self.conn, second, 100_000, "screenshot yang sama")
        self.assertIn(f"Catatan #{first} (screenshot yang sama) tetap dihitung.", out)
        self.assertEqual(self.spent(), {"transport": 100_000})


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
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 14)
            self.assertEqual(conn.execute("SELECT title, resolution FROM feature_requests").fetchone()[:], ("x", None))
            for t in ("change_log", "balance_reports", "one_off_bills"):
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
            # the source is asked, not assumed (no source was cash, and could take any bank's debit of that size)
            with self.assertRaisesRegex(Exception, "tanyakan ke pemilik"):
                call("record_expense", {"amount": 25_000, "merchant": "BAKSO", "txn_date": "2026-10-29", "account_alias": "",
                                        "card_alias": "", "tunai": False})
            with self.assertRaisesRegex(Exception, "SATU"):
                call("record_expense", {"amount": 25_000, "merchant": "BAKSO", "txn_date": "2026-10-29",
                                        "account_alias": "jago-harian", "tunai": True})
            self.assertIn("stored", call("record_expense", {"amount": 25_000, "merchant": "BAKSO", "txn_date": "2026-10-29",
                                                          "tunai": True}))
            self.assertIn("2026-10-29 | Rp 25.000 | tunai", call("daftar_belanja"))
            # a merged record is taken out of a row it is not; unused fields come empty
            ledger = connect(os.path.join(d, "l.db"))
            call("record_expense", {"amount": 156_541, "merchant": "PHO STREET", "txn_date": "2026-10-29",
                                    "account_alias": "jago-harian"})
            rid = ledger.execute("SELECT id FROM transactions WHERE merchant='PHO STREET'").fetchone()[0]
            mid = ledger.execute("INSERT INTO transactions(account_id, txn_date, merchant, amount, status, source) SELECT id,"
                                 " '2026-10-29', 'QRIS PHO', -156541, 'unverified', 'mutation' FROM accounts WHERE alias='jago-harian'"
                                 ).lastrowid
            ledger.execute("UPDATE transactions SET merged_into=? WHERE id=?", (mid, rid))
            ledger.commit()
            out = call("ubah_belanja", {"id": rid, "jumlah_tercatat": 156_541, "alasan": "bukan yang itu", "rekening": "",
                                        "kartu": "", "tunai": False, "jumlah": 0, "tanggal": "", "merchant": "", "kategori": "",
                                        "lepas": True})
            self.assertIn(f"Dilepas dari mutasi bank #{mid}", out)
            self.assertIsNone(ledger.execute("SELECT merged_into FROM transactions WHERE id=?", (rid,)).fetchone()[0])
            ledger.close()


if __name__ == "__main__":
    unittest.main()
