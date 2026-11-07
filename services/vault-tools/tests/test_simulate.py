import asyncio
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_roadmap import TODAY, full_world, statement  # noqa: E402

from vault_tools import reports, simulate, tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402

try:
    from vault_tools.server import create_app
    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False


def world():
    conn = full_world()
    tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 30_000_000, interest_bp_month=200)
    statement(conn, 1, 30_000_000, 3_000_000)
    return conn


class Simulate(unittest.TestCase):
    def test_cycle_one_pays_the_open_statements_from_the_cash_after_bills_living_money_and_the_pot(self):
        r = simulate.simulate(world(), TODAY)
        first = r["rows"][0]
        self.assertEqual(r["payday"], "2026-10-30")
        self.assertEqual(first["cash"], 42_000_000 - 11_115_000 - 5_701_000 - 3_000_000)          # 22.184.000
        self.assertEqual((first["pot"], first["paid"], first["due"]), (9_000_000, 13_184_000, 30_000_000))
        self.assertEqual(first["balance"], 16_816_000 + 336_320)                                   # carried, 2% a month
        self.assertEqual(len(r["rows"]), 12)

    def test_each_lever_moves_the_cash_by_exactly_its_amount(self):
        base = simulate.simulate(world(), TODAY)["rows"]
        self.assertEqual(simulate.simulate(world(), TODAY, reserve=1_000_000)["rows"][0]["cash"], base[0]["cash"] + 2_000_000)
        self.assertEqual(simulate.simulate(world(), TODAY, ekstra_sekarang=5_000_000)["rows"][0]["cash"], base[0]["cash"] + 5_000_000)
        hemat = simulate.simulate(world(), TODAY, hemat=1_000_000)["rows"]
        self.assertEqual(hemat[0]["cash"], base[0]["cash"])                     # the open statements are already printed
        self.assertEqual(hemat[1]["cash"], base[1]["cash"] + 1_000_000)
        spend = simulate.simulate(world(), TODAY, belanja_kartu=2_000_000)["rows"]
        self.assertEqual(spend[0]["due"], base[0]["due"])
        self.assertEqual(spend[1]["due"], base[1]["due"] + 2_000_000)           # spending beyond the living money lands on the next bill

    def test_subscriptions_and_card_instalments_are_not_counted_twice(self):
        """Regression: the open statements already hold this month's subscriptions and instalments; the old model also took
        them from the same month's cash and showed a deficit (and a card balance of 48M) that did not exist."""
        from vault_tools import card_installments as ci
        from vault_tools import subscriptions as sub
        conn = world()
        sub.upsert(conn, "gym", "Gym", 1_500_000, "bca-1")
        sub.upsert(conn, "maybe", "Maybe", 500_000, "bca-1", status="unsure")      # not counted until confirmed
        ci.record(conn, "bca-1", "2026-10-05", [{"description": "HP", "amount": 1_000_000, "seq": 11, "total": 12}])
        a, b = simulate.simulate(world(), TODAY)["rows"], simulate.simulate(conn, TODAY)["rows"]
        self.assertEqual((b[0]["cash"], b[0]["due"]), (a[0]["cash"], a[0]["due"]))   # cycle 1: inside the open statement
        self.assertEqual(b[1]["new"], 1_500_000 + 1_000_000)                     # November statement: gym + instalment 12/12
        self.assertEqual(b[2]["new"], 1_500_000)                                 # the instalment has ended

    def test_a_contract_with_an_end_month_stops_being_charged(self):
        from vault_tools import subscriptions as sub
        conn = world()
        sub.upsert(conn, "coway-cs", "Coway CS", 400_000, "bca-1", ends="2026-12")
        rows = simulate.simulate(conn, TODAY)["rows"]
        self.assertEqual([r["new"] for r in rows[1:4]], [400_000, 400_000, 0])   # Nov and Dec statements, then over

    def test_extra_money_now_clears_cards_sooner_and_costs_less_interest(self):
        a = simulate.simulate(world(), TODAY, months=24)
        b = simulate.simulate(world(), TODAY, ekstra_sekarang=8_000_000, months=24)
        self.assertLess(b["interest"], a["interest"])
        self.assertEqual(b["rows"][0]["balance"], a["rows"][0]["balance"] - 8_000_000 - 160_000)    # 8M less carried at 2%

    def test_deferring_the_pot_frees_cash_now_and_raises_the_deposit_later(self):
        a = simulate.simulate(world(), TODAY)
        b = simulate.simulate(world(), TODAY, tunda_pot=2)
        self.assertEqual([r["pot"] for r in b["rows"][:2]], [0, 0])
        self.assertEqual(b["rows"][0]["paid"], a["rows"][0]["paid"] + 9_000_000)     # the 9M went to the card instead
        self.assertEqual(b["rows"][2]["pot"], 10_385_000)                       # 135M / 13 deposits, rounded up to Rp 1.000
        one = simulate.simulate(world(), TODAY, tunda_pot=1)
        self.assertEqual(one["rows"][1]["pot"], 9_643_000)                      # the same figure the plan's "Opsi B" quotes

    def test_bills_beyond_the_salary_land_on_a_card_and_the_text_says_so(self):
        conn = world()
        tools.set_threshold(conn, "net_salary", 15_000_000)                     # below fixed + car + living money
        r = simulate.simulate(conn, TODAY)
        self.assertEqual(r["rows"][0]["short"], 11_115_000 + 5_701_000 + 3_000_000 - 15_000_000)
        text = simulate.format_result(r, r)
        self.assertIn("ditalangi kartu", text)
        self.assertIn("BELUM lunas", text)

    def test_the_text_is_plain_facts_with_a_baseline(self):
        w = world()
        text = simulate.format_result(simulate.simulate(w, TODAY), simulate.simulate(w, TODAY, hemat=500_000, ekstra_sekarang=7_000_000))
        self.assertIn("Tanpa perubahan:", text)
        self.assertIn("Dengan skenario:", text)
        self.assertIn("penghematan Rp 500.000/bulan mulai tagihan berikutnya", text)
        self.assertIn("bayar ekstra sekarang Rp 7.000.000", text)
        self.assertIn("Selisih bunga: hemat", text)

    def test_needs_a_salary(self):
        with self.assertRaises(ValueError):
            simulate.simulate(connect(":memory:"), TODAY)


