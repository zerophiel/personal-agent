"""make verify (scripts/verify.py) against the fake VPS of tests/test_mirror.py. A real make mirror writes the copy it compares with, so
the two cannot drift apart on what MIRROR.json holds."""
import importlib.util
import os
import stat
import subprocess
import sys
import unittest

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tm = load("tests/test_mirror.py", "test_mirror_for_verify")
verify = load("scripts/verify.py", "verify_for_test")
HEALTHY = "vault\trunning\tUp 4 days\nvault-tools\trunning\tUp 4 days (healthy)\nfront\trunning\tUp 1 day\n"
FAKES = {
    "docker": r"""#!/bin/bash
state=${CONTAINERS:-up}
case "$1" in
  compose)
    printf '%s\n' "$*" >> "$DOCKER_LOG"
    [ -z "${COMPOSE_FAIL:-}" ] || exit 1
    printf '%s\n' vault vault-tools front ;;
  ps)
    if [ "$2" = "-q" ]; then [ "$state" != up ] || echo abc123; exit 0; fi
    if [ "$2" = "-a" ]; then printf '%s\n' "$*" >> "$DOCKER_LOG"; cat "$DOCKER_PS"; exit 0; fi
    echo "personal-agent-vault-1 image $state" ;;
  exec)
    case "$2" in
      personal-agent-vault-tools-1) printf 'Paket_Satu==1.0\npaket-dua==2.0\n' ;;
      personal-agent-change-proposals-1)
        [ -z "${PROPOSALS_DOWN:-}" ] || exit 1
        printf 'paket-tiga==%s\n' "${PIP_VERSION:-3.0}" ;;
      *) exit 1 ;;
    esac ;;
  image) echo "image:tag sha256:abc def" ;;
esac
""",
    "systemctl": r"""#!/bin/bash
case "$1" in
  is-enabled) if [ "$2" = "${UNIT_OFF:-x}" ]; then echo disabled; exit 1; fi; echo enabled ;;
  is-active) if [ "$2" = "${UNIT_OFF:-x}" ]; then echo inactive; exit 3; fi; echo active ;;
  list-units)
    case "$*" in
      *--state=failed*) [ -z "${UNIT_FAILED:-}" ] || echo "$UNIT_FAILED loaded failed failed Uji" ;;
    esac ;;
esac
exit 0
""",
    "setpriv": '#!/bin/bash\necho "$1 $2" >> "$SETPRIV_LOG"\nshift 5\nexec "$@"\n',
}


