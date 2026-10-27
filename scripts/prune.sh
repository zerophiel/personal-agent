#!/usr/bin/env bash
# Weekly Docker cleanup. NEVER touches volumes. Keeps images used by current compose files
# and those listed in the previous release manifest. DRY_RUN=1 only prints.
set -euo pipefail
ROOT="${ROOT:-/opt/personal-agent}"
MANIFEST_DIR="${ROOT}/releases"          # current.txt, previous.txt: one image ref/ID per line
run() { if [[ "${DRY_RUN:-0}" == 1 ]]; then echo "[dry-run] $*"; else "$@"; fi; }

keep=$(mktemp); trap 'rm -f "$keep"' EXIT
docker compose -f "$ROOT/compose/docker-compose.yml" --env-file "$ROOT/config/stack.env" config --images 2>/dev/null >>"$keep" || true
cat "$MANIFEST_DIR"/current.txt "$MANIFEST_DIR"/previous.txt 2>/dev/null >>"$keep" || true
# running containers' images are also protected
docker ps -q | xargs -r docker inspect --format '{{.Image}} {{.Config.Image}}' >>"$keep"

before=$(df --output=used -B1M / | tail -1)
run docker container prune -f
run docker image prune -f                          # dangling only
docker images --format '{{.Repository}}:{{.Tag}} {{.ID}}' | while read -r ref id; do
  if ! grep -qE "(^|[ ])(${ref}|${id}|sha256:${id}[0-9a-f]*)($|[ ])" "$keep"; then
    echo "unused image: $ref"
    run docker image rm "$id" || true
  fi
done
run docker builder prune -f --filter until=168h
after=$(df --output=used -B1M / | tail -1)
echo "prune: freed ~$((before - after)) MB; $(df -h / | awk 'NR==2{print $5" used"}')"
