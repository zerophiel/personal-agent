#!/usr/bin/env python3
"""Tahap B2 of the return from kimiclaw: copies kimi's frozen vault data into a root-only staging folder on orig and
checks it there. Orig's live data is not touched; that is install.py's step.

Nothing lands on the laptop. Each database is backed up on kimi by the uid that owns it, as scripts/db-copy.py
copies one, and the bytes are piped through this process straight into the staging folder; the ingest folder goes
the same way as a tar stream.

Before it: kimi frozen (B1: its finance timers and vault-tools stopped, nothing holding a database), then probed
again:  probe.py kimi KIMI kimi_frozen.json
The staged copy must equal that report row for row (row hashes), file for file (sha256) and line for line
(_events.jsonl), and its schemas must equal orig's live ones. Only then are the staged names made final and a
MANIFEST.json written for install.py. The staging folder must not exist yet: a new stamp for each attempt.
Prints counts and statuses only.

Usage: stage.py KIMI ORIG kimi_frozen.json stamp [--file-copy]     (KIMI, ORIG: user@host, never typed; see probe.py)
"""
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("return_probe", os.path.join(HERE, "probe.py"))
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

PY = "/usr/bin/python3"
NAMES = (("ledger", "ledger.db"), ("ingest", "ingest.db"))

# On kimi, as root: one database out on stdout, copied by the uid that owns it (no root-owned journal beside it).
SEND = r'''
import os, shutil, sqlite3, subprocess, sys, tempfile
COPY, COPY_FILE = __COPY__, __COPY_FILE__
path, how = sys.argv[1], sys.argv[2]
st = os.stat(path)
def as_owner(cmd):
    if st.st_uid == os.getuid():
        return cmd
    return ["setpriv", "--reuid=%d" % st.st_uid, "--regid=%d" % st.st_gid, "--clear-groups",
            "--inh-caps=+dac_read_search", "--ambient-caps=+dac_read_search"] + cmd
if how == "memory" and hasattr(sqlite3.Connection, "serialize"):
    sys.exit(subprocess.run(as_owner([sys.executable, "-I", "-c", COPY, path]), cwd="/").returncode)
tmp = tempfile.mkdtemp(prefix="pa-return-copy-")
try:
    os.chown(tmp, st.st_uid, st.st_gid)
    out = os.path.join(tmp, "copy.db")
    rc = subprocess.run(as_owner([sys.executable, "-I", "-c", COPY_FILE, path, out]), cwd="/").returncode
    if rc:
        sys.exit(rc)
    with open(out, "rb") as f:
        shutil.copyfileobj(f, sys.stdout.buffer)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
'''

# On orig, as root: the staged copy against kimi's frozen report and orig's live schemas; final names and MANIFEST only
# when every check holds.
VALIDATE = r'''
S = CFG["staging"]
exp = CFG["expected"]
res, ok, reports = {}, True, {}
for name, fname in (("ledger", "ledger.db"), ("ingest", "ingest.db")):
    r = db_report(os.path.join(S, fname + ".part"))
    reports[name] = r
    e = exp["dbs"][name]
    live = db_report(CFG["dbs"][name])
    rows_same = set(r.get("tables", {})) == set(e["tables"]) and all(
        r["tables"][t]["rows"] == e["tables"][t]["rows"] for t in e["tables"])
    res[name] = {"integrity": r.get("integrity"), "schema_as_kimi": r.get("schema_hash") == e["schema_hash"],
                 "schema_as_orig": r.get("schema_hash") == live.get("schema_hash"),
                 "user_version_as_orig": r.get("user_version") == live.get("user_version"),
                 "rows_as_kimi": rows_same, "rows": sum(t["count"] for t in r.get("tables", {}).values())}
    ok = ok and r.get("integrity") == ["ok"] and rows_same and all(
        res[name][k] for k in ("schema_as_kimi", "schema_as_orig", "user_version_as_orig"))
ing = ingest_report(os.path.join(S, "ingest"))
files = {k: v["sha"] for k, v in ing["files"].items()} if ing else {}
res["ingest_files"] = {"staged": len(files), "expected": len(exp["ingest_files"]), "same": files == exp["ingest_files"],
                       "not_plain": ing["others"] if ing else None}
res["events_same"] = ((ing or {}).get("events") or {}).get("line_hashes") == exp["events"]
ok = ok and ing is not None and res["ingest_files"]["same"] and res["events_same"] and ing["others"] == 0
res["same_disk_as_data"] = os.stat(S).st_dev == os.stat(CFG["data_root"]).st_dev
if ok:
    man = {"stamp": CFG["stamp"], "files": {}, "counts": {}, "digests": {}}
    for name, fname in (("ledger", "ledger.db"), ("ingest", "ingest.db")):
        os.rename(os.path.join(S, fname + ".part"), os.path.join(S, fname))
        man["files"][fname] = fsha(os.path.join(S, fname))
        man["counts"][name] = {t: v["count"] for t, v in reports[name]["tables"].items()}
        man["digests"][name] = {t: hx(sorted(v["rows"].items())) for t, v in reports[name]["tables"].items()}
    man["ingest_files"] = files
    with open(os.path.join(S, "MANIFEST.json"), "w") as f:
        json.dump(man, f)
        f.flush()
        os.fsync(f.fileno())
res["ok"] = ok
print(json.dumps(res))
'''


