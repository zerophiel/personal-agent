import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_roadmap import TODAY, full_world, statement  # noqa: E402

from vault_tools import card_installments as ci  # noqa: E402
from vault_tools import roadmap as rm  # noqa: E402
from vault_tools import tools  # noqa: E402


def world():
    conn = full_world()
    tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 10_000_000, interest_bp_month=275)
    statement(conn, 1, 8_000_000, 800_000)               # statement_date 2026-10-05
    return conn


ITEMS = [{"description": "TOKOPEDIA CICILAN", "amount": 1_000_000, "seq": 3, "total": 12},
         {"description": "iPhone EZ Pay", "amount": 2_500_000, "seq": 11, "total": 12}]


class Installments(unittest.TestCase):
    def test_records_and_derives_remaining_months_and_end(self):
        conn = world()
        msg = ci.record(conn, "bca-1", "2026-10-05", ITEMS)
        self.assertIn("2 cicilan tercatat", msg)
        self.assertIn("Rp 3.500.000/bulan", msg)
        a = {x["description"]: x for x in ci.active(conn)}
        self.assertEqual((a["TOKOPEDIA CICILAN"]["left"], a["TOKOPEDIA CICILAN"]["remaining"], a["TOKOPEDIA CICILAN"]["ends"]),
                         (9, 9_000_000, "2027-07-05"))
        self.assertEqual(a["iPhone EZ Pay"]["left"], 1)

    def test_a_newer_statement_refreshes_and_one_that_drops_an_item_finishes_it(self):
        conn = world()
        ci.record(conn, "bca-1", "2026-10-05", ITEMS)
        conn.execute("INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,fees,total_due,"
                     "minimum_due,reconciled,recon_diff,ingested_at) VALUES (1,?,'2026-11-05','2026-11-25',0,0,5,0,5,1,1,0,'t')", ("9" * 64,))
        conn.commit()
        self.assertEqual(len(ci.active(conn)), 0)                 # November statement refreshed nothing: both treated as finished
        ci.record(conn, "bca-1", "2026-11-05", [{"description": "TOKOPEDIA CICILAN", "amount": 1_000_000, "seq": 4, "total": 12}])
        act = ci.active(conn)
        self.assertEqual([(x["description"], x["seq"]) for x in act], [("TOKOPEDIA CICILAN", 4)])
        ci.record(conn, "bca-1", "2026-10-05", [{"description": "TOKOPEDIA CICILAN", "amount": 1_000_000, "seq": 3, "total": 12}])
        self.assertEqual(ci.active(conn)[0]["seq"], 4)             # an older statement never rolls it back

    def test_same_installment_worded_differently_is_one_row(self):
        """Regression: 'Tokopedia 6/18' and 'Tokopedia 200244 6/18' were stored twice."""
        conn = world()
        ci.record(conn, "bca-1", "2026-10-05", [{"description": "Tokopedia", "amount": 200_244, "seq": 6, "total": 18}])
        ci.record(conn, "bca-1", "2026-10-05", [{"description": "Tokopedia 200244 6/18", "amount": 200_244, "seq": 6, "total": 18}])
        self.assertEqual(len(ci.active(conn)), 1)
        self.assertEqual(ci.monthly_total(conn), 200_244)
        ci.record(conn, "bca-1", "2026-10-05", [{"description": "A", "amount": 500_000, "seq": 1, "total": 6},
                                                {"description": "B", "amount": 500_000, "seq": 2, "total": 6}])
        self.assertEqual(ci.monthly_total(conn), 1_200_244)              # two equal installments in one statement stay two

    def test_last_payment_is_not_active(self):
        conn = world()
        ci.record(conn, "bca-1", "2026-10-05", [{"description": "X", "amount": 500_000, "seq": 12, "total": 12}])
        self.assertEqual(ci.active(conn), [])
        self.assertEqual(ci.format_list(conn), "Tidak ada cicilan kartu yang tercatat aktif.")

    def test_rejects_nonsense(self):
        conn = world()
        for seq, total in ((13, 12), (0, 12), (1, 1), (1, 99)):
            with self.assertRaises(ValueError, msg=(seq, total)):
                ci.record(conn, "bca-1", "2026-10-05", [{"description": "X", "amount": 1000, "seq": seq, "total": total}])
        with self.assertRaises(ValueError):
            ci.record(conn, "nope", "2026-10-05", ITEMS)
        with self.assertRaises(ValueError):
            ci.record(conn, "bca-1", "2026-10-05", [{"description": "X", "amount": 0, "seq": 1, "total": 3}])

    def test_roadmap_counts_them_and_shrinks_card_capacity(self):
        base = rm.roadmap(world(), TODAY)
        conn = world()
        ci.record(conn, "bca-1", "2026-10-05", ITEMS)
        r = rm.roadmap(conn, TODAY)
        self.assertEqual(r["capacity"], base["capacity"] - 3_500_000)
        by = {i["alias"]: i for i in r["items"]}
        self.assertEqual(by["bca-1: TOKOPEDIA CICILAN"]["kind"], "cicilan kartu")
        self.assertEqual(r["total_remaining"], base["total_remaining"] + 9_000_000 + 2_500_000)
        self.assertIn("2027-07-05", [d for d, _, _ in r["freed"]])
        self.assertIn("cicilan kartu", rm.format_roadmap(r))


if __name__ == "__main__":
    unittest.main()