class CardsFirstPot(unittest.TestCase):
    def world(self, salary=42_000_000):
        conn = world()
        tools.set_threshold(conn, "net_salary", salary)
        tools.set_pot_schedule(conn, "hutang-teman", None, None, TODAY, pace="sisa")
        return conn

    def test_cards_are_cleared_first_then_the_pot_takes_what_is_left(self):
        r = simulate.simulate(self.world(), TODAY, months=16)
        first, second = r["rows"][0], r["rows"][1]
        self.assertEqual((first["paid"], first["pot"]), (22_184_000, 0))              # all the cash goes to the 30M bill
        self.assertEqual(second["paid"], 7_816_000 + 156_320)                          # the rest + 2%
        self.assertEqual(second["pot"], 22_184_000 - second["paid"])
        self.assertTrue(all(row["pot"] == 22_184_000 for row in r["rows"][2:6]))
        f = r["funds"][0]
        self.assertEqual((f["pace"], f["paydays"], f["at_due"], f["gap"]), ("sisa", 15, 135_000_000, 0))

    def test_cards_first_costs_less_interest_than_a_set_deposit_and_still_meets_the_target(self):
        rata = simulate.simulate(world(), TODAY, months=16)
        sisa = simulate.simulate(world(), TODAY, months=16, pola_pot="sisa")
        self.assertEqual((rata["interest"], sisa["interest"]), (336_320 + 79_366, 156_320))
        self.assertEqual(sisa["funds"][0]["at_due"], 135_000_000)

    def test_a_shortfall_at_the_due_date_is_reported_and_the_due_day_salary_counts_only_when_chosen(self):
        conn = self.world(salary=26_000_000)                                           # 6.184.000 a payday after bills
        r = simulate.simulate(conn, TODAY, months=17)
        f = r["funds"][0]
        self.assertEqual(f["paydays"], 15)
        self.assertGreater(f["gap"], 0)
        self.assertIn("KURANG", simulate.format_result(r, r))
        g = simulate.simulate(conn, TODAY, months=17, gaji_hari_tenggat=True)["funds"][0]
        self.assertEqual(g["paydays"], 16)                       # 31 Jan 2028 is a Monday: that salary lands on the due date
        self.assertEqual(g["at_due"] - f["at_due"], 6_184_000)
        tools.set_pot_schedule(conn, "hutang-teman", None, None, TODAY, due_payday=True)    # the owner's choice, stored
        self.assertEqual(simulate.simulate(conn, TODAY, months=17)["funds"][0]["paydays"], 16)


