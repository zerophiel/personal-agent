"""Property tests: hundreds of random ledgers (salary, bills, loans, cards, subscriptions, instalments, pots of both patterns,
emergency fund, random days) must never produce a plan or a simulation that breaks its own arithmetic. The self-checks in
`invariants` run inside generate_payday_plan and simulate, so a violation raises CalculationError and fails the test."""
import copy
import os
import random
import sys
import unittest
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import card_installments as ci  # noqa: E402
from vault_tools import invariants, simulate, subscriptions, tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402
from vault_tools.payee_vault import PayeeVault  # noqa: E402

CASES = 200


def rupiah(rng, lo, hi):
    return rng.randrange(lo, hi)            # any whole rupiah, not only round numbers


def random_world(rng):
    today = date(2026, 10, 1) + timedelta(days=rng.randrange(0, 180))
    conn = connect(":memory:")
    PayeeVault(conn, bytes(range(32))).store("pot-rek", "account", "Jago", "106879418405")
    conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('pot','Jago','pool')")
    conn.execute("INSERT INTO accounts(alias,bank,kind) VALUES ('main','Mandiri','main')")
    conn.commit()
    tools.set_threshold(conn, "net_salary", rupiah(rng, 3_000_000, 80_000_000))
    if rng.random() < 0.9:
        tools.set_threshold(conn, "living_reserve", rupiah(rng, 0, 12_000_000))
    if rng.random() < 0.3:
        tools.set_leftover_living_cash(conn, rupiah(rng, 0, 9_000_000), today) if tools.get_threshold(conn, "living_reserve") else None
    for i in range(rng.randint(0, 4)):
        tools.upsert_expense(conn, f"fx{i}", f"fx{i}-va", rupiah(rng, 50_000, 6_000_000), rng.randint(1, 31))
    for i in range(rng.randint(0, 2)):
        inst, n = rupiah(rng, 100_000, 7_000_000), rng.randint(1, 30)
        tools.upsert_debt(conn, f"loan{i}", "X", inst * n, inst, n, rng.randint(1, 28), rng.choice([None, 815]),
                          pay_method="autodebit", debit_account_alias="main")
    for i, bank in enumerate(rng.sample(["BCA", "CIMB", "HSBC", "Mega", "DBS"], rng.randint(0, 5))):
        tools.upsert_card(conn, f"c{i}", bank, f"{1000 + i}", rng.randint(1, 28), rng.randint(1, 28), 50_000_000,
                          interest_bp_month=rng.choice([None, 95, 175, 225, 275]))
        total = rupiah(rng, 0, 30_000_000)
        minimum = rng.randrange(0, total // 4 + 1)
        stmt = today - timedelta(days=rng.randrange(0, 40))
        due = stmt + timedelta(days=rng.randrange(10, 25))
        conn.execute("INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,fees,total_due,"
                     "minimum_due,reconciled,recon_diff,ingested_at,paid_amount) VALUES (?,?,?,?,0,0,?,0,?,?,1,0,'t',?)",
                     (i + 1, f"{i}".ljust(64, "x"), stmt.isoformat(), due.isoformat(), total, total, minimum,
                      rng.choice([0, 0, 0, rng.randrange(0, total + 1)])))
        conn.commit()
        if rng.random() < 0.5:
            seq = rng.randint(1, 11)
            ci.record(conn, f"c{i}", stmt.isoformat(), [{"description": f"cicilan {i}", "amount": rupiah(rng, 50_000, 3_000_000),
                                                         "seq": seq, "total": rng.randint(seq + 1, 24)}])
    for i in range(rng.randint(0, 5)):
        ends = rng.choice([None, f"{rng.randint(2026, 2029)}-{rng.randint(1, 12):02d}"])
        subscriptions.upsert(conn, f"sub{i}", f"Sub {i}", rupiah(rng, 10_000, 2_000_000), "c0", ends=ends,
                             essential=rng.random() < 0.3)
    if rng.random() < 0.8:
        due = today + timedelta(days=rng.randrange(40, 900))
        tools.upsert_sinking_fund(conn, "pot1", rupiah(rng, 5_000_000, 200_000_000), due.isoformat(), "pot", "pot-rek",
                                  saved_so_far=rng.choice([0, rupiah(rng, 0, 50_000_000)]), today=today)
        pace = rng.choice(["rata", "sisa", "low"])
        if pace == "sisa":
            tools.set_pot_schedule(conn, "pot1", None, None, today, pace="sisa", due_payday=rng.random() < 0.5)
        elif pace == "low":
            try:
                until = today + timedelta(days=rng.randrange(31, 300))
                tools.set_pot_schedule(conn, "pot1", rupiah(rng, 0, 5_000_000), until.strftime("%Y-%m"), today)
            except ValueError:
                pass                               # a low phase longer than the horizon is refused by design
    if rng.random() < 0.6:
        tools.set_threshold(conn, "emergency_target", rupiah(rng, 500_000, 6_000_000))
        tools.set_threshold(conn, "emergency_monthly", rupiah(rng, 100_000, 1_000_000))
        if rng.random() < 0.5:
            tools.set_emergency_balance(conn, rupiah(rng, 0, 7_000_000))
    return conn, today


class RandomLedgers(unittest.TestCase):
    def test_no_plan_or_simulation_ever_breaks_its_own_arithmetic(self):
        rng = random.Random(20261028)
        for case in range(CASES):
            conn, today = random_world(rng)
            with self.subTest(case=case, today=today.isoformat()):
                tools.generate_payday_plan(conn, today)                                   # raises CalculationError on a violation
                simulate.simulate(conn, today, months=rng.randint(1, 36), belanja_kartu=rng.choice([0, rupiah(rng, 0, 5_000_000)]),
                                  hemat=rng.choice([0, rupiah(rng, 0, 3_000_000)]), ekstra_sekarang=rng.choice([0, rupiah(rng, 0, 20_000_000)]),
                                  pola_pot=rng.choice([None, "rata", "sisa"]), gaji_hari_tenggat=rng.choice([None, True, False]))


class TheChecksCatchBrokenNumbers(unittest.TestCase):
    """The checks are not vacuous: each kind of broken number is caught."""
    def snap(self):
        return {"salary": 10_000_000, "cash_to_hold": 3_000_000, "reserve": 3_000_000, "unfunded": [],
                "transfers": [{"to_alias": "kartu", "amount": 5_000_000, "reason": "tagihan kartu - minimum"},
                              {"to_alias": "pot", "amount": 2_000_000, "reason": "setoran pot (sisa setelah kartu)"}]}

    def test_plan(self):
        self.assertEqual(invariants.plan_errors(self.snap(), {"kartu": 5_000_000}), [])
        bad = copy.deepcopy(self.snap())
        bad["transfers"][1]["amount"] = 2_000_001                                         # one rupiah too many
        self.assertTrue(invariants.plan_errors(bad))
        bad = copy.deepcopy(self.snap())
        bad["cash_to_hold"], bad["transfers"][1]["amount"] = 2_000_000, 3_000_000         # the pot ate the living money
        self.assertTrue(any("uang harian terpotong" in e for e in invariants.plan_errors(bad)))
        self.assertTrue(any("melebihi tagihan" in e for e in invariants.plan_errors(self.snap(), {"kartu": 4_000_000})))
        bad = copy.deepcopy(self.snap())
        bad["transfers"][0]["amount"] = 5_000_000.0                                       # floats are never money
        self.assertTrue(invariants.plan_errors(bad))
        with self.assertRaises(invariants.CalculationError):
            invariants.require(["x"], "uji")

    def test_simulation(self):
        conn, today = random_world(random.Random(7))
        r = simulate.simulate(conn, today, months=6)
        self.assertEqual(invariants.simulation_errors(r), [])
        bad = copy.deepcopy(r)
        bad["rows"][0]["paid"] += 1                                                       # a payment that never happened
        self.assertTrue(invariants.simulation_errors(bad))
        bad = copy.deepcopy(r)
        bad["rows"][-1]["balance"] += 1                                                   # the card books do not balance
        self.assertTrue(any("tidak seimbang" in e for e in invariants.simulation_errors(bad)))


if __name__ == "__main__":
    unittest.main()
