#!/usr/bin/env bash
# make mirror: the full plaintext copy of the VPS data and secrets into private/ of the main checkout, by the owner's
# decision of 2026-11-06 (docs/SECURITY.md), so that folder alone can rebuild the bot (docs/REBUILD.md). The destination is
# the folder holding the shared .git, also from a linked worktree, so removing a worktree never removes the copy.
#   private/vps    the current copy: data/, secrets/, host/ (ownership lists, live config, versions), MIRROR.json
#   private/.prev  the copy before it, kept only when that one had no raw database
#   private/.new   being pulled; it replaces vps only after scripts/mirror-check.py passes, so a failed pull, an empty host
#                  or the wrong host never moves a good copy
#   private/laptop, private/knowledge  what lives only on this laptop; added to, never deleted from
# Databases come from scripts/db-copy.py, everything else from rsync as root on the VPS. Read-only there. Prints counts and
# statuses only: statement file names hold the owner's name and account fragments, so rsync's messages go to
# private/mirror.log. Exit 0: all good. Exit 3: swapped, but a database is carried raw or a host fact failed. Exit 1: no swap.
# Usage: mirror.sh user@host   (ALLOW_SHRINK=1 accepts a ledger with fewer rows than the last copy)
set -euo pipefail
umask 077
host=${1:-}
[ -n "$host" ] || { echo "usage: $0 user@host" >&2; exit 2; }
here=$(cd "$(dirname "$0")/.." && pwd)
PY=${MIRROR_PY:-python3}
DATA=${MIRROR_REMOTE_DATA:-/opt/personal-agent-data}
SECRETS=${MIRROR_REMOTE_SECRETS:-/opt/personal-agent-secrets}
ROOTFS=${MIRROR_REMOTE_ROOT:-/}
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=15 -o ServerAliveCountMax=4)
# Named, one by one: never /etc/shadow or the ssh host keys. Read as root, for private/ only.
LIVE='etc/ssh/sshd_config etc/ssh/sshd_config.d etc/docker/daemon.json etc/systemd/journald.conf.d etc/sysctl.d/99-swappiness.conf etc/apt/apt.conf.d/20auto-upgrades etc/apt/sources.list.d/docker.list etc/apt/keyrings/docker.asc etc/fstab etc/sudoers.d etc/default/ufw etc/ufw/user.rules etc/ufw/user6.rules etc/timezone etc/systemd/system/pa-*'

say() { echo "mirror: $*"; }
refuse() { echo "mirror: refused: $*; the last copy stays as it was" >&2; exit 1; }
as_root() { ssh "${SSH_OPTS[@]}" "$host" "sudo -n bash -c $(printf %q "$1")" </dev/null; }

# --- the fence, before anything exists to protect: the main checkout may not have this repo's .gitignore yet
common=$(git -C "$here" rev-parse --path-format=absolute --git-common-dir) || refuse "this is not a git checkout"
root=$(dirname "$common")
private=$root/private
new=$private/.new
mkdir -p "$common/info"
grep -qxF /private/ "$common/info/exclude" 2>/dev/null || printf '\n/private/\n' >> "$common/info/exclude"
git -C "$root" check-ignore -q private/ || refuse "git does not ignore private/ in the main checkout"
grep -q -e '--exclude /private/' "$here/Makefile" || refuse "make deploy in this checkout would send private/ to the VPS"
install -d -m 0700 "$private"
chmod 0700 "$private"
say "fence ok"

exec 9>"$private/.lock"
flock -n 9 || refuse "another make mirror is running"

# --- an interrupted swap: put the newest whole copy back in place; see the swap below for what each name means
if [ ! -d "$private/vps" ]; then
  if [ -d "$private/.old" ]; then
    mv "$private/.old" "$private/vps"
    say "restored the last copy after an interrupted run"
  elif [ -d "$private/.prev" ]; then
    mv "$private/.prev" "$private/vps"
    say "restored the last copy after an interrupted run"
  fi
fi
if [ ! -d "$private/.prev" ] && [ -d "$private/.prev.old" ]; then
  mv "$private/.prev.old" "$private/.prev"
fi
rm -rf "$new" "$private/.old" "$private/.prev.old"

