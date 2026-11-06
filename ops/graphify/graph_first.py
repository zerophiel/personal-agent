#!/usr/bin/env python3
"""UserPromptSubmit hook (.claude/settings.json): every request starts from the project map, the owner's standing rule.
When graphify-out/graph.json exists it adds a short note to the model's context: query the graph before any grep or
file read, where the live-bot snapshot and the Hermes engine graph are, and which indexed files changed since the
build. It reads graphify-out/manifest.json, file mtimes and the docs/runtime/README.md header only, never the prompt,
prints nothing without a graph and always exits 0, so a broken map can never block a message. Pipe test:
  echo '{}' | CLAUDE_PROJECT_DIR=$PWD python3 -I ops/graphify/graph_first.py"""
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

ENGINE_GRAPH = "~/.graphify/repos/NousResearch/hermes-agent-v0.22.5/graphify-out/graph.json"
DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt", ".pdf"}
# private/: make mirror's plaintext copy; its file names never reach the context
SKIP_DIRS = {".git", ".claude", "graphify-out", "__pycache__", "node_modules", ".venv", "venv", "private"}
SENSITIVE = re.compile(r"(?i)token|secret|passw|credential|\.env\b")   # names graphify skips; never reported as new
SHOW = 6
WIB = 7 * 3600


def wib(ts):
    return time.strftime("%Y-%m-%d %H:%M WIB", time.gmtime(ts + WIB))


def ignore_patterns(root):
    pats = []
    for name in (".gitignore", ".graphifyignore"):
        try:
            with open(os.path.join(root, name), encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError:
            continue
        pats += [ln.strip() for ln in lines if ln.strip() and not ln.lstrip().startswith(("#", "!"))]
    return pats


def ignored(rel, pats):
    base = rel.rsplit("/", 1)[-1]
    for p in pats:
        if p.endswith("/"):
            if rel.startswith(p) or f"/{p}" in f"/{rel}":
                return True
        elif fnmatch.fnmatch(rel, p.lstrip("/")) or ("/" not in p and fnmatch.fnmatch(base, p)):
            return True
    return False


def md5(path):
    h = hashlib.md5(usedforsecurity=False)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def behind(root):
    """Indexed files changed, deleted or added since the build, and docs still waiting for semantic re-extraction,
    judged the way graphify's detect_incremental does: a moved mtime counts only when the MD5 differs from the stored
    hash (semantic_hash for docs, ast_hash for code), so a fresh checkout with new mtimes is not reported."""
    try:
        with open(os.path.join(root, "graphify-out", "manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, ValueError):
        return []
    rows = {str(k).replace("\\", "/"): v for k, v in manifest.items() if isinstance(v, dict)}
    out = []
    for rel, row in sorted(rows.items()):
        path = os.path.join(root, rel)
        try:
            mtime = os.stat(path).st_mtime
        except OSError:
            out.append(f"{rel} (deleted)")
            continue
        doc = os.path.splitext(rel)[1].lower() in DOC_SUFFIXES
        stored = row.get("semantic_hash" if doc else "ast_hash") or ""
        if doc and not stored:
            out.append(f"{rel} (not re-extracted)")
        elif mtime != row.get("mtime") and (not stored or md5(path) != stored):
            out.append(rel)
    suffixes = {os.path.splitext(k)[1].lower() for k in rows} - {""}
    pats = ignore_patterns(root)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
        for f in sorted(filenames):
            rel = os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, "/")
            if (os.path.splitext(f)[1].lower() in suffixes and rel not in rows and not SENSITIVE.search(f)
                    and not ignored(rel, pats)):
                out.append(f"{rel} (new)")
    return out


def snapshot(root):
    """When docs/runtime/ was collected from the VPS, from its README header."""
    try:
        with open(os.path.join(root, "docs", "runtime", "README.md"), encoding="utf-8") as f:
            head = f.read(2000)
    except OSError:
        return " (missing: make runtime-map)"
    m = re.search(r"\bon (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d)", head)
    if not m:
        return ""
    at = datetime.fromisoformat(m.group(1))
    days = (datetime.now(timezone.utc) - at).days
    age = "today" if days < 1 else f"{days} day{'s' * (days > 1)} ago"
    return f", collected {at.strftime('%Y-%m-%d %H:%M')} WIB ({age}; refresh with make runtime-map)"


def mirror_age(root):
    """One line on how old make mirror's copy is, or None outside git. private/ sits beside the shared .git, also seen from a
    linked worktree, and only the time of its MIRROR.json is looked at: nothing there is opened or listed."""
    try:
        done = subprocess.run(["git", "-C", root, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                              capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0 or not done.stdout.strip():
        return None
    try:
        at = os.stat(os.path.join(os.path.dirname(done.stdout.strip()), "private", "vps", "MIRROR.json")).st_mtime
    except OSError:
        return "No local copy of the VPS data and secrets yet (make mirror); never read or list private/."
    days = int((time.time() - at) // 86400)
    age = "today" if days < 1 else f"{days} day{'s' * (days > 1)} ago"
    return f"Local copy of the VPS data and secrets in private/: pulled {wib(at)} ({age}; make mirror refreshes it); never read or list private/."


def main():
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    graph = os.path.join(root, "graphify-out", "graph.json")
    if not os.path.isfile(graph):
        return
    lines = [f"Project map first (owner's rule): before any grep, search or file read, run graphify query \"<question>\""
             f" (or graphify explain / graphify path) on graphify-out/graph.json, built {wib(os.stat(graph).st_mtime)};"
             f" overview in graphify-out/GRAPH_REPORT.md. Live bot side: docs/runtime/README.md{snapshot(root)}."
             f" Hermes engine: graphify query \"<question>\" --graph {ENGINE_GRAPH}."]
    stale = behind(root)
    if stale:
        more = f" and {len(stale) - SHOW} more" if len(stale) > SHOW else ""
        lines.append(f"Graph is behind the working tree ({len(stale)}): {', '.join(stale[:SHOW])}{more}."
                     " Code: graphify update . (free); docs: /graphify . --update.")
    copy = mirror_age(root)
    if copy:
        lines.append(copy)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "\n".join(lines)}}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:   # the map is a hint; a message must never fail because of it
        print(f"graph_first: {type(e).__name__}", file=sys.stderr)
    sys.exit(0)
