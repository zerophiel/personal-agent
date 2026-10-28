import json
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_roadmap import TODAY, full_world, statement  # noqa: E402

from vault_tools import card_installments as ci  # noqa: E402
from vault_tools import notion_sync as ns  # noqa: E402
from vault_tools import subscriptions as sub  # noqa: E402
from vault_tools import tools  # noqa: E402

TOKEN = "secret_TOKEN_must_never_appear"


class FakeNotion:
    """Records every call; serves child pages and blocks like the real API closely enough."""
    def __init__(self, pages=None, fail_status=None, rate_limit_first=False):
        self.calls, self.titles = [], {}
        self.children = {"FIN": [{"id": pid, "type": "child_page", "child_page": {"title": t}} for t, pid in (pages or {}).items()]}
        for pid in (pages or {}).values():
            self.children[pid] = [{"id": f"old-{pid}-1", "type": "paragraph"}, {"id": f"old-{pid}-2", "type": "table"}]
        self.fail_status, self.limited, self.n = fail_status, rate_limit_first, 0

    def http(self, method, url, data, headers):
        assert headers["Authorization"] == f"Bearer {TOKEN}"
        path = url.split("/v1/")[1]
        body = json.loads(data) if data else None
        self.calls.append((method, path, body))
        if self.limited and self.n == 0:
            self.n += 1
            return 429, b"{}"
        if self.fail_status:
            return self.fail_status, b'{"message":"nope secret_TOKEN_must_never_appear"}'
        if method == "GET":
            bid = path.split("/")[1]
            return 200, json.dumps({"results": self.children.get(bid, []), "has_more": False}).encode()
        if method == "POST" and path == "pages":
            pid = f"new-{len(self.calls)}"
            self.children[pid] = []
            self.titles[pid] = body["properties"]["title"]["title"][0]["text"]["content"]
            return 200, json.dumps({"id": pid}).encode()
        if method == "PATCH" and path.startswith("pages/"):
            self.titles[path.split("/")[1]] = body["properties"]["title"]["title"][0]["text"]["content"]
        return 200, b"{}"


def world():
    conn = full_world()
    tools.upsert_card(conn, "bca-1", "BCA", "1111", 5, 25, 10_000_000, interest_bp_month=275)
    statement(conn, 1, 8_000_000, 800_000)
    ci.record(conn, "bca-1", "2026-10-05", [{"description": "TOKOPEDIA", "amount": 1_000_000, "seq": 3, "total": 12}])
    sub.upsert(conn, "spotify", "Spotify", 119_900, "bca-1")
    return conn


class Sync(unittest.TestCase):
    def run_sync(self, fake, conn=None):
        n = ns.Notion(TOKEN, http=fake.http, sleep=lambda s: None)
        return ns.sync(conn or world(), n, "FIN", TODAY), n

    def test_creates_missing_pages_and_fills_them(self):
        fake = FakeNotion()
        done, _ = self.run_sync(fake)
        self.assertEqual(len(done), 5)
        creates = [c for c in fake.calls if c[0] == "POST"]
        self.assertEqual(len(creates), 5)
        appends = [c for c in fake.calls if c[0] == "PATCH" and c[1].endswith("/children")]
        self.assertEqual(len(appends), 5)
        text = json.dumps([c[2] for c in fake.calls])
        self.assertIn("Spotify", text)
        self.assertIn("Rp 119.900", text)

    def test_existing_pages_are_updated_new_blocks_first_then_old_ones_archived(self):
        fake = FakeNotion(pages={"Rencana gajian 2026-09-30": "P1", "Tagihan kartu": "P2"})
        self.run_sync(fake)
        methods = [(m, p) for m, p, _ in fake.calls if "P1" in p]
        append_i = next(i for i, (m, p) in enumerate(methods) if m == "PATCH" and p == "blocks/P1/children")
        delete_i = next(i for i, (m, p) in enumerate(methods) if m == "DELETE")
        self.assertLess(append_i, delete_i)                                       # a failure never leaves an empty page
        self.assertEqual(sorted(p for m, p, _ in fake.calls if m == "DELETE" and "P1" in p), ["blocks/old-P1-1", "blocks/old-P1-2"])
        self.assertTrue(fake.titles["P1"].startswith("Rencana gajian 2026-10"))   # the date in the title moves with the plan
        self.assertEqual(len([c for c in fake.calls if c[0] == "POST"]), 3)       # the other three did not exist

    def test_child_pages_are_never_deleted(self):
        fake = FakeNotion(pages={"Tagihan kartu": "P2"})
        fake.children["P2"].append({"id": "sub-page", "type": "child_page", "child_page": {"title": "x"}})
        self.run_sync(fake)
        self.assertNotIn("blocks/sub-page", [p for m, p, _ in fake.calls if m == "DELETE"])

    def test_no_card_numbers_and_no_token_in_what_is_written(self):
        fake = FakeNotion()
        self.run_sync(fake)
        written = json.dumps([c[2] for c in fake.calls if c[2]])
        self.assertNotIn(TOKEN, written)
        self.assertNotIn("106879418405", written)             # the pot account number stored in the payee vault
        self.assertNotIn("4111", written)

    def test_rate_limit_is_retried(self):
        fake = FakeNotion(rate_limit_first=True)
        done, _ = self.run_sync(fake)
        self.assertEqual(len(done), 5)

    def test_errors_never_echo_the_response_or_the_token(self):
        fake = FakeNotion(fail_status=403)
        n = ns.Notion(TOKEN, http=fake.http, sleep=lambda s: None)
        with self.assertRaises(ns.NotionError) as cm:
            ns.sync(world(), n, "FIN", TODAY)
        self.assertNotIn(TOKEN, str(cm.exception))
        self.assertNotIn("nope", str(cm.exception))

    def test_more_than_100_blocks_are_appended_in_chunks(self):
        fake = FakeNotion(pages={"Tagihan kartu": "P2"})
        n = ns.Notion(TOKEN, http=fake.http, sleep=lambda s: None)
        n.replace_content("P2", [ns.bullet(f"b{i}") for i in range(230)])
        sizes = [len(b["children"]) for m, p, b in fake.calls if m == "PATCH" and p == "blocks/P2/children"]
        self.assertEqual(sizes, [100, 100, 30])

    def test_table_builder_limits_rows_and_keeps_width(self):
        t = ns.table(["a", "b"], [["1", "2"]] * 120)
        self.assertEqual(t["table"]["table_width"], 2)
        self.assertEqual(len(t["table"]["children"]), 91)


if __name__ == "__main__":
    unittest.main()