log=$private/mirror.log
: > "$log"
trap 'rm -rf "$new"' EXIT
install -d -m 0700 "$new" "$new/data" "$new/secrets" "$new/host" "$new/host/live"

# Nothing of the project running, no pa-* unit at work: a frozen host, where the copy must match its listing exactly.
busy() {
  as_root "docker ps -q --filter label=com.docker.compose.project=personal-agent && systemctl list-units 'pa-*.service' --state=active,activating --no-legend --no-pager"
}
busy_start=$(busy 2>>"$log") || refuse "the VPS does not answer (ssh or sudo failed)"

ownership() {
  ssh "${SSH_OPTS[@]}" "$host" "sudo -n /usr/bin/python3 -I - $(printf %q "$DATA") $(printf %q "$SECRETS")" <<'EOF'
import json, os, stat, sys
def row(label, path, rel):
    try:
        st = os.lstat(path)
    except OSError:
        return
    m = st.st_mode
    kind = "d" if stat.S_ISDIR(m) else "f" if stat.S_ISREG(m) else "l" if stat.S_ISLNK(m) else "o"
    print(json.dumps({"r": label, "p": rel, "t": kind, "u": st.st_uid, "g": st.st_gid, "m": stat.S_IMODE(m)}))
for label, root in (("data", sys.argv[1]), ("secrets", sys.argv[2])):
    row(label, root, "")
    for folder, dirs, files in os.walk(root):
        for name in dirs + files:
            path = os.path.join(folder, name)
            row(label, path, os.path.relpath(path, root))
EOF
}

# 0 and 24 (a file vanished while copying, on a live host) pass; 23 (some files failed) is tried once more. Times compare to
# the nanosecond: with --copy-dest, a same-size file changed within the second of the last copy would otherwise stay old.
pull() {
  local from=$1 to=$2 tries=0 rc
  shift 2
  while :; do
    rc=0
    rsync -rlptz -q --modify-window=-1 --rsync-path='sudo -n rsync' -e "ssh ${SSH_OPTS[*]}" --chmod=D700,F600 "$@" "$host:$from/" "$to/" 2>>"$log" || rc=$?
    case $rc in
      0|24) return 0 ;;
      23) if [ "$tries" = 0 ]; then tries=1; continue; fi ;;
    esac
    return "$rc"
  done
}

ownership > "$new/host/ownership.before.jsonl" 2>>"$log" || refuse "listing the VPS folders failed"
"$PY" -I "$here/scripts/db-copy.py" "$host" "$DATA" "$new/data" "$new/host/db-report.json" "$new/host/db-excludes" 2>>"$log" || refuse "the database step stopped (details in private/mirror.log)"
reuse=()
[ -d "$private/vps/data" ] && reuse=("--copy-dest=$private/vps/data")
pull "$DATA" "$new/data" "${reuse[@]}" --from0 "--exclude-from=$new/host/db-excludes" || refuse "copying the data failed (rsync exit $?, details in private/mirror.log)"
pull "$SECRETS" "$new/secrets" || refuse "copying the secrets failed (rsync exit $?, details in private/mirror.log)"
ownership > "$new/host/ownership.jsonl" 2>>"$log" || refuse "listing the VPS folders failed"
busy_end=$(busy 2>>"$log") || refuse "the VPS stopped answering"
frozen=0
[ -z "$busy_start$busy_end" ] && frozen=1

# --- facts about the host. None holds a secret, and a failed one is carried over from the last copy and counted.
facts_failed=0
carry() {
  [ -e "$private/vps/host/$1" ] && cp -a "$private/vps/host/$1" "$new/host/$1"
  return 0
}
fact() {
  if ! as_root "$2" > "$new/host/$1" 2>>"$log"; then
    facts_failed=$((facts_failed + 1))
    carry "$1"
  fi
}
live_etc() {
  as_root "cd $(printf %q "$ROOTFS") && for f in $LIVE; do [ -e \"\$f\" ] && printf '%s\n' \"\$f\"; done | tar -cf - -T -" 2>>"$log"
}
if live_etc | tar -xf - -C "$new/host/live" --no-same-owner 2>>"$log"; then
  chmod -R u+rwX "$new/host/live"
else
  facts_failed=$((facts_failed + 1))
  rm -rf "$new/host/live"
  carry live
