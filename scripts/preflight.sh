#!/usr/bin/env bash
# Read-only VPS checks. Makes no changes. Run: make preflight
set -u
echo "== virtualization =="; systemd-detect-virt || true
echo "== cpu/mem/disk =="; nproc; free -m | head -2; df -h / | tail -1
echo "== os =="; . /etc/os-release; echo "$PRETTY_NAME"
echo "== docker =="; docker --version 2>&1; docker compose version 2>&1; docker info --format '{{.Driver}} {{.CgroupVersion}}' 2>&1
echo "== listening ports =="; ss -tlnH | awk '{print $4}'
echo "== ssh config =="; sudo -n sshd -T 2>/dev/null | grep -Ei '^(permitrootlogin|passwordauthentication)' || echo "(need sudo for sshd -T)"
echo "== firewall =="; sudo -n ufw status 2>/dev/null || echo "(ufw not readable)"
echo "== cpu steal (5s) =="; top -bn2 -d5 | grep '^%Cpu' | tail -1
