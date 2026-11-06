#!/usr/bin/env python3
"""What scripts/restore.sh says about the copy in private/ and the snapshots in R2: times and counts, nothing else.
Usage: restore-facts.py copy MIRROR.json
       restore-facts.py snapshots MIRROR.json < output of restic snapshots --json"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7))


def when(text):
    """restic writes nanoseconds, and only newer Pythons read them."""
    return datetime.fromisoformat(re.sub(r"\.\d+", "", text).replace("Z", "+00:00")).astimezone(WIB)


def show(moment):
    return moment.strftime("%Y-%m-%d %H:%M WIB")


def age(moment):
    hours = int((datetime.now(WIB) - moment).total_seconds() // 3600)
    return f"{hours} hours ago" if hours < 48 else f"{hours // 24} days ago"


def main():
    what, path = sys.argv[1:3]
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    pulled = when(doc["pulled_at"])
    if what == "copy":
        print(f"restore: the copy was pulled {show(pulled)} ({age(pulled)}) from a {'frozen' if doc['frozen'] else 'live'} "
              f"host, raw databases: {doc['counts']['db_raw']}")
        return
    rows = sorted(json.load(sys.stdin), key=lambda r: when(r["time"]))
    for row in rows:
        print(f"  {row.get('short_id') or row['id'][:8]}  {show(when(row['time']))}")
    print(f"restore: {len(rows)} snapshots; the copy in private/ was pulled {show(pulled)} ({age(pulled)})")
    if rows:
        print("restore: the newest snapshot is " + ("NEWER than the copy (make restore-restic)" if when(rows[-1]["time"]) > pulled
                                                    else "older than the copy (make restore)"))


if __name__ == "__main__":
    main()
