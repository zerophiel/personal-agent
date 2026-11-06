"""What a new host needs before its services start: scripts/data-dirs.sh, scripts/secret-gen.sh, scripts/secrets-check.sh and
scripts/make-venv.sh. A fake install stands in for the root-only part: a test user cannot chown to the bots' uids."""
import os
import stat
import subprocess
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
FAKE_INSTALL = """#!/bin/bash
# install -d [-o U] [-g G] [-m M] PATH: records the call, makes the folder with the mode, leaves the owner
printf '%s\\n' "$*" >> "$INSTALL_LOG"
mode=0755
while [ $# -gt 1 ]; do
  case "$1" in
    -d) shift ;;
    -o|-g) shift 2 ;;
    -m) mode=$2; shift 2 ;;
    *) shift ;;
  esac
done
mkdir -p "$1"
chmod "$mode" "$1"
"""


def manifest(name):
    with open(os.path.join(ROOT, "config", name), encoding="utf-8") as f:
        return [line.split() for line in f if line.strip() and not line.startswith("#")]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = self.tmp.name
        self.bin = os.path.join(self.d, "bin")
        os.mkdir(self.bin)
        path = os.path.join(self.bin, "install")
        with open(path, "w", encoding="utf-8") as f:
            f.write(FAKE_INSTALL)
        os.chmod(path, stat.S_IRWXU)
        self.data = os.path.join(self.d, "data")
        self.secrets = os.path.join(self.d, "secrets")
        self.log = os.path.join(self.d, "install.log")

    def run_script(self, name, *args, **env):
        full = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], INSTALL_LOG=self.log,
                    PA_DATA_DIR=self.data, PA_SECRETS_DIR=self.secrets, **env)
        return subprocess.run(["bash", os.path.join(ROOT, "scripts", name), *args], env=full, capture_output=True,
                              text=True, timeout=30)

    def calls(self):
        with open(self.log, encoding="utf-8") as f:
            return f.read().splitlines()

    def write(self, path, body="x", mode=0o444):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        os.chmod(path, mode)


