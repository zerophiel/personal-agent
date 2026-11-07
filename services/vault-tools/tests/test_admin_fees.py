"""The bank's admin fees (usulan #4, 31 Oct 2026): every payment from the salary account costs a fee the plans did not count
(Rp 7.500 per card payment, Rp 6.500 per other transfer), so the account ran short of what the plan said. The plan pays each
fee with its payment, once per destination, keeps the living money's fee with the reserve, and counts fees from the payday
biaya_admin_mulai, so a plan already carried out keeps its numbers."""
import json
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import invariants, notion_sync, reports, rincian, simulate, tools  # noqa: E402
from vault_tools.payday import Fee, Obligation, build_plan  # noqa: E402
from vault_tools.payee_vault import PayeeVault  # noqa: E402

from test_payday_progress import KEY, PAYDAY, world  # noqa: E402

NOV_30 = date(2026, 11, 30)
# world() at PAYDAY with the owner's fees and DBS paid to its card number: what the plan must say, worked out by hand
EXPECTED_FEES = [
    {"date": "2026-11-04", "to_alias": "cimb-1", "amount": 6_500, "kind": "transfer"},
    {"date": "2026-11-07", "to_alias": "dbs-1", "amount": 7_500, "kind": "kartu"},
    {"date": "2026-11-10", "to_alias": "jenius-1", "amount": 6_500, "kind": "transfer"},
    {"date": "2026-10-30", "to_alias": "sekolah-va", "amount": 6_500, "kind": "transfer"},
    {"date": "2026-10-30", "to_alias": "uang-harian", "amount": 6_500, "kind": "transfer"},
]


def fees_world():
    conn = world()
    PayeeVault(conn, KEY).store("num-5685", "card", "DBS", "4" * 16)
    tools.upsert_card(conn, "dbs-1", "DBS", "5685", 25, 10, 20_000_000, pay_to_alias="num-5685", interest_bp_month=175)
    tools.set_threshold(conn, "biaya_admin_kartu", 7_500)
    tools.set_threshold(conn, "biaya_admin_transfer", 6_500)
    return conn


def bills_of(conn, payday):
    """The bills the plan of `payday` covers, as generate_payday_plan hands them to the invariants."""
    hol = tools.id_holidays(payday.year) | tools.id_holidays(payday.year + 1)
    plan, obs, _ = tools.payday_plan(conn, payday, hol)
    out = {}
    for o in obs:
        if o.kind != "pool_rest" and o.due < plan.next_payday:
            out[o.payee_alias] = out.get(o.payee_alias, 0) + o.amount
    return out


def fixed(alias, due, amount, fee, pay_to=None):
    return Obligation("fixed", alias, due, amount, pay_to=pay_to or alias, fee=fee)


