#!/usr/bin/env bash
# make venv: the Python of make test and make mirror, with the exact packages of the vault-tools image, which hold what the other
# server tests import, plus what only tests need: PyYAML, and reportlab to draw the statement PDFs. It lives outside the repo, as
# ~/.venv-gmail does, so it never reaches the VPS and never stops a worktree from being removed. uv can fetch Python 3.12, the
# containers' version; without uv, the system's Python has to do.
# Usage: make-venv.sh folder
set -euo pipefail
venv=${1:?usage: make-venv.sh folder}
here=$(cd "$(dirname "$0")/.." && pwd)
case "$venv/" in
  "$here"/*) echo "refused: the venv must be outside the repo" >&2; exit 1 ;;
esac
lock=$here/services/vault-tools/requirements.lock
if command -v uv >/dev/null 2>&1; then
  uv venv -q --allow-existing --python 3.12 "$venv"
  uv pip install -q --python "$venv/bin/python" -r "$lock" PyYAML reportlab
else
  python3 -m venv "$venv"
  "$venv/bin/python" -m pip install -q -r "$lock" PyYAML reportlab
fi
"$venv/bin/python" -I -c 'import sys, cryptography, mcp, reportlab, yaml; print("venv ok: Python", sys.version.split()[0])'
