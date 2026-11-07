#!/usr/bin/env bash
# Build the vault container's env file ON the VPS from the secret files (root-only 0600), like render-front-env.sh. Values are
# never printed. Run with sudo before the vault starts (make render-envs). What is missing stops it before anything is written,
# and the file is replaced whole, so a stop leaves the last one as it was: compose refuses to start without this file.
set -euo pipefail
S=${PA_SECRETS_DIR:-/opt/personal-agent-secrets}
OUT=${PA_VAULT_ENV:-/opt/personal-agent-data/vault.env}
here=$(cd "$(dirname "$0")/.." && pwd)
ID="${MY_TELEGRAM_ID:-$(sed -n 's/^MY_TELEGRAM_ID=//p' "$here/config/stack.env")}"
[[ "$ID" =~ ^[0-9]+$ ]] || { echo "MY_TELEGRAM_ID not found in config/stack.env" >&2; exit 1; }
for f in anthropic_vault_key telegram_vault_token vault_tools_mcp_token vault_tools_internal_token; do
  [[ -f "$S/$f" && -s "$S/$f" ]] || { echo "missing secret $f (make secrets-check says how to make it)" >&2; exit 1; }
done
umask 077
trap 'rm -f "$OUT.tmp"' EXIT
{
  printf 'ANTHROPIC_API_KEY=%s\n'            "$(cat "$S/anthropic_vault_key")"
  printf 'TELEGRAM_BOT_TOKEN=%s\n'           "$(cat "$S/telegram_vault_token")"
  printf 'VAULT_TOOLS_MCP_TOKEN=%s\n'        "$(cat "$S/vault_tools_mcp_token")"
  printf 'VAULT_TOOLS_INTERNAL_TOKEN=%s\n'   "$(cat "$S/vault_tools_internal_token")"
  printf 'TELEGRAM_ALLOWED_USERS=%s\n'       "$ID"
  printf 'TELEGRAM_HOME_CHANNEL=%s\n'        "$ID"
  printf 'HERMES_SKIP_CONFIG_MIGRATION=1\n'
  printf 'HTTPS_PROXY=http://squid-vault:3128\nHTTP_PROXY=http://squid-vault:3128\n'
  printf 'NO_PROXY=localhost,127.0.0.1,vault-tools\n'
  printf 'TZ=Asia/Jakarta\n'
} > "$OUT.tmp"
chmod 0600 "$OUT.tmp"
mv -f "$OUT.tmp" "$OUT"
echo "rendered $OUT ($(wc -l < "$OUT") vars)"
