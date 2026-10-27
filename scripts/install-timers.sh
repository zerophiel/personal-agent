#!/usr/bin/env bash
# Install host systemd units from host/ (agents cannot edit these). Run via make deploy.
set -euo pipefail
src="$(cd "$(dirname "$0")/.." && pwd)/host"
install -m 0644 "$src"/*.service "$src"/*.timer /etc/systemd/system/
systemctl daemon-reload
for t in "$src"/*.timer; do systemctl enable --now "$(basename "$t")"; done
timedatectl set-timezone Asia/Jakarta
systemctl list-timers 'pa-*' --no-pager
