"""make applied-pull against a temporary git checkout: what it commits from the applier's records, and what it refuses."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("applied_pull", ROOT / "scripts" / "applied-pull.py")
ap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ap)

SOUL = "Kamu asisten front.\nJawab singkat.\n"
NEW = SOUL + "Sapa pemilik dengan ramah.\n"
SOUL_PATH = "services/hermes/front/SOUL.md"


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


class AppliedPull(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.repo, True)
        for rel, text in (("services/control/control.py", (ROOT / "services/control/control.py").read_text()),
                          (SOUL_PATH, SOUL), ("services/hermes/front/config.yaml", "model: {}\n"),
                          ("config/squid/front.conf", "http_port 3128\n"), ("README.md", "x\n")):
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.repo / rel).write_text(text)
        self.git("init", "-q")
        for k, v in (("user.name", "test"), ("user.email", "nobody"), ("commit.gpgsign", "false")):
            self.git("config", k, v)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.control = ap.load_control(self.repo)

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], capture_output=True, text=True, check=True).stdout

    def record(self, pid=3, before=SOUL, content=NEW, path=SOUL_PATH, zone="front", **kw):
        p = self.control.validate({"summary": "Sapa pemilik", "permission_diff": "tidak ada", "risk_notes": "kecil",
                                   "rollback": "usulkan versi lama", "zone": zone, "change_type": "config",
                                   "files": [{"path": path, "content": content}]})
        rec = {"id": pid, "status": "applied", "proposal": p, "services": ["front"],
               "files": [{"path": path, "sha256_before": sha(before), "sha256_after": sha(content)}],
               "decided_at": "2026-11-02T01:00:00+00:00", "started_at": "2026-11-02T01:00:05+00:00",
               "applied_at": "2026-11-02T01:01:00+00:00"}
        rec.update(kw)
        return rec

    def pull(self, records):
        with contextlib.redirect_stdout(io.StringIO()):
            return ap.pull(records, self.repo)

    def test_an_applied_change_becomes_one_commit_of_its_file_and_record(self):
        (self.repo / "README.md").write_text("staged elsewhere\n")
        self.git("add", "README.md")
        self.assertEqual(self.pull([self.record()]), [3])
        self.assertEqual((self.repo / SOUL_PATH).read_text(), NEW)
        self.assertEqual(self.git("log", "-1", "--format=%s"), f"apply proposal #3 ({SOUL_PATH})\n")
        self.assertEqual(self.git("show", "--name-only", "--format=", "HEAD").split(), ["ops/applied/3.json", SOUL_PATH])
        self.assertEqual(self.git("diff", "--cached", "--name-only"), "README.md\n")      # left staged, not committed
        kept = json.loads((self.repo / "ops/applied/3.json").read_text())
        self.assertEqual(sorted(kept), ["applied_at", "change_type", "decided_at", "files", "id", "services", "status",
                                        "zone"])
        self.assertNotIn("Sapa pemilik dengan ramah", json.dumps(kept))
        self.assertEqual(self.pull([self.record()]), [])                                  # once
        self.assertEqual(len(self.git("log", "--format=%h").split()), 2)

    def test_changes_build_on_each_other_oldest_first(self):
        newer = NEW + "Pakai bahasa santai.\n"
        self.assertEqual(self.pull([self.record(5, before=NEW, content=newer), self.record(4)]), [4, 5])
        self.assertEqual((self.repo / SOUL_PATH).read_text(), newer)
        self.assertEqual(self.git("log", "-2", "--format=%s").splitlines(),
                         [f"apply proposal #5 ({SOUL_PATH})", f"apply proposal #4 ({SOUL_PATH})"])

    def test_a_record_that_does_not_fit_changes_nothing_and_says_why(self):
        def committed(text):
            (self.repo / SOUL_PATH).write_text(text)
            self.git("commit", "-q", "-am", "edited here")

        rec = self.record()
        cases = (
            (None, self.record(content=NEW + "​"), "characters a diff does not show"),
            (None, dict(rec, status="rolled_back"), "not an applied record"),
            (None, self.record(path="services/hermes/vault/SOUL.md", zone="vault"), "never writes"),
            (None, dict(rec, files=[]), "file list differs"),
            (None, dict(rec, files=[dict(rec["files"][0], sha256_after=sha("x"))]), "does not match the hash"),
            (lambda: committed(SOUL + "edited here\n"), rec, "not what the VPS had before"),
            (lambda: (committed(SOUL + "edited here\n"), (self.repo / SOUL_PATH).write_text(SOUL)), rec,
             "uncommitted changes"),
        )
        base = self.git("rev-parse", "HEAD").strip()
        for prepare, bad, why in cases:
            if prepare:
                prepare()
            before = ((self.repo / SOUL_PATH).read_text(), self.git("rev-parse", "HEAD"))
            with self.assertRaises(SystemExit) as e:
                self.pull([bad])
            self.assertIn("#3 not pulled: ", str(e.exception.code))
            self.assertIn(why, str(e.exception.code))
            self.assertNotIn("Sapa pemilik dengan ramah", str(e.exception.code))
            self.assertEqual(((self.repo / SOUL_PATH).read_text(), self.git("rev-parse", "HEAD")), before, why)
            self.assertFalse((self.repo / "ops").exists(), why)
            self.git("reset", "-q", "--hard", base)

    def test_without_a_git_identity_nothing_is_written(self):
        self.git("config", "--unset", "user.name")
        self.git("config", "--unset", "user.email")
        self.git("config", "user.useConfigOnly", "true")
        env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_AUTHOR", "GIT_COMMITTER"))}
        env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
        with mock.patch.dict(os.environ, env, clear=True), self.assertRaises(SystemExit) as e:
            self.pull([self.record()])
        self.assertIn("#3 not pulled: git has no identity", str(e.exception.code))
        self.assertEqual((self.repo / SOUL_PATH).read_text(), SOUL)
        self.assertFalse((self.repo / "ops").exists())

    def test_the_pull_stops_at_the_first_record_that_does_not_fit(self):
        bad = dict(self.record(5, before=NEW, content=NEW + "x\n"), status="rolled_back")
        with self.assertRaises(SystemExit) as e:
            self.pull([self.record(6, before=NEW + "x\n", content=NEW + "y\n"), bad, self.record(4)])
        self.assertIn("#5 not pulled", str(e.exception.code))
        self.assertEqual(self.git("log", "-1", "--format=%s"), f"apply proposal #4 ({SOUL_PATH})\n")   # #6 waits
        self.assertEqual([p.name for p in (self.repo / "ops/applied").iterdir()], ["4.json"])
        with self.assertRaises(SystemExit) as e:
            self.pull([self.record(7, before=NEW, content=SOUL), {"status": "applied"}])
        self.assertIn("without an id; nothing pulled", str(e.exception.code))
        self.assertEqual((self.repo / SOUL_PATH).read_text(), NEW)

    def test_the_records_come_from_the_applier_alone_and_contents_are_never_printed(self):
        self.assertIn("/opt/personal-agent-data/applier/applied", ap.REMOTE)
        self.assertNotIn("control-state", ap.REMOTE)                  # control's copy is not the applier's record
        out = io.StringIO()
        with mock.patch.object(ap, "fetch", lambda host: [self.record()]), contextlib.redirect_stdout(out):
            ap.main(["u@h"], self.repo)
        self.assertEqual(out.getvalue(), f"applied-pull: #3 committed ({SOUL_PATH})\n"
                                         "applied-pull: 1 new commit(s); make deploy carries them\n")


if __name__ == "__main__":
    unittest.main()
