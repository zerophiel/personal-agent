#!/usr/bin/env bash
# Generate a random secret ON the VPS (never typed, never in chat). Refuses to overwrite:
# replacing vault_tools_key would make every stored payee number undecryptable.
# Usage: secret-gen.sh NAME key|token
set -euo pipefail
name="${1:?secret name required}"; type="${2:?key|token}"
[[ "$name" =~ ^[a-z0-9_]+$ ]] || { echo "invalid name"; exit 1; }
dir=/opt/personal-agent-secrets
install -d -m 0700 -o root -g root "$dir"
[[ ! -e "${dir}/${name}" ]] || { echo "${name} already exists; refusing to overwrite"; exit 1; }
umask 077
case "$type" in
  key)   head -c 32 /dev/urandom | base64 -w0 > "${dir}/${name}" ;;   # 32 bytes, base64
  token) head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n' > "${dir}/${name}" ;;  # 64 hex chars
  *) echo "type must be key or token"; exit 1 ;;
esac
chmod 0444 "${dir}/${name}"   # dir stays 0700 root; file is mounted into the container as a docker secret
echo "generated ${name} (${type})"
