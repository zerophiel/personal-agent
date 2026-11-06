SHELL := /bin/bash
# config/vps.env is the one place the address lives; make <target> VPS_HOST=... VPS_USER=... reaches another host
VPS_HOST ?= $(shell sed -n 's/^VPS_HOST=//p' config/vps.env)
VPS_USER ?= $(shell sed -n 's/^VPS_USER=//p' config/vps.env)
REMOTE_DIR ?= /opt/personal-agent
SSH := ssh $(VPS_USER)@$(VPS_HOST)
COMPOSE := sudo docker compose -f compose/docker-compose.yml --env-file config/stack.env
# make venv's Python when it exists (outside the repo, so it is never synced), else the system's
VENV ?= $(HOME)/.venv-personal-agent
PY ?= $(firstword $(wildcard $(VENV)/bin/python) python3)

.PHONY: help preflight deploy sync up front render-envs secrets-check timers applier venv applied-pull status logs secret-set secret-gen pdf-passwords prune prune-dry backup restore snapshots restore-restic mirror capture test runtime-map graph

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

# The pieces of make deploy, one at a time, for a new host (docs/REBUILD.md) or a change that should restart nothing.
# Only the copy: what it carries takes effect when a service restarts or a timer next runs.
sync:
	bash scripts/deploy-guard.sh start $(VPS_USER)@$(VPS_HOST)
	rsync -az --delete --exclude .git --exclude .claude --exclude 'secrets/*.dec*' --exclude graphify-out --exclude CLAUDE.md --exclude __pycache__ --exclude /private/ ./ $(VPS_USER)@$(VPS_HOST):$(REMOTE_DIR)/
	bash scripts/deploy-guard.sh end $(VPS_USER)@$(VPS_HOST)

# The always-on services, and the image of the morning job, so that a failed build shows now and not at 06:00
up:
	bash scripts/deploy-guard.sh start $(VPS_USER)@$(VPS_HOST)
	$(SSH) 'cd $(REMOTE_DIR) && sudo bash scripts/data-dirs.sh && $(COMPOSE) up -d --build && $(COMPOSE) --profile jobs build ingest-gmail'
	bash scripts/deploy-guard.sh end $(VPS_USER)@$(VPS_HOST)

# The front zone, which make deploy and make up never start or stop (docs/RUNBOOK.md, Front zone)
front:
	$(SSH) 'cd $(REMOTE_DIR) && $(COMPOSE) --profile front up -d --build --wait change-proposals front'

# The env files of vault and front from the secret files; the comms zone is not started, so its file is not made
render-envs:
	$(SSH) 'cd $(REMOTE_DIR) && sudo bash scripts/render-vault-env.sh && sudo bash scripts/render-front-env.sh'

# Is every secret there with its mode, and how to make one that is not (names only)
secrets-check:
	$(SSH) 'cd $(REMOTE_DIR) && sudo bash scripts/secrets-check.sh'

# Only the host timers; they start the morning jobs and the backups, so on a new host they come last
timers:
	$(SSH) 'cd $(REMOTE_DIR) && sudo bash scripts/install-timers.sh'

# The applier (services/applier/install.sh): its host check needs front, squid-front and Telegram connected
applier:
	$(SSH) 'cd $(REMOTE_DIR) && sudo bash services/applier/install.sh'

# The Python of make test and make mirror, with the exact packages of vault-tools
venv:
	bash scripts/make-venv.sh $(VENV)

# The front changes the applier made on the VPS on the owner's tap (services/applier), as one commit each in this checkout
applied-pull:
	python3 -I scripts/applied-pull.py $(VPS_USER)@$(VPS_HOST)

status:
	$(SSH) 'cd $(REMOTE_DIR) && $(COMPOSE) ps && df -h / && free -m && sudo docker system df'

logs:
	$(SSH) 'cd $(REMOTE_DIR) && $(COMPOSE) logs --tail=100 $(SVC)'

# make secret-set NAME=telegram_control_token  (value is prompted on the VPS, never echoed)
secret-set:
	@test -n "$(NAME)" || (echo "NAME required"; exit 1)
	scp -q scripts/secret-set.sh $(VPS_USER)@$(VPS_HOST):/tmp/pa-secret-set.sh
	$(SSH) -t 'sudo bash /tmp/pa-secret-set.sh $(NAME); rm -f /tmp/pa-secret-set.sh'

