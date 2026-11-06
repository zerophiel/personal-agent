#!/usr/bin/env bash
# Deploy the daily-account anchor and the per-day removal (e5d494c, 60ae046) from a checkout of worktree-m1-skeleton:
#   ! bash /home/danoe/personal-agent/.claude/worktrees/m1-skeleton/ops/datafix/2026-11-01-pocket-balance/deploy.sh
# Order matters, the reverse of the pace fix: the data fix calls record_account_balance, which anchors only in the new
# code, so it runs AFTER vault-tools is rebuilt. Only vault-tools is rebuilt and the vault (Hermes) restarted (SOUL and
# tool docstrings changed). Safe to run again.
set -euo pipefail
D=ops/datafix/2026-11-01-pocket-balance
IDLE=ops/datafix/2026-10-31-pace-fix/idle_check.py
H='ubuntu@<vps>'   # history, ran once: ops/datafix/README.md
COMPOSE="sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env"
mask() { sed -E 's/[0-9]{9,}/[angka]/g'; }
cd "$(dirname "$0")/../../.."

echo "== 0/6 checkout"
test -z "$(git status --porcelain)" || { echo "STOP: uncommitted changes in the checkout"; exit 1; }
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/worktree-m1-skeleton)" || { echo "STOP: HEAD is not the pushed branch"; exit 1; }
git log --oneline -1

echo "== 1/6 bot idle?"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-1 /opt/hermes/.venv/bin/python -I -' < "$IDLE" | mask

echo "== 2/6 sync the repo (the rsync of make deploy)"
rsync -az --delete --exclude .git --exclude .claude --exclude 'secrets/*.dec*' --exclude graphify-out --exclude CLAUDE.md --exclude /private/ ./ "$H:/opt/personal-agent/"

echo "== 3/6 rebuild vault-tools only, wait until healthy"
ssh -o BatchMode=yes "$H" "cd /opt/personal-agent && $COMPOSE up -d --build --wait --wait-timeout 180 vault-tools" 2>&1 | tail -4

echo "== 4/6 ledger backup + the reading (on the new code)"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-tools-1 python -I -' < "$D/fix_data.py" | mask

echo "== 5/6 restart the vault (Hermes) when idle"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-1 /opt/hermes/.venv/bin/python -I -' < "$IDLE" | mask
ssh -o BatchMode=yes "$H" "cd /opt/personal-agent && $COMPOSE restart vault" 2>&1 | tail -2

echo "== 6/6 check (read only)"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-tools-1 python -I -' < "$D/verify.py" | mask
ssh -o BatchMode=yes "$H" "sudo docker ps --filter name=personal-agent-vault --format '{{.Names}} {{.Status}}'"
echo "DONE. Send /new to the bot once."
