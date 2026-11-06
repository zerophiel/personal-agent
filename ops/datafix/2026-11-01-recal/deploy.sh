#!/usr/bin/env bash
# Deploy the 1 Nov recalibration (numbers the bot worked out itself now come from the code) from a checkout of
# worktree-m1-skeleton:
#   ! bash /home/danoe/personal-agent/.claude/worktrees/m1-skeleton/ops/datafix/2026-11-01-recal/deploy.sh
# Code only, no data change: vault-tools is rebuilt (tools, docstrings) and the vault (Hermes) restarted (SOUL and the
# cardguard plugin, both read-only mounts, are read at start). Safe to run again.
set -euo pipefail
D=ops/datafix/2026-11-01-recal
IDLE=ops/datafix/2026-10-31-pace-fix/idle_check.py
H=ubuntu@43.157.242.194
COMPOSE="sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env"
mask() { sed -E 's/[0-9]{9,}/[angka]/g'; }
cd "$(dirname "$0")/../../.."

echo "== 0/7 checkout"
test -z "$(git status --porcelain)" || { echo "STOP: uncommitted changes in the checkout"; exit 1; }
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/worktree-m1-skeleton)" || { echo "STOP: HEAD is not the pushed branch"; exit 1; }
git log --oneline -1

echo "== 1/7 bot idle?"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-1 /opt/hermes/.venv/bin/python -I -' < "$IDLE" | mask

echo "== 2/7 ledger backup (no data change, the way back all the same)"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-tools-1 python -I -' < "$D/backup.py" | mask

echo "== 3/7 sync the repo (the rsync of make deploy)"
rsync -az --delete --exclude .git --exclude .claude --exclude 'secrets/*.dec*' --exclude graphify-out --exclude CLAUDE.md --exclude /private/ ./ "$H:/opt/personal-agent/"

echo "== 4/7 rebuild vault-tools only, wait until healthy"
ssh -o BatchMode=yes "$H" "cd /opt/personal-agent && $COMPOSE up -d --build --wait --wait-timeout 180 vault-tools" 2>&1 | tail -4

echo "== 5/7 restart the vault (Hermes) when idle"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-1 /opt/hermes/.venv/bin/python -I -' < "$IDLE" | mask
ssh -o BatchMode=yes "$H" "cd /opt/personal-agent && $COMPOSE restart vault" 2>&1 | tail -2

echo "== 6/7 check vault-tools (read only)"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-tools-1 python -I -' < "$D/verify.py" | mask

echo "== 7/7 check the vault: SOUL and cardguard as in this checkout"
sha256sum services/hermes/vault/SOUL.md services/hermes/vault/plugins/cardguard/__init__.py | cut -c1-16
ssh -o BatchMode=yes "$H" 'sudo docker exec personal-agent-vault-1 sha256sum /opt/data/SOUL.md /opt/data/plugins/cardguard/__init__.py' | cut -c1-16
ssh -o BatchMode=yes "$H" "sudo docker ps --filter name=personal-agent-vault --format '{{.Names}} {{.Status}}'"
echo "DONE. Send /new to the bot once."
