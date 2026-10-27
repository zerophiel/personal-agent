#!/usr/bin/env bash
# Build the vault container's env file ON the VPS from the secret files (root-only 0600).
# Values are never printed. Run before `docker compose up vault`.
set -euo pipefail
S=/opt/personal-agent-secrets
OUT=/opt/personal-agent-data/vault.env
umask 077
{
  printf 'ANTHROPIC_API_KEY=%s\n'            "$(cat $S/anthropic_vault_key)"
  printf 'TELEGRAM_BOT_TOKEN=%s\n'           "$(cat $S/telegram_vault_token)"
  printf 'VAULT_TOOLS_MCP_TOKEN=%s\n'        "$(cat $S/vault_tools_mcp_token)"
  printf 'VAULT_TOOLS_INTERNAL_TOKEN=%s\n'   "$(cat $S/vault_tools_internal_token)"
  printf 'TELEGRAM_ALLOWED_USERS=%s\n'       "${MY_TELEGRAM_ID:?}"
  printf 'TELEGRAM_HOME_CHANNEL=%s\n'        "${MY_TELEGRAM_ID:?}"
  printf 'HERMES_SKIP_CONFIG_MIGRATION=1\n'
  printf 'HTTPS_PROXY=http://squid-vault:3128\nHTTP_PROXY=http://squid-vault:3128\n'
  printf 'NO_PROXY=localhost,127.0.0.1,vault-tools\n'
  printf 'TZ=Asia/Jakarta\n'
} > "$OUT"
chmod 0600 "$OUT"
echo "rendered $OUT ($(wc -l < "$OUT") vars)"
