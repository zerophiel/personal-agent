#!/usr/bin/env bash
# restic -> Cloudflare R2. Needs /opt/personal-agent-secrets/restic.env with literal KEY=VALUE lines
# (no quotes, no shell evaluation, any characters allowed in values):
#   RESTIC_REPOSITORY=s3:https://<account>.r2.cloudflarestorage.com/<bucket>
#   RESTIC_PASSWORD=...  AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...
# Usage: backup.sh [init|backup|forget|check|snapshots [--json]|restore <snapshot> <dir>]
set -euo pipefail
ENV_FILE="${ENV_FILE:-/opt/personal-agent-secrets/restic.env}"
LEDGER="${PA_LEDGER:-/opt/personal-agent-data/vault-tools/ledger.db}"
while IFS='=' read -r key value; do
  [[ "$key" =~ ^(RESTIC_REPOSITORY|RESTIC_PASSWORD|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY)$ ]] || continue
  export "$key=$value"
done < "$ENV_FILE"
export AWS_DEFAULT_REGION=auto   # R2 uses region "auto"
# Under systemd there is no HOME, so restic ran without a cache and read the repository's index over the network each time.
export RESTIC_CACHE_DIR="${RESTIC_CACHE_DIR:-/var/cache/personal-agent-restic}"
# A run that meets another's lock waits for it: on 1 Nov pa-check and pa-forget, both at 04:00, failed on each other's.
r() { restic --retry-lock 30m "$@"; }
# A host with no ledger must not add snapshots that push the good ones out of retention. Reading the repository stays allowed:
# an empty host needs that to restore.
has_ledger() { [[ -s "$LEDGER" ]] || { echo "refused: this host has no ledger.db, so no $1"; exit 1; }; }
case "${1:-backup}" in
  init)      restic init ;;
  # A fixed --host and grouping by paths: a new VPS has another hostname, and its snapshots must find their parent and share
  # one retention with the old host's, whose snapshots would otherwise be kept forever as a group of their own.
  backup)    has_ledger backup; r backup --host personal-agent --exclude-caches /opt/personal-agent-data /opt/personal-agent-secrets ;;
  forget)    has_ledger forget; r forget --group-by paths --prune --keep-daily 7 --keep-weekly 4 --keep-monthly 6 ;;
  check)     r check ;;
  snapshots) r snapshots "${@:2}" ;;
  restore)   snapshot="${2:?snapshot id required}"; target="${3:?target dir required}"   # scratch dir only; refuses a non-empty one
             [[ -z "$(ls -A "$target" 2>/dev/null)" ]] || { echo "target not empty"; exit 1; }
             r restore "$snapshot" --target "$target" ;;
  *) echo "usage: $0 [init|backup|forget|check|snapshots|restore <snapshot> <dir>]"; exit 2 ;;
esac
