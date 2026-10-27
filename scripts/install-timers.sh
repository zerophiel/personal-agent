#!/usr/bin/env bash
# Install host systemd units from host/ (agents cannot edit these). Run via make deploy.
set -euo pipefail
src="$(cd "$(dirname "$0")/.." && pwd)/host"
install -m 0644 "$src"/*.service "$src"/*.timer "$src"/*.path /etc/systemd/system/
systemctl daemon-reload
for u in "$src"/*.timer "$src"/*.path; do systemctl enable --now "$(basename "$u")"; done
timedatectl set-timezone Asia/Jakarta
systemctl list-timers 'pa-*' --no-pager
