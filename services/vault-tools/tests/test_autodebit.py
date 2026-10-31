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
        self.assertIn("AUTODEBET dari rekening mandiri-utama: cicilan-mobil Rp 5.701.000 (2026-11-02)", rem)
        self.assertIn("Pastikan saldo minimal Rp 5.701.000 sebelum 2026-11-02", rem)
        text = tools.summarize_plan(snap)
        self.assertIn("autodebet, saldo harus cukup sebelum 2026-11-02", text)
        self.assertNotIn("8808", json.dumps(snap))

    def test_debits_from_one_account_add_up_with_what_the_bank_holds_back(self):
        """Owner 2026-10-28: Mandiri holds Rp 100.000; with SPayLater on the 1st and the car on the 2nd, a balance of only the
        car instalment would let the car debit fail. One figure per account, before the first debit."""
        conn = setup()
        car(conn, pay_method="autodebit", debit_account_alias="mandiri-utama")
        tools.upsert_debt(conn, "spaylater", "Shopee", 5 * 270_000, 270_000, 5, 1, None, pay_method="autodebit",
                          debit_account_alias="mandiri-utama")
        tools.set_threshold(conn, "saldo_ditahan:mandiri-utama", 100_000)
        rem = [r for r in tools.generate_payday_plan(conn, TODAY)["reminders"] if r.startswith("AUTODEBET")]
        self.assertEqual(len(rem), 1)
        self.assertIn("spaylater Rp 270.000 (2026-11-01); cicilan-mobil Rp 5.701.000 (2026-11-02)", rem[0])
        self.assertIn("ditambah saldo minimum yang ditahan bank Rp 100.000", rem[0])
        self.assertIn("Pastikan saldo minimal Rp 6.071.000 sebelum 2026-11-01 dan jangan dipakai sampai 2026-11-02", rem[0])
        self.assertIn("Rp 100.000", tools.data_overview(conn, TODAY))

    def test_plain_transfer_debt_unchanged(self):
        conn = setup()
        car(conn, pay_to_alias="mtf-va")
        snap = tools.generate_payday_plan(conn, TODAY)
        t = [x for x in snap["transfers"] if x["to_alias"] == "cicilan-mobil"][0]
        self.assertEqual((t["method"], t["pay_to"]), ("transfer", "mtf-va"))
        self.assertFalse(any("AUTODEBET" in r for r in snap["reminders"]))


