#!/usr/bin/env bash
# Run with sudo on the VPS before the services that write them first start (make deploy runs it): each folder owned by
# the uid its writer runs as. Safe to run again; never deletes or empties anything.
#   control-state    control (uid 10001) only: control.db, decided/, approved/
#   proposals-inbox  change-proposals writes, control reads and empties (both uid 10001)
#   hermes-front     the front Hermes data dir (the image's uid 10000, as hermes-vault)
set -euo pipefail
D=/opt/personal-agent-data
install -d -o 10001 -g 10001 -m 0700 "$D/control-state" "$D/proposals-inbox"
install -d -o 10000 -g 10000 -m 0700 "$D/hermes-front"
stat -c '%n %u:%g %a' "$D/control-state" "$D/proposals-inbox" "$D/hermes-front"
