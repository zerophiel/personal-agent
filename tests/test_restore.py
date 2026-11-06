"""make restore, make snapshots and make restore-restic (scripts/restore.sh, apply-ownership.py, recover-dbs.py). The whole way
runs against the fake VPS of tests/test_mirror.py: a real make mirror, then a restore onto a second empty folder. A test user
cannot chown to the bots' uids, so the list's own owners are checked with os.lchown mocked."""
import importlib.util
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tm = load("tests/test_mirror.py", "test_mirror_for_restore")
ownership = load("scripts/apply-ownership.py", "apply_ownership")
PIECES = ("scripts/restore.sh", "scripts/restore-facts.py", "scripts/apply-ownership.py", "scripts/recover-dbs.py", "scripts/backup.sh")
FAKES = {
    "setpriv": '#!/bin/bash\nshift 5\nexec "$@"\n',
    "restic": r"""#!/bin/bash
case "$1" in
  snapshots)
    [ -z "${RESTIC_FAIL:-}" ] || { echo "Fatal: s3:https://rahasia.example/bucket" >&2; exit 1; }
    cat "$RESTIC_LIST" ;;
  restore)
    [ -z "${RESTIC_FAIL:-}" ] || { echo "Fatal: s3:https://rahasia.example/bucket" >&2; exit 1; }
    echo "restoring $2 to $4 s3:https://rahasia.example/bucket"
    cp -a "$RESTIC_TREE/." "$4/" ;;
esac
""",
}


def read(path, mode="r"):
    with open(path, mode) as f:
        return f.read()


