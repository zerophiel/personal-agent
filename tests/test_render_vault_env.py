"""scripts/render-vault-env.sh: compose refuses to start without this file, and until now only a hand on the VPS made it."""
import os
import re
import stat
import subprocess
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPT = os.path.join(ROOT, "scripts", "render-vault-env.sh")
SECRETS = {"anthropic_vault_key": "test-vault-key", "telegram_vault_token": "test-vault-bot",
           "vault_tools_mcp_token": "test-mcp", "vault_tools_internal_token": "test-internal"}
NAMES = ["ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN", "VAULT_TOOLS_MCP_TOKEN", "VAULT_TOOLS_INTERNAL_TOKEN",
         "TELEGRAM_ALLOWED_USERS", "TELEGRAM_HOME_CHANNEL", "HERMES_SKIP_CONFIG_MIGRATION", "HTTPS_PROXY", "HTTP_PROXY",
         "NO_PROXY", "TZ"]


class Render(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.secrets = os.path.join(self.d.name, "secrets")
        os.mkdir(self.secrets)
        for name, value in SECRETS.items():
            self.put(name, value)
        self.out = os.path.join(self.d.name, "vault.env")

    def put(self, name, value):
        with open(os.path.join(self.secrets, name), "w", encoding="utf-8") as f:
            f.write(value)

    def render(self, owner="4242"):
        env = dict(os.environ, PA_SECRETS_DIR=self.secrets, PA_VAULT_ENV=self.out)
        env.pop("MY_TELEGRAM_ID", None)
        if owner is not None:
            env["MY_TELEGRAM_ID"] = owner
        return subprocess.run(["bash", SCRIPT], env=env, capture_output=True, text=True, timeout=30)

    def rendered(self):
        with open(self.out, encoding="utf-8") as f:
            return dict(line.rstrip("\n").split("=", 1) for line in f)

    def keep_a_last_file(self):
        with open(self.out, "w", encoding="utf-8") as f:
            f.write("YANG_LAMA=1\n")

    def last_file_is_whole(self):
        self.assertEqual(self.rendered(), {"YANG_LAMA": "1"})
        self.assertEqual(os.listdir(self.d.name).count("vault.env.tmp"), 0)

    def test_renders_the_vault_values_for_the_owner_alone(self):
        r = self.render()
        self.assertEqual(r.returncode, 0, r.stderr)
        env = self.rendered()
        self.assertEqual(list(env), NAMES)
        self.assertEqual((env["ANTHROPIC_API_KEY"], env["TELEGRAM_BOT_TOKEN"]), ("test-vault-key", "test-vault-bot"))
        self.assertEqual((env["VAULT_TOOLS_MCP_TOKEN"], env["VAULT_TOOLS_INTERNAL_TOKEN"]), ("test-mcp", "test-internal"))
        self.assertEqual((env["TELEGRAM_ALLOWED_USERS"], env["TELEGRAM_HOME_CHANNEL"]), ("4242", "4242"))
        self.assertEqual((env["HTTPS_PROXY"], env["HTTP_PROXY"]), ("http://squid-vault:3128",) * 2)
        self.assertEqual(stat.S_IMODE(os.stat(self.out).st_mode), 0o600)
        self.assertEqual(os.listdir(self.d.name).count("vault.env.tmp"), 0)
        for value in SECRETS.values():
            self.assertNotIn(value, r.stdout + r.stderr)

    def test_the_owner_comes_from_stack_env_under_sudo(self):
        r = self.render(owner=None)        # sudo drops MY_TELEGRAM_ID; that left a partial file before this guard
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(ROOT, "config", "stack.env"), encoding="utf-8") as f:
            (owner,) = re.findall(r"^MY_TELEGRAM_ID=(\d+)$", f.read(), re.M)
        self.assertEqual(self.rendered()["TELEGRAM_ALLOWED_USERS"], owner)

    def test_a_replaced_file_loses_a_stale_wide_mode(self):
        self.keep_a_last_file()
        with open(self.out + ".tmp", "w", encoding="utf-8") as f:
            f.write("sisa\n")
        os.chmod(self.out + ".tmp", 0o644)
        self.assertEqual(self.render().returncode, 0)
        self.assertEqual(stat.S_IMODE(os.stat(self.out).st_mode), 0o600)

    def test_a_missing_or_empty_secret_stops_before_writing(self):
        self.keep_a_last_file()
        for name in SECRETS:
            for missing in (True, False):
                with self.subTest(name=name, missing=missing):
                    if missing:
                        os.remove(os.path.join(self.secrets, name))
                    else:
                        self.put(name, "")
                    r = self.render()
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(f"missing secret {name}", r.stderr)
                    self.last_file_is_whole()
                    self.put(name, SECRETS[name])

    def test_refuses_an_owner_id_that_is_not_one_number(self):
        self.keep_a_last_file()
        self.assertEqual(self.render(owner="4242,77").returncode, 1)
        self.last_file_is_whole()

    def test_a_folder_named_as_a_secret_is_a_missing_secret(self):
        # Docker makes a folder for a bind source that does not exist; cat on it fails inside printf's argument, which set -e
        # does not see, so without the guard the token would be rendered empty
        self.keep_a_last_file()
        os.remove(os.path.join(self.secrets, "vault_tools_internal_token"))
        os.mkdir(os.path.join(self.secrets, "vault_tools_internal_token"))
        r = self.render()
        self.assertEqual(r.returncode, 1)
        self.assertIn("missing secret vault_tools_internal_token", r.stderr)
        self.last_file_is_whole()

    def test_writes_where_compose_reads_it(self):
        with open(SCRIPT, encoding="utf-8") as f:
            (out,) = re.findall(r"^OUT=\$\{PA_VAULT_ENV:-(\S+)\}$", f.read(), re.M)
        with open(os.path.join(ROOT, "compose/docker-compose.yml"), encoding="utf-8") as f:
            self.assertIn(f"env_file: {out} ", f.read())


if __name__ == "__main__":
    unittest.main()
