#!/usr/bin/env bash
# Run with sudo on the VPS before the services that write them first start (make deploy and make up run it): the folders of
# config/data.manifest, each owned by the uid its writer runs as. Safe to run again; never deletes or empties anything.
set -euo pipefail
D=${PA_DATA_DIR:-/opt/personal-agent-data}
here=$(cd "$(dirname "$0")/.." && pwd)
if [ ! -d "$D" ]; then install -d -o 0 -g 0 -m 0700 "$D"; fi   # as the live host: root's alone, each service mounts its own folder
while read -r path uid gid mode; do
  case "$path" in ''|'#'*) continue ;; esac
  install -d -o "$uid" -g "$gid" -m "$mode" "$D/$path"
  stat -c '%n %u:%g %a' "$D/$path"
done < "$here/config/data.manifest"
