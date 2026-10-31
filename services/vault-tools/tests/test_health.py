import asyncio
import json
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import health as hl  # noqa: E402
from vault_tools import mutations as mu  # noqa: E402
from vault_tools import reports  # noqa: E402
from vault_tools import tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402

TODAY = date(2026, 11, 10)          # window 2026-10-30 .. 2026-11-30 (31 days); today is day 12 = 38% elapsed


def planned(salary=10_000_000):
    conn = connect(":memory:")
    conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('mandiri-utama','Mandiri','main')")
    conn.commit()
    tools.set_threshold(conn, "net_salary", salary)
    tools.generate_payday_plan(conn, TODAY, payday=date(2026, 10, 30))
    return conn


def spend(conn, amount, merchant="WARUNG", day="2026-11-05", **kw):
    return hl.record_expense(conn, TODAY, amount, merchant, day, **kw)


class RecordExpense(unittest.TestCase):
    def test_stored_negative_unverified_with_receipt_source(self):
        conn = planned()
        r = spend(conn, 50_000, "KOPI KENANGAN", category="makan")
        self.assertEqual((r["status"], r["category"]), ("stored", "makan"))
        row = conn.execute("SELECT amount, status, source, merchant FROM transactions").fetchone()
        self.assertEqual((row["amount"], row["status"], row["source"]), (-50_000, "unverified", "receipt"))

    def test_same_screenshot_twice_is_flagged_unless_confirmed(self):
        conn = planned()
        spend(conn, 50_000, "KOPI KENANGAN")
        dup = spend(conn, 50_000, "Kopi Kenangan")
        self.assertEqual(dup["status"], "possible_duplicate")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 1)
        self.assertEqual(spend(conn, 50_000, "KOPI KENANGAN", allow_duplicate=True)["status"], "stored")
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 2)
        self.assertEqual(spend(conn, 50_000, "KOPI KENANGAN", day="2026-11-06")["status"], "stored")   # other day: fine

    def test_a_resent_screenshot_described_in_other_words_is_still_a_duplicate(self):
        """Regression 2026-10-28: after /new the bot re-read the same Flazz top-up screenshot, named it differently and stored
        it a second time (the merchant text was the only key)."""
        conn = planned()
        conn.execute("INSERT OR IGNORE INTO accounts(alias,bank,kind,last4) VALUES ('mandiri-utama','Mandiri','main','2701')")
        conn.commit()
        self.assertEqual(spend(conn, 100_000, "Isi saldo Flazz (tol)", account_alias="mandiri-utama")["status"], "stored")
        dup = spend(conn, 100_000, "Isi Flazz BCA (tol)", account_alias="mandiri-utama")
        self.assertEqual((dup["status"], dup["existing_merchant"]), ("possible_duplicate", "Isi saldo Flazz (tol)"))
        self.assertEqual(spend(conn, 100_000, "Parkir mall")["status"], "stored")          # no source given: merchant decides

    def test_validation(self):
        conn = planned()
        for kw in ({"amount": 0}, {"amount": -5}, {"merchant": "  "}, {"txn_date": "2027-01-01"},
                   {"account_alias": "ghost"}, {"card_alias": "ghost"}):
            args = dict(amount=1000, merchant="X", txn_date="2026-11-05")
            args.update(kw)
            with self.assertRaises(ValueError):
                hl.record_expense(conn, TODAY, **args)
        with self.assertRaises(TypeError):
            spend(conn, 1500.5)

    def test_category_rule_is_applied_and_verified(self):
        conn = planned()
        mu.set_category_rule(conn, "NETFLIX.COM 123456", "langganan")
        spend(conn, 186_000, "NETFLIX.COM 654321")
        row = conn.execute("SELECT category, status FROM transactions").fetchone()
        self.assertEqual((row["category"], row["status"]), ("langganan", "verified"))
        self.assertEqual(mu.list_uncategorized(conn), [])


