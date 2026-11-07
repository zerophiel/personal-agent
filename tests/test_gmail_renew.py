import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPT = os.path.join(ROOT, "scripts", "gmail-renew.sh")
NEW = {"refresh_token": "new-test-value", "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
       "token_uri": "https://oauth2.googleapis.com/token", "client_id": "test-client-a",
       "issued_at": "2026-11-02T03:00:00+00:00"}
OTHER = dict(NEW, client_id="test-client-b")       # the same token, minted with another OAuth client
OLD = '{"refresh_token": "old-test-value", "issued_at": "2026-10-27T06:23:31+00:00"}'

# Stands in for ~/.venv-gmail/bin/python: the import check passes, and "running gmail-auth.py" notes its arguments and
# prints what MODE says.
FAKE_PY = """#!/bin/bash
[ "$1" = "-c" ] && exit 0
printf '%s\\n' "$@" > "$ARGS"
case "$MODE" in
  ok) printf '%s' '""" + json.dumps(NEW) + """' ;;
  other) printf '%s' '""" + json.dumps(OTHER) + """' ;;
  cancel) echo "login dibatalkan" >&2; exit 1 ;;
  partial) printf '%s' '{"scopes": []}' ;;
esac
"""
# Stands in for ssh to the VPS: runs the remote command string with bash here, without sudo, and leaves a mark.
FAKE_SSH = """#!/bin/bash
printf '%s' "$1" > "$MARK"
cmd="$2"
exec bash -c "${cmd#sudo -n }"
"""


