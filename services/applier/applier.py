"""applier (M3): puts a change the owner approved in control onto the VPS. Root host unit, stdlib only, no LLM.

pa-applier.path starts it when control records an approval, pa-applier.timer every five minutes. Each approved id is
handled once, in order:
 1. control-state/approved/<id>.json (a small regular file, never a link) must match control.db, opened read-only:
    status approved, the same proposal, the same review;
 2. control's own validate() passes and the change is one this unit applies: zone front, files in FRONT_FILES only, a
    diff the owner was shown whole before the buttons, no hidden characters, and every file still as it was when that
    diff was made (review.base_sha256). Anything else is refused: a human builds it from the proposal;
 3. in a temporary copy of the tree, tests/test_zones.py passes with the change, and a squid conf passes `squid -k parse`
    in a throwaway container without a network;
 4. the old files are kept (backup/<id>.json), the new ones written atomically with the old owner and mode, and the
    service recreated (a file mount keeps the old inode until then) and checked: running, not restarting, front back on
    Telegram from a new process, and the files inside the container the new ones;
 5. a failed check puts the old files back and recreates the service again; there is no second attempt. A run that
    stopped between the backup and the outcome (power, a kill) is undone the same way at the next run, unless a file
    is neither the old nor the new version by then: that one is left alone and reported for a human.
The outcome is kept in applied/, failed/ or skipped/ (root only) and, for control to report, in outcome/<id>.json
(mounted read-only into control). Approvals decided before outcome/applier.json's time are skipped: they predate this
unit (#1 and #2 were tests). The deployed tree is rsynced from the repo, so a deploy holds this unit off while it runs
and refuses while an applied change is not in the repo yet (scripts/deploy-guard.sh, make applied-pull).
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import fcntl
import hashlib
import importlib.util
import json
import logging
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

log = logging.getLogger("applier")

REPO, DATA = Path("/opt/personal-agent"), Path("/opt/personal-agent-data")
# What this unit may write: the compose service each file is mounted into, and where. Narrower than control's PATHS on
# purpose, so a control bug cannot widen it: front only; skills wait for a skills mount, vault and comms for a human.
FRONT_FILES = {
    "services/hermes/front/config.yaml": ("front", "/opt/data/config.yaml"),
    "services/hermes/front/SOUL.md": ("front", "/opt/data/SOUL.md"),
    "config/squid/front.conf": ("squid-front", "/etc/squid/squid.conf"),
}
BODY_KEYS = ("summary", "permission_diff", "risk_notes", "rollback", "zone", "change_type", "files")
STAGE = ("tests", "compose", "host", "services/hermes", "config/squid")     # what tests/test_zones.py reads
ID_FILE = re.compile(r"(\d{1,9})\.json")
HOLD_SECONDS = 30 * 60          # a deploy hold older than this is left over from a deploy that stopped halfway
HEALTH_SECONDS, STEADY_SECONDS, POLL_SECONDS = 240, 20, 5
MAX_FILE_BYTES = 1_000_000

# tests/test_zones.py in the staged copy; prints one JSON line (test names only, never file text)
_ZONE_TESTS = (
    "import json, unittest\n"
    "suite = unittest.defaultTestLoader.discover('tests', pattern='test_zones.py')\n"
    "res = unittest.TextTestRunner(stream=open('/dev/null', 'w')).run(suite)\n"
    "print(json.dumps({'run': res.testsRun, 'skipped': len(res.skipped),\n"
    "                  'failed': [t.id().rsplit('.', 1)[-1] for t, _ in res.failures + res.errors]}))\n")
# `squid -k parse` exits 0 even when it drops an http_access line it cannot read, so every line it prints must be one of
# these: the file being processed, or the two warnings of a container without a network (seen on the VPS 2026-11-01).
_SQUID_PREFIX = re.compile(r"^[0-9/: .]*(?:kid\d+)?\|\s*")
_SQUID_OK = re.compile(r"Processing( Configuration File)?: |WARNING: '[^']*' rDNS test failed|"
                       r"WARNING: Could not determine this machines public hostname")


def squid_complaints(output: str) -> list[str]:
    lines = (_SQUID_PREFIX.sub("", line).strip() for line in output.splitlines())
    return [line for line in lines if line and not _SQUID_OK.match(line)]


def run(argv: list[str], cwd: Path | None = None, timeout: int = 300) -> tuple[int, str]:
    """A command's exit code and output; a failure is returned, never raised (a raise after the files are written would
    skip the rollback)."""
    try:
        r = subprocess.run(argv, cwd=cwd, timeout=timeout, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except OSError as e:        # e.g. docker missing
        return 127, type(e).__name__
    return r.returncode, r.stdout + r.stderr


def load_control(path: Path):
    """control.py from the deployed tree: the proposal rules are control's own."""
    spec = importlib.util.spec_from_file_location("control_for_applier", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(data: bytes | None) -> str | None:
    return None if data is None else hashlib.sha256(data).hexdigest()


def stamp(text) -> float:
    """An ISO-8601 time as epoch seconds; 0 when missing or unreadable."""
    try:
        return datetime.fromisoformat(text).timestamp()
    except (TypeError, ValueError):
        return 0.0


def write_json(path: Path, rec: dict, mode: int) -> None:
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())
        os.fchmod(f.fileno(), mode)
    os.replace(tmp, path)


