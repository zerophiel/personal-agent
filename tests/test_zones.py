"""Zone boundaries as the repo states them: compose networks and mounts, and what each Hermes profile may do."""
import os
import re
import unittest

try:
    import yaml
except ImportError:  # the vault-tools venv may lack PyYAML; the system python3 used by `make test` has it
    yaml = None

ROOT = os.path.join(os.path.dirname(__file__), "..")


def load(path):
    with open(os.path.join(ROOT, path), encoding="utf-8") as f:
        return yaml.safe_load(f)


def mounts(svc):
    return [v if isinstance(v, str) else f"{v['source']}:{v['target']}" for v in svc.get("volumes", [])]


@unittest.skipUnless(yaml, "PyYAML not installed")
class Compose(unittest.TestCase):
    def setUp(self):
        self.c = load("compose/docker-compose.yml")
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
        self.assertFalse([x for x in m if "vault" in x or "secrets" in x or "ingest" in x])
        self.assertNotIn("secrets", front)
        self.assertEqual([e["path"] for e in front["env_file"]], ["/opt/personal-agent-data/front.env"])


@unittest.skipUnless(yaml, "PyYAML not installed")
class HermesProfiles(unittest.TestCase):
    NEVER = {"terminal", "code_execution", "file", "computer_use", "delegation", "cronjob", "kanban"}

    def test_no_zone_has_a_shell_files_or_remote_control(self):
        for zone in ("vault", "front"):
            cfg = load(f"services/hermes/{zone}/config.yaml")
            self.assertLessEqual(self.NEVER, set(cfg["agent"]["disabled_toolsets"]), zone)
            self.assertEqual(cfg["unauthorized_dm_behavior"], "ignore", zone)
            self.assertTrue(cfg["gateway"]["platforms"]["telegram"]["extra"]["disable_link_previews"], zone)
            self.assertFalse(re.search(r"opus|fable", str(cfg["model"]) + str(cfg["auxiliary"])), zone)

    def test_front_has_only_the_proposal_tool_and_no_finance(self):
        cfg = load("services/hermes/front/config.yaml")
        self.assertEqual(list(cfg["mcp_servers"]), ["change_proposals"])
        srv = cfg["mcp_servers"]["change_proposals"]
        self.assertEqual(srv["url"], "http://change-proposals:8000/mcp")
        self.assertEqual(srv["headers"]["Authorization"], "Bearer ${env:CHANGE_PROPOSALS_MCP_TOKEN}")
        self.assertIn("browser", cfg["agent"]["disabled_toolsets"])
        self.assertIn("skills", cfg["agent"]["disabled_toolsets"])
        with open(os.path.join(ROOT, "services/hermes/front/SOUL.md"), encoding="utf-8") as f:
            soul = f.read()
        self.assertIn("@danoevault_agent", soul)
        self.assertIn("`submit`", soul)
        self.assertNotRegex(soul, r"\d{5,}")                                       # no numbers of the owner's


if __name__ == "__main__":
    unittest.main()