fi
fact packages.txt 'dpkg-query -W -f="\${Package} \${Version}\n"'
fact containers.txt 'docker ps -a --format "{{.Names}} {{.Image}} {{.State}}"'
fact images.txt 'docker image ls --digests --format "{{.Repository}}:{{.Tag}} {{.Digest}} {{.ID}}"'
fact units.txt "systemctl list-unit-files 'pa-*' --no-legend --no-pager; systemctl list-timers 'pa-*' --all --no-legend --no-pager"
fact ufw.txt 'ufw status verbose'
fact machine.txt 'cat /etc/os-release; uname -m; nproc; free -m; df -h /; swapon --show; timedatectl show -p Timezone --value'
for service in vault-tools change-proposals; do
  if [ "$frozen" = 1 ]; then   # stopped on purpose: the versions are in requirements.lock and the last copy
    carry "pip-$service.txt"
  else
    fact "pip-$service.txt" "docker exec personal-agent-$service-1 pip --no-cache-dir freeze"
  fi
done

# --- the checks decide whether this copy replaces the last one
check=0
"$PY" -I "$here/scripts/mirror-check.py" --new "$new" --prev "$private/vps/MIRROR.json" --repo "$here" --frozen "$frozen" --facts-failed "$facts_failed" || check=$?
case $check in
  0|3) ;;
  *) echo "mirror: failed checks; the last copy stays as it was" >&2; exit 1 ;;
esac

# --- the swap. Every step is a rename, and the recovery above handles a kill between any two. .prev moves on only when the
# outgoing copy had no raw database; otherwise it stays the last wholly clean one and the outgoing copy goes.
outgoing_clean() {
  "$PY" -I -c 'import json, sys; sys.exit(0 if json.load(open(sys.argv[1])).get("clean") else 1)' "$private/vps/MIRROR.json" 2>/dev/null
}
if [ -d "$private/vps" ]; then
  if outgoing_clean; then
    if [ -d "$private/.prev" ]; then mv "$private/.prev" "$private/.prev.old"; fi
    mv "$private/vps" "$private/.prev"
  else
    mv "$private/vps" "$private/.old"
  fi
fi
mv "$new" "$private/vps"
rm -rf "$private/.prev.old" "$private/.old"
say "swapped"

# --- what lives only on this laptop: added to and refreshed, never deleted from, so transcripts outlive Claude Code's own
# 30-day cleanup. The private SSH key stays out: it belongs to the laptop, and a new laptop makes a new one.
laptop_missing=0
keep() {  # keep <source folder> <destination folder>
  if [ -d "$1" ]; then
    local rc=0
    install -d -m 0700 "$2"
    rsync -rlpt -q --chmod=D700,F600 "$1/" "$2/" 2>>"$log" || rc=$?
    case $rc in 0|24) ;; *) laptop_missing=$((laptop_missing + 1)) ;; esac
  else
    laptop_missing=$((laptop_missing + 1))
  fi
}
keep_file() {  # keep_file <source file> <destination folder>
  if [ -f "$1" ]; then
    install -d -m 0700 "$2"
    install -m 0600 "$1" "$2/"
  else
    laptop_missing=$((laptop_missing + 1))
  fi
}
keep_file "$HOME/client_secret_ingest.json" "$private/laptop"
keep_file "$HOME/client_secret.ingest.json" "$private/laptop"
keep_file "$HOME/.ssh/id_ed25519.pub" "$private/laptop"
project=${root//[\/.]/-}   # Claude Code's folder for this checkout, and one more for each of its worktrees
keep "$HOME/.claude/projects/$project" "$private/knowledge/claude-projects/$project"
for folder in "$HOME/.claude/projects/$project"--*; do
  if [ -d "$folder" ]; then keep "$folder" "$private/knowledge/claude-projects/$(basename "$folder")"; fi
done
keep "$HOME/.graphify/repos/NousResearch/hermes-agent-v0.22.5" "$private/knowledge/hermes-engine"
keep "$here/graphify-out" "$private/knowledge/graphify-out"
say "laptop part: $laptop_missing missing"

if [ "$check" = 3 ]; then
  echo "mirror: swapped with warnings: a database is carried raw or a host fact failed (private/mirror.log, MIRROR.json)" >&2
fi
say "done"
exit "$check"
