import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import mutations as mu  # noqa: E402
from vault_tools import tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402
from vault_tools.payee_vault import PayeeVault  # noqa: E402

TODAY = date(2026, 10, 27)          # payday 2026-10-30
DUE = "2028-01-15"
TARGET = 135_000_000


def setup(salary=20_000_000):
    conn = connect(":memory:")
    v = PayeeVault(conn, bytes(range(32)))
    v.store("pot-rek", "account", "BCA", "1234567890")
    v.store("teman-rek", "account", "Mandiri", "9876543210")
    v.store("num-1111", "card", "?", "4111 1111 1111 1111")
    conn.execute("INSERT INTO accounts(alias,bank,kind,last4) VALUES ('pot','BCA','pool','7890')")
    conn.execute("INSERT INTO accounts(alias,bank,kind,last4) VALUES ('main','BCA','main','1234')")
    conn.commit()
    tools.set_threshold(conn, "net_salary", salary)
    return conn


def fund(conn, **kw):
    args = dict(alias="hutang-teman", target=TARGET, due_date=DUE, pool_alias="pot", pool_pay_to_alias="pot-rek",
                creditor_pay_to_alias="teman-rek", saved_so_far=0, today=TODAY)
    args.update(kw)
    return tools.upsert_sinking_fund(conn, **args)


def row(conn, alias="hutang-teman"):
    return conn.execute("SELECT * FROM sinking_funds WHERE alias=?", (alias,)).fetchone()


HOL = tools.id_holidays(2026) | tools.id_holidays(2027) | tools.id_holidays(2028)


class Math(unittest.TestCase):
    def test_fifteen_paydays_from_oct_2026_to_dec_2027(self):
        self.assertEqual(tools.sinking_paydays_left(date(2026, 10, 30), date(2028, 1, 15), HOL), 15)

    def test_last_contribution_must_land_before_due_buffer(self):
        # due 2028-01-31 is also a payday, but the buffer (3 days) excludes it: Jan payday not counted
        self.assertEqual(tools.sinking_paydays_left(date(2027, 12, 31), date(2028, 1, 31), HOL), 1)
        self.assertEqual(tools.sinking_paydays_left(date(2028, 1, 31), date(2028, 1, 31), HOL), 0)

    def test_per_month_exact_and_rounded_up(self):
        conn = setup()
        fund(conn)
        s = tools.sinking_required(conn, row(conn), date(2026, 10, 30), HOL)
        self.assertEqual((s["saved"], s["remaining"], s["paydays_left"], s["per_month"]), (0, TARGET, 15, 9_000_000))
        fund(conn, saved_so_far=15_000_000)
        self.assertEqual(tools.sinking_required(conn, row(conn), date(2026, 10, 30), HOL)["per_month"], 8_000_000)
        fund(conn, saved_so_far=1)       # 134,999,999 / 15 = 8,999,999.93 -> next Rp 1.000
        self.assertEqual(tools.sinking_required(conn, row(conn), date(2026, 10, 30), HOL)["per_month"], 9_000_000)
        fund(conn, saved_so_far=3_333_333)   # 131,666,667 / 15 = 8,777,777.8 -> 8,778,000
        self.assertEqual(tools.sinking_required(conn, row(conn), date(2026, 10, 30), HOL)["per_month"], 8_778_000)

    def test_contributions_over_the_horizon_cover_the_target(self):
        conn = setup()
        fund(conn, saved_so_far=3_333_333)
        s = tools.sinking_required(conn, row(conn), date(2026, 10, 30), HOL)
        self.assertGreaterEqual(s["per_month"] * s["paydays_left"] + 3_333_333, TARGET)

    def test_deposits_on_pool_account_count_only_when_categorized_and_after_start(self):
        conn = setup()
        fund(conn)
        mu.record_mutations(conn, "pot", "a" * 64, "2026-10-01", "2026-11-30", None, None, [
            {"date": "2026-10-28", "description": "SETOR DARI MAIN", "amount": 9_000_000},
            {"date": "2026-10-20", "description": "SETORAN LAMA", "amount": 5_000_000},      # before the fund existed
            {"date": "2026-11-05", "description": "BUNGA", "amount": 12_000}])
        self.assertEqual(tools.sinking_saved(conn, row(conn)), 0)                         # nothing categorized yet
        for r in conn.execute("SELECT id, merchant FROM transactions").fetchall():
            if "SETOR" in r["merchant"]:
                mu.set_category(conn, r["id"], "sinking:hutang-teman")
        self.assertEqual(tools.sinking_saved(conn, row(conn)), 9_000_000)                  # old row is before saved_asof? 10-20 < 10-27


