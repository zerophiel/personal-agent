import importlib.util
import os
import threading
import unittest
from types import SimpleNamespace

_path = os.path.join(os.path.dirname(__file__), "..", "plugins", "cardguard", "__init__.py")
_spec = importlib.util.spec_from_file_location("cardguard", _path)
cg = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cg)


def ev(text, mid=1):
    return SimpleNamespace(text=text, message_id=mid)


class CardGuard(unittest.TestCase):
    def test_rewrites_spaced_and_plain(self):
        for raw in ("4111 1111 1111 1111", "4111111111111111", "4111-1111-1111-1111"):
            out = cg.on_inbound(ev(f"kartu {raw} ok"))
            self.assertEqual(out, {"action": "rewrite", "text": "kartu [[CARD:****1111]] ok"})

    def test_plain_text_untouched(self):
        self.assertIsNone(cg.on_inbound(ev("gaji Rp 10000000 masuk")))
        self.assertIsNone(cg.on_inbound(ev("ref 4111111111111112")))  # fails Luhn
        self.assertIsNone(cg.on_inbound(ev(None)))

    def test_delete_only_private_chats(self):
        calls = []
        done = threading.Event()

        def deleter(chat, mid):
            calls.append((chat, mid))
            done.set()

        dm = SimpleNamespace(message_id=2, source=SimpleNamespace(chat_type="dm", chat_id=99))
        cg._delete_async(dm, deleter)
        self.assertTrue(done.wait(2))
        self.assertEqual(calls, [(99, 2)])
        grp = SimpleNamespace(message_id=3, source=SimpleNamespace(chat_type="group", chat_id=-5))
        cg._delete_async(grp, deleter)
        no_id = SimpleNamespace(message_id=None, source=SimpleNamespace(chat_type="dm", chat_id=99))
        cg._delete_async(no_id, deleter)
        threading.Event().wait(0.2)
        self.assertEqual(calls, [(99, 2)])

    def test_fail_closed_on_error(self):
        class Boom:
            message_id = 9
            @property
            def text(self):
                raise RuntimeError("boom")
        self.assertEqual(cg.on_inbound(Boom()), {"action": "skip"})


if __name__ == "__main__":
    unittest.main()
