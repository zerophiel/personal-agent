#!/usr/bin/env bash
# make secrets-check, with sudo on the VPS: is every secret of config/secrets.manifest there with its mode, and how to make one
# that is not. Names and modes only: no value is read, and of a Hermes home's .env only whether a key name is set. Such a line
# wins over the rendered env (Hermes loads that file with override), so a rotated token must leave it too.
# Exit 1 when a secret is missing or has the wrong mode; the comms zone is built but not started, so its names may be absent.
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
S=${PA_SECRETS_DIR:-/opt/personal-agent-secrets}
D=${PA_DATA_DIR:-/opt/personal-agent-data}
manifest=$here/config/secrets.manifest
present=0 bad=0 comms=0

how_to_make() {  # how_to_make <name> <how>
  case "$2" in
    set)       echo "make secret-set NAME=$1" ;;
    gen:token) echo "make secret-gen NAME=$1 TYPE=token" ;;
    gen:key)   echo "make restore brings it back; a new key leaves the stored numbers unreadable" ;;
    pdf)       echo "make pdf-passwords" ;;
    renew)     echo "bash scripts/gmail-renew.sh from the laptop, docs/GMAIL_OAUTH.md" ;;
    client)    echo "docs/GMAIL_OAUTH.md" ;;
    hand)      echo "root 0600, the format is at the top of scripts/backup.sh" ;;
    *)         echo "config/secrets.manifest" ;;
  esac
}

while read -r name how zone mode; do
  case "$name" in ''|'#'*) continue ;; esac
  if [ ! -f "$S/$name" ] || [ ! -s "$S/$name" ]; then
    if [ "$zone" = comms ]; then comms=$((comms + 1)); continue; fi
    echo "missing: $name ($(how_to_make "$name" "$how"))"
    bad=$((bad + 1))
  elif [ "0$(stat -c %a "$S/$name")" != "$mode" ]; then
    echo "wrong mode: $name is $(stat -c %a "$S/$name") (sudo chmod $mode $S/$name)"
    bad=$((bad + 1))
  else
    present=$((present + 1))
  fi
done < "$manifest"

if [ -d "$S" ]; then
  for path in "$S"/*; do
    [ -e "$path" ] || continue
    grep -q "^$(basename "$path")[[:blank:]]" "$manifest" || echo "note: $(basename "$path") is not in config/secrets.manifest"
  done
fi

for home in "$D"/hermes-*; do
  [ -f "$home/.env" ] || continue
  for key in TELEGRAM_BOT_TOKEN ANTHROPIC_API_KEY; do
    line="^[[:blank:]]*(export[[:blank:]]+)?$key[[:blank:]]*="
    if grep -qE "$line" "$home/.env"; then
      echo "note: $(basename "$home")/.env sets $key and wins over the rendered env; after rotating that token: sudo sed -i -E '/$line/d' $home/.env"
    fi
  done
done

echo "secrets: $present in order, $bad to fix; comms zone, not started: $comms absent"
[ "$bad" = 0 ]
