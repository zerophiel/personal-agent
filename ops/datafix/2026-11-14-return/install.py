#!/usr/bin/env python3
"""Tahap B4 of the return from kimiclaw: puts the copy that stage.py staged and checked on orig in place of orig's
frozen 9 Nov data, keeping that data as the backup. Runs on orig as root, with every container down.

Install, in this order, stopping at the first failed check:
1. Checks, nothing changed yet: no container runs, no process holds a database, no data unit is active; the staged
   files still match MANIFEST.json; each live database is the one the orig report saw (size and mtime) with an empty
   WAL and journal, and its backup name is free. Each staged ingest file is new to orig, the same as orig's, or
   _events.jsonl whose live content is the start of the staged one (ingest-gmail only appends; the events cursor in
   the ledger counts its lines). Any other file with the same name and other content stops it.
2. The databases: the staged copy is written beside each live file (".return-new", same owner and mode, fsynced,
   checked against MANIFEST); then the empty -wal and -shm go, the live file gets a second name
   (<name>.bak-pre-return-<date>, a hard link: the 9 Nov data as it was), and the copy is renamed over the live name.
3. The ingest folder: new files go in with the owner and mode most files in their folder have, keeping kimi's mtime;
   _events.jsonl is replaced, keeping its owner and mode. Files only orig has stay.
4. Checked in place (immutable=1, nothing written): integrity, and every table's rows equal the staged copy's
   (digests in MANIFEST); every staged ingest file equals its live one. Only then is the staging folder removed.

--check runs step 1 only. --rollback undoes steps 2 and 3 for the databases and _events.jsonl: the returned
database (with any -wal it has) gets the name <name>.return-undone, the backup takes the live name back, and
_events.jsonl is cut back to its 9 Nov length after its start is checked. New ingest files stay: nothing refers to
them then. Prints counts and statuses only; the result JSON (counts, sizes, short hashes) is saved for --rollback.

Usage: install.py ORIG stamp orig_report.json result.json [--check | --rollback]
"""
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("return_probe", os.path.join(HERE, "probe.py"))
probe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe)

# Units that write or read the data while they run; none may be active during the swap.
QUIET_UNITS = ["pa-ingest.service", "pa-uploads.service", "pa-applier.service", "pa-backup.service",
               "pa-notion.service", "pa-gmail-token.service", "pa-ingest-alert.service"]

