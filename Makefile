SHELL := /bin/bash
VPS_HOST ?= 43.157.242.194
VPS_USER ?= ubuntu
REMOTE_DIR ?= /opt/personal-agent
SSH := ssh $(VPS_USER)@$(VPS_HOST)
COMPOSE := sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env

.PHONY: help preflight deploy applied-pull status logs secret-set secret-gen pdf-passwords prune prune-dry backup restore mirror capture test runtime-map graph

help:
	@grep -E '^[a-z-]+:' Makefile | cut -d: -f1 | tr '\n' ' '; echo

# Read-only VPS checks (KVM, Docker, disk, steal). Safe to run.
preflight:
	$(SSH) 'bash -s' < scripts/preflight.sh

# Sync repo to VPS and apply compose + host timers. Plaintext secrets, private/ (make mirror's copy of the data and
# secrets), the local project map and the Python caches of local test runs are never synced. The guard holds the
# applier meanwhile and refuses while it has applied a change this checkout lacks (make applied-pull).
deploy:
	bash scripts/deploy-guard.sh start $(VPS_USER)@$(VPS_HOST)
	rsync -az --delete --exclude .git --exclude .claude --exclude 'secrets/*.dec*' --exclude graphify-out --exclude CLAUDE.md --exclude __pycache__ --exclude /private/ ./ $(VPS_USER)@$(VPS_HOST):$(REMOTE_DIR)/
	$(SSH) 'cd $(REMOTE_DIR) && sudo bash scripts/install-timers.sh && sudo bash scripts/data-dirs.sh && $(COMPOSE) up -d --build'
	bash scripts/deploy-guard.sh end $(VPS_USER)@$(VPS_HOST)

# The front changes the applier made on the VPS on the owner's tap (services/applier), as one commit each in this checkout
applied-pull:
	python3 -I scripts/applied-pull.py $(VPS_USER)@$(VPS_HOST)

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

# make pdf-passwords   (interactive, hidden input, runs on the VPS)
pdf-passwords:
	scp -q scripts/pdf-passwords-set.py $(VPS_USER)@$(VPS_HOST):/tmp/pa-pdf-passwords.py
	$(SSH) -t 'sudo python3 /tmp/pa-pdf-passwords.py; rm -f /tmp/pa-pdf-passwords.py'

prune-dry:
	$(SSH) 'cd $(REMOTE_DIR) && sudo DRY_RUN=1 bash scripts/prune.sh'

prune:
	$(SSH) 'cd $(REMOTE_DIR) && sudo bash scripts/prune.sh'

backup:
	$(SSH) 'sudo systemctl start pa-backup.service && journalctl -u pa-backup -n 20 --no-pager'

restore:
	@echo "See docs/RUNBOOK.md#restore (restores to a scratch dir only)"

# The full plaintext copy of the VPS data and secrets into private/ of the main checkout: read-only on the VPS, never in
# git, never synced, counts and statuses only. ALLOW_SHRINK=1 accepts a ledger with fewer rows than the last copy.
mirror:
	bash scripts/mirror.sh $(VPS_USER)@$(VPS_HOST)

# The hand-made host config and the exact Python packages, from the live VPS into this checkout to review and commit (read-only there)
capture:
	bash scripts/capture-recipe.sh $(VPS_USER)@$(VPS_HOST)

test:
	python3 -I -m unittest discover -s tests -v
	cd services/hermes/vault && python3 -I -m unittest discover -s tests -v   # the cardguard plugin
	cd services/hermes/front && python3 -I -m unittest discover -s tests -v   # the cardblock plugin
	cd services/control && python3 -I -m unittest discover -s tests -v
	cd services/applier && python3 -I -m unittest discover -s tests -v   # a fake docker; its zone-rule test needs PyYAML
	cd services/change-proposals && $${VAULT_PY:-python3} -I -m unittest discover -s tests -v   # needs mcp, as the vault-tools server tests
	cd services/comms-brokers && $${VAULT_PY:-python3} -I -m unittest discover -s tests -v   # M4 brokers; the MCP server tests need mcp too
	cd services/ingest-gmail && python3 -I -m unittest discover -s tests -v
	cd services/vault-tools && $${VAULT_PY:-python3} -I -m unittest discover -s tests -v   # VAULT_PY=venv python to include server tests

# Read-only snapshot of the live bot into docs/runtime/ (names, counts, dates; no secrets, balances or message text)
runtime-map:
	python3 -I ops/runtime-map/collect.py

# Refresh the code side of graphify-out/ (AST only, no LLM cost); after doc edits run /graphify . --update in Claude Code
graph:
	GRAPHIFY_NO_AUTO_REFRESH=1 graphify update .