class BuildPlan(unittest.TestCase):
    def test_the_fee_is_paid_with_its_payment(self):
        p = build_plan(PAYDAY, 1_000_000, [fixed("ipl", date(2026, 11, 5), 300_000, 6_500)])
        self.assertEqual([t.amount for t in p.transfers], [300_000])
        self.assertEqual(p.fees, (Fee(date(2026, 11, 2), "ipl", 6_500, "transfer"),))
        self.assertEqual(p.cash_to_hold, 693_500)

    def test_a_cards_minimum_and_rest_share_one_fee(self):
        card = Obligation("card", "dbs", date(2026, 11, 10), 1_000_000, 100_000, pay_to="num", fee=7_500, fee_kind="kartu")
        p = build_plan(PAYDAY, 2_000_000, [card])
        self.assertEqual([t.amount for t in p.transfers], [100_000, 900_000])
        self.assertEqual([(f.to_alias, f.amount, f.kind) for f in p.fees], [("dbs", 7_500, "kartu")])
        self.assertEqual(p.cash_to_hold, 992_500)

    def test_one_fee_per_destination(self):
        p = build_plan(PAYDAY, 5_000_000, [fixed("les-a", date(2026, 11, 5), 600_000, 6_500, "rek-les"),
                                           fixed("les-b", date(2026, 11, 5), 400_000, 6_500, "rek-les")])
        self.assertEqual(len(p.fees), 1)
        self.assertEqual(p.cash_to_hold, 5_000_000 - 1_000_000 - 6_500)

    def test_short_money_pays_the_fee_first(self):
        p = build_plan(PAYDAY, 100_000, [fixed("ipl", date(2026, 11, 5), 200_000, 6_500)])
        self.assertEqual([t.amount for t in p.transfers], [93_500])
        self.assertEqual(sum(f.amount for f in p.fees), 6_500)
        self.assertEqual(p.cash_to_hold, 0)
        self.assertEqual(p.unfunded[0].amount, 106_500)

    def test_nothing_paid_costs_no_fee(self):
        p = build_plan(PAYDAY, 5_000, [fixed("ipl", date(2026, 11, 5), 200_000, 6_500)])
        self.assertEqual((p.transfers, p.fees, p.cash_to_hold), ((), (), 5_000))

    def test_the_living_fee_is_kept_with_the_reserve(self):
        rest = Obligation("card", "dbs", date(2026, 11, 10), 4_000_000, 0, pay_to="num", fee=7_500, fee_kind="kartu")
        p = build_plan(PAYDAY, 5_000_000, [rest], reserve=3_000_000, reserve_fee=6_500, reserve_to="uang-harian")
        self.assertEqual(p.cash_to_hold, 3_000_000)          # the whole living money: the fee of moving it is kept on top
        self.assertEqual([t.amount for t in p.transfers], [1_986_000])
        self.assertEqual([(f.to_alias, f.amount) for f in p.fees], [("dbs", 7_500), ("uang-harian", 6_500)])

    def test_no_living_fee_without_money_to_move(self):
        p = build_plan(PAYDAY, 5_000, [], reserve=3_000_000, reserve_fee=6_500)
        self.assertEqual((p.fees, p.cash_to_hold), ((), 5_000))

    def test_bad_fees_are_refused(self):
        with self.assertRaises(ValueError):
            fixed("ipl", PAYDAY, 1, -1)
        with self.assertRaises(TypeError):
            fixed("ipl", PAYDAY, 1, 6_500.0)
        with self.assertRaises(ValueError):
            Obligation("fixed", "ipl", PAYDAY, 1, fee_kind="admin")
        with self.assertRaises(ValueError):
            build_plan(PAYDAY, 1, [], reserve=1, reserve_fee=-1)


class Rule(unittest.TestCase):
    def test_kind_and_method(self):
        conn = fees_world()
        self.assertEqual(tools.admin_fee(conn, "dbs-1", "transfer", "num-5685"), (7_500, "kartu"))
        self.assertEqual(tools.admin_fee(conn, "cimb-1", "transfer", None), (6_500, "transfer"))
        self.assertEqual(tools.admin_fee(conn, "sekolah-va", "transfer", "sekolah-va"), (6_500, "transfer"))
        self.assertEqual(tools.admin_fee(conn, "mandiri-4365", "app_menu", "num-5685"), (0, "kartu"))     # the bank's own menu
        self.assertEqual(tools.admin_fee(conn, "cicilan-mobil", "autodebit", "mandiri-utama"), (0, "transfer"))

    def test_one_items_own_fee_wins(self):
        conn = fees_world()
        tools.set_threshold(conn, "biaya_admin:sekolah-va", 0)      # e.g. a VA the bank charges nothing for
        tools.set_threshold(conn, "biaya_admin:dbs-1", 2_500)
        self.assertEqual(tools.admin_fee(conn, "sekolah-va", "transfer", "sekolah-va"), (0, "transfer"))
        self.assertEqual(tools.admin_fee(conn, "dbs-1", "transfer", "num-5685"), (2_500, "kartu"))
        fees = {f["to_alias"]: f["amount"] for f in tools.generate_payday_plan(conn, PAYDAY)["fees"]}
        self.assertNotIn("sekolah-va", fees)
        self.assertEqual(fees["dbs-1"], 2_500)

    def test_none_set_none_counted(self):
        conn = world()
        self.assertEqual(tools.admin_fee(conn, "cimb-1", "transfer", None), (0, "transfer"))
        snap = tools.generate_payday_plan(conn, PAYDAY)
        self.assertNotIn("fees", snap)
        self.assertEqual(snap["cash_to_hold"], 3_000_000)

    def test_threshold_bounds(self):
        conn = world()
        with self.assertRaises(ValueError):
            tools.set_threshold(conn, "biaya_admin_kartu", 100_001)
        with self.assertRaises(ValueError):
            tools.set_threshold(conn, "biaya_admin:dbs-1", -1)
        with self.assertRaises(ValueError):
            tools.set_threshold(conn, "biaya_admin_mulai", 20261131)
        self.assertEqual(tools.set_threshold(conn, "biaya_admin_mulai", 20261130), "biaya_admin_mulai = 20261130")