class Way(tm.Base):
    def setUp(self):
        super().setUp()
        for name, body in FAKES.items():
            path = os.path.join(self.d, "bin", name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            os.chmod(path, stat.S_IRWXU)
        with open(os.path.join(ROOT, "scripts", "verify.py"), "rb") as f:
            self.write(os.path.join(self.repo, "scripts", "verify.py"), f.read())
        self.write(os.path.join(self.repo, "services", "vault-tools", "requirements.lock"), b"# komentar\npaket-satu==1.0\npaket-dua==2.0\n")
        self.write(os.path.join(self.repo, "services", "change-proposals", "requirements.lock"), b"paket-tiga==3.0\n")
        for unit in ("host/pa-backup.timer", "host/pa-backup.service", "host/pa-uploads.path", "services/applier/systemd/pa-applier.timer"):
            self.write(os.path.join(self.repo, *unit.split("/")), b"[Unit]\n")
        self.opt = os.path.join(self.d, "vps", "opt")
        os.makedirs(self.opt)
        self.docker_log = os.path.join(self.d, "docker-log")
        self.setpriv_log = os.path.join(self.d, "setpriv-log")
        self.docker_ps = self.write(os.path.join(self.d, "docker-ps"), HEALTHY.encode())
        self.env.update(RESTORE_REMOTE_OPT=self.opt, DOCKER_PS=self.docker_ps, DOCKER_LOG=self.docker_log, SETPRIV_LOG=self.setpriv_log)

    def verify(self, *args, **env):
        return subprocess.run([sys.executable, "-I", os.path.join(self.repo, "scripts", "verify.py"), "vps", *args],
                              env=dict(self.env, **env), capture_output=True, text=True, timeout=120)

    def line(self, done, name):
        (one,) = [x for x in done.stdout.splitlines() if x.startswith(name + ":")]
        return one

    def add_row(self):
        self.writer.execute("INSERT INTO entries VALUES ('baru')")
        self.writer.commit()

    def drop_row(self):
        self.writer.execute("DELETE FROM entries")
        self.writer.commit()

    def ps(self, text):
        self.write(self.docker_ps, text.encode())


class AllGood(Way):
    def test_right_after_a_copy_everything_passes(self):
        self.good()
        done = self.verify()
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.line(done, "containers"), "containers: ok (3 of 3 up, 1 with a healthcheck healthy)")
        self.assertEqual(self.line(done, "ledger"), "ledger: ok (integrity ok, 2 tables, 2 rows, copy 2)")
        self.assertEqual(self.line(done, "packages"), "packages: ok (vault-tools 2, change-proposals 1 equal their locks)")
        self.assertEqual(self.line(done, "timers"), "timers: ok (3 of 3 enabled and active)")
        self.assertEqual(self.line(done, "failed_units"), "failed_units: ok (0)")
        self.assertEqual(self.line(done, "leftovers"), "leftovers: ok (0)")
        self.assertEqual(done.stdout.splitlines()[-1], "verify: all checks passed")

    def test_the_output_holds_no_data_no_file_name_and_no_host(self):
        self.good()
        done = self.verify()
        for word in (tm.SECRET_VALUE, tm.PRIVATE_NAME, "hanya-di-wal", self.d):
            self.assertNotIn(word, done.stdout + done.stderr)

    def test_the_ledger_is_opened_by_its_own_owner(self):
        self.good()
        self.verify()
        st = os.stat(self.ledger)
        with open(self.setpriv_log, encoding="utf-8") as f:
            self.assertIn(f"--reuid={st.st_uid} --regid={st.st_gid}\n", f.read())

    def test_the_expected_services_are_the_main_file_and_front_and_never_a_one_off(self):
        self.good()
        self.verify()
        with open(self.docker_log, encoding="utf-8") as f:
            calls = f.read()
        self.assertIn("/personal-agent/compose/docker-compose.yml --env-file ", calls)
        self.assertIn("--profile front config --services", calls)
        self.assertNotIn("comms", calls)
        self.assertIn("label=com.docker.compose.oneoff=False", calls)

    def test_the_real_repo_expects_the_units_and_locks_that_exist(self):
        units = verify.expected_units()
        for unit in ("pa-backup.timer", "pa-uploads.path", "pa-applier.timer", "pa-applier.path"):
            self.assertIn(unit, units)
        self.assertFalse([u for u in units if u.endswith(".service")])
        for service in verify.LOCKED:
            self.assertTrue(os.path.exists(os.path.join(ROOT, "services", service, "requirements.lock")))


class Ledger(Way):
    def test_more_rows_than_the_copy_is_a_live_bot(self):
        self.good()
        self.add_row()
        done = self.verify()
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.line(done, "ledger"), "ledger: ok (integrity ok, 2 tables, 3 rows, copy 2)")

    def test_fewer_rows_than_the_copy_fails(self):
        self.good()
        self.drop_row()
        done = self.verify()
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.line(done, "ledger"), "ledger: fail (integrity ok, 2 tables, 1 rows, copy 2: fewer rows than the copy)")
        self.assertEqual(done.stdout.splitlines()[-1], "verify: 1 failed")

    def test_after_a_snapshot_a_smaller_ledger_is_only_reported(self):
        self.good()
        self.drop_row()
        done = self.verify("--r2")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("ledger: note (", done.stdout)
        self.assertIn("fewer rows than the copy", done.stdout)

    def test_a_table_gone_fails_though_the_total_grew(self):
        self.good()
        for _ in range(3):
            self.add_row()
        self.writer.execute("DROP TABLE payee_secrets")
        self.writer.commit()
        done = self.verify()
        self.assertEqual(done.returncode, 1)
        self.assertIn("tables gone: payee_secrets", self.line(done, "ledger"))

    def test_one_table_lower_with_the_total_up_is_a_note(self):
        self.good()
        self.writer.execute("CREATE TABLE tambahan(x)")
        self.writer.execute("INSERT INTO tambahan VALUES (1), (2)")
        self.writer.execute("DELETE FROM entries")
        self.writer.commit()
        done = self.verify()
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("ledger: note (", done.stdout)
        self.assertIn("fewer rows than the copy in: entries", done.stdout)

    def test_no_copy_is_a_note_and_not_a_failure(self):
        done = self.verify()
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.line(done, "ledger"), "ledger: note (integrity ok, 2 tables, 2 rows, no copy in private/ to compare with)")

    def test_no_ledger_fails(self):
        self.good()
        done = self.verify(MIRROR_REMOTE_DATA=os.path.join(self.d, "tiada"))
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.line(done, "ledger"), "ledger: fail (no ledger, or it cannot be read)")

    def test_a_damaged_ledger_fails_after_a_snapshot_too(self):
        self.good()
        self.writer.close()
        size = os.path.getsize(self.ledger)
        with open(self.ledger, "r+b") as f:
            f.seek(4096)
            f.write(b"\xff" * (size - 4096))
        done = self.verify("--r2")
        self.assertEqual(done.returncode, 1)
        self.assertIn("ledger: fail (", done.stdout)


