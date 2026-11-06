#!/usr/bin/env bash
# make capture: what the rebuild recipe needs from the live VPS and this repo lacks, read-only there, written into this
# checkout to review with git diff and commit. The hand-made host config goes to host/etc/ (scripts/install-timers.sh does
# not pick it up), and the exact packages of the running containers to requirements.lock. None of it holds a secret: the
# config files are named one by one, and every lock line must look like name==version, or nothing is written. It also prints
# the image digests to pin, and whether the running images were built on what the python tag points at now.
# comms-brokers has never been built: its direct pins are change-proposals' pins, so it shares that lock.
# Usage: capture-recipe.sh user@host
set -euo pipefail
host=${1:-}
[ -n "$host" ] || { echo "usage: $0 user@host" >&2; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
ROOTFS=${CAPTURE_REMOTE_ROOT:-}
FILES='etc/ssh/sshd_config.d/00-hardening.conf etc/docker/daemon.json etc/systemd/journald.conf.d/size.conf etc/sysctl.d/99-swappiness.conf etc/apt/apt.conf.d/20auto-upgrades'
LOCK_LINE='^[A-Za-z0-9][A-Za-z0-9._-]*==[A-Za-z0-9][A-Za-z0-9.+!_-]*$'
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=15)

as_root() { ssh "${SSH_OPTS[@]}" "$host" "sudo -n bash -c $(printf %q "$1")" </dev/null; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
mkdir "$tmp/etc" "$tmp/lock"

# Everything is read first and put in place at the end, so a failed read leaves the checkout as it was.
for rel in $FILES; do
  mkdir -p "$tmp/$(dirname "$rel")"
  as_root "cat $(printf %q "$ROOTFS/$rel")" > "$tmp/$rel"
  [ -s "$tmp/$rel" ] || { echo "capture: /$rel is empty on the VPS; nothing written" >&2; exit 1; }
done

for service in vault-tools change-proposals; do
  as_root "docker exec personal-agent-$service-1 pip --no-cache-dir freeze" > "$tmp/lock/$service"
  if [ ! -s "$tmp/lock/$service" ] || grep -qvE "$LOCK_LINE" "$tmp/lock/$service"; then
    echo "capture: the package list of $service does not look like name==version lines; nothing written" >&2
    exit 1
  fi
done

report=$(ssh "${SSH_OPTS[@]}" "$host" "sudo -n /usr/bin/python3 -I -" <<'EOF'
import json, subprocess
def run(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=120).stdout
def registry(ref, fmt="{{json .Manifest}}"):
    return json.loads(run("docker", "buildx", "imagetools", "inspect", ref, "--format", fmt))
BASE, SQUID = "python:3.12-slim", "ubuntu/squid:6.6-24.04_edge"
image = registry(BASE, '{{json (index .Image "linux/amd64")}}')
layers = image["rootfs"]["diff_ids"]
version = [e.split("=", 1)[1] for e in image["config"]["Env"] if e.startswith("PYTHON_VERSION=")]
print(f"{BASE}: {registry(BASE)['digest']} (Python {version[0] if version else 'unknown'})")
for name in ("vault-tools", "control", "ingest-gmail", "change-proposals"):
    built = json.loads(run("docker", "image", "inspect", f"personal-agent-{name}", "--format", "{{json .RootFS.Layers}}"))
    print(f"  personal-agent-{name} built on it: {'yes' if built[:len(layers)] == layers else 'no'}")
local = json.loads(run("docker", "image", "inspect", SQUID, "--format", "{{json .RepoDigests}}"))
print(f"{SQUID}: local {' '.join(local)}; registry now {registry(SQUID)['digest']}")
EOF
)

for rel in $FILES; do
  mkdir -p "$here/host/$(dirname "$rel")"
  install -m 0644 "$tmp/$rel" "$here/host/$rel"
done
write_lock() {  # write_lock <package list> <service folder>
  { echo "# pip freeze of the running container (make capture); the Dockerfile installs from this file."; cat "$1"; } > "$here/services/$2/requirements.lock"
}
write_lock "$tmp/lock/vault-tools" vault-tools
write_lock "$tmp/lock/change-proposals" change-proposals
write_lock "$tmp/lock/change-proposals" comms-brokers
echo "capture: host/etc and three requirements.lock written; review them with git diff"
printf '%s\n' "$report"
