"""cardblock (front): a message holding a card number is dropped before dispatch; the detection equals vault's cardguard."""
import importlib.util
import os
import threading
import time
import unittest
from types import SimpleNamespace
from unittest import mock

HERE = os.path.dirname(__file__)


def load(name, *parts):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, *parts))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


cb = load("cardblock", "..", "plugins", "cardblock", "__init__.py")
OWNER = "1001"
CARD = "4111 1111 1111 1111"   # the public Visa test number (Luhn-valid)
DROPPED = {"action": "skip", "reason": "cardblock"}


def ev(text, user_id=OWNER, chat_type="dm", mid=7):
    return SimpleNamespace(text=text, message_id=mid,
                           source=SimpleNamespace(chat_type=chat_type, chat_id=user_id, user_id=user_id))


class CardBlock(unittest.TestCase):
    def setUp(self):
        self.calls, self.sent = [], threading.Event()
        env = mock.patch.dict(os.environ, {"TELEGRAM_ALLOWED_USERS": OWNER})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(setattr, cb, "_bot", cb._bot)
        cb._bot = self.bot

    def bot(self, method, **params):
        self.calls.append((method, params))
        if method == "sendMessage":
            self.sent.set()
            return {"message_id": 8}
        return True

    def quiet(self):
        """No Bot API call was made, nor one started in the background."""
        threading.Event().wait(0.1)
        return not self.calls

    def test_the_owners_message_with_a_card_number_is_dropped_deleted_and_explained(self):
        for text in (f"tolong cek {CARD} ya", "4111-1111-1111-1111", "4111111111111111"):
            self.calls.clear()
            self.sent.clear()
            self.assertEqual(cb.on_inbound(ev(text)), DROPPED, text)
            self.assertTrue(self.sent.wait(2), text)
            self.assertEqual([m for m, _ in self.calls], ["deleteMessage", "sendMessage"], text)
            self.assertEqual(self.calls[0][1], {"chat_id": OWNER, "message_id": 7})
            self.assertEqual(self.calls[1][1]["chat_id"], OWNER)
            self.assertEqual(self.calls[1][1]["text"], cb.NOTICE)

    def test_anyone_else_is_dropped_without_a_word(self):
        # Hermes runs this hook before its own sender check: a stranger, a group or a sender without an id gets nothing
        for e in (ev(CARD, user_id="2002"), ev(CARD, chat_type="group"), ev(CARD, user_id=None)):
            self.assertEqual(cb.on_inbound(e), DROPPED)
        self.assertTrue(self.quiet())

    def test_without_an_allowlist_nobody_gets_a_notice_and_the_message_still_drops(self):
        with mock.patch.dict(os.environ, {"TELEGRAM_ALLOWED_USERS": ""}):
            self.assertEqual(cb.on_inbound(ev(CARD)), DROPPED)
        self.assertTrue(self.quiet())

    def test_captions_and_inlined_text_documents_are_checked(self):
        # a photo's caption arrives as event.text; a small text document is inlined as "[Content of <name>]:\n..."
        for text in (f"foto kartu, nomornya {CARD}", f"[Content of kartu.txt]:\nnomor {CARD.replace(' ', '')}\n\nsimpan ya"):
            self.calls.clear()
            self.sent.clear()
            self.assertEqual(cb.on_inbound(ev(text)), DROPPED, text)
            self.assertTrue(self.sent.wait(2), text)

    def test_everything_else_goes_through_untouched(self):
        for text in (None, "", "Berapa kurs dolar hari ini?", "Rp 1.500.000 untuk 3 orang", "telepon 0812-3456-7890",
                     "4111 1111 1111 1112", "tanggal 2026-11-01 jam 09.30", "/start", "resi 12345678901"):
            self.assertIsNone(cb.on_inbound(ev(text)), text)
        self.assertTrue(self.quiet())

    def test_an_error_drops_the_message(self):
        error = {"action": "skip", "reason": "cardblock-error"}
        with mock.patch.object(cb, "find_numbers", side_effect=RuntimeError("boom")):
            self.assertEqual(cb.on_inbound(ev("apa kabar")), error)
        with mock.patch.object(cb, "_owner_ids", side_effect=RuntimeError("boom")):
            self.assertEqual(cb.on_inbound(ev(CARD)), error)
        self.assertTrue(self.quiet())

    def test_telegram_failing_or_slow_never_lets_the_message_through(self):
        release, done = threading.Event(), threading.Event()
        self.addCleanup(release.set)

        def failing(method, **params):
            if method == "sendMessage":
                done.set()
            return None

        def slow(method, **params):
            release.wait(2)
            return failing(method, **params)

        cb._bot = failing
        self.assertEqual(cb.on_inbound(ev(CARD)), DROPPED)
        self.assertTrue(done.wait(2))                          # each background thread ends inside its own test
        done.clear()
        cb._bot = slow
        started = time.monotonic()
        self.assertEqual(cb.on_inbound(ev(CARD)), DROPPED)
        self.assertLess(time.monotonic() - started, 0.5)      # delete + notice run off the dispatch path
        release.set()
        self.assertTrue(done.wait(2))

    def test_the_notice_holds_no_number_and_names_the_vault_bot(self):
        self.assertIn("@danoevault_agent", cb.NOTICE)
        self.assertNotRegex(cb.NOTICE, r"\d")

    def test_only_the_dispatch_hook_is_registered(self):
        hooks = []
        cb.register(SimpleNamespace(register_hook=lambda name, fn: hooks.append((name, fn))))
        self.assertEqual(hooks, [("pre_gateway_dispatch", cb.on_inbound)])


