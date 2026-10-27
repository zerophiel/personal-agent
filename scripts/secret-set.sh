#!/usr/bin/env bash
# Prompt for a secret value on the VPS (not echoed, never in chat) and store it root-owned 0400.
set -euo pipefail
name="${1:?secret name required}"
[[ "$name" =~ ^[a-z0-9_]+$ ]] || { echo "invalid name"; exit 1; }
dir=/opt/personal-agent-secrets
install -d -m 0700 -o root -g root "$dir"
read -rsp "Value for ${name}: " value; echo
umask 077
printf '%s' "$value" > "${dir}/${name}"
chmod 0444 "${dir}/${name}"   # readable by container uid via docker secret mount; dir stays 0700 root
echo "stored ${name}"
