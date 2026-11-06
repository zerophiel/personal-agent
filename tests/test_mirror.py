"""make mirror (scripts/mirror.sh, db-copy.py, mirror-check.py) against a fake VPS in a temporary folder. ssh runs the remote
command here without sudo or setpriv, rsync is the real one minus the remote parts, and the database writer really holds a
row only in its -wal while the copy runs."""
import base64
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

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PIECES = ("scripts/mirror.sh", "scripts/db-copy.py", "scripts/mirror-check.py", "config/secrets.manifest",
          "services/vault-tools/vault_tools/payee_vault.py", "Makefile")
SECRET_VALUE = "nilai-rahasia-uji"
PRIVATE_NAME = "Rekening PEMILIK 1234.pdf"
try:
    import cryptography
except ImportError:
    cryptography = None

FAKES = {
    "ssh": r"""#!/bin/bash
[ -z "${SSH_FAIL:-}" ] || exit 255
while [ "$1" = "-o" ]; do shift 2; done
shift
cmd="$*"
cmd=${cmd//sudo -n /}
cmd=$(printf '%s' "$cmd" | sed -E 's/setpriv --reuid=[0-9]+ --regid=[0-9]+ --clear-groups --inh-caps=\+dac_read_search --ambient-caps=\+dac_read_search //')
cmd=${cmd//\/usr\/bin\/python3/$REMOTE_PY}
exec bash -c "$cmd"
""",
    "rsync": r"""#!/bin/bash
args=(); skip=0; remote=0
for a in "$@"; do
  if [ "$skip" = 1 ]; then skip=0; continue; fi
  case "$a" in
    -e) skip=1 ;;
    --rsync-path=*) ;;
    vps:*) args+=("${a#vps:}"); remote=1 ;;
    *) args+=("$a") ;;
  esac
done
rc=0
"$REAL_RSYNC" "${args[@]}" || rc=$?
if [ "$remote" = 1 ]; then
  echo call >> "$RSYNC_CALLS"
  dest="${args[-1]}"
  case "$dest" in
    */data/)
      [ -z "${RSYNC_DROP:-}" ] || rm -f "$dest$RSYNC_DROP"
      [ -z "${RSYNC_TOUCH:-}" ] || touch "$RSYNC_TOUCH" ;;
  esac
  if [ -s "${RSYNC_EXITS:-/nonexistent}" ]; then
    rc=$(head -1 "$RSYNC_EXITS"); sed -i 1d "$RSYNC_EXITS"
  fi
fi
exit "$rc"
""",
    "mv": r"""#!/bin/bash
n=0
if [ -n "${MV_COUNT:-}" ]; then
  n=$(($(cat "$MV_COUNT" 2>/dev/null || echo 0) + 1)); echo "$n" > "$MV_COUNT"
fi
if [ "$n" = "${MV_KILL_BEFORE:-x}" ]; then kill -KILL "$PPID"; exit 137; fi
"$REAL_MV" "$@" || exit $?
if [ "$n" = "${MV_KILL_AFTER:-x}" ]; then kill -KILL "$PPID"; exit 137; fi
""",
    "docker": r"""#!/bin/bash
state=${CONTAINERS:-up}
case "$1" in
  ps)
    if [ "$2" = "-q" ]; then [ "$state" != up ] || echo abc123; exit 0; fi
    echo "personal-agent-vault-1 image $state" ;;
  exec) [ "$state" = up ] || exit 1; echo "paket==${PIP_VERSION:-1.0}" ;;
  image) echo "image:tag sha256:abc def" ;;
esac
""",
    "systemctl": '#!/bin/bash\nexit 0\n',
    "ufw": '#!/bin/bash\necho "Status: active"\n',
    "dpkg-query": '#!/bin/bash\necho "paket 1.0"\n',
    "timedatectl": '#!/bin/bash\necho Asia/Jakarta\n',
    "swapon": '#!/bin/bash\nexit 0\n',
}


def tree(path):
    """Every path under a folder with its bytes: what must not move when a pull fails."""
    out = {}
    for folder, dirs, files in os.walk(path):
        for name in dirs + files:
            p = os.path.join(folder, name)
            out[os.path.relpath(p, path)] = open(p, "rb").read() if os.path.isfile(p) and not os.path.islink(p) else None
    return out


