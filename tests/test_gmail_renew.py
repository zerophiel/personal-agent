import json
import os
import stat
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "gmail-renew.sh")
NEW = {"refresh_token": "new-test-value", "scopes": ["https://www.googleapis.com/auth/gmail.readonly"],
       "token_uri": "https://oauth2.googleapis.com/token", "issued_at": "2026-11-02T03:00:00+00:00"}
OLD = '{"refresh_token": "old-test-value", "issued_at": "2026-10-27T06:23:31+00:00"}'

# Stands in for ~/.venv-gmail/bin/python: the import check passes, and "running gmail-auth.py" prints what MODE says.
FAKE_PY = """#!/bin/bash
[ "$1" = "-c" ] && exit 0
case "$MODE" in
  ok) printf '%s' '""" + json.dumps(NEW) + """' ;;
  cancel) echo "login dibatalkan" >&2; exit 1 ;;
  partial) printf '%s' '{"scopes": []}' ;;
esac
"""
# Stands in for ssh to the VPS: runs the remote command string with bash here, without sudo, and leaves a mark.
FAKE_SSH = """#!/bin/bash
touch "$MARK"
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
        self.env = dict(os.environ, PATH=bin_ + os.pathsep + os.environ["PATH"], GMAIL_PY=os.path.join(bin_, "python"),
                        GMAIL_RENEW_TOKEN=self.token, GMAIL_RENEW_VPS="vps", MARK=self.mark)

    def run_renew(self, mode, client=None):
        return subprocess.run(["bash", SCRIPT, client or self.client], env=dict(self.env, MODE=mode),
                              capture_output=True, text=True, timeout=30)

    def test_new_token_replaces_old_in_place(self):
        inode = os.stat(self.token).st_ino
        r = self.run_renew("ok")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.load(open(self.token)), NEW)
        self.assertEqual(os.stat(self.token).st_ino, inode)          # compose mounts the file: the inode stays
        self.assertFalse(os.path.exists(self.token + ".new"))
        self.assertIn("diperbarui", r.stderr)
        self.assertNotIn("new-test-value", r.stdout + r.stderr)     # the token is never printed

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


if __name__ == "__main__":
    unittest.main()
