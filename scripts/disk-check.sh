#!/usr/bin/env bash
# Hourly: alert at 75% via the control bot; at 90% also prune build cache (never volumes).
set -euo pipefail
pct=$(df --output=pcent / | tail -1 | tr -dc '0-9')
notify() {
  tok=$(cat /opt/personal-agent-secrets/telegram_control_token)
  curl -fsS -m 20 "https://api.telegram.org/bot${tok}/sendMessage" \
    --data-urlencode "chat_id=${MY_TELEGRAM_ID}" --data-urlencode "text=$1" \
    -d disable_web_page_preview=true >/dev/null || true
}
if (( pct >= 90 )); then docker builder prune -f >/dev/null; notify "Disk ${pct}% - build cache dipangkas"
elif (( pct >= 75 )); then notify "Disk ${pct}% terpakai"; fi
echo "disk ${pct}%"
