import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from control import handle, is_authorized  # noqa: E402

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


if __name__ == "__main__":
    unittest.main()