@unittest.skipUnless(cryptography and shutil.which("rsync") and shutil.which("flock") and hasattr(sqlite3.Connection, "serialize"),
                     "needs rsync, flock, the cryptography package and Python 3.11+")
class Base(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.repo = os.path.join(self.d, "repo")
        self.home = os.path.join(self.d, "home")
        os.makedirs(self.home)
        for piece in PIECES:
            target = os.path.join(self.repo, piece)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy(os.path.join(ROOT, piece), target)
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x")
        self.private = os.path.join(self.repo, "private")
        self.make_vps()
        fake = os.path.join(self.d, "bin")
        os.makedirs(fake)
        for name, body in FAKES.items():
            path = os.path.join(fake, name)
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)
            os.chmod(path, stat.S_IRWXU)
        self.rsync_calls = os.path.join(self.d, "rsync-calls")
        self.env = dict(os.environ, PATH=fake + os.pathsep + os.environ["PATH"], HOME=self.home, MIRROR_PY=sys.executable,
                        REMOTE_PY=sys.executable, MIRROR_REMOTE_DATA=self.data, MIRROR_REMOTE_SECRETS=self.secrets,
                        MIRROR_REMOTE_ROOT=self.rootfs, MIRROR_DB_PAUSE="0", REAL_RSYNC=shutil.which("rsync"),
                        REAL_MV=shutil.which("mv"), RSYNC_CALLS=self.rsync_calls)

    def git(self, *args, cwd=None):
        return subprocess.run(["git", "-C", cwd or self.repo, *args], capture_output=True, text=True, check=True).stdout

    def write(self, path, body=b"x"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(body)
        return path

    def make_vps(self):
        self.data = os.path.join(self.d, "vps", "data")
        self.secrets = os.path.join(self.d, "vps", "secrets")
        self.rootfs = os.path.join(self.d, "vps", "root")
        spec = importlib.util.spec_from_file_location("payee_vault_for_mirror", os.path.join(
            ROOT, "services", "vault-tools", "vault_tools", "payee_vault.py"))
        self.payee = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.payee)
        self.key = os.urandom(32)
        self.ledger = self.write(os.path.join(self.data, "vault-tools", "ledger.db"), b"")
        conn = sqlite3.connect(self.ledger)
        self.addCleanup(conn.close)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA wal_autocheckpoint=0")
        conn.execute("CREATE TABLE payee_secrets(alias TEXT PRIMARY KEY, kind TEXT, bank TEXT, last4 TEXT, nonce BLOB,"
                     " ciphertext BLOB, match_hash BLOB, created_at TEXT)")
        conn.execute("CREATE TABLE entries(x TEXT)")
        conn.commit()
        self.writer = conn
        self.payee.PayeeVault(conn, self.key).store("uji-rekening", "account", "bank", "12345678")
        conn.execute("INSERT INTO entries VALUES ('hanya-di-wal')")
        conn.commit()
        self.write(self.ledger + ".bak-20261101", b"cadangan")
        for name in ("hermes-vault/state.db", "control-state/control.db", "hermes-front/odd[1].db"):
            path = self.write(os.path.join(self.data, name), b"")
            c = sqlite3.connect(path)
            c.execute("CREATE TABLE t(x)")
            c.execute("INSERT INTO t VALUES (1)")
            c.commit()
            c.close()
        self.write(os.path.join(self.data, "hermes-front", "odd[1].db-journal"), b"")
        self.write(os.path.join(self.data, "hermes-vault", "empty.db"), b"")
        self.write(os.path.join(self.data, "hermes-vault", "notes.db"), b"bukan sqlite")
        self.write(os.path.join(self.data, "ingest", PRIVATE_NAME), b"pdf")
        self.write(os.path.join(self.data, "ingest", "baris\nbaru.txt"), b"nama aneh")
        self.write(os.path.join(self.data, "vault.env"), SECRET_VALUE.encode())
        self.write(os.path.join(self.data, "gen.txt"), b"1")
        self.write(os.path.join(self.data, "hermes-vault", ".env"), b"# TELEGRAM_BOT_TOKEN=\n")
        os.makedirs(os.path.join(self.data, "kosong"))
        os.symlink("../gen.txt", os.path.join(self.data, "kosong", "tautan"))
        os.mkfifo(os.path.join(self.data, "gw.fifo"))   # like the gateway's sockets: neither a file nor a folder, not copied
        os.chmod(os.path.join(self.data, "hermes-vault"), 0o700)
        with open(os.path.join(ROOT, "config", "secrets.manifest"), encoding="utf-8") as f:
            names = [x.split() for x in f if x.strip() and not x.startswith("#")]
        for name, _, zone, mode in names:
            if zone != "comms":
                body = base64.b64encode(self.key) + b"\n" if name == "vault_tools_key" else SECRET_VALUE.encode()
                os.chmod(self.write(os.path.join(self.secrets, name), body), int(mode, 8))
        self.write(os.path.join(self.rootfs, "etc", "docker", "daemon.json"), b"{}\n")
        self.write(os.path.join(self.rootfs, "etc", "shadow"), b"tidak boleh ikut")
        self.write(os.path.join(self.rootfs, "etc", "ssh", "ssh_host_ed25519_key"), b"tidak boleh ikut")
        self.write(os.path.join(self.rootfs, "etc", "ssh", "sshd_config.d", "00-hardening.conf"), b"PermitRootLogin no\n")
        self.write(os.path.join(self.rootfs, "etc", "systemd", "system", "pa-backup.timer"), b"[Timer]\n")

    def run_mirror(self, script=None, **env):
        return subprocess.run(["bash", script or os.path.join(self.repo, "scripts", "mirror.sh"), "vps"],
                              env=dict(self.env, **env), capture_output=True, text=True, timeout=120)

    def good(self, **env):
        done = self.run_mirror(**env)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        return done

    def copy(self, *parts):
        return os.path.join(self.private, "vps", *parts)

    def doc(self, gen="vps"):
        with open(os.path.join(self.private, gen, "MIRROR.json"), encoding="utf-8") as f:
            return json.load(f)

    def row_count(self, *parts):
        conn = sqlite3.connect("file:" + self.copy(*parts) + "?immutable=1", uri=True)
        try:
            return conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        finally:
            conn.close()