def crashed_writer(path):
    """A database as restic finds it: a committed row only in the -wal, and the writer never closed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run([sys.executable, "-I", "-c", (
        "import os, sqlite3, sys\n"
        "c = sqlite3.connect(sys.argv[1])\n"
        "c.execute('PRAGMA journal_mode=WAL')\n"
        "c.execute('PRAGMA wal_autocheckpoint=0')\n"
        "c.execute('CREATE TABLE entries(x TEXT)')\n"
        "c.execute(\"INSERT INTO entries VALUES ('hanya-di-wal')\")\n"
        "c.commit()\n"
        "os._exit(0)\n"), path], check=True)


class Way(tm.Base):
    def setUp(self):
        super().setUp()
        for piece in PIECES:
            shutil.copy(os.path.join(ROOT, piece), os.path.join(self.repo, piece))
        fake = os.path.join(self.d, "bin")
        for name, body in FAKES.items():
            with open(os.path.join(fake, name), "w", encoding="utf-8") as f:
                f.write(body)
            os.chmod(os.path.join(fake, name), stat.S_IRWXU)
        self.opt = os.path.join(self.d, "new", "opt")
        os.makedirs(self.opt)
        self.new_data = os.path.join(self.opt, "personal-agent-data")
        self.new_secrets = os.path.join(self.opt, "personal-agent-secrets")
        self.restic_list = os.path.join(self.d, "snapshots.json")
        self.restic_tree = os.path.join(self.d, "snapshot")
        self.env.update(RESTORE_REMOTE_OPT=self.opt, RESTIC_LIST=self.restic_list, RESTIC_TREE=self.restic_tree)

    def run_restore(self, *args, **env):
        env.setdefault("CONTAINERS", "down")
        return subprocess.run(["bash", os.path.join(self.repo, "scripts", "restore.sh"), *args],
                              env=dict(self.env, **env), capture_output=True, text=True, timeout=120)

    def restore(self, **env):
        return self.run_restore("mirror", "vps", "vps", **env)

    def restored(self, **env):
        done = self.restore(**env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done

    def nothing_in_place(self):
        self.assertFalse(os.path.exists(self.new_data))
        self.assertFalse(os.path.exists(self.new_secrets))
        self.assertEqual([n for n in os.listdir(self.opt) if n.startswith(".pa-restore-")], [])

    def listing(self):
        with open(self.copy("host", "ownership.jsonl"), encoding="utf-8") as f:
            return [json.loads(x) for x in f]

    def clean_output(self, done):
        for leak in (tm.SECRET_VALUE, tm.PRIVATE_NAME, "rahasia.example"):
            self.assertNotIn(leak, done.stdout + done.stderr)


class FromTheCopy(Way):
    def test_the_copy_lands_with_each_listed_mode(self):
        self.good()
        done = self.restored()
        self.clean_output(done)
        self.assertIn("in place", done.stdout)
        self.assertEqual(read(os.path.join(self.new_data, "ingest", tm.PRIVATE_NAME), "rb"), b"pdf")
        self.assertEqual(read(os.path.join(self.new_secrets, "restic.env")), tm.SECRET_VALUE)
        self.assertEqual(os.readlink(os.path.join(self.new_data, "kosong", "tautan")), "../gen.txt")
        checked = 0
        for row in self.listing():
            base = self.new_data if row["r"] == "data" else self.new_secrets
            path = os.path.join(base, row["p"]) if row["p"] else base
            if row["t"] == "o" or row["p"].endswith(("-wal", "-shm", "-journal")):
                self.assertFalse(os.path.lexists(path), row["p"])
                continue
            st = os.lstat(path)
            if row["t"] != "l":
                self.assertEqual(stat.S_IMODE(st.st_mode), row["m"], row["p"])
                checked += 1
        self.assertGreater(checked, 20)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.new_secrets, "notion_token")).st_mode), 0o444)
        self.assertEqual(sorted(n for n in os.listdir(self.opt) if n.startswith(".pa-")), [])

    def test_the_rows_of_the_wal_arrive_and_the_ledger_opens_as_the_service_opens_it(self):
        self.good()
        self.restored()
        conn = sqlite3.connect(os.path.join(self.new_data, "vault-tools", "ledger.db"))
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        self.assertEqual(conn.execute("SELECT x FROM entries").fetchall(), [("hanya-di-wal",)])

    def test_it_says_how_old_the_copy_is(self):
        self.good()
        self.assertIn("from a live host, raw databases: 0", self.restored().stdout)

    def test_confirm_must_repeat_the_address(self):
        self.good()
        for wrong in ("", "alamat-lain"):
            done = self.run_restore("mirror", "ubuntu@vps", wrong)
            self.assertEqual(done.returncode, 1)
            self.assertIn("CONFIRM", done.stderr)
            self.nothing_in_place()

    def test_no_copy_no_restore(self):
        done = self.restore()
        self.assertEqual(done.returncode, 1)
        self.assertIn("no copy", done.stderr)

    def test_a_host_with_this_project_is_refused(self):
        self.good()
        done = self.restore(CONTAINERS="up")
        self.assertEqual(done.returncode, 1)
        self.assertIn("containers", done.stderr)
        self.nothing_in_place()

    def test_a_second_restore_is_refused_and_touches_nothing(self):
        self.good()
        self.restored()
        marker = os.path.join(self.new_data, "gen.txt")
        with open(marker, "w", encoding="utf-8") as f:
            f.write("data baru bot")
        done = self.restore()
        self.assertEqual(done.returncode, 1)
        self.assertIn("already has a ledger", done.stderr)
        self.assertEqual(read(marker), "data baru bot")

    def test_folders_with_content_are_refused_and_empty_ones_are_fine(self):
        self.good()
        for folder in (self.new_data, self.new_secrets):
            self.write(os.path.join(folder, "milik-orang"))
            done = self.restore()
            self.assertEqual(done.returncode, 1)
            self.assertIn("already has", done.stderr)
            self.assertTrue(os.path.exists(os.path.join(folder, "milik-orang")))
            os.unlink(os.path.join(folder, "milik-orang"))
        self.restored()

    def test_a_run_stopped_between_its_renames_can_run_again(self):
        self.good()
        self.write(os.path.join(self.new_secrets, "dari-run-lama"))
        self.write(os.path.join(self.opt, ".pa-placing"), b"")
        self.write(os.path.join(self.opt, ".pa-restore-lama", "data", "x"))
        self.restored()
        self.assertFalse(os.path.exists(os.path.join(self.new_secrets, "dari-run-lama")))
        self.assertTrue(os.path.exists(os.path.join(self.new_data, "vault-tools", "ledger.db")))
        self.assertEqual([n for n in os.listdir(self.opt) if n.startswith(".pa-")], [])

    def test_a_failed_upload_leaves_nothing_and_the_next_run_works(self):
        self.good()
        exits = self.write(os.path.join(self.d, "exits"), b"12\n")
        done = self.restore(RSYNC_EXITS=exits)
        self.assertEqual(done.returncode, 1)
        self.assertIn("upload failed", done.stderr)
        self.clean_output(done)
        self.nothing_in_place()
        self.restored()

    def test_a_silent_vps_stops_it(self):
        self.good()
        done = self.restore(SSH_FAIL="1")
        self.assertEqual(done.returncode, 1)
        self.assertIn("does not answer", done.stderr)


class FromR2(Way):
    def snapshots(self, *times):
        with open(self.restic_list, "w", encoding="utf-8") as f:
            json.dump([{"short_id": f"abcd{i:04d}", "id": f"abcd{i:04d}" + "0" * 56, "time": t} for i, t in enumerate(times)], f)

    def make_snapshot(self):
        crashed_writer(os.path.join(self.restic_tree, "opt", "personal-agent-data", "vault-tools", "ledger.db"))
        self.write(os.path.join(self.restic_tree, "opt", "personal-agent-secrets", "restic.env"), b"kunci-lama")
        self.write(os.path.join(self.restic_tree, "opt", "personal-agent-secrets", "notion_token"), b"t")

    def test_the_list_says_which_is_newer_and_leaves_nothing_on_the_host(self):
        self.good()
        self.snapshots("2020-01-01T01:00:00.123456789Z", "2020-01-02T02:00:00+08:00")
        done = self.run_restore("snapshots", "vps")
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("abcd0000  2020-01-01 08:00 WIB", done.stdout)
        self.assertIn("abcd0001  2020-01-02 01:00 WIB", done.stdout)
        self.assertIn("older than the copy", done.stdout)
        self.clean_output(done)
        self.nothing_in_place()
        self.snapshots("2099-01-01T01:00:00Z")
        self.assertIn("NEWER than the copy", self.run_restore("snapshots", "vps").stdout)

    def test_what_restic_says_stays_out_of_the_output(self):
        self.good()
        self.snapshots()
        done = self.run_restore("snapshots", "vps", RESTIC_FAIL="1")
        self.assertEqual(done.returncode, 1)
        self.clean_output(done)
        self.assertIn("rahasia.example", read(os.path.join(self.private, "restore.log")))
        self.nothing_in_place()

    def test_a_snapshot_lands_with_the_wal_replayed_by_sqlite(self):
        self.good()
        self.make_snapshot()
        wal = os.path.join(self.restic_tree, "opt", "personal-agent-data", "vault-tools", "ledger.db-wal")
        self.assertGreater(os.path.getsize(wal), 0)
        done = self.run_restore("restic", "vps", "vps", "abcd0001")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertIn("databases ok=1 failed=0", done.stdout)
        self.clean_output(done)
        ledger = os.path.join(self.new_data, "vault-tools", "ledger.db")
        self.assertIn(b"hanya-di-wal", read(ledger, "rb"))
        conn = sqlite3.connect(ledger)
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("SELECT x FROM entries").fetchall(), [("hanya-di-wal",)])
        self.assertEqual([n for n in os.listdir(self.opt) if n.startswith(".pa-")], [])

    def test_the_restic_env_that_opened_the_repository_stays(self):
        self.good()
        self.make_snapshot()
        self.assertEqual(self.run_restore("restic", "vps", "vps", "latest").returncode, 0)
        path = os.path.join(self.new_secrets, "restic.env")
        self.assertEqual(read(path), tm.SECRET_VALUE)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertEqual(read(os.path.join(self.new_secrets, "notion_token")), "t")

    def test_a_damaged_database_stops_it_with_an_older_snapshot_as_the_way_on(self):
        self.good()
        self.make_snapshot()
        self.write(os.path.join(self.restic_tree, "opt", "personal-agent-data", "hermes-vault", "state.db"),
                   b"SQLite format 3\0" + b"\xff" * 5000)
        done = self.run_restore("restic", "vps", "vps", "abcd0001")
        self.assertEqual(done.returncode, 1)
        self.assertIn("older snapshot", done.stdout)
        self.assertIn("databases ok=1 failed=1", done.stdout)
        self.nothing_in_place()

    def test_a_snapshot_without_a_ledger_stops_it(self):
        self.good()
        self.write(os.path.join(self.restic_tree, "opt", "personal-agent-data", "catatan"))
        self.write(os.path.join(self.restic_tree, "opt", "personal-agent-secrets", "x"))
        done = self.run_restore("restic", "vps", "vps", "abcd0001")
        self.assertEqual(done.returncode, 1)
        self.assertIn("no ledger.db", done.stdout)
        self.nothing_in_place()

    def test_a_snapshot_without_the_folders_stops_it(self):
        self.good()
        os.makedirs(os.path.join(self.restic_tree, "opt"))
        done = self.run_restore("restic", "vps", "vps", "abcd0001")
        self.assertEqual(done.returncode, 1)
        self.assertIn("lacks", done.stderr)
        self.nothing_in_place()

    def test_refusals_before_anything_moves(self):
        self.good()
        self.make_snapshot()
        for args, why in ((("restic", "vps", "lain", "abcd0001"), "CONFIRM"), (("restic", "vps", "vps", "bukan id!"), "SNAPSHOT"),
                          (("restic", "vps", "vps", ""), "SNAPSHOT")):
            done = self.run_restore(*args)
            self.assertEqual(done.returncode, 1)
            self.assertIn(why, done.stderr)
            self.nothing_in_place()
        done = self.run_restore("restic", "vps", "vps", "abcd0001", CONTAINERS="up")
        self.assertEqual(done.returncode, 1)
        self.assertIn("containers", done.stderr)
        done = self.run_restore("restic", "vps", "vps", "abcd0001", RESTIC_FAIL="1")
        self.assertEqual(done.returncode, 1)
        self.clean_output(done)
        self.nothing_in_place()


class Owners(unittest.TestCase):
    """apply-ownership.py on its own, with the changes of owner recorded instead of made."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        os.makedirs(os.path.join(self.d, "tools"))
        os.makedirs(os.path.join(self.d, "secrets"))
        os.makedirs(os.path.join(self.d, "data", "vault"))
        self.rows = [self.row("data", "", "d", 0, 0o755), self.row("secrets", "", "d", 0, 0o700),
                     self.row("data", "vault", "d", 10001, 0o700)]
        self.calls = {}
        patcher = mock.patch.object(ownership.os, "lchown", side_effect=lambda p, u, g: self.calls.__setitem__(p, (u, g)))
        patcher.start()
        self.addCleanup(patcher.stop)

    def row(self, root, rel, kind, uid, mode):
        return {"r": root, "p": rel, "t": kind, "u": uid, "g": uid, "m": mode}

    def touch(self, *parts, mode=0o600):
        path = os.path.join(self.d, *parts)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("x")
        os.chmod(path, mode)
        return path

    def run_it(self, cleaned=(), before=None):
        for name, rows in (("ownership.jsonl", self.rows), ("ownership.before.jsonl", self.rows if before is None else before)):
            with open(os.path.join(self.d, "tools", name), "w", encoding="utf-8") as f:
                f.write("".join(json.dumps(r) + "\n" for r in rows))
        with open(os.path.join(self.d, "tools", "db-report.json"), "w", encoding="utf-8") as f:
            json.dump({"clean": list(cleaned), "raw": [], "plain": []}, f)
        with mock.patch.object(sys, "argv", ["apply-ownership.py", self.d]):
            return ownership.main()

    def test_owner_and_mode_come_from_the_list(self):
        path = self.touch("data", "vault", "ledger.db")
        self.rows.append(self.row("data", "vault/ledger.db", "f", 10001, 0o644))
        self.assertEqual(self.run_it(), 0)
        self.assertEqual(self.calls[path], (10001, 10001))
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o644)
        self.assertEqual(self.calls[os.path.join(self.d, "data")], (0, 0))
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.d, "data", "vault")).st_mode), 0o700)

    def test_a_name_that_is_not_utf8_still_gets_its_owner(self):
        name = os.fsdecode(b"nama\xff.pdf")
        path = self.touch("data", "vault", name)
        self.rows.append(self.row("data", "vault/" + name, "f", 10001, 0o640))
        self.assertEqual(self.run_it(), 0)
        self.assertEqual(self.calls[path], (10001, 10001))

    def test_a_link_changes_itself_and_never_what_it_points_at(self):
        secret = self.touch("secrets", "restic.env")
        link = os.path.join(self.d, "data", "vault", "tautan")
        os.symlink(secret, link)
        self.rows.extend([self.row("data", "vault/tautan", "l", 10001, 0o777), self.row("secrets", "restic.env", "f", 0, 0o600)])
        self.assertEqual(self.run_it(), 0)
        self.assertEqual(self.calls[link], (10001, 10001))
        self.assertEqual(self.calls[secret], (0, 0))
        self.assertEqual(stat.S_IMODE(os.stat(secret).st_mode), 0o600)

    def test_a_link_on_the_way_stops_everything(self):
        secret = self.touch("secrets", "restic.env")
        os.symlink(os.path.join(self.d, "secrets"), os.path.join(self.d, "data", "vault", "lewat"))
        self.rows.append(self.row("data", "vault/lewat/restic.env", "f", 10001, 0o666))
        self.assertEqual(self.run_it(), 1)
        self.assertEqual(self.calls, {})
        self.assertEqual(stat.S_IMODE(os.stat(secret).st_mode), 0o600)

    def test_a_path_leaving_its_folder_stops_everything(self):
        for rel in ("../secrets/restic.env", "/etc/passwd", "vault/../../x"):
            with self.subTest(rel=rel):
                self.rows.append(self.row("data", rel, "f", 10001, 0o666))
                self.assertEqual(self.run_it(), 1)
                self.assertEqual(self.calls, {})
                self.rows.pop()

    def test_a_root_outside_the_two_stops_everything(self):
        self.rows.append(self.row("tools", "ownership.jsonl", "f", 10001, 0o666))
        self.assertEqual(self.run_it(), 1)
        self.assertEqual(self.calls, {})

    def test_a_listed_file_gone_is_counted_and_a_cleaned_side_file_is_not(self):
        self.touch("data", "vault", "ledger.db")
        self.rows.extend([self.row("data", "vault/ledger.db", "f", 10001, 0o644), self.row("data", "vault/ledger.db-wal", "f", 10001, 0o644),
                          self.row("data", "vault/hilang", "f", 10001, 0o644), self.row("data", "gw.sock", "o", 10001, 0o644)])
        with mock.patch("builtins.print") as said:
            self.assertEqual(self.run_it(cleaned=["vault/ledger.db"]), 0)
        self.assertIn(mock.call("restore: owners set=4 links=0 missing=1 unlisted=0 not_files=1"), said.call_args_list)

    def test_what_the_list_lacks_takes_its_folders_owner_and_loses_group_and_other(self):
        path = self.touch("data", "vault", "baru.txt", mode=0o664)
        inner = self.touch("data", "vault", "baru", "isi.txt", mode=0o755)
        self.assertEqual(self.run_it(), 0)
        folder = os.path.join(self.d, "data", "vault")
        order = list(self.calls)
        self.assertLess(order.index(folder), order.index(path))   # the folder is settled first; its owner on disk is then read
        self.assertLess(order.index(os.path.dirname(inner)), order.index(inner))
        self.assertEqual(self.calls[path], (os.getuid(), os.getgid()))   # lchown is mocked, so the folder is still the test user's
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(inner).st_mode), 0o700)

    def test_a_top_folder_in_both_lists_must_be_there(self):
        self.rows.append(self.row("data", "hermes-vault", "d", 10000, 0o700))
        self.assertEqual(self.run_it(), 1)
        self.assertEqual(self.calls, {})

    def test_a_top_folder_born_during_the_pull_may_be_missing(self):
        before = list(self.rows)
        self.rows.append(self.row("data", "baru-lahir", "d", 10000, 0o700))
        self.assertEqual(self.run_it(before=before), 0)

    def test_a_deep_folder_gone_is_only_counted(self):
        self.rows.append(self.row("data", "vault/tmpabc", "d", 10000, 0o700))
        self.assertEqual(self.run_it(), 0)


class Targets(unittest.TestCase):
    def test_the_make_targets_exist(self):
        with open(os.path.join(ROOT, "Makefile"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn('\nrestore:\n\tbash scripts/restore.sh mirror $(VPS_USER)@$(VPS_HOST) "$(CONFIRM)"\n', text)
        self.assertIn("\nsnapshots:\n\tbash scripts/restore.sh snapshots $(VPS_USER)@$(VPS_HOST)\n", text)
        self.assertIn('\nrestore-restic:\n\tbash scripts/restore.sh restic $(VPS_USER)@$(VPS_HOST) "$(CONFIRM)" "$(SNAPSHOT)"\n', text)


if __name__ == "__main__":
    unittest.main()
