#!/usr/bin/env bash
# Weekly Docker cleanup. NEVER touches volumes. Keeps the images of every compose service in every profile (a stopped
# front zone or a timer job keeps its image), of running containers and of the release manifests, compared by full image
# ID: `docker images` lists the digest-pinned Hermes image as <none>, so names alone never matched it. If compose cannot
# list its images, the script stops before removing anything. DRY_RUN=1 only prints.
set -euo pipefail
ROOT="${ROOT:-/opt/personal-agent}"
MANIFEST_DIR="${ROOT}/releases"          # current.txt, previous.txt: one image ref/ID per line
run() { if [[ "${DRY_RUN:-0}" == 1 ]]; then echo "[dry-run] $*"; else "$@"; fi; }
compose=(docker compose -f "$ROOT/compose/docker-compose.yml" --env-file "$ROOT/config/stack.env")

refs=$(mktemp); keep=$(mktemp); trap 'rm -f "$refs" "$keep"' EXIT
plist=$("${compose[@]}" config --profiles)        # front, jobs
profiles=()
for p in $plist; do profiles+=(--profile "$p"); done
"${compose[@]}" "${profiles[@]}" config --images >>"$refs"
cat "$MANIFEST_DIR"/current.txt "$MANIFEST_DIR"/previous.txt 2>/dev/null >>"$refs" || true
# running containers' images are also protected
docker ps -q | xargs -r docker inspect --format '{{.Image}}' >>"$refs"
while read -r ref; do
  [[ -z "$ref" ]] || docker image inspect --format '{{.Id}}' "$ref" 2>/dev/null || true
done <"$refs" | sort -u >"$keep"

before=$(df --output=used -B1M / | tail -1)
run docker container prune -f
run docker image prune -f                          # dangling only
docker images --no-trunc --format '{{.ID}} {{.Repository}}:{{.Tag}}' | while read -r id ref; do
  if ! grep -qxF "$id" "$keep"; then
    echo "unused image: $ref"
    run docker image rm "$id" || true
  fi
done
run docker builder prune -f --filter until=168h
after=$(df --output=used -B1M / | tail -1)
echo "prune: freed ~$((before - after)) MB; $(df -h / | awk 'NR==2{print $5" used"}')"
