#!/usr/bin/env python3
"""The scan before a commit: reads a diff on stdin and reports the added lines that look like a secret or personal data, masked, with
their file and line. The token and name patterns are those of ops/runtime-map/collect.py, so there is no second copy of the owner's name.

Usage: git add <files> && git diff --cached -U0 | python3 -I ops/privacy/diff_scan.py
Exit 1 when something is reported: read it before committing. docs/LAPTOP.md lists the hits known to be harmless."""
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import mask  # noqa: E402

collect = mask.load_collect()
CHECKS = {
    "digits>=9": re.compile(r"\d{9,}"),
    "grouped number": re.compile(r"\b\d{3,4}(?:[ -]\d{3,4}){2,}\b"),
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"),
    "token": collect.TOKEN,
    "github or slack token": re.compile(r"ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|xox[abposr]-[A-Za-z0-9-]{10,}"),
    "owner name": collect.OWNER,
}


def shown(text):
    return re.sub(r"\d{5,}", "[n]", collect.scrub(text.strip()))[:140]


def main():
    sys.stdin.reconfigure(errors="replace")
    path, line_no, hits = None, 0, {}
    for raw in sys.stdin.read().splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else raw[4:]
            continue
        hunk = re.match(r"@@ -\d+(?:,\d+)? \+(\d+)", raw)
        if hunk:
            line_no = int(hunk.group(1))
        elif raw.startswith("+"):
            for name, pattern in CHECKS.items():
                if pattern.search(raw[1:]):
                    hits.setdefault((path, name), []).append(f"{line_no}: {shown(raw[1:])}")
            line_no += 1
    if not hits:
        print("scan: no hits in added lines")
        return 0
    for (where, name), rows in sorted(hits.items()):
        print(f"{where} [{name}] x{len(rows)}")
        for row in rows[:4]:
            print(f"    {row}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