INSTALL = r'''
S = CFG["staging"]
TAG = CFG["tag"]
DB = {"ledger": CFG["dbs"]["ledger"], "ingest": CFG["dbs"]["ingest"]}
FNAME = {"ledger": "ledger.db", "ingest": "ingest.db"}
LIVE_DIR = CFG["ingest_dir"]
STAGED_DIR = os.path.join(S, "ingest")
EVENTS = "_events.jsonl"
res = {"mode": CFG["mode"]}


def done(ok, why=None):
    res["ok"] = ok
    if why:
        res["stopped"] = why
    print(json.dumps(res))
    sys.exit(0)


def quiet_host():
    p = subprocess.run(["docker", "ps", "-q"], capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        done(False, "docker ps failed")
    if p.stdout.split():
        done(False, "containers are running")
    if holders(list(DB.values())):
        done(False, "a process holds a database")
    for u in CFG["quiet_units"]:
        state = run(["systemctl", "is-active", u]).strip()
        if state in ("active", "activating", "reloading", "deactivating"):
            done(False, u + " is " + state)


def sync_dir(d):
    fd = os.open(d, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_beside(src, dst, uid, gid, mode, mtime=None):
    """src copied next to dst under a temporary name, owner and mode set, fsynced; returns that name."""
    tmp = dst + ".return-new"
    shutil.copyfile(src, tmp)
    os.chown(tmp, uid, gid)
    os.chmod(tmp, mode)
    if mtime is not None:
        os.utime(tmp, (mtime, mtime))
    with open(tmp, "rb") as f:
        os.fsync(f.fileno())
    return tmp


def safe_dir(d):
    return d if d and all(SAFE_PART.fullmatch(x) for x in d.split("/")) else ("." if not d else "[lain]")


def digests(r):
    return {t: hx(sorted(v["rows"].items())) for t, v in r["tables"].items()}


def make_dirs(rel_dir):
    top = os.stat(LIVE_DIR)
    cur = LIVE_DIR
    for part in [x for x in rel_dir.split("/") if x]:
        cur = os.path.join(cur, part)
        if not os.path.isdir(cur):
            os.mkdir(cur)
            os.chown(cur, top.st_uid, top.st_gid)
            os.chmod(cur, stat.S_IMODE(top.st_mode))


def staged_files():
    out = []
    for folder, dnames, fnames in os.walk(STAGED_DIR):
        dnames.sort()
        for name in sorted(fnames):
            out.append(os.path.relpath(os.path.join(folder, name), STAGED_DIR))
    return out


def install():
    # 1. checks; nothing is changed before all of them hold
    quiet_host()
    try:
        with open(os.path.join(S, "MANIFEST.json")) as f:
            man = json.load(f)
    except OSError:
        done(False, "no MANIFEST.json in the staging folder: stage.py did not finish")
    for n in DB:
        if fsha(os.path.join(S, FNAME[n])) != man["files"][FNAME[n]]:
            done(False, n + ": the staged copy differs from MANIFEST")
        live = DB[n]
        st = os.stat(live)
        exp = CFG["live_expected"][n]
        if st.st_size != exp["size"] or int(st.st_mtime) != exp["mtime"]:
            done(False, n + ": the live file changed since the orig report")
        for suf in ("-wal", "-journal"):
            if os.path.lexists(live + suf) and os.path.getsize(live + suf):
                done(False, n + suf + " is not empty")
        if os.path.lexists(live + TAG):
            done(False, n + ": the backup name is taken")
    new, same, events = [], 0, None
    for rel in staged_files():
        p, lp = os.path.join(STAGED_DIR, rel), os.path.join(LIVE_DIR, rel)
        if not stat.S_ISREG(os.lstat(p).st_mode):
            done(False, "ingest: a staged entry is not a plain file")
        if not os.path.lexists(lp):
            new.append(rel)
            continue
        if not stat.S_ISREG(os.lstat(lp).st_mode):
            done(False, "ingest: a live entry is not a plain file")
        if fsha(p) == fsha(lp):
            same += 1
            continue
        if rel == EVENTS:
            with open(lp, "rb") as f:
                old = f.read()
            with open(p, "rb") as f:
                cur = f.read()
            if not cur.startswith(old) or (old and not old.endswith(b"\n")):
                done(False, EVENTS + ": the live file is not the start of the staged one")
            events = {"old_size": len(old), "old_sha": hashlib.sha256(old).hexdigest()[:32], "new_size": len(cur),
                      "old_lines": old.count(b"\n"), "new_lines": cur.count(b"\n")}
            continue
        done(False, "ingest: a file with the same name and other content")
    owners = {}
    for rel in new:
        d = os.path.dirname(rel)
        if d in owners:
            continue
        c = collections.Counter()
        live_d = os.path.join(LIVE_DIR, d)
        if os.path.isdir(live_d):
            for name in os.listdir(live_d):
                s = os.lstat(os.path.join(live_d, name))
                if stat.S_ISREG(s.st_mode) and not name.startswith("_"):
                    c[(s.st_uid, s.st_gid, stat.S_IMODE(s.st_mode))] += 1
        top = os.stat(LIVE_DIR)
        owners[d] = c.most_common(1)[0][0] if c else (top.st_uid, top.st_gid, 0o644)
    res["plan"] = {"new": len(new), "same": same, "events": events,
                   "new_per_folder": dict(collections.Counter(safe_dir(os.path.dirname(r)) for r in new)),
                   "owners": {safe_dir(d): "%d:%d %s" % (o[0], o[1], oct(o[2])) for d, o in owners.items()}}
    if CFG["mode"] == "check":
        done(True)

    # 2. the databases: copies beside the live files first, checked; then swapped in
    tmps = {}
    for n in DB:
        st = os.stat(DB[n])
        tmps[n] = write_beside(os.path.join(S, FNAME[n]), DB[n], st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode))
        if fsha(tmps[n]) != man["files"][FNAME[n]]:
            done(False, n + ": the copy beside the live file differs; nothing swapped")
    for n in DB:
        live = DB[n]
        for suf in ("-wal", "-shm", "-journal"):
            if os.path.lexists(live + suf):
                os.unlink(live + suf)
        os.link(live, live + TAG)
        os.rename(tmps[n], live)
        sync_dir(os.path.dirname(live))
    res["swapped"] = list(DB)

    # 3. the ingest folder
    touched = {LIVE_DIR}
    for rel in new:
        d = os.path.dirname(rel)
        make_dirs(d)
        src, dst = os.path.join(STAGED_DIR, rel), os.path.join(LIVE_DIR, rel)
        uid, gid, mode = owners[d]
        os.rename(write_beside(src, dst, uid, gid, mode, os.stat(src).st_mtime), dst)
        touched.add(os.path.dirname(dst))
    if events:
        lp = os.path.join(LIVE_DIR, EVENTS)
        st = os.stat(lp)
        os.rename(write_beside(os.path.join(STAGED_DIR, EVENTS), lp, st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode)),
                  lp)
    for d in sorted(touched):
        sync_dir(d)

    # 4. checked in place
    check, ok = {}, True
    for n in DB:
        r = db_report(DB[n])
        check[n] = {"integrity": r["integrity"], "rows_as_staged": digests(r) == man["digests"][n],
                    "rows": sum(v["count"] for v in r["tables"].values())}
        ok = ok and r["integrity"] == ["ok"] and check[n]["rows_as_staged"]
    differ = 0
    for rel in staged_files():
        lp = os.path.join(LIVE_DIR, rel)
        if not os.path.isfile(lp) or fsha(lp) != fsha(os.path.join(STAGED_DIR, rel)):
            differ += 1
    check["ingest_files_differ"] = differ
    res["check"] = check
    if not (ok and differ == 0):
        done(False, "the check in place failed; staging kept, the backups are beside the live files")
    shutil.rmtree(S)
    res["staging_removed"] = True
    done(True)

def rollback():
    quiet_host()
    for n in DB:
        live = DB[n]
        if not os.path.isfile(live + TAG):
            done(False, n + ": there is no backup " + TAG)
        for suf in ("", "-wal", "-shm", "-journal"):
            if os.path.lexists(live + ".return-undone" + suf):
                done(False, n + ": the name for the returned copy is taken")
    ev = CFG.get("events")
    lp = os.path.join(LIVE_DIR, EVENTS)
    if ev:
        with open(lp, "rb") as f:
            head = f.read(ev["old_size"])
        if len(head) != ev["old_size"] or hashlib.sha256(head).hexdigest()[:32] != ev["old_sha"]:
            done(False, EVENTS + ": its start is not the file from before the return")
    for n in DB:
        live = DB[n]
        for suf in ("-wal", "-shm", "-journal"):
            if os.path.lexists(live + suf):
                os.rename(live + suf, live + ".return-undone" + suf)
        os.rename(live, live + ".return-undone")
        os.rename(live + TAG, live)
        sync_dir(os.path.dirname(live))
    if ev:
        st = os.stat(lp)
        tmp = lp + ".return-new"
        with open(tmp, "wb") as f:
            f.write(head)
            f.flush()
            os.fsync(f.fileno())
        os.chown(tmp, st.st_uid, st.st_gid)
        os.chmod(tmp, stat.S_IMODE(st.st_mode))
        os.rename(tmp, lp)
        sync_dir(LIVE_DIR)
    res["check"] = {}
    for n in DB:
        r = db_report(DB[n])
        res["check"][n] = {"integrity": r["integrity"], "rows": sum(v["count"] for v in r["tables"].values()),
                           "size": os.path.getsize(DB[n]), "mtime": int(os.stat(DB[n]).st_mtime)}
    done(all(res["check"][n]["integrity"] == ["ok"] for n in DB))


try:
    rollback() if CFG["mode"] == "rollback" else install()
except SystemExit:
    raise
except Exception as e:   # the JSON still comes out, with what was done so far (res) and the plan for --rollback
    res["exception"] = type(e).__name__
    done(False, "broke off with " + type(e).__name__)
'''


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    orig, stamp, report_path, result_path = args[:4]
    mode = "check" if "--check" in argv else "rollback" if "--rollback" in argv else "install"
    with open(report_path, encoding="utf-8") as f:
        rep = json.load(f)
    extra = {"mode": mode, "staging": probe.LAYOUTS["orig"]["staging"].format(stamp=stamp),
             "tag": ".bak-pre-return-" + stamp[:8], "quiet_units": QUIET_UNITS,
             "live_expected": {n: {"size": rep["dbs"][n]["size"], "mtime": rep["dbs"][n]["mtime"]}
                               for n in ("ledger", "ingest")}}
    if mode == "rollback":
        with open(result_path, encoding="utf-8") as f:
            extra["events"] = (json.load(f).get("plan") or {}).get("events")
    done = probe.run_remote("orig", orig, probe.remote_script("orig", main=INSTALL, **extra))
    if done.returncode:
        print(done.stderr.decode(errors="replace")[-800:], file=sys.stderr)
        sys.exit(f"install {mode}: the script on orig broke off (exit {done.returncode}); look before anything else")
    res = json.loads(done.stdout)
    if mode != "rollback":
        with open(result_path, "w", encoding="utf-8") as f:
            json.dump(res, f)
    for k, v in res.items():
        print(f"  {k}: {v}")
    if not res["ok"]:
        sys.exit(f"install {mode}: stopped: {res.get('stopped')}")
    print(f"install {mode}: ok")


if __name__ == "__main__":
    main(sys.argv[1:])
