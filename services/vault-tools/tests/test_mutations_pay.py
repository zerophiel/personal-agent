import asyncio
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import mutations as mu  # noqa: E402
from vault_tools import names, tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402
from vault_tools.masking import mask_sensitive  # noqa: E402
from vault_tools.payee_vault import PayeeVault  # noqa: E402

KEY = bytes(range(32))
H1, H2, H3 = "1" * 64, "2" * 64, "3" * 64


def acct_db():
    conn = connect(":memory:")
    conn.execute("INSERT INTO accounts(alias,bank,kind,last4) VALUES ('bca-main','BCA','main','1234')")
    conn.commit()
    return conn


def rows(*items):
    return [{"date": d, "description": desc, "amount": a} for d, desc, a in items]


class Migration(unittest.TestCase):
    def test_v1_ledger_is_upgraded_in_place(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "old.db")
            old = sqlite3.connect(path)
            old.executescript("""
              CREATE TABLE cards (id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, bank TEXT NOT NULL,
                last4 TEXT NOT NULL, statement_day INTEGER NOT NULL, due_day INTEGER NOT NULL, credit_limit INTEGER NOT NULL);
              CREATE TABLE transactions (id INTEGER PRIMARY KEY, statement_id INTEGER, card_id INTEGER, account_id INTEGER,
                txn_date TEXT NOT NULL, merchant TEXT NOT NULL, amount INTEGER NOT NULL, category TEXT,
                status TEXT NOT NULL, source TEXT NOT NULL);
              INSERT INTO cards VALUES (1,'old','CIMB','1111',5,20,1000000);
            """)
            old.commit()
            old.close()
            conn = connect(path)
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(cards)")}
            self.assertTrue({"pay_method", "pay_to_alias"} <= cols)
            tcols = {r["name"] for r in conn.execute("PRAGMA table_info(transactions)")}
            self.assertTrue({"dedupe_key", "file_hash"} <= tcols)
            self.assertEqual(conn.execute("SELECT alias, pay_method FROM cards").fetchone()[:], ("old", "transfer"))
            connect(path)  # idempotent second open