def stream(src_host, src_cmd, dst_host, dst_cmd, timeout=3600):
    """src's stdout into dst's stdin, through this process's pipes only. Returns both exit codes and stderr tails."""
    with tempfile.TemporaryFile() as a_err, tempfile.TemporaryFile() as b_err:
        a = subprocess.Popen(probe.SSH + [src_host, src_cmd], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=a_err)
        b = subprocess.Popen(probe.SSH + [dst_host, dst_cmd], stdin=a.stdout, stdout=subprocess.DEVNULL, stderr=b_err)
        a.stdout.close()
        try:
            b.wait(timeout=timeout)
            a.wait(timeout=60)
        except subprocess.TimeoutExpired:
            a.kill()
            b.kill()
            a.wait()
            b.wait()
        tails = []
        for f in (a_err, b_err):
            f.seek(0)
            tails.append(f.read().decode(errors="replace")[-300:])
    return a.returncode, b.returncode, tails[0], tails[1]


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    kimi, orig, frozen_path, stamp = args[:4]
    how = "file" if "--file-copy" in argv else "memory"
    lay = probe.LAYOUTS
    staging = lay["orig"]["staging"].format(stamp=stamp)
    with open(frozen_path, encoding="utf-8") as f:
        frozen = json.load(f)
    for n, _ in NAMES:
        d = frozen["dbs"].get(n, {})
        if d.get("error") or not d.get("exists") or not d.get("tables"):
            sys.exit(f"stage: the frozen kimi report lacks a readable {n} database; nothing copied")
    if frozen.get("holders"):
        sys.exit(f"stage: on kimi something still held a database ({len(frozen['holders'])}); freeze first")
    if not frozen.get("ingest"):
        sys.exit("stage: the frozen kimi report has no ingest folder; nothing copied")
    sudo = "sudo -n " if lay["orig"]["sudo"] else ""
    made = subprocess.run(probe.SSH + [orig, f"{sudo}mkdir -m 0700 {shlex.quote(staging)}"], capture_output=True)
    if made.returncode:
        sys.exit(f"stage: could not make a new staging folder on orig (exit {made.returncode}; it must not exist yet)")
    print("stage: staging folder made on orig")
    send = SEND.replace("__COPY__", repr(probe.COPY), 1).replace("__COPY_FILE__", repr(probe.COPY_FILE), 1)
    for name, fname in NAMES:
        src = f"{PY} -I -c {shlex.quote(send)} {shlex.quote(lay['kimi']['dbs'][name])} {how}"
        part = shlex.quote(f"{staging}/{fname}.part")
        dst = f"{sudo}sh -c {shlex.quote('umask 077 && cat > ' + part)}"
        ra, rb, ea, eb = stream(kimi, src, orig, dst)
        print(f"stage {fname}: kimi exit {ra}, orig exit {rb}")
        if ra or rb:
            print(ea, eb, file=sys.stderr)
            sys.exit(f"stage: {fname} did not arrive whole; staging stays for a look, live data untouched")
    parent, base = os.path.split(lay["kimi"]["ingest_dir"].rstrip("/"))
    src = f"tar -C {shlex.quote(parent)} -cf - {shlex.quote(base)}"
    target = shlex.quote(f"{staging}/ingest")
    dst = f"{sudo}sh -c {shlex.quote(f'umask 077 && mkdir {target} && tar -C {target} --strip-components=1 --no-same-owner -xf -')}"
    ra, rb, ea, eb = stream(kimi, src, orig, dst)
    print(f"stage ingest folder: kimi exit {ra}, orig exit {rb}")
    if ra or rb:
        print(ea, eb, file=sys.stderr)
        sys.exit("stage: the ingest folder did not arrive whole; staging stays for a look, live data untouched")
    expected = {"dbs": {n: {"schema_hash": frozen["dbs"][n]["schema_hash"],
                            "tables": {t: {"rows": v["rows"]} for t, v in frozen["dbs"][n]["tables"].items()}}
                        for n, _ in NAMES},
                "ingest_files": {k: v["sha"] for k, v in frozen["ingest"]["files"].items()},
                "events": (frozen["ingest"].get("events") or {}).get("line_hashes")}
    script = probe.remote_script("orig", main=VALIDATE, staging=staging, expected=expected, stamp=stamp)
    done = probe.run_remote("orig", orig, script)
    if done.returncode:
        print(done.stderr.decode(errors="replace")[-600:], file=sys.stderr)
        sys.exit(f"stage: the check on orig failed to run (exit {done.returncode}); live data untouched")
    res = json.loads(done.stdout)
    for k, v in res.items():
        print(f"  {k}: {v}")
    if not res["ok"]:
        sys.exit("stage: the staged copy does not match kimi's frozen state; not made final, live data untouched")
    print(f"stage: staged and checked, MANIFEST written ({len(expected['ingest_files'])} ingest files)")


if __name__ == "__main__":
    main(sys.argv[1:])
