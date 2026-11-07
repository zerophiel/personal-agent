#!/usr/bin/env bash
# The host side of make bootstrap (scripts/bootstrap.sh). Runs as root from an upload folder that holds host/etc,
# config/host-packages.txt, this script and the login's public key.
#   first:  everything but the doors: packages, Docker, swap, log limits, time zone, the login account with its key and sudo,
#           and /opt/personal-agent. Root and password logins still work, so a mistake here locks nobody out.
#   second: runs after the laptop has logged in with the key and used sudo: the sshd drop-in and the firewall.
# Safe to run again. The data and secrets folders stay absent: make restore puts them in place and refuses a host with a ledger.
# This script refuses that host too, and one with the project's containers, so it cannot touch a host in use.
# Usage: bootstrap-host.sh first|second upload_folder login
set -euo pipefail
umask 022

part=${1:-}
up=${2:-}
login=${3:-}
ROOTFS=${BOOTSTRAP_ROOT:-}
SWAP_TOTAL=$((4 * 1024 * 1024 * 1024))
SWAP_ENOUGH=$((3950 * 1024 * 1024))   # 4 GB shows as one page less, mkswap refuses a tiny file, and make preflight asks for 3900 MB
SWAP_NAME=/swapfile-personal-agent    # no provider's name: what a provider set up only counts, and stays
DROP_IN=etc/ssh/sshd_config.d/00-hardening.conf
SUDOERS=etc/sudoers.d/90-personal-agent-login
LOG=$ROOTFS/var/log/personal-agent-bootstrap.log

refuse() { echo "bootstrap: refused: $*; nothing changed" >&2; exit 1; }

fit_or_refuse() {
  case "$part" in
    first|second) ;;
    *) echo "usage: $0 first|second upload_folder login" >&2; exit 2 ;;
  esac
  [[ "$login" =~ ^[a-z_][a-z0-9_-]*$ ]] || refuse "the login must be a plain account name"
  [ "$login" != root ] || refuse "the login cannot be root: this recipe closes root logins"
  # shellcheck disable=SC1091
  . "$ROOTFS/etc/os-release"
  [ "${ID:-}-${VERSION_ID:-}" = ubuntu-24.04 ] || refuse "this recipe is for Ubuntu 24.04, this host has ${PRETTY_NAME:-something else}"
  [ "$(dpkg --print-architecture)" = amd64 ] || refuse "this recipe is for amd64"
  if command -v docker >/dev/null 2>&1 \
     && [ -n "$(docker ps -aq --filter label=com.docker.compose.project=personal-agent 2>/dev/null || true)" ]; then
    refuse "this host already has the project's containers"
  fi
  [ ! -e "$ROOTFS/opt/personal-agent-data/vault-tools/ledger.db" ] || refuse "this host already holds a ledger"
}

place() {  # place <path under etc/>: from the upload to the host
  install -D -m 0644 -o 0 -g 0 "$up/host/$1" "$ROOTFS/$1"
}

recipe_files() {  # all of host/etc but the two with their own moment: new captured files need no change here
  local rel
  while IFS= read -r rel; do
    case "$rel" in
      "$DROP_IN"|"$SUDOERS") continue ;;
    esac
    place "$rel"
  done < <(cd "$up/host" && find etc -type f | sort)
}

apt_run() {
  if ! DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=600 -o Dpkg::Options::=--force-confdef \
       -o Dpkg::Options::=--force-confold "$@" >>"$LOG" 2>&1; then
    echo "bootstrap: apt-get $1 failed; the end of $LOG:" >&2
    tail -n 15 "$LOG" >&2
    exit 1
  fi
}

packages() {  # only Docker at an exact version: Ubuntu's index drops old versions, Docker's keeps them
  local named pinned
  named=$(awk '!/^#/ && $3 == "note" {print $1}' "$up/config/host-packages.txt")
  pinned=$(awk '!/^#/ && $3 == "pin" {print $1 "=" $2}' "$up/config/host-packages.txt")
  apt_run update
  # shellcheck disable=SC2086
  apt_run install -y $named
  # shellcheck disable=SC2086
  apt_run install -y --allow-downgrades $pinned
}

