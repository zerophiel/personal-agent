#!/usr/bin/env bash
# Remove the 17 doubled Mandiri October rows and deploy the overlap matching from a checkout of worktree-m1-skeleton:
#   ! bash /home/danoe/personal-agent/.claude/worktrees/m1-skeleton/ops/datafix/2026-11-01-mandiri-dupes/deploy.sh
# Scoped: two folders are synced, each onto its own twin, so --delete stays inside it (the operating note forbids a
# subfolder onto the server ROOT). A content dry run on 1 Nov showed only this fix and cardguard differ in them:
# - services/vault-tools, rebuilt: the overlap matching, the ledger check, the audit rule;
# - services/hermes/vault: cardguard's owner check and TTL count log (e9c1bc4), which never reached the VPS (SOUL.md
#   and config.yaml are unchanged). The plugin is mounted as a folder, so the vault restart loads it; the same restart
#   reconnects Hermes to the new tool server. Pre-checked in the vault container: the allowlist holds the owner alone.
# Control stays v2 and nothing of the M3 applier ships: that is the M3 gate's own `make deploy`. No SOUL or tool
# docstring changed, so no /new. The new code goes in before the rows go, so a re-sent e-statement cannot bring them
# back. Safe to run again.
set -euo pipefail
D=ops/datafix/2026-11-01-mandiri-dupes
IDLE=ops/datafix/2026-10-31-pace-fix/idle_check.py
H='ubuntu@<vps>'   # history, ran once: ops/datafix/README.md
COMPOSE="sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env"
CG=services/hermes/vault/plugins/cardguard/__init__.py
mask() { sed -E 's/[0-9]{9,}/[angka]/g'; }
cd "$(dirname "$0")/../../.."

echo "== 0/6 checkout"
test -z "$(git status --porcelain)" || { echo "STOP: uncommitted changes in the checkout"; exit 1; }
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/worktree-m1-skeleton)" || { echo "STOP: HEAD is not the pushed branch"; exit 1; }
git log --oneline -1

echo "== 1/6 bot idle?"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-1 /opt/hermes/.venv/bin/python -I -' < "$IDLE" | mask

echo "== 2/6 sync services/vault-tools and services/hermes/vault only"
rsync -az --delete --exclude __pycache__ services/vault-tools/ "$H:/opt/personal-agent/services/vault-tools/"
rsync -az --delete --exclude __pycache__ services/hermes/vault/ "$H:/opt/personal-agent/services/hermes/vault/"

echo "== 3/6 rebuild vault-tools only, wait until healthy"
ssh -o BatchMode=yes "$H" "cd /opt/personal-agent && $COMPOSE up -d --build --wait --wait-timeout 180 vault-tools" 2>&1 | tail -4

echo "== 4/6 ledger backup + remove the doubled rows (on the new code)"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-tools-1 python -I -' < "$D/fix_data.py" | mask

echo "== 5/6 restart the vault (Hermes) when idle"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-1 /opt/hermes/.venv/bin/python -I -' < "$IDLE" | mask
ssh -o BatchMode=yes "$H" "cd /opt/personal-agent && $COMPOSE restart vault" 2>&1 | tail -2

echo "== 6/6 check (read only)"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-tools-1 python -I -' < "$D/verify.py" | mask
want=$(sha256sum "$CG" | cut -d' ' -f1)
got=$(ssh -o BatchMode=yes "$H" 'sudo docker exec personal-agent-vault-1 sha256sum /opt/data/plugins/cardguard/__init__.py' | cut -d' ' -f1)
test "$want" = "$got" || { echo "STOP: cardguard in the vault container is not the repo's"; exit 1; }
echo "cardguard in the vault container: the repo's"
ssh -o BatchMode=yes "$H" "sudo grep -c 'TELEGRAM_ALLOWED_USERS is empty' /opt/personal-agent-data/hermes-vault/logs/agent.log || true" \
  | sed 's/^/agent.log lines saying the allowlist is empty (want 0): /'
ssh -o BatchMode=yes "$H" "sudo docker ps --filter name=personal-agent-vault --format '{{.Names}} {{.Status}}'"
echo "DONE. No /new needed. About a minute after the restart agent.log says 'cardguard: command menu restored'."
