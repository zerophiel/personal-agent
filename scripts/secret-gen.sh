#!/usr/bin/env bash
# Generate a random secret ON the VPS (never typed, never in chat). Refuses to overwrite, and refuses vault_tools_key unless told
# this is the very first install: a new key makes every stored payee number undecryptable, and the key of a rebuilt host comes
# back through make restore.
# Usage: secret-gen.sh NAME key|token [--first-install]
set -euo pipefail
name="${1:?secret name required}"; type="${2:?key|token}"; first="${3:-}"
[[ "$name" =~ ^[a-z0-9_]+$ ]] || { echo "invalid name"; exit 1; }
if [[ "$name" == vault_tools_key && "$first" != --first-install ]]; then
  echo "vault_tools_key opens the stored account numbers, and a new one leaves them unreadable: bring the old one back (make restore)." >&2
  echo "Only on a host that never held any: make secret-gen NAME=vault_tools_key TYPE=key FIRST_INSTALL=1" >&2
  exit 1
fi
dir=${PA_SECRETS_DIR:-/opt/personal-agent-secrets}
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
