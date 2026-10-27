SHELL := /bin/bash
VPS_HOST ?= 43.157.242.194
VPS_USER ?= ubuntu
REMOTE_DIR ?= /opt/personal-agent
SSH := ssh $(VPS_USER)@$(VPS_HOST)
COMPOSE := sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env

.PHONY: help preflight deploy status logs secret-set secret-gen prune prune-dry backup restore test

help:
	@grep -E '^[a-z-]+:' Makefile | cut -d: -f1 | tr '\n' ' '; echo

# Read-only VPS checks (KVM, Docker, disk, steal). Safe to run.
preflight:
	$(SSH) 'bash -s' < scripts/preflight.sh

# Sync repo to VPS and apply compose + host timers. Plaintext secrets are never synced.
deploy:
	rsync -az --delete --exclude .git --exclude .claude --exclude 'secrets/*.dec*' ./ $(VPS_USER)@$(VPS_HOST):$(REMOTE_DIR)/
	$(SSH) 'cd $(REMOTE_DIR) && sudo bash scripts/install-timers.sh && $(COMPOSE) up -d --build'

status:
	$(SSH) 'cd $(REMOTE_DIR) && $(COMPOSE) ps && df -h / && free -m && docker system df'

logs:
	$(SSH) 'cd $(REMOTE_DIR) && $(COMPOSE) logs --tail=100 $(SVC)'

# make secret-set NAME=telegram_control_token  (value is prompted on the VPS, never echoed)
secret-set:
	@test -n "$(NAME)" || (echo "NAME required"; exit 1)
	scp -q scripts/secret-set.sh $(VPS_USER)@$(VPS_HOST):/tmp/pa-secret-set.sh
	$(SSH) -t 'sudo bash /tmp/pa-secret-set.sh $(NAME); rm -f /tmp/pa-secret-set.sh'

# make secret-gen NAME=vault_tools_key TYPE=key   (random value created on the VPS)
secret-gen:
	@test -n "$(NAME)" -a -n "$(TYPE)" || (echo "NAME and TYPE required"; exit 1)
	scp -q scripts/secret-gen.sh $(VPS_USER)@$(VPS_HOST):/tmp/pa-secret-gen.sh
	$(SSH) 'sudo bash /tmp/pa-secret-gen.sh $(NAME) $(TYPE); rm -f /tmp/pa-secret-gen.sh'

prune-dry:
	$(SSH) 'cd $(REMOTE_DIR) && sudo DRY_RUN=1 bash scripts/prune.sh'

prune:
	$(SSH) 'cd $(REMOTE_DIR) && sudo bash scripts/prune.sh'

backup:
	$(SSH) 'sudo systemctl start pa-backup.service && journalctl -u pa-backup -n 20 --no-pager'

restore:
	@echo "See docs/RUNBOOK.md#restore (restores to a scratch dir only)"

test:
	cd services/control && python3 -I -m unittest discover -s tests -v
	cd services/vault-tools && $${VAULT_PY:-python3} -I -m unittest discover -s tests -v   # VAULT_PY=venv python to include server tests