class Plan(unittest.TestCase):
    def setUp(self):
        self.conn = fees_world()
        self.snap = tools.generate_payday_plan(self.conn, PAYDAY)

    def test_the_numbers(self):
        s = self.snap
        self.assertEqual(s["fees"], EXPECTED_FEES)
        amounts = {}
        for t in s["transfers"]:
            amounts[t["to_alias"]] = amounts.get(t["to_alias"], 0) + t["amount"]
        self.assertEqual(amounts["dbs-1"], 500_000 + 6_466_500)          # 6.500.000 without fees: 33.500 less
        self.assertEqual(amounts["cimb-1"], 200_000)
        self.assertNotIn("hutang-teman", amounts)
        self.assertEqual(s["cash_to_hold"], 3_000_000)
        self.assertEqual(sum(amounts.values()), 16_966_500)
        self.assertEqual(sum(amounts.values()) + 33_500 + s["cash_to_hold"], s["salary"])
        self.assertEqual(s["living_transfer"]["amount"], 3_000_000)
        snap = {k: v for k, v in s.items() if k != "progress"}
        self.assertEqual(invariants.plan_errors(snap, bills_of(self.conn, PAYDAY)), [])

    def test_each_item_carries_its_fee(self):
        fee = {it["to"]: it["fee"] for it in self.snap["progress"]["items"]}
        self.assertEqual(fee, {"cimb-1": 6_500, "dbs-1": 7_500, "jenius-1": 6_500, "sekolah-va": 6_500, "uang-harian": 6_500,
                               "spaylater": 0, "cicilan-mobil": 0})

    def test_the_code_adds_them_up(self):
        line = "BIAYA ADMIN perkiraan Rp 33.500 (1× bayar kartu Rp 7.500; 4× transfer Rp 26.000)"
        self.assertIn(line, tools.summarize_plan(self.snap))
        self.assertIn("BIAYA ADMIN perkiraan untuk yang belum: Rp 33.500", tools.payday_status(self.conn, PAYDAY))
        tools.record_card_payment(self.conn, PAYDAY, "jenius-1", 6_000_000)
        self.assertIn("BIAYA ADMIN perkiraan untuk yang belum: Rp 27.000", tools.payday_status(self.conn, PAYDAY))

    def test_a_balance_counts_the_fees_still_to_go(self):
        out = tools.record_account_balance(self.conn, PAYDAY, "mandiri-utama", 25_000_000)
        self.assertIn("ditambah biaya admin perkiraan Rp 33.500", out)
        # 25.000.000 - auto-debits 1.800.000 - transfers 18.166.500 (the living money's 3.000.000 among them) - fees 33.500
        self.assertIn("sesudahnya yang bisa dipakai Rp 5.000.000", out)

    def test_reports(self):
        text = rincian.build(self.conn, PayeeVault(self.conn, KEY), self.snap)
        self.assertIn("_Biaya admin bank perkiraan Rp 33.500, dipotong per transfer di luar total ini_", text)
        tools.record_card_payment(self.conn, PAYDAY, "jenius-1", 6_000_000)
        snap = tools.generate_payday_plan(self.conn, PAYDAY)
        self.assertIn("perkiraan Rp 33.500, dipotong per transfer di luar total ini; untuk yang belum Rp 27.000_",
                      rincian.build(self.conn, PayeeVault(self.conn, KEY), snap))
        self.assertIn("Biaya admin bank (perkiraan)</b>: <b>Rp 33.500</b>", reports._rencana(self.conn, PAYDAY))
        blocks = json.dumps(notion_sync.render_plan(self.conn, PAYDAY)[1], ensure_ascii=False)
        self.assertIn("Biaya admin bank (perkiraan) Rp 33.500: 1× bayar kartu Rp 7.500; 4× transfer Rp 26.000", blocks)


