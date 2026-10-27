#!/usr/bin/env bash
# restic -> Cloudflare R2. Needs /opt/personal-agent-secrets/restic.env with:
#   RESTIC_REPOSITORY=s3:https://<account>.r2.cloudflarestorage.com/<bucket>
#   RESTIC_PASSWORD=... AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=...
# Usage: backup.sh [backup|forget|check]
set -euo pipefail
set -a; . /opt/personal-agent-secrets/restic.env; set +a
case "${1:-backup}" in
  backup) restic backup --exclude-caches /opt/personal-agent-data /opt/personal-agent-secrets ;;
  forget) restic forget --prune --keep-daily 7 --keep-weekly 4 --keep-monthly 6 ;;
  check)  restic check ;;
  *) echo "usage: $0 [backup|forget|check]"; exit 2 ;;
esac
