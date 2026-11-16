#!/usr/bin/env python3
"""Read-only probe of one host before the return from kimiclaw (2026-11-14, Tahap A of the plan in PROGRESS).

From 9 to 14 Nov the vault ran on a second server ("kimi", an OpenClaw host), and the original VPS ("orig") stood
frozen. This probe reports what each holds, so that compare.py can say what the return brings home. It sends one
stdlib script to the host, run as root, and writes the host's answer as JSON.

It only reads:
- orig is frozen, its WAL empty: databases are opened with immutable=1, which writes nothing beside them.
- kimi is live: a database is backed up into memory by its own uid, the way scripts/db-copy.py copies one, so no
  root-owned journal is left next to it. A python without sqlite3 serialize (before 3.11) backs it up into a private
  temporary folder instead, removed right after (--file-copy forces that way, for the tests).
- What leaves a host: row hashes, counts, sizes, schema and table names, and short code values (categories,
  statuses, bank codes). File names are hashed, because statement file names carry the owner's name. Secrets: names
  only, never opened. Process environments and the OpenClaw config are not read.

Usage: probe.py orig|kimi user@host report.json [--file-copy]
The address is never typed: the caller takes it from config/vps.env (orig) or the Tailscale peer list (kimi).
stage.py and install.py reuse the remote functions here (remote_script) with their own main part.
"""
import json
import os
import subprocess
import sys

LAYOUTS = {
    "orig": {
        "sudo": True,
        "db_mode": "immutable",
        "dbs": {"ledger": "/opt/personal-agent-data/vault-tools/ledger.db",
                "ingest": "/opt/personal-agent-data/ingest-state/ingest.db",
                "control": "/opt/personal-agent-data/control-state/control.db"},
        "ingest_dir": "/opt/personal-agent-data/ingest",
        "data_root": "/opt/personal-agent-data",
        "secrets_dir": "/opt/personal-agent-secrets",
        "unit_patterns": ["pa-*"],
        "orig_extras": True,
        "staging": "/opt/.pa-return-{stamp}",   # stage.py and install.py: root-only, on the disk of the data
    },
    "kimi": {
        "sudo": False,
        "db_mode": "backup",
        "dbs": {"ledger": "/opt/vault-tools/data/ledger.db",
                "ingest": "/opt/vault-tools/state/ingest-state/ingest.db"},
        "ingest_dir": "/opt/vault-tools/ingest",
        "data_root": "/opt/vault-tools",
        "secrets_dir": "/opt/vault-tools/secrets",
        "unit_patterns": ["pa-*", "vault-*", "*ingest*", "*gmail*", "openclaw*", "*rincian*", "*finance*"],
        "code_roots": ["/opt/vault-tools", "/opt/ingest-gmail"],
        "listing_roots": ["/opt/vault-tools/data", "/opt/vault-tools/state", "/opt/vault-tools/scripts"],
        "command_roots": ["/opt/vault-tools", "/opt/ingest-gmail", "/root/.openclaw/workspace", "/root/.openclaw/skills"],
        "cron_root": "/root/.openclaw/cron",
    },
}

# Columns whose values are codes. A value new on one host is checked against what the old code knows.
ENUM = {
    "transactions": ["category", "status", "source"], "card_lines": ["category", "kind"],
    "category_rules": ["category"], "category_keywords": ["category"], "statements": ["lines_status"],
    "accounts": ["bank", "kind"], "cards": ["bank", "pay_method"], "payee_secrets": ["bank", "kind"],
    "skipped_files": ["reason"], "thresholds": ["key"], "fund_reports": ["fund"], "change_log": ["tbl", "action"],
    "plan_progress": ["item"], "debt_payments": ["debt_alias", "how"], "subscriptions": ["source", "status"],
    "feature_requests": ["status"], "one_off_bills": ["status", "method"], "processed": ["status"],
    "proposals": ["status"],
}
# Of those, the ones whose short values may be shown (aliases and plan items are never shown: they hold names).
SHOW = {("transactions", "category"), ("transactions", "status"), ("transactions", "source"),
        ("card_lines", "category"), ("card_lines", "kind"), ("category_rules", "category"),
        ("category_keywords", "category"), ("statements", "lines_status"), ("accounts", "bank"), ("accounts", "kind"),
        ("cards", "bank"), ("cards", "pay_method"), ("payee_secrets", "bank"), ("payee_secrets", "kind"),
        ("skipped_files", "reason"), ("thresholds", "key"), ("fund_reports", "fund"), ("change_log", "tbl"),
        ("change_log", "action"), ("debt_payments", "how"), ("subscriptions", "status"), ("feature_requests", "status"),
        ("one_off_bills", "status"), ("one_off_bills", "method"), ("processed", "status"), ("proposals", "status")}
