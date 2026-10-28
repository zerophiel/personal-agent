import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_roadmap import TODAY, full_world, statement  # noqa: E402

from vault_tools import card_installments as ci  # noqa: E402
from vault_tools import reports  # noqa: E402
from vault_tools import subscriptions as sub  # noqa: E402
from vault_tools import tools  # noqa: E402


def world():
    conn = full_world()
    tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 10_000_000)
    tools.upsert_card(conn, "cimb-2", "CIMB", "2222", 5, 5, 10_000_000)
    statement(conn, 1, 8_000_000, 800_000)
    statement(conn, 2, 3_000_000, 300_000)
    ci.record(conn, "bca-1", "2026-10-05", [{"description": "TOKOPEDIA", "amount": 1_000_000, "seq": 3, "total": 12}])
    sub.upsert(conn, "spotify", "Spotify", 119_900, "bca-1")
    return conn


class Reports(unittest.TestCase):
    def test_every_command_in_the_menu_has_a_report_and_renders(self):
        conn = world()
        for name in reports.NAMES:
            text = reports.build(conn, name, TODAY)
            self.assertTrue(text.strip(), name)
            self.assertLess(len(text), 20000, name)

    def test_unknown_report_is_refused(self):
        with self.assertRaises(ValueError):
            reports.build(world(), "rincian", TODAY)

    def test_tagihan_lists_balance_minimum_and_days_left_without_full_numbers(self):
        text = reports.build(world(), "tagihan", TODAY)
        self.assertIn("BCA ...1111: sisa Rp 8.000.000, minimum Rp 800.000", text)
        self.assertIn("Total sisa: Rp 11.000.000", text)
        self.assertNotIn("106879418405", text)

    def test_lewat_is_shown_for_an_overdue_bill(self):
        conn = world()
        text = reports.build(conn, "tagihan", date(2026, 12, 1))
        self.assertIn("LEWAT", text)

    def test_cicilan_and_help_mention_what_matters(self):
        conn = world()
        self.assertIn("Spotify", reports.build(conn, "cicilan", TODAY))
        self.assertIn("/rencana", reports.HELP)
        self.assertIn("Nomor lengkap tidak pernah saya lihat", reports.HELP)


if __name__ == "__main__":
    unittest.main()
