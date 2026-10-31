"""Payday progress (30 Oct 2026). A payday's plan is computed from the ledger as it stood BEFORE that payday, so paying from
that salary is progress, never a smaller plan next to a still whole salary: the old code handed the freed cash to the pot (plans
#57-#60 and the simulation showed 19-20.7M for a pot that got nothing). Also: instalments paid by hand ahead of the auto-debit,
a card whose minimum is paid is not "due", and what the owner already reported is listed so it is not asked again."""
import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import reports, rincian, roadmap, simulate, tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402
from vault_tools.payee_vault import PayeeVault  # noqa: E402

try:
    from vault_tools.server import MCP_TOOL_NAMES, create_app
    HAVE_SERVER = True
except ImportError:  # system python without mcp/starlette: run these in the vault-tools venv
    HAVE_SERVER = False

KEY = bytes(range(32))
BEFORE, PAYDAY, NOV_1 = date(2026, 10, 27), date(2026, 10, 30), date(2026, 11, 1)


def stmt(conn, card_id, printed, due, total, minimum):
    conn.execute(
        "INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,fees,total_due,"
        "minimum_due,reconciled,recon_diff,ingested_at) VALUES (?,?,?,?,0,0,?,0,?,?,1,0,'t')",
        (card_id, f"{card_id}{printed}".ljust(64, "0"), printed, due, total, total, minimum))
    conn.commit()


def world(path=":memory:"):
    """Salary 20M; living money 3M; school 2M; two auto-debited instalments (1.8M); a pot filled from what is left; three
    cards: the salary clears Jenius, most of DBS, and only CIMB's minimum (like 30 Oct, scaled down)."""
    conn = connect(path)
    vault = PayeeVault(conn, KEY)
    vault.store("pot-rek", "account", "Jago", "1020000080511")
    vault.store("uang-harian", "account", "Jago", "1020000087861")
    vault.store("sekolah-va", "va", "BCA", "8800012345678")
    conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('pot','Jago','pool')")
    conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('mandiri-utama','Mandiri','main')")
    conn.commit()
    tools.set_threshold(conn, "net_salary", 20_000_000)
    tools.set_threshold(conn, "living_reserve", 3_000_000)
    tools.upsert_expense(conn, "sekolah", "sekolah-va", 2_000_000, 1)
    tools.upsert_debt(conn, "cicilan-mobil", "MTF", 10 * 1_500_000, 1_500_000, 10, 2, 815,
                      pay_method="autodebit", debit_account_alias="mandiri-utama")
    tools.upsert_debt(conn, "spaylater", "Shopee", 5 * 300_000, 300_000, 5, 1, 0,
                      pay_method="autodebit", debit_account_alias="mandiri-utama")
    tools.upsert_sinking_fund(conn, "hutang-teman", 30_000_000, "2028-01-31", "pot", "pot-rek", today=BEFORE)
    tools.set_pot_schedule(conn, "hutang-teman", None, None, BEFORE, pace="sisa")
    tools.upsert_card(conn, "jenius-1", "Jenius", "0480", 26, 13, 20_000_000, interest_bp_month=225)
    tools.upsert_card(conn, "dbs-1", "DBS", "5685", 25, 10, 20_000_000, interest_bp_month=175)
    tools.upsert_card(conn, "cimb-1", "CIMB", "9888", 19, 7, 20_000_000, interest_bp_month=95)
    stmt(conn, 1, "2026-10-26", "2026-11-13", 6_000_000, 600_000)
    stmt(conn, 2, "2026-10-25", "2026-11-10", 8_000_000, 500_000)
    stmt(conn, 3, "2026-10-19", "2026-11-07", 4_000_000, 200_000)
    return conn


