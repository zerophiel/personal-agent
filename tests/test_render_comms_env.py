"""scripts/render-comms-env.sh (M4): the comms env file from the secret files, and never another zone's key or bot."""
import os
import re
import stat
import subprocess
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPT = os.path.join(ROOT, "scripts", "render-comms-env.sh")
OWN = {"anthropic_comms_key": "test-comms-key", "telegram_comms_token": "test-comms-bot",
       "gmail_broker_mcp_token": "test-gmail-broker", "calendar_broker_mcp_token": "test-calendar-broker"}
OTHERS = {"anthropic_vault_key": "test-vault-key", "anthropic_front_key": "test-front-key",
          "telegram_vault_token": "test-vault-bot", "telegram_front_token": "test-front-bot",
          "telegram_control_token": "test-control-bot"}
NAMES = {"ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN", "GMAIL_BROKER_MCP_TOKEN", "CALENDAR_BROKER_MCP_TOKEN",
         "TELEGRAM_ALLOWED_USERS", "TELEGRAM_HOME_CHANNEL", "HERMES_SKIP_CONFIG_MIGRATION", "HTTPS_PROXY", "HTTP_PROXY",
         "NO_PROXY", "TZ"}


class Render(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.secrets = os.path.join(self.d, "secrets")
        os.mkdir(self.secrets)
        for name, value in {**OWN, **OTHERS}.items():
            self.put(name, value)
        self.out = os.path.join(self.d, "comms.env")

    def put(self, name, value):
        with open(os.path.join(self.secrets, name), "w") as f:
            f.write(value)

    def render(self, owner="4242"):
        env = dict(os.environ, PA_SECRETS_DIR=self.secrets, PA_COMMS_ENV=self.out, MY_TELEGRAM_ID=owner)
        return subprocess.run(["bash", SCRIPT], env=env, capture_output=True, text=True, timeout=30)

    def rendered(self):
        with open(self.out) as f:
            return dict(line.rstrip("\n").split("=", 1) for line in f)

    def test_renders_the_comms_values_for_the_owner_alone(self):
        r = self.render()
        self.assertEqual(r.returncode, 0, r.stderr)
        env = self.rendered()
        self.assertEqual(set(env), NAMES)                                 # no Google token: the brokers hold those
        self.assertEqual({env[k] for k in ("ANTHROPIC_API_KEY", "TELEGRAM_BOT_TOKEN", "GMAIL_BROKER_MCP_TOKEN",
                                           "CALENDAR_BROKER_MCP_TOKEN")}, set(OWN.values()))
        self.assertEqual((env["ANTHROPIC_API_KEY"], env["TELEGRAM_BOT_TOKEN"]), ("test-comms-key", "test-comms-bot"))
        self.assertEqual((env["TELEGRAM_ALLOWED_USERS"], env["TELEGRAM_HOME_CHANNEL"]), ("4242", "4242"))
        self.assertEqual((env["HTTPS_PROXY"], env["HTTP_PROXY"]), ("http://squid-comms:3128",) * 2)
        self.assertEqual(stat.S_IMODE(os.stat(self.out).st_mode), 0o600)
        for value in OWN.values():                                        # values are never printed
            self.assertNotIn(value, r.stdout + r.stderr)

    def test_every_env_reference_of_the_comms_config_is_rendered(self):
        with open(os.path.join(ROOT, "services/hermes/comms/config.yaml"), encoding="utf-8") as f:
            cfg = f.read()
        refs = set(re.findall(r"\$\{env:(\w+)\}", cfg))
        hosts = set(re.findall(r'url: "http://([\w-]+):', cfg))
        self.assertEqual((refs, hosts), ({"GMAIL_BROKER_MCP_TOKEN", "CALENDAR_BROKER_MCP_TOKEN"},
                                         {"gmail-broker", "calendar-broker"}))
        r = self.render()
        self.assertEqual(r.returncode, 0, r.stderr)
        env = self.rendered()
        self.assertLessEqual(refs, set(env))
        self.assertLessEqual(hosts, set(env["NO_PROXY"].split(",")))     # the brokers are reached directly, not via squid

    def test_writes_where_compose_reads_it(self):
        with open(SCRIPT, encoding="utf-8") as f:
            (out,) = re.findall(r"^OUT=\$\{PA_COMMS_ENV:-(\S+)\}$", f.read(), re.M)
        with open(os.path.join(ROOT, "compose/docker-compose.comms.yml"), encoding="utf-8") as f:
            self.assertEqual(re.findall(r"- path: (\S+)", f.read()), [out])

    def test_refuses_another_zones_key_or_bot(self):
        for own, other in (("anthropic_comms_key", "anthropic_vault_key"), ("anthropic_comms_key", "anthropic_front_key"),
                           ("telegram_comms_token", "telegram_vault_token"),
                           ("telegram_comms_token", "telegram_front_token"),
                           ("telegram_comms_token", "telegram_control_token")):
            with self.subTest(other=other):
                self.put(own, OTHERS[other])
                r = self.render()
                self.assertEqual(r.returncode, 1)
                self.assertIn(f"must not be {other}", r.stderr)
                self.assertFalse(os.path.exists(self.out))
                self.put(own, OWN[own])

    def test_a_missing_or_empty_secret_stops_before_writing(self):
        for name in OWN:
            for missing in (True, False):
                with self.subTest(name=name, missing=missing):
                    if missing:
                        os.remove(os.path.join(self.secrets, name))
                    else:
                        self.put(name, "")
                    r = self.render()
                    self.assertEqual(r.returncode, 1)
                    self.assertIn(f"missing secret {name}", r.stderr)
                    self.assertFalse(os.path.exists(self.out))
                    self.put(name, OWN[name])

    def test_refuses_an_owner_id_that_is_not_one_number(self):
        r = self.render(owner="4242,77")
        self.assertEqual(r.returncode, 1)
        self.assertFalse(os.path.exists(self.out))


if __name__ == "__main__":
    unittest.main()
