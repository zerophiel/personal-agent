#!/usr/bin/env python3
"""make mirror's checks (scripts/mirror.sh), on the laptop, on the copy about to become private/vps. One line per check,
counts and statuses only: never a value, never the name of a data file (statement names hold the owner's name and
account fragments). Writes MIRROR.json into the new copy.
Exit 0: all good. Exit 3: good enough to swap, but a database is carried raw or a host fact failed. Exit 1: do not swap.
Usage: mirror-check.py --new DIR --prev MIRROR.json --repo DIR --frozen 0|1 --facts-failed N"""
import argparse
import base64
import importlib.util
import json
import os
import re
import sqlite3
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone

MAGIC = b"SQLite format 3\0"
DB_SUFFIXES = (".db", ".sqlite", ".sqlite3")   # as scripts/db-copy.py
LEDGER = "vault-tools/ledger.db"
SIDE_FILES = ("-wal", "-shm", "-journal")
TEMP_NAME = re.compile(r"(\.tmp[^/]*|\.pa-tmp|(^|/)tmp[^/]*)$")   # a live host's files that come and go between listings
ENV_KEYS = {"telegram": "TELEGRAM_BOT_TOKEN", "anthropic": "ANTHROPIC_API_KEY"}
FAIL, NOTE, OK = "fail", "note", "ok"


def immutable(path):
    return sqlite3.connect("file:" + urllib.parse.quote(os.path.abspath(path)) + "?immutable=1", uri=True)


def integrity_ok(path):
    try:
        with open(path, "rb") as f:
            if f.read(16) != MAGIC:
                return False
        conn = immutable(path)
        try:
            return conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        finally:
            conn.close()
    except (OSError, sqlite3.Error):
        return False


def starts_as_sqlite(path):
    try:
        with open(path, "rb") as f:
            return f.read(16) == MAGIC
    except OSError:
        return False