# make secret-gen NAME=vault_tools_mcp_token TYPE=token   (random value created on the VPS; vault_tools_key also takes FIRST_INSTALL=1)
secret-gen:
	@test -n "$(NAME)" -a -n "$(TYPE)" || (echo "NAME and TYPE required"; exit 1)
	scp -q scripts/secret-gen.sh $(VPS_USER)@$(VPS_HOST):/tmp/pa-secret-gen.sh
	$(SSH) 'sudo bash /tmp/pa-secret-gen.sh $(NAME) $(TYPE) $(if $(FIRST_INSTALL),--first-install); rm -f /tmp/pa-secret-gen.sh'

# make pdf-passwords   (interactive, hidden input, runs on the VPS)
pdf-passwords:
	scp -q scripts/pdf-passwords-set.py $(VPS_USER)@$(VPS_HOST):/tmp/pa-pdf-passwords.py
	$(SSH) -t 'sudo python3 /tmp/pa-pdf-passwords.py; rm -f /tmp/pa-pdf-passwords.py'

prune-dry:
	$(SSH) 'cd $(REMOTE_DIR) && sudo DRY_RUN=1 bash scripts/prune.sh'

prune:
	$(SSH) 'cd $(REMOTE_DIR) && sudo bash scripts/prune.sh'

backup:
	$(SSH) 'sudo systemctl start pa-backup.service && sudo journalctl -u pa-backup -n 20 --no-pager'

# private/ onto a new, empty VPS (docs/REBUILD.md). CONFIRM repeats the address; it refuses a host with this project on it.
restore:
	bash scripts/restore.sh mirror $(VPS_USER)@$(VPS_HOST) "$(CONFIRM)"

# The snapshots in R2, and whether the newest is newer than private/. Opens them with private/'s restic.env, kept on no host.
snapshots:
	bash scripts/restore.sh snapshots $(VPS_USER)@$(VPS_HOST)

# As make restore, from a snapshot, when R2 is newer than private/: SNAPSHOT=<id from make snapshots> CONFIRM=<address>
restore-restic:
	bash scripts/restore.sh restic $(VPS_USER)@$(VPS_HOST) "$(CONFIRM)" "$(SNAPSHOT)"

# The full plaintext copy of the VPS data and secrets into private/ of the main checkout: read-only on the VPS, never in
# git, never synced, counts and statuses only. ALLOW_SHRINK=1 accepts a ledger with fewer rows than the last copy.
mirror:
	MIRROR_PY=$${MIRROR_PY:-$(PY)} bash scripts/mirror.sh $(VPS_USER)@$(VPS_HOST)

# The hand-made host config and the exact Python packages, from the live VPS into this checkout to review and commit (read-only there)
capture:
	bash scripts/capture-recipe.sh $(VPS_USER)@$(VPS_HOST)

# make venv first: without PyYAML, mcp and cryptography some suites skip their tests or fail on the import
test:
	$(PY) -I -m unittest discover -s tests -v
	cd services/hermes/vault && $(PY) -I -m unittest discover -s tests -v   # the cardguard plugin
	cd services/hermes/front && $(PY) -I -m unittest discover -s tests -v   # the cardblock plugin
	cd services/control && $(PY) -I -m unittest discover -s tests -v
	cd services/applier && $(PY) -I -m unittest discover -s tests -v   # a fake docker; its zone-rule test needs PyYAML
	cd services/change-proposals && $(PY) -I -m unittest discover -s tests -v   # needs mcp, as the vault-tools server tests
	cd services/comms-brokers && $(PY) -I -m unittest discover -s tests -v   # M4 brokers; the MCP server tests need mcp too
	cd services/ingest-gmail && $(PY) -I -m unittest discover -s tests -v
	cd services/vault-tools && $(PY) -I -m unittest discover -s tests -v   # the server tests need mcp

# Read-only snapshot of the live bot into docs/runtime/ (names, counts, dates; no secrets, balances or message text)
runtime-map:
	python3 -I ops/runtime-map/collect.py --host $(VPS_USER)@$(VPS_HOST)

# Refresh the code side of graphify-out/ (AST only, no LLM cost); after doc edits run /graphify . --update in Claude Code
graph:
	GRAPHIFY_NO_AUTO_REFRESH=1 graphify update .