class PayRules(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        self.v = PayeeVault(self.conn, KEY)
        self.v.store("num-4417", "card", "?", "4111 1111 1111 1111")
        self.v.store("bca-rek", "account", "BCA", "1234567890")
        self.v.store("jenius-rek", "va", "Jenius", "8808123456789012")

    def card(self, bank, **kw):
        return tools.upsert_card(self.conn, f"{bank}-1", bank, "1111", 5, 20, 10_000_000, **kw)

    def test_bca_and_jenius_need_account_not_card_number(self):
        with self.assertRaises(ValueError):
            self.card("bca", pay_to_alias="num-4417")          # card number: rejected
        with self.assertRaises(ValueError):
            self.card("jenius", pay_to_alias="num-4417")
        self.assertIn("transfer", self.card("bca", pay_to_alias="bca-rek"))
        self.assertIn("transfer", self.card("jenius", pay_to_alias="jenius-rek"))   # VA accepted

    def test_mandiri_pays_via_app_menu_with_card_number(self):
        self.assertIn("menu aplikasi", self.card("mandiri", pay_to_alias="num-4417"))
        self.assertEqual(self.conn.execute("SELECT pay_method FROM cards WHERE alias='mandiri-1'").fetchone()[0], "app_menu")
        with self.assertRaises(ValueError):
            self.card("mandiri", pay_method="transfer")
        with self.assertRaises(ValueError):
            self.card("mandiri", pay_to_alias="bca-rek")       # an account number is not the card

    def test_other_banks_transfer_to_card_number_and_unknown_payee_rejected(self):
        self.assertIn("transfer", self.card("cimb", pay_to_alias="num-4417"))
        with self.assertRaises(ValueError):
            self.card("cimb", pay_to_alias="ghost")

    def test_reupsert_keeps_existing_pay_target(self):
        self.card("bca", pay_to_alias="bca-rek")
        self.card("bca")                                       # no pay_to given: keep
        self.assertEqual(self.conn.execute("SELECT pay_to_alias FROM cards WHERE alias='bca-1'").fetchone()[0], "bca-rek")

    def test_plan_carries_method_and_target(self):
        self.card("mandiri", pay_to_alias="num-4417")
        tools.set_threshold(self.conn, "net_salary", 10_000_000)
        self.conn.execute(
            "INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,fees,"
            "total_due,minimum_due,reconciled,recon_diff,ingested_at) VALUES (1,'h','2026-10-05','2026-11-05',0,0,500000,0,500000,50000,1,0,'t')")
        self.conn.commit()
        snap = tools.generate_payday_plan(self.conn, date(2026, 10, 27))
        t = snap["transfers"][0]
        self.assertEqual((t["method"], t["pay_to"]), ("app_menu", "num-4417"))
        self.assertIn("via menu aplikasi", tools.summarize_plan(snap))
        self.assertNotIn("4111", json.dumps(snap))


class Names(unittest.TestCase):
    def test_safe_name_and_hermes_path(self):
        self.assertEqual(names.safe_name("Mutasi <Okt> é.pdf"), "Mutasi ?Okt? ?.pdf")
        self.assertEqual(names.normalize_ref("/opt/data/cache/documents/x.pdf"), "telegram/x.pdf")
        self.assertEqual(names.normalize_ref("telegram/x.pdf"), "telegram/x.pdf")

    def test_list_uploads_newest_first_sanitized_and_skips_symlinks(self):
        with tempfile.TemporaryDirectory() as d:
            for n, t in (("old.pdf", 100), ("Mutasi é.csv", 300), ("mid.pdf", 200)):
                p = os.path.join(d, n)
                open(p, "w").close()
                os.utime(p, (t, t))
            os.symlink("/etc/passwd", os.path.join(d, "link.pdf"))
            self.assertEqual(tools.list_uploads(d), ["telegram/Mutasi ?.csv", "telegram/mid.pdf", "telegram/old.pdf"])
            self.assertEqual(tools.list_uploads(os.path.join(d, "none")), [])


class Masking(unittest.TestCase):
    def test_account_numbers_masked_amounts_untouched(self):
        t = "TRSF 1234567890123 ke BUDI Rp 1.500.000,00 saldo 10000000 ref 12345"
        out = mask_sensitive(t, mask_accounts=True)
        self.assertIn("[[NUM:****0123]]", out)
        self.assertIn("1.500.000,00", out)
        self.assertIn("saldo 10000000", out)          # 8 digits: an amount, not an account
        self.assertEqual(mask_sensitive(t), t.replace("", ""))  # off by default

    def test_digit_run_touching_separator_left_alone(self):
        self.assertEqual(mask_sensitive("1234567890,50", mask_accounts=True), "1234567890,50")


class Mutations(unittest.TestCase):
    def test_record_reconcile_and_flag(self):
        conn = acct_db()
        r = mu.record_mutations(conn, "bca-main", H1, "2026-09-01", "2026-09-30", 1_000_000, 5_500_000,
                                rows(("2026-09-25", "GAJI PT X", 5_000_000), ("2026-09-26", "INDOMARET 123456", -500_000)))
        self.assertEqual((r["status"], r["new_rows"], r["reconciled"]), ("stored", 2, True))
        bad = mu.record_mutations(conn, "bca-main", H2, "2026-10-01", "2026-10-31", 0, 999,
                                  rows(("2026-10-02", "X", 100)))
        self.assertFalse(bad["reconciled"])
        self.assertIn("selisih 899", bad["warning"])
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 3)   # stored, not corrected

    def test_same_file_and_overlapping_periods_dedupe(self):
        conn = acct_db()
        a = rows(("2026-09-10", "KOPI", -30_000), ("2026-09-10", "KOPI", -30_000), ("2026-09-11", "GRAB", -50_000))
        mu.record_mutations(conn, "bca-main", H1, "2026-09-01", "2026-09-30", None, None, a)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 3)  # two identical coffees kept
        self.assertEqual(mu.record_mutations(conn, "bca-main", H1, "2026-09-01", "2026-09-30", None, None, a)["status"], "duplicate")
        b = a + rows(("2026-09-12", "BARU", -10_000))
        r = mu.record_mutations(conn, "bca-main", H2, "2026-09-10", "2026-10-05", None, None, b)
        self.assertEqual((r["new_rows"], r["already_known"]), (1, 3))
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 4)

    def test_bad_input(self):
        conn = acct_db()
        for kw in ({"account_alias": "ghost"}, {"file_hash": "short"}, {"period_end": "2026-08-01"}):
            args = dict(account_alias="bca-main", file_hash=H3, period_start="2026-09-01", period_end="2026-09-30",
                        opening_balance=None, closing_balance=None, rows=rows(("2026-09-02", "x", -1)))
            args.update(kw)
            with self.assertRaises(ValueError):
                mu.record_mutations(conn, **args)
        with self.assertRaises(TypeError):
            mu.record_mutations(conn, "bca-main", H3, "2026-09-01", "2026-09-30", None, None, rows(("2026-09-02", "x", 1.5)))
        with self.assertRaises(ValueError):
            mu.record_mutations(conn, "bca-main", H3, "2026-09-01", "2026-09-30", None, None, [])

    def seed_months(self, conn):
        for i, month in enumerate(("2026-07", "2026-08", "2026-09", "2026-10")):
            mu.record_mutations(conn, "bca-main", f"{i}" * 64, f"{month}-01", f"{month}-28", None, None, rows(
                (f"{month}-25", "GAJI PT MAJU 998877", 10_000_000 + i * 1000),
                (f"{month}-05", "NETFLIX.COM 123456", -186_000),
                (f"{month}-06", "WARUNG MAKAN", -120_000 - i),
                (f"{month}-07", "TRANSFER KE TABUNGAN", -2_000_000),
            ))

    def test_rules_apply_to_new_and_existing_rows(self):
        conn = acct_db()
        mu.record_mutations(conn, "bca-main", H1, "2026-09-01", "2026-09-30", None, None, rows(("2026-09-05", "NETFLIX.COM 111111", -186_000)))
        self.assertEqual(mu.list_uncategorized(conn)[0].split(" | ")[:2], ["netflix.com #", "1x"])
        self.assertIn("1 transaksi diperbarui", mu.set_category_rule(conn, "Netflix.com 999999", "langganan"))
        mu.record_mutations(conn, "bca-main", H2, "2026-10-01", "2026-10-31", None, None, rows(("2026-10-05", "NETFLIX.COM 222222", -186_000)))
        cats = [r[0] for r in conn.execute("SELECT category FROM transactions")]
        self.assertEqual(cats, ["langganan", "langganan"])
        self.assertEqual(mu.list_uncategorized(conn), [])
        with self.assertRaises(ValueError):
            mu.set_category(conn, 999, "x")

    def test_cashflow_excludes_internal_transfers_and_flags_unverified(self):
        conn = acct_db()
        self.seed_months(conn)
        mu.set_category_rule(conn, "TRANSFER KE TABUNGAN", mu.INTERNAL)
        c = mu.cashflow(conn, "2026-10")
        spend = 186_000 + 120_003              # netflix + warung (Oct is i=3); the savings transfer is excluded
        self.assertEqual((c["income"], c["expenses"], c["net"]), (10_003_000, spend, 10_003_000 - spend))
        self.assertEqual(c["savings_rate_bp"], (10_003_000 - spend) * 10_000 // 10_003_000)
        self.assertGreater(c["unverified"], 0)
        text = mu.format_cashflow(c)
        self.assertIn("Rp 10.003.000", text)
        self.assertIn("belum diverifikasi", text)
        self.assertEqual(mu.format_cashflow(mu.cashflow(conn, "2025-01")), "Belum ada mutasi untuk 2025-01.")
        with self.assertRaises(ValueError):
            mu.cashflow(conn, "2026-13")

    def test_one_off_items_stay_out_of_the_monthly_picture(self):
        conn = acct_db()
        mu.record_mutations(conn, "bca-main", H1, "2026-10-01", "2026-10-31", None, None, rows(
            ("2026-10-13", "KLAIM JHT", 130_000_000), ("2026-10-15", "PEMBAYARAN HSBC", -23_000_000),
            ("2026-10-25", "GAJI PT MAJU", 42_000_000), ("2026-10-26", "BELANJA", -2_000_000)))
        mu.set_category_rule(conn, "KLAIM JHT", "sekali:jht")
        mu.set_category_rule(conn, "PEMBAYARAN HSBC", "sekali:pelunasan-kartu")
        c = mu.cashflow(conn, "2026-10")
        self.assertEqual((c["income"], c["expenses"], c["net"]), (42_000_000, 2_000_000, 40_000_000))
        self.assertEqual((c["one_off_in"], c["one_off_out"]), (130_000_000, 23_000_000))
        text = mu.format_cashflow(c)
        self.assertIn("Sekali/perantara (tidak dihitung dalam rasio): masuk Rp 130.000.000; keluar Rp 23.000.000", text)
        self.assertEqual(c["savings_rate_bp"], 40_000_000 * 10_000 // 42_000_000)
        self.assertNotIn("klaim jht", [k for k, _ in c["by_category"]])
        from vault_tools import health as hl
        self.assertFalse(hl.is_discretionary("sekali:jht"))

    def test_money_passing_through_the_owner_is_not_income_expense_or_living(self):
        conn = acct_db()
        mu.record_mutations(conn, "bca-main", H1, "2026-01-01", "2026-01-31", None, None, rows(
            ("2026-01-17", "TRSF DARI REZA", 100_000_000), ("2026-01-17", "TRSF KE AMMAR", -100_000_000),
            ("2026-01-25", "GAJI PT MAJU", 40_000_000), ("2026-01-26", "BELANJA", -3_000_000)))
        mu.set_category_rule(conn, "TRSF DARI REZA", "perantara:ammar-reza")
        mu.set_category_rule(conn, "TRSF KE AMMAR", "perantara:ammar-reza")
        c = mu.cashflow(conn, "2026-01")
        self.assertEqual((c["income"], c["expenses"], c["net"]), (40_000_000, 3_000_000, 37_000_000))
        self.assertEqual((c["one_off_in"], c["one_off_out"]), (100_000_000, 100_000_000))
        self.assertIn("Sekali/perantara", mu.format_cashflow(c))
        from vault_tools import health as hl
        self.assertFalse(hl.is_discretionary("perantara:ammar-reza"))
        mu.record_mutations(conn, "bca-main", "8" * 64, "2026-02-01", "2026-02-28", None, None,
                            rows(("2026-02-25", "GAJI PT MAJU", 40_000_001), ("2026-02-13", "TRSF DARI REZA", 120_000_000)))
        mu.record_mutations(conn, "bca-main", "7" * 64, "2026-03-01", "2026-03-31", None, None, rows(("2026-03-25", "GAJI PT MAJU", 40_000_002)))
        s = mu.suggest_salary(conn)
        self.assertIn("'gaji pt maju'", s)                                           # the pass-through credit is not the "salary"
        self.assertIn("Rp 40.0", s)
        self.assertNotIn("120", s)

    def test_one_off_credit_is_never_suggested_as_salary(self):
        conn = acct_db()
        for i, month in enumerate(("2026-08", "2026-09", "2026-10")):
            mu.record_mutations(conn, "bca-main", str(i) * 64, f"{month}-01", f"{month}-28", None, None,
                                rows((f"{month}-25", "GAJI PT MAJU 998877", 40_000_000 + i)))
        mu.record_mutations(conn, "bca-main", "9" * 64, "2026-10-01", "2026-10-30", None, None,
                            rows(("2026-10-13", "KLAIM JHT BPJS", 130_000_000)))
        mu.set_category_rule(conn, "KLAIM JHT BPJS", "sekali:jht")
        s = mu.suggest_salary(conn)
        self.assertIn("gaji pt maju #", s)
        self.assertIn("Rp 40.0", s)
        self.assertNotIn("jht", s)

    def test_recurring_and_salary_detection(self):
        conn = acct_db()
        self.seed_months(conn)
        rec = mu.recurring(conn)
        self.assertTrue(any(r.startswith("netflix.com #") and "4 bulan" in r for r in rec))
        self.assertTrue(any(r.startswith("warung makan") for r in rec))
        sal = mu.suggest_salary(conn)
        self.assertIn("gaji pt maju #", sal)
        self.assertIn("Rp 10.0", sal)
        self.assertIn("konfirmasi", sal)
        self.assertIn("belum cukup", mu.suggest_salary(acct_db()))


try:
    from starlette.testclient import TestClient
    from vault_tools.server import MCP_TOOL_NAMES, create_app
    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False

INT_T, MCP_T = "i" * 40, "m" * 40
TODAY = date(2026, 10, 27)


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class ServerFlows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ing = os.path.join(self.tmp.name, "ingest")
        os.makedirs(os.path.join(self.ing, "telegram"))
        self.app = create_app(os.path.join(self.tmp.name, "l.db"), KEY, MCP_T, INT_T, allowed_hosts=["testserver"],
                              today=lambda: TODAY, ingest_dir=self.ing, passwords_path=None)
        self.call = lambda n, a=None: asyncio.run(self.app.state.mcp.call_tool(n, a or {}))

    def tearDown(self):
        self.tmp.cleanup()

    def internal(self, c, path, body):
        return c.post(path, json=body, headers={"Authorization": f"Bearer {INT_T}"})

    def test_tool_list_complete_and_still_no_secret_tools(self):
        names_ = {t.name for t in asyncio.run(self.app.state.mcp.list_tools())}
        self.assertEqual(names_, set(MCP_TOOL_NAMES))
        self.assertFalse({n for n in names_ if "reveal" in n or "store" in n or "rincian" in n})

    def test_telegram_csv_upload_to_mutations_to_cashflow(self):
        csv = ("Tanggal,Keterangan,Jumlah\n2026-10-25,GAJI PT MAJU,10000000\n"
               "2026-10-26,TRSF 1234567890123 BUDI,-250000\n")
        with open(os.path.join(self.ing, "telegram", "mutasi okt.csv"), "w") as f:
            f.write(csv)
        listed = json.loads(json.dumps(self.call("list_uploads"), default=str))
        self.assertIn("telegram/mutasi okt.csv", json.dumps(listed))
        out = json.dumps(self.call("ingest_statement", {"file_ref": "/opt/data/cache/documents/mutasi okt.csv"}), default=str)
        self.assertIn("GAJI PT MAJU", out)
        self.assertNotIn("1234567890123", out)          # account number masked
        self.assertIn("file_hash=", out)
        self.call("upsert_account", {"alias": "bca-main", "bank": "BCA", "kind": "main"})
        h = out.split("file_hash=")[1][:64]
        res = self.call("record_mutations", {"account_alias": "bca-main", "file_hash": h, "period_start": "2026-10-01",
                                              "period_end": "2026-10-31", "opening_balance": 0, "closing_balance": 9_750_000,
                                              "rows": [{"date": "2026-10-25", "description": "GAJI PT MAJU", "amount": 10_000_000},
                                                       {"date": "2026-10-26", "description": "TRSF [[NUM:****0123]] BUDI", "amount": -250_000}]})
        self.assertIn("reconciled", json.dumps(res, default=str))
        summary = json.dumps(self.call("cashflow_summary", {"month": "2026-10"}), default=str)
        self.assertIn("Rp 10.000.000", summary)
        self.assertIn("Rp 250.000", summary)

    def test_unsupported_upload_types_rejected(self):
        for name, data in (("x.exe", b"MZ\x00\x01 binary"), ("x.xlsx", b"PK\x03\x04 zip")):
            with open(os.path.join(self.ing, "telegram", name), "wb") as f:
                f.write(data)
            out = json.dumps(self.call("ingest_statement", {"file_ref": f"telegram/{name}"}), default=str)
            self.assertIn("GAGAL", out)

    def test_rincian_shows_account_for_bca_and_menu_hint_for_mandiri(self):
        with TestClient(self.app) as c:
            store = lambda alias, kind, bank, num: self.internal(c, "/internal/store_payee", {  # noqa: E731
                "alias": alias, "kind": kind, "bank": bank, "number": num}).json()["alias"]
            card = store("num-4417", "card", "?", "4111 1111 1111 1111")
            rek = store("bca-rek", "account", "BCA", "1234567890")
            self.call("set_threshold", {"key": "net_salary", "value": 10_000_000})
            self.call("upsert_card", {"alias": "mandiri-1", "bank": "Mandiri", "last4": "1111", "statement_day": 5,
                                      "due_day": 20, "credit_limit": 1_000_000, "pay_to_alias": card})
            self.call("upsert_card", {"alias": "bca-1", "bank": "BCA", "last4": "2222", "statement_day": 5,
                                      "due_day": 21, "credit_limit": 1_000_000, "pay_to_alias": rek})
            conn = sqlite3.connect(os.path.join(self.tmp.name, "l.db"))
            for cid, total in ((1, 400_000), (2, 600_000)):
                conn.execute("INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,charges,"
                             "fees,total_due,minimum_due,reconciled,recon_diff,ingested_at) VALUES (?,?,?,?,0,0,?,0,?,?,1,0,'t')",
                             (cid, f"{cid}" * 64, "2026-10-05", "2026-11-05", total, total, total // 10))
            conn.commit()
            conn.close()
            plan_text = json.dumps(self.call("generate_payday_plan"), default=str)
            self.assertNotIn("4111", plan_text)
            self.assertNotIn("1234567890", plan_text)
            text = self.internal(c, "/internal/rincian", {}).text
            self.assertIn("Lewat menu aplikasi bank (bukan transfer)", text)
            self.assertIn("Mandiri …1111", text)
            self.assertIn("Nomor kartu: `4111111111111111`", text)           # the card number is what the app menu asks for
            self.assertIn("*1. BCA …2222* - tagihan kartu, bayar ke rekening", text)
            self.assertIn("Nomor: `1234567890`", text)                       # a BCA card is paid to the registered account number
            self.assertNotIn("Transfer ke BCA Kartu", text)


if __name__ == "__main__":
    unittest.main()