class BalanceCheck(unittest.TestCase):
    """Usulan #1 (2026-10-28): the owner reads the Mandiri balance in the app; code says whether the auto-debits still to
    come (plus what the bank holds back) fit, so the car debit does not fail."""
    def world(self):
        conn = setup()
        car(conn, pay_method="autodebit", debit_account_alias="mandiri-utama")
        tools.upsert_debt(conn, "spaylater", "Shopee", 5 * 270_000, 270_000, 5, 1, None, pay_method="autodebit",
                          debit_account_alias="mandiri-utama")
        tools.set_threshold(conn, "saldo_ditahan:mandiri-utama", 100_000)
        return conn

    def test_enough_to_the_rupiah_and_one_rupiah_short(self):
        conn = self.world()
        ok = tools.record_account_balance(conn, date(2026, 10, 30), "mandiri-utama", 6_071_000)
        self.assertIn("spaylater Rp 270.000 (2026-11-01); cicilan-mobil Rp 5.701.000 (2026-11-02); ditambah saldo minimum "
                      "yang ditahan bank Rp 100.000", ok)
        self.assertIn("Butuh Rp 6.071.000 sebelum 2026-11-01: saldo CUKUP (lebih Rp 0)", ok)
        self.assertIn("hanya benar bila semua transfer gajian sudah dilakukan", ok)      # payday: transfers may still be due
        self.assertIn("KURANG Rp 1", tools.record_account_balance(conn, date(2026, 10, 30), "mandiri-utama", 6_070_999))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM balance_reports").fetchone()[0], 2)

    def test_a_debit_due_today_gives_both_figures(self):
        conn = self.world()
        out = tools.record_account_balance(conn, date(2026, 11, 1), "mandiri-utama", 5_900_000)
        self.assertIn("BELUM terpotong: butuh Rp 6.071.000, saldo KURANG Rp 171.000", out)
        self.assertIn("SUDAH terpotong: butuh Rp 5.801.000, saldo CUKUP (lebih Rp 99.000)", out)
        # a salary transfer still open: what is left after it, for both cases as well
        PayeeVault(conn, bytes(range(32))).store("sekolah-va", "va", "BCA", "9" * 10)
        tools.upsert_expense(conn, "sekolah", "sekolah-va", 50_000, 1)
        tools.generate_payday_plan(conn, date(2026, 11, 1))
        self.assertIn("Transfer gajian yang belum tercatat selesai: sekolah-va Rp 50.000. Bila dibayar dari rekening ini: bila "
                      "autodebet hari ini BELUM terpotong, saldonya KURANG Rp 221.000 untuk itu; bila SUDAH terpotong, sesudahnya "
                      "yang bisa dipakai Rp 49.000. Laporkan saldo lagi",
                      tools.record_account_balance(conn, date(2026, 11, 1), "mandiri-utama", 5_900_000))

    def test_after_the_last_debit_nothing_is_due_until_the_next_salary(self):
        out = tools.record_account_balance(self.world(), date(2026, 11, 10), "mandiri-utama", 500_000)
        self.assertIn("Tidak ada autodebet dari mandiri-utama sampai gajian berikutnya (2026-11-30)", out)
        self.assertNotIn("transfer gajian", out)
        # the free balance in the code's words (30 Oct: the bot took the held 100.000 off itself)
        self.assertIn("(2026-11-30). Yang bisa dipakai Rp 400.000: saldo Rp 500.000 dikurangi saldo minimum yang ditahan bank "
                      "Rp 100.000.", out)
        self.assertNotIn("; ditambah", out)
        low = tools.record_account_balance(self.world(), date(2026, 11, 10), "mandiri-utama", 60_000)
        self.assertIn("Saldo Rp 60.000 di bawah saldo minimum yang ditahan bank Rp 100.000: tidak ada yang bisa dipakai.", low)

    def test_the_plan_reads_a_balance_from_this_payday_only(self):
        conn = self.world()
        tools.record_account_balance(conn, date(2026, 10, 20), "mandiri-utama", 9_000_000)      # before this payday
        self.assertFalse([r for r in tools.generate_payday_plan(conn, date(2026, 10, 30))["reminders"] if r.startswith("SALDO")])
        tools.record_account_balance(conn, date(2026, 10, 30), "mandiri-utama", 6_000_000)
        rem = [r for r in tools.generate_payday_plan(conn, date(2026, 10, 30))["reminders"] if r.startswith("SALDO")]
        self.assertEqual(len(rem), 1)
        self.assertIn("Rp 6.000.000, dilaporkan 2026-10-30 pukul", rem[0])
        self.assertIn("saldo KURANG Rp 71.000", rem[0])
        self.assertRegex(tools.data_overview(conn, TODAY), r"- mandiri-utama \| Mandiri \| main \| 0001 \| Rp 100\.000 \| "
                                                            r"Rp 6\.000\.000, dilaporkan 2026-10-30 pukul \d\d:\d\d WIB")

    def test_unknown_account_and_negative_balance_are_refused(self):
        conn = self.world()
        with self.assertRaisesRegex(ValueError, "belum terdaftar"):
            tools.record_account_balance(conn, TODAY, "ghost", 1_000)
        with self.assertRaisesRegex(ValueError, "negatif"):
            tools.record_account_balance(conn, TODAY, "mandiri-utama", -1)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM balance_reports").fetchone()[0], 0)


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
            self.assertIn("Autodebet (tidak perlu transfer, pastikan saldo cukup)", text)
            self.assertIn("Cicilan Mobil", text)
            self.assertIn("dari rekening Mandiri", text)
            self.assertIn("Rp 5.701.000", text)
            self.assertIn("Saldo rekening Mandiri minimal *Rp 5.701.000* sampai semua autodebetnya terpotong", text)
            self.assertNotIn("`", text)                                              # no copyable number at all


if __name__ == "__main__":
    unittest.main()