# Per-row tags kept for added and changed rows, all CHECK-bound codes.
TAGS = {"transactions": ["source", "status"], "card_lines": ["kind"], "statements": ["lines_status"],
        "change_log": ["tbl", "action"], "thresholds": ["key"]}
NEEDLES = ["/opt/vault-tools", "/opt/ingest-gmail", "/root/", "/opt/personal-agent", "/ingest/", "/data/", "/tmp/"]

# A database copied by the uid that owns it, read-only: into memory and out as bytes (python 3.11 and later), or
# into a file in a private temporary folder (older python). stage.py sends the same two.
COPY = ("import sqlite3, sys, urllib.parse\n"
        "src = sqlite3.connect('file:' + urllib.parse.quote(sys.argv[1]) + '?mode=ro', uri=True, timeout=30)\n"
        "mem = sqlite3.connect(':memory:')\n"
        "src.backup(mem)\n"
        "sys.stdout.buffer.write(mem.serialize())\n")
COPY_FILE = ("import sqlite3, sys, urllib.parse\n"
             "src = sqlite3.connect('file:' + urllib.parse.quote(sys.argv[1]) + '?mode=ro', uri=True, timeout=30)\n"
             "dst = sqlite3.connect(sys.argv[2])\n"
             "src.backup(dst)\n"
             "dst.close()\n")