def pay_as_on_30_oct(conn):
    """The plan's card amounts, the rest of CIMB from an account balance (outside the salary), and both auto-debited
    instalments by hand ahead of the debit."""
    tools.record_card_payment(conn, PAYDAY, "jenius-1", 6_000_000)
    tools.record_card_payment(conn, PAYDAY, "dbs-1", 7_000_000)
    tools.record_card_payment(conn, PAYDAY, "cimb-1", 200_000)
    tools.record_card_payment(conn, PAYDAY, "cimb-1", 3_800_000)
    tools.record_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000)
    tools.record_debt_payment(conn, PAYDAY, "spaylater", 300_000)


def plan_of(snap):
    return [(t["to_alias"], t["reason"], t["amount"]) for t in snap["transfers"]]


class PlanStaysAfterPaying(unittest.TestCase):
    def test_paying_from_the_salary_never_shrinks_the_plan_or_feeds_the_pot(self):
        """Regression (plans #57-#60): after the card payments the plan put the salary, already spent, into the pot."""
        conn = world()
        before = tools.generate_payday_plan(conn, PAYDAY)
        self.assertEqual(sum(t["amount"] for t in before["transfers"]) + before["cash_to_hold"], 20_000_000)
        tools.record_card_payment(conn, PAYDAY, "jenius-1", 6_000_000)
        tools.record_card_payment(conn, PAYDAY, "dbs-1", 7_000_000)
        tools.record_card_payment(conn, PAYDAY, "cimb-1", 4_000_000)
        after = tools.generate_payday_plan(conn, NOV_1)
        self.assertEqual(plan_of(after), plan_of(before))
        self.assertEqual((after["cash_to_hold"], after["unfunded"]), (before["cash_to_hold"], before["unfunded"]))
        self.assertNotIn("hutang-teman", [t["to_alias"] for t in after["transfers"]])

    def test_the_simulation_starts_from_the_payday_like_its_plan(self):
        """Regression: "Nov 2026: kas 22,08 jt; kartu 872.061; pot 20,71 jt" once the payments were recorded."""
        conn = world()
        first = simulate.simulate(conn, PAYDAY)["rows"][0]
        pay_as_on_30_oct(conn)
        r = simulate.simulate(conn, NOV_1)
        now = r["rows"][0]
        self.assertEqual((now["cash"], now["paid"], now["pot"], now["loans"]), (first["cash"], first["paid"], 0, 1_800_000))
        self.assertEqual((first["cash"], first["paid"]), (13_200_000, 13_200_000))
        self.assertEqual(now["outside"], 3_800_000)                         # CIMB's rest, paid from an account balance
        self.assertEqual(now["balance"], 1_000_000 + 17_500)                # only DBS's rest is carried, at 1.75%
        self.assertEqual(r["start_balance"], 18_000_000)
        self.assertIn("Rp 3.800.000 di antaranya sudah dibayar dengan uang di luar gaji", simulate.format_result(r, r))

    def test_a_deferral_also_holds_back_a_pot_filled_from_what_is_left(self):
        """Regression (/usulan #10): tunda_pot moved only a set ('rata') pot; a 'sisa' pot took the money anyway."""
        conn = world()
        base = simulate.simulate(conn, PAYDAY)["rows"]
        held = simulate.simulate(conn, PAYDAY, tunda_pot=2)["rows"]
        self.assertEqual([r["pot"] for r in base[:3]], [0, 8_346_400, 13_200_000])
        self.assertEqual([r["pot"] for r in held[:3]], [0, 0, 13_200_000])
        self.assertEqual(held[1]["free"], base[1]["pot"] + base[1]["free"])         # the money stays free, nothing vanishes
        low = simulate.simulate(conn, PAYDAY, pot_awal=1_000_000, pot_awal_bulan=3)["rows"]
        self.assertEqual([r["pot"] for r in low[:4]], [0, 1_000_000, 1_000_000, 13_200_000])


