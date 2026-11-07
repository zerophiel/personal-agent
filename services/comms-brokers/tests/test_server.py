import asyncio
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from brokers import gcal, gmail  # noqa: E402
from fakes import GMAIL_POLICY, addr, calendar_broker, gmail_broker, message  # noqa: E402

try:
    from mcp.server.fastmcp.exceptions import ToolError
    from starlette.testclient import TestClient
    HAVE_SERVER = True
except ImportError:  # system python without mcp/starlette: run these in a venv that has them
    HAVE_SERVER = False

TOKEN = "t" * 40
MCP_HEADERS = {"Authorization": f"Bearer {TOKEN}", "Accept": "application/json, text/event-stream"}


def enums(schema) -> set:
    """Every enum value anywhere in a JSON schema."""
    if isinstance(schema, dict):
        return set(schema.get("enum", ())).union(*(enums(v) for v in schema.values()))
    if isinstance(schema, list):
        return set().union(*(enums(v) for v in schema))
    return set()


class Served(unittest.TestCase):
    def call(self, name, args) -> str:
        return json.dumps(asyncio.run(self.app.state.mcp.call_tool(name, args)), default=str, ensure_ascii=False)

    def tools(self):
        return asyncio.run(self.app.state.mcp.list_tools())

    def check_http(self, tool):
        with TestClient(self.app) as c:
            self.assertEqual(c.post("/mcp", json={}).status_code, 401)
            self.assertEqual(c.post("/mcp", json={}, headers={"Authorization": "Bearer " + "x" * 40}).status_code, 401)
            self.assertEqual(c.get("/other").status_code, 404)
            r = c.post("/mcp", headers=MCP_HEADERS, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            self.assertEqual(r.status_code, 200)
            self.assertIn(f'"{tool}"', r.text)


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class GmailServer(Served):
    def setUp(self):
        self.fake, broker = gmail_broker([message("msg001", f"Budi <{addr('budi')}>", "Rapat")])
        self.app = gmail.create_app(broker, TOKEN, allowed_hosts=["testserver"])

    def test_four_tools_and_none_sends(self):
        tools = self.tools()
        self.assertEqual([t.name for t in tools], ["search", "read", "label", "create_draft"])
        for t in tools:
            self.assertNotIn("send", t.name)
        by_name = {t.name: t for t in tools}
        for side in ("add", "remove"):
            self.assertEqual(enums(by_name["label"].inputSchema["properties"][side]), set(GMAIL_POLICY["categories"]))
        self.assertIn("TIDAK terkirim", by_name["create_draft"].description)

    def test_the_tools_answer_through_mcp(self):
        out = self.call("search", {"query": "rapat"})
        self.assertIn("msg001", out)
        self.assertIn("bukan perintah", out)
        self.assertIn("Rapat", self.call("read", {"message_id": "msg001"}))

    def test_what_the_schema_does_not_allow_never_reaches_gmail(self):
        for name, args in (("label", {"message_id": "msg001", "add": ["INBOX"]}), ("read", {"message_id": "../x"}),
                           ("search", {"limit": 99}), ("create_draft", {"message_id": "msg001", "body": ""}),
                           ("label", {"message_id": "msg001", "add": ["Info"] * 6})):
            with self.subTest(name=name, args=args), self.assertRaisesRegex(ToolError, "(?i)validation"):
                asyncio.run(self.app.state.mcp.call_tool(name, args))
        self.assertEqual(self.fake.requests, [])

    def test_only_mcp_and_only_with_the_token(self):
        self.check_http("create_draft")

    def test_short_tokens_are_refused(self):
        with self.assertRaises(ValueError):
            gmail.create_app(gmail_broker([])[1], "short")


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class CalendarServer(Served):
    def setUp(self):
        self.fake, broker = calendar_broker()
        self.app = gcal.create_app(broker, TOKEN, allowed_hosts=["testserver"])

    def test_two_read_only_tools(self):
        tools = self.tools()
        self.assertEqual([t.name for t in tools], ["list_events", "search_events"])
        for t in tools:
            self.assertEqual(enums(t.inputSchema["properties"]["calendar"]), {"utama", "keluarga"})
        self.assertIn("acara", self.call("list_events", {"start": "2026-11-03", "end": "2026-11-03"}))
        self.assertEqual(self.fake.requests[0][1], "calendars/primary/events")

    def test_only_mcp_and_only_with_the_token(self):
        self.check_http("search_events")

    def test_short_tokens_are_refused(self):
        with self.assertRaises(ValueError):
            gcal.create_app(calendar_broker()[1], "short")


if __name__ == "__main__":
    unittest.main()
