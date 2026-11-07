#!/usr/bin/env bash
# Read-only checks of a host after make bootstrap: can it run the stack, and can it reach everything the stack needs? Changes
# nothing and uses no credential. Exit 0 only when every check passes. A failure is a reason to fix the host or take another
# provider while the old bot still runs (docs/REBUILD.md). Run: make preflight
# R2 is not here: its address is inside restic.env, and make snapshots proves it.
# It reaches the host on stdin (bash -s), so main reads /dev/null: a command that reads stdin must not eat the script.
set -u
OS_RELEASE=${PREFLIGHT_OS_RELEASE:-/etc/os-release}
MIN_CPUS=2
MIN_MEM_MB=7000
MIN_DISK_GB=40
MIN_SWAP_MB=3900
failed=0

verdict() {  # verdict <label> <what was seen> <test command...>
  local label=$1 seen=$2
  shift 2
  if "$@" >/dev/null 2>&1; then
    echo "ok    $label: $seen"
  else
    echo "FAIL  $label: $seen"
    failed=$((failed + 1))
  fi
}
note() { echo "note  $1: $2"; }
at_least() { [ "$1" -ge "$2" ]; }
holds() { printf '%s\n' "$1" | grep -Eq "$2"; }
answered() { [ "$1" != 000 ] && [ "$1" != 403 ] && [ "$1" != 451 ]; }   # the API answers a refused region with 403 or 451
answered_at_all() { [ "$1" != 000 ]; }

reach() {  # reach <test> <url>: no credential, so any HTTP answer shows the way is open
  local code
  code=$(curl -sS -o /dev/null -m 20 -w '%{http_code}' "$2" 2>/dev/null) || true
  code=${code:-000}
  verdict "reach" "$2 answers $code" "$1" "$code"
}

main() {
  local container arch cpus mem swap disk docker_info sshd_says ufw_says zone
  container=$(systemd-detect-virt --container 2>/dev/null) || true
  verdict "machine" "$(systemd-detect-virt 2>/dev/null), container: ${container:-none}" test "${container:-none}" = none

  [ -r "$OS_RELEASE" ] && . "$OS_RELEASE"
  verdict "os" "${PRETTY_NAME:-unknown}" test "${ID:-}-${VERSION_ID:-}" = ubuntu-24.04
  arch=$(dpkg --print-architecture 2>/dev/null)
  verdict "architecture" "${arch:-unknown}" test "${arch:-}" = amd64

  cpus=$(nproc)
  verdict "cpus" "$cpus, at least $MIN_CPUS" at_least "$cpus" "$MIN_CPUS"
  mem=$(free -m | awk '/^Mem:/ {print $2}')
  verdict "memory" "$mem MB, at least $MIN_MEM_MB" at_least "$mem" "$MIN_MEM_MB"
  swap=$(free -m | awk '/^Swap:/ {print $2}')
  verdict "swap" "$swap MB, at least $MIN_SWAP_MB" at_least "$swap" "$MIN_SWAP_MB"
  disk=$(df -BG --output=avail / | tail -1 | tr -dc '0-9')
  verdict "free disk" "$disk GB, at least $MIN_DISK_GB" at_least "$disk" "$MIN_DISK_GB"

  verdict "sudo" "works without a password" sudo -n true
  verdict "docker" "$(sudo -n docker --version 2>&1 | head -1)" sudo -n docker --version
  verdict "compose" "$(sudo -n docker compose version 2>&1 | head -1)" sudo -n docker compose version
  docker_info=$(sudo -n docker info --format '{{.Driver}} {{.CgroupVersion}} {{.LoggingDriver}}' 2>&1 | head -1)
  verdict "docker setup" "$docker_info" holds "$docker_info" '^(overlayfs|overlay2) 2 json-file$'

  verdict "python" "sqlite3 serialize and yaml" python3 -I -c 'import sqlite3, yaml; sqlite3.Connection.serialize'
  verdict "restic" "$(restic version 2>&1 | head -1)" restic version
  verdict "rsync" "$(rsync --version 2>&1 | head -1)" rsync --version

  sshd_says=$(sudo -n sshd -T 2>/dev/null | grep -Ei '^(permitrootlogin|passwordauthentication) ' | sort | tr '\n' ' ')
  verdict "ssh" "$sshd_says" test "$sshd_says" = "passwordauthentication no permitrootlogin no "
  ufw_says=$(sudo -n ufw status 2>/dev/null)
  verdict "firewall" "$(printf '%s\n' "$ufw_says" | head -1), 22/tcp open" holds "$ufw_says" '^Status: active'
  verdict "firewall port" "22/tcp allowed" holds "$ufw_says" '^22/tcp +ALLOW'
  zone=$(timedatectl show -p Timezone --value 2>/dev/null)
  verdict "time zone" "${zone:-unknown}: the timers run on it" test "${zone:-}" = Asia/Jakarta

  note "clock synced" "$(timedatectl show -p NTPSynchronized --value 2>/dev/null)"
  note "listening" "$(ss -tlnH | awk '{print $4}' | tr '\n' ' ')"
  note "cpu steal over 5s" "$(top -bn2 -d5 | grep '^%Cpu' | tail -1)"

  reach answered https://api.anthropic.com/v1/messages
  reach answered_at_all https://api.telegram.org/
  reach answered_at_all https://api.notion.com/v1/users
  reach answered_at_all https://gmail.googleapis.com/
  reach answered_at_all https://oauth2.googleapis.com/
  reach answered_at_all https://www.googleapis.com/
  reach answered_at_all https://calendar.google.com/
  reach answered_at_all https://raw.githubusercontent.com/
  reach answered_at_all https://registry-1.docker.io/v2/
  reach answered_at_all https://auth.docker.io/token
  reach answered_at_all https://production.cloudflare.docker.com/
  reach answered_at_all https://pypi.org/simple/
  reach answered_at_all https://files.pythonhosted.org/
  reach answered_at_all https://download.docker.com/linux/ubuntu/

  if [ "$failed" -eq 0 ]; then
    echo "preflight: all checks passed"
    return 0
  fi
  echo "preflight: $failed failed"
  return 1
}

main </dev/null
exit $?
