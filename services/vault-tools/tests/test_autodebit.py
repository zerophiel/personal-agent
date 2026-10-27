import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402
from vault_tools.payee_vault import PayeeVault  # noqa: E402

TODAY = date(2026, 10, 27)


def setup():
    conn = connect(":memory:")
    PayeeVault(conn, bytes(range(32))).store("mtf-va", "va", "MTF", "8808111122223333")
    PayeeVault(conn, bytes(range(32))).store("num-1111", "card", "?", "4111 1111 1111 1111")
    conn.execute("INSERT INTO accounts(alias,bank,kind,last4) VALUES ('mandiri-utama','Mandiri','main','0001')")
    conn.commit()
    tools.set_threshold(conn, "net_salary", 42_000_000)
    return conn


def car(conn, **kw):
    args = dict(alias="cicilan-mobil", lender="MTF", outstanding=114_020_000, installment=5_701_000,
                tenor_left=20, due_day=2, rate_bp=815)
    args.update(kw)
    return tools.upsert_debt(conn, **args)


class Rules(unittest.TestCase):
    def test_autodebit_needs_a_registered_account(self):
        conn = setup()
        with self.assertRaises(ValueError):
            car(conn, pay_method="autodebit")                                     # no account given
        with self.assertRaises(ValueError):
            car(conn, pay_method="autodebit", debit_account_alias="ghost")
        self.assertIn("autodebet dari mandiri-utama",
                      car(conn, pay_method="autodebit", debit_account_alias="mandiri-utama"))

    def test_transfer_payee_must_be_account_or_va_and_bad_method_rejected(self):
        conn = setup()
        with self.assertRaises(ValueError):
            car(conn, pay_method="transfer", pay_to_alias="num-1111")           # a card number is not a payment target
        with self.assertRaises(ValueError):
            car(conn, pay_method="cash")
        self.assertIn("transfer", car(conn, pay_to_alias="mtf-va"))

    def test_update_keeps_stored_payment_setup_and_switching_clears_the_other(self):
        conn = setup()
        car(conn, pay_method="autodebit", debit_account_alias="mandiri-utama")
        car(conn, outstanding=100_000_000)                                        # no payment args: keep autodebit
        r = conn.execute("SELECT * FROM debts").fetchone()
        self.assertEqual((r["pay_method"], r["debit_account_alias"], r["outstanding"]), ("autodebit", "mandiri-utama", 100_000_000))
        car(conn, pay_method="transfer", pay_to_alias="mtf-va")
        r = conn.execute("SELECT * FROM debts").fetchone()
        self.assertEqual((r["pay_method"], r["pay_to_alias"], r["debit_account_alias"]), ("transfer", "mtf-va", None))


class InThePlan(unittest.TestCase):
    def test_autodebit_in_plan_with_reminder_and_no_number(self):
        conn = setup()
        car(conn, pay_method="autodebit", debit_account_alias="mandiri-utama")
        snap = tools.generate_payday_plan(conn, TODAY)
        t = [x for x in snap["transfers"] if x["to_alias"] == "cicilan-mobil"][0]
        self.assertEqual((t["amount"], t["method"], t["pay_to"], t["due"]), (5_701_000, "autodebit", "mandiri-utama", "2026-11-02"))
        self.assertEqual(snap["cash_to_hold"], 42_000_000 - 5_701_000)            # the money is still reserved
        rem = " ".join(snap["reminders"])
        self.assertIn("AUTODEBET cicilan-mobil", rem)
        self.assertIn("mandiri-utama", rem)
        self.assertIn("Rp 5.701.000", rem)
        self.assertIn("2026-11-02", rem)
        text = tools.summarize_plan(snap)
        self.assertIn("autodebet, saldo harus cukup sebelum 2026-11-02", text)
        self.assertNotIn("8808", json.dumps(snap))

    def test_plain_transfer_debt_unchanged(self):
        conn = setup()
        car(conn, pay_to_alias="mtf-va")
        snap = tools.generate_payday_plan(conn, TODAY)
        t = [x for x in snap["transfers"] if x["to_alias"] == "cicilan-mobil"][0]
        self.assertEqual((t["method"], t["pay_to"]), ("transfer", "mtf-va"))
        self.assertFalse(any("AUTODEBET" in r for r in snap["reminders"]))


class Migration(unittest.TestCase):
    def test_v4_ledger_gets_the_debt_columns(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "l.db")
            old = sqlite3.connect(path)
            old.executescript("CREATE TABLE debts (id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, lender TEXT NOT NULL,"
                              " outstanding INTEGER NOT NULL, installment INTEGER NOT NULL, tenor_left INTEGER NOT NULL,"
                              " rate_bp INTEGER, due_day INTEGER NOT NULL);"
                              " INSERT INTO debts VALUES (1,'old','X',1000,100,10,NULL,5);")
            old.commit()
            old.close()
            conn = connect(path)
            self.assertTrue({"pay_method", "pay_to_alias", "debit_account_alias"} <= {r["name"] for r in conn.execute("PRAGMA table_info(debts)")})
            self.assertEqual(conn.execute("SELECT alias, pay_method FROM debts").fetchone()[:], ("old", "transfer"))
            connect(path)                                                          # idempotent


try:
    from starlette.testclient import TestClient
    from vault_tools.server import create_app
    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class Rincian(unittest.TestCase):
    def test_rincian_shows_autodebit_reminder_and_never_a_number(self):
        with tempfile.TemporaryDirectory() as d:
            app = create_app(os.path.join(d, "l.db"), bytes(range(32)), "m" * 40, "i" * 40,
                             allowed_hosts=["testserver"], today=lambda: TODAY, ingest_dir=d, passwords_path=None)
            call = lambda n, a: asyncio.run(app.state.mcp.call_tool(n, a))  # noqa: E731
            call("set_threshold", {"key": "net_salary", "value": 42_000_000})
            call("upsert_account", {"alias": "mandiri-utama", "bank": "Mandiri", "kind": "main"})
            call("upsert_debt", {"alias": "cicilan-mobil", "lender": "MTF", "outstanding": 114_020_000,
                                 "installment": 5_701_000, "tenor_left": 20, "due_day": 2, "rate_bp": 815,
                                 "pay_method": "autodebit", "debit_account_alias": "mandiri-utama"})
            call("generate_payday_plan", {})
            with TestClient(app) as c:
                text = c.post("/internal/rincian", json={}, headers={"Authorization": "Bearer " + "i" * 40}).text
            self.assertIn("AUTODEBET dari rekening MANDIRI (mandiri-utama) pada 2026-11-02", text)
            self.assertIn("Rp 5.701.000", text)
            self.assertNotIn("`", text)                                              # no copyable number at all


if __name__ == "__main__":
    unittest.main()
