#!/usr/bin/env bash
# Install the applier on the VPS, only after the owner's go-ahead and after a make deploy that carries this folder:
#   cd /opt/personal-agent && sudo bash services/applier/install.sh
# Stops at the first problem (the host check changes nothing). The install applies nothing by itself: approvals decided
# before it are skipped silently, so the test proposals #1 and #2 never run. Undo: docs/RUNBOOK.md, section Applier.
set -euo pipefail
cd "$(dirname "$0")/../.."
[ "$(id -u)" = 0 ] || { echo "run it with sudo" >&2; exit 1; }
install -d -o 0 -g 0 -m 0700 /opt/personal-agent-data/applier
install -d -o 0 -g 0 -m 0755 /opt/personal-agent-data/applier/outcome
/usr/bin/python3 -I services/applier/applier.py --check
/usr/bin/python3 -I services/applier/applier.py --mark-installed      # from now on control says what a tap does
install -m 0644 services/applier/systemd/pa-applier.service services/applier/systemd/pa-applier.path \
  services/applier/systemd/pa-applier.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now pa-applier.path pa-applier.timer
systemctl start pa-applier.service                                     # one pass now: skips what came before
journalctl -u pa-applier.service -n 20 --no-pager
systemctl list-timers pa-applier.timer --no-pager