class SameDetectionAsVault(unittest.TestCase):
    """Front's cardblock and vault's cardguard must flag exactly the same numbers and take the same sender as the owner."""

    def test_same_owner_check(self):
        cg = load("cardguard_for_owner_parity", "..", "..", "vault", "plugins", "cardguard", "__init__.py")
        calls = []
        self.addCleanup(setattr, cb, "_bot", cb._bot)
        cb._bot = lambda method, **params: calls.append(method) or True
        cases = [("1001", "dm", "1001"), (1001, "dm", "1001"), ("1002", "dm", "1001"), ("1001", "group", "1001"),
                 (None, "dm", "1001"), ("1001", "dm", " 7, 1001 "), ("1001", "dm", "")]
        for user_id, chat_type, allowed in cases:
            calls.clear()
            event = SimpleNamespace(text=CARD, message_id=7,
                                    source=SimpleNamespace(chat_type=chat_type, chat_id=5, user_id=user_id))
            with mock.patch.dict(os.environ, {"TELEGRAM_ALLOWED_USERS": allowed}):
                self.assertEqual(cb.on_inbound(event), DROPPED)
                threading.Event().wait(0.1)      # cardblock tells the owner from a thread
                self.assertEqual("deleteMessage" in calls, cg._is_owner(event), (user_id, chat_type, allowed))

    def test_parity(self):
        cg = load("cardguard_for_parity", "..", "..", "vault", "plugins", "cardguard", "__init__.py")
        self.assertEqual(cb._CANDIDATE.pattern, cg._CANDIDATE.pattern)
        corpus = [CARD, "4111-1111-1111-1111", "4111 1111 1111 1112", "5500 0000 0000 0004", "340000000000009",
                  "6011000990139424 dan 4111111111111111", "IMEI 490154203237518", "Rp 1.500.000", "0812-3456-7890",
                  "123456789012", "12345678901234567890", "4111 1111 1111 1111 1111", ""]
        for text in corpus:
            self.assertEqual(cb.find_numbers(text), cg.find_numbers(text), text)
        self.assertEqual(cb.find_numbers("IMEI 490154203237518"), ["490154203237518"])   # Luhn also flags an IMEI


if __name__ == "__main__":
    unittest.main()
