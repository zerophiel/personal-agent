#!/usr/bin/env bash
# Deploy 2 (admin fees, bills paid once, undoing an instalment, the vault's stop grace period) from a checkout of
# worktree-m1-skeleton:
#   ! bash /home/danoe/personal-agent/.claude/worktrees/m1-skeleton/ops/datafix/2026-11-01-deploy2/deploy.sh
# The dry run comes first, by hand: fix_data.py with DRY=1 and a copy of the new code in VT (see its docstring).
# vault-tools is rebuilt (schema 14 on its first connect, after the backup), the data fix runs, and the vault (Hermes) is
# recreated: compose changed (stop_grace_period) and SOUL, a read-only mount, is read at start. Safe to run again.
set -euo pipefail
D=ops/datafix/2026-11-01-deploy2
IDLE=ops/datafix/2026-10-31-pace-fix/idle_check.py
H=ubuntu@43.157.242.194
COMPOSE="sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env"
mask() { sed -E 's/[0-9]{9,}/[angka]/g'; }
idle() { ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-1 /opt/hermes/.venv/bin/python -I -' < "$IDLE" | mask; }
cd "$(dirname "$0")/../../.."

echo "== 0/8 checkout"
test -z "$(git status --porcelain)" || { echo "STOP: uncommitted changes in the checkout"; exit 1; }
test "$(git rev-parse HEAD)" = "$(git rev-parse origin/worktree-m1-skeleton)" || { echo "STOP: HEAD is not the pushed branch"; exit 1; }
git log --oneline -1

echo "== 1/8 bot idle?"
idle

echo "== 2/8 ledger backup, before the new code migrates it to schema 14"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-tools-1 python -I -' < "$D/backup.py" | mask

echo "== 3/8 sync the repo (the rsync of make deploy), check compose"
rsync -az --delete --exclude .git --exclude .claude --exclude 'secrets/*.dec*' --exclude graphify-out --exclude CLAUDE.md \
  --exclude __pycache__ ./ "$H:/opt/personal-agent/"
ssh -o BatchMode=yes "$H" "cd /opt/personal-agent && $COMPOSE config -q && echo compose ok"

echo "== 4/8 rebuild vault-tools only, wait until healthy"
ssh -o BatchMode=yes "$H" "cd /opt/personal-agent && $COMPOSE up -d --build --wait --wait-timeout 180 vault-tools" 2>&1 | tail -4

echo "== 5/8 data fix when idle: fees from 30 Nov, the Coway expense, usulan #4 and #6, the plan made again"
idle
ssh -o BatchMode=yes "$H" 'sudo docker exec -i personal-agent-vault-tools-1 python -I -' < "$D/fix_data.py" | mask

echo "== 6/8 recreate the vault (Hermes) when idle"
idle
ssh -o BatchMode=yes "$H" "cd /opt/personal-agent && $COMPOSE up -d --no-deps --force-recreate vault" 2>&1 | tail -3

echo "== 7/8 check vault-tools (read only, on a copy)"
ssh -o BatchMode=yes "$H" 'sudo docker exec -i -e CHECK=1 personal-agent-vault-tools-1 python -I -' < "$D/fix_data.py" | mask

echo "== 8/8 check the vault: SOUL and cardguard as in this checkout, the stop grace period"
sha256sum services/hermes/vault/SOUL.md services/hermes/vault/plugins/cardguard/__init__.py | cut -c1-16
ssh -o BatchMode=yes "$H" 'sudo docker exec personal-agent-vault-1 sha256sum /opt/data/SOUL.md /opt/data/plugins/cardguard/__init__.py' | cut -c1-16
ssh -o BatchMode=yes "$H" "sudo docker inspect -f '{{.Name}} stop timeout {{.Config.StopTimeout}}' personal-agent-vault-1"
ssh -o BatchMode=yes "$H" "sudo docker ps --filter name=personal-agent-vault --format '{{.Names}} {{.Status}}'"
echo "DONE. Send /new to the bot once."