class Merge(unittest.TestCase):
    def setUp(self):
        self.conn = planned()
        spend(self.conn, 50_000, "KOPI KENANGAN", day="2026-11-05", category="makan", account_alias="mandiri-utama")

    def mutation(self, desc="QRIS KOPI KENANGAN 998877", day="2026-11-06", amount=-50_000, h="a" * 64):
        return mu.record_mutations(self.conn, "mandiri-utama", h, "2026-11-01", "2026-11-30", None, None,
                                   [{"date": day, "description": desc, "amount": amount}])

    def test_receipt_seen_in_bank_mutation_is_counted_once_and_keeps_its_category(self):
        self.mutation()
        rec = self.conn.execute("SELECT merged_into FROM transactions WHERE source='receipt'").fetchone()[0]
        mut = self.conn.execute("SELECT id, category, status FROM transactions WHERE source='mutation'").fetchone()
        self.assertEqual(rec, mut["id"])
        self.assertEqual((mut["category"], mut["status"]), ("makan", "unverified"))
        self.assertEqual(hl.spending_pace(self.conn, TODAY)["spent"], 50_000)          # not 100_000
        self.assertEqual(hl.budget_status(self.conn, "2026-11"), [])                    # no budget set, nothing double

    def test_different_amount_or_far_date_is_not_merged(self):
        self.mutation(amount=-51_000, h="b" * 64)
        self.mutation(day="2026-11-20", h="c" * 64)
        self.assertIsNone(self.conn.execute("SELECT merged_into FROM transactions WHERE source='receipt'").fetchone()[0])

    def test_one_receipt_merges_into_only_one_mutation(self):
        mu.record_mutations(self.conn, "mandiri-utama", "d" * 64, "2026-11-01", "2026-11-30", None, None,
                            [{"date": "2026-11-05", "description": "KOPI A", "amount": -50_000},
                             {"date": "2026-11-06", "description": "KOPI B", "amount": -50_000}])
        self.assertEqual(hl.spending_pace(self.conn, TODAY)["spent"], 100_000)          # two real mutation rows, receipt absorbed
        merged = self.conn.execute("SELECT COUNT(*) FROM transactions WHERE merged_into IS NOT NULL").fetchone()[0]
        self.assertEqual(merged, 1)


class _Banks:
    """Mandiri, BCA and Jago (its one statement lists every pocket: jago-harian purchases are in jago-utama's file), a card,
    and statement uploads."""

    def setUp(self):
        self.conn = planned()
        for alias, bank in (("bca-utama", "BCA"), ("jago-utama", "jago"), ("jago-harian", "Jago")):
            self.conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES (?,?,'main')", (alias, bank))
        self.conn.commit()
        tools.upsert_card(self.conn, "cimb-1", "CIMB", "2222", 5, 5, 10_000_000)

    def upload(self, account, h, *rows, period=("2026-11-01", "2026-11-30")):
        mu.record_mutations(self.conn, account, h * 64, *period, None, None,
                            [{"date": d, "description": desc, "amount": a} for d, desc, a in rows])

    def merged(self, rid):
        return self.conn.execute("SELECT merged_into FROM transactions WHERE id=?", (rid,)).fetchone()[0]

    def spent(self):
        return hl.spending_pace(self.conn, TODAY)["spent"]

    def count(self):
        return self.conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]


