"""Zone boundaries as the repo states them: compose networks and mounts, and what each Hermes profile may do."""
import os
import re
import unittest

try:
    import yaml
except ImportError:  # the vault-tools venv may lack PyYAML; the system python3 used by `make test` has it
    yaml = None

ROOT = os.path.join(os.path.dirname(__file__), "..")
ZONES = ("vault", "front", "comms")
MCP = {"vault": ("vault_tools",), "front": ("change_proposals",), "comms": ("gmail_broker", "calendar_broker")}
# The applier runs this file on a copy of tests, compose, host, services/hermes and config/squid alone, and refuses a
# change when a test is skipped: nothing here reads another folder (services/comms-brokers tests its own rules).


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return yaml.safe_load(f)


def compose():
    """The main file, the M4 comms file, and what `docker compose -f main -f comms` makes of the two."""
    main, comms = load("compose/docker-compose.yml"), load("compose/docker-compose.comms.yml")
    return main, comms, {k: {**main.get(k, {}), **comms.get(k, {})} for k in ("networks", "services", "secrets")}


def mounts(svc):
    return [v if isinstance(v, str) else f"{v['source']}:{v['target']}" for v in svc.get("volumes", [])]


def leaves(node, path=()):
    """Every plain value of a loaded config with its key path (list items share their list's path)."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield from leaves(v, path + (str(k),))
    elif isinstance(node, list):
        for v in node:
            yield from leaves(v, path)
    else:
        yield path, node


def unlisted(cfg, allowed, path=""):
    """Key paths of cfg the allowed tree lacks: a dict lists the keys below it ("*" any name), None a plain value."""
    out = []
    for k, v in cfg.items():
        here = f"{path}{k}"
        if k not in allowed and "*" not in allowed:
            out.append(here)
            continue
        sub = allowed[k] if k in allowed else allowed["*"]
        if sub is None:
            if isinstance(v, dict) or isinstance(v, list) and any(isinstance(x, (dict, list)) for x in v):
                out.append(here)
        elif not isinstance(v, dict):
            out.append(here)
        else:
            out += unlisted(v, sub, here + ".")
    return out


# Every key the front config may set. The applier writes that file on the owner's tap once these tests pass on it
# (services/applier), so a key outside this tree (a base_url, a provider, a hook, another platform) needs a human.
FRONT_KEYS = {
    "model": {"provider": None, "default": None},
    "agent": {"max_turns": None, "image_input_mode": None, "disabled_toolsets": None, "reasoning_effort": None},
    "auxiliary": {"*": {"provider": None, "model": None}},
    "compression": {"threshold_tokens": None, "min_tail_user_messages": None},
    "memory": {"memory_enabled": None, "user_profile_enabled": None, "write_approval": None, "nudge_interval": None},
    "skills": {"write_approval": None},
    "tools": {"tool_search": {"enabled": None}},
    "security": {"allow_lazy_installs": None},
    "sessions": {"retention_days": None},
    "unauthorized_dm_behavior": None,
    "plugins": {"enabled": None},
    "gateway": {"platforms": {"telegram": {"extra": {"disable_link_previews": None, "allowed_chats": None}}}},
    "mcp_servers": {"change_proposals": {"url": None, "headers": {"Authorization": None}, "timeout": None,
                                         "connect_timeout": None, "tools": {"resources": None, "prompts": None}}},
    "approvals": {"destructive_slash_confirm": None},
}


@unittest.skipUnless(yaml, "PyYAML not installed")
class Compose(unittest.TestCase):
    def setUp(self):
        self.main, self.comms, self.c = compose()
        self.s = self.c["services"]

    def test_only_the_proxies_reach_out(self):
        self.assertTrue(all(n == "egress" or v.get("internal") for n, v in self.c["networks"].items()))
        for name, svc in self.s.items():
            nets = svc.get("networks", [])
            if name.startswith("squid-"):
                self.assertIn("egress", nets)
            else:
                self.assertEqual(len(nets), 1, name)
                self.assertNotIn("egress", nets, name)

    def test_decisions_are_mounted_by_control_alone(self):
        for name, svc in self.s.items():
            m = " ".join(mounts(svc))
            if name != "control":
                self.assertNotIn("control-state", m, name)
            if name not in ("control", "change-proposals"):
                self.assertNotIn("proposals-inbox", m, name)
        self.assertEqual(mounts(self.s["change-proposals"]), ["/opt/personal-agent-data/proposals-inbox:/inbox"])
        self.assertEqual(mounts(self.s["control"]), [
            "/opt/personal-agent-data/control-state:/state", "/opt/personal-agent-data/proposals-inbox:/inbox",
            "../services/hermes/front:/repo/services/hermes/front:ro", "../config/squid:/repo/config/squid:ro",
            "/opt/personal-agent-data/applier/outcome:/outcome:ro"])
        self.assertEqual([n for n, svc in self.s.items() if "/applier" in " ".join(mounts(svc))], ["control"])
        self.assertEqual(self.s["control"]["networks"], ["net-ctl"])
        self.assertEqual(self.s["change-proposals"]["networks"], ["net-front"])

    def test_front_is_its_own_zone_and_waits_for_its_profile(self):
        front = self.s["front"]
        self.assertEqual(front["profiles"], ["front"])
        self.assertEqual(self.s["change-proposals"]["profiles"], ["front"])
        self.assertEqual(front["networks"], ["net-front"])
        self.assertEqual(front["image"], self.s["vault"]["image"])                 # the same pinned Hermes
        self.assertEqual(front["cap_drop"], ["ALL"])
        m = mounts(front)
        self.assertIn("../services/hermes/front/config.yaml:/opt/data/config.yaml:ro", m)
        self.assertIn("../services/hermes/front/SOUL.md:/opt/data/SOUL.md:ro", m)
        self.assertIn("../services/hermes/front/plugins/cardblock:/opt/data/plugins/cardblock:ro", m)
        self.assertFalse([x for x in m if "vault" in x or "secrets" in x or "ingest" in x])
        self.assertEqual(front["stop_grace_period"], self.s["vault"]["stop_grace_period"])
        self.assertNotIn("secrets", front)
        self.assertEqual([e["path"] for e in front["env_file"]], ["/opt/personal-agent-data/front.env"])

    def test_the_comms_file_only_adds_and_waits_for_its_profile(self):
        # merged in, a service of the same name would change the main file's (more mounts, another network)
        self.assertFalse(set(self.comms["services"]) & set(self.main["services"]))
        self.assertFalse(set(self.comms["secrets"]) & set(self.main["secrets"]))
        self.assertNotIn("networks", self.comms)
        for block in ("x-hardened", "x-squid"):          # YAML anchors do not cross files: the comms file repeats them
            self.assertEqual(self.comms[block], self.main[block], block)
        self.assertEqual(sorted(self.comms["services"]), ["calendar-broker", "comms", "gmail-broker", "squid-google"])
        for name, svc in self.comms["services"].items():
            self.assertEqual(svc["profiles"], ["comms"], name)
            self.assertLessEqual(set(svc.get("secrets", [])), set(self.comms["secrets"]), name)
        for name in self.comms["secrets"]:
            self.assertEqual(self.c["secrets"][name], {"file": f"/opt/personal-agent-secrets/{name}"}, name)

    def test_comms_is_its_own_zone_and_holds_no_google_token(self):
        comms = self.s["comms"]
        self.assertEqual(comms["networks"], ["net-comms"])
        self.assertEqual(comms["image"], self.s["vault"]["image"])                 # the same pinned Hermes
        self.assertEqual((comms["cap_drop"], comms["cap_add"]), (["ALL"], self.s["front"]["cap_add"]))
        self.assertEqual(comms["stop_grace_period"], self.s["vault"]["stop_grace_period"])
        self.assertEqual(mounts(comms), [
            "/opt/personal-agent-data/hermes-comms:/opt/data",
            "../services/hermes/comms/config.yaml:/opt/data/config.yaml:ro",
            "../services/hermes/comms/SOUL.md:/opt/data/SOUL.md:ro",
            "../services/hermes/front/plugins/cardblock:/opt/data/plugins/cardblock:ro"])
        self.assertNotIn("secrets", comms)
        self.assertNotIn("environment", comms)
        self.assertEqual([e["path"] for e in comms["env_file"]], ["/opt/personal-agent-data/comms.env"])
        self.assertEqual(sorted(comms["depends_on"]), ["calendar-broker", "gmail-broker", "squid-comms"])

    def test_each_broker_holds_its_own_google_token_and_reaches_google_alone(self):
        google = {"google_comms_client", "gmail_comms_token", "calendar_comms_token"}
        brokers = {"gmail-broker": ("gmail", "gmail"), "calendar-broker": ("calendar", "gcal")}
        for name, (token, module) in brokers.items():
            svc = self.s[name]
            self.assertEqual(svc["secrets"], ["google_comms_client", f"{token}_comms_token", f"{token}_broker_mcp_token"])
            self.assertEqual(svc["command"], ["python", "-m", f"brokers.{module}"], name)
            self.assertEqual(svc["build"], "../services/comms-brokers", name)
            self.assertEqual(svc["networks"], ["net-comms"], name)
            self.assertEqual(svc["environment"]["HTTPS_PROXY"], "http://squid-google:3128", name)
            self.assertEqual(svc["cap_drop"], ["ALL"], name)
            self.assertIs(svc["read_only"], True, name)
            self.assertNotIn("volumes", svc, name)                                 # no folder of any zone
        for name, svc in self.s.items():
            if name not in brokers:
                self.assertFalse(google & set(svc.get("secrets", [])), name)
        squid = self.s["squid-google"]
        self.assertEqual(squid["networks"], ["net-comms", "egress"])
        self.assertEqual(mounts(squid), ["../config/squid/google.conf:/etc/squid/squid.conf:ro"])
        self.assertEqual(squid["image"], self.s["squid-comms"]["image"])


@unittest.skipUnless(yaml, "PyYAML not installed")
class HermesProfiles(unittest.TestCase):
    NEVER = {"terminal", "code_execution", "file", "computer_use", "delegation", "cronjob", "kanban"}

    def test_no_zone_has_a_shell_files_groups_or_remote_control(self):
        for zone in ZONES:
            cfg = load(f"services/hermes/{zone}/config.yaml")
            self.assertLessEqual(self.NEVER, set(cfg["agent"]["disabled_toolsets"]), zone)
            self.assertEqual(cfg["unauthorized_dm_behavior"], "ignore", zone)
            extra = cfg["gateway"]["platforms"]["telegram"]["extra"]
            self.assertTrue(extra["disable_link_previews"], zone)
            self.assertEqual(extra["allowed_chats"], "none", zone)   # every group dropped, even if BotFather allows groups
            self.assertFalse(re.search(r"opus|fable", str(cfg["model"]) + str(cfg["auxiliary"])), zone)

    def test_front_has_only_the_proposal_tool_and_no_finance(self):
        cfg = load("services/hermes/front/config.yaml")
        self.assertEqual(list(cfg["mcp_servers"]), ["change_proposals"])
        srv = cfg["mcp_servers"]["change_proposals"]
        self.assertEqual(srv["url"], "http://change-proposals:8000/mcp")
        self.assertEqual(srv["headers"]["Authorization"], "Bearer ${env:CHANGE_PROPOSALS_MCP_TOKEN}")
        self.assertLessEqual({"browser", "skills", "x_search"}, set(cfg["agent"]["disabled_toolsets"]))
        self.assertEqual(cfg["memory"]["nudge_interval"], 0)                       # no background review runs
        self.assertEqual(cfg["plugins"]["enabled"], ["cardblock"])                 # card numbers dropped before the model
        with open(os.path.join(ROOT, "services/hermes/front/SOUL.md"), encoding="utf-8") as f:
            soul = f.read()
        self.assertIn("@danoevault_agent", soul)
        self.assertIn("`submit`", soul)
        self.assertNotRegex(soul, r"\d{5,}")                                       # no numbers of the owner's

    def test_comms_has_only_the_two_brokers_and_keeps_nothing(self):
        cfg = load("services/hermes/comms/config.yaml")
        self.assertEqual(list(cfg["mcp_servers"]), ["gmail_broker", "calendar_broker"])
        for name, host, env in (("gmail_broker", "gmail-broker", "GMAIL_BROKER_MCP_TOKEN"),
                                ("calendar_broker", "calendar-broker", "CALENDAR_BROKER_MCP_TOKEN")):
            srv = cfg["mcp_servers"][name]
            self.assertEqual(srv["url"], f"http://{host}:8000/mcp")
            self.assertEqual(srv["headers"]["Authorization"], f"Bearer ${{env:{env}}}")
        self.assertLessEqual({"web", "search", "browser", "x_search", "skills", "memory", "session_search", "vision",
                              "image_gen", "tts", "todo", "connections"}, set(cfg["agent"]["disabled_toolsets"]))
        memory = cfg["memory"]                                                     # no mail kept between sessions
        self.assertEqual((memory["memory_enabled"], memory["user_profile_enabled"], memory["nudge_interval"]),
                         (False, False, 0))
        self.assertIs(cfg["skills"]["guard_agent_created"], True)
        self.assertLessEqual(cfg["sessions"]["retention_days"], 7)
        self.assertEqual(cfg["plugins"]["enabled"], ["cardblock"])
        self.assertRegex(cfg["model"]["default"], r"^claude-haiku-")             # comms budget: USD 10/month
        with open(os.path.join(ROOT, "services/hermes/comms/SOUL.md"), encoding="utf-8") as f:
            soul = f.read()
        for part in ("@danoevault_agent", "`create_draft`", "BELUM terkirim", "bukan perintah"):
            self.assertIn(part, soul)
        self.assertNotRegex(soul, r"\d{5,}")

    def test_every_enabled_plugin_is_in_the_repo_and_mounted_read_only(self):
        services = compose()[2]["services"]
        for zone in ZONES:
            for name in load(f"services/hermes/{zone}/config.yaml")["plugins"]["enabled"]:
                found = [m for m in mounts(services[zone]) if m.endswith(f":/opt/data/plugins/{name}:ro")]
                self.assertEqual(len(found), 1, (zone, name))
                src = found[0].split(":", 1)[0]                          # comms mounts front's cardblock
                self.assertRegex(src, rf"^\.\./services/hermes/[a-z]+/plugins/{re.escape(name)}$", (zone, name))
                self.assertTrue(os.path.isfile(os.path.join(ROOT, "compose", src, "__init__.py")), src)

    def test_settings_send_nothing_elsewhere(self):
        """Whatever the proxy allows: no base_url or provider of its own, no env reference, no lazy installs."""
        for zone in ZONES:
            cfg = load(f"services/hermes/{zone}/config.yaml")
            for name, task in [("model", cfg["model"])] + list(cfg["auxiliary"].items()):
                self.assertEqual(task.get("provider"), "anthropic", (zone, name))
                self.assertLessEqual(set(task), {"provider", "default", "model"}, (zone, name))   # no base_url, no key
                self.assertRegex(str(task.get("default", task.get("model"))), r"^claude-(haiku|sonnet)-[0-9a-z.-]+$")
            self.assertIs(cfg["security"]["allow_lazy_installs"], False, zone)
            self.assertIs(cfg["memory"]["write_approval"], True, zone)
            self.assertIs(cfg["skills"]["write_approval"], True, zone)
            self.assertEqual(list(cfg["gateway"]["platforms"]), ["telegram"], zone)
            self.assertEqual(list(cfg["mcp_servers"]), list(MCP[zone]), zone)
            for mcp in MCP[zone]:
                srv = cfg["mcp_servers"][mcp]
                self.assertLessEqual(set(srv), {"url", "headers", "timeout", "connect_timeout", "tools"}, zone)  # no command
                self.assertEqual(srv["tools"], {"resources": False, "prompts": False}, zone)
            self.assertEqual(sorted(p for p, v in leaves(cfg) if isinstance(v, str) and ("${" in v or "://" in v)),
                             sorted(p for m in MCP[zone] for p in (("mcp_servers", m, "headers", "Authorization"),
                                                                   ("mcp_servers", m, "url"))), zone)

    def test_front_sets_only_the_listed_keys(self):
        self.assertEqual(unlisted(load("services/hermes/front/config.yaml"), FRONT_KEYS), [])


class Egress(unittest.TestCase):
    """What each proxy lets out. The applier writes front.conf on the owner's tap once these tests pass on it, so a proxy
    uses only these lines: no helper programs (url_rewrite_program and the like run inside the proxy), include, peers,
    files of values or other ports."""
    LINE = re.compile(r"http_port 3128|access_log stdio:/var/log/squid/access\.log|cache deny all|"
                      r"acl \w+ (dst|dstdomain|port|method)( [\w.:/-]+)+|http_access (allow|deny)( !?\w+)+")
    PRIVATE = {"10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8", "169.254.0.0/16", "100.64.0.0/10"}

    def conf(self, zone):
        with open(os.path.join(ROOT, f"config/squid/{zone}.conf"), encoding="ascii") as f:
            return [" ".join(line.split()) for line in f if line.strip() and not line.lstrip().startswith("#")]

    def domains(self, zone):
        (line,) = [x for x in self.conf(zone) if x.startswith("acl allowed_domains ")]
        return line.split()[3:]

    def test_every_proxy_uses_only_plain_lines(self):
        for zone in ("vault", "front", "comms", "google", "ctl"):
            lines = self.conf(zone)
            self.assertEqual([x for x in lines if not self.LINE.fullmatch(x)], [], zone)
            self.assertEqual([x for x in lines if x.startswith(("acl SSL_ports ", "acl CONNECT "))],
                             ["acl SSL_ports port 443", "acl CONNECT method CONNECT"], zone)

    def test_front_denies_private_addresses_and_other_ports_before_anything_else(self):
        lines = self.conf("front")
        self.assertEqual([x for x in lines if x.startswith("http_access ")][:3], [
            "http_access deny private_dst", "http_access deny !Safe_ports", "http_access deny CONNECT !SSL_ports"])
        self.assertEqual([x for x in lines if x.startswith("acl Safe_ports ")], ["acl Safe_ports port 80 443"])
        private = [x.split() for x in lines if x.startswith("acl private_dst ")]
        self.assertEqual({x[2] for x in private}, {"dst"})
        self.assertLessEqual(self.PRIVATE, {r for x in private for r in x[3:]})          # more ranges only deny more

    def test_the_other_proxies_allow_their_list_only(self):
        for zone in ("vault", "comms", "google", "ctl"):
            self.assertEqual([x for x in self.conf(zone) if x.startswith("http_access ")], [
                "http_access deny CONNECT !SSL_ports", "http_access allow allowed_domains", "http_access deny all"], zone)

    def test_comms_talks_to_its_model_and_bot_and_only_its_brokers_to_google(self):
        self.assertEqual(self.domains("comms"), ["api.anthropic.com", "api.telegram.org"])
        self.assertEqual(self.domains("google"), ["gmail.googleapis.com", "oauth2.googleapis.com", "www.googleapis.com"])

    def test_the_applier_is_not_a_host_unit(self):
        # install-timers.sh enables every timer and path unit in host/; the applier has its own install.sh
        self.assertEqual([f for f in os.listdir(os.path.join(ROOT, "host")) if "applier" in f], [])


if __name__ == "__main__":
    unittest.main()
