#!/usr/bin/env python3
"""Run ON the VPS (via `make pdf-passwords`). Prompts for statement PDF passwords per bank with
hidden input, builds the JSON correctly, and writes /opt/personal-agent-secrets/pdf_passwords.

- Nothing is echoed or printed back except the bank names and how many passwords were saved.
- Existing entries are kept unless you re-enter that bank (blank at the first prompt = keep).
- The file is rewritten IN PLACE (same inode): the vault-tools container bind-mounts this single
  file, and replacing it with a new file would leave the container reading the old one.
"""
import getpass
import json
import os
import sys

PATH = os.environ.get("PDF_PASSWORDS_FILE", "/opt/personal-agent-secrets/pdf_passwords")
BANKS = ["dbs", "cimb", "hsbc", "mandiri", "mega", "jenius", "bca"]


def collect(prompt=getpass.getpass, say=print) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for bank in BANKS:
        pws: list[str] = []
        while True:
            label = "(kosong = lewati/biarkan)" if not pws else "(kosong = selesai untuk bank ini)"
            pw = prompt(f"Password PDF {bank} #{len(pws) + 1} {label}: ")
            if not pw:
                break
            pws.append(pw)
        if pws:
            out[bank] = pws
            say(f"  {bank}: {len(pws)} password")
    return out


def merge(existing: dict, new: dict) -> dict:
    return {**{k.lower(): v for k, v in existing.items()}, **new}


def main() -> int:
    if not sys.stdin.isatty():
        print("Perlu terminal interaktif (jalankan lewat make pdf-passwords).", file=sys.stderr)
        return 2
    try:
        with open(PATH) as f:
            existing = json.load(f)
    except (FileNotFoundError, ValueError):
        existing = {}
    print("Masukkan password PDF per bank. Satu bank bisa punya beberapa password (mis. berganti-ganti).")
    new = collect()
    merged = merge(existing, new)
    with open(PATH, "r+" if os.path.exists(PATH) else "w") as f:   # in place, keep inode
        f.seek(0)
        f.truncate()
        json.dump(merged, f)
    os.chmod(PATH, 0o444)
    print(f"Tersimpan. Bank terisi: {', '.join(sorted(merged)) or '(kosong)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