class Validation(unittest.TestCase):
    def test_pool_must_be_pool_account_and_payees_must_be_accounts(self):
        conn = setup()
        with self.assertRaises(ValueError):
            fund(conn, pool_alias="main")                       # not a pool account
        with self.assertRaises(ValueError):
            fund(conn, pool_alias="ghost")
        with self.assertRaises(ValueError):
            fund(conn, pool_pay_to_alias="num-1111")            # a card number is not a pot account
        with self.assertRaises(ValueError):
            fund(conn, creditor_pay_to_alias="ghost")
        for bad in ({"due_date": "2026-10-01"}, {"target": 0}, {"saved_so_far": -1}):
            with self.assertRaises(ValueError):
                fund(conn, **bad)

    def test_upsert_updates_without_losing_creditor(self):
        conn = setup()
        fund(conn)
        fund(conn, creditor_pay_to_alias=None, target=140_000_000)
        r = row(conn)
        self.assertEqual((r["target"], r["creditor_pay_to"]), (140_000_000, "teman-rek"))


class InThePlan(unittest.TestCase):
    def test_monthly_contribution_goes_to_the_pool_account_in_the_plan(self):
        conn = setup(20_000_000)
        fund(conn)
        snap = tools.generate_payday_plan(conn, TODAY)
        t = [x for x in snap["transfers"] if x["to_alias"] == "hutang-teman"][0]
        self.assertEqual((t["amount"], t["pay_to"], t["method"]), (9_000_000, "pot-rek", "transfer"))
        self.assertEqual(snap["cash_to_hold"], 11_000_000)
        self.assertNotIn("1234567890", str(snap))                # the number itself never enters the plan
        self.assertIn("hutang-teman", tools.summarize_plan(snap))

    def test_shortfall_is_reported_not_hidden(self):
        conn = setup(5_000_000)                                  # salary cannot cover Rp 9.000.000
        fund(conn)
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertEqual(snap["transfers"][0]["amount"], 5_000_000)
        self.assertEqual(snap["unfunded"][0]["amount"], 4_000_000)
        self.assertTrue(snap["warnings"])

    def test_final_window_tops_up_then_reminds_to_pay_from_the_pool(self):
        conn = setup(10_000_000)
        fund(conn, saved_so_far=130_000_000, today=date(2027, 12, 20))
        snap = tools.generate_payday_plan(conn, date(2027, 12, 20))
        self.assertEqual(snap["payday"], "2027-12-31")            # still before the 15 Jan due date
        self.assertEqual([(t["to_alias"], t["amount"]) for t in snap["transfers"]], [("hutang-teman", 5_000_000)])
        text = " ".join(snap["reminders"])
        self.assertIn("JATUH TEMPO 2028-01-15", text)
        self.assertIn("bayar Rp 135.000.000", text)
        self.assertIn("dari rekening pot pot", text)
        self.assertIn("+ setoran gajian ini Rp 5.000.000", text)
        self.assertEqual(snap["cash_to_hold"], 5_000_000)         # only the top-up came from salary
        self.assertEqual(snap["warnings"], [])                    # 130M + 5M reaches the target
        self.assertIn("JATUH TEMPO", tools.summarize_plan(snap))

    def test_final_window_warns_when_pot_cannot_reach_target(self):
        conn = setup(10_000_000)
        fund(conn, saved_so_far=120_000_000, today=date(2027, 12, 20))   # needs 15M, salary only 10M
        snap = tools.generate_payday_plan(conn, date(2027, 12, 20))
        self.assertEqual(snap["transfers"][0]["amount"], 10_000_000)
        self.assertTrue(any("kurang Rp 5.000.000" in w for w in snap["warnings"]))

    def test_status_text(self):
        conn = setup()
        fund(conn, saved_so_far=15_000_000)
        s = tools.sinking_status(conn, TODAY)
        self.assertIn("terkumpul Rp 15.000.000 (11%)", s)
        self.assertIn("setoran Rp 8.000.000/bulan selama 15 gajian", s)
        self.assertEqual(tools.sinking_status(setup(), TODAY), "Belum ada dana terikat.")


if __name__ == "__main__":
    unittest.main()
