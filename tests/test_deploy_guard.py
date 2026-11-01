"""scripts/deploy-guard.sh with a fake ssh: what make deploy is let through, and what each step runs on the VPS."""
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "deploy-guard.sh"
# stands in for ssh: keeps its arguments and the script it was sent, answers $IDS and exits $RC
FAKE_SSH = """#!/bin/sh
n=$(find "$LOG" -name '*.args' | wc -l)
printf '%s\\n' "$*" > "$LOG/$n.args"
cat > "$LOG/$n.stdin"
printf '%b' "$IDS"
exit "${RC:-0}"
"""
APPLIER = "/opt/personal-agent-data/applier"


class DeployGuard(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.repo, self.log, bin_dir = self.tmp / "repo", self.tmp / "log", self.tmp / "bin"
        for d in (self.repo / "scripts", self.repo / "ops/applied", self.log, bin_dir):
            d.mkdir(parents=True)
        shutil.copy(SCRIPT, self.repo / "scripts/deploy-guard.sh")
        (self.repo / "ops/applied/3.json").write_text("{}")
        (bin_dir / "ssh").write_text(FAKE_SSH)
        os.chmod(bin_dir / "ssh", 0o755)
        self.path = f"{bin_dir}:/usr/bin:/bin"

    def guard(self, step, ids="", rc=0):
        env = {"PATH": self.path, "LOG": str(self.log), "IDS": ids, "RC": str(rc)}
        return subprocess.run(["bash", str(self.repo / "scripts/deploy-guard.sh"), step, "ubuntu@vps"], env=env,
                              capture_output=True, text=True, timeout=60)

    def calls(self):
        n = len(list(self.log.glob("*.args")))
        return [((self.log / f"{i}.args").read_text().split(), (self.log / f"{i}.stdin").read_text()) for i in range(n)]

    def test_a_deploy_goes_ahead_when_every_applied_change_is_here(self):
        r = self.guard("start", ids="3\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        [(args, script)] = self.calls()
        self.assertEqual(args, ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "ubuntu@vps", "sudo", "bash", "-s"])
        self.assertIn(f'date +%s > "$A/deploy-hold"', script)
        self.assertIn('flock -w 1200 "$A/lock" true', script)
        self.assertLess(script.index("deploy-hold"), script.index("flock"))       # held first, then the lock drained

    def test_a_change_not_pulled_refuses_and_lifts_the_hold_again(self):
        for ids, named in (("3\n4\n", "#4"), ("3\nx;rm\n", "#x;rm")):
            shutil.rmtree(self.log)
            self.log.mkdir()
            r = self.guard("start", ids=ids)
            self.assertEqual(r.returncode, 1)
            self.assertIn(f"not in this checkout: {named}. Run make applied-pull first.", r.stderr)
            self.assertEqual(len(self.calls()), 2)
            self.assertIn(f"rm -f {APPLIER}/deploy-hold", self.calls()[1][1])

    def test_no_answer_from_the_vps_is_a_refusal(self):
        r = self.guard("start", rc=255)
        self.assertEqual(r.returncode, 1)
        self.assertIn("could not be held", r.stderr)

    def test_end_lifts_the_hold_and_starts_the_applier_if_installed(self):
        self.assertEqual(self.guard("end").returncode, 0)
        [(_, script)] = self.calls()
        self.assertIn(f"rm -f {APPLIER}/deploy-hold", script)
        self.assertIn("if systemctl cat pa-applier.service >/dev/null 2>&1; then systemctl start --no-block "
                      "pa-applier.service; fi", script)
        self.assertEqual(self.guard("deploy").returncode, 2)

    def test_on_the_vps_start_holds_and_lists_the_applied_ids(self):
        self.guard("start", ids="3\n")
        script = self.calls()[0][1]
        state = self.tmp / "applier"
        (state / "applied").mkdir(parents=True)
        for name in ("3.json", "12.json", "notes.txt"):
            (state / "applied" / name).write_text("{}")
        r = subprocess.run(["bash", "-s"], input=script.replace(APPLIER, str(state)), capture_output=True, text=True,
                           timeout=60)
        self.assertEqual((r.returncode, r.stdout), (0, "12\n3\n"), r.stderr)
        self.assertLess(abs(int((state / "deploy-hold").read_text()) - time.time()), 60)
        shutil.rmtree(state)
        r = subprocess.run(["bash", "-s"], input=script.replace(APPLIER, str(state)), capture_output=True, text=True,
                           timeout=60)
        self.assertEqual((r.returncode, r.stdout), (0, ""), r.stderr)          # not installed: nothing to hold


if __name__ == "__main__":
    unittest.main()
