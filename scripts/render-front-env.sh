#!/usr/bin/env bash
# Build the front container's env file ON the VPS from the secret files (root-only 0600), like render-vault-env.sh.
# Values are never printed. Run with sudo before `docker compose --profile front up -d` (docs/RUNBOOK.md, front zone).
# The front zone has its OWN Anthropic key (a separate workspace with its own spend limit) and its own bot token.
set -euo pipefail
S=/opt/personal-agent-secrets
OUT=/opt/personal-agent-data/front.env
ID="${MY_TELEGRAM_ID:-$(sed -n 's/^MY_TELEGRAM_ID=//p' /opt/personal-agent/config/stack.env)}"
[[ "$ID" =~ ^[0-9]+$ ]] || { echo "MY_TELEGRAM_ID not found in config/stack.env" >&2; exit 1; }
for f in anthropic_front_key telegram_front_token change_proposals_mcp_token; do
  [[ -s "$S/$f" ]] || { echo "missing secret $f (make secret-set NAME=$f)" >&2; exit 1; }
done
cmp -s "$S/anthropic_front_key" "$S/anthropic_vault_key" && { echo "anthropic_front_key must not be the vault key" >&2; exit 1; }
cmp -s "$S/telegram_front_token" "$S/telegram_vault_token" && { echo "telegram_front_token must not be the vault bot's" >&2; exit 1; }
umask 077
{
  printf 'ANTHROPIC_API_KEY=%s\n'            "$(cat $S/anthropic_front_key)"
  printf 'TELEGRAM_BOT_TOKEN=%s\n'           "$(cat $S/telegram_front_token)"
  printf 'CHANGE_PROPOSALS_MCP_TOKEN=%s\n'   "$(cat $S/change_proposals_mcp_token)"
  printf 'TELEGRAM_ALLOWED_USERS=%s\n'       "$ID"
  printf 'TELEGRAM_HOME_CHANNEL=%s\n'        "$ID"
  printf 'HERMES_SKIP_CONFIG_MIGRATION=1\n'
  printf 'HTTPS_PROXY=http://squid-front:3128\nHTTP_PROXY=http://squid-front:3128\n'
  printf 'NO_PROXY=localhost,127.0.0.1,change-proposals\n'
  printf 'TZ=Asia/Jakarta\n'
} > "$OUT"
chmod 0600 "$OUT"
echo "rendered $OUT ($(wc -l < "$OUT") vars)"
