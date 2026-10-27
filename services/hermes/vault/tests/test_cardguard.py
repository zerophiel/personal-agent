import importlib.util
import os
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

    def test_fail_closed_on_error(self):
        class Boom:
            message_id = 9
            @property
            def text(self):
                raise RuntimeError("boom")
        self.assertEqual(cg.on_inbound(Boom()), {"action": "skip"})


if __name__ == "__main__":
    unittest.main()