class Copy(Base):
    def test_everything_arrives_and_only_the_owner_can_read_it(self):
        done = self.good()
        self.assertEqual(open(self.copy("data", "ingest", PRIVATE_NAME), "rb").read(), b"pdf")
        self.assertEqual(open(self.copy("data", "vault-tools", "ledger.db.bak-20261101"), "rb").read(), b"cadangan")
        self.assertEqual(open(self.copy("data", "ingest", "baris\nbaru.txt"), "rb").read(), b"nama aneh")
        self.assertEqual(os.readlink(self.copy("data", "kosong", "tautan")), "../gen.txt")
        self.assertEqual(open(self.copy("secrets", "restic.env")).read(), SECRET_VALUE)
        self.assertEqual(stat.S_IMODE(os.stat(self.private).st_mode), 0o700)
        for name in ("secrets/restic.env", "secrets/notion_token", "data/vault.env", "data/gen.txt"):
            self.assertEqual(stat.S_IMODE(os.stat(self.copy(*name.split("/"))).st_mode), 0o600, name)
        self.assertEqual(stat.S_IMODE(os.stat(self.copy("secrets")).st_mode), 0o700)
        self.assertFalse(os.path.exists(os.path.join(self.private, ".new")))
        self.assertTrue(self.doc()["clean"])
        self.assertIn("secrets: ok", done.stdout)
        self.assertIn("mirror: done", done.stdout)

    def test_a_row_only_in_the_wal_is_in_the_copy(self):
        self.assertGreater(os.path.getsize(self.ledger + "-wal"), 0)
        self.assertNotIn(b"hanya-di-wal", open(self.ledger, "rb").read())
        self.good()
        self.assertEqual(self.row_count("data", "vault-tools", "ledger.db"), 1)
        for side in ("-wal", "-shm", "-journal"):
            self.assertFalse(os.path.exists(self.copy("data", "vault-tools", "ledger.db" + side)), side)

    def test_the_copy_opens_as_the_service_opens_it(self):
        self.good()
        spare = shutil.copy(self.copy("data", "vault-tools", "ledger.db"), os.path.join(self.d, "spare.db"))
        conn = sqlite3.connect(spare)
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("PRAGMA journal_mode").fetchone()[0], "wal")
        conn.execute("INSERT INTO entries VALUES ('baru')")
        conn.commit()
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0], 2)

    def test_each_uid_can_reach_its_database_through_the_root_only_data_folder(self):
        # The fake ssh strips exactly this: without the capability every database on the real VPS fails with EACCES
        with open(os.path.join(ROOT, "scripts", "db-copy.py"), encoding="utf-8") as f:
            self.assertIn('REACH = "--inh-caps=+dac_read_search --ambient-caps=+dac_read_search"', f.read())
        self.assertEqual(self.good().returncode, 0)
        self.assertTrue(self.doc()["clean"])

    def test_a_wildcard_in_a_name_still_keeps_side_files_out(self):
        self.good()
        self.assertTrue(os.path.isfile(self.copy("data", "hermes-front", "odd[1].db")))
        self.assertFalse(os.path.exists(self.copy("data", "hermes-front", "odd[1].db-journal")))

    def test_empty_and_non_sqlite_db_files_stay_ordinary(self):
        self.good()
        self.assertEqual(os.path.getsize(self.copy("data", "hermes-vault", "empty.db")), 0)
        self.assertEqual(open(self.copy("data", "hermes-vault", "notes.db"), "rb").read(), b"bukan sqlite")
        self.assertEqual(self.doc()["counts"]["db_plain"], 2)
        self.assertEqual(self.doc()["counts"]["db_clean"], 4)

    def test_output_holds_no_file_name_and_no_value(self):
        done = self.good()
        for text in (done.stdout + done.stderr, open(os.path.join(self.private, "mirror.log")).read()):
            self.assertNotIn(SECRET_VALUE, text)
        out = done.stdout + done.stderr
        for word in ("PEMILIK", "Rekening", "state.db", "ledger.db", "vault.env", "restic"):
            self.assertNotIn(word, out, word)

    def test_the_owner_and_mode_list_covers_both_roots(self):
        self.good()
        with open(self.copy("host", "ownership.jsonl"), encoding="utf-8") as f:
            rows = {(r["r"], r["p"]): r for r in map(json.loads, f)}
        self.assertEqual(rows[("data", "")]["t"], "d")
        self.assertEqual(rows[("secrets", "")]["t"], "d")
        self.assertEqual(rows[("secrets", "restic.env")]["m"], 0o600)
        self.assertEqual(rows[("secrets", "notion_token")]["m"], 0o444)
        self.assertEqual(rows[("data", "hermes-vault")]["m"], 0o700)
        self.assertEqual(rows[("data", "kosong/tautan")]["t"], "l")
        self.assertEqual(rows[("data", "gw.fifo")]["t"], "o")
        self.assertFalse(os.path.lexists(self.copy("data", "gw.fifo")))
        self.assertIn(("data", "ingest/baris\nbaru.txt"), rows)
        self.assertIn(("data", "ingest/" + PRIVATE_NAME), rows)

    def test_named_host_config_only(self):
        self.good()
        live = tree(self.copy("host", "live"))
        self.assertIn("etc/docker/daemon.json", live)
        self.assertIn("etc/ssh/sshd_config.d/00-hardening.conf", live)
        self.assertIn("etc/systemd/system/pa-backup.timer", live)
        self.assertNotIn("etc/shadow", live)
        self.assertNotIn("etc/ssh/ssh_host_ed25519_key", live)
        self.assertEqual(open(self.copy("host", "pip-vault-tools.txt")).read(), "paket==1.0\n")

    def test_a_second_run_keeps_the_first_as_prev(self):
        self.good()
        self.write(os.path.join(self.data, "gen.txt"), b"2")
        self.good()
        self.assertEqual(open(self.copy("data", "gen.txt")).read(), "2")
        self.assertEqual(open(os.path.join(self.private, ".prev", "data", "gen.txt")).read(), "1")

    def test_a_third_run_drops_the_oldest(self):
        for gen in ("1", "2", "3"):
            self.write(os.path.join(self.data, "gen.txt"), gen.encode())
            self.good()
        self.assertEqual(open(self.copy("data", "gen.txt")).read(), "3")
        self.assertEqual(open(os.path.join(self.private, ".prev", "data", "gen.txt")).read(), "2")
        self.assertEqual(sorted(x for x in os.listdir(self.private) if x.startswith(".") and x != ".lock"), [".prev"])

    def test_a_file_gone_from_the_vps_goes_from_the_next_copy(self):
        self.good()
        os.unlink(os.path.join(self.data, "gen.txt"))
        self.good()
        self.assertFalse(os.path.exists(self.copy("data", "gen.txt")))

    def test_comms_secrets_may_be_missing(self):
        self.assertIn("7 not started", self.good().stdout)