REMOTE_FUNCS = r'''
import collections, hashlib, json, os, re, shutil, sqlite3, stat, subprocess, sys, tempfile, urllib.parse
CFG = json.loads(__CFG__)
SAFE = re.compile(r"[a-z][a-z0-9_-]{0,29}")
SAFE_PART = re.compile(r"[A-Za-z0-9._-]{1,40}")


def hx(v):
    b = v if isinstance(v, bytes) else repr(v).encode("utf-8", "surrogatepass")
    return hashlib.sha256(b).hexdigest()[:24]


def fsha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:32]


def side_files(path):
    out = {}
    for suf in ("-wal", "-shm", "-journal"):
        try:
            st = os.lstat(path + suf)
            out[suf] = {"size": st.st_size, "uid": st.st_uid}
        except FileNotFoundError:
            pass
    return out


def as_owner(st, cmd):
    """cmd run by the uid that owns the database, with read access only (as scripts/db-copy.py runs a copy)."""
    if st.st_uid == os.getuid():
        return cmd
    return ["setpriv", "--reuid=%d" % st.st_uid, "--regid=%d" % st.st_gid, "--clear-groups",
            "--inh-caps=+dac_read_search", "--ambient-caps=+dac_read_search"] + cmd


def connect(path):
    if CFG["db_mode"] == "immutable":
        return sqlite3.connect("file:" + urllib.parse.quote(path) + "?mode=ro&immutable=1", uri=True)
    st = os.stat(path)
    if hasattr(sqlite3.Connection, "serialize") and not CFG.get("file_copy"):
        data = subprocess.run(as_owner(st, [sys.executable, "-I", "-c", CFG["copy"], path]), capture_output=True,
                              check=True, cwd="/", timeout=600).stdout
        if data[18:20] == b"\x02\x02":   # the WAL flag: an in-memory copy reads only as a rollback-journal file
            data = data[:18] + b"\x01\x01" + data[20:]
        mem = sqlite3.connect(":memory:")
        mem.deserialize(data)
        return mem
    # No serialize in this python (before 3.11): the owner backs it up into a private temporary folder instead.
    tmp = tempfile.mkdtemp(prefix="pa-return-probe-")
    try:
        os.chown(tmp, st.st_uid, st.st_gid)
        out = os.path.join(tmp, "copy.db")
        subprocess.run(as_owner(st, [sys.executable, "-I", "-c", CFG["copy_file"], path, out]), check=True, cwd="/",
                       timeout=600)
        mem = sqlite3.connect(":memory:")
        src = sqlite3.connect("file:" + urllib.parse.quote(out) + "?mode=ro&immutable=1", uri=True)
        src.backup(mem)
        src.close()
        return mem
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def db_report(path):
    r = {"exists": os.path.isfile(path)}
    if not r["exists"]:
        return r
    st = os.stat(path)
    r.update(size=st.st_size, uid=st.st_uid, gid=st.st_gid, mode=oct(st.st_mode & 0o7777), mtime=int(st.st_mtime),
             side=side_files(path))
    with open(path, "rb") as f:
        head = f.read(100)
    r["wal_flag"] = len(head) >= 20 and head[18] == 2 and head[19] == 2
    conn = connect(path)
    try:
        r["integrity"] = [x[0] for x in conn.execute("PRAGMA integrity_check").fetchall()][:5]
        r["user_version"] = conn.execute("PRAGMA user_version").fetchone()[0]
        objs = sorted(conn.execute("SELECT type, name, tbl_name, sql FROM sqlite_master "
                                   "WHERE name NOT LIKE 'sqlite_%'").fetchall(), key=repr)
        r["schema_hash"] = hx(objs)
        r["objects"] = [[o[0], o[1]] for o in objs]
        r["tables"] = {}
        for t in [o[1] for o in objs if o[0] == "table"]:
            cols = conn.execute('PRAGMA table_info("%s")' % t).fetchall()
            names = [c[1] for c in cols]
            pk = [c[1] for c in sorted((c for c in cols if c[5] > 0), key=lambda c: c[5])]
            rows, tags, dup = {}, {}, 0
            sel = ", ".join('"%s"' % n for n in names)
            tag_cols = [n for n in CFG["tags"].get(t, []) if n in names]
            for row in conn.execute('SELECT %s FROM "%s"' % (sel, t)):
                key = hx([row[names.index(k)] for k in pk]) if pk else hx(list(row))
                if key in rows:
                    dup += 1
                rows[key] = hx(list(row))
                if tag_cols:
                    vals = [row[names.index(c)] for c in tag_cols]
                    tags[key] = "|".join(str(v) if v is not None and SAFE.fullmatch(str(v)) else ("-" if v is None else "[lain]")
                                         for v in vals)
            needles = {}
            for c in names:
                for nd in CFG["needles"]:
                    n = conn.execute('SELECT count(*) FROM "%s" WHERE typeof("%s")=\'text\' AND instr("%s", ?) > 0'
                                     % (t, c, c), (nd,)).fetchone()[0]
                    if n:
                        needles["%s|%s" % (c, nd)] = n
            enum = {}
            for c in CFG["enum"].get(t, []):
                if c not in names:
                    continue
                vals = {}
                for v, n in conn.execute('SELECT "%s", count(*) FROM "%s" GROUP BY 1' % (c, t)):
                    show = [t, c] in CFG["show"] and v is not None and SAFE.fullmatch(str(v)) is not None
                    vals[hx(v)] = {"n": n, "v": str(v) if show else None}
                enum[c] = vals
            r["tables"][t] = {"count": len(rows) + dup, "pk": pk, "dup_keys": dup, "rows": rows, "tags": tags,
                              "needles": needles, "enum": enum}
        if "doc_files" in r["tables"]:
            dirs = collections.Counter()
            for (p,) in conn.execute("SELECT path FROM doc_files"):
                d = os.path.dirname(str(p))
                parts = [x for x in d.split("/") if x]
                dirs["/" + "/".join(parts) if all(SAFE_PART.fullmatch(x) for x in parts) else "[lain]"] += 1
            r["doc_dirs"] = dict(dirs)
    finally:
        conn.close()
    return r


def ingest_report(root):
    if not os.path.isdir(root):
        return None
    files, tops, others = {}, collections.Counter(), 0
    for folder, dnames, fnames in os.walk(root):
        dnames.sort()
        for n in sorted(fnames):
            p = os.path.join(folder, n)
            st = os.lstat(p)
            if not stat.S_ISREG(st.st_mode):
                others += 1
                continue
            rel = os.path.relpath(p, root)
            top = rel.split("/")[0] if "/" in rel else "."
            top = top if SAFE_PART.fullmatch(top) else "[lain]"
            ext = os.path.splitext(n)[1].lower()
            ext = ext if re.fullmatch(r"\.[a-z0-9]{1,6}", ext) else "[lain]"
            files[hx(rel)] = {"size": st.st_size, "sha": fsha(p), "top": top, "ext": ext, "uid": st.st_uid,
                              "gid": st.st_gid, "mode": oct(st.st_mode & 0o7777), "mtime": int(st.st_mtime)}
            tops[top + " " + ext] += 1
    ev = os.path.join(root, "_events.jsonl")
    events = None
    if os.path.isfile(ev):
        with open(ev, "rb") as f:
            lines = f.read().split(b"\n")
        if lines and lines[-1] == b"":
            lines.pop()
        keysets, types = collections.Counter(), collections.Counter()
        for line in lines:
            try:
                e = json.loads(line)
                keysets[",".join(sorted(k if SAFE.fullmatch(k) else "[lain]" for k in e))] += 1
                t = str(e.get("type"))
                types[t if SAFE.fullmatch(t) else "[lain]"] += 1
            except ValueError:
                keysets["[bukan json]"] += 1
        events = {"lines": len(lines), "line_hashes": [hx(x) for x in lines], "keysets": dict(keysets),
                  "types": dict(types), "ends_newline": os.path.getsize(ev) == 0 or open(ev, "rb").read()[-1:] == b"\n"}
    dst = os.stat(root)
    return {"files": files, "tops": dict(tops), "others": others, "events": events,
            "dir": {"uid": dst.st_uid, "gid": dst.st_gid, "mode": oct(dst.st_mode & 0o7777)}}


def run(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def units(patterns):
    res = {}
    for line in run(["systemctl", "list-unit-files", "--no-legend", "--no-pager"] + patterns).splitlines():
        parts = line.split()
        if not parts:
            continue
        name = parts[0]
        u = {"file": parts[1] if len(parts) > 1 else "?", "active": run(["systemctl", "is-active", name]).strip()}
        props = ["UnitFileState", "ActiveState", "SubState"]
        if name.endswith(".timer"):
            props += ["NextElapseUSecRealtime", "LastTriggerUSec", "Unit", "Persistent"]
        if name.endswith(".service"):
            props += ["User", "ExecMainStartTimestamp", "Result", "ExecMainStatus"]
        out = run(["systemctl", "show", name] + ["-p" + p for p in props])
        u["show"] = dict(l.split("=", 1) for l in out.splitlines() if "=" in l)
        if name.endswith(".timer"):
            u["stamp"] = os.path.exists("/var/lib/systemd/timers/stamp-" + name)
        res[name] = u
    return res


def holders(paths):
    targets = [os.path.realpath(p) for p in paths]
    res = []
    for pid in os.listdir("/proc"):
        if not pid.isdigit():
            continue
        try:
            fds = os.listdir("/proc/%s/fd" % pid)
        except OSError:
            continue
        for fd in fds:
            try:
                t = os.readlink("/proc/%s/fd/%s" % (pid, fd))
            except OSError:
                continue
            if any(t == x or t.startswith(x + "-") for x in targets):
                try:
                    comm = open("/proc/%s/comm" % pid).read().strip()
                except OSError:
                    comm = "?"
                res.append({"pid": int(pid), "comm": comm if SAFE_PART.fullmatch(comm) else "[lain]"})
                break
    return res


CODE_EXT = (".py", ".sh", ".service", ".timer")
SKIP = {"venv", ".venv", "data", "secrets", "ingest", "state", "__pycache__", "node_modules", ".git", "logs", "backup",
        "backups"}


def code(roots):
    out = {}
    for root in roots:
        if not os.path.isdir(root):
            out[root] = None
            continue
        files = {}
        for folder, dnames, fnames in os.walk(root):
            dnames[:] = sorted(d for d in dnames if d not in SKIP)
            for n in sorted(fnames):
                keep = n.endswith(CODE_EXT) or n in ("senders.json", "pyproject.toml") or re.fullmatch(r"requirements.*\.txt", n)
                if not keep:
                    continue
                p = os.path.join(folder, n)
                st = os.lstat(p)
                if stat.S_ISREG(st.st_mode) and st.st_size < 5_000_000:
                    files[os.path.relpath(p, root)] = {"sha": fsha(p), "size": st.st_size, "mtime": int(st.st_mtime)}
        out[root] = files
    return out


def listing(roots):
    out = {}
    for root in roots:
        if not os.path.isdir(root):
            out[root] = None
            continue
        rows = []
        for folder, dnames, fnames in os.walk(root):
            dnames.sort()
            for n in sorted(fnames):
                p = os.path.join(folder, n)
                st = os.lstat(p)
                rel = os.path.relpath(p, root)
                ok = all(SAFE_PART.fullmatch(x) for x in rel.split("/"))
                rows.append({"name": rel if ok else "[nama lain]", "size": st.st_size, "mtime": int(st.st_mtime),
                             "uid": st.st_uid})
        out[root] = rows
    return out


SCOPE = re.compile(r"""["']type["']\s*:\s*["'](default|all_private_chats|all_group_chats|all_chat_administrators|chat|chat_administrators|chat_member)["']""")
LANG = re.compile(r"""language_code["']?\s*[:=]\s*["']([a-z]{2})["']""")


def command_files(roots):
    res = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for folder, dnames, fnames in os.walk(root):
            dnames[:] = sorted(d for d in dnames if d not in SKIP)
            for n in sorted(fnames):
                p = os.path.join(folder, n)
                try:
                    if os.path.getsize(p) > 2_000_000:
                        continue
                    text = open(p, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                if "setMyCommands" in text or "set_my_commands" in text or "deleteMyCommands" in text:
                    rel = os.path.relpath(p, root)
                    res.append({"root": root, "file": rel if all(SAFE_PART.fullmatch(x) for x in rel.split("/")) else "[nama lain]",
                                "scopes": sorted(set(SCOPE.findall(text))), "langs": sorted(set(LANG.findall(text))),
                                "delete": "deleteMyCommands" in text})
    return res


KEYWORDS = ("vault", "ledger", "rincian", "tagihan", "ingest", "gmail", "keuangan", "finance", "gajian", "statement",
            "rencana", "harian")


def cron_jobs(root):
    if not root or not os.path.isdir(root):
        return None
    jobs = []
    for folder, dnames, fnames in os.walk(root):
        for n in sorted(fnames):
            if not n.endswith(".json"):
                continue
            try:
                data = json.load(open(os.path.join(folder, n)))
            except (OSError, ValueError):
                continue
            items = data.get("jobs") if isinstance(data, dict) else data
            for j in items if isinstance(items, list) else []:
                if not isinstance(j, dict):
                    continue
                text = json.dumps(j).lower()
                sched = j.get("schedule")
                jobs.append({"enabled": j.get("enabled"),
                             "schedule": {k: v for k, v in sched.items() if k in ("kind", "expr", "every", "everyMs", "tz")}
                             if isinstance(sched, dict) else None,
                             "hits": [k for k in KEYWORDS if k in text]})
    return jobs


def secret_names(d):
    if not d or not os.path.isdir(d):
        return None
    out = []
    for n in sorted(os.listdir(d)):
        st = os.lstat(os.path.join(d, n))
        out.append({"name": n if SAFE_PART.fullmatch(n) else "[nama lain]", "size_gt0": st.st_size > 0,
                    "mode": oct(st.st_mode & 0o7777), "mtime": int(st.st_mtime)})
    return out


def orig_extras():
    x = {}
    x["containers_running"] = len(run(["docker", "ps", "-q"]).split())
    x["containers_all"] = len(run(["docker", "ps", "-aq"]).split())
    data = CFG["data_root"]
    appr = os.path.join(data, "control-state", "approved")
    ids = [int(m.group(1)) for n in (os.listdir(appr) if os.path.isdir(appr) else [])
           if (m := re.fullmatch(r"(\d{1,9})\.json", n))]
    done = lambda i: any(os.path.exists(os.path.join(data, "applier", k, "%d.json" % i)) for k in ("applied", "failed", "skipped"))
    x["applier"] = {"approved": len(ids), "pending": sum(1 for i in ids if not done(i))}
    sec = CFG["secrets_dir"]
    x["secrets"] = {}
    for n in ("telegram_vault_token", "gmail_ingest_token", "telegram_front_token", "telegram_control_token"):
        try:
            st = os.stat(os.path.join(sec, n))
            x["secrets"][n] = {"size_gt0": st.st_size > 0, "mtime": int(st.st_mtime), "mode": oct(st.st_mode & 0o7777)}
        except FileNotFoundError:
            x["secrets"][n] = None
    for n in ("vault.env", "front.env"):
        try:
            st = os.stat(os.path.join(data, n))
            x[n] = {"mtime": int(st.st_mtime), "mode": oct(st.st_mode & 0o7777)}
        except FileNotFoundError:
            x[n] = None
    return x
'''