class Gate(unittest.TestCase):
    def test_a_plan_made_before_keeps_its_numbers(self):
        conn = fees_world()
        tools.set_threshold(conn, "biaya_admin_mulai", 20261130)
        rows = lambda: conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]  # noqa: E731
        conn.execute("DELETE FROM thresholds WHERE key IN ('biaya_admin_kartu', 'biaya_admin_transfer')")
        before = tools.generate_payday_plan(conn, PAYDAY)
        n = rows()
        tools.set_threshold(conn, "biaya_admin_kartu", 7_500)
        tools.set_threshold(conn, "biaya_admin_transfer", 6_500)
        after = tools.generate_payday_plan(conn, PAYDAY)
        self.assertEqual(rows(), n)                          # the same snapshot, byte for byte: no new plan row
        self.assertNotIn("fees", after)
        self.assertEqual(after["transfers"], before["transfers"])
        self.assertEqual(after["cash_to_hold"], 3_000_000)
        self.assertFalse(tools.fees_on(conn, PAYDAY))
        self.assertTrue(tools.fees_on(conn, NOV_30))

    def test_the_next_plan_has_them(self):
        conn = fees_world()
        tools.set_threshold(conn, "biaya_admin_mulai", 20261130)
        snap = tools.generate_payday_plan(conn, NOV_30)
        fees = {f["to_alias"]: f["amount"] for f in snap["fees"]}
        self.assertEqual((fees["sekolah-va"], fees["uang-harian"]), (6_500, 6_500))
        paid = sum(t["amount"] for t in snap["transfers"])
        self.assertEqual(paid + sum(fees.values()) + snap["cash_to_hold"], snap["salary"])


class Invariants(unittest.TestCase):
    def setUp(self):
        self.conn = fees_world()
        snap = tools.generate_payday_plan(self.conn, PAYDAY)
        self.snap = {k: v for k, v in snap.items() if k != "progress"}
        self.bills = bills_of(self.conn, PAYDAY)

    def errors(self, change):
        snap = json.loads(json.dumps(self.snap))
        change(snap)
        return " | ".join(invariants.plan_errors(snap, self.bills))

    def test_a_fee_without_its_payment(self):
        def change(s):
            s["fees"].append({"date": "2026-10-30", "to_alias": "lain", "amount": 6_500, "kind": "transfer"})
            s["cash_to_hold"] -= 6_500
        self.assertIn("biaya admin lain tanpa transfer", self.errors(change))

    def test_a_fee_twice(self):
        def change(s):
            s["fees"].append(dict(s["fees"][0]))
            s["cash_to_hold"] -= s["fees"][0]["amount"]
        self.assertIn("biaya admin tercatat dua kali", self.errors(change))

    def test_a_fee_not_counted(self):
        def change(s):
            s["fees"][0]["amount"] += 1_000
        self.assertIn("!= gaji", self.errors(change))

    def test_a_fee_not_whole(self):
        def change(s):
            s["fees"][0]["amount"] = 6_500.5
            s["cash_to_hold"] -= 0.5
        self.assertIn("biaya admin cimb-1 tidak valid", self.errors(change))


class Simulation(unittest.TestCase):
    def test_cycle_one_is_its_plan_later_cycles_the_estimate(self):
        conn = fees_world()
        self.assertEqual(tools.fee_estimate(conn), 40_000)   # school, three cards (DBS by card), the pot, the living money
        rows = simulate.simulate(conn, PAYDAY, months=3)["rows"]
        self.assertEqual([r["fees"] for r in rows], [33_500, 40_000, 40_000])
        plain = simulate.simulate(world(), PAYDAY, months=1)["rows"][0]
        self.assertEqual(plain["cash"] - rows[0]["cash"], 33_500)

    def test_counted_from_the_start_payday(self):
        conn = fees_world()
        tools.set_threshold(conn, "biaya_admin_mulai", 20261130)
        rows = simulate.simulate(conn, PAYDAY, months=2)["rows"]
        self.assertEqual([r["fees"] for r in rows], [0, 40_000])


if __name__ == "__main__":
    unittest.main()
