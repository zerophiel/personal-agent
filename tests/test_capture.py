"""make capture (scripts/capture-recipe.sh) against a fake VPS: ssh runs the remote command here, docker answers from a script."""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
FILES = ("etc/ssh/sshd_config.d/00-hardening.conf", "etc/docker/daemon.json", "etc/systemd/journald.conf.d/size.conf",
         "etc/sysctl.d/99-swappiness.conf", "etc/apt/apt.conf.d/20auto-upgrades")
FAKE_SSH = r"""#!/bin/bash
[ -z "${SSH_FAIL:-}" ] || exit 255
while [ "$1" = "-o" ]; do shift 2; done
shift
cmd="$*"
cmd=${cmd//sudo -n /}
cmd=${cmd//\/usr\/bin\/python3/$REMOTE_PY}
exec bash -c "$cmd"
"""
FAKE_DOCKER = r"""#!/bin/bash
case "$1 $2" in
  "exec "*) cat "$FREEZE" ;;
  "buildx imagetools")
    if [[ "$*" == *'.Image'* ]]; then
      echo '{"rootfs":{"diff_ids":["sha256:a"]},"config":{"Env":["PATH=/x","PYTHON_VERSION=3.12.16"]}}'
    else
      echo '{"digest":"sha256:indeks-'"${4%%:*}"'"}'
    fi ;;
  "image inspect")
    if [[ "$3" == *squid* ]]; then echo '["ubuntu/squid@sha256:lokal"]'; else echo "${LAYERS:-[\"sha256:a\",\"sha256:b\"]}"; fi ;;
esac
"""


class Capture(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.repo = os.path.join(self.d, "repo")
        os.makedirs(os.path.join(self.repo, "scripts"))
        shutil.copy(os.path.join(ROOT, "scripts", "capture-recipe.sh"), os.path.join(self.repo, "scripts"))
        for service in ("vault-tools", "change-proposals", "comms-brokers"):
            os.makedirs(os.path.join(self.repo, "services", service))
        self.rootfs = os.path.join(self.d, "vps")
        for rel in FILES:
            self.write(os.path.join(self.rootfs, rel), f"isi {rel}\n")
        self.write(os.path.join(self.rootfs, "etc", "shadow"), "tidak boleh ikut\n")
        fake = os.path.join(self.d, "bin")
        for name, body in (("ssh", FAKE_SSH), ("docker", FAKE_DOCKER)):
            self.write(os.path.join(fake, name), body)
            os.chmod(os.path.join(fake, name), stat.S_IRWXU)
        self.freeze = self.write(os.path.join(self.d, "freeze"), "Paket_A==1.2.3\nb.c==4.5+lokal\n")
        self.env = dict(os.environ, PATH=fake + os.pathsep + os.environ["PATH"], CAPTURE_REMOTE_ROOT=self.rootfs,
                        REMOTE_PY=sys.executable, FREEZE=self.freeze)

    def write(self, path, body):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        return path

    def run_capture(self, **env):
        return subprocess.run(["bash", os.path.join(self.repo, "scripts", "capture-recipe.sh"), "vps"],
                              env=dict(self.env, **env), capture_output=True, text=True, timeout=60)

    def written(self):
        out = []
        for folder, _, names in os.walk(self.repo):
            out += [os.path.relpath(os.path.join(folder, n), self.repo) for n in names if n != "capture-recipe.sh"]
        return sorted(out)

    def test_the_named_files_and_the_locks_arrive(self):
        done = self.run_capture()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        for rel in FILES:
            with open(os.path.join(self.repo, "host", rel), encoding="utf-8") as f:
                self.assertEqual(f.read(), f"isi {rel}\n")
            self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.repo, "host", rel)).st_mode), 0o644)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "host", "etc", "shadow")))
        for service in ("vault-tools", "change-proposals", "comms-brokers"):
            with open(os.path.join(self.repo, "services", service, "requirements.lock"), encoding="utf-8") as f:
                lines = f.read().splitlines()
            self.assertTrue(lines[0].startswith("# "))
            self.assertEqual(lines[1:], ["Paket_A==1.2.3", "b.c==4.5+lokal"])

    def test_the_digests_to_pin_are_printed(self):
        out = self.run_capture().stdout
        self.assertIn("python:3.12-slim: sha256:indeks-python (Python 3.12.16)", out)
        self.assertIn("personal-agent-vault-tools built on it: yes", out)
        self.assertIn("ubuntu/squid:6.6-24.04_edge: local ubuntu/squid@sha256:lokal; registry now sha256:indeks-ubuntu/squid", out)

    def test_it_says_when_the_tag_moved(self):
        out = self.run_capture(LAYERS=json.dumps(["sha256:lain", "sha256:b"])).stdout
        self.assertIn("personal-agent-control built on it: no", out)

    def test_a_list_that_is_not_name_version_writes_nothing(self):
        for body in ("Paket_A==1.2.3\nprivat @ git+https://rahasia@contoh/x\n", ""):
            with self.subTest(body=body):
                self.write(self.freeze, body)
                done = self.run_capture()
                self.assertEqual(done.returncode, 1)
                self.assertIn("name==version", done.stderr)
                self.assertNotIn("rahasia", done.stdout + done.stderr)
                self.assertEqual(self.written(), [])

    def test_a_missing_config_file_writes_nothing(self):
        os.unlink(os.path.join(self.rootfs, FILES[1]))
        done = self.run_capture()
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(self.written(), [])

    def test_no_answer_from_the_vps_writes_nothing(self):
        done = self.run_capture(SSH_FAIL="1")
        self.assertNotEqual(done.returncode, 0)
        self.assertEqual(self.written(), [])


class Target(unittest.TestCase):
    def test_make_capture_is_a_target(self):
        with open(os.path.join(ROOT, "Makefile"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("\ncapture:\n\tbash scripts/capture-recipe.sh $(VPS_USER)@$(VPS_HOST)\n", text)


if __name__ == "__main__":
    unittest.main()
