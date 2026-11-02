import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.parse
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from brokers import gcal, gmail  # noqa: E402
from brokers.common import (TOKEN_URL, Budget, GoogleError, GoogleSession, TokenError, clean, html_to_text,  # noqa: E402
                            mask_numbers, one_address, one_line, reply)
from fakes import CLIENT, addr, card  # noqa: E402

try:
    import starlette  # noqa: F401  (brokers.serve, which each broker's main() imports, needs it)
    HAVE_SERVER = True
except ImportError:  # system python without mcp/starlette: run these in a venv that has them
    HAVE_SERVER = False

SCOPE = "https://www.googleapis.com/auth/gmail.modify"


class Cleaning(unittest.TestCase):
    def test_links_go_and_bare_domains_are_defanged(self):
        self.assertEqual(clean("Klik https://evil.example/a?b=1 atau www.evil.example sekarang, lalu buka evil.example",
                               300), "Klik [tautan] atau [tautan] sekarang, lalu buka evil[.]example")
        self.assertEqual(clean("tulis ke mailto:x lalu ftp://y", 100), "tulis ke [tautan] lalu [tautan]")

    def test_card_account_and_long_numbers_are_masked(self):
        c = card()
        not_luhn = c[:-1] + str((int(c[-1]) + 1) % 10)
        cases = ((f"kartu {c} ya", "kartu [nomor kartu] ya"),
                 ("kartu " + " ".join(c[i:i + 4] for i in range(0, 16, 4)), "kartu [nomor kartu]"),
                 (f"kode {not_luhn}", "kode [angka]"),
                 ("VA " + "-".join(("0812", "3456", "7890")), "VA [nomor]"),
                 ("ref " + "7" * 10, "ref [angka]"),
                 ("kartu " + "".join(chr(0xFF10 + int(d)) for d in c), "kartu [nomor kartu]"))   # full-width digits
        for raw, want in cases:
            self.assertEqual(clean(raw, 200), want)
        self.assertEqual(mask_numbers(f"bayar {c}"), "bayar [nomor kartu]")

    def test_amounts_dates_and_short_codes_stay(self):
        text = "Rp 1.250.000 pada 2026-11-03 jam 09:00, kode 123456"
        self.assertEqual(clean(text, 200), text)

    def test_hidden_characters_go_and_whitespace_is_tidied(self):
        raw = "a" + chr(0x200B) + "b" + chr(0x202E) + "c" + chr(0xFEFF) + chr(0x07) + "d \t e\n\n\n\n f "
        self.assertEqual(clean(raw, 100), "abcd e\n\nf")
        self.assertEqual(clean("x" * 50, 10), "x" * 9 + "…")

    def test_html_becomes_text_without_scripts_styles_or_comments(self):
        raw = ("<html><head><title>judul</title><style>p{color:red}</style></head><body><p>Halo&nbsp;Budi&amp;Ani</p>"
               "<script>alert(1)</script><!-- tersembunyi --><div>baris 2<br>baris 3</div></body></html>")
        self.assertEqual(clean(html_to_text(raw), 200), "Halo Budi&Ani\nbaris 2\nbaris 3")

    def test_one_line_and_one_address(self):
        self.assertEqual(one_line("Re: hai\r\nBcc: x", 200), "Re: hai Bcc: x")
        self.assertEqual(len(one_line("x" * 300)), 200)
        self.assertEqual(one_address(f"Budi <{addr('Budi')}>"), ("Budi", addr("budi")))
        for value in (f"{addr('a')}, {addr('b')}", "bukan alamat", ""):
            self.assertEqual(one_address(value), ("", ""))


class FakeToken:
    def __init__(self, scope=SCOPE):
        self.scope, self.status, self.api_status, self.calls, self.refresh_tokens = scope, 200, 200, [], []

    def __call__(self, method, url, data, headers):
        self.calls.append((url, headers))
        if url != TOKEN_URL:
            return self.api_status, b'{"ok": true}'
        self.refresh_tokens.append(urllib.parse.parse_qs(data.decode())["refresh_token"][0])
        if self.status != 200:
            return self.status, b'{"error": "invalid_grant"}' if self.status == 400 else b'{"error": "x"}'
        n = sum(1 for u, _ in self.calls if u == TOKEN_URL)
        return 200, json.dumps({"access_token": f"at{n}", "expires_in": 3600, "scope": self.scope}).encode()


