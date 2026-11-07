#!/usr/bin/env python3
"""make restore-restic's database step, as root on the new VPS over a restored snapshot (scripts/restore.sh). Restic backs up
the files as they lay, so a database may come with a -wal holding committed rows, or a journal holding a half-done write. A
-wal is never deleted by hand: each database is opened read-write as its own uid, as its service would, so SQLite itself
replays or rolls back, then passes PRAGMA integrity_check. A failure stops the restore: an older snapshot is the way on.
Prints counts; names go to stderr, which scripts/restore.sh keeps in private/.
Usage: recover-dbs.py data_folder"""
import os
import stat
import subprocess
import sys

MAGIC = b"SQLite format 3\0"
LEDGER = os.path.join("vault-tools", "ledger.db")
RECOVER = r"""
import sqlite3, sys
conn = sqlite3.connect(sys.argv[1], timeout=30)
print(conn.execute("PRAGMA integrity_check").fetchone()[0])
conn.close()
"""


def databases(root):
    for folder, _, names in os.walk(root):
        for name in names:
            if name.endswith((".db", ".sqlite", ".sqlite3")):
                path = os.path.join(folder, name)
                st = os.lstat(path)
                if stat.S_ISREG(st.st_mode):
                    with open(path, "rb") as f:
                        if f.read(16) == MAGIC:
                            yield path, st


def recovered(path, st):
    # The data root and the upload folder are root's alone, so its own uid cannot reach a database without the capability. It
    # lifts reading only: what SQLite writes while recovering is still written as that uid, in that uid's folder.
    done = subprocess.run(["setpriv", f"--reuid={st.st_uid}", f"--regid={st.st_gid}", "--clear-groups",
                           "--inh-caps=+dac_read_search", "--ambient-caps=+dac_read_search",
                           sys.executable, "-I", "-c", RECOVER, path], capture_output=True, text=True, timeout=900, cwd="/")
    if done.returncode == 0 and done.stdout.strip() == "ok":
        return True
    print(f"{os.path.basename(path)}: exit {done.returncode}: {done.stderr[-300:]}", file=sys.stderr)
    return False


def main():
    root = sys.argv[1]
    good, bad = 0, 0
    for path, st in databases(root):
        if recovered(path, st):
            good += 1
        else:
            bad += 1
    print(f"restore: databases ok={good} failed={bad}")
    if not os.path.isfile(os.path.join(root, LEDGER)):
        print("restore: refused: this snapshot has no ledger.db; nothing is in place")
        return 1
    if bad:
        print("restore: refused: a database failed its check; try an older snapshot (make snapshots); nothing is in place")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