class Containers(Way):
    def test_each_way_of_not_being_up_fails_and_names_the_service(self):
        self.good()
        for status in ("vault-tools\texited\tExited (1) 2 minutes ago", "vault-tools\trestarting\tRestarting (1) 3 seconds ago",
                       "vault-tools\trunning\tUp 2 minutes (unhealthy)", "vault-tools\trunning\tUp 5 seconds (health: starting)"):
            self.ps("vault\trunning\tUp 4 days\nfront\trunning\tUp 1 day\n" + status + "\n")
            done = self.verify()
            self.assertEqual(done.returncode, 1, status)
            self.assertEqual(self.line(done, "containers"), "containers: fail (2 of 3 up; down or not healthy yet: vault-tools)")

    def test_a_service_that_is_missing_fails(self):
        self.good()
        self.ps("vault\trunning\tUp 4 days\nfront\trunning\tUp 1 day\n")
        self.assertIn("not healthy yet: vault-tools", self.line(self.verify(), "containers"))

    def test_a_service_outside_the_list_changes_nothing(self):
        self.good()
        self.ps(HEALTHY + "comms\texited\tExited (0) 2 days ago\n")
        self.assertEqual(self.verify().returncode, 0)

    def test_compose_that_cannot_list_fails(self):
        self.good()
        done = self.verify(COMPOSE_FAIL="1")
        self.assertEqual(done.returncode, 1)
        self.assertIn("make sync first", self.line(done, "containers"))


class Others(Way):
    def test_a_package_that_differs_from_the_lock_fails_and_names_it(self):
        self.good()
        done = self.verify(PIP_VERSION="3.1")
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.line(done, "packages"), "packages: fail (change-proposals differs: paket-tiga==3.0, paket-tiga==3.1)")

    def test_a_container_that_does_not_answer_fails(self):
        self.good()
        done = self.verify(PROPOSALS_DOWN="1")
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.line(done, "packages"), "packages: fail (change-proposals: no answer)")

    def test_a_timer_that_is_off_fails_and_names_it(self):
        self.good()
        done = self.verify(UNIT_OFF="pa-applier.timer")
        self.assertEqual(done.returncode, 1)
        self.assertEqual(self.line(done, "timers"), "timers: fail (2 of 3 enabled and active; not: pa-applier.timer)")

    def test_a_failed_unit_is_a_note(self):
        self.good()
        done = self.verify(UNIT_FAILED="pa-forget.service")
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertEqual(self.line(done, "failed_units"), "failed_units: note (1: pa-forget.service)")

    def test_what_an_interrupted_restore_left_fails(self):
        self.good()
        os.makedirs(os.path.join(self.opt, ".pa-restore-abc"))
        done = self.verify()
        self.assertEqual(done.returncode, 1)
        self.assertIn("leftovers: fail (1 under /opt", done.stdout)

    def test_a_host_that_does_not_answer_fails_without_a_traceback(self):
        self.good()
        for env in ({"SSH_FAIL": "1"}, {"REMOTE_PY": "/bin/false"}):
            done = self.verify(**env)
            self.assertEqual(done.returncode, 1, env)
            self.assertEqual(done.stdout, "verify: the VPS does not answer (ssh or sudo failed)\n")
            self.assertEqual(done.stderr, "")


if __name__ == "__main__":
    unittest.main()
