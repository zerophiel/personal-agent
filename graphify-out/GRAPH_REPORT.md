# Graph Report - m1-skeleton  (2026-11-01)

## Corpus Check
- 136 files · ~149,291 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 32 file(s) not represented in the graph (top: .service 9, .timer 9, (none) 8)

## Summary
- 3546 nodes · 8330 edges · 198 communities (161 shown, 37 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 830 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6ea28215`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Card Installments
- Hermes and Host Runtime Probes
- suggest.py
- Cardguard Plugin and Control Bot
- tools.py
- Runtime Ledger Accounts
- Telegram HTML Safety
- connect
- os
- Live MCP Tool Catalog
- Bot Tool Usage (state.db)
- Ledger Audit (periksa_data)
- Hermes Runtime Config and Logs
- spending_pace
- Bot Activity and Models
- Cardguard Plugin Tests
- Card Payments and Paid-by-Hand
- Living Money and Daily Account
- Payday Plan Engine (Reserve)
- record_expense
- server.py
- Payees, Vault Secrets, Emergency Fund
- Runtime Map Collector
- Ledger Schema (v13 Tables)
- Debt Roadmap and Dates
- Pot Schedule Consumers
- Host Data Dirs and Backups
- Images, Compose and Secret Files
- format_idr
- Zones, Containers and Squid
- vault-tools Runtime Probe
- Read-Only Mounts and Vault Network
- Card Payment Advice
- Spending Analysis (Budget Baseline)
- create_app
- Telegram Gateway and Delivery
- Calibration Decisions and Overrides
- spend
- Notion Sync
- wib_today
- Gmail Ingest Run Tests
- Host Scripts (Holidays, PDF Passwords)
- Zone Architecture (M1-M4)
- Statement PDF Intake
- Bot calibration runbook (manual, on the owner's request)
- upsert_debt
- control.py
- Pot in the Payday Plan
- Money, Reconcile and Vault Crypto
- Hermes Agent Settings (Live)
- Gmail API Client
- Owner Names and Uploads
- Stack Env and Host Checks
- Email Sender Authentication
- Merged Records Tests
- upsert
- Runbook and Deploy (M1)
- Runtime Map Overview
- Statement Line Counting
- Compose Secrets
- Vault Zone and MCP Visibility
- Statement Recording and Pending Queue
- PDF Intake Safety Tests
- Hermes config.yaml (Repo)
- Gmail Ingest Pipeline
- Number Masking
- re
- Hermes Assumption Spikes
- Payday Plan Spec and Owner Rules
- Card Features and Deploy Plan
- Payday Plan and Pot Tools (Usage)
- Compose Logging Options
- Compose Service: ingest-gmail
- Compose Service: vault-tools
- Hermes Agent (nousresearch/hermes-agent, pinned v0.22.5)
- Auto-Debits and Due Rules
- set_category_rule
- Compose Service: control
- Compose Service: vault (Hermes)
- prune.sh
- Record Corrections and Change Log
- Compaction and Open Questions
- front
- Merge
- Graph-First Hook Tests
- Compose Service: squid-comms
- Compose Service: squid-ctl
- Compose Service: squid-front
- Compose Service: squid-vault
- Gmail OAuth and Sender Allowlist
- Debts, Balances and Proposals (State)
- Uploads and Statement Ingest (Usage)
- Graph-First Prompt Hook
- Upload Sync Tests
- Expense and Mutation Tools (Usage)
- Hermes Skills and Pending Proposals
- Corrected Source Merges
- MCP Server Security Tests
- Compose Networks
- Compose Squid Template
- living_reserve (protected monthly cash living money)
- Host Runtime and Firewall
- Proposals
- Hermes Auxiliary Models
- Hermes MCP Server Config
- change-proposals
- Sender Config Loading
- record_mutations
- Hermes Credentials Boundary
- Host Timers and Restic (State)
- Runtime Map Scrub Tests
- Gmail Client Tests
- Server Flow Tests
- simulasi_skenario (code-computed what-if simulator)
- Card Payment Targets
- Ingest Events and Cron
- Re-Read Guard
- Compose Root and Hardening
- test_zones.py
- Pot Schedule Engine
- Number Guard Tests
- Sender Search Fallback
- front/config.yaml
- Gmail Token Check Tests
- Hermes Telegram Gateway Config
- Proposal and Scenario Tools
- date
- Hermes Agent Block
- Hermes Memory Settings
- Cardguard Plugin Manifest
- System-Managed Balance Tool Test
- Hermes Compression Settings
- Ledger (ledger.db on the VPS)
- auxiliary
- Vault Env Renderer
- change_proposals
- roadmap.py
- PayRules
- Asisten umum pemilik (front)
- .world
- extra
- key_lines
- memory
- .test_a_new_living_reserve_keeps_the_owners_leftover
- recurring
- socket_inodes_as
- _Auth
- agent
- make_pdf
- _Auth
- Collect
- 2026-10-31-pace-fix/deploy.sh
- 2026-11-01-pocket-balance/deploy.sh
- 2026-11-01-recal/deploy.sh
- model
- tools
- tools
- Rincian
- data-dirs.sh
- render-front-env.sh
- accounts (ledger table, 8 rows)
- logs/errors.log
- invariants.py
- logs/agent.log
- Hermes Agent v0.22.5 (vault bot engine, Telegram bot @danoevault_agent, container personal-agent-vault-1)
- last_working_day
- category_keywords (ledger table, 9 rows)
- build
- format_idr
- Hermes Telegram adapter (polling mode)
- Telegram platform adapter (plugins/platforms/telegram/adapter.py; state connected)
- ingest_file_parts
- payday.py
- test_graph_first.py
- /rincian handled in pre_gateway_dispatch with skip plus direct Bot API send
- /ingest (read-only; filled by ingest-gmail and pa-uploads)
- payee_secrets (ledger table, 19 rows; nonce, ciphertext, match_hash)
- Invariants enforced in infrastructure, not prompts
- personal-agent-control-1 (control service; uid 10001, 128 MB / 0.25 CPU)
- hermes-vault data dir (mode 0700)
- _extract_clean
- vision_analyze engine tool
- config/stack.env (non-secret stack settings)
- Bound fund: the friend's debt pot (deadline 31 Jan 2028, Jago pot account, sinking:<fund alias>, upsert_sinking_fund)
- The bot's three /usulan built (schema v12)
- ingest-gmail job (services/ingest-gmail/Dockerfile, own ingest user)
- bp_of
- Properties
- preflight.sh
- backup.sh
- disk-check.sh
- model
- install-timers.sh
- secret-gen.sh
- secret-set.sh
- sync-uploads.sh

## God Nodes (most connected - your core abstractions)
1. `create_app()` - 95 edges
2. `generate_payday_plan()` - 90 edges
3. `format_idr()` - 87 edges
4. `connect()` - 84 edges
5. `Bot activity snapshot` - 71 edges
6. `MCP server vault_tools (56 tools at http://vault-tools:8000/mcp, named mcp__vault_tools__<name> for the model)` - 63 edges
7. `PayeeVault` - 52 edges
8. `simulate()` - 47 edges
9. `set_threshold()` - 42 edges
10. `edit_expense()` - 41 edges

## Surprising Connections (you probably didn't know these)
- `Hitting a limit: catat_usulan, then sudah kucatat di /usulan` --semantically_similar_to--> `/usulan (posts the waiting proposals again with their buttons)`  [AMBIGUOUS] [semantically similar]
  services/hermes/vault/SOUL.md → docs/RUNBOOK.md
- `/rincian handled in pre_gateway_dispatch with skip plus direct Bot API send` --semantically_similar_to--> `/rincian (destination numbers grouped per destination; the only place full numbers appear)`  [INFERRED] [semantically similar]
  docs/ARCHITECTURE.md → services/hermes/vault/SOUL.md
- `/mcp surface (model-facing; aliases and amounts only, no tool stores or reveals a full number)` --semantically_similar_to--> `Security and data rules (no re-reading recorded documents, max 2 reads per answer, alias plus last 4 digits only, no CVV or expiry, no URLs)`  [INFERRED] [semantically similar]
  docs/SECURITY.md → services/hermes/vault/SOUL.md
- `A rejected submit is fixed per its reason, never gamed; new services, host scripts, plugins and secret values are the owner's own work` --semantically_similar_to--> `Never in a proposal: host scripts, compose, plugins, control itself, secrets (new service = escalation; secret via make secret-set); at most five wait`  [INFERRED] [semantically similar]
  services/hermes/front/SOUL.md → docs/SECURITY.md
- `Numbers only from tools, this turn (no own arithmetic or rounding; old summaries are hints only)` --semantically_similar_to--> `Number guard (pre_llm_call, post_tool_call, transform_llm_output hooks; Cek angka warning)`  [INFERRED] [semantically similar]
  services/hermes/vault/SOUL.md → docs/PROGRESS.md

## Import Cycles
- 2-file cycle: `services/vault-tools/vault_tools/roadmap.py -> services/vault-tools/vault_tools/simulate.py -> services/vault-tools/vault_tools/roadmap.py`
- 2-file cycle: `services/vault-tools/vault_tools/simulate.py -> services/vault-tools/vault_tools/tools.py -> services/vault-tools/vault_tools/simulate.py`
- 3-file cycle: `services/vault-tools/vault_tools/roadmap.py -> services/vault-tools/vault_tools/tools.py -> services/vault-tools/vault_tools/simulate.py -> services/vault-tools/vault_tools/roadmap.py`

## Hyperedges (group relationships)
- **Vault zone on internal net-vault: Hermes gateway, vault-tools MCP server and squid-vault** — docs_runtime_containers_personal_agent_vault_1, docs_runtime_containers_personal_agent_vault_tools_1, docs_runtime_containers_personal_agent_squid_vault_1, docs_runtime_containers_personal_agent_net_vault, docs_runtime_vault_tools_mcp_server [EXTRACTED 1.00]
- **Plan and pot computed from the pre-salary state (usulan #9 and #10)** — docs_runtime_state_usulan_9, docs_runtime_state_usulan_10, docs_runtime_state_pre_salary_baseline, docs_runtime_state_pot_simulation, docs_runtime_state_tunda_pot_bulan, docs_runtime_state_rincian_rencana_commands, docs_runtime_state_payday_plan [EXTRACTED 1.00]
- **restic backup lifecycle through backup.sh (daily backup, monthly integrity check, weekly retention)** — docs_runtime_timers_pa_backup, docs_runtime_timers_pa_check, docs_runtime_timers_pa_forget, docs_runtime_timers_backup_sh, docs_runtime_timers_restic [EXTRACTED 1.00]
- **M3 change approval chain (front submit, change-proposals, proposals-inbox, control decides on the owner's tap, applier later)** — services_hermes_front_soul_submit_tool, docs_security_change_proposals, docs_architecture_proposals_inbox, docs_security_only_control_decides, docs_architecture_control_state, docs_security_applier_contract [EXTRACTED 1.00]
- **Payday cycle on the 1st (status_gajian, sisa_uang_harian, generate_payday_plan, periksa_data, recording tools, saldo_rekening)** — services_hermes_vault_soul_payday_list_flow, services_hermes_vault_soul_status_gajian, services_hermes_vault_soul_sisa_uang_harian, services_hermes_vault_soul_generate_payday_plan, services_hermes_vault_soul_periksa_data, services_hermes_vault_soul_payday_recording_tools, services_hermes_vault_soul_saldo_rekening [EXTRACTED 1.00]
- **Per-zone squid proxies are the only members of the egress network** — docs_architecture_squid_vault, docs_architecture_squid_front, docs_architecture_squid_comms, docs_architecture_squid_ctl, docs_architecture_egress_network [EXTRACTED 1.00]
- **Statement import tool flow** — docs_runtime_bot_activity_list_uploads, docs_runtime_bot_activity_pending_statements, docs_runtime_bot_activity_ingest_statement, docs_runtime_bot_activity_skip_statement_file, docs_runtime_bot_activity_record_statement, docs_runtime_bot_activity_list_statements, docs_runtime_bot_activity_record_mutations, docs_runtime_bot_activity_record_card_installments [INFERRED 0.75]
- **Morning statement ingest (06:00 WIB) followed by the Notion snapshot (06:30 WIB) from vault-tools through squid-vault** — docs_runtime_timers_pa_ingest, docs_runtime_timers_ingest_gmail, docs_runtime_timers_pa_notion, docs_runtime_timers_vault_tools_notion_sync, docs_runtime_timers_personal_agent_vault_tools_1, docs_runtime_proxies_api_notion_com, docs_runtime_proxies_squid_vault [INFERRED 0.75]
- **Owner-in-the-loop operations (approval before change)** — docs_runbook_first_time_vps_setup, docs_runbook_make_deploy, docs_calibration_manual_calibration, docs_architecture_control_zone, docs_calibration_data_review, docs_calibration_owner_report [INFERRED 0.75]
- **Context compression machinery** — docs_runtime_bot_activity_context_compression, docs_runtime_bot_activity_preflight_compression, docs_runtime_bot_activity_pre_api_compression, docs_runtime_bot_activity_compression_blocked, docs_runtime_bot_activity_session_compressed_warning, docs_runtime_bot_activity_auxiliary_compression_model, docs_runtime_bot_activity_sessions_compression_columns, docs_runtime_bot_activity_busy_input_mode, docs_runtime_bot_activity_compression_reply_anchor [INFERRED 0.85]
- **Gateway SIGTERM shutdown and revive cycle** — docs_runtime_bot_activity_gateway_restart_lifecycle, docs_runtime_bot_activity_s6_supervise, docs_runtime_bot_activity_shutdown_phases, docs_runtime_bot_activity_shutdown_notification, docs_runtime_bot_activity_gateway_state_persist, docs_runtime_bot_activity_container_boot_log, docs_runtime_bot_activity_gateway_shutdown_diag_log, docs_runtime_bot_activity_unclean_previous_life [INFERRED 0.85]
- **Numbers computed by code, never by the model** — docs_runtime_hermes_periksa_data, docs_runtime_hermes_generate_payday_plan, docs_runtime_hermes_simulasi_skenario, docs_runtime_hermes_belanja_kartu, docs_runtime_hermes_health_check, docs_runtime_hermes_cashflow_summary [INFERRED 0.85]
- **Full card and account numbers kept out of the bot (tokens, alias plus last 4 digits)** — docs_runtime_hermes_cardguard_plugin, docs_runtime_hermes_upsert_card, docs_runtime_hermes_upsert_account, docs_runtime_hermes_list_payees [INFERRED 0.85]
- **Statement intake: Telegram uploads and the ingest-gmail queue into recorded statements and transactions** — docs_runtime_hermes_list_uploads, docs_runtime_hermes_uploads_cache, docs_runtime_hermes_ingest_statement, docs_runtime_hermes_record_statement, docs_runtime_hermes_record_mutations, docs_runtime_hermes_pending_statements, docs_runtime_hermes_skip_statement_file, docs_runtime_hermes_ingest_events, docs_runtime_hermes_ingest_gmail_job [INFERRED 0.85]
- **Secret provisioning path (entered or generated on the VPS, kept in the secrets dir, mounted as compose secrets)** — docs_runtime_infra_files_make_secret_set, docs_runtime_infra_files_make_secret_gen, docs_runtime_infra_files_make_pdf_passwords, docs_runtime_infra_files_plaintext_secrets_stay_on_vps, docs_runtime_host_opt_personal_agent_secrets, docs_runtime_host_compose_secrets_mount [INFERRED 0.85]
- **restic backup lifecycle (backup, integrity check, retention of the data dir)** — docs_runtime_infra_files_host_pa_backup, docs_runtime_infra_files_host_pa_check, docs_runtime_infra_files_host_pa_forget, docs_runtime_infra_files_scripts_backup_sh, docs_runtime_infra_files_make_backup, docs_runtime_host_opt_personal_agent_data, docs_runtime_host_secret_restic_env [INFERRED 0.85]
- **Telegram upload relay flow (Hermes document cache to the ingest folder, 90-day retention)** — docs_runtime_infra_files_hermes_vault_document_cache, docs_runtime_infra_files_host_pa_uploads, docs_runtime_infra_files_scripts_sync_uploads_sh, docs_runtime_infra_files_upload_retention_90_days, docs_runtime_host_hermes_vault_dir, docs_runtime_host_ingest_dir [INFERRED 0.85]
- **Live-vs-repo drift checks made by the runtime map collector (deployed files, systemd units, squid configs)** — docs_runtime_readme_collect_py, docs_runtime_readme_deploy_drift, docs_runtime_timers_live_vs_repo_unit_drift, docs_runtime_proxies_live_configs_match_repo [INFERRED 0.85]
- **Daily Gmail statement ingest path (pa-ingest, ingest-gmail run, squid-vault, Google APIs)** — docs_runtime_state_pa_ingest, docs_runtime_state_ingest_gmail_container, docs_runtime_state_squid_vault, docs_runtime_state_gmail_googleapis_com, docs_runtime_state_oauth2_googleapis_com, docs_runtime_state_pa_gmail_token, docs_runtime_state_doc_files_table, docs_runtime_state_processed_messages_table [INFERRED 0.85]
- **Autodebit debts paid manually before the debit date (usulan #5, #7, #8)** — docs_runtime_state_usulan_5, docs_runtime_state_usulan_7, docs_runtime_state_usulan_8, docs_runtime_state_autodebit, docs_runtime_state_spaylater_debt, docs_runtime_state_car_instalment_debt, docs_runtime_state_debt_payments_table, docs_runtime_state_held_balance [INFERRED 0.85]
- **Encrypted payee secrets: payee_secrets nonce, ciphertext and match_hash with vault_tools_key and cryptography** — docs_runtime_vault_tools_table_payee_secrets, docs_runtime_containers_secret_vault_tools_key, docs_runtime_vault_tools_cryptography_package [INFERRED 0.85]
- **Statement ingest: ingest-gmail and pa-uploads fill /ingest, PDFs become statements and mutation files** — docs_runtime_vault_tools_ingest_gmail, docs_runtime_vault_tools_pa_uploads, docs_runtime_vault_tools_ingest, docs_runtime_vault_tools_pdf_parsing_packages, docs_runtime_vault_tools_table_doc_files, docs_runtime_vault_tools_table_statements, docs_runtime_vault_tools_table_mutation_files [INFERRED 0.85]
- **Layers that keep the bot's numbers exact (prompt rule, number guard, invariants, property tests, duplicate rule)** — services_hermes_vault_soul_numbers_only_from_tools, docs_progress_number_guard, docs_progress_invariants_self_checks, docs_progress_property_tests, docs_progress_duplicate_expense_rule [INFERRED 0.85]
- **Own-record merge lifecycle (merge, coverage gate, correct, unmerge, cash exclusion, id reuse, audit log)** — docs_progress_merge_receipts_same_bank, docs_progress_record_merge_coverage_gate, docs_progress_daftar_ubah_hapus_belanja, docs_progress_lepas_unmerge, docs_progress_cash_never_merges_tunai, docs_progress_id_reuse_fix_45dfc1e, docs_progress_dedupe_key, docs_progress_change_log [INFERRED 0.95]

## Communities (198 total, 37 thin omitted)

### Community 0 - "Card Installments"
Cohesion: 0.06
Nodes (29): Accuracy, add_statement(), Amounts, card_world(), Classify, Parsing, PerCard, Recovery (+21 more)

### Community 1 - "Hermes and Host Runtime Probes"
Cohesion: 0.06
Nodes (58): activity(), config(), day(), db_profile(), defaults_module(), engine(), fkind(), flatten() (+50 more)

### Community 2 - "suggest.py"
Cohesion: 0.05
Nodes (33): acct_db(), Completeness, r(), Suggestions, acct_db(), Mutations, rows(), cashflow() (+25 more)

### Community 3 - "Cardguard Plugin and Control Bot"
Cohesion: 0.11
Nodes (29): amounts(), _bot(), check_answer(), _chunks(), _delete_async(), _digits_of(), ensure_menu(), find_numbers() (+21 more)

### Community 4 - "tools.py"
Cohesion: 0.09
Nodes (22): ringkasan_data(), autodebit_check(), card_advice(), card_bills(), card_rate(), collect_obligations(), data_overview(), _day_in_month() (+14 more)

### Community 5 - "Runtime Ledger Accounts"
Cohesion: 0.15
Nodes (23): wajib:kartu category (6 rules), /data/cuti_bersama.json (cuti bersama: 21 entries for 2026, 19 for 2027), /data (vault-tools data directory), holidays package (0.107), ledger.db.bak-pre-* backups (43 copies dated 2026-10-27 to 2026-11-01), SQLite ledger /data/ledger.db (schema user_version 13, WAL journal), services/vault-tools/vault_tools/ledger.py (DDL + _migrate), ledger-schema.sql (ledger DDL) (+15 more)

### Community 6 - "Telegram HTML Safety"
Cohesion: 0.25
Nodes (21): UsulanReport, _anggaran(), b(), _banks(), _belanja(), bln(), build(), _cicilan() (+13 more)

### Community 7 - "connect"
Cohesion: 0.07
Nodes (9): Migration, Migration, SubscriptionLog, ThroughTheTools, Ledger, Migration, _backfill_v13(), connect() (+1 more)

### Community 8 - "os"
Cohesion: 0.14
Nodes (3): _rata_deposit(), bp_of_idr(), _round_up()

### Community 9 - "Live MCP Tool Catalog"
Cohesion: 0.08
Nodes (51): add_owner_name (add the owner's name exactly as printed in account transactions), apply_suggestions (apply category suggestions for the named descriptions; empty applies all), atur_jadwal_pot (set how a pot, an earmarked fund with a deadline, is filled), belanja_kartu (card spending breakdown per cycle from statement lines already read by code; never read the PDF for this), budget_status (budget use per category for a month, default the current one), card_installments_status (running card installments: x of y, months left and total remaining), cashflow_summary (monthly cash flow: income, spending, difference, savings ratio, per category; computed by code), cicilan_dibayar (record one debt installment already paid, e.g. a car loan or SPayLater) (+43 more)

### Community 10 - "Bot Tool Usage (state.db)"
Cohesion: 0.06
Nodes (40): Bot activity snapshot, mcp__vault_tools__add_owner_name, mcp__vault_tools__apply_suggestions, mcp__vault_tools__atur_jadwal_pot, mcp__vault_tools__belanja_kartu, mcp__vault_tools__budget_status, mcp__vault_tools__card_installments_status, mcp__vault_tools__daftar_belanja (+32 more)

### Community 11 - "Ledger Audit (periksa_data)"
Cohesion: 0.21
Nodes (10): Audit, found(), line(), stmt(), world(), format_audit(), _keyword(), _latest_cycle() (+2 more)

### Community 12 - "Hermes Runtime Config and Logs"
Cohesion: 0.10
Nodes (24): runtime/active_sessions.json (active-session entries), api_server platform (OpenAI-compatible, 127.0.0.1:8642, reachable only inside the container; connected, no requests), Bundled Hermes skills (12 categories; the skills toolset is disabled, so the model cannot load them), gateway_state.json (gateway platforms telegram and api_server, listener and gateway state), /opt/data (HERMES_HOME, read-write mount), Logger gateway.platforms.api_server (101 INFO), projects.db (projects store; every table empty), projects.db discovered_repos table (0 rows) (+16 more)

### Community 13 - "spending_pace"
Cohesion: 0.15
Nodes (8): LivingMoneyPace, _merged_target(), record_expense(), spending_pace(), _living_balance(), record_account_balance(), after(), set_leftover_living_cash()

### Community 14 - "Bot Activity and Models"
Cohesion: 0.10
Nodes (24): Hermes API server (127.0.0.1:8642, model hermes-agent), logs/container-boot.log, Hermes cron scheduler, Gateway drain timeout and runtime_draining pauses, /opt/data/.env (loaded by run_agent), Gateway control socket (/opt/data/gateway.sock), logs/gateway-exit-diag.log, Gateway housekeeping (memory trim, agent cache idle sweep) (+16 more)

### Community 15 - "Cardguard Plugin Tests"
Cohesion: 0.09
Nodes (4): CardGuard, text(), ev(), Fake

### Community 16 - "Card Payments and Paid-by-Hand"
Cohesion: 0.06
Nodes (20): CardPayment, Instalments, Migration, pay_as_on_30_oct(), plan_of(), PlanStaysAfterPaying, Progress, stmt() (+12 more)

### Community 17 - "Living Money and Daily Account"
Cohesion: 0.11
Nodes (16): amounts(), bill(), Emergency, LeftoverLivingCash, ReserveAndPot, Fund, full_world(), dana_darurat() (+8 more)

### Community 18 - "Payday Plan Engine (Reserve)"
Cohesion: 0.26
Nodes (6): amounts_of(), Engine, dummy(), WorkedExample, build_plan(), Obligation

### Community 19 - "record_expense"
Cohesion: 0.16
Nodes (8): OnlyTheOwnersRecords, delete_expense(), list_expenses(), _merged_note(), _own_row(), _paid_from(), _shown(), _with_aliases()

### Community 20 - "server.py"
Cohesion: 0.09
Nodes (6): create_app(), main(), ProposedFile, Installment, locked(), Txn

### Community 21 - "Payees, Vault Secrets, Emergency Fund"
Cohesion: 0.09
Nodes (8): DailyAccount, LinkPayees, Vault, _norm(), PayeeVault, _subkey(), link_card_payees(), link_card_payees()

### Community 22 - "Runtime Map Collector"
Cohesion: 0.16
Nodes (29): amounts(), cell(), deep_scrub(), engine_refs(), fence(), header(), listener_note(), local_tree() (+21 more)

### Community 23 - "Ledger Schema (v13 Tables)"
Cohesion: 0.09
Nodes (33): accounts, balance_reports, card_installment_scans, card_installments, card_lines, card_payments, cards, category_keywords (+25 more)

### Community 24 - "Debt Roadmap and Dates"
Cohesion: 0.09
Nodes (13): CardPath, CardPayments, LatestStatement, Recurring, Roadmap, statement(), world(), format_roadmap() (+5 more)

### Community 25 - "Pot Schedule Consumers"
Cohesion: 0.10
Nodes (13): Consumers, CardsFirstPot, EmergencyFund, Simulate, simulasi_skenario(), _bln(), format_result(), verdict() (+5 more)

### Community 26 - "Host Data Dirs and Backups"
Cohesion: 0.09
Nodes (33): docker daemon.json (json-file log driver, max-size 10m, max-file 3), Docker disk use (7 images, 7 containers, 8 local volumes, 121 build cache entries), Docker 29.9.2 and Compose 5.6.1 on the VPS, /etc/cron.d entries (e2scrub_all, sgagenttask, sysstat, yunjing), restic.env secret (mode 0600), Tencent Cloud agent cron (root crontab, qcloud stargate every 5 min, not part of the stack), Tencent Cloud VPS (Ubuntu 24.04.4 LTS, 2 CPUs, Asia/Jakarta), graphify-out/ shared project map (graph.json, GRAPH_REPORT.md, manifest.json, cost.json, labels) (+25 more)

### Community 27 - "Images, Compose and Secret Files"
Cohesion: 0.18
Nodes (15): personal-agent-vault-tools image (latest, created 2026-11-01), notion_token secret, vault_tools_internal_token secret, vault_tools_mcp_token secret, vault-tools data dir (mode 0700), api.notion.com (vault allowlist, for vault-tools), pa-holidays.service + timer (cuti bersama / holiday refresh for vault-tools, 1st at 06:30 WIB), ledger.db (LEDGER_DB=/data/ledger.db in vault-tools) (+7 more)

### Community 28 - "format_idr"
Cohesion: 0.14
Nodes (3): merge_receipts(), _refused(), _window()

### Community 29 - "Zones, Containers and Squid"
Cohesion: 0.19
Nodes (20): Anonymous squid log and spool volumes (8, from image VOLUME lines), cap_drop ALL (control, the four squids, vault-tools; vault has none), Compose project personal-agent (compose/docker-compose.yml), ubuntu/squid:6.6-24.04_edge image (all four squid containers), json-file logs, max-size 10m, max-file 3 (every container), privileged False and security_opt no-new-privileges:true (every container), No published ports (every container), personal-agent_egress network (bridge, not internal; the four squids) (+12 more)

### Community 30 - "vault-tools Runtime Probe"
Cohesion: 0.07
Nodes (32): Applier (applies approved changes; not built yet), Approvals flow (M3): front submit -> proposals-inbox -> control re-validates and posts -> owner's tap recorded, change-proposals (front zone, M3, submit tool), Control commands /status (counts), /usulan (re-post waiting proposals), /ping, control-state folder (control only; decided/, approved/ read later by the applier), Control zone and control service (approvals, no LLM, net-ctl), scripts/data-dirs.sh (creates the M3 folders), proposals-inbox folder (change-proposals writes, control reads and empties it) (+24 more)

### Community 31 - "Read-Only Mounts and Vault Network"
Cohesion: 0.10
Nodes (29): cardguard plugin (services/hermes/vault/plugins/cardguard, read-only at /opt/data/plugins/cardguard), Containers runtime map (compose project personal-agent), ANTHROPIC_API_KEY (vault env name), Hermes path env (HERMES_HOME and HERMES_WRITE_SAFE_ROOT /opt/data, HERMES_PYTHON, HERMES_RUNTIME_DIR, HERMES_TUI_DIR, HERMES_WEB_DIST, PLAYWRIGHT_BROWSERS_PATH, XDG_RUNTIME_DIR), HERMES_SKIP_CONFIG_MIGRATION=1 (vault env), LEDGER_DB=/data/ledger.db (vault-tools env), TZ (vault Asia/Jakarta; squids UTC), vault NO_PROXY: localhost, 127.0.0.1, vault-tools (+21 more)

### Community 32 - "Card Payment Advice"
Cohesion: 0.15
Nodes (8): Advice, amounts(), DueBeforePayday, LivingReserveEstimate, statement(), world(), estimate_living_reserve(), generate_payday_plan()

### Community 33 - "Spending Analysis (Budget Baseline)"
Cohesion: 0.18
Nodes (10): Analysis, Monthly, tx(), world(), analyse(), card_charges(), format_analysis(), monthly() (+2 more)

### Community 34 - "create_app"
Cohesion: 0.05
Nodes (22): Rincian, Rincian, ThroughTheTools, ThroughTheTools, ThroughTheTools, Tools, has_forbidden_card_data(), create_app() (+14 more)

### Community 35 - "Telegram Gateway and Delivery"
Cohesion: 0.17
Nodes (21): api.anthropic.com (Anthropic API; 1014 requests via squid-vault), api.telegram.org (Telegram Bot API; 49442 requests via squid-vault, 8073 via squid-ctl), Containers now: 7 running, 0 restarts, no OOM, exit 0, control container (personal-agent-control-1; running since 2026-10-31, 0 log lines in 7 days), Denied: dns.google and cloudflare-dns.com (62 requests each), Denied: link-local cloud metadata endpoint (18 requests), Denied: hermes-agent.nousresearch.com and raw.githubusercontent.com (734 and 730 requests), Denied: openrouter.ai and portal.nousresearch.com (365 requests each) (+13 more)

### Community 36 - "Calibration Decisions and Overrides"
Cohesion: 0.13
Nodes (10): Decide, Override, Parse, candidate_days(), decide(), load_year(), merge_file(), parse_github() (+2 more)

### Community 37 - "spend"
Cohesion: 0.12
Nodes (7): _Banks, LateRecordsAndResentScreenshots, MergeRules, RecordExpense, spend(), list_uncategorized(), list_uncategorized()

### Community 38 - "Notion Sync"
Cohesion: 0.11
Nodes (19): FakeNotion, Sync, bullet(), heading(), main(), Notion, NotionError, para() (+11 more)

### Community 40 - "Gmail Ingest Run Tests"
Cohesion: 0.26
Nodes (4): run(), FakeClient, message(), Run

### Community 41 - "Host Scripts (Holidays, PDF Passwords)"
Cohesion: 0.07
Nodes (25): cuti(), data_files(), day(), fkind(), fname(), free(), ledger(), money_free() (+17 more)

### Community 42 - "Zone Architecture (M1-M4)"
Cohesion: 0.16
Nodes (14): brokers (comms zone, M4), card-bus MCP (replaces Kanban, M4), Comms zone (email and calendar, net-comms; comms, brokers, card-bus in M4), egress network (the four squid proxies only, to the internet), Front zone (general and web, net-front), notion-mcp (front zone, later), sandbox (front zone, later), squid-comms proxy (allowlist) (+6 more)

### Community 43 - "Statement PDF Intake"
Cohesion: 0.23
Nodes (3): make_pdf(), decrypt(), extract_text()

### Community 44 - "Bot calibration runbook (manual, on the owner's request)"
Cohesion: 0.17
Nodes (10): Vault bot token rotation (2026-10-28), cardguard plugin (Hermes), Hermes vault bot (Telegram), Milestones (M1 platform and M2 vault deployed; M3 front/control/applier, M4 comms, M2 gate checks remaining), Number guard (pre_llm_call, post_tool_call, transform_llm_output hooks; Cek angka warning), Report commands rendered by vault_tools/reports.py (Telegram HTML), vault-tools MCP server (MCP_TOOL_NAMES), submit tool (change-proposals): one proposal = one whole change with full file contents, all fields honest (+2 more)

### Community 45 - "upsert_debt"
Cohesion: 0.10
Nodes (13): BalanceCheck, car(), InThePlan, Rules, setup(), random_world(), RandomLedgers, rupiah() (+5 more)

### Community 46 - "control.py"
Cohesion: 0.06
Nodes (21): submit(), card(), Control, handle(), is_authorized(), main(), now(), path_allowed() (+13 more)

### Community 47 - "Pot in the Payday Plan"
Cohesion: 0.13
Nodes (13): PotBalance, fund(), InThePlan, Math, row(), setup(), Validation, set_category() (+5 more)

### Community 48 - "Money, Reconcile and Vault Crypto"
Cohesion: 0.22
Nodes (4): Reconcile, check_idr(), reconcile(), Reconciliation

### Community 49 - "Hermes Agent Settings (Live)"
Cohesion: 0.08
Nodes (28): agent.reasoning_effort high (not in DEFAULT_CONFIG; a per-model override would win), auxiliary.compression: claude-sonnet-5-5 via anthropic (default auto), auxiliary config section (139 keys; our compression, title_generation and vision models on anthropic), auxiliary.title_generation: claude-haiku-5-5 via anthropic (default auto), Proposed skill card-spend-breakdown-advisory (productivity, created 2026-10-28, pending approval), catat_usulan (record a proposal when the bot hits a limit: a missing tool, calculation or command, instead of a workaround), Hermes config backups (backups/config.yaml.good.*, five from 2026-10-28 to 2026-11-01), DEFAULT_CONFIG sections table (100 top-level sections with line, key count and the keys we set) (+20 more)

### Community 50 - "Gmail API Client"
Cohesion: 0.21
Nodes (3): GmailClient, GmailError, TokenError

### Community 51 - "Owner Names and Uploads"
Cohesion: 0.15
Nodes (7): Names, normalize_ref(), safe_name(), list_uploads(), PdfError, resolve_ref(), list_uploads()

### Community 52 - "Stack Env and Host Checks"
Cohesion: 0.22
Nodes (4): days_left(), main(), message(), notify()

### Community 53 - "Email Sender Authentication"
Cohesion: 0.17
Nodes (6): auth_ok(), _clauses(), from_address(), safe_label(), Auth, hdrs()

### Community 54 - "Merged Records Tests"
Cohesion: 0.20
Nodes (5): MergedRecords, log(), edit_expense(), _give(), _take_out()

### Community 55 - "upsert"
Cohesion: 0.18
Nodes (8): world(), OwnerRules, Subscriptions, subscriptions_status(), upsert_subscription(), active_total(), format_list(), upsert()

### Community 56 - "Runbook and Deploy (M1)"
Cohesion: 0.14
Nodes (20): Open: Telegram fallback IP discovery via DNS-over-HTTPS could bypass the proxy, Spike 5: Hermes reaches Telegram via the zone proxy from an internal network (pass), Change and verify (worktree tests, dry_run.py on a ledger copy), Runbook (M1), Blocked-domain egress test (example.com via squid-ctl from control must return 403), First-time VPS setup (each step needs owner approval), Gate checks for M1, make deploy, then make status (+12 more)

### Community 57 - "Runtime Map Overview"
Cohesion: 0.06
Nodes (64): api.anthropic.com, api.notion.com, api.telegram.org, Denied: AWS IMDSv2 credential probes to the instance-metadata address (/latest/api/token, iam/security-credentials), Denied: DNS-over-HTTPS fallbacks of the HTTP clients (dns.google, cloudflare-dns.com), Denied: Hermes model-catalog and provider refreshes (hermes-agent.nousresearch.com, raw.githubusercontent.com, openrouter.ai, portal.nousresearch.com), Docker DNS (name resolution used instead of DNS-over-HTTPS), Egress proxies (squid) runtime map (+56 more)

### Community 58 - "Statement Line Counting"
Cohesion: 0.22
Nodes (5): Counting, count_dated_lines(), count_signed_lines(), count_transactions(), _first_money_is_real()

### Community 59 - "Compose Secrets"
Cohesion: 0.11
Nodes (19): file, file, file, file, file, secrets, change_proposals_mcp_token, gmail_ingest_client (+11 more)

### Community 60 - "Vault Zone and MCP Visibility"
Cohesion: 0.14
Nodes (15): Spike 7: MCP over HTTP with a bearer token from env (pass), Data review (/periksa and recurring_charges.py), /periksa command and periksa_data tool, Statement reconciliation (every statement re-reads as cocok), Holidays input (owner-maintained holiday list), /mcp surface (model-facing; aliases and amounts only, no tool stores or reveals a full number), Payee encryption key vault_tools_key (make secret-gen on the VPS, never overwritten, backed up with restic), Surface tokens (random, at least 32 chars, must differ, constant-time compare; unknown paths 404) (+7 more)

### Community 61 - "Statement Recording and Pending Queue"
Cohesion: 0.17
Nodes (8): IngestEvents, PendingStatements, ingest_events(), pending_statements(), skip_statement_file(), pending_statements(), read_new_events(), skip_statement_file()

### Community 62 - "PDF Intake Safety Tests"
Cohesion: 0.26
Nodes (5): make_pdf(), McpIngest, PdfIntake, file_sha256(), ingest()

### Community 63 - "Hermes config.yaml (Repo)"
Cohesion: 0.13
Nodes (14): approvals, destructive_slash_confirm, compression, min_tail_user_messages, threshold_tokens, plugins, enabled, security (+6 more)

### Community 64 - "Gmail Ingest Pipeline"
Cohesion: 0.22
Nodes (8): Config, emit(), _headers(), _pdf_parts(), process_message(), _save_pdf(), _state(), sweep_retention()

### Community 65 - "Number Masking"
Cohesion: 0.22
Nodes (6): Masking, Masking, luhn_valid(), _mask_digits(), mask_sensitive(), repl()

### Community 66 - "re"
Cohesion: 0.15
Nodes (9): Budgets, cash_month(), Health, Pace, planned(), _reason(), set_budget(), clean_text() (+1 more)

### Community 67 - "Hermes Assumption Spikes"
Cohesion: 0.33
Nodes (10): Assumption spikes (Hermes v0.22.5), Card token placeholder [[CARD:****last4]], cardguard plugin (card-number rewrite in pre_gateway_dispatch), Open: hooks not bounded by plugins.hook_callback_timeout, Open: Telegram-side copy of the raw message (deleteMessage live test pending), pre_gateway_dispatch hook (Hermes), Spike 10: deleteMessage on the owner's incoming message (pass), Spike 2: raw inbound Telegram text not persisted before pre_gateway_dispatch (pass) (+2 more)

### Community 68 - "Payday Plan Spec and Owner Rules"
Cohesion: 0.36
Nodes (9): Ledger (SQLite ledger.db in the vault-tools container), living_reserve (protected living money, owner's choice), sisa_uang_harian tool (writes this payday's living money), Payday plan spec (vault_tools/payday.py), daily_allowance (cash_to_hold // days_in_window), Payday window [payday, next payday), Plan output (transfers, cash_to_hold, daily_allowance, warnings), Test plan (test_payday.py) (+1 more)

### Community 69 - "Card Features and Deploy Plan"
Cohesion: 0.13
Nodes (18): ingest folder (ingest-gmail writes, vault-tools reads read-only; statement drop), ingest-gmail (timer job on net-vault, writes the ingest folder), SOUL.md: vault bot persona (personal finance advisor and planner), Card instalment recording (x/y lines, record_card_installments, card_installments_status), Card payment method rules (Jenius and BCA to an account, Mandiri via the app menu, others to the card number), Card tokens [[CARD:num-xxxx]] map to stored cards by last 4 digits; then link_card_payees, Chat uploads (list_uploads, ingest_statement, record_mutations; BARIS KURANG means resend with replace=true), dana_darurat (emergency fund status and recorded balance) (+10 more)

### Community 70 - "Payday Plan and Pot Tools (Usage)"
Cohesion: 0.21
Nodes (16): Ledger backups made 2026-11-01: pre-pace-fix, pocket-balance, recal (each with -shm and -wal copies), card_payments table (7 rows, one payment per card, last 2026-10-28 to 2026-10-30), sekali: one-off categories (e.g. coway-tunggakan, jht, jual-emas, medis, pelunasan-kartu), Emergency fund (darurat; 2 fund reports, last 2026-10-30), fixed_expenses table (6 rows), fund_reports table (3 rows: darurat 2, pot:hutang-teman 1), Payday plan (rencana gajian; paydays 2026-10-30 and 2026-11-30), Pot savings (setoran pot deposits in the payday plan) (+8 more)

### Community 71 - "Compose Logging Options"
Cohesion: 0.22
Nodes (16): logging, logging, logging, logging, driver, options, max-file, max-size (+8 more)

### Community 72 - "Compose Service: ingest-gmail"
Cohesion: 0.10
Nodes (22): environment, CONTROL_STATE_DIR, HTTPS_PROXY, MY_TELEGRAM_ID, NO_PROXY, TELEGRAM_TOKEN_FILE, build, cap_drop (+14 more)

### Community 73 - "Compose Service: vault-tools"
Cohesion: 0.14
Nodes (14): vault-tools, build, cap_drop, cpus, depends_on, mem_limit, networks, oom_score_adj (+6 more)

### Community 74 - "Hermes Agent (nousresearch/hermes-agent, pinned v0.22.5)"
Cohesion: 0.11
Nodes (15): Architecture (M1 skeleton), Hermes pin: nousresearch/hermes-agent v0.22.5 (manifest digest recorded, checked 2026-10-27), vault (Hermes finance bot container), vault-tools (vault zone tool service), /new command (fresh Telegram session), Spike 6: plugins are opt-in via plugins.enabled (confirmed), Spike 8: model id claude-sonnet-5-5 accepted (pass), Bot calibration runbook (manual, on the owner's request) (+7 more)

### Community 75 - "Auto-Debits and Due Rules"
Cohesion: 0.18
Nodes (9): belanja_kartu (/belanja: statement lines per cycle and per card; not reading PDFs), generate_payday_plan (payday plan, uses the new salary up to 7 days after payday), Frequently asked numbers, always labelled (no defisit unless tool output), Long-list commands (/rencana, /tagihan, /belanja, /cicilan, /anggaran, /peta, /kondisi, /data, /periksa), Payday list on the 1st (main flow, steps 0-5; no automatic reminders), periksa_data (data check: MASALAH and PERHATIAN; compares subscriptions with card charges), /rencana (full payday list with progress marks), ringkasan_data (data summary: open bills, own accounts, living money this month) (+1 more)

### Community 76 - "set_category_rule"
Cohesion: 0.09
Nodes (25): jago-darurat (Jago savings account), belanja-harian category (3 rules), belanja-online category (15 rules), berhenti:supir category (12 rules), biaya-bank category (47 rules), bunga category (23 rules), donasi category (7 rules), gaji category (9 rules) (+17 more)

### Community 77 - "Compose Service: control"
Cohesion: 0.14
Nodes (14): build, cap_drop, cpus, depends_on, mem_limit, networks, oom_score_adj, read_only (+6 more)

### Community 78 - "Compose Service: vault (Hermes)"
Cohesion: 0.15
Nodes (13): vault, command, cpu_shares, cpus, depends_on, env_file, image, mem_limit (+5 more)

### Community 80 - "Record Corrections and Change Log"
Cohesion: 0.28
Nodes (7): Category scheme (wajib:, sinking:, transfer_internal, sekali:, perantara:, berhenti:, free daily spending), Financial analysis (cashflow_summary, recurring_payments, suggest_salary, list_uncategorized, set_category_rule), Procedure: computing the living reserve (set_category_keyword, add_owner_name, suggest_categories, 80% categorized, living_cost_analysis from 2026-07), Record correction flow (daftar_belanja, before/after, ya, ubah_belanja or hapus_belanja, lepas=true), record_expense (recorded, alerts, possible_duplicate, allow_duplicate), Expenses from screenshots (record_expense with one source; vision_analyze for images), set_threshold (net_salary, living_reserve, saldo_ditahan:<alias>)

### Community 81 - "Compaction and Open Questions"
Cohesion: 0.28
Nodes (5): Auto-debit debts (upsert_debt pay_method=autodebit; one figure per account incl. the bank-held minimum), Daily living account (uang-harian at Jago; the owner spends daily only from it), saldo_ditahan:<account alias> (bank-held minimum balance, e.g. saldo_ditahan:mandiri-utama), saldo_rekening (account balance as shown; CUKUP/KURANG for autodebits; corrects this month's living money for the daily account), sisa_uang_harian (living money left just BEFORE the salary, usable after the bank-held minimum)

### Community 82 - "front"
Cohesion: 0.11
Nodes (19): path, required, cap_add, cap_drop, command, cpu_shares, cpus, depends_on (+11 more)

### Community 85 - "Compose Service: squid-comms"
Cohesion: 0.11
Nodes (18): name, services, squid-comms, cap_add, cap_drop, cpus, image, mem_limit (+10 more)

### Community 86 - "Compose Service: squid-ctl"
Cohesion: 0.17
Nodes (12): squid-ctl, cap_add, cap_drop, cpus, image, mem_limit, networks, oom_score_adj (+4 more)

### Community 87 - "Compose Service: squid-front"
Cohesion: 0.17
Nodes (12): squid-front, cap_add, cap_drop, cpus, image, mem_limit, networks, oom_score_adj (+4 more)

### Community 88 - "Compose Service: squid-vault"
Cohesion: 0.17
Nodes (12): squid-vault, cap_add, cap_drop, cpus, image, mem_limit, networks, oom_score_adj (+4 more)

### Community 89 - "Gmail OAuth and Sender Allowlist"
Cohesion: 0.27
Nodes (14): Gmail OAuth guide (readonly) for ingest-gmail, Bank sender allowlist with DKIM/DMARC pass (DBS, CIMB Niaga, HSBC, Mandiri, Mega), Gmail API (gmail.googleapis.com, oauth2.googleapis.com), Gmail readonly token (gmail_ingest_token), Google Cloud project personal-agent-ingest (Gmail API enabled), ingest-desktop OAuth client (gmail_ingest_client), ingest-gmail (daily deterministic job, no LLM), Keuangan/Kartu Kredit Gmail label (looked up by label ID) (+6 more)

### Community 90 - "Debts, Balances and Proposals (State)"
Cohesion: 0.29
Nodes (15): Autodebit (autodebet) of debt instalments, Ledger backups made 2026-10-28: pre-answers, calibrate, cardbudget, cardlines, daily-account, dedupe, dedupe-cards, ef-pocket, flazz-fix, held-balance, invariants, keywords, latest, notion, pot-schedule, recal-v2, recurring, rules2, scenarioA, balance_reports table (5 rows: mandiri-utama 4, jago-harian 1), Car instalment debt (cicilan-mobil): due 2 Nov paid manually 30 Oct, 18 instalments left, next autodebit 2 Dec, wajib: mandatory categories (asuransi, cicilan, ipl, kartu, les, sekolah, spaylater), debt_payments table (2 manual payments, cicilan-mobil and spaylater, 2026-10-30), debts table (2 rows), feature_requests table (/usulan, 10 rows) (+7 more)

### Community 91 - "Uploads and Statement Ingest (Usage)"
Cohesion: 0.11
Nodes (25): Vault tool names called without the MCP prefix, mcp__vault_tools__cashflow_summary, mcp__vault_tools__catat_usulan, clarify (engine tool), Engine deferred-tool wrappers (tool_search, tool_describe, tool_call), Engine (non-MCP) tool calls per day and source, Image routing: text mode (pre-analysis via vision_analyze), mcp__vault_tools__ingest_events (+17 more)

### Community 92 - "Graph-First Prompt Hook"
Cohesion: 0.16
Nodes (10): behind(), ignore_patterns(), ignored(), main(), md5(), snapshot(), wib(), find_file() (+2 more)

### Community 94 - "Expense and Mutation Tools (Usage)"
Cohesion: 0.09
Nodes (38): accounts table (8 rows), Ledger backups made 2026-10-27: pre-v4, v5, v6, v8, v9, categorize, completeness, instkey, owner-names, pending, perantara, pocketfix, scans, subs, Ledger backups made 2026-10-30: pre-leftover-fix, merge-fix, payday-progress, record-merge, unmerge, unmerge-2, usulan (with -shm and -wal copies), bca-utama account (993 transactions; 10 mutation files 2026-01-01 to 2026-10-28), card_installment_scans table (25 rows, 25 scanned statements), berhenti: stopped categories (cicilan-rumah, komisi-allianz, supir, trip-mancing), category_keywords table (9 rows), perantara: pass-through categories (3 values, 37 transactions) (+30 more)

### Community 95 - "Hermes Skills and Pending Proposals"
Cohesion: 0.10
Nodes (19): logs/agent.log (INFO and above: 22639 lines, 9 ERROR, 448 WARNING, 730 distinct templates), cardguard plugin v0.1 (replaces card numbers in inbound Telegram text with tokens before dispatch; spike), cardguard TTL file (ttl/rincian.jsonl: /rincian messages to delete after expiry; 0 lines), logs/errors.log (WARNING and above: 686 lines, 152 distinct templates), state/gateway.lifecycle.json (gateway lifecycle phase, pid and start time), Preflight-compression log line (shows the threshold in force when it was written), Log line 'Re-anchored stale current_turn_user_idx' (agent/turn_iteration_prep.py; counts mid-turn compactions), Logger cardguard (56 INFO, 4 WARNING) (+11 more)

### Community 96 - "Corrected Source Merges"
Cohesion: 0.15
Nodes (5): CorrectedSourceFindsItsStatementRow, Edit, log(), pho(), world()

### Community 98 - "Compose Networks"
Cohesion: 0.20
Nodes (10): internal, internal, internal, internal, networks, egress, net-comms, net-ctl (+2 more)

### Community 99 - "Compose Squid Template"
Cohesion: 0.20
Nodes (10): x-squid, cap_add, cap_drop, cpus, image, mem_limit, oom_score_adj, restart (+2 more)

### Community 100 - "living_reserve (protected monthly cash living money)"
Cohesion: 0.22
Nodes (10): Accuracy layers (owner: 99.99% accuracy, no miscalculation), belanja_kartu (per-card statement lines, /belanja), Card statement recording and reconciliation (7 cards), Duplicate expense rule (same date + amount + source account/card), Emergency fund (emergency_target, emergency_monthly, dana_darurat), Self-checks (vault_tools/invariants.py, CalculationError), Property tests (random ledgers, stress run), record_card_payment (same amount twice on one day refused unless ulang=true) (+2 more)

### Community 101 - "Host Runtime and Firewall"
Cohesion: 0.29
Nodes (10): authorized_keys (root: 0 entries, ubuntu: 1), fail2ban (inactive), Host firewall (active; deny incoming except 22/tcp, allow outgoing, deny routed), Host (VPS) runtime map, personal-agent-ingest-gmail image (latest, created 2026-10-28), Listening sockets (sshd on 22/tcp on all interfaces; systemd-resolved and chronyd on loopback; DHCP client on eth0), sshd: key-only login, no root login, 3 auth tries (port 22, X11 forwarding on), Unattended upgrades (APT periodic package-list update and unattended upgrade on) (+2 more)

### Community 102 - "Proposals"
Cohesion: 0.22
Nodes (3): FakeTelegram, good(), Proposals

### Community 103 - "Hermes Auxiliary Models"
Cohesion: 0.20
Nodes (10): auxiliary, compression, title_generation, vision, model, provider, model, provider (+2 more)

### Community 104 - "Hermes MCP Server Config"
Cohesion: 0.20
Nodes (10): Authorization, mcp_servers, vault_tools, prompts, resources, connect_timeout, headers, timeout (+2 more)

### Community 105 - "change-proposals"
Cohesion: 0.11
Nodes (18): context, dockerfile, build, cap_drop, cpu_shares, cpus, environment, mem_limit (+10 more)

### Community 106 - "Sender Config Loading"
Cohesion: 0.38
Nodes (3): load_senders(), main(), SenderConfig

### Community 107 - "record_mutations"
Cohesion: 0.16
Nodes (10): Installments, OneCardOneAlias, Overview, world(), active(), _add_months(), format_list(), monthly_total() (+2 more)

### Community 108 - "Hermes Credentials Boundary"
Cohesion: 0.24
Nodes (10): auth.json (Hermes credential store and pool, empty; the API key comes from env; never opened by the collector), ANTHROPIC_API_KEY env var (where the Anthropic key comes from; value never read), Hermes .env in HERMES_HOME (mode 0600, never opened by the collector), ingest_statement (read a financial file, PDF, CSV or TXT, from the ingest folder or a Telegram upload, decrypting it), list_uploads (files the owner recently uploaded via Telegram, newest first, as file_ref for ingest_statement), Log line 'credential pool: no available entries' (agent/credential_pool.py; benign), Logger agent.credential_pool (72 INFO), Runtime-map collector (ops/runtime-map/collect.py, regenerated with make runtime-map) (+2 more)

### Community 109 - "Host Timers and Restic (State)"
Cohesion: 0.11
Nodes (24): docs/runtime/README.md, State snapshot, api.notion.com (Notion API; 290 requests via squid-vault), Deploy drift: 173 repo files vs 172 in /opt/personal-agent, 172 identical, no runtime drift, pa-disk log line disk N% (112 runs in 7 days), Holiday baseline: libur and cuti bersama dates added by pa-holidays, Host systemd timers and jobs (pa-*, every result success), make runtime-map (regenerates the state snapshot from the live VPS) (+16 more)

### Community 110 - "Runtime Map Scrub Tests"
Cohesion: 0.14
Nodes (22): bca-9706 card (10 statements 2026-01-12 to 2026-10-12, last due 2026-10-28; 8 instalment rows), card_installments table (26 instalment rows across 5 cards), Card line kinds (belanja 493, biaya 134, bunga 36, cicilan 109, langganan 181, pembayaran 78, refund 35), card_lines table (1066 card statement lines), cards table (7 cards; all statements reconciled, lines ok 0 per card), cimb-9888 card (10 statements 2026-01-19 to 2026-10-19, last due 2026-11-05), dbs-5685 card (6 statements 2026-01-25 to 2026-10-25, last due 2026-11-10; 0 marked paid; 10 instalment rows), hsbc-5915 card (9 statements 2026-02-19 to 2026-10-19, last due 2026-11-04; 2 instalment rows) (+14 more)

### Community 113 - "simulasi_skenario (code-computed what-if simulator)"
Cohesion: 0.12
Nodes (18): Bot calibration from the owner's real chat (2026-10-28), Bot model config (reasoning_effort high, claude-sonnet-5-5 vision and compression, Haiku titles), Card installments (x/y) tracking, Card spending budgets (kartu:<category>), Key finding: card run-rate exceeds the room left after fixed costs, car and pot, living_leftover stored as the owner's own figure (replaces living_reserve_override), living_reserve (protected monthly cash living money), Payday plan (generate_payday_plan, /rencana, /rincian) (+10 more)

### Community 114 - "Card Payment Targets"
Cohesion: 0.12
Nodes (13): Card payment targets and link_card_payees (cards.pay_to_alias), due_payday (31 Jan 2028 salary counted for the pot), Open questions for the owner (resume here), payee_secrets (registered card/account numbers), Plan #62 (30 Oct 2026 payday: pot short at the deadline), Pot hutang-teman (friend's debt goal, single transfer on 31 Jan 2028), status_gajian (payday progress plus facts already reported), Subscription notes kept (empty field keeps, empty string clears, 300-char limit) (+5 more)

### Community 115 - "Ingest Events and Cron"
Cohesion: 0.14
Nodes (14): clarify engine tool, cron/executions.db executions table (0 rows), Hermes cron store (cron/: executions.db, job and tick locks, ticker heartbeat; no jobs), Engine tools besides MCP (only clarify and vision_analyze next to the 56 vault_tools tools), kanban.db (kanban store; toolset disabled, every table empty), kanban.db kanban_notify_subs table (0 rows), kanban.db task_attachments table (0 rows), kanban.db task_comments table (0 rows) (+6 more)

### Community 117 - "Compose Root and Hardening"
Cohesion: 0.16
Nodes (4): Balanced, check_html(), Reports, world()

### Community 118 - "test_zones.py"
Cohesion: 0.21
Nodes (4): Compose, HermesProfiles, load(), mounts()

### Community 122 - "front/config.yaml"
Cohesion: 0.15
Nodes (12): approvals, destructive_slash_confirm, compression, min_tail_user_messages, threshold_tokens, security, allow_lazy_installs, sessions (+4 more)

### Community 124 - "Hermes Telegram Gateway Config"
Cohesion: 0.33
Nodes (6): allowed_chats, disable_link_previews, gateway, platforms, telegram, extra

### Community 126 - "date"
Cohesion: 0.13
Nodes (12): account_balances(), alerts_for(), budget_status(), _by_balance(), cash_spent(), debt_load(), health_check(), is_discretionary() (+4 more)

### Community 127 - "Hermes Agent Block"
Cohesion: 0.50
Nodes (4): agent, disabled_toolsets, max_turns, reasoning_effort

### Community 128 - "Hermes Memory Settings"
Cohesion: 0.50
Nodes (4): memory, memory_enabled, user_profile_enabled, write_approval

### Community 129 - "Cardguard Plugin Manifest"
Cohesion: 0.50
Nodes (3): description, name, version

### Community 130 - "System-Managed Balance Tool Test"
Cohesion: 0.17
Nodes (18): logs/container-boot.log (boot diagnostics, 60 lines), Hermes gateway process (the Telegram bot: hermes gateway run --replace, uid 10000, kind hermes-gateway, state running), logs/gateway-exit-diag.log (exit diagnostics, 178 lines), logs/gateway_faulthandler.log (empty), logs/gateway.log (4451 lines: 3 ERROR, 437 WARNING, 231 distinct templates), Gateway multiplex standalone (only one profile exists, nothing to multiplex), Gateway runtime/dashboard API (127.0.0.1, start_gateway_api with port 0: a new port on every boot), gateway.lock, gateway.pid, gateway.sock and gateway-starts.log in HERMES_HOME (+10 more)

### Community 131 - "Hermes Compression Settings"
Cohesion: 0.16
Nodes (18): Gateway session keys (agent:main:local:dm 38, agent:main:telegram:dm 1, plus _README), sessions/sessions.json (gateway session key to session, with token and cost counters; 39 keys), sessions.retention_days 90 (same as the default: inactive days of ended-session history kept), state.db (sessions, messages, model usage, delivery obligations, routing, admissions, system prompts; SQLite WAL), state.db gateway_heartbeats table (22 rows), state.db gateway_hygiene_state table (0 rows), state.db gateway_routing table (77 rows), state.db hosted_room tables (14 hosted-room tables, all empty) (+10 more)

### Community 132 - "Ledger (ledger.db on the VPS)"
Cohesion: 0.17
Nodes (13): Cash records never merge (record_expense: exactly one of account_alias, card_alias, tunai=true), category_keywords (owner-explained names), Category scheme (perantara, berhenti, sekali, bunga, wajib, transfer_internal), change_log table (before/after rows with the owner's reason), daftar_belanja, ubah_belanja, hapus_belanja (correct owner records), transactions.dedupe_key (unique index), Id-reuse fix 45dfc1e (INTEGER PRIMARY KEY without AUTOINCREMENT), Ledger (ledger.db on the VPS) (+5 more)

### Community 133 - "auxiliary"
Cohesion: 0.20
Nodes (10): auxiliary, compression, title_generation, vision, model, provider, model, provider (+2 more)

### Community 137 - "change_proposals"
Cohesion: 0.20
Nodes (10): connect_timeout, headers, timeout, tools, url, Authorization, mcp_servers, change_proposals (+2 more)

### Community 138 - "roadmap.py"
Cohesion: 0.11
Nodes (11): PaydayWindow, Dates, Holidays, commitments(), add_months(), _clamp(), next_due(), current_payday() (+3 more)

### Community 140 - "Asisten umum pemilik (front)"
Cohesion: 0.10
Nodes (19): front (Hermes on Haiku, compose profile front, started once the owner's front secrets exist), Spike 1: read-only config.yaml and plugins mount (pass), Front memory approval (/memory pending, /memory approve <id>, /memory reject <id>), Front owner steps, in order (BotFather, Anthropic workspace, secrets, render env, start, test), Front redeploy after services/hermes/front/ changes, and stop (--profile front stop front change-proposals), Front secrets telegram_front_token and anthropic_front_key (make secret-set), Start front: compose --profile front up -d --build --wait change-proposals front, Front zone @danoefront_agent (M3, defined, not started; Haiku 5.5, web search, memory, submit) (+11 more)

### Community 141 - ".world"
Cohesion: 0.18
Nodes (15): canary.txt (root-owned file in the data dir, mode 0644), control-state dir (mode 0700), personal-agent-change-proposals image (latest, created 2026-11-01), personal-agent-control image (latest, created 2026-11-01), ingest-state dir (mode 0755), /opt/personal-agent-data (persistent state, root-owned, restic-backed), proposals-inbox dir (mode 0700, empty), change_proposals_mcp_token secret (+7 more)

### Community 142 - "extra"
Cohesion: 0.33
Nodes (6): allowed_chats, disable_link_previews, gateway, platforms, telegram, extra

### Community 143 - "key_lines"
Cohesion: 0.18
Nodes (14): hermes-front dir (mode 0700, empty), nousresearch/hermes-agent image (no tag, created 2026-10-23), ubuntu/squid:6.6-24.04_edge image, anthropic_vault_key secret, vault.env (root-only env file, mode 0600), BOT_FRONT (front Telegram bot username), config/squid/comms.conf (comms zone allowlist: Anthropic and Google APIs), config/squid/ctl.conf (control zone allowlist: Telegram API only) (+6 more)

### Community 144 - "memory"
Cohesion: 0.40
Nodes (5): memory, memory_enabled, nudge_interval, user_profile_enabled, write_approval

### Community 145 - ".test_a_new_living_reserve_keeps_the_owners_leftover"
Cohesion: 0.13
Nodes (17): jenius-akun (Jenius main account, also a payee), bca-9706 (bca card; statement day 12, due day 28, transfer to num-9706), cimb-9888 (cimb card; statement day 19, due day 7, transfer to num-9888), dbs-5685 (DBS card; statement day 25, due day 10, transfer to num-5685), hsbc-5915 (HSBC card; statement day 19, due day 4, transfer to num-5915), jenius-0480 (jenius card; statement day 26, due day 13, transfer to jenius-akun), mandiri-4365 (mandiri card; statement day 16, due day 5, paid via app_menu), mega-5855 (Mega card; statement day 22, due day 7, transfer to num-5855) (+9 more)

### Community 146 - "recurring"
Cohesion: 0.16
Nodes (11): generate_payday_plan(), status_gajian(), _carried(), _kind_text(), payday_status(), _progress_name(), _reported(), summarize_plan() (+3 more)

### Community 147 - "socket_inodes_as"
Cohesion: 0.18
Nodes (15): busy_input_mode demoted while compression is in flight, Child sessions (a compaction or /new continues the chat), Compression blocked (ineffective, structural_backoff), Compression folded away the just-delivered reply, Context compression (compaction), logs/gateways/default/current, Model context warmed: claude-sonnet-5-5 at 1M tokens, Pre-API compression (near the context or output limit) (+7 more)

### Community 149 - "agent"
Cohesion: 0.50
Nodes (4): agent, disabled_toolsets, image_input_mode, max_turns

### Community 156 - "model"
Cohesion: 0.67
Nodes (3): model, default, provider

### Community 157 - "tools"
Cohesion: 0.67
Nodes (3): enabled, tools, tool_search

### Community 158 - "tools"
Cohesion: 0.67
Nodes (3): enabled, tools, tool_search

### Community 159 - "Rincian"
Cohesion: 0.20
Nodes (13): /opt/personal-agent-secrets (secret files, mode 0700), gmail_ingest_client secret, pdf_passwords secret, telegram_control_token secret, vault_tools_key secret, .gitignore (decrypted secrets, keys, .env, .claude, graphify-out), make pdf-passwords (interactive hidden input, runs on the VPS), make secret-gen NAME=... TYPE=... (random value created on the VPS) (+5 more)

### Community 162 - "accounts (ledger table, 8 rows)"
Cohesion: 0.17
Nodes (15): bca-utama (BCA main account), fixed-expenses (Jago savings account), jago-harian (Jago main account), jago-utama (jago main account), mandiri-utama (Mandiri main account), wajib:cicilan category (9 rules), wajib:spaylater category (3 rules), cicilan-mobil (debt to MTF, autodebit from mandiri-utama, due day 2) (+7 more)

### Community 163 - "logs/errors.log"
Cohesion: 0.14
Nodes (14): agent.deadline: task timed out and abandoned, Compression summary call and aux_model telemetry, background_review model task, claude-sonnet-5-5 (vault bot model), Config migration skipped (hermes_cli.post_update), Conversation loop API calls and turn re-anchoring, destructive_slash_confirm=false not persisted (config.yaml not writable), logs/errors.log (+6 more)

### Community 164 - "invariants.py"
Cohesion: 0.21
Nodes (6): TheChecksCatchBrokenNumbers, CalculationError, plan_errors(), require(), simulation_errors(), _whole()

### Community 165 - "logs/agent.log"
Cohesion: 0.19
Nodes (13): Agent budget: max_iterations=40, logs/agent.log, cardguard capability_check: tools.override denied, cardguard number guard (amounts not from the tools), Credential pool: no available entries, Engine facts from the logs (latest line of each), Hermes model catalog fetch failing (urlopen Tunnel error), Hermes plugin discovery and provider registration (+5 more)

### Community 166 - "Hermes Agent v0.22.5 (vault bot engine, Telegram bot @danoevault_agent, container personal-agent-vault-1)"
Cohesion: 0.17
Nodes (12): Bundled engine plugins (browser, computer_use, context_engine, cron_providers, delegation, image_gen, kanban, memory, model-providers, platforms, web and others), TZ Asia/Jakarta (container timezone), Docker embedded DNS (container-local tcp and udp listeners), Engine image nousresearch/hermes-agent (release date 2026.9.24), Hermes Agent v0.22.5 (vault bot engine, Telegram bot @danoevault_agent, container personal-agent-vault-1), Install stamp (baseVersion 0.22.5, branch main, distribution docker, source ci, updateMechanism external, built 2026-10-23), installs/ and install_id (install bootstrap metadata), Log line 'router: catalog fetch failed / Model catalog' (plugins/model-providers/router; harmless) (+4 more)

### Community 167 - "last_working_day"
Cohesion: 0.24
Nodes (6): PaydayDates, is_working_day(), last_working_day(), next_payday(), next_payday(), next_salary_after()

### Community 168 - "category_keywords (ledger table, 9 rows)"
Cohesion: 0.17
Nodes (12): berhenti:trip-mancing category (1 owner keyword), komisi-allianz category (1 owner keyword), perantara:art-belanja-anak category (1 owner keyword), sekali:keluarga-istri category (1 owner keyword), wajib:ipl category (10 rules), wajib:les category (4 owner keywords), wajib:sekolah category (3 rules), Children's lesson fees (3 les-* fixed expenses due day 1, each to a BCA account payee) (+4 more)

### Community 169 - "build"
Cohesion: 0.23
Nodes (8): Rincian, _bank(), build(), account(), describe(), mark(), _nice(), rincian()

### Community 170 - "format_idr"
Cohesion: 0.21
Nodes (9): format_health(), format_idr(), budget_status(), health_check(), list_statements(), paid(), bill_status(), format_autodebit_check() (+1 more)

### Community 171 - "Hermes Telegram adapter (polling mode)"
Cohesion: 0.24
Nodes (11): Telegram fallback-IP discovery via DNS-over-HTTPS, platforms.telegram.extra.drop_pending_on_cold_boot: true, Fatal telegram adapter error: updater.stop() missed the network-recovery deadline, mcp__vault_tools__list_uploads, Reply target deleted: retry without reply_to, squid-vault proxy (http://squid-vault:3128), Hermes Telegram adapter (polling mode), Telegram inbound document cache (/opt/data/cache/documents) (+3 more)

### Community 172 - "Telegram platform adapter (plugins/platforms/telegram/adapter.py; state connected)"
Cohesion: 0.27
Nodes (8): channel_directory.json (chats the gateway knows: one telegram entry), Log line 'Cold boot: dropping Telegram updates' (Telegram adapter), Logger hermes_plugins.platforms__telegram.adapter (819 INFO, 268 WARNING, 2 ERROR), state.db conversation_generations table (1 row, source telegram), state.db delivery_obligations table (187 Telegram deliveries, all delivered, 2026-10-27 to 2026-10-31), gateway.platforms.telegram.extra.disable_link_previews true (read by the Telegram adapter), Telegram platform adapter (plugins/platforms/telegram/adapter.py; state connected), telegram_update_receipts JSON file in HERMES_HOME

### Community 173 - "ingest_file_parts"
Cohesion: 0.20
Nodes (5): ingest_statement(), record_statement(), ingest_file_parts(), load_passwords(), split_parts()

### Community 174 - "payday.py"
Cohesion: 0.20
Nodes (5): _items(), Plan, Transfer, Unfunded, plan_to_dict()

### Community 176 - "/rincian handled in pre_gateway_dispatch with skip plus direct Bot API send"
Cohesion: 0.25
Nodes (7): /rincian handled in pre_gateway_dispatch with skip plus direct Bot API send, Open: whether skip plus a direct Bot API reply writes to the session store, Spike 11: /rincian reply stays out of the session store (pass), vault's cardguard (needs vault-tools, which front cannot reach), Open decision: a rewrite-only card and account number guard plugin for front before step 4, Open question: no plugin removes card and account numbers before front's model sees them (owner's call), /internal/* surface (plugin only: store_payee, rincian)

### Community 177 - "/ingest (read-only; filled by ingest-gmail and pa-uploads)"
Cohesion: 0.25
Nodes (8): /opt/personal-agent-data/ingest (read-only at /ingest), pdf_passwords secret (read-only at /run/secrets), /ingest (read-only; filled by ingest-gmail and pa-uploads), ingest-gmail (fills /ingest), /ingest/telegram (58 files: bank statements, e-statements and mutasi sent as Telegram documents), pa-uploads (fills /ingest), PDF parsing packages (pdfplumber, pdfminer.six, pikepdf, pypdfium2), skipped_files (ledger table, 52 rows)

### Community 178 - "payee_secrets (ledger table, 19 rows; nonce, ciphertext, match_hash)"
Cohesion: 0.31
Nodes (9): vault_tools_key secret (read-only at /run/secrets), pot-jago (Jago pool account), cryptography package (50.0.2), A friend's BCA account payee (creditor_pay_to of hutang-teman), Jago account payees (dana-darurat, pot-jago-rek, uang-harian), hutang-teman sinking fund (repaying a friend by 2028-01-31 from pool pot-jago; pace sisa, due_payday 1), fund_reports (ledger table, 3 rows), payee_secrets (ledger table, 19 rows; nonce, ciphertext, match_hash) (+1 more)

### Community 179 - "Invariants enforced in infrastructure, not prompts"
Cohesion: 0.29
Nodes (6): Finding 2026-11-01: getMe showed Allow Groups still on for @danoevault_agent and @danoecontrol_bot, Hermes configs drop groups (allowed_chats: none); control drops them in code, BotFather bots (usernames end in bot, Allow Groups off), Finding: BotFather Allow Groups still on for the vault and control bots (getMe 2026-11-01), Container hardening (cap_drop ALL, no-new-privileges, read-only root fs, memory and CPU caps, oom_score_adj), Hermes zones answer only TELEGRAM_ALLOWED_USERS and drop every group (allowed_chats: none, checked against v0.22.5)

### Community 180 - "personal-agent-control-1 (control service; uid 10001, 128 MB / 0.25 CPU)"
Cohesion: 0.39
Nodes (8): control.py (python -I control.py, workdir /app), Control env (MY_TELEGRAM_ID value masked, TELEGRAM_TOKEN_FILE, PROPOSALS_INBOX_DIR, CONTROL_STATE_DIR), Hermes Telegram env (TELEGRAM_BOT_TOKEN; TELEGRAM_ALLOWED_USERS and TELEGRAM_HOME_CHANNEL values masked), /opt/personal-agent-data/control-state (rw at /state, control), /opt/personal-agent-data/proposals-inbox (rw at /inbox, control), personal-agent-control-1 (control service; uid 10001, 128 MB / 0.25 CPU), Read-only rootfs with tmpfs /tmp (control, vault-tools), telegram_control_token secret (read-only at /run/secrets, control)

### Community 181 - "hermes-vault data dir (mode 0700)"
Cohesion: 0.29
Nodes (7): hermes-vault data dir (mode 0700), ingest data dir (mode 0755), telegram_vault_token secret, BOT_VAULT (vault Telegram bot username), Hermes vault document cache (hermes-vault/cache/documents), pa-uploads.path + service + timer (relays Telegram uploads to the ingest folder), scripts/sync-uploads.sh (upload relay and retention sweep)

### Community 182 - "_extract_clean"
Cohesion: 0.25
Nodes (4): _extract_clean(), ingest_file(), sanitize(), wrap_untrusted()

### Community 183 - "vision_analyze engine tool"
Cohesion: 0.29
Nodes (7): auxiliary.vision: claude-sonnet-5-5 via anthropic (default auto), daftar_belanja (purchases recorded from screenshots, receipts or the owner's words over the last days, each with its id), hapus_belanja (delete one recorded purchase, e.g. one recorded twice; same rules as ubah_belanja), Logger tools.vision_tools (93 INFO), record_expense (record one purchase from a screenshot, receipt or the owner's words), ubah_belanja (change one recorded purchase: wrong source, amount, date, merchant or category), vision_analyze engine tool

### Community 184 - "config/stack.env (non-secret stack settings)"
Cohesion: 0.38
Nodes (7): gmail_ingest_token secret, config/stack.env (non-secret stack settings), pa-disk.service + timer (disk usage check, hourly), pa-gmail-token.service + timer (warns before the Gmail OAuth token expires, daily 08:00 WIB), MY_TELEGRAM_ID (owner's Telegram id, value scrubbed), scripts/disk-check.sh (disk usage check), scripts/gmail-token-check.py (Gmail OAuth token expiry check)

### Community 185 - "Bound fund: the friend's debt pot (deadline 31 Jan 2028, Jago pot account, sinking:<fund alias>, upsert_sinking_fund)"
Cohesion: 0.33
Nodes (3): Pot shortfall options (cut games or non-mandatory apps, count the due-day salary, talk to the friend), each tested with simulasi_skenario, Bound fund: the friend's debt pot (deadline 31 Jan 2028, Jago pot account, sinking:<fund alias>, upsert_sinking_fund), sinking_status (pot pattern and forecast at the deadline)

### Community 186 - "The bot's three /usulan built (schema v12)"
Cohesion: 0.40
Nodes (6): Auto-debits from Mandiri (car instalment MTF, SPayLater), catat_usulan and /usulan (feature requests), cicilan_dibayar (instalment paid by hand ahead of its auto-debit), Deploy 2 before the 30 Nov payday (admin fees, one-off bills, cicilan_dibayar undo), saldo_rekening (balance_reports checked against auto-debits), The bot's three /usulan built (schema v12)

### Community 187 - "ingest-gmail job (services/ingest-gmail/Dockerfile, own ingest user)"
Cohesion: 0.60
Nodes (5): compose/docker-compose.yml (Docker Compose stack), compose jobs profile (one-off ingest-gmail runs), pa-ingest.service + timer (ingest-gmail statement fetch, daily 06:00 WIB), pa-notion.service + timer (Notion snapshot of the finance picture, daily 06:30 WIB), ingest-gmail job (services/ingest-gmail/Dockerfile, own ingest user)

### Community 193 - "model"
Cohesion: 0.67
Nodes (3): model, default, provider

## Ambiguous Edges - Review These
- `pa-forget (service and timer; no recorded run, next 2026-11-01 04:00)` → `Restic backup repository (off-container copies; 5 snapshots saved in 7 days)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `cards table (7 cards; all statements reconciled, lines ok 0 per card)` → `lines_status: cocok on all 63 statements`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `dbs-5685 card (6 statements 2026-01-25 to 2026-10-25, last due 2026-11-10; 0 marked paid; 10 instalment rows)` → `card_payments table (7 rows, one payment per card, last 2026-10-28 to 2026-10-30)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `Engine tools besides MCP (only clarify and vision_analyze next to the 56 vault_tools tools)` → `cache/tool_discovery_cache.json (tool discovery cache, 287 keys, written 2026-10-27)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `cache/schema_columns.json (schema hash plus versions for 17 tables)` → `state.db (sessions, messages, model usage, delivery obligations, routing, admissions, system prompts; SQLite WAL)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `Gateway multiplex standalone (only one profile exists, nothing to multiplex)` → `state.db hosted_room tables (14 hosted-room tables, all empty)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `canary.txt (root-owned file in the data dir, mode 0644)` → `pa-backup.service + timer (restic backup, daily 02:00 WIB)`  [AMBIGUOUS]
  docs/runtime/host.md · relation: conceptually_related_to
- `pdf_passwords secret` → `ingest-gmail job (services/ingest-gmail/Dockerfile, own ingest user)`  [AMBIGUOUS]
  docs/runtime/host.md · relation: conceptually_related_to
- `telegram_update_receipts JSON file in HERMES_HOME` → `Messages sent while the bot restarts are dropped (platforms.telegram.extra.drop_pending_on_cold_boot, default true)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `Open: whether skip plus a direct Bot API reply writes to the session store` → `Spike 11: /rincian reply stays out of the session store (pass)`  [AMBIGUOUS]
  docs/assumptions.md · relation: conceptually_related_to
- `/ingest (read-only; filled by ingest-gmail and pa-uploads)` → `processed_messages (ledger table, 0 rows)`  [AMBIGUOUS]
  docs/runtime/vault-tools.md · relation: conceptually_related_to
- `Anonymous squid log and spool volumes (8, from image VOLUME lines)` → `squid exceptions (cap_add CAP_CHOWN, CAP_DAC_OVERRIDE, CAP_SETGID, CAP_SETUID; writable rootfs; tmpfs /var/log/squid)`  [AMBIGUOUS]
  docs/runtime/containers.md · relation: conceptually_related_to
- `/usulan (posts the waiting proposals again with their buttons)` → `Hitting a limit: catat_usulan, then sudah kucatat di /usulan`  [AMBIGUOUS]
  services/hermes/vault/SOUL.md · relation: semantically_similar_to
- `cardguard plugin (services/hermes/vault/plugins/cardguard, read-only at /opt/data/plugins/cardguard)` → `VAULT_TOOLS_MCP_TOKEN and VAULT_TOOLS_INTERNAL_TOKEN (vault env names)`  [AMBIGUOUS]
  docs/runtime/containers.md · relation: conceptually_related_to
- `Denied: AWS IMDSv2 credential probes to the instance-metadata address (/latest/api/token, iam/security-credentials)` → `squid-vault (vault zone egress proxy; allows api.anthropic.com, api.notion.com, api.telegram.org, gmail.googleapis.com, oauth2.googleapis.com)`  [AMBIGUOUS]
  docs/runtime/proxies.md · relation: conceptually_related_to
- `Denied: Hermes model-catalog and provider refreshes (hermes-agent.nousresearch.com, raw.githubusercontent.com, openrouter.ai, portal.nousresearch.com)` → `squid-vault (vault zone egress proxy; allows api.anthropic.com, api.notion.com, api.telegram.org, gmail.googleapis.com, oauth2.googleapis.com)`  [AMBIGUOUS]
  docs/runtime/proxies.md · relation: conceptually_related_to
- `pa-check.timer + pa-check.service (restic integrity check, 1st of month 04:00 WIB, runs backup.sh check)` → `pa-forget.timer + pa-forget.service (restic retention 7d/4w/6m, Sun 04:00 WIB, runs backup.sh forget)`  [AMBIGUOUS]
  docs/runtime/timers.md · relation: conceptually_related_to
- `Open: Telegram-side copy of the raw message (deleteMessage live test pending)` → `Spike 10: deleteMessage on the owner's incoming message (pass)`  [AMBIGUOUS]
  docs/assumptions.md · relation: conceptually_related_to
- `Plan output (transfers, cash_to_hold, daily_allowance, warnings)` → `Owner rules (non-negotiable)`  [AMBIGUOUS]
  docs/calibration.md · relation: conceptually_related_to
- `pot:hutang-teman fund (friend-debt pot; 1 fund report, 2026-10-26)` → `sinking_funds table (1 row)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `belanja_kartu (card spending breakdown per cycle from statement lines already read by code; never read the PDF for this)` → `cardguard TTL file (ttl/rincian.jsonl: /rincian messages to delete after expiry; 0 lines)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `transfer_internal category (504 transactions)` → `owner_names table (1 row)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to

## Knowledge Gaps
- **169 isolated node(s):** `AWS_DEFAULT_REGION`, `make runtime-map`, `mcp__vault_tools__add_owner_name`, `mcp__vault_tools__atur_jadwal_pot`, `mcp__vault_tools__belanja_kartu` (+164 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 863 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **37 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `State snapshot` connect `Host Timers and Restic (State)` to `Payday Plan and Pot Tools (Usage)`, `Telegram Gateway and Delivery`, `Expense and Mutation Tools (Usage)`, `Runtime Map Collector`?**
  _High betweenness centrality (0.110) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `create_app()` (e.g. with `report()` and `rincian()`) actually correct?**
  _`create_app()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AWS_DEFAULT_REGION`, `make runtime-map`, `mcp__vault_tools__add_owner_name` to the rest of the system?**
  _169 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Card Installments` be split into smaller, more focused modules?**
  _Cohesion score 0.060641627543035995 - nodes in this community are weakly interconnected._
- **Why does `Spend and quality review (bot_usage.py, bot_quality.py)` connect `Hermes Agent (nousresearch/hermes-agent, pinned v0.22.5)` to `format_idr`, `Card Features and Deploy Plan`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `pa-forget (service and timer; no recorded run, next 2026-11-01 04:00)` and `Restic backup repository (off-container copies; 5 snapshots saved in 7 days)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `cards table (7 cards; all statements reconciled, lines ok 0 per card)` and `lines_status: cocok on all 63 statements`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._