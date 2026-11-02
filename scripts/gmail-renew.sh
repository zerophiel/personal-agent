#!/usr/bin/env bash
# LAPTOP ONLY. Renew a Google token on the VPS: by default the gmail.readonly token of ingest-gmail, or one of the two
# comms tokens (M4). In Testing mode a token lasts 7 days, and pa-gmail-token warns through the control bot from 2 days
# before the ingest token runs out. scripts/gmail-auth.py mints the new token and writes it to stdout. This script pipes
# it to the VPS, where it goes into a temporary file next to the old token. The old token is replaced only once the new
# one is complete, so a login that fails, times out or is cancelled leaves the old token in use. Nothing secret is
# printed or kept on the laptop.
#
# Usage: bash scripts/gmail-renew.sh [client_secret.json] [token name]
#          (default: ~/client_secret_ingest.json gmail_ingest_token)
#        bash scripts/gmail-renew.sh ~/client_secret_comms.json gmail_comms_token      (comms: Gmail)
#        bash scripts/gmail-renew.sh ~/client_secret_comms.json calendar_comms_token   (comms: Calendar)
set -euo pipefail

VPS=${GMAIL_RENEW_VPS:-ubuntu@43.157.242.194}
CLIENT=${1:-$HOME/client_secret_ingest.json}
NAME=${2:-gmail_ingest_token}
case "$NAME" in   # the token secrets gmail-auth.py has a scope for; never any other secret
  gmail_ingest_token)   LABEL="Token Gmail" ;;
  gmail_comms_token)    LABEL="Token Gmail comms" ;;
  calendar_comms_token) LABEL="Token Kalender comms" ;;
  *) echo "Nama token tidak dikenal: $NAME (gmail_ingest_token, gmail_comms_token, calendar_comms_token)." >&2; exit 2 ;;
esac
TOKEN=${GMAIL_RENEW_DIR:-/opt/personal-agent-secrets}/$NAME
PY=${GMAIL_PY:-$HOME/.venv-gmail/bin/python}
HERE=$(cd "$(dirname "$0")" && pwd)

[ -s "$CLIENT" ] || { echo "File client OAuth tidak ada: $CLIENT (docs/GMAIL_OAUTH.md langkah 3)." >&2; exit 2; }
"$PY" -c "import google_auth_oauthlib" 2>/dev/null || {
  echo "Butuh venv: python3 -m venv ~/.venv-gmail && ~/.venv-gmail/bin/pip install google-auth-oauthlib" >&2; exit 2; }

# Runs as root on the VPS with the new token on stdin. The new token is read in full and checked (JSON with a
# refresh token and its issue date) before the old file is touched. The old file is then rewritten in place: compose
# mounts it into ingest-gmail as a file secret, so its inode stays, as with pdf-passwords-set.py.
read -r -d '' REMOTE <<'EOF' || true
set -eu
umask 077
new="$TOKEN.new"
trap 'rm -f "$new"' EXIT
cat > "$new"
python3 -c '
import json, os, sys
new, tok = sys.argv[1], sys.argv[2]
data = open(new, "rb").read()
try:
    d = json.loads(data)
    ok = bool(d.get("refresh_token")) and bool(d.get("issued_at"))
except (ValueError, AttributeError):
    ok = False
if not ok:
    sys.exit("Token baru tidak lengkap. Token lama tetap dipakai.")
if os.path.exists(tok):
    with open(tok, "r+b") as f:
        f.seek(0)
        f.write(data)
        f.truncate()
else:
    fd = os.open(tok, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    os.fchmod(fd, 0o444)
    with os.fdopen(fd, "wb") as f:
        f.write(data)
' "$new" "$TOKEN"
echo "$LABEL di VPS diperbarui $(date '+%d %b %H:%M %Z'); berlaku 7 hari." >&2
EOF

"$PY" "$HERE/gmail-auth.py" "$CLIENT" "$NAME" |
  ssh "$VPS" "sudo -n env TOKEN=$(printf %q "$TOKEN") LABEL=$(printf %q "$LABEL") bash -c $(printf %q "$REMOTE")"