class MergeRules(_Banks, unittest.TestCase):
    """Only the same money merges (2026-10-30; the old rule took any account's debit of that amount): the same bank, never
    a card purchase, never a purchase with a move between the owner's own accounts."""

    def test_another_banks_debit_of_the_same_amount_is_other_money(self):
        rid = spend(self.conn, 100_000, "ISI FLAZZ", category="transport", account_alias="mandiri-utama")["id"]
        self.upload("bca-utama", "a", ("2026-11-05", "TRSF E-BANKING 1234567", -100_000))
        self.assertIsNone(self.merged(rid))
        self.assertEqual(self.spent(), 200_000)                                   # two payments, both counted
        self.upload("mandiri-utama", "b", ("2026-11-06", "FLAZZ TOPUP 998877", -100_000))
        self.assertEqual(self.merged(rid), self.conn.execute("SELECT id FROM transactions WHERE merchant LIKE 'FLAZZ%'").fetchone()[0])
        self.assertEqual(self.spent(), 200_000)                                   # the receipt is inside its own bank's row

    def test_a_pocket_is_in_its_banks_one_statement(self):
        rid = spend(self.conn, 156_541, "PHO STREET", category="makan", account_alias="jago-harian")["id"]
        self.upload("jago-utama", "c", ("2026-11-05", "Monthly spending: PHO STREET POS Transaction", -156_541))
        self.assertIsNotNone(self.merged(rid))                                    # 'Jago' and 'jago' are one bank
        self.assertEqual(self.spent(), 156_541)

    def test_a_card_purchase_is_never_a_bank_debit(self):
        rid = spend(self.conn, 75_000, "GRAB", category="transport", card_alias="cimb-1")["id"]
        self.upload("mandiri-utama", "d", ("2026-11-05", "QRIS GRAB", -75_000))
        self.assertIsNone(self.merged(rid))

    def test_a_purchase_is_never_a_move_between_own_accounts(self):
        mu.set_category_rule(self.conn, "Danu Pocket Pocket Money In", "transfer_internal")
        parkir = spend(self.conn, 100_000, "PARKIR", category="transport", account_alias="jago-harian")["id"]
        flazz = spend(self.conn, 100_000, "Isi saldo Flazz", day="2026-11-04", category="transfer_internal",
                      account_alias="jago-harian")["id"]
        self.upload("jago-utama", "e", ("2026-11-05", "Danu Pocket Pocket Money In", -100_000))
        self.assertIsNone(self.merged(parkir))                    # the closer date, but a pocket move is not a purchase
        self.assertIsNotNone(self.merged(flazz))                  # a move the owner recorded is one
        self.assertEqual(self.spent(), 100_000)

    def test_of_two_equal_debits_the_one_on_the_receipts_date_takes_it(self):
        rid = spend(self.conn, 50_000, "KOPI KENANGAN", day="2026-11-06", category="makan", account_alias="mandiri-utama")["id"]
        self.upload("mandiri-utama", "f", ("2026-11-05", "TRSF KE ANDI", -50_000), ("2026-11-06", "QRIS KOPI KENANGAN", -50_000))
        rows = {r["merchant"]: r for r in self.conn.execute("SELECT id, merchant, category FROM transactions WHERE source='mutation'")}
        self.assertEqual(self.merged(rid), rows["QRIS KOPI KENANGAN"]["id"])     # the old rule gave it to the first row
        self.assertEqual((rows["QRIS KOPI KENANGAN"]["category"], rows["TRSF KE ANDI"]["category"]), ("makan", None))

    def test_cash_is_never_a_bank_debit(self):
        """No account and no card is cash (2026-10-30): it took any bank's debit of that size; the receipt of the row's
        own account only went first."""
        cash = spend(self.conn, 80_000, "WARUNG")["id"]
        own = spend(self.conn, 80_000, "WARUNG BU SRI", account_alias="mandiri-utama")["id"]
        self.upload("mandiri-utama", "g", ("2026-11-05", "QRIS WARUNG BU SRI", -80_000), ("2026-11-06", "TRSF KE ANDI", -80_000))
        self.assertEqual((self.merged(cash), self.merged(own) is None), (None, False))    # the free row did not take it
        late = spend(self.conn, 80_000, "BAKSO", day="2026-11-06")                         # nor a record made after it
        self.assertEqual(("merged_into" in late, self.merged(late["id"])), (False, None))
        self.assertEqual(self.spent(), 320_000)

    def test_a_row_a_rule_sorted_keeps_its_category_and_status(self):
        """The record's category only fills a row that has none; the status was overwritten anyway, so a rule's row turned
        'unverified' (or a guess turned 'verified')."""
        mu.set_category_rule(self.conn, "TOKO ABC 123456", "belanja")
        first = spend(self.conn, 60_000, "TOKO ABC", category="makan", account_alias="bca-utama")["id"]
        self.upload("bca-utama", "h", ("2026-11-05", "TOKO ABC 654321", -60_000), ("2026-11-06", "TOKO ABC 654322", -60_000))
        late = spend(self.conn, 60_000, "TOKO ABC", day="2026-11-06", category="makan", account_alias="bca-utama")
        rows = self.conn.execute("SELECT id, category, status FROM transactions WHERE source='mutation' ORDER BY txn_date").fetchall()
        self.assertEqual([(r["category"], r["status"]) for r in rows], [("belanja", "verified")] * 2)
        self.assertEqual((self.merged(first), self.merged(late["id"])), (rows[0]["id"], rows[1]["id"]))
        self.assertIn("kategori yang dihitung belanja (dari mutasi), bukan makan", late["alerts"][0])