class DataDirs(Base):
    def test_each_folder_gets_its_owner_and_mode(self):
        done = self.run_script("data-dirs.sh")
        self.assertEqual(done.returncode, 0, done.stderr)
        calls = self.calls()
        self.assertEqual(calls[0], f"-d -o 0 -g 0 -m 0700 {self.data}")
        for path, uid, gid, mode in manifest("data.manifest"):
            self.assertIn(f"-d -o {uid} -g {gid} -m {mode} {self.data}/{path}", calls)
            self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.data, path)).st_mode), int(mode, 8), path)
            self.assertIn(f"{self.data}/{path} ", done.stdout)

    def test_the_live_owners_stay_what_they_are(self):
        # make deploy runs this on the running host, and install -d resets the owner and mode of a folder that exists
        rows = {row[0]: tuple(row[1:]) for row in manifest("data.manifest")}
        self.assertEqual(rows["vault-tools"], ("10001", "10001", "0700"))
        self.assertEqual(rows["ingest"], ("10002", "10002", "0755"))
        self.assertEqual(rows["ingest-state"], ("10002", "10002", "0755"))
        self.assertEqual(rows["hermes-vault"], ("10000", "10000", "0700"))
        self.assertEqual(rows["applier"], ("0", "0", "0700"))
        self.assertEqual(rows["applier/outcome"], ("0", "0", "0755"))

    def test_a_folder_comes_before_those_inside_it(self):
        order = [row[0] for row in manifest("data.manifest")]
        self.assertLess(order.index("applier"), order.index("applier/outcome"))

    def test_nothing_in_a_folder_is_touched_and_the_root_stays(self):
        self.write(os.path.join(self.data, "vault-tools", "ledger.db"), "isi", 0o644)
        os.chmod(self.data, 0o755)
        self.assertEqual(self.run_script("data-dirs.sh").returncode, 0)
        with open(os.path.join(self.data, "vault-tools", "ledger.db"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "isi")
        self.assertEqual(stat.S_IMODE(os.stat(self.data).st_mode), 0o755)
        self.assertNotIn(f"-d -o 0 -g 0 -m 0700 {self.data}", self.calls())


class SecretGen(Base):
    def test_the_payee_key_is_not_replaced_on_a_host_that_lost_it(self):
        done = self.run_script("secret-gen.sh", "vault_tools_key", "key")
        self.assertEqual(done.returncode, 1)
        self.assertIn("unreadable", done.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.secrets, "vault_tools_key")))

    def test_the_first_install_may_make_it(self):
        done = self.run_script("secret-gen.sh", "vault_tools_key", "key", "--first-install")
        self.assertEqual(done.returncode, 0, done.stderr)
        path = os.path.join(self.secrets, "vault_tools_key")
        with open(path, encoding="utf-8") as f:
            self.assertEqual(len(f.read()), 44)   # 32 bytes in base64
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o444)

    def test_the_first_install_never_overwrites(self):
        self.write(os.path.join(self.secrets, "vault_tools_key"), "kunci-lama")
        done = self.run_script("secret-gen.sh", "vault_tools_key", "key", "--first-install")
        self.assertEqual(done.returncode, 1)
        with open(os.path.join(self.secrets, "vault_tools_key"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "kunci-lama")

    def test_a_token_needs_nothing_more(self):
        done = self.run_script("secret-gen.sh", "vault_tools_mcp_token", "token")
        self.assertEqual(done.returncode, 0, done.stderr)
        with open(os.path.join(self.secrets, "vault_tools_mcp_token"), encoding="utf-8") as f:
            self.assertRegex(f.read(), r"^[0-9a-f]{64}$")

    def test_a_name_with_other_characters_is_refused(self):
        self.assertEqual(self.run_script("secret-gen.sh", "../jahat", "token").returncode, 1)
        self.assertFalse(os.path.exists(self.log))


class SecretsCheck(Base):
    VALUE = "nilai-rahasia-uji"

    def all_secrets(self, zones=("vault", "front", "control", "jobs", "host")):
        for name, _, zone, mode in manifest("secrets.manifest"):
            if zone in zones:
                self.write(os.path.join(self.secrets, name), self.VALUE, int(mode, 8))

    def check(self):
        return self.run_script("secrets-check.sh")

    def test_a_whole_host_passes_with_comms_not_started(self):
        self.all_secrets()
        done = self.check()
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("secrets: 14 in order, 0 to fix; comms zone, not started: 7 absent", done.stdout)
        self.assertNotIn(self.VALUE, done.stdout + done.stderr)

    def test_each_missing_secret_says_how_to_make_it(self):
        self.all_secrets()
        for name, words in (("telegram_vault_token", "make secret-set NAME=telegram_vault_token"),
                            ("vault_tools_mcp_token", "make secret-gen NAME=vault_tools_mcp_token TYPE=token"),
                            ("vault_tools_key", "make restore brings it back"), ("pdf_passwords", "make pdf-passwords"),
                            ("gmail_ingest_token", "scripts/gmail-renew.sh"), ("gmail_ingest_client", "docs/GMAIL_OAUTH.md"),
                            ("restic.env", "scripts/backup.sh")):
            with self.subTest(name=name):
                path = os.path.join(self.secrets, name)
                mode = stat.S_IMODE(os.stat(path).st_mode)
                os.remove(path)
                done = self.check()
                self.assertEqual(done.returncode, 1)
                self.assertIn(f"missing: {name} (", done.stdout)
                self.assertIn(words, done.stdout)
                self.write(path, self.VALUE, mode)

    def test_an_empty_file_is_a_missing_secret(self):
        self.all_secrets()
        path = os.path.join(self.secrets, "notion_token")
        os.chmod(path, 0o644)
        self.write(path, "", 0o444)
        done = self.check()
        self.assertEqual(done.returncode, 1)
        self.assertIn("missing: notion_token", done.stdout)

    def test_a_folder_named_as_a_secret_is_a_missing_secret(self):
        self.all_secrets()
        path = os.path.join(self.secrets, "notion_token")
        os.remove(path)
        os.mkdir(path)
        os.chmod(path, 0o444)
        self.addCleanup(os.chmod, path, 0o755)
        done = self.check()
        self.assertEqual(done.returncode, 1)
        self.assertIn("missing: notion_token", done.stdout)

    def test_a_wrong_mode_fails_and_says_the_fix(self):
        # file secrets keep their mode inside a container, so 0600 root means a service that cannot read its token
        self.all_secrets()
        path = os.path.join(self.secrets, "telegram_control_token")
        os.chmod(path, 0o600)
        done = self.check()
        self.assertEqual(done.returncode, 1)
        self.assertIn(f"wrong mode: telegram_control_token is 600 (sudo chmod 0444 {path})", done.stdout)

    def test_restic_env_stays_root_only(self):
        self.all_secrets()
        os.chmod(os.path.join(self.secrets, "restic.env"), 0o644)
        done = self.check()
        self.assertEqual(done.returncode, 1)
        self.assertIn("wrong mode: restic.env is 644", done.stdout)

    def test_a_secret_nobody_knows_is_named_and_does_not_fail(self):
        self.all_secrets()
        self.write(os.path.join(self.secrets, "punya_siapa"), self.VALUE)
        done = self.check()
        self.assertEqual(done.returncode, 0)
        self.assertIn("note: punya_siapa is not in config/secrets.manifest", done.stdout)

    def test_comms_may_be_there_with_its_mode_checked(self):
        self.all_secrets(zones=("vault", "front", "control", "jobs", "host", "comms"))
        done = self.check()
        self.assertEqual(done.returncode, 0)
        self.assertIn("21 in order, 0 to fix; comms zone, not started: 0 absent", done.stdout)

    def test_a_hermes_env_key_is_answered_by_name_alone(self):
        self.all_secrets()
        home = os.path.join(self.data, "hermes-vault")
        self.write(os.path.join(home, ".env"), f"TELEGRAM_BOT_TOKEN={self.VALUE}\n  export ANTHROPIC_API_KEY = {self.VALUE}\n", 0o600)
        done = self.check()
        self.assertEqual(done.returncode, 0)
        self.assertIn("note: hermes-vault/.env sets TELEGRAM_BOT_TOKEN and wins over the rendered env", done.stdout)
        self.assertIn("note: hermes-vault/.env sets ANTHROPIC_API_KEY", done.stdout)
        self.assertNotIn(self.VALUE, done.stdout + done.stderr)

    def test_the_fix_it_prints_removes_exactly_that_line(self):
        self.all_secrets()
        path = os.path.join(self.data, "hermes-front", ".env")
        self.write(path, f"# TELEGRAM_BOT_TOKEN=contoh\nTELEGRAM_BOT_TOKEN={self.VALUE}\nTELEGRAM_BOT_TOKEN_LAIN=ada\nX=1\n", 0o600)
        done = self.check()
        (line,) = [x for x in done.stdout.splitlines() if "TELEGRAM_BOT_TOKEN" in x]
        command = line.split("rendered env; after rotating that token: sudo ")[1]
        self.assertEqual(subprocess.run(command, shell=True, check=False).returncode, 0)
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), "# TELEGRAM_BOT_TOKEN=contoh\nTELEGRAM_BOT_TOKEN_LAIN=ada\nX=1\n")

    def test_a_comment_in_a_hermes_env_is_no_answer(self):
        self.all_secrets()
        self.write(os.path.join(self.data, "hermes-vault", ".env"), "# TELEGRAM_BOT_TOKEN=contoh\n#ANTHROPIC_API_KEY=x\n", 0o600)
        done = self.check()
        self.assertNotIn("wins over", done.stdout)

    def test_every_manifest_mode_is_what_the_scripts_set(self):
        for name, how, _, mode in manifest("secrets.manifest"):
            self.assertEqual(mode, "0600" if how == "hand" else "0444", name)


class Venv(unittest.TestCase):
    def test_it_refuses_a_folder_inside_the_repo(self):
        done = subprocess.run(["bash", os.path.join(ROOT, "scripts", "make-venv.sh"), os.path.join(ROOT, "venv")],
                              capture_output=True, text=True, timeout=30)
        self.assertEqual(done.returncode, 1)
        self.assertIn("outside the repo", done.stderr)
        self.assertFalse(os.path.exists(os.path.join(ROOT, "venv")))


if __name__ == "__main__":
    unittest.main()