class Instalments(unittest.TestCase):
    def test_paid_by_hand_ahead_of_the_debit_is_not_debited_again(self):
        conn = world()
        self.assertEqual(tools.generate_payday_plan(conn, PAYDAY)["autodebit_need"]["mandiri-utama"]["total"], 1_800_000)
        out = tools.record_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000)
        self.assertIn("jatuh tempo 2026-11-02 (Rp 1.500.000) tercatat dibayar manual 2026-10-30. Sisa 9 angsuran, "
                      "sisa utang Rp 13.500.000.", out)
        self.assertEqual(tools.generate_payday_plan(conn, NOV_1)["autodebit_need"]["mandiri-utama"]["total"], 300_000)
        tools.record_debt_payment(conn, PAYDAY, "spaylater", 300_000)
        snap = tools.generate_payday_plan(conn, NOV_1)
        self.assertEqual(snap["autodebit_need"], {})
        self.assertTrue(any(r.startswith("AUTODEBET dari rekening mandiri-utama: tidak ada yang akan didebet sampai gajian 2026-11-30")
                            for r in snap["reminders"]), snap["reminders"])
        self.assertEqual(plan_of(snap), plan_of(tools.generate_payday_plan(world(), PAYDAY)))     # the plan itself is the same

    def test_which_instalment_is_meant_and_what_is_refused(self):
        conn = world()
        with self.assertRaisesRegex(ValueError, "tidak sama dengan angsuran"):
            tools.record_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_000_000)
        with self.assertRaisesRegex(ValueError, "tiap tanggal 2"):
            tools.record_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000, due="2026-11-03")
        with self.assertRaisesRegex(ValueError, "cara"):
            tools.record_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000, how="tunai")
        tools.record_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000, due="2026-11-02")
        with self.assertRaisesRegex(ValueError, "sudah tercatat dibayar"):
            tools.record_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000, due="2026-11-02")
        # the auto-debit itself went through: the latest instalment due by then
        self.assertIn("jatuh tempo 2026-11-01", tools.record_debt_payment(conn, date(2026, 11, 3), "spaylater", 300_000, how="autodebit"))
        # paid by hand on the due day itself: that day's instalment
        self.assertIn("jatuh tempo 2026-12-01", tools.record_debt_payment(conn, date(2026, 12, 1), "spaylater", 300_000))
        # fields a model sends empty mean "not given": the next one still open
        self.assertIn("jatuh tempo 2026-12-02", tools.record_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000, how="", due=""))
        self.assertEqual(conn.execute("SELECT tenor_left, outstanding FROM debts WHERE alias='cicilan-mobil'").fetchone()[:],
                         (8, 12_000_000))

    def test_the_roadmap_counts_on_from_the_first_unpaid_instalment(self):
        conn = world()
        ends = {i["alias"]: i["ends"] for i in roadmap.roadmap(conn, BEFORE)["items"]}
        tools.record_debt_payment(conn, PAYDAY, "cicilan-mobil", 1_500_000)
        after = {i["alias"]: i for i in roadmap.roadmap(conn, NOV_1)["items"]}
        self.assertEqual((after["cicilan-mobil"]["ends"], ends["cicilan-mobil"]), ("2027-08-02", "2027-08-02"))
        self.assertEqual(after["cicilan-mobil"]["remaining"], 9 * 1_500_000)