class LateRecordsAndResentScreenshots(_Banks, unittest.TestCase):
    """2026-10-30, owner: "ya betulkan juga". Matching ran only on upload and on ubah_belanja, so a purchase recorded after
    its statement counted twice; and the duplicate check skipped merged records, so the same screenshot sent again was
    stored a second time or hit the unique key."""

    def test_a_record_made_after_its_statement_merges_at_once_and_says_so(self):
        self.upload("bca-utama", "a", ("2026-11-05", "QRIS WARUNG BU SRI", -80_000), ("2026-11-06", "QRIS GRAB", -75_000))
        r = spend(self.conn, 80_000, "WARUNG BU SRI", category="makan", account_alias="bca-utama")
        mut = self.conn.execute("SELECT id FROM transactions WHERE merchant='QRIS WARUNG BU SRI'").fetchone()[0]
        self.assertEqual((r["status"], r.get("merged_into"), self.merged(r["id"])), ("stored", mut, mut))
        self.assertIn(f"sudah ada di mutasi bank #{mut} (QRIS WARUNG BU SRI, 2026-11-05, Rp 80.000, rekening bca-utama)",
                      r["alerts"][0])
        self.assertEqual(self.spent(), 155_000)                         # the two statement rows, nothing twice
        card = spend(self.conn, 75_000, "GRAB", day="2026-11-06", category="transport", card_alias="cimb-1")
        self.assertEqual(("merged_into" in card, self.merged(card["id"])), (False, None))   # it is on the card statement

    def test_a_record_past_its_banks_statements_waits_for_the_next_one(self):
        """The statement ends the day before: the record's own row is not in yet, and the window would hand it to another
        payment of the same size."""
        self.upload("bca-utama", "b", ("2026-11-04", "QRIS TOKO LAIN", -80_000), period=("2026-11-01", "2026-11-04"))
        r = spend(self.conn, 80_000, "WARUNG BU SRI", category="makan", account_alias="bca-utama")
        self.assertEqual(("merged_into" in r, self.merged(r["id"])), (False, None))
        self.upload("bca-utama", "c", ("2026-11-05", "QRIS WARUNG BU SRI", -80_000), period=("2026-11-05", "2026-11-30"))
        own = self.conn.execute("SELECT id FROM transactions WHERE merchant='QRIS WARUNG BU SRI'").fetchone()[0]
        self.assertEqual(self.merged(r["id"]), own)
        self.assertEqual(self.spent(), 160_000)                         # two payments, each counted once

    def test_a_resent_screenshot_of_a_merged_purchase_is_flagged_not_stored_again(self):
        """Live shape (PHO STREET #2440): recorded, corrected (its key is then id-based), merged on upload, the screenshot
        sent again in a new chat."""
        rid = spend(self.conn, 156_541, "PHO STREET", category="makan", account_alias="bca-utama")["id"]
        hl.edit_expense(self.conn, TODAY, rid, 156_541, "salah sumber, dari Jago harian", account_alias="jago-harian")
        self.upload("jago-utama", "d", ("2026-11-05", "Monthly spending: PHO STREET POS Transaction", -156_541))
        mut, n = self.merged(rid), self.count()
        self.assertIsNotNone(mut)
        dup = spend(self.conn, 156_541, "PHO STREET", category="makan", account_alias="jago-harian")
        self.assertEqual((dup["status"], dup.get("existing_id"), self.count()), ("possible_duplicate", rid, n))
        self.assertIn(f"sudah digabung dengan mutasi bank #{mut}", dup["message"])
        self.assertEqual(self.spent(), 156_541)

    def test_a_second_purchase_after_its_merged_twin_gets_its_own_key(self):
        first = spend(self.conn, 50_000, "KOPI KENANGAN", category="makan", account_alias="mandiri-utama")["id"]
        self.upload("mandiri-utama", "e", ("2026-11-05", "QRIS KOPI KENANGAN", -50_000))
        self.assertIsNotNone(self.merged(first))
        self.assertEqual(spend(self.conn, 50_000, "Kopi Kenangan", account_alias="mandiri-utama")["status"], "possible_duplicate")
        again = spend(self.conn, 50_000, "KOPI KENANGAN", category="makan", account_alias="mandiri-utama", allow_duplicate=True)
        self.assertEqual((again["status"], self.merged(again["id"])), ("stored", None))   # that row is the first purchase's

    def test_a_deleted_twin_leaves_no_key_clash(self):
        a = spend(self.conn, 50_000, "KOPI KENANGAN")["id"]
        spend(self.conn, 50_000, "KOPI KENANGAN", allow_duplicate=True)
        hl.delete_expense(self.conn, a, 50_000, "tercatat dua kali")
        self.assertEqual(spend(self.conn, 50_000, "KOPI KENANGAN", allow_duplicate=True)["status"], "stored")


