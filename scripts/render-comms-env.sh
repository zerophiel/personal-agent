#!/usr/bin/env bash
# Build the comms container's env file ON the VPS from the secret files (root-only), like render-front-env.sh. Values
# are never printed. Run with sudo before the comms zone starts (docs/RUNBOOK.md, "Comms zone"; M4).
# comms has its OWN Anthropic key (a third workspace with its own spend limit) and its own bot token. The Google tokens
# stay with the brokers (compose/docker-compose.comms.yml) and are never in this file.
set -euo pipefail
S=${PA_SECRETS_DIR:-/opt/personal-agent-secrets}
OUT=${PA_COMMS_ENV:-/opt/personal-agent-data/comms.env}
ID="${MY_TELEGRAM_ID:-$(sed -n 's/^MY_TELEGRAM_ID=//p' /opt/personal-agent/config/stack.env)}"
[[ "$ID" =~ ^[0-9]+$ ]] || { echo "MY_TELEGRAM_ID not found in config/stack.env" >&2; exit 1; }
for f in anthropic_comms_key telegram_comms_token gmail_broker_mcp_token calendar_broker_mcp_token; do
  [[ -s "$S/$f" ]] || { echo "missing secret $f (docs/RUNBOOK.md, comms zone)" >&2; exit 1; }
done
for f in anthropic_vault_key anthropic_front_key; do
  cmp -s "$S/anthropic_comms_key" "$S/$f" && { echo "anthropic_comms_key must not be $f" >&2; exit 1; }
done
for f in telegram_vault_token telegram_front_token telegram_control_token; do
  cmp -s "$S/telegram_comms_token" "$S/$f" && { echo "telegram_comms_token must not be $f" >&2; exit 1; }
done
umask 077
{
  printf 'ANTHROPIC_API_KEY=%s\n'           "$(cat "$S/anthropic_comms_key")"
  printf 'TELEGRAM_BOT_TOKEN=%s\n'          "$(cat "$S/telegram_comms_token")"
  printf 'GMAIL_BROKER_MCP_TOKEN=%s\n'      "$(cat "$S/gmail_broker_mcp_token")"
  printf 'CALENDAR_BROKER_MCP_TOKEN=%s\n'   "$(cat "$S/calendar_broker_mcp_token")"
  printf 'TELEGRAM_ALLOWED_USERS=%s\n'      "$ID"
  printf 'TELEGRAM_HOME_CHANNEL=%s\n'       "$ID"
  printf 'HERMES_SKIP_CONFIG_MIGRATION=1\n'
  printf 'HTTPS_PROXY=http://squid-comms:3128\nHTTP_PROXY=http://squid-comms:3128\n'
  printf 'NO_PROXY=localhost,127.0.0.1,gmail-broker,calendar-broker\n'
  printf 'TZ=Asia/Jakarta\n'
} > "$OUT"
chmod 0600 "$OUT"
echo "rendered $OUT ($(wc -l < "$OUT") vars)"