class Refusals(Base):
    def setUp(self):
        super().setUp()
        self.good()
        self.before = tree(os.path.join(self.private, "vps"))
        self.write(os.path.join(self.data, "gen.txt"), b"2")

    def assert_refused(self, done):
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertEqual(tree(os.path.join(self.private, "vps")), self.before)
        self.assertFalse(os.path.exists(os.path.join(self.private, ".new")))
        self.assertNotIn("PEMILIK", done.stdout + done.stderr)

    def test_git_not_ignoring_it(self):
        self.write(os.path.join(self.repo, ".gitignore"), b"!/private/\n")
        done = self.run_mirror()
        self.assert_refused(done)
        self.assertIn("does not ignore", done.stderr)

    def test_a_checkout_whose_deploy_would_send_it(self):
        self.write(os.path.join(self.repo, "Makefile"), b"deploy:\n\trsync -az ./ vps:/opt/\n")
        done = self.run_mirror()
        self.assert_refused(done)
        self.assertIn("make deploy", done.stderr)

    def test_a_host_without_a_ledger(self):
        for side in ("", "-wal", "-shm"):
            if os.path.exists(self.ledger + side):
                os.unlink(self.ledger + side)
        done = self.run_mirror()
        self.assert_refused(done)
        self.assertIn("no ledger.db", done.stdout)

    def test_a_python_that_cannot_serialize(self):
        wrapper = self.write(os.path.join(self.d, "python-lama"),
                             f'#!/bin/bash\n{sys.executable} "$@" | sed \'s/"serialize": true/"serialize": false/\'\n'.encode())
        os.chmod(wrapper, stat.S_IRWXU)
        done = self.run_mirror(REMOTE_PY=wrapper)
        self.assert_refused(done)
        self.assertIn("serialize", done.stdout)

    def test_no_answer_from_the_vps(self):
        done = self.run_mirror(SSH_FAIL="1")
        self.assert_refused(done)
        self.assertIn("does not answer", done.stderr)

    def test_a_ledger_with_fewer_rows(self):
        self.writer.execute("DELETE FROM entries")
        self.writer.commit()
        done = self.run_mirror()
        self.assert_refused(done)
        self.assertIn("ALLOW_SHRINK", done.stdout)
        done = self.run_mirror(ALLOW_SHRINK="1")
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(open(self.copy("data", "gen.txt")).read(), "2")

    def test_a_missing_secret(self):
        os.unlink(os.path.join(self.secrets, "notion_token"))
        done = self.run_mirror()
        self.assert_refused(done)
        self.assertIn("missing: notion_token", done.stdout)

    def test_a_key_that_opens_nothing(self):
        path = os.path.join(self.secrets, "vault_tools_key")
        os.chmod(path, 0o644)
        self.write(path, base64.b64encode(os.urandom(32)))
        done = self.run_mirror()
        self.assert_refused(done)
        self.assertIn("opens none", done.stdout)

    def test_no_stored_number(self):
        self.writer.execute("DELETE FROM payee_secrets")
        self.writer.execute("INSERT INTO entries VALUES ('penyeimbang')")
        self.writer.commit()
        done = self.run_mirror()
        self.assert_refused(done)
        self.assertIn("no stored number", done.stdout)

    def test_a_file_that_did_not_arrive(self):
        done = self.run_mirror(RSYNC_DROP="ingest/" + PRIVATE_NAME)
        self.assert_refused(done)
        self.assertIn("1 missing", done.stdout)

    def rsync_exits(self, *codes):
        path = self.write(os.path.join(self.d, "exits"), "".join(f"{c}\n" for c in codes).encode())
        if os.path.exists(self.rsync_calls):
            os.unlink(self.rsync_calls)
        return path

    def calls(self):
        with open(self.rsync_calls, encoding="utf-8") as f:
            return len(f.readlines())

    def test_rsync_failing(self):
        done = self.run_mirror(RSYNC_EXITS=self.rsync_exits(12))
        self.assert_refused(done)
        self.assertIn("rsync exit 12", done.stderr)
        self.assertEqual(self.calls(), 1)

    def test_rsync_failing_twice_with_23(self):
        done = self.run_mirror(RSYNC_EXITS=self.rsync_exits(23, 23))
        self.assert_refused(done)
        self.assertEqual(self.calls(), 2)

    def test_rsync_23_is_tried_once_more(self):
        done = self.run_mirror(RSYNC_EXITS=self.rsync_exits(23, 0))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.calls(), 3)   # data twice, secrets once

    def test_rsync_24_passes(self):
        done = self.run_mirror(RSYNC_EXITS=self.rsync_exits(24))
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertEqual(self.calls(), 2)


