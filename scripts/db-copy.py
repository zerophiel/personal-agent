#!/usr/bin/env python3
"""make mirror's database step (scripts/mirror.sh). Every SQLite database under the VPS data folder becomes one clean file
in the new copy, consistent even while its service writes. On the VPS, as the database file's own uid, a read-only
connection is backed up into memory and serialized over ssh: there is no temporary folder there, a dropped connection
leaves nothing behind, and the most it can leave is what any reader may, an owner-owned -shm or empty -wal beside the file.

A *.db that is empty or not SQLite stays an ordinary file for rsync. A database that still fails after a few tries (a hot
journal under mode=ro, damage) is left to rsync with its side files and recorded as raw: the run still swaps, and ends
non-zero. Refuses before copying anything when the host has no ledger (an empty host, or the wrong one) or its Python
cannot serialize. Prints counts only; file names stay in the report and the log inside private/.
Usage: db-copy.py user@host remote_data_root dest_dir report.json excludes0"""
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
import time
import urllib.parse

SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "-o", "ServerAliveInterval=15",
       "-o", "ServerAliveCountMax=4", "-o", "Compression=yes"]
MAGIC = b"SQLite format 3\0"
LEDGER = "vault-tools/ledger.db"
SIDE_FILES = ("-wal", "-shm", "-journal")
ATTEMPTS = 3
PAUSE = float(os.environ.get("MIRROR_DB_PAUSE", "4"))   # about ten seconds in all before a database is carried raw
# The data root is root's alone (0700), so its own uid cannot reach a database without this. It lifts reading only: whatever
# SQLite writes beside the file is still written as that uid, in that uid's folder.
REACH = "--inh-caps=+dac_read_search --ambient-caps=+dac_read_search"
INVENTORY = r"""
import json, os, sqlite3, stat, sys
root = sys.argv[1]
rows = []
for folder, _, names in os.walk(root):
    for name in names:
        if name.endswith((".db", ".sqlite", ".sqlite3")):
            path = os.path.join(folder, name)
            try:
                st = os.lstat(path)
                if stat.S_ISREG(st.st_mode):
                    with open(path, "rb") as f:
                        head = f.read(16)
                    rows.append({"rel": os.path.relpath(path, root), "uid": st.st_uid, "gid": st.st_gid,
                                 "sqlite": head == b"SQLite format 3\0"})
            except OSError:
                pass
print(json.dumps({"serialize": hasattr(sqlite3.Connection, "serialize"), "dbs": rows}))
"""
COPY = r"""
import sqlite3, sys, urllib.parse
src = sqlite3.connect("file:" + urllib.parse.quote(sys.argv[1]) + "?mode=ro", uri=True, timeout=30)
mem = sqlite3.connect(":memory:")
src.backup(mem)
sys.stdout.buffer.write(mem.serialize())
"""


def refuse(reason):
    print(f"mirror: refused: {reason}; the last copy stays as it was")
    sys.exit(1)


def inventory(host, root):
    done = subprocess.run(SSH + [host, f"sudo -n /usr/bin/python3 -I - {shlex.quote(root)}"], input=INVENTORY.encode(),
                          capture_output=True, timeout=180)
    if done.returncode != 0:
        print(done.stderr.decode(errors="replace"), file=sys.stderr)
        refuse(f"reading the database list on the VPS failed (exit {done.returncode})")
    return json.loads(done.stdout)


def sound(path):
    """A whole SQLite file as written by serialize(), which keeps the WAL flag: immutable=1 reads it without a -wal."""
    try:
        with open(path, "rb") as f:
            if f.read(16) != MAGIC:
                return False
        uri = "file:" + urllib.parse.quote(os.path.abspath(path)) + "?immutable=1"
        conn = sqlite3.connect(uri, uri=True)
        try:
            return conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def copy_one(host, root, dest, row):
    """Into a temporary name next to the final one, renamed only when whole: a failed try leaves nothing that looks good."""
    final = os.path.join(dest, row["rel"])
    tmp = final + ".pa-tmp"
    os.makedirs(os.path.dirname(final), exist_ok=True)
    remote = (f"cd / && exec setpriv --reuid={int(row['uid'])} --regid={int(row['gid'])} --clear-groups {REACH} "
              f"/usr/bin/python3 -I -c {shlex.quote(COPY)} {shlex.quote(os.path.join(root, row['rel']))}")
    try:
        with open(tmp, "wb") as out:
            done = subprocess.run(SSH + [host, "sudo -n sh -c " + shlex.quote(remote)], stdout=out,
                                  stderr=subprocess.PIPE, timeout=900)
        if done.returncode == 0 and sound(tmp):
            os.replace(tmp, final)
            return True
        print(f"{row['rel']}: exit {done.returncode}: {done.stderr.decode(errors='replace')[-400:]}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print(f"{row['rel']}: timed out", file=sys.stderr)
    if os.path.exists(tmp):
        os.unlink(tmp)
    return False


def literal(rel):
    """rsync reads a pattern as a wildcard only when it holds one, and only then does a backslash escape."""
    return re.sub(r"([*?\[\\])", r"\\\1", rel) if re.search(r"[*?\[]", rel) else rel


def main():
    host, root, dest, report, excludes = sys.argv[1:6]
    found = inventory(host, root)
    if not found["serialize"]:
        refuse("the VPS's Python has no sqlite3 serialize (3.11 or newer is needed)")
    rows = found["dbs"]
    if not any(r["rel"] == LEDGER and r["sqlite"] for r in rows):
        refuse("the VPS has no ledger.db (an empty host, or the wrong one)")
    clean, raw, plain = [], [], []
    for row in rows:
        if not row["sqlite"]:
            plain.append(row["rel"])
            continue
        for attempt in range(ATTEMPTS):
            if attempt:
                time.sleep(PAUSE)
            if copy_one(host, root, dest, row):
                clean.append(row["rel"])
                break
        else:
            raw.append(row["rel"])
    with open(excludes, "wb") as f:   # what rsync must leave alone: a clean copy is whole, its side files would only mislead
        for rel in clean:
            for suffix in ("",) + SIDE_FILES:
                f.write(os.fsencode("/" + literal(rel + suffix)) + b"\0")
    with open(report, "w", encoding="utf-8") as f:
        json.dump({"clean": clean, "raw": raw, "plain": plain}, f)
    print(f"mirror: databases clean={len(clean)} raw={len(raw)} plain={len(plain)}")


if __name__ == "__main__":
    main()