class Renew(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.token = os.path.join(self.d, "gmail_ingest_token")
        with open(self.token, "w") as f:
            f.write(OLD)
        self.client = os.path.join(self.d, "client.json")
        with open(self.client, "w") as f:
            f.write("{}")
        bin_ = os.path.join(self.d, "bin")
        os.mkdir(bin_)
        for name, body in (("python", FAKE_PY), ("ssh", FAKE_SSH)):
            p = os.path.join(bin_, name)
            with open(p, "w") as f:
                f.write(body)
            os.chmod(p, stat.S_IRWXU)
        self.mark = os.path.join(self.d, "ssh-called")
        self.args = os.path.join(self.d, "auth-args")
        self.env = dict(os.environ, PATH=bin_ + os.pathsep + os.environ["PATH"], GMAIL_PY=os.path.join(bin_, "python"),
                        GMAIL_RENEW_DIR=self.d, GMAIL_RENEW_VPS="vps", MARK=self.mark, ARGS=self.args)

    def run_renew(self, mode, client=None, name=None):
        argv = ["bash", SCRIPT, client or self.client] + ([name] if name else [])
        return subprocess.run(argv, env=dict(self.env, MODE=mode), capture_output=True, text=True, timeout=30)

    def auth_args(self):
        """What gmail-auth.py was given."""
        with open(self.args) as f:
            script, *args = f.read().splitlines()
        self.assertEqual(os.path.basename(script), "gmail-auth.py")
        return args

    def test_new_token_replaces_old_in_place(self):
        inode = os.stat(self.token).st_ino
        r = self.run_renew("ok")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.load(open(self.token)), NEW)
        self.assertEqual(os.stat(self.token).st_ino, inode)          # compose mounts the file: the inode stays
        self.assertFalse(os.path.exists(self.token + ".new"))
        self.assertIn("Token Gmail di VPS diperbarui", r.stderr)
        self.assertEqual(self.auth_args(), [self.client, "gmail_ingest_token"])   # the default is the ingest token
        self.assertNotIn("new-test-value", r.stdout + r.stderr)     # the token is never printed

    def test_the_address_comes_from_the_one_address_file(self):
        del self.env["GMAIL_RENEW_VPS"]
        self.assertEqual(self.run_renew("ok").returncode, 0)
        with open(os.path.join(ROOT, "config", "vps.env"), encoding="utf-8") as f:
            vps = dict(line.strip().split("=", 1) for line in f if "=" in line and not line.startswith("#"))
        with open(self.mark, encoding="utf-8") as f:
            self.assertEqual(f.read(), f"{vps['VPS_USER']}@{vps['VPS_HOST']}")

    def test_cancelled_login_keeps_old_token(self):
        r = self.run_renew("cancel")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(open(self.token).read(), OLD)
        self.assertFalse(os.path.exists(self.token + ".new"))
        self.assertIn("Token lama tetap dipakai", r.stderr)

    def test_incomplete_token_keeps_old_token(self):
        r = self.run_renew("partial")
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(open(self.token).read(), OLD)
        self.assertFalse(os.path.exists(self.token + ".new"))

    def test_first_token_is_created_read_only(self):
        os.remove(self.token)
        r = self.run_renew("ok")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.load(open(self.token)), NEW)
        self.assertEqual(stat.S_IMODE(os.stat(self.token).st_mode), 0o444)

    def test_missing_client_file_stops_before_ssh(self):
        r = self.run_renew("ok", client=os.path.join(self.d, "nope.json"))
        self.assertEqual(r.returncode, 2)
        self.assertFalse(os.path.exists(self.mark))
        self.assertEqual(open(self.token).read(), OLD)

    def test_a_comms_token_goes_to_its_own_file(self):
        for name, label in (("gmail_comms_token", "Token Gmail comms"), ("calendar_comms_token", "Token Kalender comms")):
            with self.subTest(name=name):
                r = self.run_renew("ok", name=name)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(self.auth_args(), [self.client, name])        # gmail-auth.py mints that token's scope
                path = os.path.join(self.d, name)
                self.assertEqual(json.load(open(path)), NEW)
                self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o444)
                self.assertIn(f"{label} di VPS diperbarui", r.stderr)
                self.assertEqual(open(self.token).read(), OLD)                 # the ingest token is left alone

    def test_a_token_minted_with_another_client_keeps_the_old_one(self):
        # e.g. the comms client given without a token name: the VPS could not refresh that token
        for name, client in (("gmail_ingest_token", "gmail_ingest_client"),
                             ("gmail_comms_token", "google_comms_client"),
                             ("calendar_comms_token", "google_comms_client")):
            with self.subTest(name=name):
                path = os.path.join(self.d, name)
                with open(path, "w") as f:
                    f.write(OLD)
                with open(os.path.join(self.d, client), "w") as f:
                    json.dump({"installed": {"client_id": OTHER["client_id"]}}, f)
                r = self.run_renew("ok", name=name)
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("client OAuth lain", r.stderr)
                self.assertIn("Token lama tetap dipakai", r.stderr)
                self.assertEqual(open(path).read(), OLD)
                self.assertFalse(os.path.exists(path + ".new"))
                r = self.run_renew("other", name=name)          # minted with the client the VPS holds for it
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(json.load(open(path)), OTHER)

    def test_an_unknown_name_stops_before_ssh(self):
        for name in ("vault_tools_key", "../gmail_ingest_token", "gmail_ingest_token.new"):
            with self.subTest(name=name):
                r = self.run_renew("ok", name=name)
                self.assertEqual(r.returncode, 2)
                self.assertIn("tidak dikenal", r.stderr)
                self.assertFalse(os.path.exists(self.mark))
                self.assertFalse(os.path.exists(self.args))                    # gmail-auth.py never ran
        self.assertEqual(open(self.token).read(), OLD)


class Scopes(unittest.TestCase):
    def test_each_token_asks_for_the_scope_its_reader_uses(self):
        spec = importlib.util.spec_from_file_location("gmail_auth", os.path.join(ROOT, "scripts", "gmail-auth.py"))
        auth = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(auth)                    # loads without google_auth_oauthlib (main() imports it)
        sys.path.insert(0, os.path.join(ROOT, "services", "comms-brokers"))
        try:
            from brokers import gcal, gmail                # the scopes come without mcp (the servers import it)
        finally:
            sys.path.pop(0)
        self.assertEqual(auth.SCOPES, {"gmail_ingest_token": ["https://www.googleapis.com/auth/gmail.readonly"],
                                       "gmail_comms_token": list(gmail.SCOPES),
                                       "calendar_comms_token": list(gcal.SCOPES)})
        self.assertEqual(set(auth.ASK), set(auth.SCOPES))
        with open(SCRIPT, encoding="utf-8") as f:            # the names gmail-renew.sh accepts are these, no other
            self.assertEqual(sorted(re.findall(r"^  (\w+)\)", f.read(), re.M)), sorted(auth.SCOPES))


if __name__ == "__main__":
    unittest.main()