class Applier:
    def __init__(self, repo: Path = REPO, data: Path = DATA, runner=run, clock=time.time, sleep=time.sleep):
        self.repo = Path(os.path.realpath(repo))
        self.state, self.cstate = data / "applier", data / "control-state"
        self.outcome, self.front_home = data / "applier" / "outcome", data / "hermes-front"
        self.run, self.clock, self.sleep = runner, clock, sleep
        self.control = load_control(self.repo / "services/control/control.py")

    # --- the deployed tree -------------------------------------------------------------------------------------------
    def regular(self, path: Path) -> os.stat_result:
        """A file of the tree, reached without a link and itself a regular file; OSError otherwise."""
        if os.path.realpath(path) != str(path):
            raise OSError(f"{path.relative_to(self.repo)} goes through a link")
        st = os.lstat(path)
        if not stat.S_ISREG(st.st_mode):
            raise OSError(f"{path.relative_to(self.repo)} is not a regular file")
        return st

    def read(self, rel: str) -> bytes | None:
        path = self.repo / rel
        try:
            self.regular(path)
        except FileNotFoundError:
            return None
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as f:
            return f.read(MAX_FILE_BYTES + 1)

    def write(self, rel: str, data: bytes) -> None:
        """Atomically, with the owner and mode the file had (the next rsync from the repo finds it as it left it)."""
        path = self.repo / rel
        st = self.regular(path)
        tmp = path.with_name(f".{path.name}.applier.tmp")
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
                os.fchown(f.fileno(), st.st_uid, st.st_gid)
                os.fchmod(f.fileno(), stat.S_IMODE(st.st_mode))
            os.replace(tmp, path)
        except BaseException:
            with contextlib.suppress(OSError):
                os.unlink(tmp)
            raise
        dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

    def compose(self, *args: str) -> list[str]:
        return ["docker", "compose", "-f", str(self.repo / "compose/docker-compose.yml"), "--env-file",
                str(self.repo / "config/stack.env"), "--profile", "front", *args]

    # --- control's records -------------------------------------------------------------------------------------------
    def installed_at(self) -> float | None:
        try:
            with open(self.outcome / "applier.json", encoding="utf-8") as f:
                return stamp(json.load(f)["installed_at"]) or None
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def mark_installed(self) -> None:
        """The install time, once: approvals decided before it are never applied."""
        if self.installed_at() is None:
            write_json(self.outcome / "applier.json", {"installed_at": self.control.now()}, 0o644)

    def pending(self) -> list[int]:
        approved = self.cstate / "approved"
        for d in (self.cstate, approved):
            if not stat.S_ISDIR(os.lstat(d).st_mode):
                raise OSError(f"{d} is not a folder")
        ids = sorted(int(m.group(1)) for name in os.listdir(approved) if (m := ID_FILE.fullmatch(name)))
        return [i for i in ids if not any((self.state / k / f"{i}.json").exists() for k in ("applied", "failed", "skipped"))]

    def db_row(self, pid: int):
        """(status, body, review) from control.db, opened read-only: a root connection that may write would leave a
        root-owned journal next to it, and control (uid 10001) could no longer write its own database."""
        db = self.cstate / "control.db"
        if not stat.S_ISREG(os.lstat(db).st_mode):
            raise sqlite3.OperationalError("control.db is not a regular file")
        con = sqlite3.connect(f"file:{urllib.parse.quote(str(db))}?mode=ro", uri=True, timeout=10)
        try:
            return con.execute("SELECT status, body, review FROM proposals WHERE id=?", (pid,)).fetchone()
        finally:
            con.close()

    # --- the run -----------------------------------------------------------------------------------------------------
    @contextlib.contextmanager
    def locked(self, wait: float = 60):
        """The lock scripts/deploy-guard.sh takes too (flock on the same file)."""
        fd = os.open(self.state / "lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            deadline = time.monotonic() + wait
            while True:
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() > deadline:
                        raise TimeoutError("applier lock busy") from None
                    time.sleep(1)
            yield
        finally:
            os.close(fd)

    def held(self) -> bool:
        try:
            since = float((self.state / "deploy-hold").read_text().strip() or 0)
        except FileNotFoundError:
            return False
        except ValueError:
            since = 0.0
        if self.clock() - since < HOLD_SECONDS:
            return True
        log.warning("applier: ignoring a deploy hold older than %d minutes", HOLD_SECONDS // 60)
        return False

    def run_once(self) -> list[tuple[int, str]]:
        installed = self.installed_at()
        if installed is None:
            log.info("applier: not installed (no outcome/applier.json); nothing done")
            return []
        for d in ("applied", "failed", "skipped", "backup", "tmp"):
            os.makedirs(self.state / d, mode=0o700, exist_ok=True)
        done = []
        for pid in self.pending():
            with self.locked():          # per id, so a deploy can start between two applies
                if self.held():
                    log.info("applier: a deploy is running; approvals wait for it")
                    break
                stopped = (self.state / "backup" / f"{pid}.json").exists()
                status = self.recover(pid) if stopped else self.handle(pid, installed)
            if status:
                log.info("applier: #%d %s", pid, status)
                done.append((pid, status))
        return done

    def handle(self, pid: int, installed: float) -> str | None:
        """One approved id to its outcome; None leaves it for the next run (control.db could not be read now)."""
        try:
            rec = self.control.read_proposal(self.cstate / "approved" / f"{pid}.json")
        except (ValueError, OSError) as e:      # a link, a folder, oversized or broken JSON
            return self.refuse(pid, None, f"file persetujuannya tidak terbaca ({e})")
        if not isinstance(rec, dict):
            return self.refuse(pid, None, "file persetujuannya bukan objek JSON")
        decided = stamp(rec.get("decided_at"))
        if not decided:
            return self.refuse(pid, None, "waktu persetujuannya tidak terbaca")
        if decided < installed:
            return self.skip(pid, "approved before the applier was installed")
        try:
            row = self.db_row(pid)
        except sqlite3.Error as e:
            log.warning("applier: control.db not readable (%s); #%d waits for the next run", type(e).__name__, pid)
            return None
        try:
            p = self.control.validate({k: rec[k] for k in BODY_KEYS if k in rec})
        except ValueError as e:
            return self.refuse(pid, None, f"tidak lolos aturan control: {e}")
        if row is None or row[0] != "approved" or rec.get("id") != pid or rec.get("status") != "approved":
            return self.refuse(pid, p, "control.db tidak mencatatnya sebagai disetujui")
        review = rec.get("review")
        if review is None and row[2] is None:
            return self.refuse(pid, p, "usulan ini masuk sebelum control menampilkan diff; minta agen mengirim ulang")
        if json.loads(row[1]) != p or not isinstance(review, dict) or row[2] is None or json.loads(row[2]) != review:
            return self.refuse(pid, p, "isi file persetujuannya berbeda dengan control.db")
        why = self.not_applicable(p, review) or self.precheck(p)
        if why:
            return self.refuse(pid, p, why)
        return self.apply(pid, p, rec)

    def not_applicable(self, p: dict, review: dict) -> str | None:
        if p["zone"] != "front":
            return f"zona {p['zone']} tidak diterapkan otomatis; manusia yang membangunnya dari usulan ini"
        if p["change_type"] == "credential":
            return "nilai rahasia tidak lewat tombol; minta dipasang dengan make secret-set"
        if p["change_type"] == "skill":
            return "skill belum bisa diterapkan otomatis (folder skills front belum di-mount)"
        paths = [f["path"] for f in p["files"]]
        if not paths or any(x not in FRONT_FILES for x in paths):
            return "ada file di luar yang boleh diubah applier"
        if review.get("diff_shown") is not True or review.get("why"):
            return f"diff-nya tidak tampil utuh sebelum tombol ({review.get('why') or 'tanpa diff'})"
        base = review.get("base_sha256")
        if not isinstance(base, dict) or set(base) != set(paths):
            return "diff-nya tidak mencakup semua file usulan"
        if any(self.control.hidden_chars(f["path"], f["content"]) for f in p["files"]):
            return "isinya mengandung karakter yang tidak terlihat di Telegram"
        try:
            now = {x: sha(self.read(x)) for x in paths}
        except OSError as e:
            return f"file yang terpasang tidak aman ditulis ({e})"
        missing = [x for x in paths if now[x] is None]
        if missing:
            return f"{missing[0]} tidak ada di server"
        changed = [x for x in paths if now[x] != base[x]]
        if changed:
            return f"{changed[0]} sudah berubah sejak diff-nya kamu lihat; minta agen mengirim ulang usulannya"
        if all(sha(f["content"].encode()) == base[f["path"]] for f in p["files"]):
            return "isinya sama dengan yang sudah terpasang"
        return None

    def precheck(self, p: dict) -> str | None:
        """Before anything changes: the service is up (one stopped on purpose is not started by an apply), the zone
        rules hold with the change, and a squid conf parses."""
        for service in sorted({FRONT_FILES[f["path"]][0] for f in p["files"]}):
            if not self.container(service):
                return f"{service} sedang tidak jalan; usulan ini menunggu manusia"
        why = self.zone_tests(p["files"])
        for f in p["files"]:
            if why is None and FRONT_FILES[f["path"]][0].startswith("squid-"):
                why = self.squid_parse(f["content"], FRONT_FILES[f["path"]][0])
        return why

    def zone_tests(self, files: list[dict]) -> str | None:
        """tests/test_zones.py on a copy of the tree with the change in it: a change that breaks a zone rule the repo
        states (no shell, only the proposal tool, cardblock on, private ranges blocked first, ...) is refused."""
        with tempfile.TemporaryDirectory(prefix="pa-applier-") as tmp:
            try:
                for rel in STAGE:
                    shutil.copytree(self.repo / rel, Path(tmp) / rel, symlinks=True,
                                    ignore=shutil.ignore_patterns("__pycache__"))
                for f in files:
                    (Path(tmp) / f["path"]).write_bytes(f["content"].encode())
            except OSError as e:
                return f"salinan untuk tes aturan zona gagal dibuat ({type(e).__name__})"
            rc, out = self.run([sys.executable, "-I", "-c", _ZONE_TESTS], cwd=Path(tmp), timeout=120)
        try:
            res = json.loads(out.strip().splitlines()[-1])
            ran, skipped, failed = int(res["run"]), int(res["skipped"]), list(res["failed"])
        except (ValueError, IndexError, KeyError, TypeError):
            return "tes aturan zona tidak bisa dijalankan"
        if failed:
            return "melanggar aturan zona: " + ", ".join(map(str, failed))[:300]
        if rc != 0 or ran == 0 or skipped:      # PyYAML missing skips every test: that is no pass
            return "tes aturan zona tidak berjalan utuh"
        return None

    def squid_parse(self, content: str, service: str) -> str | None:
        """The proposed conf through the squid image that service runs, in a throwaway container without a network."""
        cid = self.container(service)
        rc, image = self.run(["docker", "inspect", "-f", "{{.Config.Image}}", cid], timeout=60) if cid else (1, "")
        if rc != 0 or not image.strip():
            return f"{service} tidak jalan, konfigurasinya tidak bisa diuji"
        # under the state folder, not /tmp: the Docker daemon resolves the mount source outside this unit's namespaces
        os.makedirs(self.state / "tmp", mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="squid-", dir=self.state / "tmp") as tmp:
            conf = Path(tmp) / "squid.conf"
            conf.write_bytes(content.encode())
            os.chmod(conf, 0o644)
            rc, out = self.run(["docker", "run", "--rm", "--network", "none", "--cap-drop", "ALL", "--security-opt",
                                "no-new-privileges:true", "--entrypoint", "squid", "-v", f"{conf}:/etc/squid/squid.conf:ro",
                                image.strip(), "-k", "parse"], timeout=120)
        bad = squid_complaints(out)
        if rc != 0 or bad:
            return "squid menolak konfigurasinya: " + (bad[0] if bad else f"kode keluar {rc}")[:200]
        return None

    def apply(self, pid: int, p: dict, rec: dict) -> str:
        paths = [f["path"] for f in p["files"]]
        new = {f["path"]: f["content"].encode() for f in p["files"]}
        old = {x: self.read(x) for x in paths}
        services = sorted({FRONT_FILES[x][0] for x in paths})
        # before the first write, and the outcome after the last: a backup without an outcome is an apply that stopped
        write_json(self.state / "backup" / f"{pid}.json",
                   {"id": pid, "proposal": p, "files": [{"path": x, "sha256": sha(old[x]), "sha256_after": sha(new[x]),
                                                         "b64": base64.b64encode(old[x]).decode()} for x in paths]}, 0o600)
        started = self.control.now()
        problem = self.change(new, services)
        files = [{"path": x, "sha256_before": sha(old[x]), "sha256_after": sha(new[x])} for x in paths]
        if problem is None:
            write_json(self.state / "applied" / f"{pid}.json",
                       {"id": pid, "status": "applied", "proposal": p, "files": files, "services": services,
                        "decided_at": rec["decided_at"], "started_at": started, "applied_at": self.control.now()}, 0o600)
            self.publish(pid, "applied", p, services)
            return "applied"
        log.warning("applier: #%d failed (%s); putting the old files back", pid, problem)
        again = self.change(old, services)
        status = "rolled_back" if again is None else "rollback_failed"
        reason = problem if again is None else f"{problem}; pengembalian: {again}"
        write_json(self.state / "failed" / f"{pid}.json",
                   {"id": pid, "status": status, "reason": reason, "zone": p["zone"], "change_type": p["change_type"],
                    "files": files, "services": services, "started_at": started, "at": self.control.now()}, 0o600)
        self.publish(pid, status, p, services, reason)
        return status

    def recover(self, pid: int) -> str:
        """An apply that stopped halfway (the machine went down, the unit was killed): the old files go back if what is
        installed is still the old or the new version, never over a third one (a deploy since). Not tried again."""
        try:
            with open(self.state / "backup" / f"{pid}.json", "rb") as f:     # root-only folder, written by apply()
                backup = json.loads(f.read())
            p = backup["proposal"]
            old = {x["path"]: base64.b64decode(x["b64"], validate=True) for x in backup["files"]}
            known = {x["path"]: (x["sha256"], x["sha256_after"]) for x in backup["files"]}
            if not old or any(rel not in FRONT_FILES or sha(old[rel]) != known[rel][0] for rel in old):
                raise ValueError("backup does not match its hashes")
        except (OSError, ValueError, KeyError, TypeError) as e:
            reason = f"penerapannya terhenti di tengah jalan dan cadangannya tidak terbaca ({type(e).__name__})"
            write_json(self.state / "failed" / f"{pid}.json", {"id": pid, "status": "rollback_failed", "reason": reason,
                                                                "at": self.control.now()}, 0o600)
            self.publish(pid, "rollback_failed", None, [], reason)
            return "rollback_failed"
        services = sorted({FRONT_FILES[rel][0] for rel in old})
        try:
            now = {rel: sha(self.read(rel)) for rel in old}
        except OSError:
            now = {}
        if any(now.get(rel) not in known[rel] for rel in old):
            status = "rollback_failed"
            reason = "penerapannya terhenti di tengah jalan dan file-nya sudah diubah dari luar applier, jadi tidak dikembalikan"
        else:
            log.warning("applier: #%d stopped halfway earlier; putting the old files back", pid)
            again = self.change(old, services)
            status = "rolled_back" if again is None else "rollback_failed"
            reason = "penerapannya terhenti di tengah jalan" + ("" if again is None else f"; pengembalian: {again}")
        write_json(self.state / "failed" / f"{pid}.json",
                   {"id": pid, "status": status, "reason": reason, "zone": p["zone"], "change_type": p["change_type"],
                    "files": [{"path": rel, "sha256_before": known[rel][0], "sha256_after": known[rel][1]} for rel in old],
                    "services": services, "at": self.control.now()}, 0o600)
        self.publish(pid, status, p, services, reason)
        return status

    def change(self, files: dict[str, bytes], services: list[str]) -> str | None:
        """Write the files, recreate the services and check them: None, else what failed. Never raises, so a failure
        after the first write always reaches the rollback."""
        try:
            before = {s: self.marker(s) for s in services}
            since = self.clock()
            for rel, data in files.items():
                self.write(rel, data)
            rc, _ = self.run(self.compose("up", "-d", "--no-deps", "--force-recreate", "--wait", "--wait-timeout",
                                          str(HEALTH_SECONDS), *services), cwd=self.repo, timeout=HEALTH_SECONDS + 90)
            if rc != 0:
                return f"docker compose up gagal (kode {rc})"
            for s in services:
                why = self.healthy(s, before[s], since) or self.mounted(s, files)
                if why:
                    return why
            return None
        except Exception as e:
            return f"kesalahan tak terduga ({type(e).__name__})"

    def container(self, service: str) -> str:
        rc, out = self.run(self.compose("ps", "-q", service), cwd=self.repo, timeout=60)
        return out.split()[0] if rc == 0 and out.split() else ""

    def gateway(self) -> dict:
        try:
            with open(self.front_home / "gateway_state.json", encoding="utf-8") as f:
                g = json.load(f)
            return g if isinstance(g, dict) else {}
        except (OSError, ValueError):
            return {}

    def telegram(self) -> dict:
        tg = (self.gateway().get("platforms") or {}).get("telegram")
        return tg if isinstance(tg, dict) else {}

    def marker(self, service: str) -> dict:
        """What must differ once the service is recreated: its container and, for front, the process that writes its
        Telegram state (gateway_state.json outlives the container, so an old "connected" proves nothing)."""
        tg = self.telegram() if service == "front" else {}
        return {"container": self.container(service), "writer": (tg.get("writer_pid"), tg.get("writer_start_time"))}

    def check(self, service: str, before: dict, since: float) -> str | None:
        cid = self.container(service)
        if not cid:
            return f"{service} tidak jalan"
        if cid == before["container"]:
            return f"{service} belum dibuat ulang"
        rc, out = self.run(["docker", "inspect", "-f", "{{.State.Running}} {{.RestartCount}}", cid], timeout=60)
        if rc != 0 or out.split() != ["true", "0"]:
            return f"{service} tidak jalan stabil"
        if service == "front":
            g, tg = self.gateway(), self.telegram()
            if g.get("gateway_state") != "running" or tg.get("state") != "connected":
                return "front belum tersambung ke Telegram"
            if (tg.get("writer_pid"), tg.get("writer_start_time")) == before["writer"]:
                return "status Telegram front masih dari proses lama"
            if stamp(tg.get("updated_at")) < since:
                return "status Telegram front belum diperbarui sejak dibuat ulang"
        else:
            rc, _ = self.run(["docker", "exec", cid, "squid", "-k", "check"], timeout=60)
            if rc != 0:
                return f"{service}: squid tidak jalan"
        return None

    def healthy(self, service: str, before: dict, since: float) -> str | None:
        deadline = self.clock() + HEALTH_SECONDS
        while (why := self.check(service, before, since)) is not None:
            if self.clock() >= deadline:
                return why
            self.sleep(POLL_SECONDS)
        self.sleep(STEADY_SECONDS)          # still up a little later: not a crash loop
        return self.check(service, before, since)

    def mounted(self, service: str, files: dict[str, bytes]) -> str | None:
        """The service reads the files just written, not the inode it was started with."""
        cid = self.container(service)
        for rel, data in files.items():
            svc, inside = FRONT_FILES[rel]
            if svc == service:
                rc, out = self.run(["docker", "exec", cid, "sha256sum", inside], timeout=60)
                if rc != 0 or out.split()[:1] != [sha(data)]:
                    return f"{service} belum membaca versi baru {rel}"
        return None

    # --- outcomes ----------------------------------------------------------------------------------------------------
    def publish(self, pid: int, status: str, p: dict | None, services: list[str], reason: str = "") -> None:
        """What control tells the owner (no file contents); readable by control's uid through its read-only mount."""
        write_json(self.outcome / f"{pid}.json",
                   {"id": pid, "status": status, "zone": p and p["zone"], "change_type": p and p["change_type"],
                    "paths": [f["path"] for f in p["files"]] if p else [], "services": services, "reason": reason,
                    "at": self.control.now()}, 0o644)

    def refuse(self, pid: int, p: dict | None, reason: str) -> str:
        write_json(self.state / "failed" / f"{pid}.json",
                   {"id": pid, "status": "refused", "reason": reason, "zone": p and p["zone"],
                    "change_type": p and p["change_type"], "at": self.control.now()}, 0o600)
        self.publish(pid, "refused", p, [], reason)
        return "refused"

    def skip(self, pid: int, reason: str) -> str:
        write_json(self.state / "skipped" / f"{pid}.json",
                   {"id": pid, "status": "skipped", "reason": reason, "at": self.control.now()}, 0o600)
        return "skipped"

    # --- install -----------------------------------------------------------------------------------------------------
    def self_check(self) -> bool:
        """What the applier needs on this host, checked without changing anything (services/applier/install.sh)."""
        results = []

        def check(name, fn):
            try:
                why = fn()
            except Exception as e:  # a check that cannot run is a failed check
                why = f"{type(e).__name__}: {e}"
            results.append(why is None)
            print(("ok   " if why is None else "FAIL ") + name + ("" if why is None else f": {why}"))

        def quietly(fn):
            return lambda: (fn(), None)[1]

        check("control.db opens read-only, with control's review column", quietly(lambda: self.db_row(0)))
        check("control-state/approved is a folder", quietly(self.pending))
        check("the files the applier may write are regular files",
              lambda: None if all(self.read(x) is not None for x in FRONT_FILES) else "one is missing")
        check("tests/test_zones.py passes on the installed tree", lambda: self.zone_tests([]))
        check("front and squid-front run", lambda: None if self.container("front") and self.container("squid-front")
              else "not running")
        check("squid -k parse accepts the installed front.conf (its output is all the applier knows)",
              lambda: self.squid_parse(self.read("config/squid/front.conf").decode(), "squid-front"))
        check("front's gateway state says Telegram is connected",
              lambda: None if self.telegram().get("state") == "connected" else "not connected")
        check("the state folders are root's", lambda: None if all(
            os.lstat(d).st_uid == 0 and stat.S_IMODE(os.lstat(d).st_mode) == m
            for d, m in ((self.state, 0o700), (self.outcome, 0o755))) else "owner or mode differs")
        return all(results)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Apply the changes the owner approved in control (docs/SECURITY.md).")
    ap.add_argument("--check", action="store_true", help="check what the applier needs; change nothing")
    ap.add_argument("--mark-installed", action="store_true",
                    help="record the install time, once (approvals decided before it are never applied)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    a = Applier()
    if args.check:
        return 0 if a.self_check() else 1
    if args.mark_installed:
        a.mark_installed()
        return 0
    a.run_once()
    return 0


if __name__ == "__main__":
    sys.exit(main())