class Progress(unittest.TestCase):
    def test_status_lists_what_is_done_open_paid_outside_and_each_card_as_it_is_now(self):
        conn = world()
        pay_as_on_30_oct(conn)
        text = tools.payday_status(conn, NOV_1)
        for line in ("✅ jenius-1 Rp 6.000.000 (2026-10-30) [kartu]",
                     "✅ cicilan-mobil Rp 1.500.000 (dibayar manual 2026-10-30) [cicilan, autodebet 2026-11-02]",
                     "⏳ sekolah-va Rp 2.000.000 [transfer, jatuh tempo 2026-11-01] (setelah ditransfer: transfer_selesai)",
                     "+ cimb-1 Rp 3.800.000",
                     "- cimb-1: Rp 3.800.000 (tagihan kartu - sisa saldo (bayar penuh)); sudah dibayar di luar rencana Rp 3.800.000: "
                     "tertutup, tidak ada sisa",
                     "- dbs-1: minimum sudah terpenuhi: tidak telat, tidak ada denda. Sisa Rp 1.000.000 dibawa ke tagihan berikutnya",
                     "- LUNAS: cimb-1, jenius-1",
                     # the sum from the code: the closed cimb-1 is not added to what is still open (30 Oct)
                     "JUMLAH (dihitung kode, jangan menjumlah sendiri): dibawa ke tagihan berikutnya (minimum terpenuhi, "
                     "berbunga) Rp 1.000.000; 1 pos sudah tertutup"):
            self.assertIn(line, text)
        self.assertNotIn("MENDESAK", text)
        summary = tools.summarize_plan(tools.generate_payday_plan(conn, NOV_1))
        self.assertIn("| belum sekolah-va Rp 2.000.000; uang-harian Rp 3.000.000 | di luar rencana cimb-1 Rp 3.800.000", summary)
        self.assertIn("! JUMLAH (dihitung kode, jangan menjumlah sendiri): dibawa ke tagihan berikutnya", summary)

    def test_the_total_keeps_what_has_no_money_apart_from_a_rest_carried_with_interest(self):
        unf = [{"to": "kartu-a", "amount": 500_000, "covered": 0, "left": 500_000, "reason": "tagihan kartu - minimum", "cost": 50_000},
               {"to": "kartu-a", "amount": 2_000_000, "covered": 0, "left": 2_000_000, "reason": tools.CARD_REST, "cost": 35_000},
               {"to": "kartu-b", "amount": 872_061, "covered": 0, "left": 872_061, "reason": tools.CARD_REST, "cost": 15_261},
               {"to": "sekolah", "amount": 1_000_000, "covered": 1_000_000, "left": 0, "reason": "pengeluaran tetap", "cost": 0}]
        self.assertEqual(tools._unfunded_total({"unfunded": [], "progress": {"unfunded": unf}}),
                         "JUMLAH (dihitung kode, jangan menjumlah sendiri): belum ada dananya Rp 2.500.000; dibawa ke tagihan "
                         "berikutnya (minimum terpenuhi, berbunga) Rp 872.061; 1 pos sudah tertutup")
        self.assertIsNone(tools._unfunded_total({"unfunded": [], "progress": {"unfunded": unf[2:3]}}))   # one item: its own line

    def test_what_the_owner_reported_is_listed_so_it_is_not_asked_again(self):
        conn = world()
        tools.set_leftover_living_cash(conn, 1_200_000, PAYDAY)
        tools.record_account_balance(conn, NOV_1, "mandiri-utama", 2_000_000)
        tools.set_pot_balance(conn, "hutang-teman", 0, NOV_1)
        known = tools.payday_status(conn, NOV_1).split("SUDAH TERCATAT, JANGAN DITANYAKAN ULANG: ")[1]
        self.assertIn("sisa uang harian sebelum gaji Rp 1.200.000", known)
        self.assertIn("saldo mandiri-utama Rp 2.000.000", known)
        self.assertIn("saldo pot hutang-teman Rp 0 (dilaporkan 2026-11-01)", known)

    def test_an_emergency_balance_read_after_the_payday_says_whether_the_deposit_arrived(self):
        """Regression (30 Oct 16:29): 600.048 then 600.000, both read after the 500.000 deposit, made the bot say the deposit
        had not arrived and ask for another 500.000."""
        conn = world()
        tools.set_threshold(conn, "emergency_target", 3_000_000)
        tools.set_threshold(conn, "emergency_monthly", 500_000)
        plain = tools.set_emergency_balance(conn, 100_000, date(2026, 10, 29))            # before the payday: no comparison
        self.assertNotIn("Dibanding", plain)
        self.assertNotIn("mestinya", plain)
        self.assertIn("Dibanding sebelum gajian 2026-10-30 (Rp 100.000): setoran gajian ini Rp 500.000 sudah masuk.",
                      tools.set_emergency_balance(conn, 600_048, PAYDAY))
        again = tools.set_emergency_balance(conn, 600_000, PAYDAY)
        self.assertIn("setoran gajian ini Rp 500.000 sudah masuk", again)
        self.assertNotIn("kurang", again)
        self.assertIn("Sebelum gajian 2026-10-30: Rp 100.000; dengan setoran gajian ini Rp 500.000 mestinya Rp 600.000; kurang "
                      "Rp 300.000 (belum disetor atau ada yang dipakai", tools.set_emergency_balance(conn, 300_000, NOV_1))
        self.assertEqual(tools.emergency_status(conn, PAYDAY)["next"], 500_000)            # the payday's deposit stays
        tools._fund_report(conn, "darurat", date(2026, 10, 29), 100_000)                  # a report added later, dated back
        self.assertIn("saldo dana darurat Rp 300.000 (dilaporkan 2026-11-01)", tools.payday_status(conn, NOV_1))

    def test_marking_transfers_and_pointing_cards_and_instalments_to_their_own_tools(self):
        conn = world()
        self.assertEqual(tools.mark_transfers_done(conn, NOV_1, ["sekolah"]),
                         "Tercatat selesai (gajian 2026-10-30): sekolah-va Rp 2.000.000. Transfer lain yang belum ditandai: uang-harian.")
        with self.assertRaisesRegex(ValueError, "record_card_payment"):
            tools.mark_transfers_done(conn, NOV_1, ["jenius-1"])
        with self.assertRaisesRegex(ValueError, "cicilan_dibayar"):
            tools.mark_transfers_done(conn, NOV_1, ["cicilan-mobil"])
        with self.assertRaises(ValueError):
            tools.mark_transfers_done(conn, NOV_1)                                   # neither a destination nor semua
        self.assertIn("uang-harian Rp 3.000.000", tools.mark_transfers_done(conn, NOV_1, all_open=True))
        self.assertIn("Tidak ada yang diubah", tools.mark_transfers_done(conn, NOV_1, all_open=True))
        self.assertIn("Tanda selesai dihapus: sekolah-va", tools.mark_transfers_done(conn, NOV_1, ["sekolah-va"], undo=True))
        self.assertIn("⏳ sekolah-va", tools.payday_status(conn, NOV_1))

    def test_a_balance_in_the_payday_days_names_the_transfers_still_open(self):
        conn = world()
        pay_as_on_30_oct(conn)
        self.assertIn("Angka ini hanya benar bila", tools.record_account_balance(conn, NOV_1, "mandiri-utama", 9_000_000))  # no plan stored
        tools.generate_payday_plan(conn, NOV_1)                          # the plan the payday flow stores
        out = tools.record_account_balance(conn, NOV_1, "mandiri-utama", 9_000_000)
        self.assertIn("Transfer gajian yang belum tercatat selesai: sekolah-va Rp 2.000.000; uang-harian Rp 3.000.000. Bila dibayar "
                      "dari rekening ini, sesudahnya yang bisa dipakai Rp 4.000.000. Laporkan saldo lagi setelah transfer.", out)
        self.assertIn("Bila dibayar dari rekening ini, saldonya KURANG Rp 1.000.000 untuk itu.",
                      tools.record_account_balance(conn, NOV_1, "mandiri-utama", 4_000_000))
        tools.mark_transfers_done(conn, NOV_1, all_open=True)            # all done: the balance is final, no caveat
        self.assertNotIn("transfer gajian", tools.record_account_balance(conn, NOV_1, "mandiri-utama", 4_000_000).lower())

    def test_rincian_and_the_reports_mark_what_is_done(self):
        conn = world()
        pay_as_on_30_oct(conn)
        snap = tools.generate_payday_plan(conn, NOV_1)
        text = rincian.build(conn, PayeeVault(conn, KEY), snap)
        self.assertIn("• Jenius …0480: *Rp 6.000.000* ✅ SUDAH", text)
        self.assertIn("• Cicilan Mobil: *Rp 1.500.000* ✅ dibayar manual 2026-10-30, tidak didebet lagi", text)
        self.assertIn("Tidak ada autodebet yang masih menunggu", text)
        self.assertIn("Rp 3.800.000 di antaranya sudah dibayar dengan uang di luar gaji, sisa Rp 1.000.000", text)
        self.assertNotIn("Saldo rekening Mandiri minimal", text)
        plan = reports._rencana(conn, NOV_1)
        self.assertIn("✅ Jenius …0480", plan)
        self.assertIn("minimum terpenuhi, tidak telat dan tidak ada denda", plan)
        bills = reports._tagihan(conn, NOV_1)
        self.assertIn("🔵 <b>DBS …5685</b>", bills)
        self.assertNotIn("Jatuh tempo", bills)                                       # minimum paid or paid off: nothing is due
        self.assertIn("dibayar Rp 7.000.000, minimum sudah terpenuhi: tidak telat", tools.data_overview(conn, NOV_1))


