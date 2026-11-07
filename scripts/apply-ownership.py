#!/usr/bin/env python3
"""make restore's ownership step, as root on the new VPS over the uploaded copy (scripts/restore.sh). The laptop's user cannot
store the bots' uids, so the list make mirror took on the old VPS is the source of owner and mode. Nothing outside the upload
folder is touched: it never follows a link, chown on a link changes the link itself, a link never gets a chmod, and a listed
path that passes through a link stops the run, so a link in a Hermes home cannot hand restic.env to another uid.

What is listed but not in the copy is skipped and counted (a file gone on a live host), except the side files of a database
make mirror cleaned, which are meant to be gone. What is in the copy but not listed takes the owner of its folder with no
access for group or other. Only a broken promise stops the run: a path leaving its folder, a link on the way, or a top folder
that both listings have and the copy lacks. Prints counts; names go to stderr, which scripts/restore.sh keeps in private/.
Usage: apply-ownership.py upload_folder   (holding data/, secrets/, and tools/ with the lists and db-report.json)"""
import json
import os
import stat
import sys

ROOTS = ("data", "secrets")
SIDE_FILES = ("-wal", "-shm", "-journal")


class Refused(Exception):
    pass


def read_rows(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def inside(rel):
    return not rel.startswith("/") and ".." not in rel.split("/")


def link_on_the_way(root, rel):
    path = root
    for part in rel.split("/")[:-1]:
        path = os.path.join(path, part)
        try:
            if stat.S_ISLNK(os.lstat(path).st_mode):
                return True
        except OSError:
            return False
    return False


def target(staging, row):
    root = os.path.join(staging, row["r"])
    return os.path.join(root, row["p"]) if row["p"] else root


def top_folders(rows):
    return {(r["r"], r["p"]) for r in rows if r["t"] == "d" and "/" not in r["p"]}


def check(staging, rows, before):
    """Before anything changes: a run that stops leaves only the upload folder, which the next run clears."""
    left, linked, lost = [], [], []
    for row in rows:
        if row["r"] not in ROOTS or (row["p"] and not inside(row["p"])):
            left.append(row["p"])
        elif row["p"] and link_on_the_way(os.path.join(staging, row["r"]), row["p"]):
            linked.append(row["p"])
    for root, rel in sorted(top_folders(rows) & top_folders(before)):
        path = target(staging, {"r": root, "p": rel})
        if not os.path.isdir(path) or os.path.islink(path):
            lost.append(rel or root)
    for rel in left + linked + lost:
        print(f"stopped on: {rel}", file=sys.stderr)
    if left or linked or lost:
        raise Refused(f"{len(left)} listed paths leave their folder, {len(linked)} pass through a link, "
                      f"{len(lost)} top folders are missing")


def apply(staging, rows, cleaned):
    counts = {"set": 0, "links": 0, "missing": 0, "unlisted": 0, "not_files": 0}
    meant_gone = {("data", rel + side) for rel in cleaned for side in SIDE_FILES}
    seen = set()
    for row in rows:
        key = (row["r"], row["p"])
        if row["t"] == "o":   # a socket or fifo: neither a file nor a folder, never copied, and its service makes it again
            counts["not_files"] += 1
            continue
        path = target(staging, row)
        try:
            st = os.lstat(path)
        except FileNotFoundError:
            if key not in meant_gone:
                counts["missing"] += 1
                print(f"listed, not in the copy: {row['p']}", file=sys.stderr)
            continue
        seen.add(key)
        os.lchown(path, row["u"], row["g"])
        if stat.S_ISLNK(st.st_mode):
            counts["links"] += 1
        else:
            os.chmod(path, row["m"])   # after the chown, which clears a setuid bit
            counts["set"] += 1
    for root in ROOTS:
        base = os.path.join(staging, root)
        for folder, dirs, files in os.walk(base):   # top down, so a folder's own owner is settled before its contents
            parent = os.lstat(folder)
            for name in dirs + files:
                path = os.path.join(folder, name)
                rel = os.path.relpath(path, base)
                if (root, rel) in seen:
                    continue
                st = os.lstat(path)
                os.lchown(path, parent.st_uid, parent.st_gid)
                if not stat.S_ISLNK(st.st_mode):
                    os.chmod(path, stat.S_IMODE(st.st_mode) & 0o700)
                counts["unlisted"] += 1
                print(f"not listed, took its folder's owner: {rel}", file=sys.stderr)
    return counts


def main():
    staging = sys.argv[1]
    tools = os.path.join(staging, "tools")
    rows = read_rows(os.path.join(tools, "ownership.jsonl"))
    before = read_rows(os.path.join(tools, "ownership.before.jsonl"))
    with open(os.path.join(tools, "db-report.json"), encoding="utf-8") as f:
        cleaned = json.load(f)["clean"]
    try:
        check(staging, rows, before)
    except Refused as refused:
        print(f"restore: refused: {refused} (names in private/restore.log); nothing is in place")
        return 1
    counts = apply(staging, rows, cleaned)
    print("restore: owners " + " ".join(f"{k}={v}" for k, v in counts.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
