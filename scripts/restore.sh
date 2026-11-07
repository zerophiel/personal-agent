#!/usr/bin/env bash
# The way back from this folder to a VPS (docs/REBUILD.md). Each way prepares the data and secrets in an upload folder,
# /opt/.pa-restore-XXXXXX on the same disk, and renames them into place only when whole: secrets first, data last, so the
# ledger that refuses a second restore appears after both are there. A run that stops leaves at most that folder, and the next
# run clears it. The host has no repo yet, so the tools travel in the same upload.
#   restore.sh mirror user@host CONFIRM            make restore: private/vps onto an empty host
#   restore.sh snapshots user@host                 make snapshots: what R2 holds, against the age of private/
#   restore.sh restic user@host CONFIRM SNAPSHOT   make restore-restic: a snapshot onto an empty host, when R2 is newer
# CONFIRM must repeat the host's address. Prints counts and statuses only; what rsync and the tools say goes to
# private/restore.log, since statement file names hold the owner's name and account fragments. restic.env reaches the VPS only
# inside the upload folder, and its messages (which can hold the repository URL) stay in that log.
set -euo pipefail
umask 077
mode=${1:-}
host=${2:-}
usage() {
  echo "usage: $0 mirror user@host CONFIRM | snapshots user@host | restic user@host CONFIRM SNAPSHOT" >&2
  exit 2
}
[ -n "$host" ] || usage
case "$mode" in
  mirror|snapshots|restic) ;;
  *) usage ;;
esac
here=$(cd "$(dirname "$0")/.." && pwd)
PY=${MIRROR_PY:-python3}
OPT=${RESTORE_REMOTE_OPT:-/opt}
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=4)

say() { echo "restore: $*"; }
refuse() { echo "restore: refused: $*; nothing is in place" >&2; exit 1; }
q() { printf %q "$1"; }
as_root() { ssh "${SSH_OPTS[@]}" "$host" "sudo -n bash -c $(q "$1")" </dev/null; }

common=$(git -C "$here" rev-parse --path-format=absolute --git-common-dir) || refuse "this is not a git checkout"
private=$(dirname "$common")/private
vps=$private/vps
log=$private/restore.log
[ -f "$vps/MIRROR.json" ] || refuse "there is no copy in private/ (make mirror on the old host)"
exec 9>"$private/.lock"
flock -n 9 || refuse "make mirror or another restore is running"
: > "$log"

if [ "$mode" != snapshots ]; then
  [ "${3:-}" = "${host#*@}" ] || refuse "CONFIRM must repeat the address of the VPS, the one this restores onto"
fi

staging=
cleanup() {
  if [ -n "$staging" ]; then as_root "rm -rf $(q "$staging")" 2>>"$log" || true; fi
}
trap cleanup EXIT

new_upload_folder() {
  staging=$(as_root 's=$(mktemp -d '"$(q "$OPT")"'/.pa-restore-XXXXXX) && install -d -m 0700 "$s/tools" && printf "%s\n" "$s"' 2>>"$log") \
    || refuse "the VPS does not answer (ssh or sudo failed)"
}
send_folder() {  # send_folder <local folder> <remote folder>
  rsync -rlptz -q --rsync-path='sudo -n rsync' -e "ssh ${SSH_OPTS[*]}" "$1/" "$host:$2/" 2>>"$log" \
    || refuse "the upload failed (rsync exit $?, details in private/restore.log)"
}
send_tools() {  # send_tools <file>...
  rsync -lptz -q --rsync-path='sudo -n rsync' -e "ssh ${SSH_OPTS[*]}" "$@" "$host:$staging/tools/" 2>>"$log" \
    || refuse "the upload failed (rsync exit $?, details in private/restore.log)"
}

# An empty host only: no containers of this project, no ledger, no data or secrets folder. An empty folder holds nothing and
# goes; secrets alone, with the marker the renames leave, are a run stopped between its two renames. Prints why not, or nothing.
guard() {
  ssh "${SSH_OPTS[@]}" "$host" "sudo -n /usr/bin/python3 -I - $(q "$OPT")" <<'EOF'
import glob, os, shutil, subprocess, sys
opt = sys.argv[1]
data, secrets = os.path.join(opt, "personal-agent-data"), os.path.join(opt, "personal-agent-secrets")
def stop(reason):
    print(reason)
    sys.exit()
try:
    containers = subprocess.run(["docker", "ps", "-q", "-a", "--filter", "label=com.docker.compose.project=personal-agent"],
                                capture_output=True, text=True, check=True).stdout
except (OSError, subprocess.CalledProcessError):
    stop("docker does not answer on the VPS (make bootstrap first)")
if containers.strip():
    stop("the VPS has this project's containers")
if os.path.lexists(os.path.join(data, "vault-tools", "ledger.db")):
    stop("the VPS already has a ledger")
for folder in (data, secrets):
    try:
        os.rmdir(folder)
    except OSError:
        pass
if os.path.lexists(data):
    stop("the VPS already has a data folder")
if os.path.lexists(secrets):
    if not os.path.exists(os.path.join(opt, ".pa-placing")):
        stop("the VPS already has a secrets folder")
    shutil.rmtree(secrets)
for left in glob.glob(os.path.join(opt, ".pa-restore-*")):
    shutil.rmtree(left)
EOF
}
check_host() {
  local why
  why=$(guard 2>>"$log") || refuse "the VPS does not answer (ssh or sudo failed)"
  [ -z "$why" ] || refuse "$why"
}