class Pace(unittest.TestCase):
    def test_status_thresholds_against_the_daily_allowance(self):
        for spent, status in ((3_000_000, "ok"), (4_500_000, "ok"), (5_500_000, "watch"), (8_000_000, "watch"), (10_000_001, "over")):
            conn = planned()
            spend(conn, spent)
            p = hl.spending_pace(conn, TODAY)
            self.assertEqual((p["allowance"], p["elapsed_pct"], p["status"]), (10_000_000, 38, status), spent)

    def test_obligations_pot_and_internal_moves_are_not_daily_spending(self):
        conn = planned()
        spend(conn, 3_000_000, "SEKOLAH", category="wajib:sekolah")
        spend(conn, 9_000_000, "SETOR POT", category="sinking:hutang-teman")
        spend(conn, 2_000_000, "KE TABUNGAN", category="transfer_internal")
        spend(conn, 100_000, "MAKAN", category="makan")
        self.assertEqual(hl.spending_pace(conn, TODAY)["spent"], 100_000)

    def test_no_plan_or_plan_for_another_window_gives_none(self):
        conn = connect(":memory:")
        self.assertIsNone(hl.spending_pace(conn, TODAY))
        self.assertIsNone(hl.spending_pace(planned(), date(2026, 12, 15)))
        self.assertIsNone(hl.spending_pace(planned(), date(2026, 10, 29)))

    def test_alert_comes_back_right_after_the_purchase(self):
        conn = planned()
        r = spend(conn, 6_000_000, "TV", category="elektronik")
        self.assertTrue(any("Waspada" in a and "60%" in a for a in r["alerts"]), r["alerts"])
        r = spend(conn, 5_000_000, "LAPTOP", category="elektronik", day="2026-11-06")
        self.assertTrue(any("MELEBIHI JATAH" in a for a in r["alerts"]), r["alerts"])


class LivingMoneyPace(unittest.TestCase):
    """Regression 2026-10-31: right after a purchase the pace said 22% of the daily money was used, counting only the
    2.827.889 top-up from the salary. The owner's month was that plus the 4.718.116 leftover already held: 7.546.005."""
    PAYDAY, DAY2 = date(2026, 10, 30), date(2026, 10, 31)

    def world(self, card=False, early=False):
        conn = connect(":memory:")
        conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('jago-harian','Jago','main')")
        conn.commit()
        tools.upsert_card(conn, "cimb-1", "CIMB", "2222", 5, 5, 10_000_000)
        tools.set_threshold(conn, "net_salary", 2_827_889)                   # no bills: the whole salary is the top-up
        tools.set_threshold(conn, "living_reserve", 7_546_005)
        if early:
            tools.set_leftover_living_cash(conn, 4_894_157, date(2026, 10, 28))   # an estimate two days before the payday
        hl.record_expense(conn, self.PAYDAY, 17_000, "WARKOP DANI", "2026-10-30", "makan", "jago-harian")  # before the reading
        if card:
            hl.record_expense(conn, self.PAYDAY, 90_000, "GRAB", "2026-10-30", "transport", card_alias="cimb-1")
        self.msg = tools.set_leftover_living_cash(conn, 4_718_116, self.PAYDAY)
        tools.generate_payday_plan(conn, self.PAYDAY, payday=self.PAYDAY)
        for amount, merchant, day in ((150_000, "PARKIR", "2026-10-30"), (51_000, "WARTEG", "2026-10-30"),
                                      (174_075, "YONNY", "2026-10-31")):
            hl.record_expense(conn, self.DAY2, amount, merchant, day, "makan", "jago-harian")
        return conn

    def test_the_top_up_plus_the_leftover_is_the_allowance(self):
        conn = self.world()
        self.assertIn("(Rp 17.000) sudah keluar dari sisa ini", self.msg)
        r = hl.record_expense(conn, self.DAY2, 249_000, "ANKER", "2026-10-31", "belanja", "jago-harian")
        self.assertFalse(any("Waspada" in a or "MELEBIHI" in a for a in r["alerts"]), r["alerts"])   # was "22% terpakai"
        p = hl.spending_pace(conn, self.DAY2)
        self.assertEqual((p["allowance"], p["from_salary"], p["leftover"]), (7_546_005, 2_827_889, 4_718_116))
        self.assertEqual((p["spent"], p["spent_before_leftover"], p["pct_used"], p["elapsed_pct"], p["status"]),
                         (624_075, 17_000, 8, 6, "ok"))                     # the coffee is already out of the leftover
        self.assertEqual((p["remaining"], p["days_left"], p["safe_per_day"]), (6_921_930, 29, 238_687))

    def test_the_same_figure_given_again_keeps_the_first_reading(self):
        conn = self.world()
        tools.set_leftover_living_cash(conn, 4_718_116, self.DAY2)        # asked again a day later: nothing new in it
        p = hl.spending_pace(conn, self.DAY2)
        self.assertEqual((p["spent_before_leftover"], p["spent"]), (17_000, 375_075))
        self.assertIn("SISA UANG HARIAN TERCATAT: Rp 4.718.116 untuk gajian 2026-10-30 (dicatat 2026-10-30); belanja tunai "
                      "sejak gajian sebelum laporan itu Rp 17.000 sudah keluar", tools.data_overview(conn, self.DAY2))

    def test_a_corrected_figure_days_later_keeps_the_payday_count(self):
        conn = self.world()
        msg = tools.set_leftover_living_cash(conn, 4_500_000, date(2026, 11, 2))
        self.assertIn("sebelum laporan sisa pertama 2026-10-30 (Rp 17.000)", msg)
        self.assertEqual((tools.get_threshold(conn, "living_leftover"), tools.get_threshold(conn, "living_leftover_at")),
                         (4_500_000, 20261030))
        p = hl.spending_pace(conn, date(2026, 11, 2))      # the purchases since the payday were not in the figure: still counted
        self.assertEqual((p["spent_before_leftover"], p["spent"]), (17_000, 375_075))

    def test_an_estimate_before_the_payday_is_counted_again_on_the_payday(self):
        conn = self.world(early=True)
        p = hl.spending_pace(conn, self.DAY2)
        self.assertEqual((p["spent_before_leftover"], p["spent"], tools.get_threshold(conn, "living_leftover_at")),
                         (17_000, 375_075, 20261030))

    def test_a_card_purchase_was_never_in_the_leftover(self):
        p = hl.spending_pace(self.world(card=True), self.DAY2)
        self.assertEqual((p["spent_before_leftover"], p["spent"]), (17_000, 465_075))

    def test_the_plan_and_the_reports_show_the_whole_month(self):
        conn = self.world()
        text = tools.summarize_plan(tools.generate_payday_plan(conn, self.DAY2))
        self.assertIn("uang harian bulan ini Rp 7.546.005 = Rp 2.827.889 dari gaji + sisa Rp 4.718.116", text)
        self.assertIn("jatah harian Rp 243.419", text)                    # 7.546.005 // 31, not 2.827.889 // 31 = 91.222
        self.assertIn("<b>Rp 7.546.005</b> (sekitar <b>Rp 243.419</b> per hari)", reports._rencana(conn, self.DAY2))
        budget = reports._anggaran(conn, self.DAY2)
        self.assertIn("Terpakai <b>Rp 375.075</b> dari Rp 7.546.005 (Rp 2.827.889 dari gaji + sisa Rp 4.718.116)", budget)
        self.assertIn("Sisa <b>Rp 7.170.930</b>, sekitar Rp 247.273/hari", budget)