class Session(unittest.TestCase):
    def session(self, fake, scopes=(SCOPE,), clock=lambda: 0.0):
        return GoogleSession(CLIENT, {"refresh_token": "rt", "scopes": list(scopes)}, [SCOPE], http=fake, clock=clock)

    def test_one_refresh_until_the_access_token_nears_its_end(self):
        now, fake = [0.0], FakeToken()
        s = self.session(fake, clock=lambda: now[0])
        s.call("GET", "https://api.example/a")
        s.call("GET", "https://api.example/b")
        now[0] = 3600 - 30
        s.call("GET", "https://api.example/c")
        self.assertEqual([u for u, _ in fake.calls].count(TOKEN_URL), 2)
        self.assertEqual([h["Authorization"] for u, h in fake.calls if u != TOKEN_URL],
                         ["Bearer at1", "Bearer at1", "Bearer at2"])

    def test_a_refused_refresh_token_is_a_token_error_and_nothing_else_is(self):
        fake = FakeToken()
        fake.status = 400
        with self.assertRaises(TokenError):
            self.session(fake).access_token()
        fake.status = 500
        with self.assertRaises(GoogleError) as cm:
            self.session(fake).access_token()
        self.assertNotIsInstance(cm.exception, TokenError)

    def test_a_token_for_other_scopes_is_refused(self):
        for scopes in ((), (SCOPE, "https://www.googleapis.com/auth/gmail.send"),
                       ("https://www.googleapis.com/auth/gmail.readonly",)):
            with self.assertRaises(GoogleError):
                self.session(FakeToken(), scopes)
        with self.assertRaises(GoogleError):          # granted more on refresh than the token file says
            self.session(FakeToken(scope=f"{SCOPE} https://mail.google.com/")).access_token()

    def test_api_failures_carry_their_status(self):
        fake = FakeToken()
        fake.api_status = 403
        with self.assertRaises(GoogleError) as cm:
            self.session(fake).call("GET", "https://api.example/a")
        self.assertEqual(cm.exception.status, 403)

    def test_a_renewed_token_is_used_from_the_next_refresh(self):
        now, fake, files = [0.0], FakeToken(), [{"refresh_token": "rt1", "scopes": [SCOPE]}]
        s = GoogleSession(CLIENT, lambda: files[-1], [SCOPE], http=fake, clock=lambda: now[0])
        s.access_token()
        files.append({"refresh_token": "rt2", "scopes": [SCOPE]})       # gmail-renew.sh rewrote the file
        s.access_token()                                                # the access token still holds: no refresh
        now[0] = 3600
        s.access_token()
        self.assertEqual(fake.refresh_tokens, ["rt1", "rt2"])

    def test_a_token_file_being_rewritten_keeps_the_token_read_last(self):
        now, fake, files = [0.0], FakeToken(), [{"refresh_token": "rt1", "scopes": [SCOPE]}]

        def load():
            if isinstance(files[-1], Exception):
                raise files[-1]
            return files[-1]

        s = GoogleSession(CLIENT, load, [SCOPE], http=fake, clock=lambda: now[0])
        for broken in (ValueError("empty or cut short"), OSError("unreadable"), {}, [], {"scopes": [SCOPE]}):
            files.append(broken)
            now[0] += 3600
            s.access_token()
        self.assertEqual(fake.refresh_tokens, ["rt1"] * 5)

    def test_a_renewed_token_for_other_scopes_is_refused(self):
        now, fake, files = [0.0], FakeToken(), [{"refresh_token": "rt1", "scopes": [SCOPE]}]
        s = GoogleSession(CLIENT, lambda: files[-1], [SCOPE], http=fake, clock=lambda: now[0])
        s.access_token()
        files.append({"refresh_token": "rt2", "scopes": [SCOPE, "https://www.googleapis.com/auth/gmail.send"]})
        now[0] = 3600
        with self.assertRaises(GoogleError):
            s.access_token()
        self.assertEqual(fake.refresh_tokens, ["rt1"])

    @unittest.skipUnless(HAVE_SERVER, "mcp/starlette not installed")
    def test_each_broker_reads_its_token_file_again(self):
        from brokers import serve

        for module, name in ((gmail, "gmail_comms_token"), (gcal, "calendar_comms_token")):
            with self.subTest(name), tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"SECRETS_DIR": d}):
                now, fake, made = [0.0], FakeToken(scope=" ".join(module.SCOPES)), []

                def put(file, value):
                    with open(os.path.join(d, file), "w", encoding="utf-8") as f:
                        f.write(value if isinstance(value, str) else json.dumps(value))

                def session(*args):
                    made.append(GoogleSession(*args, http=fake, clock=lambda: now[0]))
                    return made[-1]

                put("google_comms_client", CLIENT)
                put(name, {"refresh_token": "rt1", "scopes": list(module.SCOPES)})
                put(name.split("_")[0] + "_broker_mcp_token", "t" * 64)
                with mock.patch.object(module, "GoogleSession", session), \
                        mock.patch.object(module, "create_app", lambda *a, **k: None), \
                        mock.patch.object(serve, "run", lambda app: None):
                    module.main()
                made[0].access_token()
                put(name, {"refresh_token": "rt2", "scopes": list(module.SCOPES)})   # renewed on the VPS
                now[0] = 3600
                made[0].access_token()
                self.assertEqual(fake.refresh_tokens, ["rt1", "rt2"])


class Replies(unittest.TestCase):
    @staticmethod
    def raising(e):
        def fn():
            raise e
        return fn

    def test_failures_become_one_short_line(self):
        def run(fn):
            return json.loads(reply(fn, "Gmail", "perbarui token", "tidak ada"))

        self.assertEqual(run(lambda: {"hasil": 1}), {"hasil": 1})
        self.assertEqual(run(self.raising(TokenError("invalid_grant", 400))), {"galat": "perbarui token"})
        self.assertEqual(run(self.raising(GoogleError("GET -> 404", 404))), {"galat": "tidak ada"})
        self.assertIn("GET -> 500", run(self.raising(GoogleError("GET -> 500", 500)))["galat"])
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = run(self.raising(KeyError("isi email rahasia")))
        self.assertIn("gagal memproses", out["galat"])
        self.assertNotIn("rahasia", json.dumps(out) + err.getvalue())
        self.assertIn("KeyError", err.getvalue())

    def test_the_daily_budget_rolls(self):
        now = [0.0]
        b = Budget(2, lambda: now[0])
        self.assertEqual([b.take(), b.take(), b.take()], [True, True, False])
        now[0] = 86_399
        self.assertFalse(b.take())
        now[0] = 86_400
        self.assertTrue(b.take())


if __name__ == "__main__":
    unittest.main()
