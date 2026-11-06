#!/usr/bin/env python3
"""make verify: is the bot up as the recipe says? For the end of a rebuild (docs/REBUILD.md) and after a deploy. Read-only on the VPS.
It prints counts, statuses and the names of services, tables, packages and units, never data.

  containers    every service of the main compose file and the front profile runs, and one with a healthcheck is healthy
  ledger        integrity_check, and the rows against private/vps/MIRROR.json. Fewer in total, or a table gone, fails: a restore
                must not lose what the copy holds, and a live bot adds to it. After make restore-restic (--r2) a snapshot may
                rightly be older than the copy, so a difference is only reported.
  packages      pip freeze of the containers that install from a lock equals that lock in this checkout
  timers        every timer and path unit of host/ and of the applier is enabled and active
  failed_units  a pa-* unit that failed: a note, since one stays failed until its next run
  leftovers     nothing of an interrupted make restore under /opt

Exit 0 when nothing failed, otherwise 1. Usage: verify.py user@host [--r2]"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OPT = os.environ.get("RESTORE_REMOTE_OPT", "/opt")                          # a fake VPS in the tests, as in scripts/restore.sh
DATA = os.environ.get("MIRROR_REMOTE_DATA", OPT + "/personal-agent-data")   # as in scripts/mirror.sh
LOCKED = ("vault-tools", "change-proposals")                                # the running services that install from a lock
UNIT_FOLDERS = (ROOT / "host", ROOT / "services" / "applier" / "systemd")
OK, NOTE, FAIL = "ok", "note", "fail"
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=4"]

# Runs as root on the VPS, over stdin. The ledger is opened by its own owner, so no side file can end up owned by root; the
# capability reaches it through the root-only data folder, as in scripts/db-copy.py.
REMOTE = r"""
import glob, json, os, subprocess, sys

ask = json.loads(sys.argv[1])
COUNT = '''
import json, sqlite3, sys, urllib.parse
conn = sqlite3.connect("file:" + urllib.parse.quote(sys.argv[1]) + "?mode=ro", uri=True, timeout=30)
sound = [row[0] for row in conn.execute("PRAGMA integrity_check")] == ["ok"]
tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
print(json.dumps({"sound": sound, "rows": {t: conn.execute('SELECT COUNT(*) FROM "' + t.replace('"', '""') + '"').fetchone()[0]
                                           for t in tables}}))
'''


def run(*command, **options):
    return subprocess.run(command, capture_output=True, text=True, timeout=300, **options)


def services():
    repo = ask["opt"] + "/personal-agent"
    done = run("docker", "compose", "-f", repo + "/compose/docker-compose.yml", "--env-file", repo + "/config/stack.env",
               "--profile", "front", "config", "--services")
    return done.stdout.split() if done.returncode == 0 else None


def containers():
    done = run("docker", "ps", "-a", "--filter", "label=com.docker.compose.project=personal-agent",
               "--filter", "label=com.docker.compose.oneoff=False",
               "--format", '{{.Label "com.docker.compose.service"}}\t{{.State}}\t{{.Status}}')
    rows = {}
    for line in done.stdout.splitlines():
        service, state, status = (line.split("\t") + ["", ""])[:3]
        rows[service] = [state, status]
    return rows


def ledger():
    path = ask["data"] + "/vault-tools/ledger.db"
    try:
        st = os.stat(path)
    except OSError:
        return None
    done = run("setpriv", "--reuid=%d" % st.st_uid, "--regid=%d" % st.st_gid, "--clear-groups", "--inh-caps=+dac_read_search",
               "--ambient-caps=+dac_read_search", sys.executable, "-I", "-c", COUNT, path, cwd="/")
    return json.loads(done.stdout) if done.returncode == 0 else None


def freeze(service):
    done = run("docker", "exec", "personal-agent-%s-1" % service, "pip", "--no-cache-dir", "freeze")
    return done.stdout if done.returncode == 0 else None


