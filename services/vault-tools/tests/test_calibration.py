"""Recalibration v2: the payday a plan belongs to, the living money protected from the pot, the cards-first pot, the
emergency fund and the pot balance the owner reads in the bank app."""
import asyncio
import json
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_roadmap import full_world  # noqa: E402

from vault_tools import rincian, tools  # noqa: E402
from vault_tools.payee_vault import PayeeVault  # noqa: E402

try:
    from vault_tools.server import create_app
    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False

HOL = tools.id_holidays(2026) | tools.id_holidays(2027)
NOV_1 = date(2026, 11, 1)


def bill(conn, card_id, stmt, due, total, minimum):
    conn.execute("INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,fees,total_due,"
                 "minimum_due,reconciled,recon_diff,ingested_at) VALUES (?,?,?,?,0,0,?,0,?,?,1,0,'t')",
                 (card_id, f"{card_id}-{stmt}".ljust(64, "x"), stmt, due, total, total, minimum))
    conn.commit()


def amounts(snap):
    out = {}
    for t in snap["transfers"]:
        out[t["to_alias"]] = out.get(t["to_alias"], 0) + t["amount"]
    return out


class PaydayWindow(unittest.TestCase):
    def test_the_first_days_after_payday_still_belong_to_that_payday(self):
        cases = {date(2026, 10, 28): date(2026, 10, 30),   # before payday: the coming one
                 date(2026, 10, 30): date(2026, 10, 30),
                 NOV_1: date(2026, 10, 30),                # the owner pays everything on the 1st
                 date(2026, 11, 6): date(2026, 10, 30),    # 7 days after
                 date(2026, 11, 7): date(2026, 11, 30),    # 8 days after: the next one
                 date(2026, 11, 15): date(2026, 11, 30),
                 date(2027, 1, 2): date(2026, 12, 31)}     # across the year end
        for today, payday in cases.items():
            self.assertEqual(tools.current_payday(today, HOL), payday, today)

    def test_the_plan_asked_on_the_1st_pays_the_bills_of_the_salary_just_received(self):
        conn = full_world()
        tools.upsert_card(conn, "jenius-1", "Jenius", "0480", 26, 13, 30_000_000)
        tools.upsert_card(conn, "hsbc-1", "HSBC", "5915", 19, 4, 48_000_000, interest_bp_month=175)
        bill(conn, 1, "2026-10-26", "2026-11-13", 9_000_000, 2_600_000)
        bill(conn, 2, "2026-10-19", "2026-11-04", 6_000_000, 1_000_000)
        tools.set_pot_schedule(conn, "hutang-teman", None, None, NOV_1, pace="sisa")
        snap = tools.generate_payday_plan(conn, NOV_1)
        self.assertEqual((snap["payday"], snap["next_payday"]), ("2026-10-30", "2026-11-30"))
        paid = amounts(snap)
        self.assertEqual((paid["jenius-1"], paid["hsbc-1"]), (9_000_000, 6_000_000))      # the bills due 4-13 Nov, in full
        self.assertEqual(paid["hutang-teman"], 22_184_000 - 15_000_000)                   # the pot gets what is left
        self.assertTrue({"les-va", "ipl-va", "sekolah-va", "cicilan-mobil"} <= set(paid))   # school and lessons on the 1st, car on the 2nd
        self.assertFalse([r for r in snap["reminders"] if "SUDAH LEWAT" in r or "MENDESAK" in r])


