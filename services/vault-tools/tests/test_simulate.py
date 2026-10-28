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
    def test_free_cash_matches_the_hand_calculation(self):
        r = simulate.simulate(world(), TODAY)
        self.assertEqual(r["rows"][0]["free"], 42_000_000 - 11_115_000 - 5_701_000 - 9_000_000 - 3_000_000)    # 13.184.000
        self.assertEqual(len(r["rows"]), 12)

    def test_each_lever_moves_free_cash_by_exactly_its_amount(self):
        base = simulate.simulate(world(), TODAY)["rows"][0]["free"]
        self.assertEqual(simulate.simulate(world(), TODAY, hemat=1_000_000)["rows"][0]["free"], base + 1_000_000)
        self.assertEqual(simulate.simulate(world(), TODAY, belanja_kartu=2_000_000)["rows"][0]["free"], base - 2_000_000)
        self.assertEqual(simulate.simulate(world(), TODAY, reserve=1_000_000)["rows"][0]["free"], base + 2_000_000)

    def test_extra_money_now_clears_cards_sooner_and_costs_less_interest(self):
        a = simulate.simulate(world(), TODAY, months=24)
        b = simulate.simulate(world(), TODAY, ekstra_sekarang=8_000_000, months=24)
        self.assertLess(b["interest"], a["interest"])
        self.assertLessEqual(b["rows"][0]["balance"], a["rows"][0]["balance"] - 8_000_000 + 1)
        self.assertTrue(b["paid_off_month"] is None or a["paid_off_month"] is None or b["paid_off_month"] <= a["paid_off_month"])

    def test_deferring_the_pot_frees_cash_now_and_raises_the_deposit_later(self):
        a = simulate.simulate(world(), TODAY)
        b = simulate.simulate(world(), TODAY, tunda_pot=2)
        self.assertEqual(b["rows"][0]["free"], a["rows"][0]["free"] + 9_000_000)
        self.assertEqual(b["rows"][1]["free"], a["rows"][1]["free"] + 9_000_000)
        self.assertGreater(b["rows"][2]["pot"], 9_000_000)                      # the same Rp 135M over fewer deposits
        self.assertEqual(b["rows"][2]["pot"], 10_385_000)                       # 135M / 13 deposits, rounded up to Rp 1.000
        one = simulate.simulate(world(), TODAY, tunda_pot=1)
        self.assertEqual(one["rows"][1]["pot"], 9_643_000)                      # the same figure the plan's "Opsi B" quotes

    def test_a_negative_month_adds_to_the_balance_and_the_text_says_so(self):
        base = simulate.simulate(world(), TODAY)
        sc = simulate.simulate(world(), TODAY, belanja_kartu=20_000_000)
        self.assertLess(sc["rows"][0]["free"], 0)
        self.assertGreater(sc["rows"][0]["balance"], base["rows"][0]["balance"])
        text = simulate.format_result(base, sc)
        self.assertIn("menambah saldo kartu", text)
        self.assertIn("NAIK", text)

    def test_the_text_is_plain_facts_with_a_baseline(self):
        w = world()
        text = simulate.format_result(simulate.simulate(w, TODAY), simulate.simulate(w, TODAY, hemat=500_000, ekstra_sekarang=7_000_000))
        self.assertIn("Tanpa perubahan:", text)
        self.assertIn("Dengan skenario:", text)
        self.assertIn("penghematan Rp 500.000/bulan", text)
        self.assertIn("bayar ekstra sekarang Rp 7.000.000", text)
        self.assertIn("Selisih bunga: hemat", text)

    def test_needs_a_salary(self):
        with self.assertRaises(ValueError):
            simulate.simulate(connect(":memory:"), TODAY)


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
            self.assertIn("SKENARIO: penghematan Rp 1.000.000/bulan", out)

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


if __name__ == "__main__":
    unittest.main()