class Budgets(unittest.TestCase):
    def test_thresholds_and_exact_100_percent(self):
        for spent, status in ((790_000, "ok"), (800_000, "watch"), (1_000_000, "watch"), (1_000_001, "over")):
            conn = planned(100_000_000)           # huge allowance so only the budget alert fires
            hl.set_budget(conn, "Makan", 1_000_000)
            spend(conn, spent, "RESTO", category="makan")
            (b,) = hl.budget_status(conn, "2026-11")
            self.assertEqual((b["category"], b["status"]), ("makan", status), spent)

    def test_card_budget_counts_only_card_purchases_and_cash_never_eats_it(self):
        """Regression: a Tokopedia payment from a bank account (electricity token) ate the card budget (3060%)."""
        conn = planned(100_000_000)
        tools.upsert_card(conn, "c-1", "CIMB", "1111", 5, 20, 5_000_000)
        hl.set_budget(conn, "kartu:belanja-online", 300_000)
        spend(conn, 900_000, "TOKOPEDIA TOKEN LISTRIK", category="belanja-online")             # cash
        (b,) = hl.budget_status(conn, "2026-11")
        self.assertEqual((b["category"], b["spent"], b["status"]), ("kartu:belanja-online", 0, "ok"))
        r = spend(conn, 350_000, "SHOPEE", category="belanja-online", card_alias="c-1")
        self.assertTrue(any("Anggaran kartu:belanja-online" in a and "SUDAH LEWAT" in a for a in r["alerts"]), r["alerts"])
        hl.set_budget(conn, "belanja-online", 1_000_000)                                       # cash budget is separate
        by = {x["category"]: x for x in hl.budget_status(conn, "2026-11")}
        self.assertEqual((by["belanja-online"]["spent"], by["kartu:belanja-online"]["spent"]), (900_000, 350_000))

    def test_a_small_refund_does_not_make_the_month_before_payday_look_like_a_deficit(self):
        conn = planned(100_000_000)
        spend(conn, 5_000_000, "BELANJA", category="makan")
        conn.execute("INSERT INTO transactions(txn_date,merchant,amount,status,source) VALUES ('2026-11-03','REFUND TOKO',500000,'unverified','mutation')")
        conn.commit()
        h = hl.health_check(conn, TODAY, "2026-11")
        self.assertFalse(any(sev == "bad" and "LEBIH BESAR dari pemasukan" in t for sev, t in h["findings"]), h["findings"])

    def test_budget_alert_included_when_over(self):
        conn = planned(100_000_000)
        hl.set_budget(conn, "makan", 500_000)
        r = spend(conn, 600_000, "RESTO", category="makan")
        self.assertTrue(any("Anggaran makan" in a and "SUDAH LEWAT" in a for a in r["alerts"]))
        with self.assertRaises(ValueError):
            hl.set_budget(conn, "", 1)
        with self.assertRaises(ValueError):
            hl.set_budget(conn, "x", -1)


