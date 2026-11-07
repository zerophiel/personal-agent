#!/usr/bin/env bash
# make deploy runs this around its rsync. The applier (services/applier) changes front files on the VPS when the owner
# taps Setujui, and an rsync --delete from a checkout without those changes would quietly undo them.
#   start  holds the applier (it stops at a deploy-hold younger than 30 minutes), waits for a change in progress to
#          finish, and refuses while the VPS has an applied change this checkout lacks: make applied-pull brings it in
#   end    lets the applier run again and starts it once, if it is installed
# Fails closed: no answer from the VPS is a refusal. Usage: bash scripts/deploy-guard.sh start|end user@host
set -euo pipefail
cd "$(dirname "$0")/.."
step=${1:-} host=${2:-}
[ -n "$host" ] || { echo "usage: $0 start|end user@host" >&2; exit 2; }
as_root() { ssh -o BatchMode=yes -o ConnectTimeout=15 "$host" sudo bash -s; }

case $step in
start)
  ids=$(as_root <<'EOF'
set -euo pipefail
A=/opt/personal-agent-data/applier
if [ -d "$A" ]; then
  date +%s > "$A/deploy-hold"
  flock -w 1200 "$A/lock" true      # the applier takes this lock per change, then sees the hold and stops
  for f in "$A"/applied/*.json; do
    if [ -f "$f" ]; then basename "$f" .json; fi
  done
fi
EOF
  ) || { echo "deploy refused: the applier on $host could not be held (ssh or flock failed)" >&2; exit 1; }
  missing=""
  for id in $ids; do
    if ! [[ $id =~ ^[0-9]{1,9}$ ]] || [ ! -f "ops/applied/$id.json" ]; then missing="$missing #$id"; fi
  done
  if [ -n "$missing" ]; then
    echo "deploy refused: applied on the VPS but not in this checkout:$missing. Run make applied-pull first." >&2
    bash scripts/deploy-guard.sh end "$host"
    exit 1
  fi
  ;;
end)
  as_root <<'EOF'
set -euo pipefail
rm -f /opt/personal-agent-data/applier/deploy-hold
if systemctl cat pa-applier.service >/dev/null 2>&1; then systemctl start --no-block pa-applier.service; fi
EOF
  ;;
*)
  echo "usage: $0 start|end user@host" >&2
  exit 2
  ;;
esac