swap() {  # up to 4 GB in total, counting what the provider set up
  local file=$ROOTFS$SWAP_NAME have=0 size
  if grep -q "^$SWAP_NAME[[:space:]]" "$ROOTFS/etc/fstab"; then
    return 0
  fi
  if [ -e "$file" ]; then   # a run that stopped halfway
    swapoff "$file" 2>/dev/null || true
    rm -f "$file"
  fi
  while read -r size; do
    have=$((have + size))
  done < <(swapon --show=SIZE --bytes --noheadings)
  [ "$have" -lt "$SWAP_ENOUGH" ] || return 0
  fallocate -l "$((SWAP_TOTAL - have))" "$file"
  chmod 0600 "$file"
  mkswap "$file" >/dev/null
  swapon "$file"
  printf '%s none swap sw 0 0\n' "$SWAP_NAME" >> "$ROOTFS/etc/fstab"
}

account() {  # the login of config/vps.env: existing keys stay, and sudo comes from a file visudo has accepted
  local home group keys key work
  id -u "$login" >/dev/null 2>&1 || useradd --create-home --shell /bin/bash "$login"
  home=$(getent passwd "$login" | cut -d: -f6)
  group=$(id -gn "$login")
  keys=$ROOTFS$home/.ssh/authorized_keys
  install -d -m 0700 -o "$login" -g "$group" "$ROOTFS$home/.ssh"
  key=$(cat "$up/login.pub")
  touch "$keys"
  if ! grep -qxF -- "$key" "$keys"; then
    [ -z "$(tail -c 1 "$keys")" ] || echo >> "$keys"
    printf '%s\n' "$key" >> "$keys"
  fi
  chown "$login:$group" "$keys"
  chmod 0600 "$keys"
  work=$(mktemp)
  sed "s/@LOGIN@/$login/" "$up/host/$SUDOERS" > "$work"
  if ! visudo -cf "$work" >/dev/null; then
    rm -f "$work"
    echo "bootstrap: visudo rejects the sudo rule; it is not installed" >&2
    exit 1
  fi
  install -D -m 0440 -o 0 -g 0 "$work" "$ROOTFS/$SUDOERS"
  rm -f "$work"
  install -d -m 0755 -o "$login" -g "$group" "$ROOTFS/opt/personal-agent"
}

package_report() {  # a difference is information, not a failure
  local name version now differ=0
  while read -r name version _; do
    now=$(dpkg-query -W -f='${Version}' "$name" 2>/dev/null || echo none)
    if [ "$now" != "$version" ]; then
      echo "bootstrap: $name is $now here, $version on the old host"
      differ=$((differ + 1))
    fi
  done < <(grep -v '^#' "$up/config/host-packages.txt")
  echo "bootstrap: packages: $differ differ from the old host"
}

first() {
  [ -s "$up/login.pub" ] || refuse "the upload has no public key"
  if command -v cloud-init >/dev/null 2>&1; then
    cloud-init status --wait >/dev/null 2>&1 || true   # a new instance may still be installing; "degraded" has finished too
  fi
  recipe_files   # daemon.json before Docker's first start, and Docker's repository before apt reads it
  packages
  recipe_files   # a package's setup may have written its own copy
  swap
  sysctl --system >/dev/null
  systemctl restart systemd-journald
  systemctl enable --now docker >/dev/null
  systemctl restart docker
  timedatectl set-timezone Asia/Jakarta
  account
  package_report
  echo "bootstrap: first part done"
}

second() {
  place "$DROP_IN"
  mkdir -p "$ROOTFS/run/sshd"
  if ! sshd -t; then
    rm -f "$ROOTFS/$DROP_IN"
    echo "bootstrap: sshd rejects its config with the drop-in, so the drop-in is gone again and the firewall is untouched" >&2
    exit 1
  fi
  systemctl reload-or-restart ssh
  ufw default deny incoming >/dev/null
  ufw default allow outgoing >/dev/null
  ufw default deny routed >/dev/null
  ufw logging low >/dev/null
  ufw allow 22/tcp >/dev/null   # before the firewall goes on, or this session is the last one
  ufw --force enable >/dev/null
  echo "bootstrap: second part done"
}

fit_or_refuse
"$part"