def cash_month(conn, income, expense, h, alias="mandiri-utama", opening=None, closing=None, month="2026-11"):
    rows = []
    if income:
        rows.append({"date": f"{month}-25", "description": "GAJI", "amount": income})
    if expense:
        rows.append({"date": f"{month}-10", "description": "BELANJA BULANAN", "amount": -expense})
    mu.record_mutations(conn, alias, h * 64, f"{month}-01", f"{month}-28", opening, closing, rows)


class Health(unittest.TestCase):
    def verdict(self, conn, month="2026-11"):
        return hl.health_check(conn, TODAY, month)

    def test_deficit_month_is_bad(self):
        conn = planned()
        cash_month(conn, 5_000_000, 6_000_000, "a")
        h = self.verdict(conn)
        self.assertEqual(h["verdict"], "BURUK")
        self.assertTrue(any("LEBIH BESAR" in t and "defisit Rp 1.000.000" in t for s, t in h["findings"]))

    def test_month_in_progress_before_payday_is_not_judged_as_a_deficit(self):
        conn = planned()
        mu.record_mutations(conn, "mandiri-utama", "z" * 64, "2026-11-01", "2026-11-10", None, None,
                            [{"date": "2026-11-05", "description": "BELANJA", "amount": -3_000_000}])    # no salary yet
        h = hl.health_check(conn, TODAY, "2026-11")                                                     # today is 2026-11-10; payday 2026-11-30
        self.assertFalse(any(s == "bad" for s, _ in h["findings"]))
        self.assertTrue(any("belum lengkap: gaji baru masuk sekitar 2026-11-30" in t for _, t in h["findings"]))
        self.assertEqual(h["verdict"], "SEHAT")
        # the same numbers for a month that is over ARE a deficit
        late = hl.health_check(conn, date(2026, 12, 5), "2026-11")
        self.assertTrue(any("LEBIH BESAR" in t for _, t in late["findings"]))

    def test_good_month_is_healthy_and_low_saving_is_a_warning(self):
        conn = planned()
        cash_month(conn, 10_000_000, 2_000_000, "a")
        self.assertEqual(self.verdict(conn)["verdict"], "SEHAT")
        conn2 = planned()
        cash_month(conn2, 10_000_000, 9_500_000, "b")                    # saves 5%, floor is 10%
        h = self.verdict(conn2)
        self.assertEqual(h["verdict"], "WASPADA")
        self.assertTrue(any("di bawah target 10.0%" in t for _, t in h["findings"]))

    def test_owner_savings_target_and_floor_are_respected(self):
        conn = planned()
        cash_month(conn, 10_000_000, 7_000_000, "a")                      # saves 3M = 30%
        tools.set_threshold(conn, "monthly_savings_target", 4_000_000)
        self.assertTrue(any("target tabungan Rp 4.000.000" in t for _, t in self.verdict(conn)["findings"]))
        tools.set_threshold(conn, "min_savings_rate_bp", 4000)
        self.assertTrue(any("di bawah target 40.0%" in t for _, t in self.verdict(conn)["findings"]))

    def test_debt_service_over_the_limit_is_bad(self):
        conn = planned()
        tools.upsert_debt(conn, "mobil", "MTF", 100_000_000, 4_000_000, 25, 2, 815)     # 40% of a 10M salary
        d = hl.debt_load(conn)
        self.assertEqual((d["monthly_payments"], d["dsr_bp"], d["dsr_max_bp"]), (4_000_000, 4000, 3000))
        h = self.verdict(conn)
        self.assertEqual(h["verdict"], "BURUK")
        self.assertTrue(any("Beban utang 40.0%" in t for _, t in h["findings"]))

    def test_growing_total_debt_vs_last_month_is_flagged(self):
        conn = planned()
        tools.upsert_debt(conn, "mobil", "MTF", 100_000_000, 1_000_000, 25, 2, 815)
        hl.snapshot(conn, date(2026, 10, 15))
        tools.upsert_debt(conn, "pinjaman-baru", "Bank", 20_000_000, 500_000, 40, 5, 1200)
        h = self.verdict(conn)
        self.assertTrue(any("Total utang naik dari Rp 100.000.000 (2026-10) menjadi Rp 120.000.000" in t for _, t in h["findings"]))
        self.assertEqual(h["verdict"], "BURUK")
        conn2 = planned()
        tools.upsert_debt(conn2, "mobil", "MTF", 100_000_000, 1_000_000, 25, 2, 815)
        hl.snapshot(conn2, date(2026, 10, 15))
        tools.upsert_debt(conn2, "mobil", "MTF", 95_000_000, 1_000_000, 24, 2, 815)       # paid down
        self.assertFalse(any("Total utang naik" in t for _, t in self.verdict(conn2)["findings"]))

    def test_balance_trend_and_buffer(self):
        conn = planned()
        for i, (month, closing) in enumerate((("2026-08", 9_000_000), ("2026-09", 7_000_000), ("2026-10", 5_000_000))):
            cash_month(conn, 1_000_000, 500_000, str(i + 1), month=month, opening=closing - 500_000, closing=closing)
        h = self.verdict(conn, "2026-10")
        self.assertTrue(any("Saldo mandiri-utama turun 2 periode berturut-turut" in t for _, t in h["findings"]))
        tools.set_threshold(conn, "cash_buffer", 6_000_000)
        self.assertTrue(any("di bawah buffer Rp 6.000.000" in t for s, t in self.verdict(conn, "2026-10")["findings"] if s == "bad"))

    def test_pace_findings_and_text_report(self):
        conn = planned()
        spend(conn, 11_000_000, "BELANJA BESAR", category="elektronik")
        h = self.verdict(conn)
        self.assertTrue(any("Pengeluaran harian" in t for _, t in h["findings"]))
        text = hl.format_health(h)
        self.assertTrue(text.startswith("Penilaian keuangan 2026-11: BURUK"))
        self.assertIn("!! Pengeluaran harian", text)
        self.assertIn("Total utang Rp 0", text)

    def test_empty_ledger_is_not_a_crash(self):
        h = hl.health_check(connect(":memory:"), TODAY)
        self.assertEqual(h["verdict"], "SEHAT")
        self.assertTrue(any("Belum ada mutasi" in t for _, t in h["findings"]))