REMOTE_MAIN = r'''
out = {"host": {}, "dbs": {}}
try:
    out["host"]["os"] = [l.split("=", 1)[1].strip().strip('"') for l in open("/etc/os-release") if l.startswith("PRETTY_NAME=")][0]
except Exception:
    out["host"]["os"] = "?"
out["host"].update(python=sys.version.split()[0], sqlite=sqlite3.sqlite_version,
                   serialize=hasattr(sqlite3.Connection, "serialize"))
du = shutil.disk_usage("/")
out["host"].update(disk_free_gb=round(du.free / 1e9, 1), disk_used_pct=round(100.0 * du.used / du.total, 1))
for name, path in CFG["dbs"].items():
    try:
        out["dbs"][name] = db_report(path)
    except Exception as e:
        out["dbs"][name] = {"error": type(e).__name__}
out["ingest"] = ingest_report(CFG["ingest_dir"])
out["units"] = units(CFG["unit_patterns"])
out["holders"] = holders(list(CFG["dbs"].values()))
out["secret_names"] = secret_names(CFG.get("secrets_dir"))
if CFG.get("code_roots"):
    out["code"] = code(CFG["code_roots"])
if CFG.get("listing_roots"):
    out["listing"] = listing(CFG["listing_roots"])
if CFG.get("command_roots"):
    out["command_files"] = command_files(CFG["command_roots"])
if CFG.get("cron_root"):
    out["cron"] = cron_jobs(CFG["cron_root"])
    out["root_crontab_lines"] = sum(1 for l in run(["crontab", "-l"]).splitlines() if l.strip() and not l.startswith("#"))
if CFG.get("orig_extras"):
    out["extras"] = orig_extras()
json.dump(out, sys.stdout)
'''