class ReserveAndPot(unittest.TestCase):
    def test_a_set_pot_deposit_can_no_longer_eat_the_living_money(self):
        conn = full_world()                                    # living money 3M; pot 9M a payday ('rata')
        tools.set_threshold(conn, "net_salary", 20_000_000)
        snap = tools.generate_payday_plan(conn, date(2026, 10, 27))
        self.assertEqual(amounts(snap)["hutang-teman"], 20_000_000 - 11_115_000 - 5_701_000 - 3_000_000)   # only what is above it
        self.assertEqual(snap["cash_to_hold"], 3_000_000)
        self.assertTrue(any("dicadangkan untuk hidup harian" in w for w in snap["warnings"]))

    def test_cards_first_pot_takes_only_what_is_left_after_the_full_bills(self):
        conn = full_world()
        tools.set_pot_schedule(conn, "hutang-teman", None, None, NOV_1, pace="sisa")
        tools.upsert_card(conn, "jenius-1", "Jenius", "0480", 26, 13, 30_000_000)
        bill(conn, 1, "2026-10-26", "2026-11-13", 9_000_000, 2_600_000)
        snap = tools.generate_payday_plan(conn, NOV_1)
        paid = amounts(snap)
        self.assertEqual(paid["jenius-1"], 9_000_000)                                       # the bill in full first
        self.assertEqual(paid["hutang-teman"], 42_000_000 - 11_115_000 - 5_701_000 - 3_000_000 - 9_000_000)   # then the rest
        self.assertEqual(snap["unfunded"], [])                                              # an open-ended pot is not a shortfall
        self.assertEqual(snap["cash_to_hold"], 3_000_000)
        self.assertTrue(any("kartu dulu" in r and "perkiraan terkumpul Rp 135.000.000" in r for r in snap["reminders"]))
        self.assertFalse([w for w in snap["warnings"] if "KURANG" in w])
        self.assertIn("pola KARTU DULU", tools.sinking_status(conn, NOV_1))

    def test_a_projected_shortfall_is_a_warning_with_the_choices(self):
        conn = full_world()
        tools.set_threshold(conn, "net_salary", 26_000_000)                                 # 6.184.000 a payday after bills
        tools.set_pot_schedule(conn, "hutang-teman", None, None, NOV_1, pace="sisa")
        snap = tools.generate_payday_plan(conn, NOV_1)
        w = [x for x in snap["warnings"] if x.startswith("hutang-teman") and "KURANG" in x]
        self.assertEqual(len(w), 1)
        self.assertIn("hitung gaji di hari tenggat", w[0])
        self.assertIn("KURANG", tools.sinking_status(conn, NOV_1))

    def test_switching_patterns_is_validated(self):
        conn = full_world()
        with self.assertRaises(ValueError):
            tools.set_pot_schedule(conn, "hutang-teman", 1_000_000, "2027-06", NOV_1, pace="sisa")
        with self.assertRaises(ValueError):
            tools.set_pot_schedule(conn, "hutang-teman", None, None, NOV_1, pace="cepat")
        tools.set_pot_schedule(conn, "hutang-teman", None, None, NOV_1, pace="sisa")
        tools.set_pot_schedule(conn, "hutang-teman", 2_000_000, "2027-03", NOV_1)           # a set low phase means 'rata' again
        f = conn.execute("SELECT pace, low_amount FROM sinking_funds").fetchone()
        self.assertEqual((f["pace"], f["low_amount"]), ("rata", 2_000_000))


class Emergency(unittest.TestCase):
    def test_the_buffer_comes_before_the_pot_and_stops_when_full(self):
        conn = full_world()
        tools.set_threshold(conn, "emergency_target", 3_000_000)
        tools.set_threshold(conn, "emergency_monthly", 500_000)
        snap = tools.generate_payday_plan(conn, NOV_1)
        names = [t["to_alias"] for t in snap["transfers"]]
        self.assertLess(names.index("dana-darurat"), names.index("hutang-teman"))
        self.assertEqual(amounts(snap)["dana-darurat"], 500_000)
        text = rincian.build(conn, PayeeVault(conn, bytes(range(32))), snap)
        self.assertIn("Sisihkan ke dana darurat", text)
        self.assertIn("Rp 500.000", text)
        self.assertIn("Rp 2.800.000 dari Rp 3.000.000", tools.set_emergency_balance(conn, 2_800_000))
        self.assertEqual(amounts(tools.generate_payday_plan(conn, NOV_1))["dana-darurat"], 200_000)    # only the last 200k
        tools.set_emergency_balance(conn, 3_000_000)
        self.assertNotIn("dana-darurat", amounts(tools.generate_payday_plan(conn, NOV_1)))
        self.assertIn("PENUH", tools.format_emergency(conn))

    def test_once_the_pocket_number_is_registered_the_deposit_is_a_transfer_with_its_number(self):
        conn = full_world()
        tools.set_threshold(conn, "emergency_target", 3_000_000)
        tools.set_threshold(conn, "emergency_monthly", 500_000)
        tools.set_emergency_balance(conn, 100_000)                                   # already in the pocket
        self.assertIn("nomor tujuan belum didaftarkan", tools.data_overview(conn, NOV_1))
        vault = PayeeVault(conn, bytes(range(32)))
        vault.store("dana-darurat", "account", "Jago", "102000008051")              # what /rekening does
        snap = tools.generate_payday_plan(conn, NOV_1)
        t = [x for x in snap["transfers"] if x["to_alias"] == "dana-darurat"][0]
        self.assertEqual((t["amount"], t["pay_to"]), (500_000, "dana-darurat"))
        text = rincian.build(conn, vault, snap)
        self.assertIn("Dana Darurat (Jago)", text)
        self.assertIn("102000008051", text)                                          # /rincian is the only place with the number
        self.assertNotIn("Sisihkan ke dana darurat", text)
        self.assertIn("disetor ke dana-darurat (Jago 8051)", tools.data_overview(conn, NOV_1))
        self.assertNotIn("102000008051", str(snap) + tools.data_overview(conn, NOV_1))