try:
    from starlette.testclient import TestClient  # noqa: F401
    from vault_tools.server import MCP_TOOL_NAMES, create_app
    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class ThroughTheTools(unittest.TestCase):
    def test_screenshot_flow_budget_alert_and_health_report(self):
        with tempfile.TemporaryDirectory() as d:
            app = create_app(os.path.join(d, "l.db"), bytes(range(32)), "m" * 40, "i" * 40, allowed_hosts=["testserver"],
                             today=lambda: TODAY, ingest_dir=d, passwords_path=None)
            call = lambda n, a=None: json.loads(json.dumps(asyncio.run(app.state.mcp.call_tool(n, a or {})), default=str))  # noqa: E731
            self.assertTrue({"record_expense", "set_budget", "budget_status", "health_check", "list_statements"} <= set(MCP_TOOL_NAMES))
            call("set_threshold", {"key": "net_salary", "value": 10_000_000})
            call("generate_payday_plan", {"payday": "2026-10-30"})
            call("set_budget", {"category": "makan", "monthly_amount": 500_000})
            res = json.dumps(call("record_expense", {"amount": 600_000, "merchant": "RESTO", "txn_date": "2026-11-05", "category": "makan",
                                                     "tunai": True}))
            self.assertIn("SUDAH LEWAT", res)
            self.assertIn("makan: Rp 600.000 dari Rp 500.000 (120%) over", json.dumps(call("budget_status")))
            self.assertIn("Penilaian keuangan 2026-11:", json.dumps(call("health_check")))
            self.assertIn("Belum ada tagihan tersimpan", json.dumps(call("list_statements")))
            call("upsert_card", {"alias": "hsbc-1", "bank": "HSBC", "last4": "5915", "statement_day": 19, "due_day": 5, "credit_limit": 10_000_000})
            h = "e" * 64
            call("record_statement", {"card_alias": "hsbc-1", "file_hash": h, "statement_date": "2026-10-19", "due_date": "2026-11-05",
                                      "previous_balance": 0, "payments": 0, "charges": 1000, "fees": 0, "total_due": 1000, "minimum_due": 100})
            self.assertNotIn("file_ref", json.dumps(call("list_statements")))              # the file is gone: no dangling reference
            open(os.path.join(d, h + ".pdf"), "wb").close()
            self.assertIn(f"file_ref {h}.pdf", json.dumps(call("list_statements", {"card_alias": "hsbc-1"})))
            self.assertIn("Belum ada tagihan tersimpan", json.dumps(call("list_statements", {"card_alias": "none"})))


if __name__ == "__main__":
    unittest.main()
