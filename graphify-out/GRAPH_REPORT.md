# Graph Report - m1-skeleton  (2026-11-01)

## Corpus Check
- 142 files · ~159,768 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 32 file(s) not represented in the graph (top: .service 9, .timer 9, (none) 8)

## Summary
- 3994 nodes · 9648 edges · 189 communities (157 shown, 32 thin omitted)
- Extraction: 88% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 1091 edges (avg confidence: 0.83)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bd5ad484`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Card Statement Line Parsing
- Hermes Runtime Probes
- Merged Record Correction Tests
- Cardguard Plugin and Control Bot
- Payday Calendar and Holidays
- Ledger Database and Tables (Runtime)
- Report Renderers (reports.py)
- Shared Imports and Ledger Connections
- Bills Paid Once and Payday Dates
- Live MCP Tool Catalog
- Bot Tool Usage (state.db)
- Bank Mutations and Category Rules
- Hermes Home, Stores and Skills
- Living Money Pace and Pocket Balance
- Gateway Lifecycle and Messages
- Cardguard Plugin Tests
- Card Payments and Paid-by-Hand
- Living Money and Daily Account
- Payday Plan Builder (payday.py)
- Expense Corrections, Health and Mutations
- Service Entry Points and Locking
- Payees, Vault Secrets, Emergency Fund
- Runtime Map Collector
- Ledger Schema (v13 Tables)
- Debt Roadmap and Dates
- Pot Simulation and Schedule Consumers
- Makefile, Host Units and Backups
- Vault-Tools Image, Data and Notion Sync
- Vault-Tools Probe Script (probe_vault_tools.py)
- Zones, Containers and Squid
- Approvals and Change Proposals (M3)
- Vault Containers, MCP Server and Network
- Plan Invariants and Fee Checks
- Spending Analysis (Budget Baseline)
- MCP Server App and Tool Tests
- Egress Traffic and Containers (State)
- Holiday Fetch Decisions and Overrides
- Receipt Merge Rules and Resent Screenshots
- Notion Sync
- Sinking Fund Tests
- Gmail Ingest Client and Run
- Ledger Migrations and Backfills
- Zone Architecture and Security (M1-M4)
- Category Suggestions (suggest.py)
- Progress Hub: Bots, Zones and Milestones
- Auto-Debit Balance Checks
- One-Off Bill Placement Tests
- Host Probe Script (probe_host.py)
- Control Bot Approvals
- Hermes Agent Settings (Live)
- Card Installment Records and Tests
- Owner Names and Uploads
- Ledger Audit Tests
- Subscriptions
- Ledger, Deploys and Data-Fix Backups
- Recording Completeness Tests
- Runbook and Deploy (M1)
- Runtime Map Overview, Timers and Proxies
- Living Reserve Estimate
- Compose Secrets
- Balance Reports and Living Marks
- Open Questions, Calibration and Number Guard
- Statement PDF Intake and Sanitizing
- Hermes config.yaml (Repo)
- Report Rendering and HTML Tests
- Recalibration and Number Guard (1 Nov)
- Health Check and Verdicts
- Hermes Assumptions, Pin and Architecture
- Payday Plan Spec (Funding Order, Worked Example)
- Vault Bot SOUL and Owner Rules
- Payday Plan and Pot Tools (Usage)
- Compose Logging Options
- Compose Service: ingest-gmail
- Compose Service: vault-tools
- Calibration Runbook and Reviews
- Control Store and Proposal Files
- Ledger Categories and Thresholds
- Compose Service: control
- Compose Service: vault (Hermes)
- Weekly Docker Prune Script
- Budgets and Spending
- Living Money and Cash to Hold
- Front Compose Service
- Cashflow and Recurring Payments
- Graph-First Hook Tests
- Compose Service: squid-comms
- Compose Service: squid-ctl
- Compose Service: squid-front
- Compose Service: squid-vault
- Gmail OAuth and Sender Allowlist
- Debts, Balances and Proposals (State)
- Cardguard Number Guard Hooks
- Graph-First Prompt Hook
- Upload Sync Tests
- Ledger Tables and Backups (State Snapshot)
- Cardguard Telegram Fallback Tests
- Deploy 2 Data Fix
- MCP Server Security Tests
- Compose Networks
- Compose Squid Template
- Card Statements, Payment Targets and Reports
- Host Runtime and Firewall
- Change-Proposal Submission Tests
- Hermes Auxiliary Models
- Hermes MCP Server Config
- Change-Proposals Compose Service
- Host Scripts (Holidays, PDF Passwords, Gmail Auth)
- Corrected Source Merge Tests
- Hermes Credentials Boundary
- State Snapshot: Timers, Jobs and Restic
- Hermes Telegram Access Settings (Live)
- Cardguard Telegram Menu
- Server Flow Tests
- Payday Plan, Recalibration and Living Reserve
- 30 Oct Payday Data, Plans and Auto-Debits
- Kanban Store Tables (Unused)
- Payday Progress Tool Tests
- Compose Environment Settings
- Zone Isolation Tests
- Pot Schedule Engine
- Number Guard Tests
- Receipt Merge Tests
- Front Hermes Config
- Gmail Token Check Tests
- Hermes Telegram Gateway Config
- Report HTML Tag Balance Tests
- Admin Fee Invariant Tests
- Hermes Agent Block
- Hermes Memory Settings
- Cardguard Plugin Manifest
- WIB Date Tests
- Hermes Session Store (state.db)
- Receipt Merges and Record Fixes
- Front Auxiliary Models
- Vault Env Renderer
- Front Change-Proposals MCP
- Payday Plan Generation and Advice
- Front Agent Persona and Setup
- Service Images and Data Root
- Front Telegram Chat Filter
- Squid Egress Allowlists
- Front Memory Settings
- Vault Tools Module (tools.py)
- Session Compaction and Resets
- Front Agent Limits
- Runtime Map Hashing and Masking Tests
- Calibration Change-and-Verify Steps
- Pace-Fix Deploy Script (31 Oct)
- Pocket-Balance Deploy Script (1 Nov)
- Recalibration Deploy Script (1 Nov)
- Front Model Setting
- Front Tool Search Setting
- Vault Tool Search Setting
- Secrets Handling
- Data Dirs Script
- Front Env Render Script
- Accounts, Debts and Auto-Debits
- Hermes Vault Engine Install
- Daily Account Re-Anchor (saldo_rekening)
- Fixed Expenses and Children's Fees
- Periksa Data Checks
- Telegram Adapter Health
- Telegram Delivery and Cold Boot
- Vault Commands and Payday Flows
- Ingest Inputs
- Payee Secrets and Sinking Funds
- Hermes Config Key Walker
- Data Dirs and Upload Relay
- Receipt Vision and Purchase Tools
- Stack Settings and Host Checks
- Funding Order and Admin Fees
- Daily Money Rules (Leftover and Top-Up)
- Scheduled No-LLM Jobs
- Preflight Script
- Backup Script
- Disk Check Script
- Vault Model Setting
- Timer Install Script
- Secret Generation Script
- Secret Set Script
- Upload Sync Script
- Deploy 2 Script
- Hermes Socket Probes
- Money Formatting and Fee Lines
- PDF Password Collect Tests
- PDF Password In-Place Rewrite

## God Nodes (most connected - your core abstractions)
1. `generate_payday_plan()` - 106 edges
2. `create_app()` - 98 edges
3. `format_idr()` - 93 edges
4. `connect()` - 84 edges
5. `Bot activity snapshot` - 72 edges
6. `MCP server vault_tools (57 tools at http://vault-tools:8000/mcp, named mcp__vault_tools__<name> for the model)` - 65 edges
7. `PayeeVault` - 58 edges
8. `simulate()` - 56 edges
9. `set_threshold()` - 51 edges
10. `edit_expense()` - 41 edges

## Surprising Connections (you probably didn't know these)
- `Hitting a limit: catat_usulan, then sudah kucatat di /usulan` --semantically_similar_to--> `/usulan (posts the waiting proposals again with their buttons)`  [AMBIGUOUS] [semantically similar]
  services/hermes/vault/SOUL.md → docs/RUNBOOK.md
- `/mcp surface (model-facing; aliases and amounts only, no tool stores or reveals a full number)` --semantically_similar_to--> `Security and data rules (no re-reading recorded documents, max 2 reads per answer, alias plus last 4 digits only, no CVV or expiry, no URLs)`  [INFERRED] [semantically similar]
  docs/SECURITY.md → services/hermes/vault/SOUL.md
- `/rincian handled in pre_gateway_dispatch with skip plus direct Bot API send` --semantically_similar_to--> `/rincian (destination numbers grouped per destination; the only place full numbers appear)`  [INFERRED] [semantically similar]
  docs/ARCHITECTURE.md → services/hermes/vault/SOUL.md
- `A rejected submit is fixed per its reason, never gamed; new services, host scripts, plugins and secret values are the owner's own work` --semantically_similar_to--> `Never in a proposal: host scripts, compose, plugins, control itself, secrets (new service = escalation; secret via make secret-set); at most five wait`  [INFERRED] [semantically similar]
  services/hermes/front/SOUL.md → docs/SECURITY.md
- `No long-term memory; financial data stored only via vault_tools` --references--> `vault-tools (vault zone tool service)`  [INFERRED]
  services/hermes/vault/SOUL.md → docs/ARCHITECTURE.md

## Import Cycles
- 2-file cycle: `services/vault-tools/vault_tools/roadmap.py -> services/vault-tools/vault_tools/simulate.py -> services/vault-tools/vault_tools/roadmap.py`
- 2-file cycle: `services/vault-tools/vault_tools/simulate.py -> services/vault-tools/vault_tools/tools.py -> services/vault-tools/vault_tools/simulate.py`
- 3-file cycle: `services/vault-tools/vault_tools/roadmap.py -> services/vault-tools/vault_tools/tools.py -> services/vault-tools/vault_tools/simulate.py -> services/vault-tools/vault_tools/roadmap.py`

## Hyperedges (group relationships)
- **Calibration deploy flow (rsync, ledger backup, rebuild, data scripts, restart and /new)** — docs_calibration_rsync_step, docs_calibration_ledger_backup, docs_calibration_compose_rebuild, docs_calibration_data_change_scripts, docs_calibration_restart_vault, docs_calibration_new_command [EXTRACTED 1.00]
- **Admin fee accounting in the payday plan (estimated fees once per destination, paid with their payment, listed apart, inside the salary invariant, counted from biaya_admin_mulai, estimated in the simulation)** — docs_payday_admin_fees, docs_payday_biaya_admin_kartu, docs_payday_biaya_admin_transfer, docs_payday_biaya_admin_alias, docs_payday_no_fee_payments, docs_payday_fee_paid_with_payment, docs_payday_fee_once_per_destination, docs_payday_fees, docs_payday_fee_salary_invariant, docs_payday_biaya_admin_mulai, docs_payday_fee_estimate, docs_payday_cash_to_hold [EXTRACTED 1.00]
- **Bill paid once lifecycle (recorded on the server's day, funded as an essential or overdue item in the first plan whose window reaches its due date, marked paid, or recorded as an expense when already paid)** — docs_payday_tagihan_sekali, docs_payday_bills_paid_once, docs_payday_recorded_on, docs_payday_first_plan_rule, docs_payday_late_recorded_bill, docs_payday_transfer_selesai, docs_payday_bill_paid_is_expense, docs_payday_essentials_tier, docs_payday_overdue_tier [EXTRACTED 1.00]
- **Payday funding tiers 0 to 5 in strict order** — docs_payday_funding_order, docs_payday_overdue_tier, docs_payday_card_minimum_tier, docs_payday_essentials_tier, docs_payday_debt_and_pool_tier, docs_payday_card_balance_tier, docs_payday_savings_tier [EXTRACTED 1.00]
- **Living money accounting and re-anchoring from the daily account balance** — docs_payday_living_money, docs_payday_cash_to_hold, docs_payday_living_leftover, docs_payday_living_leftover_spent, docs_payday_set_leftover_living_cash, docs_payday_saldo_rekening, docs_payday_health_living_anchor, docs_payday_living_anchor_rule, docs_payday_anchor_correction [EXTRACTED 1.00]
- **Accuracy layers that keep the bot's numbers correct** — docs_progress_invariants_self_checks, docs_progress_property_tests, docs_progress_number_guard, docs_progress_duplicate_expense_rule [EXTRACTED 1.00]
- **M3 approval flow (front asks, control posts, the owner taps, the applier would apply)** — docs_progress_front_agent, docs_progress_change_proposals, docs_progress_submit_tool, docs_progress_proposals_inbox, docs_progress_control_v2, docs_progress_control_state, docs_progress_applier [EXTRACTED 1.00]
- **Own-record merge rules (same bank, coverage gate, merged duplicates, correction, lepas, cash never merges)** — docs_progress_merge_receipts_same_bank, docs_progress_record_merge_coverage_gate, docs_progress_duplicate_check_merged, docs_progress_merged_record_correction, docs_progress_lepas_unmerge, docs_progress_cash_never_merges_tunai, docs_progress_id_reuse_fix_45dfc1e [EXTRACTED 1.00]
- **Vault zone on internal net-vault: Hermes gateway, vault-tools MCP server and squid-vault** — docs_runtime_containers_personal_agent_vault_1, docs_runtime_containers_personal_agent_vault_tools_1, docs_runtime_containers_personal_agent_squid_vault_1, docs_runtime_containers_personal_agent_net_vault, docs_runtime_vault_tools_mcp_server [EXTRACTED 1.00]
- **Plan and pot computed from the pre-salary state (usulan #9 and #10)** — docs_runtime_state_usulan_9, docs_runtime_state_usulan_10, docs_runtime_state_pre_salary_baseline, docs_runtime_state_pot_simulation, docs_runtime_state_tunda_pot_bulan, docs_runtime_state_rincian_rencana_commands, docs_runtime_state_payday_plan [EXTRACTED 1.00]
- **restic backup lifecycle through backup.sh (daily backup, monthly integrity check, weekly retention)** — docs_runtime_timers_pa_backup, docs_runtime_timers_pa_check, docs_runtime_timers_pa_forget, docs_runtime_timers_backup_sh, docs_runtime_timers_restic [EXTRACTED 1.00]
- **M3 change approval chain (front submit, change-proposals, proposals-inbox, control decides on the owner's tap, applier later)** — services_hermes_front_soul_submit_tool, docs_security_change_proposals, docs_architecture_proposals_inbox, docs_security_only_control_decides, docs_architecture_control_state, docs_security_applier_contract [EXTRACTED 1.00]
- **Payday cycle on the 1st (status_gajian, sisa_uang_harian, generate_payday_plan, periksa_data, recording tools, saldo_rekening)** — services_hermes_vault_soul_payday_list_flow, services_hermes_vault_soul_status_gajian, services_hermes_vault_soul_sisa_uang_harian, services_hermes_vault_soul_generate_payday_plan, services_hermes_vault_soul_periksa_data, services_hermes_vault_soul_payday_recording_tools, services_hermes_vault_soul_saldo_rekening [EXTRACTED 1.00]
- **Per-zone squid proxies are the only members of the egress network** — docs_architecture_squid_vault, docs_architecture_squid_front, docs_architecture_squid_comms, docs_architecture_squid_ctl, docs_architecture_egress_network [EXTRACTED 1.00]
- **Statement import tool flow** — docs_runtime_bot_activity_list_uploads, docs_runtime_bot_activity_pending_statements, docs_runtime_bot_activity_ingest_statement, docs_runtime_bot_activity_skip_statement_file, docs_runtime_bot_activity_record_statement, docs_runtime_bot_activity_list_statements, docs_runtime_bot_activity_record_mutations, docs_runtime_bot_activity_record_card_installments [INFERRED 0.75]
- **Marking payday-plan payments as done by kind (cards, debt installments, other transfers, one-off bills), read back by status_gajian** — docs_runtime_hermes_record_card_payment, docs_runtime_hermes_cicilan_dibayar, docs_runtime_hermes_transfer_selesai, docs_runtime_hermes_tagihan_sekali, docs_runtime_hermes_status_gajian, docs_runtime_hermes_generate_payday_plan [INFERRED 0.75]
- **Front zone provisioned ahead of its bot: anthropic_front_key and telegram_front_token secrets, empty hermes-front data dir, squid-front alone on net-front** — docs_runtime_host_secret_anthropic_front_key, docs_runtime_host_secret_telegram_front_token, docs_runtime_host_hermes_front_dir, docs_runtime_containers_personal_agent_squid_front_1, docs_runtime_containers_personal_agent_net_front, docs_runtime_proxies_squid_front [INFERRED 0.75]
- **Weekly prune removes the idle ingest-gmail image and the next daily ingest rebuilds it** — docs_runtime_state_pa_prune, docs_runtime_state_docker_prune_log, docs_runtime_state_ingest_gmail_image_build, docs_runtime_state_pa_ingest, docs_runtime_state_ingest_gmail_container [INFERRED 0.75]
- **Morning statement ingest (06:00 WIB) followed by the Notion snapshot (06:30 WIB) from vault-tools through squid-vault** — docs_runtime_timers_pa_ingest, docs_runtime_timers_ingest_gmail, docs_runtime_timers_pa_notion, docs_runtime_timers_vault_tools_notion_sync, docs_runtime_timers_personal_agent_vault_tools_1, docs_runtime_proxies_api_notion_com, docs_runtime_proxies_squid_vault [INFERRED 0.75]
- **Deploy 2 on the live ledger (2026-11-01): pre-deploy2 backup, schema user_version 14 with the new one_off_bills table, biaya_admin_* thresholds, vault-tools image rebuilt 10:26 WIB** — docs_runtime_vault_tools_ledger_bak_pre_deploy2, docs_runtime_vault_tools_ledger_db, docs_runtime_vault_tools_table_one_off_bills, docs_runtime_vault_tools_threshold_biaya_admin, docs_runtime_vault_tools_ledger_py, docs_runtime_host_image_personal_agent_vault_tools, docs_runtime_containers_personal_agent_vault_tools_1 [INFERRED 0.75]
- **Daily money computation (top-up plus leftover, anchored by the daily-account reading)** — docs_progress_payday_living_money, docs_progress_cash_to_hold, docs_progress_living_leftover_spent, docs_progress_living_account_constant, docs_progress_living_balance_report, docs_progress_living_balance_mark, docs_progress_spending_pace, docs_progress_uang_harian_bulan_ini [INFERRED 0.85]
- **Deploy 2 delivered across the progress log, the payday spec and SOUL (admin fees, bills paid once, instalment undo, grace period, data fix, schema 14)** — docs_progress_deploy_2, docs_progress_admin_fees, docs_progress_tagihan_sekali, docs_progress_cicilan_dibayar_batal, docs_progress_stop_grace_period, docs_progress_deploy_2_data_fix, docs_progress_schema_v14_one_off_bills, docs_progress_deploy_2_deploy, docs_payday_admin_fees, docs_payday_bills_paid_once, services_hermes_vault_soul_admin_fees, services_hermes_vault_soul_tagihan_sekali, services_hermes_vault_soul_cicilan_dibayar_batal [INFERRED 0.85]
- **Payday progress records (schema v13 tables and the tools that write and read them)** — docs_progress_schema_v13_payment_tables, docs_progress_card_payments_table, docs_progress_debt_payments_table, docs_progress_plan_progress_table, docs_progress_fund_reports_table, docs_progress_status_gajian, docs_progress_transfer_selesai, docs_progress_cicilan_dibayar [INFERRED 0.85]
- **Pot planning flow (schedule, pattern, simulator, plan, roadmap)** — docs_progress_pot_hutang_teman, docs_progress_pot_schedule, docs_progress_atur_jadwal_pot, docs_progress_pot_pattern_sisa, docs_progress_simulasi_skenario, docs_progress_payday_plan, docs_progress_roadmap [INFERRED 0.85]
- **Context compression machinery** — docs_runtime_bot_activity_context_compression, docs_runtime_bot_activity_preflight_compression, docs_runtime_bot_activity_pre_api_compression, docs_runtime_bot_activity_compression_blocked, docs_runtime_bot_activity_session_compressed_warning, docs_runtime_bot_activity_auxiliary_compression_model, docs_runtime_bot_activity_sessions_compression_columns, docs_runtime_bot_activity_busy_input_mode, docs_runtime_bot_activity_compression_reply_anchor [INFERRED 0.85]
- **Gateway SIGTERM shutdown and revive cycle** — docs_runtime_bot_activity_gateway_restart_lifecycle, docs_runtime_bot_activity_s6_supervise, docs_runtime_bot_activity_shutdown_phases, docs_runtime_bot_activity_shutdown_notification, docs_runtime_bot_activity_gateway_state_persist, docs_runtime_bot_activity_container_boot_log, docs_runtime_bot_activity_gateway_shutdown_diag_log, docs_runtime_bot_activity_unclean_previous_life [INFERRED 0.85]
- **Numbers computed by code, never by the model** — docs_runtime_hermes_periksa_data, docs_runtime_hermes_generate_payday_plan, docs_runtime_hermes_simulasi_skenario, docs_runtime_hermes_belanja_kartu, docs_runtime_hermes_health_check, docs_runtime_hermes_cashflow_summary [INFERRED 0.85]
- **Full card and account numbers kept out of the bot (tokens, alias plus last 4 digits)** — docs_runtime_hermes_cardguard_plugin, docs_runtime_hermes_upsert_card, docs_runtime_hermes_upsert_account, docs_runtime_hermes_list_payees [INFERRED 0.85]
- **Statement intake: Telegram uploads and the ingest-gmail queue into recorded statements and transactions** — docs_runtime_hermes_list_uploads, docs_runtime_hermes_uploads_cache, docs_runtime_hermes_ingest_statement, docs_runtime_hermes_record_statement, docs_runtime_hermes_record_mutations, docs_runtime_hermes_pending_statements, docs_runtime_hermes_skip_statement_file, docs_runtime_hermes_ingest_events, docs_runtime_hermes_ingest_gmail_job [INFERRED 0.85]
- **Secret provisioning path (entered or generated on the VPS, kept in the secrets dir, mounted as compose secrets)** — docs_runtime_infra_files_make_secret_set, docs_runtime_infra_files_make_secret_gen, docs_runtime_infra_files_make_pdf_passwords, docs_runtime_infra_files_plaintext_secrets_stay_on_vps, docs_runtime_host_opt_personal_agent_secrets, docs_runtime_host_compose_secrets_mount [INFERRED 0.85]
- **restic backup lifecycle (backup, integrity check, retention of the data dir)** — docs_runtime_infra_files_host_pa_backup, docs_runtime_infra_files_host_pa_check, docs_runtime_infra_files_host_pa_forget, docs_runtime_infra_files_scripts_backup_sh, docs_runtime_infra_files_make_backup, docs_runtime_host_opt_personal_agent_data, docs_runtime_host_secret_restic_env [INFERRED 0.85]
- **Telegram upload relay flow (Hermes document cache to the ingest folder, 90-day retention)** — docs_runtime_infra_files_hermes_vault_document_cache, docs_runtime_infra_files_host_pa_uploads, docs_runtime_infra_files_scripts_sync_uploads_sh, docs_runtime_infra_files_upload_retention_90_days, docs_runtime_host_hermes_vault_dir, docs_runtime_host_ingest_dir [INFERRED 0.85]
- **Live-vs-repo drift checks made by the runtime map collector (deployed files, systemd units, squid configs)** — docs_runtime_readme_collect_py, docs_runtime_readme_deploy_drift, docs_runtime_timers_live_vs_repo_unit_drift, docs_runtime_proxies_live_configs_match_repo [INFERRED 0.85]
- **Deploy 2: admin fees and one-off bills shipped (usulan #4 and #6)** — docs_runtime_state_deploy_2, docs_runtime_state_usulan_4, docs_runtime_state_usulan_6, docs_runtime_state_admin_fee_estimate, docs_runtime_state_tagihan_sekali, docs_runtime_state_one_off_bills_table, docs_runtime_state_backup_pre_deploy2, docs_runtime_state_payday_plan [INFERRED 0.85]
- **Daily Gmail statement ingest path (pa-ingest, ingest-gmail run, squid-vault, Google APIs)** — docs_runtime_state_pa_ingest, docs_runtime_state_ingest_gmail_container, docs_runtime_state_squid_vault, docs_runtime_state_gmail_googleapis_com, docs_runtime_state_oauth2_googleapis_com, docs_runtime_state_pa_gmail_token, docs_runtime_state_doc_files_table, docs_runtime_state_processed_messages_table [INFERRED 0.85]
- **Autodebit debts paid manually before the debit date (usulan #5, #7, #8)** — docs_runtime_state_usulan_5, docs_runtime_state_usulan_7, docs_runtime_state_usulan_8, docs_runtime_state_autodebit, docs_runtime_state_spaylater_debt, docs_runtime_state_car_instalment_debt, docs_runtime_state_debt_payments_table, docs_runtime_state_held_balance [INFERRED 0.85]
- **restic check and retention locked out at 04:00 on 2026-11-01** — docs_runtime_state_pa_check, docs_runtime_state_pa_forget, docs_runtime_state_restic_repo_lock, docs_runtime_state_restic_backup, docs_runtime_state_restic_check_temp_cache, docs_runtime_state_restic_cache_warning, docs_runtime_state_host_timers [INFERRED 0.85]
- **Encrypted payee secrets: payee_secrets nonce, ciphertext and match_hash with vault_tools_key and cryptography** — docs_runtime_vault_tools_table_payee_secrets, docs_runtime_containers_secret_vault_tools_key, docs_runtime_vault_tools_cryptography_package [INFERRED 0.85]
- **Statement ingest: ingest-gmail and pa-uploads fill /ingest, PDFs become statements and mutation files** — docs_runtime_vault_tools_ingest_gmail, docs_runtime_vault_tools_pa_uploads, docs_runtime_vault_tools_ingest, docs_runtime_vault_tools_pdf_parsing_packages, docs_runtime_vault_tools_table_doc_files, docs_runtime_vault_tools_table_statements, docs_runtime_vault_tools_table_mutation_files [INFERRED 0.85]

## Communities (189 total, 32 thin omitted)

### Community 0 - "Card Statement Line Parsing"
Cohesion: 0.05
Nodes (34): Accuracy, add_statement(), Amounts, card_world(), Classify, Parsing, PerCard, Recovery (+26 more)

### Community 1 - "Hermes Runtime Probes"
Cohesion: 0.12
Nodes (29): activity(), config(), day(), db_profile(), defaults_module(), engine(), fkind(), flatten() (+21 more)

### Community 3 - "Cardguard Plugin and Control Bot"
Cohesion: 0.21
Nodes (16): _bot(), _chunks(), _delete_async(), _digits_of(), find_numbers(), _luhn(), _notify(), on_inbound() (+8 more)

### Community 4 - "Payday Calendar and Holidays"
Cohesion: 0.10
Nodes (11): PaydayWindow, Holidays, card_charges(), commitments(), next_payday(), horizon(), pot_projection(), current_payday() (+3 more)

### Community 5 - "Ledger Database and Tables (Runtime)"
Cohesion: 0.13
Nodes (27): bca-9706 (bca card; statement day 12, due day 28, transfer to num-9706), cimb-9888 (cimb card; statement day 19, due day 7, transfer to num-9888), dbs-5685 (DBS card; statement day 25, due day 10, transfer to num-5685), hsbc-5915 (HSBC card; statement day 19, due day 4, transfer to num-5915), mandiri-4365 (mandiri card; statement day 16, due day 5, paid via app_menu), mega-5855 (Mega card; statement day 22, due day 7, transfer to num-5855), SQLite ledger /data/ledger.db (schema user_version 14, WAL journal), ledger-schema.sql (ledger DDL) (+19 more)

### Community 6 - "Report Renderers (reports.py)"
Cohesion: 0.28
Nodes (19): _anggaran(), b(), _banks(), _belanja(), bln(), _cicilan(), _data(), e() (+11 more)

### Community 7 - "Shared Imports and Ledger Connections"
Cohesion: 0.14
Nodes (4): CardPath, LatestStatement, EmergencyFund, PendingStatements

### Community 8 - "Bills Paid Once and Payday Dates"
Cohesion: 0.07
Nodes (27): random_world(), rupiah(), PaydayDates, bp_of(), check_idr(), cancel(), describe(), first_plan() (+19 more)

### Community 9 - "Live MCP Tool Catalog"
Cohesion: 0.08
Nodes (57): add_owner_name (add the owner's name exactly as printed in account transactions), apply_suggestions (apply category suggestions for the named descriptions; empty applies all), atur_jadwal_pot (set how a pot, an earmarked fund with a deadline, is filled), Bank admin fees (estimates given by the owner, kept as thresholds through set_threshold), belanja_kartu (card spending breakdown per cycle from statement lines already read by code; never read the PDF for this), budget_status (budget use per category for a month, default the current one), card_installments_status (running card installments: x of y, months left and total remaining), cashflow_summary (monthly cash flow: income, spending, difference, savings ratio, per category; computed by code) (+49 more)

### Community 10 - "Bot Tool Usage (state.db)"
Cohesion: 0.04
Nodes (69): Bot activity snapshot, mcp__vault_tools__add_owner_name, mcp__vault_tools__apply_suggestions, mcp__vault_tools__atur_jadwal_pot, Vault tool names called without the MCP prefix, mcp__vault_tools__belanja_kartu, mcp__vault_tools__budget_status, mcp__vault_tools__card_installments_status (+61 more)

### Community 11 - "Bank Mutations and Category Rules"
Cohesion: 0.21
Nodes (9): acct_db(), Mutations, rows(), format_cashflow(), _purge_file(), record_mutations(), set_category_rule(), record_mutations() (+1 more)

### Community 12 - "Hermes Home, Stores and Skills"
Cohesion: 0.05
Nodes (62): runtime/active_sessions.json (active-session entries), logs/agent.log (INFO and above: 9 ERROR, 454 WARNING, 738 distinct templates), api_server platform (OpenAI-compatible, 127.0.0.1:8642, reachable only inside the container; connected, no requests), Bundled Hermes skills (12 categories; the skills toolset is disabled, so the model cannot load them), cardguard plugin v0.1 (replaces card numbers in inbound Telegram text with tokens before dispatch; spike), cardguard TTL file (ttl/rincian.jsonl: /rincian messages to delete after expiry; 0 lines), logs/container-boot.log (boot diagnostics, 61 lines), cron/executions.db executions table (0 rows) (+54 more)

### Community 13 - "Living Money Pace and Pocket Balance"
Cohesion: 0.21
Nodes (3): LivingMoneyPace, record_expense(), spending_pace()

### Community 14 - "Gateway Lifecycle and Messages"
Cohesion: 0.07
Nodes (36): Agent budget: max_iterations=40, agent.deadline: task timed out and abandoned, logs/agent.log, cardguard capability_check: tools.override denied, cardguard number guard (amounts not from the tools), Config migration skipped (hermes_cli.post_update), logs/container-boot.log, Conversation loop API calls and turn re-anchoring (+28 more)

### Community 15 - "Cardguard Plugin Tests"
Cohesion: 0.13
Nodes (3): CardGuard, text(), ev()

### Community 16 - "Card Payments and Paid-by-Hand"
Cohesion: 0.08
Nodes (15): UndoInstalment, CardPayment, Instalments, pay_as_on_30_oct(), plan_of(), Progress, stmt(), world() (+7 more)

### Community 17 - "Living Money and Daily Account"
Cohesion: 0.14
Nodes (12): amounts(), bill(), LeftoverLivingCash, ReserveAndPot, full_world(), fund_buffer_days(), _low_cycles(), set_leftover_living_cash() (+4 more)

### Community 18 - "Payday Plan Builder (payday.py)"
Cohesion: 0.08
Nodes (18): BuildPlan, fixed(), amounts_of(), Engine, Masking, dummy(), Masking, Properties (+10 more)

### Community 19 - "Expense Corrections, Health and Mutations"
Cohesion: 0.08
Nodes (23): Edit, log(), OnlyTheOwnersRecords, alerts_for(), delete_expense(), edit_expense(), _give(), _given() (+15 more)

### Community 20 - "Service Entry Points and Locking"
Cohesion: 0.06
Nodes (9): _Auth, create_app(), main(), ProposedFile, _subkey(), _Auth, Installment, locked() (+1 more)

### Community 21 - "Payees, Vault Secrets, Emergency Fund"
Cohesion: 0.09
Nodes (14): DailyAccount, Emergency, LinkPayees, Vault, Rincian, _norm(), PayeeVault, _bank() (+6 more)

### Community 22 - "Runtime Map Collector"
Cohesion: 0.16
Nodes (29): amounts(), cell(), deep_scrub(), engine_refs(), fence(), header(), listener_note(), local_tree() (+21 more)

### Community 23 - "Ledger Schema (v13 Tables)"
Cohesion: 0.08
Nodes (34): accounts, balance_reports, card_installment_scans, card_installments, card_lines, card_payments, cards, category_keywords (+26 more)

### Community 24 - "Debt Roadmap and Dates"
Cohesion: 0.12
Nodes (13): world(), Dates, Roadmap, statement(), world(), add_months(), _clamp(), format_roadmap() (+5 more)

### Community 25 - "Pot Simulation and Schedule Consumers"
Cohesion: 0.11
Nodes (10): PlanStaysAfterPaying, Consumers, CardsFirstPot, Simulate, simulasi_skenario(), _bln(), format_result(), verdict() (+2 more)

### Community 26 - "Makefile, Host Units and Backups"
Cohesion: 0.10
Nodes (27): Docker disk use (5 images, 7 containers, 8 local volumes, 125 build cache entries), pdf_passwords secret, .gitignore (decrypted secrets, keys, .env, .claude, graphify-out), graphify-out/ shared project map (graph.json, GRAPH_REPORT.md, manifest.json, cost.json, labels), pa-prune.service + timer (weekly Docker cleanup that never touches volumes, Sun 03:00 WIB), make backup (starts pa-backup.service now and shows its journal), make deploy (rsync to the VPS, install timers, data dirs, compose up --build), make graph (AST-only graphify update, no LLM cost) (+19 more)

### Community 27 - "Vault-Tools Image, Data and Notion Sync"
Cohesion: 0.24
Nodes (11): notion_token secret, vault-tools data dir (mode 0700), api.notion.com (vault allowlist, for vault-tools), pa-holidays.service + timer (cuti bersama / holiday refresh for vault-tools, 1st at 06:30 WIB), ledger.db (LEDGER_DB=/data/ledger.db in vault-tools), make test (python -I unittest for the repo and the control, change-proposals, ingest-gmail, vault-tools services), scripts/fetch-cuti.py (cuti bersama / holiday fetcher), services/vault-tools/Dockerfile (vault-tools server image with LEDGER_DB and a healthcheck) (+3 more)

### Community 28 - "Vault-Tools Probe Script (probe_vault_tools.py)"
Cohesion: 0.18
Nodes (12): cuti(), data_files(), day(), fkind(), fname(), free(), ledger(), money_free() (+4 more)

### Community 29 - "Zones, Containers and Squid"
Cohesion: 0.14
Nodes (28): Anonymous squid log and spool volumes (8, from image VOLUME lines), cap_drop ALL (control, the four squids, vault-tools; vault has none), Compose project personal-agent (compose/docker-compose.yml), control.py (python -I control.py, workdir /app), Control env (MY_TELEGRAM_ID value masked, TELEGRAM_TOKEN_FILE, PROPOSALS_INBOX_DIR, CONTROL_STATE_DIR), Hermes Telegram env (TELEGRAM_BOT_TOKEN; TELEGRAM_ALLOWED_USERS and TELEGRAM_HOME_CHANNEL values masked), ubuntu/squid:6.6-24.04_edge image (all four squid containers), json-file logs, max-size 10m, max-file 3 (every container) (+20 more)

### Community 30 - "Approvals and Change Proposals (M3)"
Cohesion: 0.09
Nodes (25): Approvals flow (M3): front submit -> proposals-inbox -> control re-validates and posts -> owner's tap recorded, change-proposals (front zone, M3, submit tool), front (Hermes on Haiku, compose profile front, started once the owner's front secrets exist), Front zone (general and web, net-front), notion-mcp (front zone, later), proposals-inbox folder (change-proposals writes, control reads and empties it), sandbox (front zone, later), One-time Setujui/Tolak buttons (+17 more)

### Community 31 - "Vault Containers, MCP Server and Network"
Cohesion: 0.11
Nodes (27): cardguard plugin (services/hermes/vault/plugins/cardguard, read-only at /opt/data/plugins/cardguard), Containers runtime map (compose project personal-agent), ANTHROPIC_API_KEY (vault env name), Hermes path env (HERMES_HOME and HERMES_WRITE_SAFE_ROOT /opt/data, HERMES_PYTHON, HERMES_RUNTIME_DIR, HERMES_TUI_DIR, HERMES_WEB_DIST, PLAYWRIGHT_BROWSERS_PATH, XDG_RUNTIME_DIR), HERMES_SKIP_CONFIG_MIGRATION=1 (vault env), LEDGER_DB=/data/ledger.db (vault-tools env), TZ (vault Asia/Jakarta; squids UTC), vault NO_PROXY: localhost, 127.0.0.1, vault-tools (+19 more)

### Community 32 - "Plan Invariants and Fee Checks"
Cohesion: 0.08
Nodes (12): bills_of(), fees_world(), Gate, Plan, Rule, Simulation, TheChecksCatchBrokenNumbers, CalculationError (+4 more)

### Community 33 - "Spending Analysis (Budget Baseline)"
Cohesion: 0.20
Nodes (9): Analysis, Monthly, tx(), world(), analyse(), format_analysis(), monthly(), _round_up() (+1 more)

### Community 34 - "MCP Server App and Tool Tests"
Cohesion: 0.03
Nodes (34): Rincian, Rincian, ThroughTheTools, ThroughTheTools, make_pdf(), ThroughTheTools, ThroughTheTools, Tools (+26 more)

### Community 35 - "Egress Traffic and Containers (State)"
Cohesion: 0.12
Nodes (29): api.anthropic.com (Anthropic API; 1037 requests via squid-vault), api.notion.com (Notion API; 370 requests via squid-vault), api.telegram.org (Telegram Bot API; 52846 requests via squid-vault, 9153 via squid-ctl), Containers now: 7 running, 0 restarts, no OOM, exit 0, control container (personal-agent-control-1; running since 2026-10-31, 5 log lines in 7 days), control container warning: getUpdates failed (5 in 7 days), Denied: dns.google and cloudflare-dns.com (63 requests each), Denied: link-local cloud metadata endpoint (18 requests) (+21 more)

### Community 36 - "Holiday Fetch Decisions and Overrides"
Cohesion: 0.13
Nodes (10): Decide, Override, Parse, candidate_days(), decide(), load_year(), merge_file(), parse_github() (+2 more)

### Community 37 - "Receipt Merge Rules and Resent Screenshots"
Cohesion: 0.17
Nodes (3): _Banks, LateRecordsAndResentScreenshots, MergeRules

### Community 38 - "Notion Sync"
Cohesion: 0.11
Nodes (19): FakeNotion, Sync, bullet(), heading(), main(), Notion, NotionError, para() (+11 more)

### Community 39 - "Sinking Fund Tests"
Cohesion: 0.20
Nodes (8): fund(), InThePlan, Math, row(), setup(), Validation, set_category(), set_category()

### Community 40 - "Gmail Ingest Client and Run"
Cohesion: 0.05
Nodes (23): auth_ok(), _clauses(), from_address(), safe_label(), GmailClient, GmailError, TokenError, Config (+15 more)

### Community 41 - "Ledger Migrations and Backfills"
Cohesion: 0.07
Nodes (12): Migration, Migration, ThroughTheTools, RandomLedgers, Ledger, Migration, Fund, UsulanReport (+4 more)

### Community 42 - "Zone Architecture and Security (M1-M4)"
Cohesion: 0.09
Nodes (33): Architecture (M1 skeleton), Applier (applies approved changes; not built yet), brokers (comms zone, M4), card-bus MCP (replaces Kanban, M4), Comms zone (email and calendar, net-comms; comms, brokers, card-bus in M4), Control commands /status (counts), /usulan (re-post waiting proposals), /ping, control-state folder (control only; decided/, approved/ read later by the applier), Control zone and control service (approvals, no LLM, net-ctl) (+25 more)

### Community 43 - "Category Suggestions (suggest.py)"
Cohesion: 0.10
Nodes (13): Suggestions, normalize(), set_category_keyword(), add_owner_name(), apply_suggestions(), set_category_keyword(), suggest_categories(), add_owner_name() (+5 more)

### Community 44 - "Progress Hub: Bots, Zones and Milestones"
Cohesion: 0.08
Nodes (39): allowed_chats: none (both Hermes configs; drops every group, keeps DMs), api.notion.com (allowed through squid-vault), Applier (writes, commits, deploys and health-checks an approved change; deferred), Vault bot token rotation (2026-10-28), BotFather Allow Groups (owner turns it off for the vault and control bots), Branch worktree-m1-skeleton, draft PR #1, catat_usulan and /usulan (feature requests), change-proposals MCP server (front's one way to ask for a change; runs only with front) (+31 more)

### Community 45 - "Auto-Debit Balance Checks"
Cohesion: 0.12
Nodes (10): BalanceCheck, car(), InThePlan, Rules, setup(), seeded(), Tools, record_account_balance() (+2 more)

### Community 46 - "One-Off Bill Placement Tests"
Cohesion: 0.14
Nodes (12): amounts(), bill_world(), catat(), Flows, Placement, Simulation, _carried(), _kind_text() (+4 more)

### Community 47 - "Host Probe Script (probe_host.py)"
Cohesion: 0.15
Nodes (21): containers(), deployed_tree(), docker_logs(), images(), listening(), mixed(), networks(), opt_layout() (+13 more)

### Community 48 - "Control Bot Approvals"
Cohesion: 0.07
Nodes (19): submit(), card(), Control, handle(), is_authorized(), main(), path_allowed(), quiet() (+11 more)

### Community 49 - "Hermes Agent Settings (Live)"
Cohesion: 0.11
Nodes (20): agent.reasoning_effort high (not in DEFAULT_CONFIG; a per-model override would win), auxiliary.compression: claude-sonnet-5-5 via anthropic (default auto), auxiliary config section (139 keys; our compression, title_generation and vision models on anthropic), auxiliary.title_generation: claude-haiku-5-5 via anthropic (default auto), Proposed skill card-spend-breakdown-advisory (productivity, created 2026-10-28, pending approval), catat_usulan (record a proposal when the bot hits a limit: a missing tool, calculation or command, instead of a workaround), clarify engine tool, Hermes config backups (backups/config.yaml.good.*, five from 2026-10-28 to 2026-11-01) (+12 more)

### Community 50 - "Card Installment Records and Tests"
Cohesion: 0.15
Nodes (11): Installments, OneCardOneAlias, Overview, world(), active(), _add_months(), format_list(), monthly_total() (+3 more)

### Community 51 - "Owner Names and Uploads"
Cohesion: 0.22
Nodes (5): Names, normalize_ref(), safe_name(), list_uploads(), list_uploads()

### Community 52 - "Ledger Audit Tests"
Cohesion: 0.21
Nodes (10): Audit, found(), line(), stmt(), world(), format_audit(), _keyword(), _latest_cycle() (+2 more)

### Community 53 - "Subscriptions"
Cohesion: 0.14
Nodes (9): SubscriptionLog, Recurring, OwnerRules, Subscriptions, subscriptions_status(), upsert_subscription(), active_total(), format_list() (+1 more)

### Community 54 - "Ledger, Deploys and Data-Fix Backups"
Cohesion: 0.20
Nodes (21): cardguard plugin (Hermes), Deploy 2 deploy (2026-11-01 10:25-10:27 WIB with deploy.sh; Hermes listed 57 tools), Ledger backups before each data fix (ledger.db.bak-pre-*), Ledger (ledger.db on the VPS), notion.json (Notion page id in the vault-tools data directory), Notion snapshot pages (Agent > Finance five sub-pages, Agent > General; private), Notion daily sync (vault_tools/notion_sync.py, no LLM), notion_token docker secret (vault-tools) (+13 more)

### Community 55 - "Recording Completeness Tests"
Cohesion: 0.47
Nodes (3): acct_db(), Completeness, r()

### Community 56 - "Runbook and Deploy (M1)"
Cohesion: 0.11
Nodes (18): Runbook (M1), Finding 2026-11-01: getMe showed Allow Groups still on for @danoevault_agent and @danoecontrol_bot, Hermes configs drop groups (allowed_chats: none); control drops them in code, Blocked-domain egress test (example.com via squid-ctl from control must return 403), BotFather bots (usernames end in bot, Allow Groups off), First-time VPS setup (each step needs owner approval), Front secrets telegram_front_token and anthropic_front_key (make secret-set), Host hardening (SSH keys only, no root login, ufw allow 22, unattended-upgrades, swap, journald and Docker log caps) (+10 more)

### Community 57 - "Runtime Map Overview, Timers and Proxies"
Cohesion: 0.06
Nodes (60): api.anthropic.com, api.notion.com, api.telegram.org, Denied: AWS IMDSv2 credential probes to the instance-metadata address (/latest/api/token, iam/security-credentials), Denied: DNS-over-HTTPS fallbacks of the HTTP clients (dns.google, cloudflare-dns.com), Denied: Hermes model-catalog and provider refreshes (hermes-agent.nousresearch.com, raw.githubusercontent.com, openrouter.ai, portal.nousresearch.com), Docker DNS (name resolution used instead of DNS-over-HTTPS), Egress proxies (squid) runtime map (+52 more)

### Community 58 - "Living Reserve Estimate"
Cohesion: 0.17
Nodes (6): LivingReserveEstimate, _by_balance(), cash_spent(), estimate_living_reserve(), is_discretionary(), _spent_by_category()

### Community 59 - "Compose Secrets"
Cohesion: 0.11
Nodes (19): file, file, file, file, file, secrets, change_proposals_mcp_token, gmail_ingest_client (+11 more)

### Community 60 - "Balance Reports and Living Marks"
Cohesion: 0.19
Nodes (14): jago-harian account (daily pocket), jago-utama account (one Jago statement file for every pocket), balance_reports table (bank-app balance reported by the owner), /data report command, format_autodebit_check (sentence when nothing is debited; fixed in the 2026-11-01 recalibration), health.LIVING_ACCOUNT (jago-harian anchors the month), living_balance_mark (system key: last transaction id at the reading), living_balance_report (system key: the balance_reports row of the reading) (+6 more)

### Community 61 - "Open Questions, Calibration and Number Guard"
Cohesion: 0.18
Nodes (16): Biggest avoidable costs (game/digital top-ups; late/overlimit fees and interest), Bot calibration from the owner's real chat (2026-10-28), Cash records never merge (record_expense: exactly one of account_alias, card_alias, tunai=true), Ended subscriptions (Catchplay, GoPro, AWS, Steam, PlayStation), Open question 2: closing the pot gap without the children's needs, Open question 3: mark each app wajib or cuttable, Document read guard (3 re-reads per 30 min), record_expense (account_alias, card_alias or tunai) (+8 more)

### Community 62 - "Statement PDF Intake and Sanitizing"
Cohesion: 0.05
Nodes (24): Counting, RereadGuard, make_pdf(), McpIngest, PdfIntake, ingest_statement(), record_statement(), count_dated_lines() (+16 more)

### Community 63 - "Hermes config.yaml (Repo)"
Cohesion: 0.13
Nodes (14): approvals, destructive_slash_confirm, compression, min_tail_user_messages, threshold_tokens, plugins, enabled, security (+6 more)

### Community 64 - "Report Rendering and HTML Tests"
Cohesion: 0.30
Nodes (4): check_html(), Reports, world(), build()

### Community 65 - "Recalibration and Number Guard (1 Nov)"
Cohesion: 0.23
Nodes (10): /rekening command (owner registers an account number), Number guard remembers amounts from the gateway's photo description (English number format), Hermes state.db (sessions; holds the flagged Cek angka replies), JUMLAH line (unfunded list total in status_gajian and the plan summary), Number guard (pre_llm_call, post_tool_call, transform_llm_output hooks; Cek angka warning), Open question 12: Jago fixed-expenses account named as registered but has no payee number, plan_progress table (plan transfers marked done), 2026-11-01 recalibration: numbers the bot worked out itself now come from the code (+2 more)

### Community 66 - "Health Check and Verdicts"
Cohesion: 0.15
Nodes (10): cash_month(), Health, account_balances(), debt_load(), format_health(), health_check(), living_anchor(), snapshot() (+2 more)

### Community 67 - "Hermes Assumptions, Pin and Architecture"
Cohesion: 0.09
Nodes (34): Hermes pin: nousresearch/hermes-agent v0.22.5 (manifest digest recorded, checked 2026-10-27), ingest folder (ingest-gmail writes, vault-tools reads read-only; statement drop), ingest-gmail (timer job on net-vault, writes the ingest folder), vault (Hermes finance bot container), vault-tools (vault zone tool service), Vault zone (finance, net-vault), Assumption spikes (Hermes v0.22.5), Card token placeholder [[CARD:****last4]] (+26 more)

### Community 68 - "Payday Plan Spec (Funding Order, Worked Example)"
Cohesion: 0.20
Nodes (13): Payday plan spec (vault_tools/payday.py), Bills paid once (2026-11-01): an open one is an essential in the plan of every payday after the day it was recorded whose window reaches its due date, Estimated cost of delay per shortfall (amount * late_cost_bp / 10000, rounded half up), late_cost_bp input (late cost in basis points), Payday window [payday, next payday), Seeded randomized properties (salary conservation, no negatives, funded + unfunded = total due, determinism under input order), recorded_on (the server's day a bill was recorded, never the host clock), Shortfall example (lower salary: instalment partly funded, later items unfunded, nothing to hold) (+5 more)

### Community 69 - "Vault Bot SOUL and Owner Rules"
Cohesion: 0.06
Nodes (35): SOUL.md: vault bot persona (personal finance advisor and planner), Auto-debit debts (upsert_debt pay_method=autodebit; one figure per account incl. the bank-held minimum), Card instalment recording (x/y lines, record_card_installments, card_installments_status), Card payment method rules (Jenius and BCA to an account, Mandiri via the app menu, others to the card number), Card tokens [[CARD:num-xxxx]] map to stored cards by last 4 digits; then link_card_payees, catat_usulan (records a missing capability or number for /usulan), Category scheme (wajib:, sinking:, transfer_internal, sekali:, perantara:, berhenti:, free daily spending), Chat uploads (list_uploads, ingest_statement, record_mutations; BARIS KURANG means resend with replace=true) (+27 more)

### Community 70 - "Payday Plan and Pot Tools (Usage)"
Cohesion: 0.19
Nodes (19): mcp__vault_tools__simulasi_skenario, card_payments table (7 rows, one payment per card, last 2026-10-28 to 2026-10-30), sekali: one-off categories (e.g. coway-tunggakan, jht, jual-emas, medis, pelunasan-kartu), Deploy 2 (2026-11-01), Deploy drift: 179 repo files vs 178 in /opt/personal-agent, 176 identical, no runtime drift, fixed_expenses table (6 rows), one_off_bills table (0 rows), Payday plan (rencana gajian; paydays 2026-10-30 and 2026-11-30) (+11 more)

### Community 71 - "Compose Logging Options"
Cohesion: 0.18
Nodes (17): logging, logging, logging, logging, driver, options, max-file, max-size (+9 more)

### Community 72 - "Compose Service: ingest-gmail"
Cohesion: 0.14
Nodes (14): build, cap_drop, cpus, depends_on, mem_limit, networks, profiles, read_only (+6 more)

### Community 73 - "Compose Service: vault-tools"
Cohesion: 0.14
Nodes (14): vault-tools, build, cap_drop, cpus, depends_on, mem_limit, networks, oom_score_adj (+6 more)

### Community 74 - "Calibration Runbook and Reviews"
Cohesion: 0.10
Nodes (22): Bot calibration runbook (manual, on the owner's request), ops/calibration/bot_quality.py (tool errors, replies that apologise or correct themselves), ops/calibration/bot_usage.py (cost per day and source at list prices), cardguard plugin (appends the number-guard flag), Hermes cost_status unknown for claude-sonnet-5-5 (compare by hand), Data review (read-only), hermes chat --oneshot with the UJI KALIBRASI prefix (no recording or changes), JUMLAH line in a tool result (2026-11-01) (+14 more)

### Community 75 - "Control Store and Proposal Files"
Cohesion: 0.14
Nodes (6): buttons(), discard(), now(), read_proposal(), Store, write_json()

### Community 76 - "Ledger Categories and Thresholds"
Cohesion: 0.08
Nodes (30): jago-darurat (Jago savings account), belanja-harian category (3 rules), belanja-online category (15 rules), berhenti:supir category (12 rules), biaya-bank category (47 rules), bunga category (23 rules), donasi category (7 rules), gaji category (9 rules) (+22 more)

### Community 77 - "Compose Service: control"
Cohesion: 0.14
Nodes (14): build, cap_drop, cpus, depends_on, mem_limit, networks, oom_score_adj, read_only (+6 more)

### Community 78 - "Compose Service: vault (Hermes)"
Cohesion: 0.14
Nodes (14): vault, command, cpu_shares, cpus, depends_on, env_file, image, mem_limit (+6 more)

### Community 80 - "Budgets and Spending"
Cohesion: 0.15
Nodes (10): Budgets, Pace, planned(), RecordExpense, spend(), budget_status(), set_budget(), list_uncategorized() (+2 more)

### Community 81 - "Living Money and Cash to Hold"
Cohesion: 0.19
Nodes (13): cash_to_hold (salary minus funded minus fees), daily_allowance (cash_to_hold // days_in_window, salary part only, stored never shown), fees (plan output list: date, destination, amount, kind kartu or transfer), living_leftover (last cycle's leftover the owner still held), living_leftover_spent (cash spent from the payday until the leftover was reported), living_money = cash_to_hold + living_leftover (the owner's daily money for the window), Plan output (transfers, fees, cash_to_hold, daily_allowance, warnings), Salary (plan input) (+5 more)

### Community 82 - "Front Compose Service"
Cohesion: 0.11
Nodes (19): path, required, cap_add, cap_drop, command, cpu_shares, cpus, depends_on (+11 more)

### Community 83 - "Cashflow and Recurring Payments"
Cohesion: 0.15
Nodes (8): cashflow(), excluded(), _month_rows(), recurring(), suggest_salary(), cashflow_summary(), recurring_payments(), suggest_salary()

### Community 85 - "Compose Service: squid-comms"
Cohesion: 0.17
Nodes (12): squid-comms, cap_add, cap_drop, cpus, image, mem_limit, networks, oom_score_adj (+4 more)

### Community 86 - "Compose Service: squid-ctl"
Cohesion: 0.15
Nodes (13): squid-ctl, cap_add, cap_drop, cpus, image, logging, mem_limit, networks (+5 more)

### Community 87 - "Compose Service: squid-front"
Cohesion: 0.15
Nodes (13): squid-front, cap_add, cap_drop, cpus, image, logging, mem_limit, networks (+5 more)

### Community 88 - "Compose Service: squid-vault"
Cohesion: 0.17
Nodes (12): squid-vault, cap_add, cap_drop, cpus, image, mem_limit, networks, oom_score_adj (+4 more)

### Community 89 - "Gmail OAuth and Sender Allowlist"
Cohesion: 0.22
Nodes (15): Gmail OAuth guide (readonly) for ingest-gmail, Bank sender allowlist with DKIM/DMARC pass (DBS, CIMB Niaga, HSBC, Mandiri, Mega), Gmail API (gmail.googleapis.com, oauth2.googleapis.com), Gmail readonly token (gmail_ingest_token), Google Cloud project personal-agent-ingest (Gmail API enabled), ingest-desktop OAuth client (gmail_ingest_client), ingest-gmail (daily deterministic job, no LLM), Keuangan/Kartu Kredit Gmail label (looked up by label ID) (+7 more)

### Community 90 - "Debts, Balances and Proposals (State)"
Cohesion: 0.28
Nodes (15): mcp__vault_tools__saldo_rekening, Autodebit (autodebet) of debt instalments, balance_reports table (6 rows: mandiri-utama 4, jago-harian 2), Car instalment debt (cicilan-mobil): due 2 Nov paid manually 30 Oct, 18 instalments left, next autodebit 2 Dec, wajib: mandatory categories (asuransi, cicilan, ipl, kartu, les, sekolah, spaylater), debt_payments table (2 manual payments, cicilan-mobil and spaylater, 2026-10-30), debts table (2 rows), feature_requests table (/usulan, 10 rows) (+7 more)

### Community 91 - "Cardguard Number Guard Hooks"
Cohesion: 0.20
Nodes (9): amounts(), check_answer(), on_llm_output(), on_pre_llm(), on_tool_result(), register(), _remember(), sweep_ttl() (+1 more)

### Community 92 - "Graph-First Prompt Hook"
Cohesion: 0.26
Nodes (7): behind(), ignore_patterns(), ignored(), main(), md5(), snapshot(), wib()

### Community 94 - "Ledger Tables and Backups (State Snapshot)"
Cohesion: 0.06
Nodes (61): accounts table (8 rows), ledger.db.bak-pre-deploy2 (with -shm and -wal copies), Ledger backups made 2026-10-27: pre-v4, v5, v6, v8, v9, categorize, completeness, instkey, owner-names, pending, perantara, pocketfix, scans, subs, Ledger backups made 2026-10-28: pre-answers, calibrate, cardbudget, cardlines, daily-account, dedupe, dedupe-cards, ef-pocket, flazz-fix, held-balance, invariants, keywords, latest, notion, pot-schedule, recal-v2, recurring, rules2, scenarioA, Ledger backups made 2026-10-30: pre-leftover-fix, merge-fix, payday-progress, record-merge, unmerge, unmerge-2, usulan (with -shm and -wal copies), Ledger backups made 2026-11-01: pre-deploy2, pre-pace-fix, pocket-balance, recal (each with -shm and -wal copies), bca-9706 card (10 statements 2026-01-12 to 2026-10-12, last due 2026-10-28; 8 instalment rows), bca-utama account (993 transactions; 10 mutation files 2026-01-01 to 2026-10-28) (+53 more)

### Community 96 - "Deploy 2 Data Fix"
Cohesion: 0.24
Nodes (5): allocation(), copy(), plan(), report(), say()

### Community 98 - "Compose Networks"
Cohesion: 0.15
Nodes (12): name, internal, internal, internal, internal, networks, egress, net-comms (+4 more)

### Community 99 - "Compose Squid Template"
Cohesion: 0.18
Nodes (11): x-squid, cap_add, cap_drop, cpus, image, logging, mem_limit, oom_score_adj (+3 more)

### Community 100 - "Card Statements, Payment Targets and Reports"
Cohesion: 0.13
Nodes (22): belanja_kartu (per-card statement lines, long numbers masked), BCA card, CIMB card, HSBC card, Card installments (x/y) tracking per scanned statement, Jenius card, Mandiri card (paid via the app menu), Mega card (+14 more)

### Community 101 - "Host Runtime and Firewall"
Cohesion: 0.17
Nodes (18): authorized_keys (root: 0 entries, ubuntu: 1), docker daemon.json (json-file log driver, max-size 10m, max-file 3), Docker 29.9.2 and Compose 5.6.1 on the VPS, /etc/cron.d entries (e2scrub_all, sgagenttask, sysstat, yunjing), fail2ban (inactive), Host firewall (active; deny incoming except 22/tcp, allow outgoing, deny routed), Host (VPS) runtime map, personal-agent-ingest-gmail image (latest, created 2026-11-01 06:00 WIB) (+10 more)

### Community 102 - "Change-Proposal Submission Tests"
Cohesion: 0.18
Nodes (3): FakeTelegram, good(), Proposals

### Community 103 - "Hermes Auxiliary Models"
Cohesion: 0.20
Nodes (10): auxiliary, compression, title_generation, vision, model, provider, model, provider (+2 more)

### Community 104 - "Hermes MCP Server Config"
Cohesion: 0.20
Nodes (10): Authorization, mcp_servers, vault_tools, prompts, resources, connect_timeout, headers, timeout (+2 more)

### Community 105 - "Change-Proposals Compose Service"
Cohesion: 0.12
Nodes (16): context, dockerfile, build, cap_drop, cpu_shares, cpus, mem_limit, networks (+8 more)

### Community 106 - "Host Scripts (Holidays, PDF Passwords, Gmail Auth)"
Cohesion: 0.06
Nodes (19): get(), main(), notify(), read_json(), main(), days_left(), main(), message() (+11 more)

### Community 107 - "Corrected Source Merge Tests"
Cohesion: 0.25
Nodes (3): CorrectedSourceFindsItsStatementRow, pho(), world()

### Community 108 - "Hermes Credentials Boundary"
Cohesion: 0.24
Nodes (10): auth.json (Hermes credential store and pool, empty; the API key comes from env; never opened by the collector), ANTHROPIC_API_KEY env var (where the Anthropic key comes from; value never read), Hermes .env in HERMES_HOME (mode 0600, never opened by the collector), ingest_statement (read a financial file, PDF, CSV or TXT, from the ingest folder or a Telegram upload, decrypting it), list_uploads (files the owner recently uploaded via Telegram, newest first, as file_ref for ingest_statement), Log line 'credential pool: no available entries' (agent/credential_pool.py; benign), Logger agent.credential_pool (72 INFO), Runtime-map collector (ops/runtime-map/collect.py, regenerated with make runtime-map) (+2 more)

### Community 109 - "State Snapshot: Timers, Jobs and Restic"
Cohesion: 0.14
Nodes (22): docs/runtime/README.md, State snapshot, pa-disk log line disk N% (120 runs in 7 days), Holiday baseline: libur and cuti bersama dates added by pa-holidays, Host systemd timers and jobs (pa-*; pa-check and pa-forget failed on 2026-11-01, the rest succeeded), make runtime-map (regenerates the state snapshot from the live VPS), pa-backup (Personal agent restic backup; last 2026-11-01 02:00, next 2026-11-02 02:00), pa-check (restic integrity check, monthly; failed 2026-11-01 04:00 with exit-code 1, next 2026-12-01 04:00) (+14 more)

### Community 110 - "Hermes Telegram Access Settings (Live)"
Cohesion: 0.25
Nodes (8): Vault container environment variable names (values never read), HERMES_SKIP_CONFIG_MIGRATION env var, TELEGRAM_ALLOWED_USERS env var (Telegram user allowlist; value never read), VAULT_TOOLS_MCP_TOKEN env var (Bearer for the vault_tools MCP server; value never read), Log line 'config migration skipped: This config predates version 12' (hermes_cli/config_migrations.py; benign), mcp_servers.vault_tools config (url http://vault-tools:8000/mcp, timeout 60, connect_timeout 20, Bearer header from VAULT_TOOLS_MCP_TOKEN, prompts and resources off), pairing/ in HERMES_HOME (empty), gateway.platforms.telegram.extra.allowed_chats none (not in DEFAULT_CONFIG; readers found by automatic search, to confirm by hand)

### Community 111 - "Cardguard Telegram Menu"
Cohesion: 0.29
Nodes (4): ensure_menu(), menu_is_ours(), _menu_loop(), push_menu()

### Community 113 - "Payday Plan, Recalibration and Living Reserve"
Cohesion: 0.11
Nodes (30): fee_estimate (simulation fees after cycle 1: one per fixed cost, instalment paid by transfer, card with a bill now, pot, emergency fund and the living money), anthropic_front_key secret (from the owner), atur_jadwal_pot (saves the pot schedule after the owner agrees; pola, pakai_gaji_hari_tenggat), Bot model config (reasoning_effort high, claude-sonnet-5-5 vision and compression, Haiku titles), DBS card, dana_darurat(saldo) (the only way to set emergency_saved), Double-count finding (open statements already held that month's instalments and subscriptions), Emergency fund (emergency_target, emergency_monthly, emergency_saved) (+22 more)

### Community 114 - "30 Oct Payday Data, Plans and Auto-Debits"
Cohesion: 0.13
Nodes (24): biaya_admin_mulai (payday from which fees count, YYYYMMDD; 20261130 live), Admin fees (/usulan #4: the owner's estimates per card payment and per other transfer; the Mandiri card via the bank-app menu and the auto-debits cost nothing), Auto-debits from Mandiri (car instalment MTF, SPayLater), biaya_admin_mulai (fees count from the 30 Nov payday, 20261130), Car instalment (MTF, incl. admin; auto-debit on day 2), cicilan_dibayar (instalment paid by hand ahead of its auto-debit), cicilan_dibayar batal=true (undoes an instalment recorded by mistake), debt_payments table (+16 more)

### Community 115 - "Kanban Store Tables (Unused)"
Cohesion: 0.33
Nodes (6): kanban.db (kanban store; toolset disabled, every table empty), kanban.db kanban_notify_subs table (0 rows), kanban.db task_attachments table (0 rows), kanban.db task_comments table (0 rows), kanban.db task_events table (0 rows), kanban.db tasks table (0 rows)

### Community 116 - "Payday Progress Tool Tests"
Cohesion: 0.29
Nodes (3): Migration, StoredPlans, ThroughTheTools

### Community 117 - "Compose Environment Settings"
Cohesion: 0.24
Nodes (10): environment, environment, CONTROL_STATE_DIR, HTTPS_PROXY, MY_TELEGRAM_ID, NO_PROXY, PROPOSALS_INBOX_DIR, TELEGRAM_TOKEN_FILE (+2 more)

### Community 118 - "Zone Isolation Tests"
Cohesion: 0.21
Nodes (4): Compose, HermesProfiles, load(), mounts()

### Community 122 - "Front Hermes Config"
Cohesion: 0.15
Nodes (12): approvals, destructive_slash_confirm, compression, min_tail_user_messages, threshold_tokens, security, allow_lazy_installs, sessions (+4 more)

### Community 124 - "Hermes Telegram Gateway Config"
Cohesion: 0.33
Nodes (6): allowed_chats, disable_link_previews, gateway, platforms, telegram, extra

### Community 127 - "Hermes Agent Block"
Cohesion: 0.50
Nodes (4): agent, disabled_toolsets, max_turns, reasoning_effort

### Community 128 - "Hermes Memory Settings"
Cohesion: 0.50
Nodes (4): memory, memory_enabled, user_profile_enabled, write_approval

### Community 129 - "Cardguard Plugin Manifest"
Cohesion: 0.50
Nodes (3): description, name, version

### Community 131 - "Hermes Session Store (state.db)"
Cohesion: 0.10
Nodes (24): Preflight-compression log line (shows the threshold in force when it was written), Log line 'Re-anchored stale current_turn_user_idx' (agent/turn_iteration_prep.py; counts mid-turn compactions), Logger agent.context_compressor (67 INFO), Logger agent.conversation_compression (286 INFO), Gateway session keys (agent:main:local:dm 38, agent:main:telegram:dm 1, plus _README), sessions/sessions.json (gateway session key to session, with token and cost counters; 39 keys), sessions.retention_days 90 (same as the default: inactive days of ended-session history kept), state.db (sessions, messages, model usage, delivery obligations, routing, admissions, system prompts; SQLite WAL) (+16 more)

### Community 132 - "Receipt Merges and Record Fixes"
Cohesion: 0.10
Nodes (43): PROGRESS.md: progress and resume point (finance / vault), Mandiri account (salary lands here; auto-debit account), Accuracy layers (owner: 99.99% accuracy, no miscalculation), Bank mutations Jan-Oct (BCA, Mandiri, Jago; verified complete, October BCA CSV reconciled), card_payments table, Cash budgets (listrik, internet, transport; count account payments), category_keywords (owner-explained names, stored in the ledger, never in the repo), Category scheme (perantara, berhenti, sekali, bunga, wajib, transfer_internal) (+35 more)

### Community 133 - "Front Auxiliary Models"
Cohesion: 0.20
Nodes (10): auxiliary, compression, title_generation, vision, model, provider, model, provider (+2 more)

### Community 137 - "Front Change-Proposals MCP"
Cohesion: 0.20
Nodes (10): connect_timeout, headers, timeout, tools, url, Authorization, mcp_servers, change_proposals (+2 more)

### Community 139 - "Payday Plan Generation and Advice"
Cohesion: 0.13
Nodes (11): Advice, amounts(), DueBeforePayday, statement(), world(), PayRules, generate_payday_plan(), rincian() (+3 more)

### Community 140 - "Front Agent Persona and Setup"
Cohesion: 0.11
Nodes (18): vault's cardguard (needs vault-tools, which front cannot reach), Open decision: a rewrite-only card and account number guard plugin for front before step 4, Front memory approval (/memory pending, /memory approve <id>, /memory reject <id>), Front owner steps, in order (BotFather, Anthropic workspace, secrets, render env, start, test), Front redeploy after services/hermes/front/ changes, and stop (--profile front stop front change-proposals), Start front: compose --profile front up -d --build --wait change-proposals front, Front zone @danoefront_agent (M3, defined, not started; Haiku 5.5, web search, memory, submit), scripts/render-front-env.sh (refuses the vault key) (+10 more)

### Community 141 - "Service Images and Data Root"
Cohesion: 0.23
Nodes (12): control-state dir (mode 0700), personal-agent-control image (latest, created 2026-11-01), proposals-inbox dir (mode 0700, empty), change_proposals_mcp_token secret, telegram_control_token secret, BOT_CONTROL (control Telegram bot username), control/control.py (control code that holds the proposal rules), HEALTHCHECK: TCP connect to 127.0.0.1:8000 (30s interval, 5s timeout, 3 retries) (+4 more)

### Community 142 - "Front Telegram Chat Filter"
Cohesion: 0.33
Nodes (6): allowed_chats, disable_link_previews, gateway, platforms, telegram, extra

### Community 143 - "Squid Egress Allowlists"
Cohesion: 0.23
Nodes (10): ubuntu/squid:6.6-24.04_edge image, BOT_FRONT (front Telegram bot username), config/squid/comms.conf (comms zone allowlist: Anthropic and Google APIs), config/squid/ctl.conf (control zone allowlist: Telegram API only), config/squid/front.conf (front zone: open web on ports 80 and 443), config/squid/vault.conf (vault zone allowlist: Anthropic, Telegram, Notion, Google), api.anthropic.com (comms and vault allowlists), api.telegram.org (control and vault allowlists) (+2 more)

### Community 144 - "Front Memory Settings"
Cohesion: 0.40
Nodes (5): memory, memory_enabled, nudge_interval, user_profile_enabled, write_approval

### Community 146 - "Vault Tools Module (tools.py)"
Cohesion: 0.06
Nodes (45): Plan, dana_darurat(), paid(), _rata_deposit(), admin_fee(), autodebit_check(), bill_status(), bp_of_idr() (+37 more)

### Community 147 - "Session Compaction and Resets"
Cohesion: 0.17
Nodes (16): Compression summary call and aux_model telemetry, background_review model task, busy_input_mode demoted while compression is in flight, Child sessions (a compaction or /new continues the chat), claude-sonnet-5-5 (vault bot model), Compression blocked (ineffective, structural_backoff), Compression folded away the just-delivered reply, Context compression (compaction) (+8 more)

### Community 149 - "Front Agent Limits"
Cohesion: 0.50
Nodes (4): agent, disabled_toolsets, image_input_mode, max_turns

### Community 151 - "Runtime Map Hashing and Masking Tests"
Cohesion: 0.31
Nodes (3): _receipt_key(), digest_with_digit_run(), Scrub

### Community 152 - "Calibration Change-and-Verify Steps"
Cohesion: 0.15
Nodes (10): Read the audit and the plan for the coming 1st, Change and verify, docker compose up -d --build vault-tools, Deploy procedure (from the worktree root), ops/calibration/dry_run.py on a copy of the live ledger, Ledger (SQLite /data/ledger.db in the vault-tools container), rsync of the worktree to /opt/personal-agent on the VPS (excluding .git and .claude), config/stack.env (+2 more)

### Community 156 - "Front Model Setting"
Cohesion: 0.67
Nodes (3): model, default, provider

### Community 157 - "Front Tool Search Setting"
Cohesion: 0.67
Nodes (3): enabled, tools, tool_search

### Community 158 - "Vault Tool Search Setting"
Cohesion: 0.67
Nodes (3): enabled, tools, tool_search

### Community 159 - "Secrets Handling"
Cohesion: 0.19
Nodes (12): /opt/personal-agent-secrets (secret files, mode 0700), anthropic_front_key secret, anthropic_vault_key secret, gmail_ingest_client secret, telegram_front_token secret, telegram_vault_token secret, vault_tools_internal_token secret, vault_tools_key secret (+4 more)

### Community 162 - "Accounts, Debts and Auto-Debits"
Cohesion: 0.31
Nodes (9): mandiri-utama (Mandiri main account), wajib:cicilan category (9 rules), wajib:spaylater category (3 rules), cicilan-mobil (debt to MTF, autodebit from mandiri-utama, due day 2), spaylater (debt to Shopee SPayLater, autodebit from mandiri-utama, due day 1), debt_payments (ledger table, 2 rows), debts (ledger table, 2 rows), net_snapshots (ledger table, 2 rows) (+1 more)

### Community 166 - "Hermes Vault Engine Install"
Cohesion: 0.17
Nodes (12): Bundled engine plugins (browser, computer_use, context_engine, cron_providers, delegation, image_gen, kanban, memory, model-providers, platforms, web and others), TZ Asia/Jakarta (container timezone), Docker embedded DNS (container-local tcp and udp listeners), Engine image nousresearch/hermes-agent (release date 2026.9.24), Hermes Agent v0.22.5 (vault bot engine, Telegram bot @danoevault_agent, container personal-agent-vault-1), Install stamp (baseVersion 0.22.5, branch main, distribution docker, source ci, updateMechanism external, built 2026-10-23), installs/ and install_id (install bootstrap metadata), Log line 'router: catalog fetch failed / Model catalog' (plugins/model-providers/router; harmless) (+4 more)

### Community 167 - "Daily Account Re-Anchor (saldo_rekening)"
Cohesion: 0.16
Nodes (8): jago-harian account alias, living_reserve (protected living money, the owner's choice since 2026-10-28), saldo_rekening tool (re-anchors the month's daily money to the balance given), Anchor correction (difference with the records), Tier 2: essentials (fixed expenses, e.g. school; bills paid once), health.living_anchor, jago-harian daily account, saldo_rekening tool (a read balance of the daily account re-anchors the month)

### Community 168 - "Fixed Expenses and Children's Fees"
Cohesion: 0.09
Nodes (23): /opt/personal-agent-data/vault-tools (rw at /data), notion_token secret (read-only at /run/secrets), personal-agent-vault-tools image (latest, created 2026-11-01 10:26 WIB), berhenti:trip-mancing category (1 owner keyword), komisi-allianz category (1 owner keyword), perantara:art-belanja-anak category (1 owner keyword), sekali:keluarga-istri category (1 owner keyword), wajib:ipl category (10 rules) (+15 more)

### Community 169 - "Periksa Data Checks"
Cohesion: 0.25
Nodes (7): Instalments gone from the statement check, Missing statements check, Old pot balance check, /periksa in Telegram and the periksa_data tool, ops/calibration/recurring_charges.py (per-month table of recurring merchants), Subscription checks (recorded vs charged, stopped subscriptions still charged), Unpaid past-due bills check

### Community 171 - "Telegram Adapter Health"
Cohesion: 0.12
Nodes (21): Hermes API server (127.0.0.1:8642, model hermes-agent), Hermes cron scheduler, Telegram fallback-IP discovery via DNS-over-HTTPS, platforms.telegram.extra.drop_pending_on_cold_boot: true, /opt/data/.env (loaded by run_agent), Fatal telegram adapter error: updater.stop() missed the network-recovery deadline, Gateway control socket (/opt/data/gateway.sock), Gateway housekeeping (memory trim, agent cache idle sweep) (+13 more)

### Community 172 - "Telegram Delivery and Cold Boot"
Cohesion: 0.27
Nodes (8): channel_directory.json (chats the gateway knows: one telegram entry), Log line 'Cold boot: dropping Telegram updates' (Telegram adapter), Logger hermes_plugins.platforms__telegram.adapter (836 INFO, 271 WARNING, 2 ERROR), state.db conversation_generations table (1 row, source telegram), state.db delivery_obligations table (193 Telegram deliveries, all delivered, 2026-10-27 to 2026-11-01), gateway.platforms.telegram.extra.disable_link_previews true (read by the Telegram adapter), Telegram platform adapter (plugins/platforms/telegram/adapter.py; state connected), telegram_update_receipts JSON file in HERMES_HOME

### Community 176 - "Vault Commands and Payday Flows"
Cohesion: 0.11
Nodes (18): /rincian handled in pre_gateway_dispatch with skip plus direct Bot API send, Open: whether skip plus a direct Bot API reply writes to the session store, Spike 11: /rincian reply stays out of the session store (pass), tagihan_sekali tool (records a bill paid once such as arrears or a repair: alias, name, amount, due date, how it is paid), transfer_selesai (or lunas) marks a bill paid once as paid; paid in a plan's window it stays in that plan's progress, /internal/* surface (plugin only: store_payee, rincian), belanja_kartu (/belanja: statement lines per cycle and per card; not reading PDFs), dana_darurat (emergency fund status and recorded balance) (+10 more)

### Community 177 - "Ingest Inputs"
Cohesion: 0.25
Nodes (8): /opt/personal-agent-data/ingest (read-only at /ingest), pdf_passwords secret (read-only at /run/secrets), /ingest (read-only; filled by ingest-gmail and pa-uploads), ingest-gmail (fills /ingest), /ingest/telegram (58 files: bank statements, e-statements and mutasi sent as Telegram documents), pa-uploads (fills /ingest), PDF parsing packages (pdfplumber, pdfminer.six, pikepdf, pypdfium2), skipped_files (ledger table, 52 rows)

### Community 178 - "Payee Secrets and Sinking Funds"
Cohesion: 0.14
Nodes (18): vault_tools_key secret (read-only at /run/secrets), bca-utama (BCA main account), fixed-expenses (Jago savings account), jago-harian (Jago main account), jago-utama (jago main account), jenius-akun (Jenius main account, also a payee), pot-jago (Jago pool account), jenius-0480 (jenius card; statement day 26, due day 13, transfer to jenius-akun) (+10 more)

### Community 179 - "Hermes Config Key Walker"
Cohesion: 0.50
Nodes (3): key_lines(), doc(), walk()

### Community 181 - "Data Dirs and Upload Relay"
Cohesion: 0.21
Nodes (11): canary.txt (root-owned file in the data dir, mode 0644), hermes-front dir (mode 0700, empty), hermes-vault data dir (mode 0700), nousresearch/hermes-agent image (no tag, created 2026-10-23), ingest data dir (mode 0755), ingest-state dir (mode 0755), /opt/personal-agent-data (persistent state, root-owned, restic-backed), vault.env (root-only env file, mode 0600) (+3 more)

### Community 183 - "Receipt Vision and Purchase Tools"
Cohesion: 0.29
Nodes (7): auxiliary.vision: claude-sonnet-5-5 via anthropic (default auto), daftar_belanja (purchases recorded from screenshots, receipts or the owner's words over the last days, each with its id), hapus_belanja (delete one recorded purchase, e.g. one recorded twice; same rules as ubah_belanja), Logger tools.vision_tools (107 INFO), record_expense (record one purchase from a screenshot, receipt or the owner's words), ubah_belanja (change one recorded purchase: wrong source, amount, date, merchant or category), vision_analyze engine tool

### Community 184 - "Stack Settings and Host Checks"
Cohesion: 0.21
Nodes (14): gmail_ingest_token secret, restic.env secret (mode 0600), config/stack.env (non-secret stack settings), pa-backup.service + timer (restic backup, daily 02:00 WIB), pa-check.service + timer (restic integrity check, 1st of month 04:00 WIB), pa-disk.service + timer (disk usage check, hourly), pa-forget.service + timer (restic retention 7d/4w/6m, Sun 04:00 WIB), pa-gmail-token.service + timer (warns before the Gmail OAuth token expires, daily 08:00 WIB) (+6 more)

### Community 185 - "Funding Order and Admin Fees"
Cohesion: 0.16
Nodes (13): Admin fees (estimates, 2026-11-01: a bank fee per transfer out of the salary account), biaya_admin:<alias> (sets one item's fee; 0: none), biaya_admin_kartu (estimated fee per payment to a card number, capped), biaya_admin_transfer (estimated fee per other transfer, capped), Tier 4: card remaining balance (default: pay in full), Tier 1: card minimum due, Kartu dbs-1111 (dummy card alias in the example), Tier 3: debt installments and pool-account transfers (+5 more)

### Community 186 - "Daily Money Rules (Leftover and Top-Up)"
Cohesion: 0.14
Nodes (21): card_advice (no longer offers cutting the living money), Card spending budgets (kartu:<category>, owner approved 2026-10-28), cash_to_hold (the part the plan takes from the salary), /anggaran report command (budgets), daily_allowance (stored salary part; stored plans not rewritten, never shown), Daily money alerts (80% and over 100%) stay, Daily money is the top-up plus the leftover (pace fix, 2026-10-31), health_check (feeds the spending pace) (+13 more)

### Community 187 - "Scheduled No-LLM Jobs"
Cohesion: 0.52
Nodes (6): compose/docker-compose.yml (Docker Compose stack), compose jobs profile (one-off ingest-gmail runs), pa-ingest.service + timer (ingest-gmail statement fetch, daily 06:00 WIB), pa-notion.service + timer (Notion snapshot of the finance picture, daily 06:30 WIB), ingest-gmail job (services/ingest-gmail/Dockerfile, own ingest user), personal-agent-vault-tools-1 container (the Notion sync runs inside it)

### Community 193 - "Vault Model Setting"
Cohesion: 0.67
Nodes (3): model, default, provider

### Community 199 - "Deploy 2 Script"
Cohesion: 1.00
Nodes (3): idle(), mask(), deploy.sh script

### Community 200 - "Hermes Socket Probes"
Cohesion: 0.67
Nodes (3): socket_inodes(), socket_inodes_as(), sockets()

### Community 203 - "Money Formatting and Fee Lines"
Cohesion: 0.10
Nodes (12): PotBalance, Money, format_idr(), mark(), list_statements(), _jt(), _fee_line(), fee_parts() (+4 more)

## Ambiguous Edges - Review These
- `Turn machinery warmed (59 tool schemas materialized)` → `tagihan_sekali tool (one-off bills: arrears, repairs)`  [AMBIGUOUS]
  docs/runtime/bot-activity.md · relation: conceptually_related_to
- `belanja_kartu (per-card statement lines, long numbers masked)` → `Ended subscriptions (Catchplay, GoPro, AWS, Steam, PlayStation)`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `Card statement recording and reconciliation (7 cards)` → `/kondisi report command`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `Open question 7: GoPro charge on the CIMB October statement (annual, stop or move?)` → `Ended subscriptions (Catchplay, GoPro, AWS, Steam, PlayStation)`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `cardguard TTL file (ttl/rincian.jsonl: /rincian messages to delete after expiry; 0 lines)` → `belanja_kartu (card spending breakdown per cycle from statement lines already read by code; never read the PDF for this)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `Gateway multiplex standalone (only one profile exists, nothing to multiplex)` → `state.db hosted_room tables (14 hosted-room tables, all empty)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `cache/schema_columns.json (schema hash plus versions for 17 tables)` → `state.db (sessions, messages, model usage, delivery obligations, routing, admissions, system prompts; SQLite WAL)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `cache/tool_discovery_cache.json (tool discovery cache, 287 keys, written 2026-10-27)` → `Engine tools besides MCP (only clarify and vision_analyze; the row still counts 56 vault_tools tools from the latest tool-schema snapshot while the schema cache section lists 57)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `Coway arrears expense (paid 30 Oct from the Mandiri balance; receipt on mandiri-utama, category sekali:coway-tunggakan like the 13 Oct rows)` → `Open question 4: Google One and Coway on Mega vs recorded, check on the November statements`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `telegram_update_receipts JSON file in HERMES_HOME` → `Messages sent while the bot restarts are dropped (platforms.telegram.extra.drop_pending_on_cold_boot, default true)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `Open: whether skip plus a direct Bot API reply writes to the session store` → `Spike 11: /rincian reply stays out of the session store (pass)`  [AMBIGUOUS]
  docs/assumptions.md · relation: conceptually_related_to
- `/ingest (read-only; filled by ingest-gmail and pa-uploads)` → `processed_messages (ledger table, 0 rows)`  [AMBIGUOUS]
  docs/runtime/vault-tools.md · relation: conceptually_related_to
- `canary.txt (root-owned file in the data dir, mode 0644)` → `pa-backup.service + timer (restic backup, daily 02:00 WIB)`  [AMBIGUOUS]
  docs/runtime/host.md · relation: conceptually_related_to
- `ingest-gmail job (services/ingest-gmail/Dockerfile, own ingest user)` → `pdf_passwords secret`  [AMBIGUOUS]
  docs/runtime/host.md · relation: conceptually_related_to
- `Anonymous squid log and spool volumes (8, from image VOLUME lines)` → `squid exceptions (cap_add CAP_CHOWN, CAP_DAC_OVERRIDE, CAP_SETGID, CAP_SETUID; writable rootfs; tmpfs /var/log/squid)`  [AMBIGUOUS]
  docs/runtime/containers.md · relation: conceptually_related_to
- `cardguard plugin (services/hermes/vault/plugins/cardguard, read-only at /opt/data/plugins/cardguard)` → `VAULT_TOOLS_MCP_TOKEN and VAULT_TOOLS_INTERNAL_TOKEN (vault env names)`  [AMBIGUOUS]
  docs/runtime/containers.md · relation: conceptually_related_to
- `/usulan (posts the waiting proposals again with their buttons)` → `Hitting a limit: catat_usulan, then sudah kucatat di /usulan`  [AMBIGUOUS]
  services/hermes/vault/SOUL.md · relation: semantically_similar_to
- `image_input_mode: native (photos go to the model as images)` → `Number guard remembers amounts from the gateway's photo description (English number format)`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `Engine tools besides MCP (only clarify and vision_analyze; the row still counts 56 vault_tools tools from the latest tool-schema snapshot while the schema cache section lists 57)` → `tagihan_sekali (a bill paid once, outside subscriptions and fixed expenses, such as arrears or a repair; aksi picks the action, with optional alias, name, amount, due date, pay-to, method, date and note)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `Denied: AWS IMDSv2 credential probes to the instance-metadata address (/latest/api/token, iam/security-credentials)` → `squid-vault (vault zone egress proxy; allows api.anthropic.com, api.notion.com, api.telegram.org, gmail.googleapis.com, oauth2.googleapis.com)`  [AMBIGUOUS]
  docs/runtime/proxies.md · relation: conceptually_related_to
- `Denied: Hermes model-catalog and provider refreshes (hermes-agent.nousresearch.com, raw.githubusercontent.com, openrouter.ai, portal.nousresearch.com)` → `squid-vault (vault zone egress proxy; allows api.anthropic.com, api.notion.com, api.telegram.org, gmail.googleapis.com, oauth2.googleapis.com)`  [AMBIGUOUS]
  docs/runtime/proxies.md · relation: conceptually_related_to
- `pa-check.timer + pa-check.service (restic integrity check, 1st of month 04:00 WIB, runs backup.sh check)` → `pa-forget.timer + pa-forget.service (restic retention 7d/4w/6m, Sun 04:00 WIB, runs backup.sh forget)`  [AMBIGUOUS]
  docs/runtime/timers.md · relation: conceptually_related_to
- `Open: Telegram-side copy of the raw message (deleteMessage live test pending)` → `Spike 10: deleteMessage on the owner's incoming message (pass)`  [AMBIGUOUS]
  docs/assumptions.md · relation: conceptually_related_to
- `card_payments table (7 rows, one payment per card, last 2026-10-28 to 2026-10-30)` → `dbs-5685 card (6 statements 2026-01-25 to 2026-10-25, last due 2026-11-10; 0 marked paid; 10 instalment rows)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `cardguard plugin (appends the number-guard flag)` → `Full destination numbers are never in the plan`  [AMBIGUOUS]
  docs/calibration.md · relation: conceptually_related_to
- `cards table (7 cards; all statements reconciled, lines ok 0 per card)` → `lines_status: cocok on all 63 statements`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `transfer_internal category (504 transactions)` → `owner_names table (1 row)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `pot:hutang-teman fund (friend-debt pot; 1 fund report, 2026-10-26)` → `sinking_funds table (1 row)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to

## Knowledge Gaps
- **176 isolated node(s):** `AWS_DEFAULT_REGION`, `make runtime-map`, `mcp__vault_tools__add_owner_name`, `mcp__vault_tools__atur_jadwal_pot`, `mcp__vault_tools__belanja_kartu` (+171 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 909 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **32 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Laptop token flow (token piped over SSH into the VPS)` connect `Gmail OAuth and Sender Allowlist` to `Runbook and Deploy (M1)`, `Host Scripts (Holidays, PDF Passwords, Gmail Auth)`?**
  _High betweenness centrality (0.220) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `create_app()` (e.g. with `report()` and `rincian()`) actually correct?**
  _`create_app()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AWS_DEFAULT_REGION`, `make runtime-map`, `mcp__vault_tools__add_owner_name` to the rest of the system?**
  _176 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Card Statement Line Parsing` be split into smaller, more focused modules?**
  _Cohesion score 0.05266106442577031 - nodes in this community are weakly interconnected._
- **Why does `ingest-gmail (daily deterministic job, no LLM)` connect `Gmail OAuth and Sender Allowlist` to `Calibration Change-and-Verify Steps`, `Zone Architecture and Security (M1-M4)`, `Hermes Assumptions, Pin and Architecture`?**
  _High betweenness centrality (0.201) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Turn machinery warmed (59 tool schemas materialized)` and `tagihan_sekali tool (one-off bills: arrears, repairs)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `belanja_kartu (per-card statement lines, long numbers masked)` and `Ended subscriptions (Catchplay, GoPro, AWS, Steam, PlayStation)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._