import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import health as hl  # noqa: E402
from vault_tools import roadmap as rm  # noqa: E402
from vault_tools import tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402
from vault_tools.payee_vault import PayeeVault  # noqa: E402

TODAY = date(2026, 10, 27)


def statement(conn, card_id, total, minimum, due="2026-11-20"):
    conn.execute(
        "INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,fees,total_due,"
        "minimum_due,reconciled,recon_diff,ingested_at) VALUES (?,?,?,?,0,0,?,0,?,?,1,0,'t')",
        (card_id, f"{card_id}" * 64, "2026-10-05", due, total, total, minimum))
    conn.commit()


class Dates(unittest.TestCase):
    def test_add_months_and_next_due_clamp_to_month_end(self):
        self.assertEqual(rm.add_months(date(2026, 1, 31), 1, 31), date(2026, 2, 28))
        self.assertEqual(rm.add_months(date(2026, 11, 2), 18, 2), date(2028, 5, 2))
        self.assertEqual(rm.add_months(date(2026, 12, 15), 1), date(2027, 1, 15))
        self.assertEqual(rm.next_due(2, date(2026, 10, 27)), date(2026, 11, 2))
        self.assertEqual(rm.next_due(30, date(2026, 10, 27)), date(2026, 10, 30))
        self.assertEqual(rm.next_due(31, date(2026, 2, 10)), date(2026, 2, 28))
        self.assertEqual(rm.next_due(27, date(2026, 10, 27)), date(2026, 10, 27))        # due today still counts


class LatestStatement(unittest.TestCase):
    def test_an_older_statement_entered_later_never_becomes_the_current_bill(self):
        """Regression: back-filling Jan-Sep after Oct made the September bill look like the open one (49.8M vs 25.6M)."""
        conn = full_world()
        tools.upsert_card(conn, "j-1", "Jenius", "0480", 26, 13, 30_000_000)
        ins = ("INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,fees,total_due,"
               "minimum_due,reconciled,recon_diff,ingested_at) VALUES (1,?,?,?,0,0,?,0,?,?,1,0,'t')")
        conn.execute(ins, ("a" * 64, "2026-10-26", "2026-11-13", 9_000_000, 9_000_000, 2_000_000))     # entered first (newest)
        conn.execute(ins, ("b" * 64, "2026-09-26", "2026-10-13", 40_000_000, 40_000_000, 4_000_000))   # back-filled later (older)
        conn.commit()
        r = rm.roadmap(conn, TODAY)
        self.assertEqual(r["card_total"], 9_000_000)
        self.assertEqual(hl.debt_load(conn)["total_debt"], 19 * 5_701_000 + 9_000_000)
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertIn("Rp 9.000.000", " ".join(snap["advice"] + snap["warnings"] + [tools.summarize_plan(snap)]))
        self.assertNotIn("40.000.000", tools.summarize_plan(snap))


class Recurring(unittest.TestCase):
    def test_subscriptions_do_not_shrink_this_paydays_cash(self):
        """Regression: subscriptions sit inside the open card statements; subtracting them again from the same month's cash
        invented a deficit."""
        from vault_tools import subscriptions as sub
        base = rm.roadmap(full_world(), TODAY)["capacity"]
        conn = full_world()
        sub.upsert(conn, "apple-one", "Apple One", 319_000, "hsbc-1")
        self.assertEqual(rm.roadmap(conn, TODAY)["capacity"], base)


class CardPath(unittest.TestCase):
    def test_avalanche_and_interest_on_the_remainder_only(self):
        conn = full_world()
        tools.set_threshold(conn, "net_salary", 13_000_000 + 11_115_000 + 5_701_000 + 3_000_000 + 9_000_000)   # 13M for the cards
        tools.upsert_card(conn, "a", "BCA", "1111", 5, 25, 10_000_000, interest_bp_month=275)
        tools.upsert_card(conn, "b", "CIMB", "2222", 5, 5, 10_000_000, interest_bp_month=225)
        statement(conn, 1, 8_000_000, 800_000)
        statement(conn, 2, 6_000_000, 600_000)
        r = rm.roadmap(conn, TODAY)["card_result"]
        # cycle 1: A 8.0M and B 5.0M paid, B keeps 1.0M -> interest 22,500; cycle 2 clears it
        self.assertEqual((r["months"], r["interest"], r["left"]), (2, 22_500, 0))


