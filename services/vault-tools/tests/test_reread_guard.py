import asyncio
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
try:
    from vault_tools import statement_pdf
    from vault_tools.server import create_app
    HAVE_SERVER = True
except ImportError:
    HAVE_SERVER = False


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class RereadGuard(unittest.TestCase):
    """Regression: the bot scanned 27 recorded statements in one chat (~70k tokens) and the session stalled."""

    def make(self, d):
        app = create_app(os.path.join(d, "l.db"), bytes(range(32)), "m" * 40, "i" * 40, allowed_hosts=["testserver"],
                         ingest_dir=d, passwords_path=None)
        call = lambda n, a=None: asyncio.run(app.state.mcp.call_tool(n, a or {}))  # noqa: E731
        return app, call

    def text_of(self, res):
        return json.dumps(res, default=str)

    def write(self, d, name, body):
        path = os.path.join(d, name)
        with open(path, "w") as f:
            f.write(body)
        return statement_pdf.file_sha256(open(path, "rb").read())

    def test_new_documents_are_never_limited_but_recorded_ones_are(self):
        with tempfile.TemporaryDirectory() as d:
            app, call = self.make(d)
            call("upsert_card", {"alias": "cimb-1", "bank": "CIMB", "last4": "1111", "statement_day": 5, "due_day": 20, "credit_limit": 5_000_000})
            hashes = []
            for i in range(6):
                hashes.append(self.write(d, f"s{i}.csv", f"01/10/2026 BELANJA {i} 100.000\n"))
                self.assertIn("file_hash=", self.text_of(call("ingest_statement", {"file_ref": f"s{i}.csv"})))     # new: all readable
            for i, h in enumerate(hashes):
                call("record_statement", {"card_alias": "cimb-1", "file_hash": h, "statement_date": f"2026-0{i + 1}-05", "due_date": f"2026-0{i + 1}-20",
                                           "previous_balance": 0, "payments": 0, "charges": 100, "fees": 0, "total_due": 100, "minimum_due": 10})
            outs = [self.text_of(call("ingest_statement", {"file_ref": f"s{i}.csv"})) for i in range(5)]
            self.assertEqual(["BATAS BACA ULANG" in o for o in outs], [False, False, False, True, True])         # 3 re-reads per window
            self.assertIn("ringkasan_data", outs[3])
            self.assertNotIn("BELANJA", outs[3])                                                                 # the content is not returned

    def test_the_bot_cannot_open_the_window_or_touch_system_keys(self):
        with tempfile.TemporaryDirectory() as d:
            app, call = self.make(d)
            for key in ("reread_open_until", "ingest_events_cursor", "living_reserve_override", "living_reserve_override_until"):
                with self.assertRaises(Exception):
                    call("set_threshold", {"key": key, "value": 1})
            call("set_threshold", {"key": "net_salary", "value": 10_000_000})                                    # normal keys still work


if __name__ == "__main__":
    unittest.main()
