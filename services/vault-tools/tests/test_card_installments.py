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


class Overview(unittest.TestCase):
    def test_shows_what_is_recorded_without_any_full_number(self):
        from datetime import date
        conn = world()
        conn.execute("UPDATE statements SET paid_amount=total_due, paid_at='2026-10-28' WHERE card_id=1")
        conn.commit()
        text = tools.data_overview(conn, date(2026, 10, 28))
        self.assertIn("bca-1 | BCA | 1111", text)
        self.assertIn("LUNAS", text)
        self.assertIn("cicilan-mobil | MTF | Rp 5.701.000 | 19 | autodebit | mandiri-utama", text)
        self.assertIn("hutang-teman", text)
        self.assertIn("ipl", text)
        self.assertNotIn("106879418405", text)


class OneCardOneAlias(unittest.TestCase):
    def test_the_same_card_cannot_be_registered_under_a_second_alias(self):
        """Regression: 'bca-blibli' and 'jenius-kk' duplicated the BCA and Jenius cards, doubling bills and installments."""
        conn = world()
        with self.assertRaises(ValueError) as cm:
            tools.upsert_card(conn, "bca-blibli", "bca", "1111", 5, 25, 10_000_000)
        self.assertIn("bca-1", str(cm.exception))
        tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 12_000_000)                      # updating the same alias is fine
        tools.upsert_card(conn, "cimb-1111", "CIMB", "1111", 5, 20, 5_000_000)                   # same digits, other bank: allowed
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM cards").fetchone()[0], 2)


class LinkPayees(unittest.TestCase):
    def test_cards_are_pointed_at_the_numbers_the_owner_registered(self):
        from vault_tools.payee_vault import PayeeVault
        conn = world()
        tools.upsert_card(conn, "jenius-0480", "Jenius", "0480", 26, 13, 30_000_000)
        tools.upsert_card(conn, "mandiri-4365", "Mandiri", "4365", 16, 5, 10_000_000)               # paid through the app: left alone
        self.assertIn("belum didaftarkan", tools.link_card_payees(conn)[0])
        v = PayeeVault(conn, bytes(range(32)))
        v.store("num-1111", "card", "?", "4111111111111111")                                         # matches bca-1 (last4 1111)
        v.store("jenius-akun", "account", "Jenius", "123456784375")
        out = tools.link_card_payees(conn)
        self.assertEqual(sorted(out), ["bca-1 -> num-1111", "jenius-0480 -> jenius-akun"])
        got = {r["alias"]: r["pay_to_alias"] for r in conn.execute("SELECT alias, pay_to_alias FROM cards")}
        self.assertEqual((got["bca-1"], got["jenius-0480"], got["mandiri-4365"]), ("num-1111", "jenius-akun", None))
        self.assertIn("belum didaftarkan", tools.link_card_payees(conn)[0])                         # idempotent


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

    def test_only_a_scanned_statement_can_end_an_installment(self):
        conn = world()
        ci.record(conn, "bca-1", "2026-10-05", ITEMS)
        conn.execute("INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,fees,total_due,"
                     "minimum_due,reconciled,recon_diff,ingested_at) VALUES (1,?,'2026-11-05','2026-11-25',0,0,5,0,5,1,1,0,'t')", ("9" * 64,))
        conn.commit()
        self.assertEqual(len(ci.active(conn)), 2)                 # November was never read for installments: proves nothing
        ci.record(conn, "bca-1", "2026-11-05", [{"description": "TOKOPEDIA CICILAN", "amount": 1_000_000, "seq": 4, "total": 12}])
        self.assertEqual([(x["description"], x["seq"]) for x in ci.active(conn)], [("TOKOPEDIA CICILAN", 4)])   # the other is gone
        ci.record(conn, "bca-1", "2026-10-05", [{"description": "TOKOPEDIA CICILAN", "amount": 1_000_000, "seq": 3, "total": 12}])
        self.assertEqual(ci.active(conn)[0]["seq"], 4)             # an older statement never rolls it back
        ci.record(conn, "bca-1", "2026-12-05", [])                 # a statement with no installments at all
        self.assertEqual(ci.active(conn), [])

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

    def test_roadmap_counts_them_without_double_counting(self):
        from vault_tools import simulate
        base = rm.roadmap(world(), TODAY)
        conn = world()
        ci.record(conn, "bca-1", "2026-10-05", ITEMS)
        r = rm.roadmap(conn, TODAY)
        self.assertEqual(r["capacity"], base["capacity"])                 # this month's instalments are inside the open bill
        self.assertEqual(simulate.simulate(conn, TODAY)["rows"][1]["new"], 3_500_000)   # and on the next one (12/12 + 4/12)
        by = {i["alias"]: i for i in r["items"]}
        self.assertEqual(by["bca-1: TOKOPEDIA CICILAN"]["kind"], "cicilan kartu")
        self.assertEqual(r["total_remaining"], base["total_remaining"] + 9_000_000 + 2_500_000)
        self.assertIn("2027-07-05", [d for d, _, _ in r["freed"]])
        self.assertIn("cicilan kartu", rm.format_roadmap(r))


if __name__ == "__main__":
    unittest.main()
