import os
import random
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools.masking import luhn_valid, mask_sensitive  # noqa: E402
from vault_tools.money import bp_of, format_idr  # noqa: E402
from vault_tools.payday import Obligation, build_plan, last_working_day, next_payday  # noqa: E402

PAYDAY = date(2026, 10, 30)


def dummy():
    return [
        Obligation("card", "dbs-1111", date(2026, 11, 5), 3_000_000, 300_000, late_cost_bp=300),
        Obligation("fixed", "sekolah-2222", date(2026, 11, 10), 2_000_000),
        Obligation("debt", "pinjaman-3333", date(2026, 11, 2), 1_500_000, late_cost_bp=200),
        Obligation("saving", "tabungan", date(2026, 11, 29), 500_000),
    ]


class PaydayDates(unittest.TestCase):
    def test_weekend_end_of_month_moves_back(self):
        self.assertEqual(date(2026, 10, 31).weekday(), 5)  # Saturday
        self.assertEqual(last_working_day(2026, 10), date(2026, 10, 30))

    def test_holiday_skipped(self):
        self.assertEqual(last_working_day(2026, 10, [date(2026, 10, 30)]), date(2026, 10, 29))

    def test_next_payday_rolls_year(self):
        self.assertEqual(next_payday(date(2026, 12, 31)), last_working_day(2027, 1))

    def test_always_working_day(self):
        for y in (2026, 2027):
            for m in range(1, 13):
                self.assertLess(last_working_day(y, m).weekday(), 5)


class WorkedExample(unittest.TestCase):
    def test_enough_salary(self):
        plan = build_plan(PAYDAY, 10_000_000, dummy())
        self.assertEqual(plan.next_payday, date(2026, 11, 30))
        self.assertEqual([t.amount for t in plan.transfers],
                         [300_000, 2_000_000, 1_500_000, 2_700_000, 500_000])  # min, esensial, cicilan, sisa kartu, tabungan
        self.assertEqual(plan.unfunded, ())
        self.assertEqual(plan.cash_to_hold, 3_000_000)
        self.assertEqual(plan.daily_allowance, 3_000_000 // 31)

    def test_shortfall_explicit(self):
        plan = build_plan(PAYDAY, 3_000_000, dummy())
        funded = {(t.to_alias, t.reason): t.amount for t in plan.transfers}
        self.assertEqual(funded[("dbs-1111", "tagihan kartu - minimum")], 300_000)
        self.assertEqual(funded[("sekolah-2222", "pengeluaran tetap")], 2_000_000)
        self.assertEqual(funded[("pinjaman-3333", "cicilan")], 700_000)
        self.assertEqual(plan.cash_to_hold, 0)
        un = {(u.to_alias, u.reason): u for u in plan.unfunded}
        self.assertEqual(un[("pinjaman-3333", "cicilan")].amount, 800_000)
        self.assertEqual(un[("pinjaman-3333", "cicilan")].est_delay_cost, 16_000)  # 2% of 800k
        self.assertEqual(un[("dbs-1111", "tagihan kartu - sisa saldo (bayar penuh)")].amount, 2_700_000)
        self.assertTrue(plan.warnings)

    def test_overdue_first(self):
        obs = dummy() + [Obligation("debt", "telat-9999", date(2026, 10, 20), 400_000)]
        plan = build_plan(PAYDAY, 10_000_000, obs)
        self.assertEqual(plan.transfers[0].to_alias, "telat-9999")
        self.assertEqual(plan.transfers[0].date, PAYDAY)

    def test_later_window_excluded(self):
        obs = [Obligation("fixed", "x", date(2026, 12, 1), 1_000_000)]
        self.assertEqual(build_plan(PAYDAY, 5_000_000, obs).transfers, ())


class Properties(unittest.TestCase):
    def rand_obs(self, rng):
        obs = []
        for i in range(rng.randint(0, 8)):
            kind = rng.choice(["card", "fixed", "debt", "pool", "saving"])
            amount = rng.randint(0, 5_000_000)
            minimum = rng.randint(0, amount) if kind == "card" else 0
            due = PAYDAY + timedelta(days=rng.randint(-15, 35))
            obs.append(Obligation(kind, f"p{i}", due, amount, minimum,
                                  late_cost_bp=rng.randint(0, 500)))
        return obs

    def test_conservation_and_order(self):
        rng = random.Random(20261027)
        for _ in range(500):
            salary = rng.randint(0, 20_000_000)
            obs = self.rand_obs(rng)
            plan = build_plan(PAYDAY, salary, obs)
            paid = sum(t.amount for t in plan.transfers)
            self.assertEqual(paid + plan.cash_to_hold, salary)
            self.assertGreaterEqual(plan.cash_to_hold, 0)
            self.assertTrue(all(t.amount > 0 for t in plan.transfers))
            self.assertTrue(all(isinstance(t.amount, int) for t in plan.transfers))
            if plan.unfunded:
                self.assertEqual(plan.cash_to_hold, 0)  # nothing left while something unfunded
            self.assertEqual(plan, build_plan(PAYDAY, salary, list(reversed(obs))))  # deterministic

    def test_total_due_equals_funded_plus_unfunded(self):
        rng = random.Random(7)
        for _ in range(300):
            obs = self.rand_obs(rng)
            nxt = next_payday(PAYDAY)
            due_total = sum(o.amount for o in obs if o.due < nxt)
            plan = build_plan(PAYDAY, rng.randint(0, 20_000_000), obs)
            self.assertEqual(sum(t.amount for t in plan.transfers)
                             + sum(u.amount for u in plan.unfunded), due_total)


class Money(unittest.TestCase):
    def test_format(self):
        self.assertEqual(format_idr(1234567), "Rp 1.234.567")
        self.assertEqual(format_idr(0), "Rp 0")
        self.assertEqual(format_idr(-1500), "-Rp 1.500")

    def test_rejects_float_and_bool(self):
        for bad in (1.5, True):
            with self.assertRaises(TypeError):
                format_idr(bad)

    def test_bp_half_up(self):
        self.assertEqual(bp_of(800_000, 200), 16_000)
        self.assertEqual(bp_of(50, 100), 1)  # 0.5 -> 1


class Masking(unittest.TestCase):
    def test_luhn(self):
        self.assertTrue(luhn_valid("4111111111111111"))
        self.assertFalse(luhn_valid("4111111111111112"))

    def test_masks_card_variants(self):
        for raw in ("4111111111111111", "4111 1111 1111 1111", "4111-1111-1111-1111"):
            out = mask_sensitive(f"kartu {raw} jatuh tempo")
            self.assertNotIn("4111 1111", out)
            self.assertNotIn("41111111", out)
            self.assertIn("****1111", out)

    def test_non_luhn_and_short_numbers_untouched(self):
        self.assertEqual(mask_sensitive("ref 4111111111111112"), "ref 4111111111111112")
        self.assertEqual(mask_sensitive("Rp 1234567"), "Rp 1234567")

    def test_extra_pattern(self):
        out = mask_sensitive("VA 8808 1234 5678", [r"8808 \d{4} \d{4}"])
        self.assertNotIn("1234 5678", out)
        self.assertIn("****5678", out)


if __name__ == "__main__":
    unittest.main()