def settle_report(new, report):
    """scripts/db-copy.py listed the databases before its copies and before the pull, so its report can be behind the copy, and
    this writes it back corrected. A database that appeared since came through rsync with its side files at different moments, so
    it is raw, whatever the list called it. One that left was carried by nothing, so it is not raw, except the ledger: that stays
    in the list for check_ledger to refuse the copy."""
    data = os.path.join(new, "data")
    report["raw"] = [rel for rel in report["raw"] if rel == LEDGER or os.path.lexists(os.path.join(data, rel))]
    known = set(report["clean"]) | set(report["raw"])
    for folder, _, files in os.walk(data):
        for name in files:
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, data)
            if rel not in known and name.endswith(DB_SUFFIXES) and not os.path.islink(path) and starts_as_sqlite(path):
                report["raw"].append(rel)
                report["plain"] = [other for other in report["plain"] if other != rel]
    with open(os.path.join(new, "host", "db-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f)


def check_databases(new, report):
    bad = sum(not integrity_ok(os.path.join(new, "data", rel)) for rel in report["clean"])
    text = f"{len(report['clean'])} clean, {len(report['raw'])} raw (not checked), {len(report['plain'])} plain"
    return (FAIL, f"{text}, {bad} failed integrity_check") if bad else (OK, text)


def read_manifest(repo):
    rows = []
    with open(os.path.join(repo, "config", "secrets.manifest"), encoding="utf-8") as f:
        for line in f:
            fields = line.split("#", 1)[0].split()
            if fields:
                rows.append(fields)   # name, how, zone, mode
    return rows


def check_secrets(new, repo):
    folder = os.path.join(new, "secrets")
    have = set(os.listdir(folder))
    rows = read_manifest(repo)
    missing = sorted(r[0] for r in rows if r[0] not in have and r[2] != "comms")
    waiting = sum(r[0] not in have and r[2] == "comms" for r in rows)
    extra = sorted(have - {r[0] for r in rows})
    empty = sorted(n for n in have if os.path.isfile(os.path.join(folder, n)) and not os.path.getsize(os.path.join(folder, n)))
    text = f"{len(have) - len(extra)} named in the manifest, {len(missing)} missing, {waiting} not started"
    if extra:
        text += f", extra: {' '.join(extra)}"
    if empty:
        text += f", empty: {' '.join(empty)}"
    if missing:
        return FAIL, f"{text}; missing: {' '.join(missing)}"
    return OK, text


def listing(path):
    """{(root label, relative path): kind} from make mirror's ownership list; os.walk's names survive the JSON unchanged."""
    out = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            out[(row["r"], row["p"])] = row["t"]
    return out


def copied(new):
    out = set()
    for label in ("data", "secrets"):
        root = os.path.join(new, label)
        out.add((label, ""))
        for folder, dirs, files in os.walk(root):
            out.update((label, os.path.relpath(os.path.join(folder, n), root)) for n in dirs + files)
    return out


def check_files(new, report, frozen):
    """A path in both listings must be in the copy. On a frozen host nothing moved, so the copy must match exactly."""
    before = listing(os.path.join(new, "host", "ownership.before.jsonl"))
    after = listing(os.path.join(new, "host", "ownership.jsonl"))
    have = copied(new)
    replaced = {("data", rel + s) for rel in report["clean"] for s in SIDE_FILES}   # a clean copy has no side files
    stable = {k for k, kind in before.items()
              if k in after and kind != "o" and after[k] != "o" and not k[1].endswith(SIDE_FILES) and not TEMP_NAME.search(k[1])}
    missing = stable - have
    extra = 0
    if frozen:
        wanted = {k for k, kind in after.items() if kind != "o" and k not in replaced}
        missing = wanted - have
        extra = len(have - wanted)
    sockets = sum(kind == "o" for kind in after.values())
    text = (f"{sum(k[0] == 'data' for k in have) - 1} data, {sum(k[0] == 'secrets' for k in have) - 1} secrets, "
            f"{len(missing)} missing, {sockets} sockets left out, host {'frozen' if frozen else 'live'}")
    if frozen:
        text += f", {extra} unlisted"
    return (FAIL if missing or extra else OK), text


def check_ledger(new, report, prev_total):
    if LEDGER not in report["clean"]:
        if not os.path.lexists(os.path.join(new, "data", LEDGER)):
            return FAIL, "not in the copy: it left the host during the pull", None
        return NOTE, "carried raw, rows not counted", None
    conn = immutable(os.path.join(new, "data", LEDGER))
    try:
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        rows = {t: conn.execute('SELECT COUNT(*) FROM "' + t.replace('"', '""') + '"').fetchone()[0] for t in tables}
    finally:
        conn.close()
    total = sum(rows.values())
    was = "no earlier copy" if prev_total is None else f"last copy {prev_total}"
    if prev_total is not None and total < prev_total:
        if os.environ.get("ALLOW_SHRINK") != "1":
            return FAIL, f"{total} rows, {was}: fewer than before (the wrong host? ALLOW_SHRINK=1 accepts it)", rows
        return NOTE, f"{total} rows, {was}: fewer than before, accepted by ALLOW_SHRINK=1", rows
    return OK, f"{total} rows, {was}", rows


def check_payee_key(new, repo, report):
    """vault_tools_key must open the stored numbers: a ledger whose key is lost cannot pay anyone. The numbers stay in this
    function's memory, compared with their last four digits, and no exception text is printed."""
    if LEDGER not in report["clean"]:
        return NOTE, "ledger carried raw, not checked"
    sys.dont_write_bytecode = True   # no __pycache__ left in the checkout
    try:
        spec = importlib.util.spec_from_file_location("payee_vault", os.path.join(
            repo, "services", "vault-tools", "vault_tools", "payee_vault.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except ImportError:
        return FAIL, "this Python lacks the cryptography package (MIRROR_PY=<python with it> make mirror)"
    try:
        with open(os.path.join(new, "secrets", "vault_tools_key"), encoding="utf-8") as f:
            key = base64.b64decode(f.read().strip())
        conn = immutable(os.path.join(new, "data", LEDGER))
        conn.row_factory = sqlite3.Row
        vault = module.PayeeVault(conn, key)
        rows = conn.execute("SELECT alias,last4 FROM payee_secrets").fetchall()
    except Exception as e:
        return FAIL, f"could not read the key or the numbers ({type(e).__name__})"
    if not rows:
        return FAIL, "no stored number to test the key against (the wrong host?)"
    opened = 0
    for row in rows:
        try:
            opened += vault.reveal(row["alias"])[-4:] == row["last4"]
        except Exception:
            pass
    conn.close()
    if not opened:
        return FAIL, f"the key opens none of the {len(rows)} stored numbers"
    return (OK if opened == len(rows) else NOTE), f"the key opens {opened} of {len(rows)} stored numbers"


def check_hermes_env(new):
    """A home .env overrides the rendered env (Hermes loads it with override), so a rotated token would not take effect.
    Only whether the two names are assigned there; the values are not looked at."""
    data = os.path.join(new, "data")
    parts, found = [], False
    for home in sorted(n for n in os.listdir(data) if n.startswith("hermes-")):
        try:
            with open(os.path.join(data, home, ".env"), "rb") as f:
                text = f.read().decode("utf-8", "replace")
        except OSError:
            parts.append(f"{home} no .env")
            continue
        hits = {label: bool(re.search(rf"(?m)^[ \t]*(?:export[ \t]+)?{key}[ \t]*=", text)) for label, key in ENV_KEYS.items()}
        found = found or any(hits.values())
        parts.append(home + " " + " ".join(f"{k}={'yes' if v else 'no'}" for k, v in hits.items()))
    return (NOTE if found else OK), "; ".join(parts)


def check_host_etc(new, repo):
    """The recipe in host/etc against the live config, names only. A difference is for the owner to decide, not a failure.
    host/etc/sudoers.d is a template for the login account, so it never equals the live file."""
    theirs = os.path.join(repo, "host", "etc")
    if not os.path.isdir(theirs):
        return NOTE, "host/etc not captured yet"
    same, differ = 0, []
    for folder, _, files in os.walk(theirs):
        for name in files:
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, theirs)
            if rel.startswith("sudoers.d" + os.sep):
                continue
            try:
                with open(path, "rb") as a, open(os.path.join(new, "host", "live", "etc", rel), "rb") as b:
                    if a.read() == b.read():
                        same += 1
                        continue
            except OSError:
                pass
            differ.append(rel)
    return (NOTE, f"{same} same, differs: {' '.join(sorted(differ))}") if differ else (OK, f"{same} same")


def previous_total(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)["counts"]["ledger_rows_total"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def git_state(repo):
    def run(*args):
        done = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
        return done.stdout.strip() if done.returncode == 0 else ""
    return run("rev-parse", "--short=12", "HEAD") or "unknown", bool(run("status", "--porcelain"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", required=True)
    ap.add_argument("--prev", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--frozen", type=int, required=True)
    ap.add_argument("--facts-failed", type=int, required=True)
    a = ap.parse_args()
    with open(os.path.join(a.new, "host", "db-report.json"), encoding="utf-8") as f:
        report = json.load(f)
    settle_report(a.new, report)
    results = {}
    last_total = previous_total(a.prev)
    status, text, rows = check_ledger(a.new, report, last_total)
    results["ledger"] = (status, text)
    results["databases"] = check_databases(a.new, report)
    results["secrets"] = check_secrets(a.new, a.repo)
    results["files"] = check_files(a.new, report, bool(a.frozen))
    results["payee_key"] = check_payee_key(a.new, a.repo, report)
    results["hermes_env"] = check_hermes_env(a.new)
    results["host_etc"] = check_host_etc(a.new, a.repo)
    for name, (status, text) in results.items():
        print(f"{name}: {status} ({text})")
    if any(status == FAIL for status, _ in results.values()):
        return 1
    sha, dirty = git_state(a.repo)
    have = copied(a.new)
    doc = {"pulled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git_sha": sha, "git_dirty": dirty,
           "frozen": bool(a.frozen), "clean": not report["raw"], "facts_failed": a.facts_failed,
           "counts": {"db_clean": len(report["clean"]), "db_raw": len(report["raw"]), "db_plain": len(report["plain"]),
                      "files_data": sum(k[0] == "data" for k in have) - 1,
                      "files_secrets": sum(k[0] == "secrets" for k in have) - 1,
                      # a raw ledger is not counted, and the next run still compares with the last count
                      "ledger_rows_total": sum(rows.values()) if rows is not None else last_total, "ledger_rows": rows},
           "checks": {name: {"status": status, "detail": text} for name, (status, text) in results.items()}}
    with open(os.path.join(a.new, "MIRROR.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    return 3 if report["raw"] or a.facts_failed else 0


if __name__ == "__main__":
    sys.exit(main())