def remote_script(side, main=REMOTE_MAIN, **extra):
    """The remote functions with this side's layout, and a main part: the probe's own, or a caller's (stage.py)."""
    cfg = dict(LAYOUTS[side])
    cfg.update(enum=ENUM, show=[list(x) for x in sorted(SHOW)], tags=TAGS, needles=NEEDLES, copy=COPY,
               copy_file=COPY_FILE)
    cfg.update(extra)
    return (REMOTE_FUNCS + main).replace("__CFG__", repr(json.dumps(cfg)), 1)


SSH = os.environ.get("PA_SSH", "ssh -o BatchMode=yes -o ConnectTimeout=15").split()   # tests set a fake one


def run_remote(side, host, script, timeout=1800):
    """script run by the host's python as root; returns the CompletedProcess (stdout is the script's JSON)."""
    py = "sudo -n /usr/bin/python3 -I -" if LAYOUTS[side]["sudo"] else "/usr/bin/python3 -I -"
    return subprocess.run(SSH + [host, py], input=script.encode(), capture_output=True, timeout=timeout)


def main():
    side, host, report = sys.argv[1:4]
    done = run_remote(side, host, remote_script(side, file_copy="--file-copy" in sys.argv))
    if done.returncode != 0:
        print(f"probe {side}: exit {done.returncode}", file=sys.stderr)
        print(done.stderr.decode(errors="replace")[-600:], file=sys.stderr)
        sys.exit(1)
    data = json.loads(done.stdout)
    with open(report, "w", encoding="utf-8") as f:
        json.dump(data, f)
    print(f"probe {side}: ok, {len(done.stdout)} bytes of report")


if __name__ == "__main__":
    main()
