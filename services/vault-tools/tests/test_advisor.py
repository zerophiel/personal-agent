import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import health as hl  # noqa: E402
from vault_tools import tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402
from vault_tools.payday import Obligation, build_plan  # noqa: E402
from vault_tools.payee_vault import PayeeVault  # noqa: E402

TODAY = date(2026, 10, 27)      # payday 2026-10-30, next 2026-11-30


def statement(conn, card_id, total, minimum, due="2026-11-20", h=None):
    conn.execute(
        "INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,fees,total_due,"
        "minimum_due,reconciled,recon_diff,ingested_at) VALUES (?,?,?,?,0,0,?,0,?,?,1,0,'t')",
        (card_id, h or f"{card_id}" * 64, "2026-10-05", due, total, total, minimum))
    conn.commit()


def world(salary=20_000_000, reserve=3_000_000, fixed=4_000_000):
    """Two cards: A (2.75%/month, due late) and B (default 2.25%, due earlier), one fixed expense."""
    conn = connect(":memory:")
    tools.set_threshold(conn, "net_salary", salary)
    if reserve is not None:
        tools.set_threshold(conn, "living_reserve", reserve)
    tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 10_000_000, interest_bp_month=275)
    tools.upsert_card(conn, "cimb-1", "CIMB", "2222", 5, 5, 10_000_000)
    statement(conn, 1, 8_000_000, 800_000, due="2026-11-25")
    statement(conn, 2, 6_000_000, 600_000, due="2026-11-05")
    if fixed:
        tools.upsert_expense(conn, "sekolah", "sekolah-va", fixed, 1)
    return conn


def amounts(snap, alias):
    return [t["amount"] for t in snap["transfers"] if t["to_alias"] == alias]


