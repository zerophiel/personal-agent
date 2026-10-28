import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import subscriptions as sub  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402


class Subscriptions(unittest.TestCase):
    def test_active_total_ignores_ended_and_unsure(self):
        conn = connect(":memory:")
        sub.upsert(conn, "google-one", "Google One", 29_000, "hsbc-5915")
        sub.upsert(conn, "anthropic", "Anthropic Max", 1_700_000, "cimb-9888", note="USD, perkiraan")
        sub.upsert(conn, "cursor", "Cursor", 340_000, "cimb-9888", status="ended", note="sudah berhenti")
        sub.upsert(conn, "apple", "Apple", 59_000, "mandiri-4365", status="unsure")
        self.assertEqual(sub.active_total(conn), 1_729_000)
        text = sub.format_list(conn)
        self.assertIn("Cursor (cursor): berhenti", text)
        self.assertIn("belum pasti", text)
        self.assertIn("Total langganan aktif: Rp 1.729.000/bulan", text)

    def test_update_changes_the_same_row(self):
        conn = connect(":memory:")
        sub.upsert(conn, "google-one", "Google One", 329_000, "hsbc-5915")
        sub.upsert(conn, "google-one", "Google One", 29_000, "hsbc-5915", note="sudah downgrade")
        self.assertEqual(sub.active_total(conn), 29_000)
        self.assertEqual(conn.execute("SELECT count(*) FROM subscriptions").fetchone()[0], 1)

    def test_validation(self):
        conn = connect(":memory:")
        for args in (("Bad Alias", "x", 1000, "c"), ("ok-alias", "x", 0, "c"), ("ok-alias", "x", -5, "c")):
            with self.assertRaises(ValueError, msg=args):
                sub.upsert(conn, *args)
        with self.assertRaises(ValueError):
            sub.upsert(conn, "ok-alias", "x", 1000, "c", status="maybe")
        self.assertEqual(sub.format_list(conn), "Belum ada langganan tercatat.")


class OwnerRules(unittest.TestCase):
    def test_a_protected_subscription_stays_protected_when_updated_without_the_flag(self):
        conn = connect(":memory:")
        self.assertIn("WAJIB", sub.upsert(conn, "rockstar-gym", "Rockstar Gym", 1_458_000, "hsbc-5915", note="gym Gracia (anak)", essential=True))
        sub.upsert(conn, "rockstar-gym", "Rockstar Gym", 1_500_000, "jenius-0480")           # moved card, new price
        self.assertEqual(conn.execute("SELECT essential, amount FROM subscriptions").fetchone()[:], (1, 1_500_000))
        self.assertIn("WAJIB: jangan diusulkan dipotong", sub.format_list(conn))

    def test_month_aware_total_drops_a_contract_after_its_last_month(self):
        conn = connect(":memory:")
        sub.upsert(conn, "coway-cs", "Coway CS", 400_000, "mega-5855", ends="2027-01")
        sub.upsert(conn, "netflix", "Netflix", 186_000, "jenius-0480")
        self.assertEqual((sub.active_total(conn, "2027-01"), sub.active_total(conn, "2027-02"), sub.active_total(conn)),
                         (586_000, 186_000, 586_000))
        with self.assertRaises(ValueError):
            sub.upsert(conn, "x", "X", 1, "a", ends="2027-13")


if __name__ == "__main__":
    unittest.main()
