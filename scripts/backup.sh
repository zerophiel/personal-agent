#!/usr/bin/env bash
# restic -> Cloudflare R2. Needs /opt/personal-agent-secrets/restic.env with literal KEY=VALUE lines
# (no quotes, no shell evaluation, any characters allowed in values):
#   RESTIC_REPOSITORY=s3:https://<account>.r2.cloudflarestorage.com/<bucket>
#   RESTIC_PASSWORD=...  AWS_ACCESS_KEY_ID=...  AWS_SECRET_ACCESS_KEY=...
# Usage: backup.sh [init|backup|forget|check|snapshots [--json]|restore <snapshot> <dir>]
set -euo pipefail
ENV_FILE="${ENV_FILE:-/opt/personal-agent-secrets/restic.env}"
while IFS='=' read -r key value; do
  [[ "$key" =~ ^(RESTIC_REPOSITORY|RESTIC_PASSWORD|AWS_ACCESS_KEY_ID|AWS_SECRET_ACCESS_KEY)$ ]] || continue
  export "$key=$value"
done < "$ENV_FILE"
export AWS_DEFAULT_REGION=auto   # R2 uses region "auto"
case "${1:-backup}" in
  init)      restic init ;;
  backup)    restic backup --exclude-caches /opt/personal-agent-data /opt/personal-agent-secrets ;;
  forget)    restic forget --prune --keep-daily 7 --keep-weekly 4 --keep-monthly 6 ;;
  check)     restic check ;;
  snapshots) restic snapshots "${@:2}" ;;
  restore)   snapshot="${2:?snapshot id required}"; target="${3:?target dir required}"   # scratch dir only; refuses a non-empty one
             [[ -z "$(ls -A "$target" 2>/dev/null)" ]] || { echo "target not empty"; exit 1; }
             restic restore "$snapshot" --target "$target" ;;
  *) echo "usage: $0 [init|backup|forget|check|snapshots|restore <snapshot> <dir>]"; exit 2 ;;
esac
