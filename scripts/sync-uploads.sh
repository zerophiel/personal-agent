#!/usr/bin/env bash
# Host job (root). Relay files the owner uploaded in Telegram from the PRIVATE Hermes cache
# (700, uid 10000) to the ingest drop folder that vault-tools can read, and enforce retention.
#   - copies regular files only (no symlinks), <= 20 MB, never overwrites different content
#   - deletes copies AND Hermes originals older than 90 days (statements keep 3 months)
set -euo pipefail
SRC="${SRC:-/opt/personal-agent-data/hermes-vault/cache/documents}"
DST="${DST:-/opt/personal-agent-data/ingest/telegram}"
RETENTION_DAYS="${RETENTION_DAYS:-90}"
OWNER="${OWNER-10002:10002}"          # empty (OWNER=) skips chown, for unprivileged tests
MAX_BYTES="${MAX_BYTES:-$((20 * 1024 * 1024))}"

[[ -d "$SRC" ]] || exit 0
install -d -m 0755 "$DST"
[[ -z "$OWNER" ]] || chown "$OWNER" "$DST"
copied=0
while IFS= read -r -d '' f; do
  name="$(basename "$f")"
  size=$(stat -c %s "$f")
  (( size <= MAX_BYTES )) || continue
  if [[ -e "$DST/$name" ]]; then
    cmp -s "$f" "$DST/$name" && continue                       # already relayed
    name="$(sha256sum "$f" | cut -c1-12)-$name"                # same name, other content
    [[ -e "$DST/$name" ]] && continue
  fi
  tmp="$(mktemp "$DST/.tmp.XXXXXX")"
  cp --no-preserve=mode,ownership --preserve=timestamps -- "$f" "$tmp"   # keep mtime so retention stays accurate
  chmod 0644 "$tmp"
  [[ -z "$OWNER" ]] || chown "$OWNER" "$tmp"
  mv -- "$tmp" "$DST/$name"                                    # atomic: readers never see a partial file
  copied=$((copied + 1))
done < <(find "$SRC" -maxdepth 1 -type f -mtime -"$RETENTION_DAYS" -print0)   # already-expired files are not relayed

purged=$(find "$SRC" "$DST" -maxdepth 1 -type f -mtime +"$RETENTION_DAYS" -print -delete | wc -l)
echo "sync-uploads: copied=$copied purged=$purged"
