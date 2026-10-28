import os
import sqlite3
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_roadmap import TODAY, full_world, statement  # noqa: E402

from vault_tools import roadmap as rm  # noqa: E402
from vault_tools import simulate, tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402


class Engine(unittest.TestCase):
    def test_even_split_is_unchanged(self):
        self.assertEqual(tools.pot_schedule(135_000_000, 15), [9_000_000] * 15)

    def test_small_first_then_catch_up_still_reaches_the_target(self):
        s = tools.pot_schedule(135_000_000, 15, 2_000_000, 8)
        self.assertEqual(s[:8], [2_000_000] * 8)
        self.assertGreaterEqual(sum(s), 135_000_000)                                  # never short of the target
        self.assertLess(sum(s), 135_000_000 + 7 * 1000)                               # rounding only
        self.assertEqual(s[8], 17_000_000)                                            # (135M - 8 x 2M) / 7 remaining paydays
        self.assertTrue(all(x == s[8] for x in s[8:14]))                              # the catch-up phase is even

    def test_a_low_phase_cannot_swallow_every_payday(self):
        self.assertEqual(tools.pot_schedule(135_000_000, 15, 1_000_000, 15), [9_000_000] * 15)      # ignored: nothing left to catch up with
        self.assertEqual(tools.pot_schedule(135_000_000, 15, 1_000_000, 0), [9_000_000] * 15)

    def test_zero_deposits_for_a_while_is_allowed(self):
        s = tools.pot_schedule(135_000_000, 15, 0, 3)
        self.assertEqual(s[:3], [0, 0, 0])
        self.assertEqual(s[3], 11_250_000)                                            # 135M / 12


class Fund(unittest.TestCase):
    def test_the_plan_uses_the_low_amount_now_and_tells_the_catch_up_figure(self):
        conn = full_world()
        out = tools.set_pot_schedule(conn, "hutang-teman", 3_000_000, "2027-06", TODAY)
        self.assertIn("setoran fase awal Rp 3.000.000/bulan sampai 2027-06", out)
        self.assertIn("lalu sekitar", out)
        f = conn.execute("SELECT * FROM sinking_funds").fetchone()
        s = tools.sinking_required(conn, f, date(2026, 10, 30), set())
        self.assertEqual(s["per_month"], 3_000_000)
        self.assertEqual(s["low_cycles"], 9)                                          # Oct 2026 .. Jun 2027
        self.assertGreater(s["later_per_month"], 9_000_000)
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertTrue(any("Pot hutang-teman: setoran fase awal Rp 3.000.000" in r for r in snap["reminders"]))
        self.assertIn(("hutang-teman", 3_000_000), [(t["to_alias"], t["amount"]) for t in snap["transfers"] if t["reason"] == "transfer pool"])

    def test_validation_and_reset(self):
        conn = full_world()
        for amount, month in ((1_000_000, "2026-09"), (1_000_000, "2028-01"), (1_000_000, "2030-01"), (1_000_000, "bukan"), (-5, "2027-06")):
            with self.assertRaises(ValueError, msg=(amount, month)):
                tools.set_pot_schedule(conn, "hutang-teman", amount, month, TODAY)
        with self.assertRaises(ValueError):
            tools.set_pot_schedule(conn, "ghost", 1, "2027-06", TODAY)
        tools.set_pot_schedule(conn, "hutang-teman", 3_000_000, "2027-06", TODAY)
        self.assertIn("kembali rata", tools.set_pot_schedule(conn, "hutang-teman", None, None, TODAY))
        f = conn.execute("SELECT * FROM sinking_funds").fetchone()
        self.assertEqual(tools.sinking_required(conn, f, date(2026, 10, 30), set())["per_month"], 9_000_000)

    def test_an_old_ledger_gets_the_new_columns(self):
        with __import__("tempfile").TemporaryDirectory() as d:
            path = os.path.join(d, "old.db")
            c = sqlite3.connect(path)
            c.execute("CREATE TABLE sinking_funds (alias TEXT PRIMARY KEY, target INTEGER, due_date TEXT, pool_alias TEXT, pool_pay_to TEXT,"
                      " creditor_pay_to TEXT, saved_so_far INTEGER, saved_asof TEXT, note TEXT)")
            c.commit()
            c.close()
            conn = connect(path)
            self.assertTrue({"low_amount", "low_until"} <= {r["name"] for r in conn.execute("PRAGMA table_info(sinking_funds)")})


class Consumers(unittest.TestCase):
    def world(self):
        conn = full_world()
        tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 30_000_000, interest_bp_month=200)
        statement(conn, 1, 20_000_000, 2_000_000)
        return conn

    def test_simulator_low_phase_raises_early_free_cash_and_lowers_it_later(self):
        a = simulate.simulate(self.world(), TODAY, months=15)
        b = simulate.simulate(self.world(), TODAY, pot_awal=2_000_000, pot_awal_bulan=8, months=15)
        self.assertEqual(b["rows"][0]["free"], a["rows"][0]["free"] + 7_000_000)
        self.assertEqual(b["rows"][0]["pot"], 2_000_000)
        self.assertGreater(b["rows"][9]["pot"], 9_000_000)
        self.assertLess(b["rows"][9]["free"], a["rows"][9]["free"])
        self.assertLess(b["interest"], a["interest"])                                 # the cards are paid down while the pot waits
        self.assertAlmostEqual(sum(r["pot"] for r in b["rows"]), 135_000_000, delta=10_000)   # the whole target is still saved

    def test_the_stored_schedule_is_used_by_the_simulator_and_the_roadmap(self):
        conn = self.world()
        tools.set_pot_schedule(conn, "hutang-teman", 2_000_000, "2027-05", TODAY)
        r = simulate.simulate(conn, TODAY, months=15)
        self.assertEqual(r["rows"][0]["pot"], 2_000_000)
        rd = rm.roadmap(conn, TODAY)
        flat = rm.roadmap(self.world(), TODAY)
        self.assertEqual(rd["capacity"], flat["capacity"] + 7_000_000)               # more room now (the pot waits) ...
        self.assertIsNotNone(rd["card_result"])

    def test_the_text_shows_both_deposit_levels(self):
        conn = self.world()
        text = simulate.format_result(simulate.simulate(conn, TODAY), simulate.simulate(conn, TODAY, pot_awal=2_000_000, pot_awal_bulan=6))
        self.assertIn("setoran pot awal Rp 2.000.000/bulan selama 6 bulan", text)
        self.assertIn("Setoran pot per bulan:", text)


if __name__ == "__main__":
    unittest.main()
