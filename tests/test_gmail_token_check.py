import importlib.util
import os
import unittest
from datetime import datetime, timedelta, timezone

_p = os.path.join(os.path.dirname(__file__), "..", "scripts", "gmail-token-check.py")
_s = importlib.util.spec_from_file_location("gtc", _p)
gtc = importlib.util.module_from_spec(_s)
_s.loader.exec_module(gtc)

NOW = datetime(2026, 11, 1, 8, 0, tzinfo=timezone.utc)


def issued(days_ago):
    return (NOW - timedelta(days=days_ago)).isoformat()


class TokenCheck(unittest.TestCase):
    def test_fresh_token_is_silent(self):
        for d in (0, 1, 4.9):
            self.assertIsNone(gtc.message(gtc.days_left(issued(d), NOW)), d)

    def test_warns_in_last_two_days(self):
        msg = gtc.message(gtc.days_left(issued(5.5), NOW))
        self.assertIn("habis dalam 1.5 hari", msg)

    def test_expired(self):
        self.assertIn("SUDAH kedaluwarsa", gtc.message(gtc.days_left(issued(7.1), NOW)))
        self.assertIn("SUDAH kedaluwarsa", gtc.message(gtc.days_left(issued(30), NOW)))

    def test_message_never_contains_token_field_names(self):
        self.assertNotIn("refresh", gtc.message(gtc.days_left(issued(8), NOW)))


if __name__ == "__main__":
    unittest.main()