def full_world():
    conn = connect(":memory:")
    PayeeVault(conn, bytes(range(32))).store("pot-rek", "account", "Jago", "106879418405")
    conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('pot','Jago','pool')")
    conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('mandiri-utama','Mandiri','main')")
    conn.commit()
    tools.set_threshold(conn, "net_salary", 42_000_000)
    tools.set_threshold(conn, "living_reserve", 3_000_000)
    for alias, amount in (("les", 3_450_000), ("ipl", 1_600_000), ("sekolah", 6_065_000)):
        tools.upsert_expense(conn, alias, alias + "-va", amount, 1)
    tools.upsert_debt(conn, "cicilan-mobil", "MTF", 19 * 5_701_000, 5_701_000, 19, 2, 815,
                      pay_method="autodebit", debit_account_alias="mandiri-utama")
    tools.upsert_sinking_fund(conn, "hutang-teman", 135_000_000, "2028-01-31", "pot", "pot-rek", today=TODAY)
    return conn


class Roadmap(unittest.TestCase):
    def test_timeline_debt_free_date_and_freed_cash(self):
        conn = full_world()
        tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 10_000_000, interest_bp_month=275)
        tools.upsert_card(conn, "cimb-1", "CIMB", "2222", 5, 5, 10_000_000)
        statement(conn, 1, 8_000_000, 800_000)
        statement(conn, 2, 6_000_000, 600_000)
        r = rm.roadmap(conn, TODAY)
        by = {i["alias"]: i for i in r["items"]}
        self.assertEqual((by["cicilan-mobil"]["ends"], by["cicilan-mobil"]["remaining"]), ("2028-05-02", 108_319_000))
        self.assertEqual((by["hutang-teman"]["ends"], by["hutang-teman"]["remaining"], by["hutang-teman"]["per_month"]),
                         ("2028-01-31", 135_000_000, 9_000_000))
        self.assertEqual(r["capacity"], 42_000_000 - 11_115_000 - 5_701_000 - 3_000_000)       # 22.184.000 before the pot
        self.assertEqual((r["card_result"]["months"], r["card_result"]["interest"], r["card_end"]), (2, 18_360, "2026-12"))
        self.assertEqual(r["debt_free_date"], "2028-05-02")
        self.assertEqual(r["freed"], [("2028-01-31", 9_000_000, "hutang-teman"), ("2028-05-02", 5_701_000, "cicilan-mobil")])
        self.assertEqual(r["total_remaining"], 108_319_000 + 135_000_000 + 14_000_000)
        text = rm.format_roadmap(r)
        self.assertIn("Perkiraan bebas utang: 2028-05-02", text)
        self.assertIn("lunas penuh dalam 2 gajian (bulan tagihan 2026-12)", text)
        self.assertIn("2028-05-02: cicilan-mobil selesai, bebas Rp 5.701.000/bulan (total terbebas Rp 14.701.000/bulan)", text)
        self.assertIn("Asumsi:", text)

    def test_without_cards_only_the_loans_decide_the_date(self):
        r = rm.roadmap(full_world(), TODAY)
        self.assertIsNone(r["card_result"])
        self.assertEqual(r["debt_free_date"], "2028-05-02")
        self.assertNotIn("Kartu:", rm.format_roadmap(r))

    def test_cards_that_cannot_be_cleared_mean_no_debt_free_date(self):
        conn = connect(":memory:")                                                   # nothing ends later to free any cash
        tools.set_threshold(conn, "net_salary", 3_000_000)
        tools.set_threshold(conn, "living_reserve", 3_000_000)                       # capacity 0
        tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 10_000_000)
        statement(conn, 1, 5_000_000, 500_000)
        r = rm.roadmap(conn, TODAY)
        self.assertLessEqual(r["capacity"], 0)
        self.assertIsNone(r["card_result"]["months"])
        self.assertIsNone(r["debt_free_date"])
        text = rm.format_roadmap(r)
        self.assertIn("TIDAK cukup untuk melunasi", text)
        self.assertIn("belum bisa ditentukan", text)

    def test_negative_capacity_now_but_cards_clear_once_the_pot_and_the_car_end(self):
        conn = full_world()
        tools.set_threshold(conn, "net_salary", 20_100_000)                          # capacity 20.1 - 11.115 - 5.701 - 9 - 3 < 0
        tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 10_000_000)
        statement(conn, 1, 5_000_000, 500_000)
        r = rm.roadmap(conn, TODAY)
        self.assertEqual(r["capacity"], 284_000)                                     # all of it goes to the set pot deposit
        self.assertGreater(r["card_result"]["months"], 15)                           # only after the pot ends (Jan 2028)

    def test_unknown_salary_does_not_invent_a_date_when_cards_exist(self):
        conn = connect(":memory:")
        tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 10_000_000)
        statement(conn, 1, 5_000_000, 500_000)
        r = rm.roadmap(conn, TODAY)
        self.assertIsNone(r["capacity"])
        self.assertIsNone(r["debt_free_date"])
        self.assertIn("net_salary belum diset", rm.format_roadmap(r))

    def test_empty_ledger(self):
        r = rm.roadmap(connect(":memory:"), TODAY)
        self.assertEqual((r["items"], r["total_remaining"], r["debt_free_date"]), ([], 0, None))