class Worktree(Base):
    def test_a_linked_worktree_fills_the_main_checkout(self):
        wt = os.path.join(self.d, "wt")
        self.git("worktree", "add", "-q", "-b", "kerja", wt)
        script = os.path.join(wt, "scripts", "mirror.sh")
        for _ in range(2):
            done = self.run_mirror(script=script)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self.assertTrue(os.path.isfile(self.copy("MIRROR.json")))
        self.assertFalse(os.path.exists(os.path.join(wt, "private")))
        self.assertEqual(self.git("status", "--short"), "")
        self.assertEqual(self.git("status", "--short", cwd=wt), "")
        with open(os.path.join(self.repo, ".git", "info", "exclude"), encoding="utf-8") as f:
            self.assertEqual(f.read().splitlines().count("/private/"), 1)
        self.git("worktree", "remove", "--force", wt)   # the copy outlives the worktree
        self.assertTrue(os.path.isfile(self.copy("MIRROR.json")))


class Frozen(Base):
    def test_a_stopped_host_carries_the_versions_over(self):
        self.good()
        done = self.good(CONTAINERS="exited", PIP_VERSION="2.0")
        self.assertTrue(self.doc()["frozen"])
        self.assertIn("host frozen", done.stdout)
        self.assertEqual(open(self.copy("host", "pip-vault-tools.txt")).read(), "paket==1.0\n")
        self.assertEqual(self.doc()["facts_failed"], 0)

    def test_a_running_host_is_not_called_frozen(self):
        self.assertIn("host live", self.good().stdout)
        self.assertFalse(self.doc()["frozen"])

    def test_a_file_appearing_during_the_pull(self):
        late = os.path.join(self.data, "muncul-saat-tarik.txt")
        self.good(RSYNC_TOUCH=late)                               # a live host: a later copy will have it
        self.assertFalse(os.path.exists(self.copy("data", "muncul-saat-tarik.txt")))
        os.unlink(late)
        done = self.run_mirror(RSYNC_TOUCH=late, CONTAINERS="exited")   # a frozen host: nothing may have moved
        self.assertEqual(done.returncode, 1, done.stdout + done.stderr)
        self.assertIn("1 missing", done.stdout)
        self.assertNotIn("muncul", done.stdout + done.stderr)

    def test_a_host_fact_failing_swaps_and_ends_non_zero(self):
        self.good()
        os.chmod(os.path.join(self.d, "bin", "ufw"), 0o755)
        self.write(os.path.join(self.d, "bin", "ufw"), b"#!/bin/bash\nexit 1\n")
        self.write(os.path.join(self.data, "gen.txt"), b"2")
        done = self.run_mirror()
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertEqual(open(self.copy("data", "gen.txt")).read(), "2")
        self.assertEqual(open(self.copy("host", "ufw.txt")).read(), "Status: active\n")   # the last good one
        self.assertEqual(self.doc()["facts_failed"], 1)


