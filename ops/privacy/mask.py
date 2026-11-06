#!/usr/bin/env python3
"""A filter on a command's output, so that what must never reach a session stays out of it. Tokens and keys, long token-like strings,
emails, public addresses, the owner's name, grouped numbers and digit runs of 9 or more are masked, and each line is cut.
It is the runtime map's own scrub (ops/runtime-map/collect.py), so there is no second copy of a pattern, the owner's name above all.

Usage: some command 2>&1 | python3 -I ops/privacy/mask.py [width]     width: where a line is cut, default 240"""
import importlib.util
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent.parent
BOT_URL = re.compile(r"bot\d+:[A-Za-z0-9_-]+")   # inside a URL: no word boundary before the digits, so the token pattern misses it


def load_collect():
    spec = importlib.util.spec_from_file_location("runtime_map_collect", ROOT / "ops" / "runtime-map" / "collect.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    width = int(sys.argv[1]) if len(sys.argv) > 1 else 240
    scrub = load_collect().scrub
    sys.stdin.reconfigure(errors="replace")
    for line in sys.stdin:
        print(scrub(BOT_URL.sub("bot[token]", line.rstrip("\n")))[:width], flush=True)


if __name__ == "__main__":
    main()
