import os
import random
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from cryptography.exceptions import InvalidTag  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402
from vault_tools.payee_vault import PayeeVault, has_forbidden_card_data  # noqa: E402
from vault_tools.reconcile import reconcile  # noqa: E402

KEY = bytes(range(32))
CARD = "4111 1111 1111 1111"


class Reconcile(unittest.TestCase):
    def test_ok(self):
        r = reconcile(2_000_000, 2_000_000, 1_500_000, 25_000, 1_525_000)
        self.assertTrue(r.ok)
        self.assertEqual(r.diff, 0)

    def test_mismatch_reported_not_fixed(self):
        r = reconcile(2_000_000, 2_000_000, 1_500_000, 25_000, 1_600_000)
        self.assertFalse(r.ok)
        self.assertEqual((r.expected_total, r.diff), (1_525_000, 75_000))

    def test_rejects_float(self):
        with self.assertRaises(TypeError):
            reconcile(1.0, 0, 0, 0, 1)

    def test_property_consistent(self):
        rng = random.Random(1)
        for _ in range(300):
            p, pay, ch, fee = (rng.randint(0, 9_000_000) for _ in range(4))
            self.assertTrue(reconcile(p, pay, ch, fee, p - pay + ch + fee).ok)
            self.assertTrue(reconcile(p, pay, ch, fee, p - pay + ch + fee + 3).ok)           # cents rounding
            self.assertFalse(reconcile(p, pay, ch, fee, p - pay + ch + fee + 4).ok)
            self.assertFalse(reconcile(p, pay, ch, fee, p - pay + ch + fee - 4).ok)


class Ledger(unittest.TestCase):
    def test_rejects_non_integer_money(self):
        conn = connect(":memory:")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO cards(alias,bank,last4,statement_day,due_day,credit_limit)"
                         " VALUES ('c1','dbs','1111',5,20,1500000.5)")

    def test_rejects_bad_status_and_duplicate_statement(self):
        conn = connect(":memory:")
        conn.execute("INSERT INTO cards(alias,bank,last4,statement_day,due_day,credit_limit)"
                     " VALUES ('c1','dbs','1111',5,20,15000000)")
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO transactions(txn_date,merchant,amount,status,source)"
                         " VALUES ('2026-10-01','x',1000,'maybe','manual')")
        row = ("c1h", "2026-10-05", "2026-10-20", 0, 0, 100, 0, 100, 10, 1, 0, "t")
        sql = ("INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,"
               "payments,charges,fees,total_due,minimum_due,reconciled,recon_diff,ingested_at)"
               " VALUES (1,?,?,?,?,?,?,?,?,?,?,?,?)")
        conn.execute(sql, row)
        with self.assertRaises(sqlite3.IntegrityError):  # idempotent by file hash
            conn.execute(sql, row)


class Vault(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "ledger.db")
        self.conn = connect(self.path)
        self.vault = PayeeVault(self.conn, KEY)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_roundtrip_and_display(self):
        shown = self.vault.store("dbs-1111", "card", "DBS", CARD)
        self.assertEqual(shown, "dbs-1111 ****1111")
        self.assertEqual(self.vault.reveal("dbs-1111"), "4111111111111111")
        self.assertEqual(self.vault.list_display(), ["dbs-1111 ****1111"])

    def test_plaintext_not_in_database_file(self):
        self.vault.store("dbs-1111", "card", "DBS", CARD)
        self.conn.close()
        raw = b""
        for name in os.listdir(self.tmp.name):  # db, wal, shm
            with open(os.path.join(self.tmp.name, name), "rb") as f:
                raw += f.read()
        self.assertNotIn(b"4111111111111111", raw)
        self.assertNotIn(b"4111 1111", raw)
        self.conn = connect(self.path)

    def test_match_without_decrypting(self):
        self.vault.store("dbs-1111", "card", "DBS", CARD)
        self.assertEqual(self.vault.find_alias("4111-1111-1111-1111"), "dbs-1111")
        self.assertIsNone(self.vault.find_alias("4111111111111129"))

    def test_wrong_key_fails(self):
        self.vault.store("dbs-1111", "card", "DBS", CARD)
        other = PayeeVault(self.conn, bytes(reversed(range(32))))
        with self.assertRaises(InvalidTag):
            other.reveal("dbs-1111")

    def test_ciphertext_bound_to_alias(self):
        self.vault.store("dbs-1111", "card", "DBS", CARD)
        self.vault.store("hsbc-2222", "card", "HSBC", "5500 0000 0000 0004")
        row = self.conn.execute("SELECT nonce,ciphertext FROM payee_secrets WHERE alias='dbs-1111'").fetchone()
        self.conn.execute("UPDATE payee_secrets SET nonce=?, ciphertext=? WHERE alias='hsbc-2222'",
                          (row["nonce"], row["ciphertext"]))
        with self.assertRaises(InvalidTag):
            self.vault.reveal("hsbc-2222")

    def test_duplicates_and_bad_input_rejected(self):
        self.vault.store("dbs-1111", "card", "DBS", CARD)
        with self.assertRaises(sqlite3.IntegrityError):
            self.vault.store("other-1", "card", "DBS", CARD)  # same number
        for alias, kind, num in (("Bad Alias", "card", CARD), ("ok-1", "pin", CARD), ("ok-2", "card", "12")):
            with self.assertRaises(ValueError):
                self.vault.store(alias, kind, "X", num)

    def test_forbidden_card_data(self):
        self.assertTrue(has_forbidden_card_data("kartu 4111111111111111 cvv 123"))
        self.assertTrue(has_forbidden_card_data("4111111111111111 exp 10/28"))
        self.assertFalse(has_forbidden_card_data("kartu 4111111111111111 tagihan"))


if __name__ == "__main__":
    unittest.main()