class CardPayments(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        tools.set_threshold(self.conn, "net_salary", 40_000_000)
        tools.upsert_card(self.conn, "bca-1", "BCA", "1111", 5, 25, 10_000_000, interest_bp_month=275)
        statement(self.conn, 1, 8_000_000, 800_000)

    def pay(self, amount):
        return tools.record_card_payment(self.conn, TODAY, "bca-1", amount)

    def test_partial_then_full_payment(self):
        self.assertEqual(self.pay(3_000_000), "bca-1: dibayar Rp 3.000.000 dari Rp 8.000.000 (minimum Rp 800.000); minimum sudah "
                                              "terpenuhi: tidak telat, tidak ada denda. Sisa Rp 5.000.000 dibawa ke tagihan berikutnya "
                                              "dan berbunga ±Rp 137.500/bulan.")
        row = self.conn.execute("SELECT paid_amount, paid_at FROM statements").fetchone()
        self.assertEqual((row["paid_amount"], row["paid_at"]), (3_000_000, None))
        self.assertEqual(self.pay(5_000_000), "bca-1: LUNAS.")
        self.assertEqual(self.conn.execute("SELECT paid_at FROM statements").fetchone()[0], TODAY.isoformat())

    def test_plan_only_asks_for_what_is_still_owed(self):
        self.pay(3_000_000)
        snap = tools.generate_payday_plan(self.conn, TODAY)
        self.assertEqual([t["amount"] for t in snap["transfers"] if t["to_alias"] == "bca-1"], [5_000_000])   # min (0.8M) is covered
        self.assertIn("LUNASI Rp 5.000.000", " ".join(snap["advice"]))
        self.assertEqual(hl.debt_load(self.conn)["total_debt"], 5_000_000)
        self.assertEqual(hl.debt_load(self.conn)["monthly_payments"], 0)                                   # minimum already met

    def test_a_paid_statement_leaves_the_plan_and_the_roadmap(self):
        self.pay(8_000_000)
        snap = tools.generate_payday_plan(self.conn, TODAY)
        self.assertEqual([t for t in snap["transfers"] if t["to_alias"] == "bca-1"], [])
        self.assertEqual(rm.roadmap(self.conn, TODAY)["cards"], [])

    def test_overpayment_is_flagged_and_bad_input_rejected(self):
        self.assertIn("kelebihan Rp 1.000.000", self.pay(9_000_000))
        with self.assertRaises(ValueError):
            self.pay(1)                                   # nothing unpaid left
        with self.assertRaises(ValueError):
            tools.record_card_payment(self.conn, TODAY, "ghost", 1000)
        with self.assertRaises(ValueError):
            tools.record_card_payment(self.conn, TODAY, "bca-1", 0)
        with self.assertRaises(TypeError):
            tools.record_card_payment(self.conn, TODAY, "bca-1", 10.5)

    def test_v7_ledger_gets_paid_amount(self):
        import sqlite3
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "l.db")
            old = sqlite3.connect(path)
            old.executescript("CREATE TABLE statements (id INTEGER PRIMARY KEY, card_id INTEGER, file_hash TEXT, statement_date TEXT,"
                              " due_date TEXT, previous_balance INTEGER, payments INTEGER, charges INTEGER, fees INTEGER,"
                              " total_due INTEGER, minimum_due INTEGER, reconciled INTEGER, recon_diff INTEGER, ingested_at TEXT, paid_at TEXT);"
                              " INSERT INTO statements VALUES (1,1,'h','a','b',0,0,0,0,100,10,1,0,'t',NULL);")
            old.commit()
            old.close()
            conn = connect(path)
            self.assertEqual(conn.execute("SELECT paid_amount FROM statements").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