class CardPayment(unittest.TestCase):
    def test_the_same_payment_twice_on_one_day_is_refused_unless_confirmed(self):
        conn = world()
        tools.record_card_payment(conn, PAYDAY, "dbs-1", 1_000_000)
        with self.assertRaisesRegex(ValueError, "ulang=true"):
            tools.record_card_payment(conn, PAYDAY, "dbs-1", 1_000_000)
        self.assertIn("dibayar Rp 2.000.000 dari Rp 8.000.000", tools.record_card_payment(conn, PAYDAY, "dbs-1", 1_000_000, again=True))
        self.assertEqual(conn.execute("SELECT COUNT(*), SUM(amount) FROM card_payments").fetchone()[:], (2, 2_000_000))

    def test_a_bill_marked_paid_without_amounts_is_closed_before_its_payday_and_progress_after(self):
        conn = world()
        conn.execute("UPDATE statements SET paid_at='2026-10-28' WHERE card_id=1")    # bills paid before v8 kept paid_amount 0
        conn.execute("UPDATE statements SET paid_at='2026-10-30' WHERE card_id=3")
        conn.commit()
        bills = {b["alias"]: b for b in tools.card_bills(conn, PAYDAY)}
        self.assertEqual((bills["jenius-1"]["owed"], bills["cimb-1"]["owed"], bills["cimb-1"]["paid_since"]), (0, 4_000_000, 4_000_000))


