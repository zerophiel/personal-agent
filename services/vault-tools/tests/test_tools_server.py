import asyncio
import json
import os
import sys
import tempfile
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from vault_tools import tools  # noqa: E402
from vault_tools.ledger import connect  # noqa: E402

try:
    from starlette.testclient import TestClient
    from vault_tools.server import MCP_TOOL_NAMES, create_app
    HAVE_SERVER = True
except ImportError:  # system python without mcp/starlette: run these in the vault-tools venv
    HAVE_SERVER = False

KEY = bytes(range(32))
MCP_T, INT_T = "m" * 40, "i" * 40
TODAY = date(2026, 10, 27)


def seeded(conn):
    tools.set_threshold(conn, "net_salary", 10_000_000)
    tools.upsert_card(conn, "dbs-1111", "DBS", "1111", 5, 20, 15_000_000)
    tools.upsert_debt(conn, "pinjaman-3333", "Bank X", 8_000_000, 1_500_000, 6, 2, 200)
    tools.upsert_expense(conn, "sekolah", "sekolah-2222", 2_000_000, 10)
    conn.execute(
        "INSERT INTO statements(card_id,file_hash,statement_date,due_date,previous_balance,payments,"
        "charges,fees,total_due,minimum_due,reconciled,recon_diff,ingested_at)"
        " VALUES (1,'h1','2026-10-05','2026-11-05',0,0,3000000,0,3000000,300000,1,0,'t')")
    conn.commit()


class Holidays(unittest.TestCase):
    def test_cuti_bersama_included(self):
        h = tools.id_holidays(2026)
        for d in (date(2026, 3, 20), date(2026, 3, 24), date(2026, 5, 15), date(2026, 12, 24)):
            self.assertIn(d, h)
        self.assertIn(date(2026, 3, 19), h)       # national holiday from python-holidays
        self.assertNotIn(date(2026, 1, 2), h)     # not a joint-leave day

    def test_payday_skips_cuti_bersama(self):
        from vault_tools.payday import last_working_day
        # 31 Mar 2026 is a working day; 24 Dec cuti + 25 Dec Natal push Dec payday only if at month end
        self.assertEqual(last_working_day(2026, 12, tools.id_holidays(2026)), date(2026, 12, 31))
        self.assertEqual(last_working_day(2026, 5, tools.id_holidays(2026)), date(2026, 5, 29))