class EmergencyFund(unittest.TestCase):
    def test_the_buffer_fills_before_the_pot_and_the_card_balances_then_stops(self):
        conn = world()
        tools.set_threshold(conn, "emergency_target", 3_000_000)
        tools.set_threshold(conn, "emergency_monthly", 500_000)
        r = simulate.simulate(conn, TODAY, months=8)
        self.assertEqual([row["ef"] for row in r["rows"]], [500_000] * 6 + [0, 0])
        self.assertEqual(r["rows"][0]["paid"], 13_184_000 - 500_000)
        self.assertEqual(r["emergency"]["saved_end"], 3_000_000)


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class Tools(unittest.TestCase):
    def make(self, d):
        app = create_app(os.path.join(d, "l.db"), bytes(range(32)), "m" * 40, "i" * 40, allowed_hosts=["testserver"], ingest_dir=d, passwords_path=None)
        return lambda n, a=None: json.dumps(asyncio.run(app.state.mcp.call_tool(n, a or {})), default=str)

    def test_simulasi_skenario_through_the_tool(self):
        with tempfile.TemporaryDirectory() as d:
            call = self.make(d)
            call("set_threshold", {"key": "net_salary", "value": 20_000_000})
            out = call("simulasi_skenario", {"hemat_per_bulan": 1_000_000})
            self.assertIn("SKENARIO: penghematan Rp 1.000.000/bulan mulai tagihan berikutnya", out)

    def test_catat_usulan_records_dedupes_and_shows_in_the_report(self):
        with tempfile.TemporaryDirectory() as d:
            call = self.make(d)
            self.assertIn("Usulan #1 tercatat", call("catat_usulan", {"judul": "Ubah format /rincian", "kebutuhan": "Pemilik minta transfer digabung per tujuan"}))
            self.assertIn("sudah tercatat (#1)", call("catat_usulan", {"judul": "ubah format /rincian", "kebutuhan": "lagi"}))
            self.assertIn("Usulan #2 tercatat", call("catat_usulan", {"judul": "Rincian belanja kartu", "kebutuhan": "per kategori"}))


class UsulanReport(unittest.TestCase):
    def test_empty_and_filled(self):
        conn = connect(":memory:")
        self.assertIn("Belum ada", reports.build(conn, "usulan", TODAY))
        conn.execute("INSERT INTO feature_requests(created_at,title,detail) VALUES ('2026-10-28T01:00:00+00:00','Simulasi skenario','tunda pot')")
        conn.commit()
        text = reports.build(conn, "usulan", TODAY)
        self.assertIn("🆕 <b>#1 Simulasi skenario</b>", text)
        self.assertIn("menunggu dikerjakan manusia", text)

    def test_what_was_built_is_shown(self):
        conn = connect(":memory:")
        conn.execute("INSERT INTO feature_requests(created_at,title,detail,status,resolution) VALUES ('2026-10-28T01:00:00+00:00',"
                     "'Rincian per kartu','apa saja di CIMB','selesai','Sudah bisa: tanya apa saja isi tagihan CIMB')")
        conn.commit()
        text = reports.build(conn, "usulan", TODAY)
        self.assertIn("✅ <b>#1 Rincian per kartu</b>", text)
        self.assertIn("➡️ Sudah bisa: tanya apa saja isi tagihan CIMB", text)


if __name__ == "__main__":
    unittest.main()
