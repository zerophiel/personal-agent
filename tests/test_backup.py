"""scripts/backup.sh with a fake restic. On 1 Nov pa-check and pa-forget failed on each other's lock, restic had no cache under
systemd, and a host with another name would have started a second retention group."""
import os
import stat
import subprocess
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
SCRIPT = os.path.join(ROOT, "scripts", "backup.sh")
FAKE = """#!/bin/bash
{
  printf '%s\\n' "ARGS $*"
  printf '%s\\n' "CACHE $RESTIC_CACHE_DIR"
  printf '%s\\n' "REPO $RESTIC_REPOSITORY"
  printf '%s\\n' "REGION $AWS_DEFAULT_REGION"
} >> "$RESTIC_LOG"
"""


class Backup(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.TemporaryDirectory()
        self.addCleanup(self.d.cleanup)
        self.bin = os.path.join(self.d.name, "bin")
        os.mkdir(self.bin)
        path = os.path.join(self.bin, "restic")
        with open(path, "w", encoding="utf-8") as f:
            f.write(FAKE)
        os.chmod(path, stat.S_IRWXU)
        self.log = os.path.join(self.d.name, "log")
        self.env_file = os.path.join(self.d.name, "restic.env")
        with open(self.env_file, "w", encoding="utf-8") as f:
            f.write("RESTIC_REPOSITORY=s3:uji\nRESTIC_PASSWORD=p=a=s\nLAIN=diabaikan\n")
        self.ledger = os.path.join(self.d.name, "ledger.db")
        with open(self.ledger, "w", encoding="utf-8") as f:
            f.write("isi")

    def run_it(self, *args, **env):
        full = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"], ENV_FILE=self.env_file, PA_LEDGER=self.ledger,
                    RESTIC_LOG=self.log)
        full.pop("RESTIC_CACHE_DIR", None)
        full.update(env)
        return subprocess.run(["bash", SCRIPT, *args], env=full, capture_output=True, text=True, timeout=30)

    def said(self, key):
        with open(self.log, encoding="utf-8") as f:
            return [line.split(" ", 1)[1].rstrip("\n") for line in f if line.startswith(key + " ")]

    def test_a_timed_run_waits_for_another_runs_lock(self):
        for step in ("backup", "forget", "check"):
            self.assertEqual(self.run_it(step).returncode, 0)
        for args in self.said("ARGS"):
            self.assertTrue(args.startswith("--retry-lock 30m "), args)

    def test_the_host_name_is_fixed_and_retention_spans_every_host(self):
        self.run_it("backup")
        self.run_it("forget")
        (backup, forget) = self.said("ARGS")
        self.assertIn(" backup --host personal-agent --exclude-caches /opt/personal-agent-data /opt/personal-agent-secrets", backup)
        self.assertIn(" forget --group-by paths --prune --keep-daily 7 --keep-weekly 4 --keep-monthly 6", forget)

    def test_restic_has_a_cache_without_a_home(self):
        self.run_it("check")
        self.assertEqual(self.said("CACHE"), ["/var/cache/personal-agent-restic"])

    def test_the_cache_can_be_elsewhere_for_a_restore(self):
        self.run_it("snapshots", RESTIC_CACHE_DIR="/opt/.pa-restore-x/cache")
        self.assertEqual(self.said("CACHE"), ["/opt/.pa-restore-x/cache"])

    def test_the_settings_come_from_the_env_file(self):
        self.run_it("check")
        self.assertEqual(self.said("REPO"), ["s3:uji"])
        self.assertEqual(self.said("REGION"), ["auto"])

    def test_no_ledger_no_backup_and_no_forget(self):
        os.remove(self.ledger)
        for gone in ("missing", "empty"):
            if gone == "empty":
                open(self.ledger, "w", encoding="utf-8").close()
            for step in ("backup", "forget"):
                with self.subTest(gone=gone, step=step):
                    done = self.run_it(step)
                    self.assertEqual(done.returncode, 1)
                    self.assertIn("no ledger.db", done.stdout)
                    self.assertFalse(os.path.exists(self.log))

    def test_an_empty_host_may_still_read_the_repository(self):
        os.remove(self.ledger)
        target = os.path.join(self.d.name, "kosong")
        os.mkdir(target)
        for args in (("snapshots", "--json"), ("check",), ("restore", "abcd1234", target)):
            self.assertEqual(self.run_it(*args).returncode, 0, args)
        self.assertEqual(self.said("ARGS"), ["--retry-lock 30m snapshots --json", "--retry-lock 30m check",
                                             f"--retry-lock 30m restore abcd1234 --target {target}"])

    def test_a_restore_refuses_a_target_with_content(self):
        target = os.path.join(self.d.name, "isi")
        os.mkdir(target)
        with open(os.path.join(target, "x"), "w", encoding="utf-8") as f:
            f.write("x")
        done = self.run_it("restore", "abcd1234", target)
        self.assertEqual(done.returncode, 1)
        self.assertFalse(os.path.exists(self.log))

    def test_a_restore_names_its_snapshot(self):
        self.assertNotEqual(self.run_it("restore").returncode, 0)
        self.assertFalse(os.path.exists(self.log))

    def test_the_timers_use_it_with_a_step(self):
        for unit, step in (("pa-backup", "backup"), ("pa-check", "check"), ("pa-forget", "forget")):
            with open(os.path.join(ROOT, "host", unit + ".service"), encoding="utf-8") as f:
                self.assertIn(f"ExecStart=/opt/personal-agent/scripts/backup.sh {step}\n", f.read())
        self.assertTrue(os.stat(SCRIPT).st_mode & stat.S_IXUSR, "systemd runs the script itself")


if __name__ == "__main__":
    unittest.main()