class Tools(unittest.TestCase):
    def test_due_dates_clamped_and_windowed(self):
        w = tools.due_dates_in_window(31, date(2026, 10, 30), date(2026, 11, 30))
        self.assertEqual(w, [date(2026, 10, 31)])  # 31 Nov clamps to 30 = end (excluded)
        self.assertEqual(tools.due_dates_in_window(10, date(2026, 10, 30), date(2026, 11, 30)),
                         [date(2026, 11, 10)])

    def test_plan_from_ledger(self):
        conn = connect(":memory:")
        seeded(conn)
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertEqual(snap["payday"], "2026-10-30")
        self.assertEqual(snap["next_payday"], "2026-11-30")
        got = {(t["to_alias"], t["reason"]): t["amount"] for t in snap["transfers"]}
        self.assertEqual(got[("dbs-1111", "tagihan kartu - minimum")], 300_000)
        self.assertEqual(got[("dbs-1111", "tagihan kartu - sisa saldo (bayar penuh)")], 2_700_000)
        self.assertEqual(got[("sekolah-2222", "pengeluaran tetap")], 2_000_000)
        self.assertEqual(got[("pinjaman-3333", "cicilan")], 1_500_000)
        self.assertEqual(snap["cash_to_hold"], 10_000_000 - 6_500_000)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0], 1)

    def test_paid_statement_excluded_and_salary_required(self):
        conn = connect(":memory:")
        with self.assertRaises(ValueError):
            tools.generate_payday_plan(conn, TODAY)
        seeded(conn)
        conn.execute("UPDATE statements SET paid_at='2026-10-20'")
        snap = tools.generate_payday_plan(conn, TODAY)
        self.assertNotIn("dbs-1111", [t["to_alias"] for t in snap["transfers"]])

    def test_summary_has_no_digits_runs(self):
        conn = connect(":memory:")
        seeded(conn)
        text = tools.summarize_plan(tools.generate_payday_plan(conn, TODAY))
        self.assertIn("Rp 2.700.000", text)
        self.assertNotIn("http", text)


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class Server(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.app = create_app(os.path.join(self.tmp.name, "l.db"), KEY, MCP_T, INT_T,
                              allowed_hosts=["testserver"], today=lambda: TODAY)

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, c, path, token, body):
        h = {"Authorization": f"Bearer {token}"} if token else {}
        return c.post(path, json=body, headers=h)

    def test_tokens_must_differ(self):
        with self.assertRaises(ValueError):
            create_app(":memory:", KEY, MCP_T, MCP_T)

    def test_mcp_tools_have_no_secret_access(self):
        names = {t.name for t in asyncio.run(self.app.state.mcp.list_tools())}
        self.assertEqual(names, set(MCP_TOOL_NAMES))
        self.assertFalse({n for n in names if "reveal" in n or "store" in n or "rincian" in n})

    def test_auth_separation(self):
        with TestClient(self.app) as c:
            body = {"alias": "dbs-1111", "kind": "card", "bank": "DBS", "number": "4111111111111111"}
            self.assertEqual(self.post(c, "/internal/store_payee", None, body).status_code, 401)
            self.assertEqual(self.post(c, "/internal/store_payee", MCP_T, body).status_code, 401)
            self.assertEqual(self.post(c, "/mcp", INT_T, {}).status_code, 401)
            self.assertEqual(c.get("/other").status_code, 404)

    def test_store_then_rincian(self):
        with TestClient(self.app) as c:
            r = self.post(c, "/internal/store_payee", INT_T,
                          {"alias": "dbs-1111", "kind": "card", "bank": "DBS", "number": "4111 1111 1111 1111"})
            self.assertEqual(r.json(), {"ok": True, "alias": "dbs-1111", "display": "dbs-1111 ****1111"})
            dup = self.post(c, "/internal/store_payee", INT_T,
                            {"alias": "other-9", "kind": "card", "bank": "?", "number": "4111111111111111"}).json()
            self.assertEqual((dup["alias"], dup["duplicate"]), ("dbs-1111", True))  # same number, same alias
            other = self.post(c, "/internal/store_payee", INT_T,
                              {"alias": "dbs-1111", "kind": "card", "bank": "?", "number": "5500 0000 0000 0004"}).json()
            self.assertEqual(other["alias"], "dbs-1111-2")                          # alias collision -> suffix
            self.assertNotIn("4111111111111111", r.text)
            self.assertIn("Belum ada", self.post(c, "/internal/rincian", INT_T, {}).text)

    def test_full_number_only_via_rincian(self):
        call = lambda name, args: asyncio.run(self.app.state.mcp.call_tool(name, args))  # noqa: E731
        call("set_threshold", {"key": "net_salary", "value": 10_000_000})
        call("upsert_card", {"alias": "dbs-1111", "bank": "DBS", "last4": "1111",
                             "statement_day": 5, "due_day": 20, "credit_limit": 15_000_000})
        call("upsert_expense", {"alias": "sekolah", "payee_alias": "dbs-1111", "amount": 2_000_000, "due_day": 10})
        out = json.dumps(call("generate_payday_plan", {}), default=str)
        with TestClient(self.app) as c:
            self.post(c, "/internal/store_payee", INT_T,
                      {"alias": "dbs-1111", "kind": "card", "bank": "DBS", "number": "4111 1111 1111 1111"})
            self.assertNotIn("4111111111111111", out)  # model-facing plan has no full number
            listed = json.dumps(call("list_payees", {}), default=str)
            self.assertNotIn("4111111111111111", listed)
            self.assertIn("****1111", listed)
            text = self.post(c, "/internal/rincian", INT_T, {}).text
            self.assertIn("4111111111111111", text)
            self.assertIn("Rp 2.000.000", text)

    def test_cvv_rejected_and_error_does_not_echo_number(self):
        with TestClient(self.app) as c:
            r = self.post(c, "/internal/store_payee", INT_T,
                          {"alias": "a-1", "kind": "card", "bank": "X", "number": "4111111111111111",
                           "raw_text": "4111111111111111 cvv 123"})
            self.assertEqual(r.status_code, 422)
            r = self.post(c, "/internal/store_payee", INT_T,
                          {"alias": "BAD ALIAS", "kind": "card", "bank": "X", "number": "4111111111111111"})
            self.assertEqual(r.status_code, 422)
            self.assertNotIn("4111", r.text)


if __name__ == "__main__":
    unittest.main()
