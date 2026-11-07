#!/usr/bin/env python3
"""make applied-pull: the front changes the applier made on the VPS (services/applier) into this checkout, one commit
each and oldest first, so the next make deploy carries them: its rsync would undo them otherwise, and
scripts/deploy-guard.sh refuses until each has its ops/applied/<id>.json. Every record is checked again against this
checkout's own control.py and files; the first one that does not fit stops the pull with the reason. File contents are
never printed."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# runs as root on the VPS: the applier's own records (root only), each holding the proposal it applied
REMOTE = r"""
import json, os, re
A = "/opt/personal-agent-data/applier/applied"
out = []
for name in sorted(os.listdir(A)) if os.path.isdir(A) else []:
    if re.fullmatch(r"\d{1,9}\.json", name):
        with os.fdopen(os.open(os.path.join(A, name), os.O_RDONLY | os.O_NOFOLLOW), "rb") as f:
            out.append(json.loads(f.read()))
print(json.dumps(out))
"""
KEEP = ("id", "status", "files", "services", "decided_at", "applied_at")   # what ops/applied/<id>.json keeps: no content


def fetch(host: str) -> list:
    r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", host, "sudo", "/usr/bin/python3", "-I",
                        "-"], input=REMOTE, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        sys.exit(f"applied-pull: reading the applier's records on {host} failed (exit {r.returncode})")
    return json.loads(r.stdout)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True).stdout


def load_control(root: Path):
    spec = importlib.util.spec_from_file_location("control", root / "services/control/control.py")
    control = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(control)
    return control


def problem(rec: dict, control, root: Path) -> str | None:
    """Why this record cannot become a commit here, else None."""
    try:
        p = control.validate(rec.get("proposal"))
    except ValueError as e:
        return f"its proposal fails this checkout's control.py ({e})"
    if rec.get("status") != "applied" or p != rec["proposal"]:
        return "it is not an applied record as the applier writes one"
    paths = [f["path"] for f in p["files"]]
    if p["zone"] != "front" or not paths or any(x not in control.AUTO_APPLY for x in paths):
        return "it changes files the applier never writes"
    hashes = rec.get("files")
    if not isinstance(hashes, list) or [h.get("path") if isinstance(h, dict) else None for h in hashes] != paths:
        return "its file list differs from its proposal's"
    for f, h in zip(p["files"], hashes):
        path = root / f["path"]
        if control.hidden_chars(f["path"], f["content"]):
            return f"{f['path']} holds characters a diff does not show"
        if sha(f["content"].encode()) != h.get("sha256_after"):
            return f"{f['path']}: the content does not match the hash the applier recorded"
        if path.is_symlink() or not path.is_file():
            return f"{f['path']} is not a plain file in this checkout"
        if sha(path.read_bytes()) != h.get("sha256_before"):
            return f"{f['path']} in this checkout is not what the VPS had before the change (merge it by hand)"
        if git(root, "status", "--porcelain", "--", f["path"]):
            return f"{f['path']} has uncommitted changes in this checkout"
    return None


def pull(records: list, root: Path = ROOT) -> list[int]:
    control = load_control(root)
    if not all(isinstance(r, dict) and type(r.get("id")) is int for r in records):
        sys.exit("applied-pull: a record without an id; nothing pulled")
    done = []
    for rec in sorted(records, key=lambda r: r["id"]):
        pid, record = rec["id"], root / "ops" / "applied" / f"{rec['id']}.json"
        if record.exists():
            continue
        why = problem(rec, control, root)
        if why:
            sys.exit(f"applied-pull: #{pid} not pulled: {why}. The ones after it wait too.")
        if subprocess.run(["git", "-C", str(root), "var", "GIT_COMMITTER_IDENT"], capture_output=True).returncode != 0:
            # Checked before anything is written: a record written without its commit reads as pulled on the next run.
            sys.exit(f"applied-pull: #{pid} not pulled: git has no identity to commit with (docs/LAPTOP.md).")
        paths = [f["path"] for f in rec["proposal"]["files"]]
        for f in rec["proposal"]["files"]:
            (root / f["path"]).write_bytes(f["content"].encode())
        record.parent.mkdir(parents=True, exist_ok=True)
        keep = {k: rec[k] for k in KEEP if k in rec}
        keep.update(zone=rec["proposal"]["zone"], change_type=rec["proposal"]["change_type"])
        record.write_text(json.dumps(keep, indent=2) + "\n", encoding="utf-8")
        name = str(record.relative_to(root))
        git(root, "add", "--", name)
        git(root, "commit", "-q", "-m", f"apply proposal #{pid} ({', '.join(paths)})\n\nApproved by the owner in control "
            f"and applied on the VPS by services/applier at {rec.get('applied_at')}; pulled by make applied-pull.",
            "--", *paths, name)
        done.append(pid)
        print(f"applied-pull: #{pid} committed ({', '.join(paths)})")
    return done


def main(argv: list[str] | None = None, root: Path = ROOT) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        sys.exit("usage: applied-pull.py user@host")
    done = pull(fetch(argv[0]), root)
    print(f"applied-pull: {len(done)} new commit(s); make deploy carries them" if done else "applied-pull: nothing new")


if __name__ == "__main__":
    main()
