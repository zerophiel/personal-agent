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
        spend(self.conn, 50_000, "KOPI KENANGAN", day="2026-11-05", category="makan")

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


class Budgets(unittest.TestCase):
    def test_thresholds_and_exact_100_percent(self):
        for spent, status in ((790_000, "ok"), (800_000, "watch"), (1_000_000, "watch"), (1_000_001, "over")):
            conn = planned(100_000_000)           # huge allowance so only the budget alert fires
            hl.set_budget(conn, "Makan", 1_000_000)
            spend(conn, spent, "RESTO", category="makan")
            (b,) = hl.budget_status(conn, "2026-11")
            self.assertEqual((b["category"], b["status"]), ("makan", status), spent)

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
            res = json.dumps(call("record_expense", {"amount": 600_000, "merchant": "RESTO", "txn_date": "2026-11-05", "category": "makan"}))
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
