#!/usr/bin/env bash
# make bootstrap: makes a new Ubuntu 24.04 host ready for docs/REBUILD.md. The first part logs in as the provider's first account
# and may ask for its password, so this is a step for the owner's terminal. Before the doors close, this laptop proves it can
# log in as the account of config/vps.env with its key, use sudo and write to /opt/personal-agent. Only then does the second part
# set up sshd and the firewall (scripts/bootstrap-host.sh).
# The upload is host/etc, the package list, the host script and the PUBLIC key. BOOTSTRAP_KEY names another public key.
# Usage: bootstrap.sh first_login vps_login@host
set -euo pipefail
first_login=${1:-}
target=${2:-}
case "$target" in
  *@*) ;;
  *) target="" ;;
esac
if [ -z "$first_login" ] || [ -z "$target" ]; then
  echo "usage: make bootstrap BOOTSTRAP_USER=<the provider's first login>" >&2
  exit 2
fi
login=${target%@*}
host=${target#*@}
key=${BOOTSTRAP_KEY:-$HOME/.ssh/id_ed25519.pub}
here=$(cd "$(dirname "$0")/.." && pwd)
FIRST=(-o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new)
AFTER=(-o BatchMode=yes -o ConnectTimeout=15 -o StrictHostKeyChecking=accept-new)

one_public_key() {  # the upload must never carry a private key by mistake
  case "$key" in
    *.pub) ;;
    *) return 1 ;;
  esac
  [ -s "$key" ] && [ "$(wc -l < "$key")" -le 1 ] && grep -qE '^(ssh-|ecdsa-|sk-)[^ ]+ [A-Za-z0-9+/=]+( .*)?$' "$key"
}
if ! one_public_key; then
  echo "bootstrap: that is not one public key. Make one with ssh-keygen -t ed25519, or name it with BOOTSTRAP_KEY=<file.pub>" >&2
  exit 2
fi

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
install -m 0644 "$key" "$tmp/login.pub"
tar -czf "$tmp/upload.tgz" -C "$here" host/etc config/host-packages.txt scripts/bootstrap-host.sh -C "$tmp" login.pub

send() {  # send <first|second> <login@host> <ssh options...>: the upload lives and dies inside this one command
  local part=$1 to=$2 elevate="sudo -n" run
  shift 2
  [ "${to%@*}" != root ] || elevate=""
  run='d=$(mktemp -d) && trap "rm -rf \"\$d\"" EXIT && tar --no-same-owner -xzf - -C "$d" && bash "$d/scripts/bootstrap-host.sh" '"$part"' "$d" '"$login"
  ssh "$@" "$to" "$elevate bash -c $(printf %q "$run")" < "$tmp/upload.tgz"
}

proof() {
  ssh "${AFTER[@]}" "$login@$host" 'sudo -n true && : > /opt/personal-agent/.bootstrap-proof && rm -f /opt/personal-agent/.bootstrap-proof' </dev/null
}

echo "bootstrap: first part, as $first_login; this takes minutes"
if ! send first "$first_login@$host" "${FIRST[@]}"; then
  echo "bootstrap: the first part stopped. If a full run already closed root and password logins: make bootstrap BOOTSTRAP_USER=$login" >&2
  exit 1
fi
if ! proof; then
  echo "bootstrap: $login cannot log in with the key, use sudo and write to /opt/personal-agent. The doors are still open: fix it and run make bootstrap again" >&2
  exit 1
fi
echo "bootstrap: login proved, second part"
send second "$login@$host" "${AFTER[@]}"
if ! proof; then
  echo "bootstrap: the login stopped working after sshd and the firewall changed. From the provider's console: rm -f /etc/ssh/sshd_config.d/00-hardening.conf && ufw disable && systemctl reload-or-restart ssh" >&2
  exit 1
fi
echo "bootstrap: done; next: make preflight (docs/REBUILD.md)"
