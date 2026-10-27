import asyncio
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import living as lv  # noqa: E402
from vault_tools import mutations as mu  # noqa: E402
from vault_tools import suggest as sg  # noqa: E402
from vault_tools import tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402

TODAY = date(2026, 10, 27)


def tx(conn, account, day, desc, amount, category=None):
    conn.execute("INSERT INTO transactions(account_id,txn_date,merchant,amount,category,status,source) VALUES (?,?,?,?,?,?,'mutation')",
                 (account, day, desc, amount, category, "verified" if category else "unverified"))


def world(salary=42_000_000):
    conn = connect(":memory:")
    conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('bca-utama','BCA','main')")       # id 1: main until June
    conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('mandiri-utama','Mandiri','main')")  # id 2: main since July
    cash = {"01": 10, "02": 12, "03": 11, "04": 9, "05": 13, "06": 10, "07": 14, "08": 12, "09": 16}    # million per month
    for m, millions in cash.items():
        month = f"2026-{m}"
        acct = 1 if int(m) <= 6 else 2
        if m == "07":                                              # the move: part of July is still on BCA
            tx(conn, 1, f"{month}-03", "QR MAKAN", -4_000_000, "makan")
            tx(conn, 2, f"{month}-12", "QR MAKAN", -10_000_000, "makan")
        else:
            tx(conn, acct, f"{month}-10", "QR MAKAN", -millions * 1_000_000, "makan")
        tx(conn, acct, f"{month}-25", "GAJI", 30_000_000 if int(m) <= 6 else 42_000_000, "gaji")
        tx(conn, acct, f"{month}-26", "PINDAH DANA KE REKENING SENDIRI", -5_000_000, "transfer_internal")
        tx(conn, acct, f"{month}-27", "BAYAR SEKOLAH", -3_000_000, "wajib:sekolah")
        tx(conn, acct, f"{month}-28", "KLAIM JHT", -1_000_000, "sekali:x")
    # March: half of the money out was never categorized -> that month must be skipped
    tx(conn, 1, "2026-03-15", "TRANSFER MISTERI", -20_000_000, None)
    tx(conn, 2, "2026-10-05", "OCT MAKAN", -99_000_000, "makan")                         # current month: never counted
    tools.set_threshold(conn, "net_salary", salary)
    tools.upsert_expense(conn, "sekolah", "sekolah-va", 4_000_000, 1)
    tools.upsert_debt(conn, "mobil", "MTF", 108_319_000, 5_701_000, 19, 2, 815)
    for month, charges in (("2026-08", 5_000_000), ("2026-09", 7_000_000)):
        conn.execute("INSERT OR IGNORE INTO cards(alias,bank,last4,statement_day,due_day,credit_limit) VALUES ('c1','X','1111',5,20,1000)")
        conn.execute("INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,fees,total_due,"
                     "minimum_due,reconciled,recon_diff,ingested_at) VALUES (1,?,?,?,0,0,?,0,?,1,1,0,'t')",
                     (month * 5, f"{month}-05", f"{month}-20", charges, charges))
    conn.commit()
    return conn


class Monthly(unittest.TestCase):
    def test_sums_across_accounts_and_excludes_non_living_money(self):
        m = lv.monthly(world(), TODAY)
        self.assertEqual(m["2026-07"]["cash"], 14_000_000)                    # 4M on BCA + 10M on Mandiri
        self.assertEqual(m["2026-07"]["excluded"], 5_000_000 + 3_000_000 + 1_000_000)   # internal + wajib + sekali
        self.assertEqual(m["2026-07"]["salary_in"], 42_000_000)
        self.assertEqual(m["2026-02"]["salary_in"], 30_000_000)               # the old salary, before the job change
        self.assertNotIn("2026-10", m)                                        # current month is never history

    def test_coverage_flags_a_poorly_categorized_month(self):
        m = lv.monthly(world(), TODAY)
        self.assertEqual(m["2026-03"]["uncategorized"], 20_000_000)
        self.assertLess(m["2026-03"]["coverage_pct"], lv.MIN_COVERAGE_PCT)
        self.assertEqual(m["2026-04"]["coverage_pct"], 100)