place() {  # place <secrets folder> <data folder>
  ssh "${SSH_OPTS[@]}" "$host" "sudo -n /usr/bin/python3 -I - $(q "$OPT") $(q "$1") $(q "$2")" 2>>"$log" <<'EOF' \
    || refuse "putting the folders in place failed (details in private/restore.log)"
import os, sys
opt, secrets, data = sys.argv[1:4]
marker = os.path.join(opt, ".pa-placing")
open(marker, "w").close()
os.rename(secrets, os.path.join(opt, "personal-agent-secrets"))
os.rename(data, os.path.join(opt, "personal-agent-data"))
os.unlink(marker)
EOF
  as_root "test -f $(q "$OPT/personal-agent-data/vault-tools/ledger.db")" 2>>"$log" || refuse "no ledger after the renames"
  say "in place"
}

need_restic() {
  [ -f "$vps/secrets/restic.env" ] || refuse "private/ has no restic.env"
  as_root "command -v restic >/dev/null" 2>>"$log" || refuse "restic is not on the VPS (make bootstrap first)"
}

case "$mode" in
  mirror)
    "$PY" -I "$here/scripts/restore-facts.py" copy "$vps/MIRROR.json"
    check_host
    new_upload_folder
    send_tools "$here/scripts/apply-ownership.py" "$vps/host/ownership.jsonl" "$vps/host/ownership.before.jsonl" "$vps/host/db-report.json"
    send_folder "$vps/secrets" "$staging/secrets"
    send_folder "$vps/data" "$staging/data"
    say "uploaded"
    as_root "/usr/bin/python3 -I $(q "$staging/tools/apply-ownership.py") $(q "$staging")" 2>>"$log" \
      || refuse "the ownership step stopped"
    place "$staging/secrets" "$staging/data"
    ;;
  snapshots)
    need_restic
    as_root "rm -rf $(q "$OPT")/.pa-restore-*" 2>>"$log" || refuse "the VPS does not answer (ssh or sudo failed)"
    new_upload_folder
    send_tools "$here/scripts/backup.sh" "$vps/secrets/restic.env"
    listing=$(as_root "ENV_FILE=$(q "$staging/tools/restic.env") RESTIC_CACHE_DIR=$(q "$staging/cache") bash $(q "$staging/tools/backup.sh") snapshots --json" 2>>"$log") \
      || refuse "restic could not list the snapshots; an R2 token with an IP limit needs this host's address (details in private/restore.log)"
    printf '%s' "$listing" | "$PY" -I "$here/scripts/restore-facts.py" snapshots "$vps/MIRROR.json"
    ;;
  restic)
    snapshot=${4:-}
    [[ "$snapshot" =~ ^([0-9a-f]{8,64}|latest)$ ]] || refuse "SNAPSHOT must be a snapshot id from make snapshots"
    "$PY" -I "$here/scripts/restore-facts.py" copy "$vps/MIRROR.json"
    need_restic
    check_host
    new_upload_folder
    send_tools "$here/scripts/backup.sh" "$here/scripts/recover-dbs.py" "$vps/secrets/restic.env"
    as_root "install -d -m 0700 $(q "$staging/tree") && ENV_FILE=$(q "$staging/tools/restic.env") RESTIC_CACHE_DIR=$(q "$staging/cache") bash $(q "$staging/tools/backup.sh") restore $(q "$snapshot") $(q "$staging/tree")" >>"$log" 2>&1 \
      || refuse "restic could not restore that snapshot (details in private/restore.log)"
    tree=$staging/tree/opt
    as_root "test -d $(q "$tree/personal-agent-data") && test -d $(q "$tree/personal-agent-secrets")" 2>>"$log" \
      || refuse "that snapshot lacks the data or secrets folder"
    as_root "/usr/bin/python3 -I $(q "$staging/tools/recover-dbs.py") $(q "$tree/personal-agent-data")" 2>>"$log" \
      || refuse "the database step stopped"
    # The restic.env that just opened the repository, in case the snapshot holds a key since rotated.
    as_root "install -m 0600 $(q "$staging/tools/restic.env") $(q "$tree/personal-agent-secrets/restic.env")" 2>>"$log" \
      || refuse "putting restic.env back failed"
    place "$tree/personal-agent-secrets" "$tree/personal-agent-data"
    ;;
esac
if [ "$mode" != snapshots ]; then say "done; next: make applied-pull (docs/REBUILD.md)"; fi