failed = run("systemctl", "list-units", "pa-*", "--state=failed", "--no-legend", "--no-pager", "--plain").stdout
print(json.dumps({
    "services": services(),
    "containers": containers(),
    "ledger": ledger(),
    "packages": {service: freeze(service) for service in ask["locked"]},
    "units": {unit: [run("systemctl", "is-enabled", unit).stdout.strip(), run("systemctl", "is-active", unit).stdout.strip()]
              for unit in ask["units"]},
    "failed": [line.split()[0] for line in failed.splitlines() if line.strip()],
    "leftovers": len(glob.glob(glob.escape(ask["opt"]) + "/.pa-*")),
}))
"""


def expected_units() -> list:
    return sorted(p.name for folder in UNIT_FOLDERS for p in folder.glob("pa-*") if p.suffix in (".timer", ".path"))


def ask_the_host(host: str):
    """What the VPS says, or None when it does not answer. What ssh and the remote side print on failure stays out of the output."""
    request = json.dumps({"opt": OPT, "data": DATA, "locked": LOCKED, "units": expected_units()})
    try:
        done = subprocess.run(SSH + [host, "sudo -n /usr/bin/python3 -I - " + shlex.quote(request)], input=REMOTE,
                              capture_output=True, text=True, timeout=900)
        return json.loads(done.stdout) if done.returncode == 0 else None
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def the_copy():
    """private/vps/MIRROR.json of the main checkout, found as scripts/mirror.sh finds it; None when there is no copy."""
    done = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                          capture_output=True, text=True)
    if done.returncode != 0:
        return None
    try:
        return json.loads((Path(done.stdout.strip()).parent / "private" / "vps" / "MIRROR.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def check_containers(services, running):
    if not services:
        return FAIL, "compose cannot list its services here (make sync first?)"

    def up(service):
        state, status = running.get(service, ("", ""))
        return state == "running" and "unhealthy" not in status and "health: starting" not in status

    bad = [s for s in services if not up(s)]
    if bad:
        return FAIL, f"{len(services) - len(bad)} of {len(services)} up; down or not healthy yet: {', '.join(bad)}"
    healthy = sum("(healthy)" in running[s][1] for s in services)
    return OK, f"{len(services)} of {len(services)} up, {healthy} with a healthcheck healthy"


def check_ledger(found, copy, r2):
    if found is None:
        return FAIL, "no ledger, or it cannot be read"
    if not found["sound"]:
        return FAIL, "integrity_check does not pass"
    rows = found["rows"]
    total = sum(rows.values())
    text = f"integrity ok, {len(rows)} tables, {total} rows"
    if copy is None:
        return NOTE, f"{text}, no copy in private/ to compare with"
    counts = copy.get("counts") or {}
    last, tables = counts.get("ledger_rows_total"), counts.get("ledger_rows") or {}
    if last is None:
        return NOTE, f"{text}, the copy holds no count"
    text += f", copy {last}"
    gone = sorted(set(tables) - set(rows))
    lower = sorted(t for t in tables if t in rows and rows[t] < tables[t])
    worse = (["fewer rows than the copy"] if total < last else []) + ([f"tables gone: {', '.join(gone)}"] if gone else [])
    if worse:
        return (NOTE if r2 else FAIL), f"{text}: {'; '.join(worse)}"
    if lower:
        return NOTE, f"{text}; fewer rows than the copy in: {', '.join(lower)}"
    return OK, text


def packages(text):
    """The name==version lines, each name in its normal form, as pip compares them."""
    out = set()
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            name, sep, version = line.partition("==")
            out.add(re.sub(r"[-_.]+", "-", name).lower() + sep + version)
    return out


def check_packages(found):
    equal, bad = [], []
    for service in LOCKED:
        lock = packages((ROOT / "services" / service / "requirements.lock").read_text(encoding="utf-8"))
        text = found.get(service)
        if text is None:
            bad.append(f"{service}: no answer")
        elif packages(text) != lock:
            bad.append(f"{service} differs: {', '.join(sorted(packages(text) ^ lock)[:6])}")
        else:
            equal.append(f"{service} {len(lock)}")
    if bad:
        return FAIL, "; ".join(bad)
    return OK, f"{', '.join(equal)} equal their locks"


def check_timers(units):
    off = sorted(unit for unit, state in units.items() if state != ["enabled", "active"])
    if off:
        return FAIL, f"{len(units) - len(off)} of {len(units)} enabled and active; not: {', '.join(off)}"
    return OK, f"{len(units)} of {len(units)} enabled and active"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host")
    parser.add_argument("--r2", action="store_true", help="after make restore-restic: a difference from the copy is only reported")
    args = parser.parse_args()
    facts = ask_the_host(args.host)
    if facts is None:
        print("verify: the VPS does not answer (ssh or sudo failed)")
        return 1
    results = {
        "containers": check_containers(facts["services"], facts["containers"]),
        "ledger": check_ledger(facts["ledger"], the_copy(), args.r2),
        "packages": check_packages(facts["packages"]),
        "timers": check_timers(facts["units"]),
        "failed_units": (NOTE, f"{len(facts['failed'])}: {', '.join(facts['failed'])}") if facts["failed"] else (OK, "0"),
        "leftovers": (FAIL, f"{facts['leftovers']} under /opt: an interrupted make restore") if facts["leftovers"] else (OK, "0"),
    }
    for name, (status, text) in results.items():
        print(f"{name}: {status} ({text})")
    failed = sum(status == FAIL for status, _ in results.values())
    print(f"verify: {failed} failed" if failed else "verify: all checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
