#!/usr/bin/env bash
# Card repayments back in the expenses, and the guard that keeps them there, from a checkout of worktree-m1-skeleton:
#   ! bash /home/danoe/personal-agent/.claude/worktrees/m1-skeleton/ops/datafix/2026-11-01-card-internal/deploy.sh
# Scoped: only services/vault-tools is synced, onto its own twin, so --delete stays inside it (the operating note forbids
# a subfolder onto the server ROOT). The new code reads a transfer to an own card's number as that card's bill
# ('wajib:kartu') and refuses 'transfer_internal' for it in set_category, set_category_rule, set_category_keyword and on
# import; then fix_data.py moves the four September repayments, their four rules and Jago's main-pocket interest and tax
# to the right categories. The code goes in first, so no tool can put them back. set_category's docstring changed, which
# the vault restart loads; no SOUL change, so no /new. Control stays v2 and nothing of the M3 applier ships. Safe to run
# again.
set -euo pipefail
D=ops/datafix/2026-11-01-card-internal
IDLE=ops/datafix/2026-10-31-pace-fix/idle_check.py
H=ubuntu@43.157.242.194
COMPOSE="sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env"
mask() { sed -E 's/[0-9]{9,}/[angka]/g'; }
cd "$(dirname "$0")/../../.."

echo "== 0/6 checkout"
test -z "$(git status --porcelain)" || { echo "STOP: uncommitted changes in the checkout"; exit 1; }
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/worktree-m1-skeleton)" || { echo "STOP: HEAD is not the pushed branch"; exit 1; }
git log --oneline -1

echo "== 1/6 bot idle?"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-1 /opt/hermes/.venv/bin/python -I -' < "$IDLE" | mask

echo "== 2/6 sync services/vault-tools only"
rsync -az --delete --exclude __pycache__ services/vault-tools/ "$H:/opt/personal-agent/services/vault-tools/"

echo "== 3/6 rebuild vault-tools only, wait until healthy"
ssh -o BatchMode=yes "$H" "cd /opt/personal-agent && $COMPOSE up -d --build --wait --wait-timeout 180 vault-tools" 2>&1 | tail -4

echo "== 4/6 ledger backup + the categories (on the new code)"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-tools-1 python -I -' < "$D/fix_data.py" | mask

echo "== 5/6 restart the vault (Hermes) when idle"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-1 /opt/hermes/.venv/bin/python -I -' < "$IDLE" | mask
ssh -o BatchMode=yes "$H" "cd /opt/personal-agent && $COMPOSE restart vault" 2>&1 | tail -2

echo "== 6/6 check (read only)"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-tools-1 python -I -' < "$D/verify.py" | mask
ssh -o BatchMode=yes "$H" "sudo docker ps --filter name=personal-agent-vault --format '{{.Names}} {{.Status}}'"
echo "DONE. No /new needed."