class LeftoverLivingCash(unittest.TestCase):
    def test_last_cycles_cash_tops_up_the_living_money_for_this_payday_only(self):
        conn = full_world()                                    # living money 3M
        tools.set_pot_schedule(conn, "hutang-teman", None, None, NOV_1, pace="sisa")
        before = amounts(tools.generate_payday_plan(conn, NOV_1))["hutang-teman"]
        self.assertIn("Rp 1.800.000", tools.set_leftover_living_cash(conn, 1_200_000, NOV_1))
        snap = tools.generate_payday_plan(conn, NOV_1)
        self.assertEqual((snap["reserve"], amounts(snap)["hutang-teman"]), (1_800_000, before + 1_200_000))   # the pot gets it
        self.assertTrue(snap["reserve_source"].startswith("sementara"))
        nxt = tools.generate_payday_plan(conn, date(2026, 11, 28))           # the next payday: back to normal
        self.assertEqual((nxt["payday"], nxt["reserve"]), ("2026-11-30", 3_000_000))
        self.assertIn("Kelebihan Rp 1.000.000", tools.set_leftover_living_cash(conn, 4_000_000, NOV_1))
        with self.assertRaises(ValueError):
            tools.set_leftover_living_cash(conn, -1, NOV_1)


class DailyAccount(unittest.TestCase):
    def test_the_living_money_is_a_transfer_to_the_daily_account_once_registered(self):
        conn = full_world()                                               # living money 3M
        tools.set_pot_schedule(conn, "hutang-teman", None, None, NOV_1, pace="sisa")
        before = tools.generate_payday_plan(conn, NOV_1)
        self.assertNotIn("living_transfer", before)
        self.assertIn("REKENING UANG HARIAN: belum didaftarkan", tools.data_overview(conn, NOV_1))
        vault = PayeeVault(conn, bytes(range(32)))
        vault.store("uang-harian", "account", "Jago", "103000008786")      # what /rekening does
        tools.set_leftover_living_cash(conn, 1_200_000, NOV_1)            # last cycle's cash, still in the main account
        snap = tools.generate_payday_plan(conn, NOV_1)
        self.assertEqual((snap["living_transfer"]["amount"], snap["living_transfer"]["also_move"]), (1_800_000, 1_200_000))
        self.assertEqual(snap["cash_to_hold"], 1_800_000)                 # the obligations' arithmetic is unchanged
        self.assertTrue(any("UANG HARIAN: transfer Rp 1.800.000" in r and "pindahkan juga sisa uang harian Rp 1.200.000" in r
                            for r in snap["reminders"]))
        text = rincian.build(conn, vault, snap)
        self.assertIn("Uang Harian (Jago)", text)
        self.assertIn("103000008786", text)
        self.assertIn("Tambahan: sisa uang harian Rp 1.200.000", text)
        self.assertIn("uang-harian: Rp 1.800.000 (uang harian ke rekening harian)", tools.summarize_plan(snap))
        self.assertNotIn("103000008786", str(snap) + tools.data_overview(conn, NOV_1))


class PotBalance(unittest.TestCase):
    def test_the_balance_read_in_the_bank_app_is_the_new_truth(self):
        conn = full_world()
        self.assertIn("Rp 4.300.000", tools.set_pot_balance(conn, "hutang-teman", 4_300_000, date(2026, 12, 2)))
        f = conn.execute("SELECT * FROM sinking_funds").fetchone()
        self.assertEqual((tools.sinking_saved(conn, f), f["saved_asof"]), (4_300_000, "2026-12-03"))
        with self.assertRaises(ValueError):
            tools.set_pot_balance(conn, "ghost", 1, date(2026, 12, 2))
        with self.assertRaises(ValueError):
            tools.set_pot_balance(conn, "hutang-teman", -1, date(2026, 12, 2))


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class ThroughTheTools(unittest.TestCase):
    def test_new_tools_and_the_system_managed_balance(self):
        with tempfile.TemporaryDirectory() as d:
            app = create_app(os.path.join(d, "l.db"), bytes(range(32)), "m" * 40, "i" * 40, allowed_hosts=["testserver"],
                             ingest_dir=d, passwords_path=None)

            def call(n, a=None):
                return json.dumps(asyncio.run(app.state.mcp.call_tool(n, a or {})), default=str)
            call("set_threshold", {"key": "net_salary", "value": 20_000_000})
            with self.assertRaises(Exception):
                call("set_threshold", {"key": "emergency_saved", "value": 1})                # only dana_darurat sets it
            self.assertIn("belum diatur", call("dana_darurat"))
            call("set_threshold", {"key": "emergency_target", "value": 3_000_000})
            self.assertIn("Rp 1.000.000 dari Rp 3.000.000", call("dana_darurat", {"saldo": 1_000_000}))
            out = call("simulasi_skenario", {"pola_pot": "sisa", "gaji_hari_tenggat": True})
            self.assertIn("pola pot KARTU DULU", out)
            self.assertIn("IKUT dipakai", out)


if __name__ == "__main__":
    unittest.main()
