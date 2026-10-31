import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from control import MAX_PENDING, Control, handle, is_authorized, shown, validate  # noqa: E402

OWNER = 1357980587


def msg(uid, chat_type="private", text="/ping"):
    return {"update_id": 1, "message": {"from": {"id": uid}, "chat": {"type": chat_type}, "text": text}}


class AuthTests(unittest.TestCase):
    def test_owner_private_ok(self):
        self.assertTrue(is_authorized(msg(OWNER), OWNER))

    def test_other_user_rejected(self):
        self.assertFalse(is_authorized(msg(42), OWNER))

    def test_owner_in_group_rejected(self):
        self.assertFalse(is_authorized(msg(OWNER, "supergroup"), OWNER))

    def test_callback_checked_too(self):
        cq = {"callback_query": {"from": {"id": 42}, "message": {"chat": {"type": "private"}}}}
        self.assertFalse(is_authorized(cq, OWNER))
        cq["callback_query"]["from"]["id"] = OWNER
        self.assertTrue(is_authorized(cq, OWNER))

    def test_unknown_update_type_rejected(self):
        self.assertFalse(is_authorized({"update_id": 1, "inline_query": {}}, OWNER))


class HandleTests(unittest.TestCase):
    def test_ping(self):
        self.assertEqual(handle(msg(OWNER)), "pong")

    def test_unknown_command_silent(self):
        self.assertIsNone(handle(msg(OWNER, text="hello")))


def proposal(**kw):
    p = {"summary": "Tambah domain cuaca untuk front", "zone": "front", "change_type": "egress_domain",
         "permission_diff": "front boleh ke api.cuaca.example", "risk_notes": "domain publik", "rollback": "hapus barisnya",
         "files": [{"path": "config/squid/front.conf", "content": "acl cuaca dstdomain api.cuaca.example\n"}]}
    p.update(kw)
    return p


class FakeTelegram:
    def __init__(self):
        self.calls, self.fail = [], False

    def call(self, method, **params):
        if self.fail and method == "sendMessage":
            raise OSError("network")
        self.calls.append((method, params))
        return {"message_id": len(self.calls)} if method == "sendMessage" else True

    def sent(self):
        return [p for m, p in self.calls if m == "sendMessage"]