class Raw(Base):
    def damage(self):
        """Passes the header test, fails to open: what a database with a hot journal looks like to a read-only connection."""
        self.write(os.path.join(self.data, "hermes-vault", "rusak.db"), b"SQLite format 3\0" + b"\xff" * 4096)

    def test_a_database_that_will_not_open_is_carried_raw_and_counted(self):
        self.damage()
        self.write(os.path.join(self.data, "hermes-vault", "rusak.db-wal"), b"sisi")
        done = self.run_mirror()
        self.assertEqual(done.returncode, 3, done.stdout + done.stderr)
        self.assertEqual(open(self.copy("data", "hermes-vault", "rusak.db"), "rb").read()[:16], b"SQLite format 3\0")
        self.assertEqual(open(self.copy("data", "hermes-vault", "rusak.db-wal"), "rb").read(), b"sisi")
        with open(self.copy("host", "db-report.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["raw"], ["hermes-vault/rusak.db"])
        self.assertFalse(self.doc()["clean"])
        self.assertEqual(self.doc()["counts"]["db_raw"], 1)
        self.assertNotIn("rusak", json.dumps(self.doc()))     # MIRROR.json holds no file names
        self.assertIn("1 raw", done.stdout)
        self.assertNotIn("rusak", done.stdout + done.stderr)

    def test_prev_stays_the_last_wholly_clean_copy(self):
        self.good()                                                     # copy 1, clean
        self.damage()
        self.write(os.path.join(self.data, "gen.txt"), b"2")
        self.assertEqual(self.run_mirror().returncode, 3)               # copy 2, raw; 1 moves to .prev
        self.assertEqual(open(os.path.join(self.private, ".prev", "data", "gen.txt")).read(), "1")
        os.unlink(os.path.join(self.data, "hermes-vault", "rusak.db"))
        self.write(os.path.join(self.data, "gen.txt"), b"3")
        self.good()                                                     # copy 3, clean; 2 goes, 1 stays
        self.assertEqual(open(self.copy("data", "gen.txt")).read(), "3")
        self.assertEqual(open(os.path.join(self.private, ".prev", "data", "gen.txt")).read(), "1")
        self.assertFalse(os.path.exists(os.path.join(self.private, ".old")))
        self.write(os.path.join(self.data, "gen.txt"), b"4")
        self.good()                                                     # copy 4; 3 was clean, so .prev moves on
        self.assertEqual(open(os.path.join(self.private, ".prev", "data", "gen.txt")).read(), "3")


class Kill(Base):
    """SIGKILL around each rename of the swap: no copy is ever lost, and the next run puts everything right."""

    def generations(self):
        for gen in ("1", "2"):
            self.write(os.path.join(self.data, "gen.txt"), gen.encode())
            self.good()
        self.write(os.path.join(self.data, "gen.txt"), b"3")

    def whole_copies(self):
        return {g for g in ("vps", ".prev", ".prev.old", ".old", ".new")
                if os.path.isfile(os.path.join(self.private, g, "MIRROR.json"))}

    def killed(self, **env):
        count = os.path.join(self.d, "mv-count")
        if os.path.exists(count):
            os.unlink(count)
        done = self.run_mirror(MV_COUNT=count, **env)
        self.assertEqual(done.returncode, -9, done.stdout + done.stderr)

    def recovers(self, prev="2"):
        self.good()
        self.assertEqual(open(self.copy("data", "gen.txt")).read(), "3")
        self.assertEqual(open(os.path.join(self.private, ".prev", "data", "gen.txt")).read(), prev)
        self.assertEqual(sorted(x for x in os.listdir(self.private) if x.startswith(".") and x != ".lock"), [".prev"])

    def test_before_each_rename(self):
        for n in ("1", "2", "3"):
            with self.subTest(rename=n):
                shutil.rmtree(self.private, True)
                self.generations()
                self.killed(MV_KILL_BEFORE=n)
                self.assertGreaterEqual(len(self.whole_copies()), 2)
                self.recovers()

    def test_after_each_rename(self):
        # after the last rename the killed run had finished its swap, so its copy is the one that moves to .prev
        for n, prev in (("1", "2"), ("2", "2"), ("3", "3")):
            with self.subTest(rename=n):
                shutil.rmtree(self.private, True)
                self.generations()
                self.killed(MV_KILL_AFTER=n)
                self.assertGreaterEqual(len(self.whole_copies()), 2)
                self.recovers(prev)

    def test_with_a_raw_outgoing_copy(self):
        for when, n, prev in (("MV_KILL_BEFORE", "1", "1"), ("MV_KILL_AFTER", "1", "1"), ("MV_KILL_BEFORE", "2", "1"),
                              ("MV_KILL_AFTER", "2", "3")):
            with self.subTest(when=when, rename=n):
                shutil.rmtree(self.private, True)
                self.write(os.path.join(self.data, "gen.txt"), b"1")
                self.good()
                self.write(os.path.join(self.data, "gen.txt"), b"2")
                bad = self.write(os.path.join(self.data, "rusak.db"), b"SQLite format 3\0" + b"\xff" * 4096)
                self.assertEqual(self.run_mirror().returncode, 3)
                os.unlink(bad)
                self.write(os.path.join(self.data, "gen.txt"), b"3")
                self.killed(**{when: n})
                self.good()
                self.assertEqual(open(self.copy("data", "gen.txt")).read(), "3")
                self.assertEqual(open(os.path.join(self.private, ".prev", "data", "gen.txt")).read(), prev)


class Laptop(Base):
    def test_what_lives_only_here_is_kept_and_never_deleted(self):
        ssh = os.path.join(self.home, ".ssh")
        self.write(os.path.join(ssh, "id_ed25519"), b"kunci privat")
        self.write(os.path.join(ssh, "id_ed25519.pub"), b"kunci publik")
        self.write(os.path.join(self.home, "client_secret_ingest.json"), b"{}")
        self.write(os.path.join(self.home, "client_secret.ingest.json"), b"{}")
        project = self.repo.replace("/", "-").replace(".", "-")
        memory = self.write(os.path.join(self.home, ".claude", "projects", project, "memory", "MEMORY.md"), b"m")
        transcript = self.write(os.path.join(self.home, ".claude", "projects", project + "--claude-worktrees-w", "t.jsonl"), b"t")
        engine = self.write(os.path.join(self.home, ".graphify", "repos", "NousResearch", "hermes-agent-v0.22.5", "e.py"), b"e")
        self.write(os.path.join(self.repo, "graphify-out", "graph.json"), b"{}")
        done = self.good()
        self.assertIn("laptop part: 0 missing", done.stdout)
        got = tree(self.private)
        self.assertIn("laptop/id_ed25519.pub", got)
        self.assertIn("laptop/client_secret_ingest.json", got)
        self.assertIn("laptop/client_secret.ingest.json", got)
        self.assertNotIn("laptop/id_ed25519", got)
        self.assertFalse([k for k, v in got.items() if v == b"kunci privat"])
        self.assertEqual(stat.S_IMODE(os.stat(os.path.join(self.private, "laptop", "id_ed25519.pub")).st_mode), 0o600)
        self.assertIn(f"knowledge/claude-projects/{project}/memory/MEMORY.md", got)
        self.assertIn(f"knowledge/claude-projects/{project}--claude-worktrees-w/t.jsonl", got)
        self.assertIn("knowledge/hermes-engine/e.py", got)
        self.assertIn("knowledge/graphify-out/graph.json", got)
        os.unlink(transcript)     # Claude Code's own cleanup after 30 days
        self.write(memory, b"m2")
        self.write(engine, b"e2")
        self.good()
        got = tree(self.private)
        self.assertIn(f"knowledge/claude-projects/{project}--claude-worktrees-w/t.jsonl", got)
        self.assertEqual(got[f"knowledge/claude-projects/{project}/memory/MEMORY.md"], b"m2")

    def test_missing_pieces_are_counted_not_fatal(self):
        done = self.good()
        self.assertRegex(done.stdout, r"laptop part: [1-9]\d* missing")


class HostChecks(Base):
    def test_the_recipe_against_the_live_config(self):
        self.write(os.path.join(self.repo, "host", "etc", "docker", "daemon.json"), b"{}\n")
        self.write(os.path.join(self.repo, "host", "etc", "sudoers.d", "90-personal-agent"), b"template\n")
        self.assertIn("host_etc: ok (1 same)", self.good().stdout)
        self.write(os.path.join(self.repo, "host", "etc", "docker", "daemon.json"), b"{\"berbeda\": 1}\n")
        self.assertIn("host_etc: note (0 same, differs: docker/daemon.json)", self.good().stdout)

    def test_nothing_captured_yet(self):
        self.assertIn("host_etc: note (host/etc not captured yet)", self.good().stdout)

    def test_a_home_env_is_answered_yes_or_no_without_its_value(self):
        self.assertIn("hermes-vault telegram=no anthropic=no", self.good().stdout)
        self.write(os.path.join(self.data, "hermes-vault", ".env"),
                   f"# komentar\nexport TELEGRAM_BOT_TOKEN={SECRET_VALUE}\n".encode())
        done = self.good()
        self.assertIn("hermes_env: note", done.stdout)
        self.assertIn("hermes-vault telegram=yes anthropic=no", done.stdout)
        self.assertNotIn(SECRET_VALUE, done.stdout + done.stderr)


class Target(unittest.TestCase):
    def test_make_mirror_is_a_target(self):
        with open(os.path.join(ROOT, "Makefile"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("\nmirror:\n\tbash scripts/mirror.sh $(VPS_USER)@$(VPS_HOST)\n", text)


if __name__ == "__main__":
    unittest.main()