class Analysis(unittest.TestCase):
    def test_default_window_is_the_last_six_complete_months(self):
        a = lv.analyse(world(), TODAY)
        self.assertEqual(a["counted"], ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"])
        # Apr 9, May 13, Jun 10, Jul 14, Aug 12, Sep 16 (million) -> sorted 9,10,12,13,14,16 -> median 12.5M
        self.assertEqual((a["tight"], a["recommended"], a["loose"]), (12_500_000, 13_750_000, 16_000_000))

    def test_from_january_skips_the_untidy_month_and_uses_the_median_of_the_rest(self):
        a = lv.analyse(world(), TODAY, from_month="2026-01")
        self.assertEqual(a["skipped"], ["2026-03"])
        self.assertEqual(len(a["counted"]), 8)
        self.assertEqual((a["tight"], a["recommended"], a["loose"]), (12_000_000, 13_200_000, 16_000_000))   # 9,10,10,12,12,13,14,16

    def test_since_the_job_change_and_monthly_free_against_todays_salary(self):
        a = lv.analyse(world(), TODAY, from_month="2026-07")
        self.assertEqual((a["tight"], a["recommended"], a["loose"]), (14_000_000, 15_400_000, 16_000_000))
        self.assertEqual(a["card_avg"], 6_000_000)                            # (5M + 7M) / 2
        self.assertEqual(a["commitments"], {"fixed": 4_000_000, "installments": 5_701_000, "pot": 0, "total": 9_701_000})
        self.assertEqual(a["monthly_free"], 42_000_000 - 9_701_000 - 15_400_000 - 6_000_000)    # 10,899,000
        text = lv.format_analysis(a)
        self.assertIn("sisa Rp 10.899.000 untuk tabungan dan pelunasan", text)
        self.assertIn("ketat Rp 14.000.000 (median), disarankan Rp 15.400.000 (median + 10%), longgar Rp 16.000.000", text)
        self.assertIn("gaji masuk Rp 42.000.000", text)
        self.assertIn("minta persetujuan pemilik lalu set_threshold living_reserve", text)

    def test_deficit_is_called_out(self):
        text = lv.format_analysis(lv.analyse(world(salary=20_000_000), TODAY, from_month="2026-07"))
        self.assertIn("DEFISIT", text)
        self.assertIn("-Rp 11.101.000", text)

    def test_one_month_is_marked_provisional_and_none_gives_a_clear_message(self):
        conn = connect(":memory:")
        self.assertIn("Belum ada mutasi bulan penuh", lv.format_analysis(lv.analyse(conn, TODAY)))
        conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('a','X','main')")
        tx(conn, 1, "2026-09-10", "MAKAN", -5_000_000, "makan")
        conn.commit()
        a = lv.analyse(conn, TODAY)
        self.assertFalse(a["enough"])
        self.assertIn("BARU 1 BULAN DATA", lv.format_analysis(a))

    def test_unset_salary_and_current_reserve_are_reported(self):
        conn = world()
        conn.execute("DELETE FROM thresholds WHERE key='net_salary'")
        tools.set_threshold(conn, "living_reserve", 8_000_000)
        text = lv.format_analysis(lv.analyse(conn, TODAY, from_month="2026-07"))
        self.assertIn("net_salary belum diset", text)
        self.assertIn("living_reserve yang berlaku sekarang: Rp 8.000.000", text)

    def test_mostly_uncategorized_history_gives_no_recommendation(self):
        conn = connect(":memory:")
        conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('a','X','main')")
        for m in ("2026-08", "2026-09"):
            tx(conn, 1, f"{m}-10", "APA SAJA", -9_000_000, None)
            tx(conn, 1, f"{m}-11", "MAKAN", -1_000_000, "makan")
        conn.commit()
        a = lv.analyse(conn, TODAY)
        self.assertIsNone(a["recommended"])
        self.assertIn("Belum bisa merekomendasikan living_reserve", lv.format_analysis(a))


class Suggestions(unittest.TestCase):
    def descs(self, conn, items):
        conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('a','X','main')")
        for desc, amount in items:
            tx(conn, 1, "2026-09-10", desc, amount)
        conn.commit()

    def test_rules_on_real_looking_descriptors(self):
        owners = ["danuarta wiratama"]
        cases = [
            ("transfer bi fast ke bca danuarta wiratama", -1, "transfer_internal"),
            ("transfer bi fast ke bca budi santoso", -1, None),
            ("pembayaran hsbc", -1, "wajib:kartu"),
            ("pembayaran dbs / ex - anz", -1, "wajib:kartu"),
            ("pembayaran kartu kredit", -1, "wajib:kartu"),
            ("biaya transaksi bank pembayaran hsbc", -1, "biaya-bank"),               # must not look like a card payment
            ("biaya transfer bi fast", -1, "biaya-bank"),
            ("pembayaran spaylater #", -1, "wajib:spaylater"),
            ("pendebitan otomatis auto coll # ang ke", -1, "wajib:cicilan"),
            ("pembayaran tokopedia", -1, "belanja-online"),
            ("pembayaran qr ke gado-gado pak jae", -1, "makan"),
            ("transaksi di edc yakiniku ten tangerang", -1, "makan"),
            ("pembayaran qr ke indomaret", -1, "belanja-harian"),
            ("transfer ke bank lain bca anetasia anggoro", -1, None),
            ("pembayaran klaim jht bpjs ketenagakerjaan", 1, "sekali:jht"),
            ("gaji pt maju", 1, "gaji"),
            ("transfer masuk dari budi", 1, None),
        ]
        for desc, sign, want in cases:
            self.assertEqual(sg.suggest_category(desc, sign * 1000, owners), want, desc)

    def test_owner_name_is_needed_and_validated(self):
        conn = connect(":memory:")
        self.descs(conn, [("Transfer BI Fast Ke BCA DANUARTA WIRATAMA", -5_000_000)])
        self.assertIsNone(next(iter(sg.groups(conn).values()))["suggestion"])
        with self.assertRaises(ValueError):
            sg.add_owner_name(conn, "ab")
        sg.add_owner_name(conn, "  Danuarta   Wiratama ")
        self.assertEqual(next(iter(sg.groups(conn).values()))["suggestion"], "transfer_internal")

    def test_suggestions_list_and_apply_all(self):
        conn = connect(":memory:")
        self.descs(conn, [("Pembayaran HSBC", -23_000_000), ("Pembayaran HSBC", -23_000_000), ("Pembayaran Tokopedia 123456789", -500_000),
                          ("Transfer ke bank lain BCA ANETASIA", -800_000)])
        lines = sg.suggestions(conn)
        self.assertEqual(lines[0], "pembayaran hsbc | 2x | Rp 46.000.000 | usulan: wajib:kartu")
        self.assertIn("pembayaran tokopedia # | 1x | Rp 500.000 | usulan: belanja-online", lines)
        self.assertIn("1 kelompok lain tanpa usulan, total Rp 800.000", lines[-1])
        self.assertEqual(sg.apply_suggestions(conn), "2 kelompok dikategorikan (3 transaksi)")
        cats = {r["merchant"]: (r["category"], r["status"]) for r in conn.execute("SELECT merchant, category, status FROM transactions")}
        self.assertEqual(cats["Pembayaran HSBC"], ("wajib:kartu", "verified"))
        self.assertEqual(cats["Transfer ke bank lain BCA ANETASIA"], (None, "unverified"))     # no suggestion: left alone
        left = sg.suggestions(conn)
        self.assertEqual(len(left), 1)                                                          # only the "no suggestion" remainder
        self.assertTrue(left[0].startswith("(1 kelompok lain tanpa usulan, total Rp 800.000"))

    def test_apply_only_the_listed_descriptors_and_rules_cover_future_rows(self):
        conn = connect(":memory:")
        self.descs(conn, [("Pembayaran HSBC", -1_000_000), ("Pembayaran Tokopedia", -2_000_000)])
        self.assertEqual(sg.apply_suggestions(conn, ["pembayaran hsbc"]), "1 kelompok dikategorikan (1 transaksi)")
        self.assertEqual(conn.execute("SELECT category FROM transactions WHERE merchant='Pembayaran Tokopedia'").fetchone()[0], None)
        mu.record_mutations(conn, "a", "a" * 64, "2026-10-01", "2026-10-31", None, None,
                            [{"date": "2026-10-15", "description": "Pembayaran HSBC", "amount": -5_000_000}])
        self.assertEqual(conn.execute("SELECT category FROM transactions WHERE txn_date='2026-10-15'").fetchone()[0], "wajib:kartu")

    def test_nothing_to_suggest(self):
        self.assertEqual(sg.suggestions(connect(":memory:"))[0].split(":")[0], "Tidak ada usulan")


try:
    from starlette.testclient import TestClient  # noqa: F401
    from vault_tools.server import MCP_TOOL_NAMES, create_app
    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class Tools(unittest.TestCase):
    def test_flow_through_the_tools(self):
        with tempfile.TemporaryDirectory() as d:
            app = create_app(os.path.join(d, "l.db"), bytes(range(32)), "m" * 40, "i" * 40, allowed_hosts=["testserver"],
                             today=lambda: TODAY, ingest_dir=d, passwords_path=None)
            call = lambda n, a=None: asyncio.run(app.state.mcp.call_tool(n, a or {}))  # noqa: E731
            self.assertTrue({"add_owner_name", "suggest_categories", "apply_suggestions", "living_cost_analysis"} <= set(MCP_TOOL_NAMES))
            call("upsert_account", {"alias": "m", "bank": "Mandiri", "kind": "main"})
            for i, month in enumerate(("2026-08", "2026-09")):
                call("record_mutations", {"account_alias": "m", "file_hash": str(i) * 64, "period_start": f"{month}-01",
                                          "period_end": f"{month}-28", "rows": [
                    {"date": f"{month}-05", "description": "Pembayaran QR ke GADO-GADO PAK JAE", "amount": -6_000_000},
                    {"date": f"{month}-06", "description": "Pembayaran HSBC", "amount": -1_000_000}]})
            self.assertIn("pembayaran qr ke gado-gado pak jae", str(call("suggest_categories")))
            self.assertIn("2 kelompok dikategorikan (4 transaksi)", str(call("apply_suggestions")))
            self.assertIn("disarankan Rp 6.600.000", str(call("living_cost_analysis")))
            with self.assertRaises(Exception):
                call("living_cost_analysis", {"from_month": "202608"})


if __name__ == "__main__":
    unittest.main()