class Engine(unittest.TestCase):
    def test_reserve_is_paid_after_obligations_and_minimums_but_before_card_balances(self):
        obs = [Obligation("fixed", "sekolah", date(2026, 11, 1), 4_000_000),
               Obligation("card", "a", date(2026, 11, 20), 6_000_000, 600_000)]
        p = build_plan(date(2026, 10, 30), 10_000_000, obs, reserve=2_000_000)
        self.assertEqual([t.amount for t in p.transfers if t.to_alias == "a"], [600_000, 3_400_000])   # 10 - 4 - 2 = 4M for card
        self.assertEqual((p.cash_to_hold, p.reserve), (2_000_000, 2_000_000))
        self.assertEqual(p.unfunded[0].amount, 2_000_000)
        self.assertIn("dicadangkan untuk hidup harian", p.warnings[0])

    def test_minimums_and_essentials_are_never_taken_by_the_reserve(self):
        obs = [Obligation("fixed", "sekolah", date(2026, 11, 1), 8_000_000),
               Obligation("card", "a", date(2026, 11, 20), 6_000_000, 600_000)]
        p = build_plan(date(2026, 10, 30), 10_000_000, obs, reserve=5_000_000)
        self.assertEqual([t.amount for t in p.transfers], [600_000, 8_000_000])                        # min + essential paid
        self.assertEqual(p.cash_to_hold, 1_400_000)                                                    # reserve cannot be filled fully

    def test_no_reserve_keeps_the_old_behaviour(self):
        obs = [Obligation("card", "a", date(2026, 11, 20), 6_000_000, 600_000)]
        p = build_plan(date(2026, 10, 30), 10_000_000, obs)
        self.assertEqual(([t.amount for t in p.transfers], p.cash_to_hold, p.reserve), ([600_000, 5_400_000], 4_000_000, 0))

    def test_extra_card_payments_go_to_the_highest_interest_card_first(self):
        obs = [Obligation("card", "low", date(2026, 11, 5), 5_000_000, 500_000, late_cost_bp=200),     # earlier due, cheaper
               Obligation("card", "high", date(2026, 11, 25), 5_000_000, 500_000, late_cost_bp=300)]
        p = build_plan(date(2026, 10, 30), 7_000_000, obs)
        self.assertEqual(amounts_of(p, "high"), [500_000, 4_500_000])                                  # paid in full first
        self.assertEqual(amounts_of(p, "low"), [500_000, 1_500_000])                                   # 7 - 1.0 mins - 4.5 = 1.5M left
        self.assertEqual((p.unfunded[0].to_alias, p.unfunded[0].amount), ("low", 3_000_000))
        self.assertEqual(p.unfunded[0].est_delay_cost, 3_000_000 * 200 // 10_000)                      # 60,000


def amounts_of(plan, alias):
    return [t.amount for t in plan.transfers if t.to_alias == alias]


class Advice(unittest.TestCase):
    def test_pay_one_card_in_full_partly_pay_the_other_with_cost_and_option_a(self):
        conn = world()
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertEqual(amounts(snap, "bca-1"), [800_000, 7_200_000])        # highest rate: cleared completely
        self.assertEqual(amounts(snap, "cimb-1"), [600_000, 4_400_000])       # reserve stops it at 5.0M of 6.0M
        self.assertEqual(snap["cash_to_hold"], 3_000_000)
        text = "\n".join(snap["advice"])
        self.assertIn("bca-1: LUNASI Rp 8.000.000. Tidak ada bunga.", text)
        self.assertIn("cimb-1: bayar sebagian Rp 5.000.000 dari Rp 6.000.000 (minimum Rp 600.000). "
                      "Sisa Rp 1.000.000 berbunga sekitar Rp 22.500 bulan depan (2.25%/bulan).", text)
        self.assertIn("Opsi A: kurangi cadangan harian Rp 1.000.000 untuk melunasi lebih banyak (hemat bunga sekitar Rp 22.500)", text)
        self.assertIn("total bunga kartu bulan depan sekitar Rp 22.500", text)
        self.assertNotIn("Opsi B", text)                                       # no pot in this world
        self.assertIn("> bca-1: LUNASI", tools.summarize_plan(snap))

    def test_everything_paid_in_full_when_cash_allows(self):
        conn = world(salary=30_000_000)
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertTrue(all("LUNASI" in a for a in snap["advice"]), snap["advice"])
        self.assertEqual(snap["unfunded"], [])
        self.assertEqual(snap["cash_to_hold"], 30_000_000 - 1_400_000 - 4_000_000 - 12_600_000)       # 12.0M incl. reserve
        self.assertNotIn("Opsi", " ".join(snap["advice"]))

    def test_option_b_postponing_pot_deposit_shows_the_effect_on_next_months_deposit(self):
        conn = world(salary=17_000_000, fixed=0)
        v = PayeeVault(conn, bytes(range(32)))
        v.store("pot-rek", "account", "Jago", "106879418405")
        conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('pot','Jago','pool')")
        conn.commit()
        tools.upsert_sinking_fund(conn, "hutang-teman", 135_000_000, "2028-01-31", "pot", "pot-rek", today=TODAY)
        conn.execute("DELETE FROM statements WHERE card_id=2")                  # only card A: total 8M, min 0.8M, 2.75%
        conn.commit()
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertEqual(amounts(snap, "hutang-teman"), [9_000_000])
        self.assertEqual(amounts(snap, "bca-1"), [800_000, 4_200_000])          # 17 - 0.8 - 9 = 7.2; minus reserve 3 = 4.2
        text = "\n".join(snap["advice"])
        self.assertIn("Sisa Rp 3.000.000 berbunga sekitar Rp 82.500", text)
        self.assertIn("Opsi B: tunda Rp 3.000.000 dari setoran pot hutang-teman", text)
        self.assertIn("(hemat bunga sekitar Rp 82.500)", text)
        self.assertIn("setoran bulan depan naik dari Rp 9.000.000 menjadi Rp 9.215.000", text)

    def test_savings_target_ranks_below_card_interest(self):
        conn = world(salary=20_000_000)
        tools.set_threshold(conn, "monthly_savings_target", 1_000_000)
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertEqual(amounts(snap, "tabungan"), [])                         # cards still unpaid: no savings
        self.assertIn("Tabungan: Rp 0 dari target Rp 1.000.000. Target belum tercapai bulan ini.", "\n".join(snap["advice"]))
        rich = world(salary=30_000_000)
        tools.set_threshold(rich, "monthly_savings_target", 1_000_000)
        snap = tools.generate_payday_plan(rich, TODAY)
        self.assertEqual(amounts(snap, "tabungan"), [1_000_000])
        self.assertIn("Tabungan: Rp 1.000.000 dari target Rp 1.000.000.", "\n".join(snap["advice"]))

    def test_missing_reserve_is_called_out_when_cards_exist(self):
        conn = world(reserve=None)
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertEqual(snap["reserve_source"], "belum diset")
        self.assertTrue(any("Cadangan hidup harian belum diset" in w for w in snap["warnings"]))
        self.assertTrue(all("LUNASI" in a for a in snap["advice"]))              # 20 - 1.4 - 4 = 14.6M covers 12.6M

    def test_card_rate_validation_and_it_is_kept_when_omitted(self):
        conn = connect(":memory:")
        for bad in (-1, 1001):
            with self.assertRaises(ValueError):
                tools.upsert_card(conn, "x-1", "BCA", "1111", 5, 20, 1_000_000, interest_bp_month=bad)
        tools.upsert_card(conn, "x-1", "BCA", "1111", 5, 20, 1_000_000, interest_bp_month=275)
        tools.upsert_card(conn, "x-1", "BCA", "1111", 5, 20, 2_000_000)
        self.assertEqual(conn.execute("SELECT interest_bp_month FROM cards").fetchone()[0], 275)

    def test_unpaid_delay_cost_uses_each_cards_own_rate(self):
        conn = world(salary=6_000_000, reserve=0, fixed=0)       # 6M: both minimums (1.4M) + 4.6M toward A's 7.2M rest
        snap = tools.generate_payday_plan(conn, TODAY)
        costs = {u["to_alias"]: u["est_delay_cost"] for u in snap["unfunded"]}
        self.assertEqual(costs["bca-1"], (7_200_000 - 4_600_000) * 275 // 10_000)          # 2.6M at 2.75%
        self.assertEqual(costs["cimb-1"], 5_400_000 * 225 // 10_000)                       # 5.4M at default 2.25%


class DueBeforePayday(unittest.TestCase):
    def test_bill_due_before_the_salary_is_flagged_first_with_the_minimum(self):
        conn = world(fixed=0)
        conn.execute("UPDATE statements SET due_date='2026-10-28' WHERE card_id=1")          # due tomorrow; payday is 2026-10-30
        conn.commit()
        snap = tools.generate_payday_plan(conn, TODAY)
        first = snap["reminders"][0]
        self.assertTrue(first.startswith("MENDESAK: tagihan bca-1 jatuh tempo 2026-10-28, sebelum gajian 2026-10-30."), first)
        self.assertIn("Bayar minimal Rp 800.000 (penuh Rp 8.000.000) dari saldo yang ada sekarang agar tidak kena denda", first)
        self.assertNotIn("cimb-1", first)                                                      # B is due 2026-11-05, after payday
        self.assertIn("MENDESAK", tools.summarize_plan(snap))

    def test_minimum_already_met_is_info_not_urgent(self):
        conn = world(fixed=0)
        conn.execute("UPDATE statements SET due_date='2026-10-28' WHERE card_id=1")
        conn.commit()
        tools.record_card_payment(conn, TODAY, "bca-1", 1_000_000)                          # more than the 800,000 minimum
        first = tools.generate_payday_plan(conn, TODAY)["reminders"][0]
        self.assertTrue(first.startswith("INFO: tagihan bca-1 sudah memenuhi minimum; sisa Rp 7.000.000 jatuh tempo 2026-10-28"), first)
        self.assertNotIn("MENDESAK", first)
        self.assertNotIn("Rp 0", first)

    def test_bill_already_past_due_says_so(self):
        conn = world(fixed=0)
        conn.execute("UPDATE statements SET due_date='2026-10-20' WHERE card_id=1")
        conn.commit()
        self.assertTrue(tools.generate_payday_plan(conn, TODAY)["reminders"][0].startswith("SUDAH LEWAT: tagihan bca-1"))

    def test_no_reminder_when_every_bill_is_due_after_payday(self):
        snap = tools.generate_payday_plan(world(), TODAY)
        self.assertFalse(any("MENDESAK" in r or "SUDAH LEWAT" in r for r in snap["reminders"]))

    def test_only_the_minimum_when_minimum_equals_total(self):
        conn = world(fixed=0)
        conn.execute("UPDATE statements SET due_date='2026-10-28', total_due=800000, minimum_due=800000 WHERE card_id=1")
        conn.commit()
        r = tools.generate_payday_plan(conn, TODAY)["reminders"][0]
        self.assertTrue(r.endswith("dari saldo yang ada sekarang."), r)


class LivingReserveEstimate(unittest.TestCase):
    def tx(self, conn, month, category, amount, status="verified"):
        conn.execute("INSERT INTO transactions(txn_date,merchant,amount,category,status,source) VALUES (?,?,?,?,?,'mutation')",
                     (f"{month}-10", "X", amount, category, status))
        conn.commit()

    def test_median_of_tidy_months_only(self):
        conn = connect(":memory:")
        self.tx(conn, "2026-06", "makan", -1_000_000)                          # June: 90% of its money out is uncategorized -> skipped
        self.tx(conn, "2026-06", None, -9_000_000, status="unverified")
        self.tx(conn, "2026-08", "makan", -2_000_000)
        self.tx(conn, "2026-09", "makan", -2_700_000)
        self.tx(conn, "2026-09", "transport", -300_000)
        self.tx(conn, "2026-09", "wajib:sekolah", -6_000_000)                  # obligation: excluded, but it IS categorized
        self.tx(conn, "2026-09", "transfer_internal", -5_000_000)              # own transfer: excluded
        self.tx(conn, "2026-10", "makan", -9_999_000)                          # the current month is not history
        self.assertEqual(hl.estimate_living_reserve(conn, date(2026, 10, 30)), 2_500_000)    # median of Aug 2.0M and Sep 3.0M

    def test_one_tidy_month_or_untidy_months_give_no_estimate(self):
        conn = connect(":memory:")
        self.tx(conn, "2026-09", "makan", -4_000_000)
        self.assertEqual(hl.estimate_living_reserve(conn, date(2026, 10, 30)), 0)          # one month is not a pattern
        self.tx(conn, "2026-08", "makan", -1_000_000)
        self.tx(conn, "2026-08", None, -9_000_000, status="unverified")                    # Aug is only 10% categorized
        self.assertEqual(hl.estimate_living_reserve(conn, date(2026, 10, 30)), 0)

    def test_capped_at_sixty_percent_of_salary_and_zero_without_history(self):
        conn = connect(":memory:")
        self.assertEqual(hl.estimate_living_reserve(conn, date(2026, 10, 30)), 0)
        self.tx(conn, "2026-08", "makan", -5_000_000)
        self.tx(conn, "2026-09", "makan", -5_000_000)
        self.assertEqual(hl.estimate_living_reserve(conn, date(2026, 10, 30), salary=3_000_000), 1_800_000)

    def test_used_by_the_plan_when_not_set_and_labelled(self):
        conn = world(reserve=None)
        self.tx(conn, "2026-08", "makan", -2_500_000)
        self.tx(conn, "2026-09", "makan", -2_500_000)
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertEqual((snap["reserve"], snap["reserve_source"]), (2_500_000, "estimasi dari transaksi yang sudah diverifikasi"))
        self.assertIn("Cadangan hidup harian: Rp 2.500.000 (estimasi", tools.summarize_plan(snap))

    def test_a_leftover_counts_for_its_own_payday_only(self):
        conn = world(reserve=3_000_000)
        tools.set_leftover_living_cash(conn, 2_000_000, date(2026, 10, 28))        # belongs to the Oct 30 payday
        self.assertEqual(tools.reserve_for(conn, date(2026, 10, 30))[0], 1_000_000)
        self.assertIn("sementara", tools.reserve_for(conn, date(2026, 10, 30))[1])
        self.assertEqual(tools.reserve_for(conn, date(2026, 11, 30)), (3_000_000, "diset pemilik"))     # back to normal by itself
        self.assertEqual(tools.reserve_for(conn, date(2026, 9, 30)), (3_000_000, "diset pemilik"))      # nor an earlier one
        self.assertEqual(tools.reserve_for(world(reserve=3_000_000), date(2026, 10, 30)), (3_000_000, "diset pemilik"))
        tools.set_leftover_living_cash(conn, 0, date(2026, 10, 28))                 # nothing left: the full amount, no note
        self.assertEqual(tools.reserve_for(conn, date(2026, 10, 30)), (3_000_000, "diset pemilik"))

    def test_untidy_history_never_drives_the_plan(self):
        """Regression: a Rp 13M reserve estimated from half-categorized months made the plan pay only a card minimum."""
        conn = world(reserve=None)
        for m, cash, unknown in (("2026-07", 17_000_000, 27_000_000), ("2026-08", 4_000_000, 60_000_000), ("2026-09", 18_000_000, 45_000_000)):
            self.tx(conn, m, "makan", -cash)
            self.tx(conn, m, None, -unknown, status="unverified")
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertEqual((snap["reserve"], snap["reserve_source"]), (0, "belum diset"))
        self.assertTrue(all("LUNASI" in a for a in snap["advice"]), snap["advice"])          # cards paid in full, not "only the minimum"
        self.assertTrue(any("Cadangan hidup harian belum diset" in w for w in snap["warnings"]))


try:
    import asyncio
    from starlette.testclient import TestClient
    from vault_tools.server import create_app
    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class Rincian(unittest.TestCase):
    def test_savings_line_has_no_number_to_copy(self):
        with tempfile.TemporaryDirectory() as d:
            app = create_app(os.path.join(d, "l.db"), bytes(range(32)), "m" * 40, "i" * 40, allowed_hosts=["testserver"],
                             today=lambda: TODAY, ingest_dir=d, passwords_path=None)
            call = lambda n, a=None: asyncio.run(app.state.mcp.call_tool(n, a or {}))  # noqa: E731
            call("set_threshold", {"key": "net_salary", "value": 10_000_000})
            call("set_threshold", {"key": "monthly_savings_target", "value": 1_000_000})
            call("generate_payday_plan", {})
            with TestClient(app) as c:
                text = c.post("/internal/rincian", json={}, headers={"Authorization": "Bearer " + "i" * 40}).text
            self.assertIn("Sisihkan ke tabungan sendiri", text)
            self.assertNotIn("`", text)


if __name__ == "__main__":
    unittest.main()
