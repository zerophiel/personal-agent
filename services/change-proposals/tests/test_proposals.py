import asyncio
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "..", "control"))
import control  # noqa: E402

try:
    from starlette.testclient import TestClient
    from proposals import MAX_PER_DAY, MAX_WAITING, create_app
    HAVE_SERVER = True
except ImportError:  # system python without mcp/starlette: run these in a venv that has them
    HAVE_SERVER = False

TOKEN = "t" * 40
DAY = 86_400.0


def good(**kw):
    p = {"summary": "Tambah domain cuaca untuk front", "zone": "front", "change_type": "egress_domain",
         "permission_diff": "front boleh ke api.cuaca.example", "risk_notes": "domain publik", "rollback": "hapus barisnya",
         "files": [{"path": "config/squid/front.conf", "content": "acl cuaca dstdomain api.cuaca.example\n"}]}
    p.update(kw)
    return p


class FakeTelegram:
    def __init__(self):
        self.sent = []

    def call(self, method, **params):
        if method == "sendMessage":
            self.sent.append(params)
            return {"message_id": len(self.sent)}
        return True


@unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
class Proposals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.inbox = Path(self.tmp.name) / "inbox"
        self.inbox.mkdir()
        self.now = [10 * DAY]
        self.app = create_app(str(self.inbox), TOKEN, allowed_hosts=["testserver"], clock=lambda: self.now[0])

    def tearDown(self):
        self.tmp.cleanup()

    def submit(self, args) -> str:
        return json.dumps(asyncio.run(self.app.state.mcp.call_tool("submit", args)), default=str, ensure_ascii=False)

    def files(self):
        return sorted(p.name for p in self.inbox.iterdir())

    def test_one_tool_whose_choices_are_controls_own(self):
        tools = asyncio.run(self.app.state.mcp.list_tools())
        self.assertEqual([t.name for t in tools], ["submit"])
        props = tools[0].inputSchema["properties"]
        self.assertEqual(set(props["zone"]["enum"]), set(control.ZONES))
        self.assertEqual(set(props["change_type"]["enum"]), set(control.CHANGE_TYPES))
        self.assertIn("services/hermes/{zone}/skills/", tools[0].description)

    def test_a_valid_proposal_lands_whole_in_the_inbox_and_control_posts_it(self):
        out = self.submit(good())
        self.assertIn("Usulan terkirim", out)
        self.assertIn("BELUM ada yang berubah", out)
        [name] = self.files()
        self.assertRegex(name, r"^\d{8}T\d{6}Z-[0-9a-f]{8}\.json$")
        self.assertEqual(stat.S_IMODE((self.inbox / name).stat().st_mode), 0o600)
        self.assertEqual(json.loads((self.inbox / name).read_text(encoding="utf-8")), control.validate(good()))
        tg = FakeTelegram()
        control.Control(tg, 42, Path(self.tmp.name) / "state", self.inbox).tick()
        self.assertEqual(self.files(), [])
        self.assertIn("Usulan perubahan #1 (zona front, jenis egress_domain)", tg.sent[0]["text"])
        self.assertIn("reply_markup", tg.sent[0])

    def test_what_control_would_refuse_is_never_written(self):
        for bad, why in ((good(files=[{"path": "scripts/install-timers.sh", "content": "x"}]), "hanya boleh mengubah"),
                         (good(change_type="credential"), "tidak berisi file"),
                         (good(summary="x" * 501), "lebih dari 500")):
            out = self.submit(bad)
            self.assertIn("Usulan TIDAK dikirim", out)
            self.assertIn(why, out)
        self.assertEqual(self.files(), [])

    def test_waiting_and_daily_caps(self):
        for _ in range(MAX_WAITING):
            self.assertIn("terkirim", self.submit(good()))
        self.assertIn("belum diambil control", self.submit(good()))
        for p in self.inbox.iterdir():                  # control takes them
            p.unlink()
        for _ in range(MAX_PER_DAY - MAX_WAITING):
            self.assertIn("terkirim", self.submit(good()))
            for p in self.inbox.iterdir():
                p.unlink()
        self.assertIn(f"sudah {MAX_PER_DAY} usulan dalam 24 jam", self.submit(good()))
        self.now[0] += DAY
        self.assertIn("terkirim", self.submit(good()))

    def test_only_mcp_and_only_with_the_token(self):
        with TestClient(self.app) as c:
            self.assertEqual(c.post("/mcp", json={}).status_code, 401)
            self.assertEqual(c.post("/mcp", json={}, headers={"Authorization": "Bearer " + "x" * 40}).status_code, 401)
            self.assertEqual(c.get("/other").status_code, 404)
            r = c.post("/mcp", headers={"Authorization": f"Bearer {TOKEN}", "Accept": "application/json, text/event-stream"},
                       json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
            self.assertEqual(r.status_code, 200)
            self.assertIn('"submit"', r.text)

    def test_short_tokens_are_refused(self):
        with self.assertRaises(ValueError):
            create_app(str(self.inbox), "short")


if __name__ == "__main__":
    unittest.main()