class StoredPlans(unittest.TestCase):
    def test_a_plan_is_stored_once_per_change_not_per_question(self):
        conn = world()
        for _ in range(3):
            tools.generate_payday_plan(conn, PAYDAY)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0], 1)
        tools.record_debt_payment(conn, PAYDAY, "spaylater", 300_000)                # the auto-debit reminder changes
        tools.generate_payday_plan(conn, PAYDAY)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0], 2)
        last = json.loads(conn.execute("SELECT snapshot_json FROM plans ORDER BY id DESC LIMIT 1").fetchone()[0])
        self.assertNotIn("progress", last)


class Migration(unittest.TestCase):
    def test_v12_payments_and_balances_move_into_the_dated_tables_once(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "l.db")
            conn = world(path)
            stmt(conn, 1, "2026-09-26", "2026-10-13", 5_000_000, 500_000)               # an older Jenius bill, partly paid
            tools.set_threshold(conn, "emergency_saved", 600_000)
            conn.execute("UPDATE sinking_funds SET saved_so_far=5000000, saved_asof='2026-10-27'")
            # what v12's record_card_payment left: amounts on the statements only
            conn.execute("UPDATE statements SET paid_amount=1000000 WHERE statement_date='2026-09-26'")
            conn.execute("UPDATE statements SET paid_amount=2000000 WHERE card_id=2")
            conn.execute("UPDATE statements SET paid_amount=4000000, paid_at='2026-10-28' WHERE card_id=3")
            conn.executescript("DROP TABLE card_payments; DROP TABLE debt_payments; DROP TABLE plan_progress;"
                               " DROP TABLE fund_reports; PRAGMA user_version = 12;")
            conn.close()
            conn = connect(path)
            self.assertEqual(conn.execute("PRAGMA user_version").fetchone()[0], 13)
            got = [tuple(r) for r in conn.execute(
                "SELECT s.statement_date, p.paid_on, p.amount FROM card_payments p JOIN statements s ON s.id = p.statement_id"
                " ORDER BY s.statement_date, p.amount")]
            self.assertEqual(got, [("2026-09-26", "2026-10-13", 1_000_000),          # older bill: on its due date
                                   ("2026-10-19", "2026-10-28", 4_000_000),          # closed: on the day it was closed
                                   ("2026-10-25", tools.wib_today().isoformat(), 2_000_000)])   # open: the day of the move
            funds = {r["fund"]: (r["reported_on"], r["balance"]) for r in conn.execute("SELECT * FROM fund_reports")}
            self.assertEqual(funds, {"darurat": (tools.wib_today().isoformat(), 600_000),
                                     "pot:hutang-teman": ("2026-10-26", 5_000_000)})
            conn.close()
            conn = connect(path)                                                         # idempotent
            self.assertEqual([conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("card_payments", "fund_reports")],
                             [3, 2])
            conn.close()


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class ThroughTheTools(unittest.TestCase):
    def test_the_new_tools_with_empty_fields_as_a_model_sends_them(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "l.db")
            world(path).close()
            app = create_app(path, KEY, "m" * 40, "i" * 40, allowed_hosts=["testserver"], today=lambda: PAYDAY,
                             ingest_dir=d, passwords_path=None)
            call = lambda n, a=None: json.dumps(asyncio.run(app.state.mcp.call_tool(n, a or {})), default=str, ensure_ascii=False)  # noqa: E731
            self.assertTrue({"cicilan_dibayar", "transfer_selesai", "status_gajian"} <= set(MCP_TOOL_NAMES))
            self.assertIn("jatuh tempo 2026-11-01", call("cicilan_dibayar", {"alias": "spaylater", "jumlah": 300_000, "cara": "",
                                                                            "jatuh_tempo": ""}))
            self.assertIn("sekolah-va Rp 2.000.000", call("transfer_selesai", {"tujuan": ["sekolah", ""], "semua": False, "batal": False}))
            with self.assertRaises(Exception):
                call("transfer_selesai", {"tujuan": [], "semua": False, "batal": False})
            self.assertIn("minimum sudah terpenuhi", call("record_card_payment", {"card_alias": "dbs-1", "amount": 1_000_000}))
            with self.assertRaisesRegex(Exception, "ulang=true"):
                call("record_card_payment", {"card_alias": "dbs-1", "amount": 1_000_000})
            self.assertIn("dibayar Rp 1.000.000; minimum sudah terpenuhi", call("list_statements", {"card_alias": "dbs-1"}))
            status = call("status_gajian")
            self.assertIn("✅ spaylater Rp 300.000 (dibayar manual 2026-10-30)", status)
            self.assertIn("✅ sekolah-va Rp 2.000.000", status)
            self.assertIn("◐ dbs-1 Rp 1.000.000 dari Rp 7.000.000", status)
            call("set_threshold", {"key": "emergency_target", "value": 3_000_000})
            self.assertIn("Rp 600.000 dari Rp 3.000.000", call("dana_darurat", {"saldo": 600_000}))
            db = sqlite3.connect(path)
            self.assertEqual(db.execute("SELECT reported_on, balance FROM fund_reports WHERE fund='darurat'").fetchall(),
                             [("2026-10-30", 600_000)])                                  # dated by the server's day, not the host's
            db.close()


if __name__ == "__main__":
    unittest.main()