class ValidateTests(unittest.TestCase):
    def test_a_good_proposal_passes_as_is(self):
        self.assertEqual(validate(proposal())["files"][0]["path"], "config/squid/front.conf")
        self.assertEqual(validate(proposal(files=[]))["files"], [])

    def test_bad_proposals_are_refused(self):
        for bad in (proposal(zone="control"), proposal(change_type="deploy"), proposal(summary=" "),
                    proposal(summary="x" * 501), proposal(extra="y"),
                    proposal(files=[{"path": "../etc/passwd", "content": ""}]),
                    proposal(files=[{"path": "/etc/passwd", "content": ""}]),
                    proposal(files=[{"path": "secrets/telegram", "content": ""}]),
                    proposal(files=[{"path": "services/control/control.py", "content": ""}]),
                    proposal(files=[{"path": "a//b", "content": ""}]),
                    proposal(files=[{"path": "a.txt", "content": 1}]), ["not", "a", "dict"]):
            with self.assertRaises(ValueError):
                validate(bad)

    def test_model_text_is_defanged(self):
        t = shown("buka https://evil.example/x atau evil.example, tanya @orang‮\x07", 200)
        self.assertEqual(t, "buka https[:]//evil[.]example/x atau evil[.]example, tanya (at)orang")
        self.assertEqual(shown("x" * 10, 5), "xxxx…")
        self.assertEqual(shown("Rp 1.234.567", 50), "Rp 1.234.567")         # numbers stay as they are

    def test_quiet_hours_are_22_to_6_wib(self):
        from datetime import datetime, timezone
        from control import quiet
        at = lambda h: datetime(2026, 11, 1, (h - 7) % 24, 30, tzinfo=timezone.utc)   # noqa: E731 - WIB hour h
        self.assertEqual([h for h in range(24) if quiet(at(h))], [0, 1, 2, 3, 4, 5, 22, 23])


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        d = Path(tempfile.mkdtemp())
        self.state, self.inbox, self.tg = d / "state", d / "inbox", FakeTelegram()
        self.bot = Control(self.tg, OWNER, self.state, self.inbox)

    def drop(self, name, body):
        (self.inbox / name).write_text(json.dumps(body) if not isinstance(body, str) else body, encoding="utf-8")

    def tap(self, data, message_id=1):
        self.bot.on_update({"update_id": 9, "callback_query": {"id": "cq", "from": {"id": OWNER}, "data": data,
                                                               "message": {"message_id": message_id, "chat": {"type": "private"}}}})

    def nonce(self):
        return json.loads(self.tg.sent()[-1]["reply_markup"])["inline_keyboard"][0][0]["callback_data"][2:]

    def test_a_proposal_is_posted_with_one_time_buttons_and_approved_once(self):
        self.drop("p1.json", proposal())
        self.bot.tick()
        self.assertEqual(list(self.inbox.iterdir()), [])                    # taken out of the inbox
        card = self.tg.sent()[0]
        self.assertIn("Usulan perubahan #1 (zona front, jenis egress_domain)", card["text"])
        self.assertIn("api[.]cuaca[.]example", card["text"])
        self.assertNotIn("parse_mode", card)
        keys = json.loads(card["reply_markup"])["inline_keyboard"][0]
        nonce = keys[0]["callback_data"][2:]
        self.assertEqual((keys[0]["callback_data"], keys[1]["callback_data"]), (f"a:{nonce}", f"r:{nonce}"))
        self.tap(f"a:{nonce}")
        rec = json.loads((self.state / "approved" / "1.json").read_text())
        self.assertEqual((rec["status"], rec["zone"], rec["files"][0]["path"]), ("approved", "front", "config/squid/front.conf"))
        self.assertTrue((self.state / "decided" / "1.json").exists())
        self.assertIn(("editMessageReplyMarkup", {"chat_id": OWNER, "message_id": 1,
                                                  "reply_markup": json.dumps({"inline_keyboard": []})}), self.tg.calls)
        self.assertIn("Usulan #1 DISETUJUI", self.tg.sent()[-1]["text"])
        before = len(self.tg.sent())
        self.tap(f"r:{nonce}")                                               # the second tap, even the other button
        self.assertEqual(len(self.tg.sent()), before)
        self.assertEqual(json.loads((self.state / "approved" / "1.json").read_text())["status"], "approved")
        self.assertEqual(self.tg.calls[-2], ("answerCallbackQuery", {"callback_query_id": "cq",
                                                                      "text": "Sudah diputuskan atau tidak berlaku"}))

    def test_a_rejection_leaves_nothing_for_the_applier(self):
        self.drop("p1.json", proposal())
        self.bot.tick()
        self.tap(f"r:{self.nonce()}")
        self.assertFalse((self.state / "approved").exists())
        self.assertEqual(json.loads((self.state / "decided" / "1.json").read_text())["status"], "rejected")
        self.assertIn("Usulan #1 DITOLAK", self.tg.sent()[-1]["text"])

    def test_forged_or_malformed_buttons_decide_nothing(self):
        self.drop("p1.json", proposal())
        self.bot.tick()
        for data in ("a:" + "0" * 32, "a:short", "x:" + self.nonce(), "", "a:" + self.nonce().upper()):
            self.tap(data)
        self.assertEqual(handle(msg(OWNER, text="/status"), self.bot.store).split(". ")[1],
                         "Usulan menunggu keputusan: 1; disetujui (belum diterapkan, applier belum aktif): 0; ditolak: 0; "
                         "file usulan tidak valid: 0.")

    def test_an_invalid_file_is_recorded_reported_and_never_posted_with_buttons(self):
        self.drop("bad.json", proposal(zone="control"))
        self.drop("broken.json", "{not json")
        self.drop("half.json.tmp", proposal())                              # still being written: left alone
        self.bot.tick()
        self.assertEqual([p.name for p in self.inbox.iterdir()], ["half.json.tmp"])
        self.assertEqual(self.bot.store.counts(), {"pending": 0, "approved": 0, "rejected": 0, "invalid": 2})
        self.assertTrue(all("reply_markup" not in p and "ditolak otomatis" in p["text"] for p in self.tg.sent()))

    def test_links_folders_and_deep_json_are_refused_without_touching_anything_else(self):
        secret = self.state.parent / "secret.json"
        secret.write_text(json.dumps(proposal()), encoding="utf-8")         # a valid proposal, but outside the inbox
        (self.inbox / "link.json").symlink_to(secret)
        (self.inbox / "dir.json").mkdir()
        (self.inbox / "dir.json" / "x").write_text("x")
        self.drop("deep.json", "[" * 100_000 + "]" * 100_000)
        self.drop("good.json", proposal())
        self.bot.tick()
        self.assertEqual(list(self.inbox.iterdir()), [])
        self.assertTrue(secret.exists())                                    # the link went, not its target
        self.assertEqual(self.bot.store.counts(), {"pending": 1, "approved": 0, "rejected": 0, "invalid": 3})
        self.assertEqual(sum("ditolak otomatis" in p["text"] for p in self.tg.sent()), 3)

    def test_a_failed_button_removal_still_reports_the_decision(self):
        self.drop("p1.json", proposal())
        self.bot.tick()
        nonce, call = self.nonce(), self.tg.call

        def edit_fails(method, **params):
            if method == "editMessageReplyMarkup":
                raise OSError("message too old")
            return call(method, **params)
        self.tg.call = edit_fails
        self.tap(f"a:{nonce}")
        self.assertIn("Usulan #1 DISETUJUI", self.tg.sent()[-1]["text"])

    def test_at_most_five_wait_and_the_rest_stay_in_the_inbox(self):
        for i in range(MAX_PENDING + 1):
            self.drop(f"p{i}.json", proposal(summary=f"usulan {i}"))
        self.bot.tick()
        self.assertEqual(self.bot.store.counts()["pending"], MAX_PENDING)
        self.assertEqual([p.name for p in self.inbox.iterdir()], [f"p{MAX_PENDING}.json"])

    def test_a_failed_send_is_posted_at_the_next_tick(self):
        self.drop("p1.json", proposal())
        self.tg.fail = True
        with self.assertRaises(OSError):
            self.bot.tick()
        self.tg.fail = False
        self.bot.tick()
        self.assertEqual(len(self.tg.sent()), 1)
        self.assertIn("Usulan perubahan #1", self.tg.sent()[0]["text"])

    def test_usulan_lists_the_waiting_ones_again_with_their_buttons(self):
        self.bot.on_update(msg(OWNER, text="/usulan"))
        self.assertEqual(self.tg.sent()[-1]["text"], "Tidak ada usulan yang menunggu keputusan.")
        self.drop("p1.json", proposal())
        self.bot.tick()
        first = self.nonce()
        self.bot.on_update(msg(OWNER, text="/usulan"))
        self.assertEqual(self.nonce(), first)
        self.tap(f"a:{first}", message_id=3)
        self.assertEqual(self.bot.store.counts()["approved"], 1)


if __name__ == "__main__":
    unittest.main()
