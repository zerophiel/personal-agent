# Graph Report - m1-skeleton  (2026-11-02)

## Corpus Check
- 158 files · ~184,469 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 35 file(s) not represented in the graph (top: .service 10, .timer 10, (none) 8)

## Summary
- 4525 nodes · 11452 edges · 217 communities (164 shown, 53 thin omitted)
- Extraction: 86% EXTRACTED · 14% INFERRED · 0% AMBIGUOUS · INFERRED: 1617 edges (avg confidence: 0.83)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ae4fa17e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Card Statement Line Parsing
- Hermes Runtime Probes
- Card Spending Summary and Per-Card Detail (belanja_kartu)
- Cardguard Plugin (Number Guard, Menu, Control Bot)
- Runtime Map Overview, Host Timers and pa-* Units
- Vault-Tools Data Dir, Ledger Backups and Change Log
- Report Renderers, Subscriptions and Audit Tests
- Shared Imports, Ledger Connections and Ops Scripts
- Front Change Applier (applier.py)
- Live MCP Tool Catalog
- Bot Activity: Tool Calls, Tool Usage and Prompt Snapshots (state.db)
- Bank Mutation Recording, Rules and Tests
- Hermes Home, Engine Install, Credentials and Stores
- Applier Self-Checks, Zone Tests and Prechecks
- Gateway Lifecycle and Messages
- Cardguard Tests and Cardblock Plugin
- Card and Debt Payments, Undo and Paid-by-Hand
- Rupiah Formatting, Text Cleaning and Shared Helpers (money.py, mutations.py)
- Payday Plan Builder (payday.py)
- Egress Proxies (squid) Runtime Map
- Daily Money Pace and Purchase Alerts (health.py)
- Payee Vault, Rincian and Calibration Tests
- Runtime Map Collector
- Ledger Schema (v13 Tables)
- Debt Roadmap, Thresholds and Calibration Tests
- Pot Simulation, Admin Fees and Plan Invariants
- Makefile Targets, Stack Settings, Deploy Guard and Host Units
- Runbook: Applier Install, Deploys and Recovery
- Applier Tests (test_applier.py)
- Zones, Containers and Squid
- Approvals Flow and Proposal Folders (Architecture)
- Receipt Merge Rules and Resent Screenshots
- Gmail Sender Authentication (auth.py)
- Spending Analysis (Budget Baseline)
- MCP Server App, Budgets and Tool Flow Tests
- Egress, Containers and Telegram Polling (State)
- Holiday Fetch Decisions, Overrides and Tests
- Health Check, Budget Status and Debt Load (health.py)
- Ledger Database and Tables (Runtime)
- Sinking Fund Tests
- Gmail Ingest Run and Its Tests
- Pot Deposit Schedule (pot_schedule)
- Runbook (M1-M3): VPS Setup and Front Start
- Category Suggestions (suggest.py)
- Progress Hub: Bots, Zones and Milestones
- Live Catalog: Payday, Bill and Instalment Tools, Ledger Masking
- Host Data Dirs, Env Files and Control/Applier Paths (Runtime)
- Host Probe Script (probe_host.py)
- Control Bot Approval Tests
- Hermes Agent Settings and Toolsets (Live)
- Payday Tests, Masking and Money Helpers
- Card Installments (card_installments.py)
- Bills Paid Once (one_off.py) and Placement Tests
- Security: Egress, Squid Proxies and Sender Checks
- Ledger, Deploys and Data-Fix Backups
- Recording Completeness Tests
- Vault-Tools Probe Script (probe_vault_tools.py)
- Hermes Engine Image, Install and Bundled Plugins
- Hermes Gateway Containers (Vault, Front)
- Compose Secrets
- Front Cardblock Plugin Tests (CardBlock)
- Control Bot Core and Diff Posting (Control class)
- Statement PDF Intake and Sanitizing
- Hermes config.yaml (Repo)
- Ledger Cards, Card Payees and Subscriptions
- Expense Recording, Corrections, Deletion and Debt Payments
- Ledger Thresholds, Budgets and Plans
- Hermes Assumptions, Architecture and Vault-Tools Surfaces
- Payday Plan Spec (Funding Order, Worked Example)
- Control Bot Auth and Applied-Outcome Tests
- Payday Plan, Debts, Balances and Usulan (State Snapshot)
- Compose Logging Options
- Compose: ingest-gmail Service and Env Settings
- Compose: vault-tools and ingest-gmail Services
- Calibration Runbook and Reviews
- Audit and Report Rendering Tests
- Card Statement Recording and Reconciliation Tests (record_statement)
- Compose Service: control
- Compose Service: vault (Hermes)
- Weekly Docker Prune Script
- Notion Sync, Client and Page Rendering (notion_sync.py)
- Living Money and Cash to Hold
- Front Compose Service
- Payday Plan Generation and Advisor Tests
- Graph-First Hook Tests
- Compose Service: squid-comms
- Compose Service: squid-ctl
- Compose Service: squid-front
- Compose Service: squid-vault
- Gmail OAuth and Sender Allowlist
- Card, Statement and Instalment Tables (State Snapshot)
- Fee Invariant Tests (test_admin_fees.py)
- Graph-First Hook (graph_first.py)
- Upload Sync Tests
- Ledger Tables and Backups (State Snapshot)
- Control Diff Review Tests
- Deploy 2 Data Fix
- MCP Server Security Tests
- Compose Networks
- Compose Squid Template
- Card Statements, Payment Targets and Reports
- Expense Correction Tests (edit_expense, test_corrections.py)
- Change-Proposal Submission Tests
- Hermes Auxiliary Models
- Hermes MCP Server Config
- Change-Proposals Compose Service
- Living Reserve Estimate Tests (estimate_living_reserve)
- Gmail Ingest Job: Messages, PDFs and Retention (run.py)
- Vault-Tools Surfaces (/mcp and /internal) and Requirements
- State Snapshot: Timers, Jobs, Restic and Runs
- Gmail API Client (GmailClient)
- Control Proposal Store
- Server Flow Tests
- Progress: Receipt Merges, Record Fixes and 1 Nov Recalibration
- Applied-Pull Host Script (applied-pull.py)
- Holiday Fetch Apply Decision (decide)
- Vault SOUL: Payday List and Owner Rules
- Statement Line Counting and Completeness
- Zone Isolation and Egress Tests
- Report Builder and Usulan Report Tests (test_reports.py)
- Number Guard Tests
- Statement Reconciliation (reconcile.py)
- Front Hermes Config
- Gmail Token Check Tests
- Hermes Telegram Gateway Config
- Change Proposals Server (proposals.py)
- Gmail Ingest Sender Config (load_senders)
- Hermes Agent Block
- Hermes Memory Settings
- Cardguard Plugin Manifest
- Approvals, Control Zone and Applier (Contract and Runbook)
- Hermes Session Store and Telegram Delivery
- Progress: Doubled Mandiri Rows, Overlap Matching and Card-Repayment Fix
- Front Auxiliary Models
- Vault Env Renderer
- Front Change-Proposals MCP
- Hermes Telegram Adapter, Plugins and Delivery
- Bot Activity: Sessions, Context Compression and /new Resets
- Front Agent Persona and Setup
- Runtime Map Scrub Tests
- Front Telegram Chat Filter
- Statement PDF Ingest Tests
- Front Memory Settings
- Applied-Pull Tests (test_applied_pull.py)
- Vault Tools Module (tools.py)
- Applier Safe File Reads and Atomic Writes
- Hermes Engine Tools and Tool Search
- Front Agent Limits
- Control Bot (control.py) and Deploy Guard Tests
- Hermes Kanban Store (kanban.db)
- Statement Reread Guard Tests
- Pace-Fix Deploy Script (31 Oct)
- Pocket-Balance Deploy Script (1 Nov)
- Recalibration Deploy Script (1 Nov)
- Front Model Setting
- Front Cardblock Plugin (cardblock/__init__.py)
- Vault Tool Search Setting
- Infrastructure Files: Dockerfiles, Compose and Squid Allowlists
- Data Dirs Script
- Front Env Render Script
- Deploy Drift, SOUL Mount and Skills Prompt Snapshot
- Ingest Data Dir and Upload Relay (pa-uploads)
- Deploy Guard Tests (test_deploy_guard.py)
- Gmail Client Tests (tokens, pagination, errors)
- Progress: Recalibration v2, Payday Plans and Daily Money Rules
- Gmail Token Check Script (gmail-token-check.py)
- Fixed Expenses and Children's Fees
- Periksa Checks (calibration: subscriptions, statements, pots)
- Mandiri Doubled Rows Data Fix (fix_data.py)
- Bot Activity: Gateway Lifecycle, Shutdowns and Restarts
- Cardblock Plugin Manifest
- Control Tests: Fake Telegram
- Front and Vault Card Detection Parity Tests
- Telegram HTML Tag Balance Check (Balanced)
- Vault SOUL: Persona, Data and Card Rules
- Ingest Inputs
- Ledger Accounts, Payee Secrets and Sinking Funds
- Owner Names and Uploads
- Card Line Kind Classification (classify)
- Gmail Search of Unlabelled Statements (SearchedClient)
- Front Compression Settings
- Hermes Config Key Lines Probe (key_lines)
- Statement Row Models (Installment, Txn)
- Bank Admin Fee Estimates and Rules
- Cardguard Answer Check and LLM Hooks (check_answer)
- Bank Amount Formats (parse_amount)
- Plan Invariant Checks (invariants.py)
- Front First Start: BotFather, Workspace Key and Spend Limits
- Preflight Script
- Backup Script
- Disk Check Script
- Vault Model Setting
- Timer Install Script
- Secret Generation Script
- Secret Set Script
- Upload Sync Script
- Control Proposal Validation
- Deploy 2 Script
- Hermes Socket Inode Probes (socket_inodes)
- Daily Account Re-Anchor (saldo_rekening)
- Progress: M4 Comms Open Question, Spend Limits and Front Cost Follow-Up
- Card Statement Layout and Date Tests
- WIB Date Tests (test_sinking.py)
- Ledger Categories and Thresholds
- Vault-Tools Token Middleware (_Auth)
- Deploy Guard Script (deploy-guard.sh)
- Applier Install Script (install.sh)
- PDF Password Collection Tests (pdf_passwords_set)
- Card Line Transaction Date (_date)
- Card-Internal Data Fix Deploy (deploy.sh)
- Card Lines vs Statement Totals (reconcile)
- Cardguard Telegram Command Menu (ensure_menu)
- Receipt-to-Mutation Merge Tests (Merge)
- Scenario Simulation via MCP Tool Tests (test_simulate)
- Mandiri Doubled Rows Deploy Script (deploy.sh)

## God Nodes (most connected - your core abstractions)
1. `generate_payday_plan()` - 106 edges
2. `create_app()` - 98 edges
3. `format_idr()` - 93 edges
4. `connect()` - 87 edges
5. `Bot activity snapshot` - 72 edges
6. `MCP server vault_tools (57 tools at http://vault-tools:8000/mcp, named mcp__vault_tools__<name> for the model)` - 65 edges
7. `PayeeVault` - 58 edges
8. `simulate()` - 56 edges
9. `set_threshold()` - 51 edges
10. `record_mutations()` - 45 edges

## Surprising Connections (you probably didn't know these)
- `Hitting a limit: catat_usulan, then sudah kucatat di /usulan` --semantically_similar_to--> `/usulan (posts the waiting proposals again with their buttons)`  [AMBIGUOUS] [semantically similar]
  services/hermes/vault/SOUL.md → docs/RUNBOOK.md
- `/mcp surface (model-facing; aliases and amounts only, no tool stores or reveals a full number)` --semantically_similar_to--> `Security and data rules (no re-reading recorded documents, max 2 reads per answer, alias plus last 4 digits only, no CVV or expiry, no URLs)`  [INFERRED] [semantically similar]
  docs/SECURITY.md → services/hermes/vault/SOUL.md
- `/rincian handled in pre_gateway_dispatch with skip plus direct Bot API send` --semantically_similar_to--> `/rincian (destination numbers grouped per destination; the only place full numbers appear)`  [INFERRED] [semantically similar]
  docs/ARCHITECTURE.md → services/hermes/vault/SOUL.md
- `A rejected submit is fixed per its reason, never gamed; new services, host scripts, plugins and secret values are the owner's own work` --semantically_similar_to--> `Never in a proposal: host scripts, compose, plugins, control itself, secrets (new service = escalation; secret via make secret-set); at most five wait`  [INFERRED] [semantically similar]
  services/hermes/front/SOUL.md → docs/SECURITY.md
- `main()` --indirect_call--> `e()`  [INFERRED]
  scripts/fetch-cuti.py → services/vault-tools/vault_tools/reports.py

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
- **Card-repayment remedy (the finding, mutations.card_paid, wajib:kartu, own_last4 accounts only, the transfer_internal guard, the data fix, deploy.sh and the deploy)** — docs_progress_card_as_own_account_finding, docs_progress_card_repayment_fix, docs_progress_mutations_card_paid, docs_progress_wajib_kartu, docs_progress_own_last4, docs_progress_card_payment_transfer_internal_guard, docs_progress_card_internal_data_fix, docs_progress_card_internal_deploy_sh, docs_progress_card_internal_deploy [EXTRACTED 1.00]
- **Doubled Mandiri rows remedy (the finding, record_mutations overlap matching, the BUKU TIDAK COCOK ledger check and audit rule 8, the data fix, deploy.sh and the deploy)** — docs_progress_doubled_mandiri_rows_finding, docs_progress_overlap_date_amount_matching, docs_progress_buku_tidak_cocok_ledger_gap, docs_progress_audit_rule_8_ledger_gap, docs_progress_mandiri_dupes_data_fix, docs_progress_mandiri_dupes_deploy_sh, docs_progress_mandiri_dupes_deploy [EXTRACTED 1.00]
- **Front go-live on 2026-11-01 (secrets set, prune fixed, start, rendered env checked, one-shot submit test, test proposal #2)** — docs_progress_front_live, docs_progress_telegram_front_token, docs_progress_anthropic_front_key, docs_progress_prune_sh_fix, docs_progress_front_start, docs_progress_front_rendered_env, docs_progress_front_oneshot_submit_test, docs_progress_test_proposal_2 [EXTRACTED 1.00]
- **M3 approval flow (front asks, control posts its own diff, the owner taps, the applier applies; live since 2026-11-01 23:24 WIB)** — docs_progress_front_agent, docs_progress_change_proposals, docs_progress_submit_tool, docs_progress_proposals_inbox, docs_progress_control_v3, docs_progress_proposal_review, docs_progress_control_state, docs_progress_applier, docs_progress_setujui_applies_front_diff [EXTRACTED 1.00]
- **M3 install steps on 2026-11-01 (pre-checks, make deploy with the data folders, install.sh with its host checks and units, control v3 migrated)** — docs_progress_m3_install_prechecks, docs_progress_m3_make_deploy, docs_progress_applier_data_folders, docs_progress_applier_units_install_sh, docs_progress_applier_install_host_checks, docs_progress_pa_applier_units, docs_progress_applier_outcome_files, docs_progress_control_v3_after_install [EXTRACTED 1.00]
- **M4 comms decisions the owner makes before anything is built (permissions, sending kept out by the broker, Google consent, its own bot, Anthropic key, card-bus)** — docs_progress_oq18_m4_comms, docs_progress_m4_comms, docs_progress_comms_permissions_choice, docs_progress_comms_broker_blocks_sending, docs_progress_comms_google_oauth_client, docs_progress_telegram_comms_token, docs_progress_comms_anthropic_workspace, docs_progress_card_bus [EXTRACTED 1.00]
- **Own-record merge rules (same bank, coverage gate, merged duplicates, correction, lepas, cash never merges)** — docs_progress_merge_receipts_same_bank, docs_progress_record_merge_coverage_gate, docs_progress_duplicate_check_merged, docs_progress_merged_record_correction, docs_progress_lepas_unmerge, docs_progress_cash_never_merges_tunai, docs_progress_id_reuse_fix_45dfc1e [EXTRACTED 1.00]
- **Vault zone on internal net-vault: Hermes gateway, vault-tools MCP server and squid-vault** — docs_runtime_containers_personal_agent_vault_1, docs_runtime_containers_personal_agent_vault_tools_1, docs_runtime_containers_personal_agent_squid_vault_1, docs_runtime_containers_personal_agent_net_vault, docs_runtime_vault_tools_mcp_server [EXTRACTED 1.00]
- **Applier changes and deploys: deploy-guard holds the applier around make deploy, make applied-pull brings its VPS-side changes into the checkout as commits** — docs_runtime_infra_files_services_applier, docs_runtime_infra_files_make_applied_pull, docs_runtime_infra_files_scripts_applied_pull_py, docs_runtime_infra_files_make_deploy, docs_runtime_infra_files_scripts_deploy_guard_sh, docs_runtime_infra_files_deploy_guard_holds_applier [EXTRACTED 1.00]
- **Plan and pot computed from the pre-salary state (usulan #9 and #10)** — docs_runtime_state_usulan_9, docs_runtime_state_usulan_10, docs_runtime_state_pre_salary_baseline, docs_runtime_state_pot_simulation, docs_runtime_state_tunda_pot_bulan, docs_runtime_state_rincian_rencana_commands, docs_runtime_state_payday_plan [EXTRACTED 1.00]
- **restic backup lifecycle through backup.sh (daily backup, monthly integrity check, weekly retention)** — docs_runtime_timers_pa_backup, docs_runtime_timers_pa_check, docs_runtime_timers_pa_forget, docs_runtime_timers_backup_sh, docs_runtime_timers_restic [EXTRACTED 1.00]
- **Applier gates before an approved front change is written (approved file matching control.db, front files only, the diff the owner saw whole and unchanged since, zone rules and squid parse, backup then recreate and check)** — docs_security_applier_input, docs_security_applier_front_files, docs_security_applier_exactly_what_owner_saw, docs_security_applier_rules_before_writing, docs_security_applier_writing_and_checking [EXTRACTED 1.00]
- **M3 change approval chain (front submit, change-proposals, proposals-inbox, control shows its own diff and decides on the owner's tap, the applier applies an approved front change and reports the outcome once)** — services_hermes_front_soul_submit_tool, docs_security_change_proposals, docs_architecture_proposals_inbox, docs_security_owner_sees_control_diff, docs_security_only_control_decides, docs_architecture_control_state, docs_security_applier_contract, docs_security_applier_reporting [EXTRACTED 1.00]
- **Payday cycle on the 1st (status_gajian, sisa_uang_harian, generate_payday_plan, periksa_data, recording tools, saldo_rekening)** — services_hermes_vault_soul_payday_list_flow, services_hermes_vault_soul_status_gajian, services_hermes_vault_soul_sisa_uang_harian, services_hermes_vault_soul_generate_payday_plan, services_hermes_vault_soul_periksa_data, services_hermes_vault_soul_payday_recording_tools, services_hermes_vault_soul_saldo_rekening [EXTRACTED 1.00]
- **Per-zone squid proxies are the only members of the egress network** — docs_architecture_squid_vault, docs_architecture_squid_front, docs_architecture_squid_comms, docs_architecture_squid_ctl, docs_architecture_egress_network [EXTRACTED 1.00]
- **Statement import tool flow** — docs_runtime_bot_activity_list_uploads, docs_runtime_bot_activity_pending_statements, docs_runtime_bot_activity_ingest_statement, docs_runtime_bot_activity_skip_statement_file, docs_runtime_bot_activity_record_statement, docs_runtime_bot_activity_list_statements, docs_runtime_bot_activity_record_mutations, docs_runtime_bot_activity_record_card_installments [INFERRED 0.75]
- **Marking payday-plan payments as done by kind (cards, debt installments, other transfers, one-off bills), read back by status_gajian** — docs_runtime_hermes_record_card_payment, docs_runtime_hermes_cicilan_dibayar, docs_runtime_hermes_transfer_selesai, docs_runtime_hermes_tagihan_sekali, docs_runtime_hermes_status_gajian, docs_runtime_hermes_generate_payday_plan [INFERRED 0.75]
- **Front stack up on 2026-11-01 04:34 UTC: front and change-proposals containers, first squid-front traffic** — docs_runtime_state_front_container, docs_runtime_state_change_proposals_container, docs_runtime_state_squid_front, docs_runtime_state_squid_front_startup_hosts, docs_runtime_state_containers_now [INFERRED 0.75]
- **Weekly prune removes the idle ingest-gmail image and the next daily ingest rebuilds it** — docs_runtime_state_pa_prune, docs_runtime_state_docker_prune_log, docs_runtime_state_ingest_gmail_image_build, docs_runtime_state_pa_ingest, docs_runtime_state_ingest_gmail_container [INFERRED 0.75]
- **Morning statement ingest (06:00 WIB) followed by the Notion snapshot (06:30 WIB) from vault-tools through squid-vault** — docs_runtime_timers_pa_ingest, docs_runtime_timers_ingest_gmail, docs_runtime_timers_pa_notion, docs_runtime_timers_vault_tools_notion_sync, docs_runtime_timers_personal_agent_vault_tools_1, docs_runtime_proxies_api_notion_com, docs_runtime_proxies_squid_vault [INFERRED 0.75]
- **Card-internal step on the live ledger (2026-11-01): the pre-card-internal backup with, in the same snapshot, transfer_internal rules down from 249 to 243, wajib:kartu rules up from 6 to 10 and change_log up from 20 to 34 rows** — docs_runtime_vault_tools_ledger_bak_pre_card_internal, docs_runtime_vault_tools_ledger_db, docs_runtime_vault_tools_category_transfer_internal, docs_runtime_vault_tools_category_wajib_kartu, docs_runtime_vault_tools_table_category_rules, docs_runtime_vault_tools_table_change_log [INFERRED 0.75]
- **Deploy 2 on the live ledger (2026-11-01): pre-deploy2 backup, schema user_version 14 with the new one_off_bills table, biaya_admin_* thresholds, vault-tools image rebuilt 10:26 WIB** — docs_runtime_vault_tools_ledger_bak_pre_deploy2, docs_runtime_vault_tools_ledger_db, docs_runtime_vault_tools_table_one_off_bills, docs_runtime_vault_tools_threshold_biaya_admin, docs_runtime_vault_tools_ledger_py, docs_runtime_host_image_personal_agent_vault_tools, docs_runtime_containers_personal_agent_vault_tools_1 [INFERRED 0.75]
- **Mandiri duplicate-rows data fix on the live ledger (2026-11-01): pre-mandiri-dupes backup, mandiri-utama rows in transactions and mutation_files, change_log entries** — docs_runtime_vault_tools_ledger_bak_pre_mandiri_dupes, docs_runtime_vault_tools_ledger_db, docs_runtime_vault_tools_account_mandiri_utama, docs_runtime_vault_tools_table_transactions, docs_runtime_vault_tools_table_mutation_files, docs_runtime_vault_tools_table_change_log [INFERRED 0.75]
- **DNS-over-HTTPS fallback containment (no route out of the zone containers, squid-vault denies DoH, the fallback transport uses the zone proxy)** — docs_assumptions_open_doh_fallback, docs_assumptions_zone_containers_no_route, docs_assumptions_telegram_fallback_proxy, docs_architecture_squid_vault, docs_architecture_internal_only_networks [INFERRED 0.85]
- **Applier safety chain (control's own diff as the review, zone rules, squid -k parse, old files back on failure, outcomes through control, the make deploy guard and applied-pull)** — docs_progress_control_v3, docs_progress_proposal_review, docs_progress_zone_rules, docs_progress_squid_parse_check, docs_progress_applier_restore_on_failure, docs_progress_applier, docs_progress_make_deploy_applied_guard, docs_progress_make_applied_pull [INFERRED 0.85]
- **Vault cardguard owner check rollout (built, found never on the VPS, pre-checked, synced and restarted by the doubled-rows deploy, live since 2026-11-01 20:13 WIB, with the sweep_ttl delete count)** — docs_progress_cardguard_owner_check, docs_progress_cardguard_owner_check_not_on_vps, docs_progress_cardguard_is_owner_precheck, docs_progress_mandiri_dupes_deploy_sh, docs_progress_mandiri_dupes_deploy, docs_security_cardguard_owner_check_live, docs_security_earlier_cardguard_any_private_chat, docs_assumptions_sweep_ttl_delete_count, docs_progress_ttl_sweep_check [INFERRED 0.85]
- **Daily money computation (top-up plus leftover, anchored by the daily-account reading)** — docs_progress_payday_living_money, docs_progress_cash_to_hold, docs_progress_living_leftover_spent, docs_progress_living_account_constant, docs_progress_living_balance_report, docs_progress_living_balance_mark, docs_progress_spending_pace, docs_progress_uang_harian_bulan_ini [INFERRED 0.85]
- **Deploy 2 delivered across the progress log, the payday spec and SOUL (admin fees, bills paid once, instalment undo, grace period, data fix, schema 14)** — docs_progress_deploy_2, docs_progress_admin_fees, docs_progress_tagihan_sekali, docs_progress_cicilan_dibayar_batal, docs_progress_stop_grace_period, docs_progress_deploy_2_data_fix, docs_progress_schema_v14_one_off_bills, docs_progress_deploy_2_deploy, docs_payday_admin_fees, docs_payday_bills_paid_once, services_hermes_vault_soul_admin_fees, services_hermes_vault_soul_tagihan_sekali, services_hermes_vault_soul_cicilan_dibayar_batal [INFERRED 0.85]
- **Payday progress records (schema v13 tables and the tools that write and read them)** — docs_progress_schema_v13_payment_tables, docs_progress_card_payments_table, docs_progress_debt_payments_table, docs_progress_plan_progress_table, docs_progress_fund_reports_table, docs_progress_status_gajian, docs_progress_transfer_selesai, docs_progress_cicilan_dibayar [INFERRED 0.85]
- **Pot planning flow (schedule, pattern, simulator, plan, roadmap)** — docs_progress_pot_hutang_teman, docs_progress_pot_schedule, docs_progress_atur_jadwal_pot, docs_progress_pot_pattern_sisa, docs_progress_simulasi_skenario, docs_progress_payday_plan, docs_progress_roadmap [INFERRED 0.85]
- **Deploys while the applier is installed (make deploy holds the applier and refuses while the VPS has an applied change this checkout lacks; make applied-pull brings it in; a stale hold is ended with deploy-guard.sh)** — docs_security_applier_deploys_and_repo, docs_runbook_deploy_while_installed, docs_runbook_make_applied_pull, docs_runbook_deploy_guard_hold, docs_runbook_make_deploy [INFERRED 0.85]
- **Applier install at the M3 gate, 2026-11-01 23:22-23:24 WIB (the owner's go-ahead, make deploy carrying control v3 with its own diff, install.sh with its host check and units, one run skipping the test #1 as decided before the install time)** — docs_security_applier_prerequisites, docs_runbook_applier_install, docs_runbook_control_v3_deploy, docs_runbook_make_deploy, docs_runbook_applier_install_sh, docs_security_applier_install_marker, docs_security_test_1_skip_record [INFERRED 0.85]
- **Context compression machinery** — docs_runtime_bot_activity_context_compression, docs_runtime_bot_activity_preflight_compression, docs_runtime_bot_activity_pre_api_compression, docs_runtime_bot_activity_compression_blocked, docs_runtime_bot_activity_session_compressed_warning, docs_runtime_bot_activity_auxiliary_compression_model, docs_runtime_bot_activity_sessions_compression_columns, docs_runtime_bot_activity_busy_input_mode, docs_runtime_bot_activity_compression_reply_anchor [INFERRED 0.85]
- **Gateway SIGTERM shutdown and revive cycle** — docs_runtime_bot_activity_gateway_restart_lifecycle, docs_runtime_bot_activity_s6_supervise, docs_runtime_bot_activity_shutdown_phases, docs_runtime_bot_activity_shutdown_notification, docs_runtime_bot_activity_gateway_state_persist, docs_runtime_bot_activity_container_boot_log, docs_runtime_bot_activity_gateway_shutdown_diag_log, docs_runtime_bot_activity_unclean_previous_life [INFERRED 0.85]
- **Change-proposal path: the front gateway holds CHANGE_PROPOSALS_MCP_TOKEN and reaches change-proposals directly (NO_PROXY), which shares the proposals-inbox with control** — docs_runtime_containers_personal_agent_front_1, docs_runtime_containers_env_change_proposals_mcp_token, docs_runtime_containers_env_front_no_proxy, docs_runtime_containers_personal_agent_change_proposals_1, docs_runtime_containers_secret_change_proposals_mcp_token, docs_runtime_containers_mount_proposals_inbox, docs_runtime_containers_personal_agent_control_1 [INFERRED 0.85]
- **Numbers computed by code, never by the model** — docs_runtime_hermes_periksa_data, docs_runtime_hermes_generate_payday_plan, docs_runtime_hermes_simulasi_skenario, docs_runtime_hermes_belanja_kartu, docs_runtime_hermes_health_check, docs_runtime_hermes_cashflow_summary [INFERRED 0.85]
- **Full card and account numbers kept out of the bot (tokens, alias plus last 4 digits)** — docs_runtime_hermes_cardguard_plugin, docs_runtime_hermes_upsert_card, docs_runtime_hermes_upsert_account, docs_runtime_hermes_list_payees [INFERRED 0.85]
- **Statement intake: Telegram uploads and the ingest-gmail queue into recorded statements and transactions** — docs_runtime_hermes_list_uploads, docs_runtime_hermes_uploads_cache, docs_runtime_hermes_ingest_statement, docs_runtime_hermes_record_statement, docs_runtime_hermes_record_mutations, docs_runtime_hermes_pending_statements, docs_runtime_hermes_skip_statement_file, docs_runtime_hermes_ingest_events, docs_runtime_hermes_ingest_gmail_job [INFERRED 0.85]
- **Front zone live: anthropic_front_key and telegram_front_token secrets, front.env and the hermes-front data dir on the host, the front gateway with change-proposals and squid-front on net-front** — docs_runtime_host_secret_anthropic_front_key, docs_runtime_host_secret_telegram_front_token, docs_runtime_host_hermes_front_dir, docs_runtime_host_front_env, docs_runtime_containers_personal_agent_front_1, docs_runtime_containers_personal_agent_change_proposals_1, docs_runtime_containers_personal_agent_squid_front_1, docs_runtime_containers_personal_agent_net_front, docs_runtime_proxies_squid_front [INFERRED 0.85]
- **Secret provisioning path (entered or generated on the VPS, kept in the secrets dir, mounted as compose secrets)** — docs_runtime_infra_files_make_secret_set, docs_runtime_infra_files_make_secret_gen, docs_runtime_infra_files_make_pdf_passwords, docs_runtime_infra_files_plaintext_secrets_stay_on_vps, docs_runtime_host_opt_personal_agent_secrets, docs_runtime_host_compose_secrets_mount [INFERRED 0.85]
- **restic backup lifecycle (backup, integrity check, retention of the data dir)** — docs_runtime_infra_files_host_pa_backup, docs_runtime_infra_files_host_pa_check, docs_runtime_infra_files_host_pa_forget, docs_runtime_infra_files_scripts_backup_sh, docs_runtime_infra_files_make_backup, docs_runtime_host_opt_personal_agent_data, docs_runtime_host_secret_restic_env [INFERRED 0.85]
- **Telegram upload relay flow (Hermes document cache to the ingest folder, 90-day retention)** — docs_runtime_infra_files_hermes_vault_document_cache, docs_runtime_infra_files_host_pa_uploads, docs_runtime_infra_files_scripts_sync_uploads_sh, docs_runtime_infra_files_upload_retention_90_days, docs_runtime_host_hermes_vault_dir, docs_runtime_host_ingest_dir [INFERRED 0.85]
- **Live-vs-repo drift checks made by the runtime map collector (deployed files, systemd units, squid configs)** — docs_runtime_readme_collect_py, docs_runtime_readme_deploy_drift, docs_runtime_timers_live_vs_repo_unit_drift, docs_runtime_proxies_live_configs_match_repo [INFERRED 0.85]
- **Card-internal data fix on 2026-11-01 23:12 WIB: backup, change_log edits of category_rules and transactions, internal transfers recategorised** — docs_runtime_state_card_internal_fix, docs_runtime_state_backup_pre_card_internal, docs_runtime_state_change_log_table, docs_runtime_state_category_rules_table, docs_runtime_state_transactions_table, docs_runtime_state_category_transfer_internal, docs_runtime_state_category_wajib [INFERRED 0.85]
- **Deploy 2: admin fees and one-off bills shipped (usulan #4 and #6)** — docs_runtime_state_deploy_2, docs_runtime_state_usulan_4, docs_runtime_state_usulan_6, docs_runtime_state_admin_fee_estimate, docs_runtime_state_tagihan_sekali, docs_runtime_state_one_off_bills_table, docs_runtime_state_backup_pre_deploy2, docs_runtime_state_payday_plan [INFERRED 0.85]
- **Daily Gmail statement ingest path (pa-ingest, ingest-gmail run, squid-vault, Google APIs)** — docs_runtime_state_pa_ingest, docs_runtime_state_ingest_gmail_container, docs_runtime_state_squid_vault, docs_runtime_state_gmail_googleapis_com, docs_runtime_state_oauth2_googleapis_com, docs_runtime_state_pa_gmail_token, docs_runtime_state_doc_files_table, docs_runtime_state_processed_messages_table [INFERRED 0.85]
- **M3 deploy on 2026-11-01 about 23:22 WIB: pre-m3 backup, control, vault-tools and vault restart, applier installed, no deploy drift left** — docs_runtime_state_m3_deploy, docs_runtime_state_backup_pre_m3, docs_runtime_state_control_container, docs_runtime_state_vault_tools_container, docs_runtime_state_vault_container, docs_runtime_state_pa_applier, docs_runtime_state_deploy_drift, docs_runtime_bot_activity_hermes_gateway [INFERRED 0.85]
- **Mandiri duplicates data fix on 2026-11-01: backup, change_log deletions and the mutation file edit** — docs_runtime_state_mandiri_dupes_fix, docs_runtime_state_backup_pre_mandiri_dupes, docs_runtime_state_change_log_table, docs_runtime_state_transactions_table, docs_runtime_state_mutation_files_table, docs_runtime_state_mandiri_utama [INFERRED 0.85]
- **Autodebit debts paid manually before the debit date (usulan #5, #7, #8)** — docs_runtime_state_usulan_5, docs_runtime_state_usulan_7, docs_runtime_state_usulan_8, docs_runtime_state_autodebit, docs_runtime_state_spaylater_debt, docs_runtime_state_car_instalment_debt, docs_runtime_state_debt_payments_table, docs_runtime_state_held_balance [INFERRED 0.85]
- **restic check and retention locked out at 04:00 on 2026-11-01** — docs_runtime_state_pa_check, docs_runtime_state_pa_forget, docs_runtime_state_restic_repo_lock, docs_runtime_state_restic_backup, docs_runtime_state_restic_check_temp_cache, docs_runtime_state_restic_cache_warning, docs_runtime_state_host_timers [INFERRED 0.85]
- **Owner-approved front change flow: control writes an approval into control-state/approved, pa-applier.path (or the 5-minute timer) starts applier.py on the host, and its outcome comes back to control read-only at /outcome** — docs_runtime_containers_personal_agent_control_1, docs_runtime_timers_control_state_approved, docs_runtime_timers_pa_applier, docs_runtime_timers_applier_py, docs_runtime_host_applier_dir, docs_runtime_containers_mount_applier_outcome [INFERRED 0.85]
- **Encrypted payee secrets: payee_secrets nonce, ciphertext and match_hash with vault_tools_key and cryptography** — docs_runtime_vault_tools_table_payee_secrets, docs_runtime_containers_secret_vault_tools_key, docs_runtime_vault_tools_cryptography_package [INFERRED 0.85]
- **Statement ingest: ingest-gmail and pa-uploads fill /ingest, PDFs become statements and mutation files** — docs_runtime_vault_tools_ingest_gmail, docs_runtime_vault_tools_pa_uploads, docs_runtime_vault_tools_ingest, docs_runtime_vault_tools_pdf_parsing_packages, docs_runtime_vault_tools_table_doc_files, docs_runtime_vault_tools_table_statements, docs_runtime_vault_tools_table_mutation_files [INFERRED 0.85]
- **Front card-number defense (cardblock drops card-like digit runs before dispatch, front's SOUL handles card photos and other numbers, detection kept equal to vault's cardguard)** — docs_security_cardblock_plugin, docs_progress_cardblock_plugin, docs_runbook_cardblock_plugin, docs_security_cardblock_limits, services_hermes_front_soul_card_messages_removed, services_hermes_front_soul_sensitive_numbers_rule, docs_progress_cardguard_plugin [INFERRED 0.85]
- **Test approvals the applier never applied (#1 approved with Setujui and skipped at the install as skipped/1.json; #2 front's test skill, rejected by the owner on 1 Nov)** — docs_progress_test_proposal_1, docs_progress_test_proposal_2, docs_security_test_approvals_never_applied, docs_progress_applier, docs_security_applier_contract, docs_security_test_1_skip_record [INFERRED 0.85]

## Communities (217 total, 53 thin omitted)

### Community 0 - "Card Statement Line Parsing"
Cohesion: 0.20
Nodes (12): Accuracy, add_statement(), card_world(), Recovery, Store, _all_instalments(), categorize(), format_summary() (+4 more)

### Community 1 - "Hermes Runtime Probes"
Cohesion: 0.12
Nodes (29): activity(), config(), day(), db_profile(), defaults_module(), engine(), fkind(), flatten() (+21 more)

### Community 2 - "Card Spending Summary and Per-Card Detail (belanja_kartu)"
Cohesion: 0.22
Nodes (7): PerCard, _card(), card_detail(), format_detail(), _netted(), summary(), belanja_kartu()

### Community 3 - "Cardguard Plugin (Number Guard, Menu, Control Bot)"
Cohesion: 0.18
Nodes (18): _bot(), _chunks(), _delete_async(), _digits_of(), find_numbers(), _luhn(), _notify(), on_inbound() (+10 more)

### Community 4 - "Runtime Map Overview, Host Timers and pa-* Units"
Cohesion: 0.08
Nodes (47): api.notion.com, Runtime map collector (ops/runtime-map/collect.py), containers.md (every container: image, user, command, env names, mounts, networks, limits, hardening; changes on deploy), graphify-out/GRAPH_REPORT.md (where to start in the project graph), graphify query, path and explain commands, /graphify --update in Claude Code (refresh the project graph for docs), hermes-defaults.md (every DEFAULT_CONFIG key of the engine with its default and doc comment, plus OPTIONAL_ENV_VARS; changes on Hermes upgrade), Hermes engine graph (hermes-agent v0.22.5, local only, too big for git) (+39 more)

### Community 5 - "Vault-Tools Data Dir, Ledger Backups and Change Log"
Cohesion: 0.28
Nodes (13): transfer_internal category (243 rules), wajib:kartu category (10 rules), /data/cuti_bersama.json (cuti bersama: 21 entries for 2026, 19 for 2027), /data (vault-tools data directory), holidays package (0.107), ledger.db.bak-pre-card-internal (ledger copy taken before the card-internal step, with -shm and -wal sidecars, 2026-11-01), ledger.db.bak-pre-* backups (47 copies dated 2026-10-27 to 2026-11-01), ledger.db.bak-pre-deploy2 (ledger copy taken before Deploy 2, with -shm and -wal sidecars, 2026-11-01) (+5 more)

### Community 6 - "Report Renderers, Subscriptions and Audit Tests"
Cohesion: 0.26
Nodes (20): check(), _anggaran(), b(), _banks(), _belanja(), bln(), _cicilan(), _data() (+12 more)

### Community 7 - "Shared Imports, Ledger Connections and Ops Scripts"
Cohesion: 0.04
Nodes (21): get(), main(), notify(), read_json(), main(), collect(), main(), merge() (+13 more)

### Community 8 - "Front Change Applier (applier.py)"
Cohesion: 0.15
Nodes (3): main(), squid_complaints(), stamp()

### Community 9 - "Live MCP Tool Catalog"
Cohesion: 0.07
Nodes (53): add_owner_name (add the owner's name exactly as printed in account transactions), apply_suggestions (apply category suggestions for the named descriptions; empty applies all), atur_jadwal_pot (set how a pot, an earmarked fund with a deadline, is filled), belanja_kartu (card spending breakdown per cycle from statement lines already read by code; never read the PDF for this), budget_status (budget use per category for a month, default the current one), card_installments_status (running card installments: x of y, months left and total remaining), Proposed skill card-spend-breakdown-advisory (productivity, created 2026-10-28, pending approval), cashflow_summary (monthly cash flow: income, spending, difference, savings ratio, per category; computed by code) (+45 more)

### Community 10 - "Bot Activity: Tool Calls, Tool Usage and Prompt Snapshots (state.db)"
Cohesion: 0.04
Nodes (72): Bot activity snapshot, mcp__vault_tools__add_owner_name, mcp__vault_tools__apply_suggestions, mcp__vault_tools__atur_jadwal_pot, Vault tool names called without the MCP prefix, mcp__vault_tools__belanja_kartu, mcp__vault_tools__budget_status, mcp__vault_tools__card_installments_status (+64 more)

### Community 11 - "Bank Mutation Recording, Rules and Tests"
Cohesion: 0.17
Nodes (12): show(), acct_db(), Mutations, rows(), is_discretionary(), cashflow(), format_cashflow(), ledger_gap() (+4 more)

### Community 12 - "Hermes Home, Engine Install, Credentials and Stores"
Cohesion: 0.06
Nodes (55): runtime/active_sessions.json (active-session entries), logs/agent.log (INFO and above: 9 ERROR, 473 WARNING, 753 distinct templates), api_server platform (OpenAI-compatible, 127.0.0.1:8642, reachable only inside the container; connected, no requests), cardguard plugin v0.1 (replaces card numbers in inbound Telegram text with tokens before dispatch; spike), cardguard TTL file (ttl/rincian.jsonl: /rincian messages to delete after expiry; 0 lines), channel_directory.json (chats the gateway knows: one telegram entry), logs/container-boot.log (boot diagnostics, 64 lines), cron/executions.db executions table (0 rows) (+47 more)

### Community 13 - "Applier Self-Checks, Zone Tests and Prechecks"
Cohesion: 0.11
Nodes (4): Applier, run(), sha(), write_json()

### Community 14 - "Gateway Lifecycle and Messages"
Cohesion: 0.09
Nodes (29): Agent budget: max_iterations=40, agent.deadline: task timed out and abandoned, logs/agent.log, cardguard capability_check: tools.override denied, cardguard number guard (amounts not from the tools), Config migration skipped (hermes_cli.post_update), Conversation loop API calls and turn re-anchoring, Credential pool: no available entries (+21 more)

### Community 15 - "Cardguard Tests and Cardblock Plugin"
Cohesion: 0.08
Nodes (3): CardGuard, ev(), Fake

### Community 16 - "Card and Debt Payments, Undo and Paid-by-Hand"
Cohesion: 0.08
Nodes (18): UndoInstalment, CardPayment, Instalments, Migration, pay_as_on_30_oct(), plan_of(), Progress, stmt() (+10 more)

### Community 17 - "Rupiah Formatting, Text Cleaning and Shared Helpers (money.py, mutations.py)"
Cohesion: 0.05
Nodes (34): plan(), Money, log(), format_health(), _give(), _given(), merge_receipts(), _merged_note() (+26 more)

### Community 18 - "Payday Plan Builder (payday.py)"
Cohesion: 0.12
Nodes (13): BuildPlan, fixed(), amounts_of(), Engine, dummy(), Properties, WorkedExample, build_plan() (+5 more)

### Community 19 - "Egress Proxies (squid) Runtime Map"
Cohesion: 0.21
Nodes (20): config/squid/comms.conf (read-only as /etc/squid/squid.conf), config/squid/ctl.conf (read-only as /etc/squid/squid.conf), config/squid/vault.conf (read-only as /etc/squid/squid.conf), api.anthropic.com, api.telegram.org, Denied: AWS IMDSv2 credential probes to the instance-metadata address (/latest/api/token, iam/security-credentials), Denied: DNS-over-HTTPS fallbacks of the HTTP clients (dns.google, cloudflare-dns.com), Denied: Hermes model-catalog and provider refreshes (hermes-agent.nousresearch.com, raw.githubusercontent.com, openrouter.ai, portal.nousresearch.com) (+12 more)

### Community 20 - "Daily Money Pace and Purchase Alerts (health.py)"
Cohesion: 0.13
Nodes (8): LivingMoneyPace, alerts_for(), _by_balance(), living_anchor(), record_expense(), spending_pace(), _spent_by_category(), _th()

### Community 21 - "Payee Vault, Rincian and Calibration Tests"
Cohesion: 0.04
Nodes (38): fees_world(), Gate, Plan, Rule, Simulation, Advice, amounts(), DueBeforePayday (+30 more)

### Community 22 - "Runtime Map Collector"
Cohesion: 0.16
Nodes (29): amounts(), cell(), deep_scrub(), engine_refs(), fence(), header(), listener_note(), local_tree() (+21 more)

### Community 23 - "Ledger Schema (v13 Tables)"
Cohesion: 0.08
Nodes (34): accounts, balance_reports, card_installment_scans, card_installments, card_lines, card_payments, cards, category_keywords (+26 more)

### Community 24 - "Debt Roadmap, Thresholds and Calibration Tests"
Cohesion: 0.08
Nodes (18): world(), CardPath, CardPayments, Dates, LatestStatement, Recurring, Roadmap, statement() (+10 more)

### Community 25 - "Pot Simulation, Admin Fees and Plan Invariants"
Cohesion: 0.10
Nodes (12): PlanStaysAfterPaying, Consumers, CardsFirstPot, EmergencyFund, Simulate, simulasi_skenario(), _bln(), format_result() (+4 more)

### Community 26 - "Makefile Targets, Stack Settings, Deploy Guard and Host Units"
Cohesion: 0.06
Nodes (54): restart unless-stopped (every container), authorized_keys (root: 0 entries, ubuntu: 1), docker daemon.json (json-file log driver, max-size 10m, max-file 3), Docker disk use (6 images, 9 containers, 8 local volumes, 129 build cache entries), Docker 29.9.2 and Compose 5.6.1 on the VPS, /etc/cron.d entries (e2scrub_all, sgagenttask, sysstat, yunjing), fail2ban (inactive), Host firewall (active; deny incoming except 22/tcp, allow outgoing, deny routed) (+46 more)

### Community 27 - "Runbook: Applier Install, Deploys and Recovery"
Cohesion: 0.20
Nodes (19): Applier (M3, installed 2026-11-01 23:23 WIB): services/applier applies a front change the owner approved in control, Applier install (done 2026-11-01 23:22-23:24 WIB on the owner's go-ahead at the M3 gate; again only after an uninstall, and only with the owner's go-ahead): make deploy, then services/applier/install.sh on the VPS; from then on the card says the applier applies exactly the diff above it, services/applier/install.sh: the host check runs first, changes nothing and stops at the first FAIL; then the install time is recorded, pa-applier.path and pa-applier.timer are enabled and one run skips the approvals from before (the test #1), Look at the applier: journalctl -u pa-applier.service, and sudo ls of applier/applied, applier/failed and applier/skipped; a record holds hashes and reasons, Applier units pa-applier.service, pa-applier.path and pa-applier.timer (in services/applier/systemd/, not host/), Applier uninstall: disable pa-applier.path and pa-applier.timer, remove the three units from /etc/systemd/system, daemon-reload, then remove applier/outcome/applier.json, Control v3 deploy (2026-11-01 23:22 WIB): since then control posts the diff it computed itself before every card, Hold left by a deploy that stopped halfway: end it with bash scripts/deploy-guard.sh end (+11 more)

### Community 28 - "Applier Tests (test_applier.py)"
Cohesion: 0.08
Nodes (8): Agreement, Apply, Base, FakeDocker, Install, proposal(), RealZoneTests, sha()

### Community 29 - "Zones, Containers and Squid"
Cohesion: 0.08
Nodes (53): Anonymous squid log and spool volumes (8, from image VOLUME lines), cap_drop ALL (every container except vault: change-proposals, control, front, the four squids, vault-tools), change-proposals healthcheck (Python TCP connect to 127.0.0.1:8000, 3 s timeout), Compose project personal-agent (compose/docker-compose.yml), Containers runtime map (compose project personal-agent), control.py (python -I control.py, workdir /app), CHANGE_PROPOSALS_MCP_TOKEN (front env name), control proxy env (HTTPS_PROXY http://squid-ctl:3128, NO_PROXY localhost) (+45 more)

### Community 30 - "Approvals Flow and Proposal Folders (Architecture)"
Cohesion: 0.20
Nodes (16): Applier (services/applier, a root host unit; installed 2026-11-01 23:23 WIB): applies an approved front change and writes applier/outcome/<id>.json, applier/outcome folder (the applier, a root host unit, writes; control reads it read-only), Approvals flow (M3): front submit -> proposals-inbox -> control re-validates, posts its own diff against the installed files, then the card -> the owner's tap recorded in control-state -> the applier applies an approved front change and writes applier/outcome/<id>.json, which control reports once, change-proposals (front zone, M3, submit tool), Control posts the diff it computes itself against the installed files (read-only mounts of services/hermes/front/ and config/squid/), then the card, control-state folder (control only writes; the applier reads approved/ and control.db read-only), scripts/data-dirs.sh (creates the M3 folders), proposals-inbox folder (change-proposals writes, control reads and empties it) (+8 more)

### Community 31 - "Receipt Merge Rules and Resent Screenshots"
Cohesion: 0.12
Nodes (7): _Banks, LateRecordsAndResentScreenshots, MergeRules, RecordExpense, spend(), list_uncategorized(), list_uncategorized()

### Community 32 - "Gmail Sender Authentication (auth.py)"
Cohesion: 0.17
Nodes (6): auth_ok(), _clauses(), from_address(), safe_label(), Auth, hdrs()

### Community 33 - "Spending Analysis (Budget Baseline)"
Cohesion: 0.18
Nodes (10): Analysis, Monthly, tx(), world(), analyse(), card_charges(), format_analysis(), monthly() (+2 more)

### Community 34 - "MCP Server App, Budgets and Tool Flow Tests"
Cohesion: 0.03
Nodes (37): Rincian, Rincian, ThroughTheTools, ThroughTheTools, ThroughTheTools, ThroughTheTools, Tools, ThroughTheTools (+29 more)

### Community 35 - "Egress, Containers and Telegram Polling (State)"
Cohesion: 0.14
Nodes (32): Telegram fallback-IP discovery via DNS-over-HTTPS, Hermes model catalog fetch failing (urlopen Tunnel error), api.anthropic.com (Anthropic API; 1060 requests via squid-vault, 16 via squid-front), api.telegram.org (Telegram Bot API; the busiest allowed host on squid-vault, squid-ctl and squid-front, 4539 requests via squid-front), change-proposals container (personal-agent-change-proposals-1; running and healthy since 2026-11-01), Containers now: 9 running, 0 restarts, no OOM, exit 0, control container (personal-agent-control-1; running since 2026-11-01 16:22 UTC, 0 log lines in 7 days), Denied: dns.google and cloudflare-dns.com (66 requests each) (+24 more)

### Community 36 - "Holiday Fetch Decisions, Overrides and Tests"
Cohesion: 0.17
Nodes (8): Override, Parse, candidate_days(), load_year(), merge_file(), parse_github(), parse_ics_cuti(), render_diff()

### Community 37 - "Health Check, Budget Status and Debt Load (health.py)"
Cohesion: 0.11
Nodes (12): Budgets, cash_month(), Health, Pace, planned(), account_balances(), budget_status(), debt_load() (+4 more)

### Community 38 - "Ledger Database and Tables (Runtime)"
Cohesion: 0.25
Nodes (15): SQLite ledger /data/ledger.db (schema user_version 14, WAL journal), ledger-schema.sql (ledger DDL), card_installment_scans (ledger table, 25 rows), card_installments (ledger table, 26 rows), card_lines (ledger table, 1066 rows), cards (ledger table, 7 rows), debt_payments (ledger table, 2 rows), debts (ledger table, 2 rows) (+7 more)

### Community 39 - "Sinking Fund Tests"
Cohesion: 0.18
Nodes (9): fund(), InThePlan, Math, row(), setup(), Validation, _not_a_card_bill(), set_category() (+1 more)

### Community 40 - "Gmail Ingest Run and Its Tests"
Cohesion: 0.21
Nodes (3): FakeClient, message(), Run

### Community 42 - "Runbook (M1-M3): VPS Setup and Front Start"
Cohesion: 0.14
Nodes (16): Runbook (M1), Finding 2026-11-01: getMe showed Allow Groups still on for @danoevault_agent and @danoecontrol_bot, Hermes configs drop groups (allowed_chats: none); control drops them in code, Blocked-domain egress test (example.com via squid-ctl from control must return 403), BotFather bots (usernames end in bot, Allow Groups off), First-time VPS setup (each step needs owner approval), Gate checks for M1, make preflight (read-only: KVM, Ubuntu 24.04, enough disk) (+8 more)

### Community 43 - "Category Suggestions (suggest.py)"
Cohesion: 0.09
Nodes (13): Suggestions, card_paid(), set_category_keyword(), add_owner_name(), apply_suggestions(), set_category_keyword(), suggest_categories(), add_owner_name() (+5 more)

### Community 44 - "Progress Hub: Bots, Zones and Milestones"
Cohesion: 0.08
Nodes (67): No direct route out of the zone containers (ENETUNREACH to Hermes' seed Telegram IPs from vault, front, vault-tools, control and change-proposals; external names do not resolve), allowed_chats: none (both Hermes configs; drops every group, keeps DMs), anthropic_front_key secret (set by the owner on 2026-11-01 09:09 WIB), api.notion.com (allowed through squid-vault), Applier (services/applier: writes, deploys and health-checks an approved front change; built 2026-11-01, installed 2026-11-01 23:23 WIB), The applier, built (M3, 2026-11-01 afternoon); installed 23:23 WIB, Applier data folders (applier/ root 0700, applier/outcome/ root 0755; made by make deploy), Applier install's eight host checks (control.db read-only with the review column, approved/ a folder, regular files, tests/test_zones.py on the installed tree, front and squid-front running, squid -k parse on front.conf, front's Telegram state, root's state folders) (+59 more)

### Community 45 - "Live Catalog: Payday, Bill and Instalment Tools, Ledger Masking"
Cohesion: 0.29
Nodes (11): Bank admin fees (estimates given by the owner, kept as thresholds through set_threshold), cicilan_dibayar (record one debt installment already paid, e.g. a car loan or SPayLater), cicilan_dibayar batal flag (optional boolean, default false: cancel a debt installment recorded as paid), generate_payday_plan (deterministic payday plan; without a payday it plans the running one), sisa_uang_harian (record last month's leftover daily money the owner still holds just before the salary arrives), status_gajian (progress of the running payday plan according to the ledger: paid, unpaid, paid outside the plan), tagihan_sekali (a bill paid once, outside subscriptions and fixed expenses, such as arrears or a repair; aksi picks the action, with optional alias, name, amount, due date, pay-to, method, date and note), transfer_selesai (mark payday-plan transfers the owner has made, other than cards and installments, such as fixed expenses) (+3 more)

### Community 46 - "Host Data Dirs, Env Files and Control/Applier Paths (Runtime)"
Cohesion: 0.15
Nodes (18): change-proposals env (PROPOSALS_INBOX_DIR; no proxy env), Control env (MY_TELEGRAM_ID value masked, TELEGRAM_TOKEN_FILE, PROPOSALS_INBOX_DIR, CONTROL_STATE_DIR, APPLIER_OUTCOME_DIR, CONTROL_REPO_DIR), /opt/personal-agent-data/applier/outcome (read-only at /outcome, control), /opt/personal-agent-data/control-state (rw at /state, control), /opt/personal-agent-data/proposals-inbox (rw at /inbox, change-proposals and control), telegram_control_token secret (read-only at /run/secrets, control), applier data dir (mode 0700, root-owned), canary.txt (root-owned file in the data dir, mode 0644) (+10 more)

### Community 47 - "Host Probe Script (probe_host.py)"
Cohesion: 0.14
Nodes (22): containers(), deployed_tree(), docker_logs(), images(), listening(), mixed(), networks(), opt_layout() (+14 more)

### Community 49 - "Hermes Agent Settings and Toolsets (Live)"
Cohesion: 0.08
Nodes (26): agent.reasoning_effort high (not in DEFAULT_CONFIG; a per-model override would win), auxiliary.compression: claude-sonnet-5-5 via anthropic (default auto), auxiliary config section (139 keys; our compression, title_generation and vision models on anthropic), auxiliary.title_generation: claude-haiku-5-5 via anthropic (default auto), catat_usulan (record a proposal when the bot hits a limit: a missing tool, calculation or command, instead of a workaround), Hermes config backups (backups/config.yaml.good.*, five from 2026-10-28 to 2026-11-01), DEFAULT_CONFIG sections table (100 top-level sections with line, key count and the keys we set), Hermes profile config.yaml (read-only bind mount of services/hermes/vault/config.yaml, identical to the repo) (+18 more)

### Community 50 - "Payday Tests, Masking and Money Helpers"
Cohesion: 0.19
Nodes (6): Masking, Masking, luhn_valid(), _mask_digits(), mask_sensitive(), repl()

### Community 51 - "Card Installments (card_installments.py)"
Cohesion: 0.15
Nodes (11): Installments, OneCardOneAlias, Overview, world(), active(), _add_months(), format_list(), monthly_total() (+3 more)

### Community 52 - "Bills Paid Once (one_off.py) and Placement Tests"
Cohesion: 0.09
Nodes (22): amounts(), bill_world(), catat(), Flows, Placement, Simulation, ThroughTheTools, cancel() (+14 more)

### Community 53 - "Security: Egress, Squid Proxies and Sender Checks"
Cohesion: 0.14
Nodes (25): Control zone and control service (approvals, no LLM, net-ctl), egress network (the four squid proxies only, to the internet), squid-comms proxy (allowlist), squid-ctl proxy (api.telegram.org only), squid-front proxy (web, private ranges blocked), squid-vault proxy (allowlist), Closed: the DNS-over-HTTPS fallback cannot bypass the proxy, Spike 1: read-only config.yaml and plugins mount (pass) (+17 more)

### Community 54 - "Ledger, Deploys and Data-Fix Backups"
Cohesion: 0.10
Nodes (47): sweep_ttl logs how many deletes Telegram accepted (counts only), Vault bot token rotation (2026-10-28), Read-only pre-check in the vault container with the new cardguard module (the allowlist holds exactly the owner; _is_owner true for the owner's DM only, not a group or another id; card detection unchanged), Front follow-up live 2026-11-01 20:13 WIB: vault's cardguard acts only for the owner in a private chat, Finding: vault's cardguard owner check (built 2026-11-01 14:54 WIB) never reached the VPS; the plugin there hashed as the recalibration commit's, cardguard plugin (Hermes), category_keywords (owner-explained names, stored in the ledger, never in the repo), /bantuan report command (help) (+39 more)

### Community 55 - "Recording Completeness Tests"
Cohesion: 0.47
Nodes (3): acct_db(), Completeness, r()

### Community 56 - "Vault-Tools Probe Script (probe_vault_tools.py)"
Cohesion: 0.19
Nodes (12): cuti(), data_files(), day(), fkind(), fname(), free(), ledger(), money_free() (+4 more)

### Community 57 - "Hermes Engine Image, Install and Bundled Plugins"
Cohesion: 0.11
Nodes (19): auth.json (Hermes credential store and pool, empty; the API key comes from env; never opened by the collector), Bundled engine plugins (browser, computer_use, context_engine, cron_providers, delegation, image_gen, kanban, memory, model-providers, platforms, web and others), TZ Asia/Jakarta (container timezone), Docker embedded DNS (container-local tcp and udp listeners), Engine image nousresearch/hermes-agent (release date 2026.9.24), ANTHROPIC_API_KEY env var (where the Anthropic key comes from; value never read), Hermes .env in HERMES_HOME (mode 0600, never opened by the collector), Hermes Agent v0.22.5 (vault bot engine, Telegram bot @danoevault_agent, container personal-agent-vault-1) (+11 more)

### Community 58 - "Hermes Gateway Containers (Vault, Front)"
Cohesion: 0.19
Nodes (21): cardblock plugin (services/hermes/front/plugins/cardblock, read-only at /opt/data/plugins/cardblock), cardguard plugin (services/hermes/vault/plugins/cardguard, read-only at /opt/data/plugins/cardguard), ANTHROPIC_API_KEY (vault and front env name), Hermes path env (HERMES_HOME and HERMES_WRITE_SAFE_ROOT /opt/data, HERMES_PYTHON, HERMES_RUNTIME_DIR, HERMES_TUI_DIR, HERMES_WEB_DIST, PLAYWRIGHT_BROWSERS_PATH, XDG_RUNTIME_DIR), HERMES_SKIP_CONFIG_MIGRATION=1 (vault and front env), Hermes Telegram env (TELEGRAM_BOT_TOKEN; TELEGRAM_ALLOWED_USERS and TELEGRAM_HOME_CHANNEL values masked), TZ (vault and front Asia/Jakarta; squids UTC), services/hermes/front/config.yaml (read-only at /opt/data/config.yaml) (+13 more)

### Community 59 - "Compose Secrets"
Cohesion: 0.11
Nodes (19): file, file, file, file, file, secrets, change_proposals_mcp_token, gmail_ingest_client (+11 more)

### Community 60 - "Front Cardblock Plugin Tests (CardBlock)"
Cohesion: 0.20
Nodes (4): CardBlock, failing(), slow(), ev()

### Community 61 - "Control Bot Core and Diff Posting (Control class)"
Cohesion: 0.19
Nodes (3): auto_reason(), Control, outcome_text()

### Community 62 - "Statement PDF Intake and Sanitizing"
Cohesion: 0.12
Nodes (11): ingest_statement(), record_statement(), decrypt(), _extract_clean(), extract_text(), ingest_file(), ingest_file_parts(), load_passwords() (+3 more)

### Community 63 - "Hermes config.yaml (Repo)"
Cohesion: 0.13
Nodes (14): approvals, destructive_slash_confirm, compression, min_tail_user_messages, threshold_tokens, plugins, enabled, security (+6 more)

### Community 64 - "Ledger Cards, Card Payees and Subscriptions"
Cohesion: 0.16
Nodes (14): bca-9706 (bca card; statement day 12, due day 28, transfer to num-9706), cimb-9888 (cimb card; statement day 19, due day 7, transfer to num-9888), dbs-5685 (DBS card; statement day 25, due day 10, transfer to num-5685), hsbc-5915 (HSBC card; statement day 19, due day 4, transfer to num-5915), mandiri-4365 (mandiri card; statement day 16, due day 5, paid via app_menu), mega-5855 (Mega card; statement day 22, due day 7, transfer to num-5855), langganan category (1 rule), num-* card payees (num-0480, num-1111, num-4365, num-5685, num-5855, num-5915, num-9706, num-9888; no card in the cards table ends in 1111) (+6 more)

### Community 65 - "Expense Recording, Corrections, Deletion and Debt Payments"
Cohesion: 0.09
Nodes (10): CorrectedSourceFindsItsStatementRow, Edit, log(), OnlyTheOwnersRecords, pho(), world(), delete_expense(), list_expenses() (+2 more)

### Community 66 - "Ledger Thresholds, Budgets and Plans"
Cohesion: 0.10
Nodes (25): jago-darurat (Jago savings account), belanja-harian category (3 rules), belanja-online category (15 rules), berhenti:supir category (12 rules), biaya-bank category (48 rules), bunga category (24 rules), donasi category (7 rules), gaji category (9 rules) (+17 more)

### Community 67 - "Hermes Assumptions, Architecture and Vault-Tools Surfaces"
Cohesion: 0.10
Nodes (30): Architecture (M1 skeleton), brokers (comms zone, M4), card-bus MCP (replaces Kanban, M4), Comms zone (email and calendar, net-comms; comms, brokers, card-bus in M4), Hermes pin: nousresearch/hermes-agent v0.22.5 (manifest digest recorded, checked 2026-10-27), ingest folder (ingest-gmail writes, vault-tools reads read-only; statement drop), ingest-gmail (timer job on net-vault, writes the ingest folder), /rincian handled in pre_gateway_dispatch with skip plus direct Bot API send (+22 more)

### Community 68 - "Payday Plan Spec (Funding Order, Worked Example)"
Cohesion: 0.13
Nodes (19): Payday plan spec (vault_tools/payday.py), Bills paid once (2026-11-01): an open one is an essential in the plan of every payday after the day it was recorded whose window reaches its due date, Tier 4: card remaining balance (default: pay in full), Tier 1: card minimum due, Estimated cost of delay per shortfall (amount * late_cost_bp / 10000, rounded half up), Kartu dbs-1111 (dummy card alias in the example), Tier 3: debt installments and pool-account transfers, Tier 2: essentials (fixed expenses, e.g. school; bills paid once) (+11 more)

### Community 69 - "Control Bot Auth and Applied-Outcome Tests"
Cohesion: 0.16
Nodes (6): handle(), is_authorized(), AppliedTests, AuthTests, HandleTests, msg()

### Community 70 - "Payday Plan, Debts, Balances and Usulan (State Snapshot)"
Cohesion: 0.11
Nodes (37): mcp__vault_tools__saldo_rekening, mcp__vault_tools__simulasi_skenario, Autodebit (autodebet) of debt instalments, Ledger backups made 2026-10-28: pre-answers, calibrate, cardbudget, cardlines, daily-account, dedupe, dedupe-cards, ef-pocket, flazz-fix, held-balance, invariants, keywords, latest, notion, pot-schedule, recal-v2, recurring, rules2, scenarioA, balance_reports table (6 rows: mandiri-utama 4, jago-harian 2), Car instalment debt (cicilan-mobil): due 2 Nov paid manually 30 Oct, 18 instalments left, next autodebit 2 Dec, card_payments table (7 rows, one payment per card, last 2026-10-28 to 2026-10-30), sekali: one-off categories (e.g. coway-tunggakan, jht, jual-emas, medis, pelunasan-kartu) (+29 more)

### Community 71 - "Compose Logging Options"
Cohesion: 0.22
Nodes (16): logging, logging, logging, logging, driver, options, max-file, max-size (+8 more)

### Community 72 - "Compose: ingest-gmail Service and Env Settings"
Cohesion: 0.14
Nodes (14): build, cap_drop, cpus, depends_on, mem_limit, networks, profiles, read_only (+6 more)

### Community 73 - "Compose: vault-tools and ingest-gmail Services"
Cohesion: 0.08
Nodes (26): environment, environment, APPLIER_OUTCOME_DIR, CONTROL_REPO_DIR, CONTROL_STATE_DIR, HTTPS_PROXY, MY_TELEGRAM_ID, NO_PROXY (+18 more)

### Community 74 - "Calibration Runbook and Reviews"
Cohesion: 0.07
Nodes (30): Bot calibration runbook (manual, on the owner's request), ops/calibration/bot_usage.py (cost per day and source at list prices), cardguard plugin (appends the number-guard flag), Change and verify, docker compose up -d --build vault-tools, Hermes cost_status unknown for claude-sonnet-5-5 (compare by hand), Data review (read-only), Deploy procedure (from the worktree root) (+22 more)

### Community 75 - "Audit and Report Rendering Tests"
Cohesion: 0.10
Nodes (18): Audit, found(), line(), stmt(), world(), SubscriptionLog, OwnerRules, Subscriptions (+10 more)

### Community 76 - "Card Statement Recording and Reconciliation Tests (record_statement)"
Cohesion: 0.32
Nodes (3): card_db(), RecordStatement, record_statement()

### Community 77 - "Compose Service: control"
Cohesion: 0.14
Nodes (14): build, cap_drop, cpus, depends_on, mem_limit, networks, oom_score_adj, read_only (+6 more)

### Community 78 - "Compose Service: vault (Hermes)"
Cohesion: 0.14
Nodes (14): vault, command, cpu_shares, cpus, depends_on, env_file, image, mem_limit (+6 more)

### Community 80 - "Notion Sync, Client and Page Rendering (notion_sync.py)"
Cohesion: 0.11
Nodes (19): FakeNotion, Sync, bullet(), heading(), main(), Notion, NotionError, para() (+11 more)

### Community 81 - "Living Money and Cash to Hold"
Cohesion: 0.19
Nodes (13): cash_to_hold (salary minus funded minus fees), daily_allowance (cash_to_hold // days_in_window, salary part only, stored never shown), fees (plan output list: date, destination, amount, kind kartu or transfer), living_leftover (last cycle's leftover the owner still held), living_leftover_spent (cash spent from the payday until the leftover was reported), living_money = cash_to_hold + living_leftover (the owner's daily money for the window), Plan output (transfers, fees, cash_to_hold, daily_allowance, warnings), Salary (plan input) (+5 more)

### Community 82 - "Front Compose Service"
Cohesion: 0.10
Nodes (20): path, required, cap_add, cap_drop, command, cpu_shares, cpus, depends_on (+12 more)

### Community 83 - "Payday Plan Generation and Advisor Tests"
Cohesion: 0.10
Nodes (14): BalanceCheck, car(), InThePlan, Rules, setup(), seeded(), Tools, saldo_rekening() (+6 more)

### Community 85 - "Compose Service: squid-comms"
Cohesion: 0.17
Nodes (12): squid-comms, cap_add, cap_drop, cpus, image, mem_limit, networks, oom_score_adj (+4 more)

### Community 86 - "Compose Service: squid-ctl"
Cohesion: 0.17
Nodes (12): squid-ctl, cap_add, cap_drop, cpus, image, mem_limit, networks, oom_score_adj (+4 more)

### Community 87 - "Compose Service: squid-front"
Cohesion: 0.17
Nodes (12): squid-front, cap_add, cap_drop, cpus, image, mem_limit, networks, oom_score_adj (+4 more)

### Community 88 - "Compose Service: squid-vault"
Cohesion: 0.11
Nodes (18): name, services, squid-vault, cap_add, cap_drop, cpus, image, mem_limit (+10 more)

### Community 89 - "Gmail OAuth and Sender Allowlist"
Cohesion: 0.33
Nodes (12): Gmail OAuth guide (readonly) for ingest-gmail, Bank sender allowlist with DKIM/DMARC pass (DBS, CIMB Niaga, HSBC, Mandiri, Mega), Gmail API (gmail.googleapis.com, oauth2.googleapis.com), Gmail readonly token (gmail_ingest_token), Google Cloud project personal-agent-ingest (Gmail API enabled), ingest-desktop OAuth client (gmail_ingest_client), ingest-gmail (daily deterministic job, no LLM), Keuangan/Kartu Kredit Gmail label (looked up by label ID) (+4 more)

### Community 90 - "Card, Statement and Instalment Tables (State Snapshot)"
Cohesion: 0.17
Nodes (20): Ledger backups made 2026-10-27: pre-v4, v5, v6, v8, v9, categorize, completeness, instkey, owner-names, pending, perantara, pocketfix, scans, subs, bca-9706 card (10 statements 2026-01-12 to 2026-10-12, last due 2026-10-28; 8 instalment rows), card_installment_scans table (25 rows, 25 scanned statements), card_installments table (26 instalment rows across 5 cards), Card line kinds (belanja 493, biaya 134, bunga 36, cicilan 109, langganan 181, pembayaran 78, refund 35), card_lines table (1066 card statement lines), cards table (7 cards; all statements reconciled, lines ok 0 per card), perantara: pass-through categories (3 values, 37 transactions) (+12 more)

### Community 92 - "Graph-First Hook (graph_first.py)"
Cohesion: 0.26
Nodes (7): behind(), ignore_patterns(), ignored(), main(), md5(), snapshot(), wib()

### Community 94 - "Ledger Tables and Backups (State Snapshot)"
Cohesion: 0.09
Nodes (46): mcp__vault_tools__periksa_data, mcp__vault_tools__record_expense, mcp__vault_tools__record_mutations, accounts table (8 rows), ledger.db.bak-pre-card-internal (with -shm and -wal copies), ledger.db.bak-pre-deploy2 (with -shm and -wal copies), ledger.db.bak-pre-m3 (with -shm and -wal copies), ledger.db.bak-pre-mandiri-dupes (with -shm and -wal copies) (+38 more)

### Community 96 - "Deploy 2 Data Fix"
Cohesion: 0.24
Nodes (5): allocation(), copy(), plan(), report(), say()

### Community 98 - "Compose Networks"
Cohesion: 0.20
Nodes (10): internal, internal, internal, internal, networks, egress, net-comms, net-ctl (+2 more)

### Community 99 - "Compose Squid Template"
Cohesion: 0.20
Nodes (10): x-squid, cap_add, cap_drop, cpus, image, mem_limit, oom_score_adj, restart (+2 more)

### Community 100 - "Card Statements, Payment Targets and Reports"
Cohesion: 0.09
Nodes (34): Biggest avoidable costs (game/digital top-ups; late/overlimit fees and interest), belanja_kartu (per-card statement lines, long numbers masked), BCA card, CIMB card, HSBC card, Card installments (x/y) tracking per scanned statement, Jenius card, Mandiri card (paid via the app menu) (+26 more)

### Community 101 - "Expense Correction Tests (edit_expense, test_corrections.py)"
Cohesion: 0.24
Nodes (3): MergedRecords, edit_expense(), _merged_target()

### Community 102 - "Change-Proposal Submission Tests"
Cohesion: 0.16
Nodes (5): create_app(), main(), FakeTelegram, good(), Proposals

### Community 103 - "Hermes Auxiliary Models"
Cohesion: 0.20
Nodes (10): auxiliary, compression, title_generation, vision, model, provider, model, provider (+2 more)

### Community 104 - "Hermes MCP Server Config"
Cohesion: 0.20
Nodes (10): Authorization, mcp_servers, vault_tools, prompts, resources, connect_timeout, headers, timeout (+2 more)

### Community 105 - "Change-Proposals Compose Service"
Cohesion: 0.12
Nodes (16): context, dockerfile, build, cap_drop, cpu_shares, cpus, mem_limit, networks (+8 more)

### Community 107 - "Gmail Ingest Job: Messages, PDFs and Retention (run.py)"
Cohesion: 0.28
Nodes (10): main(), Config, emit(), _headers(), _pdf_parts(), process_message(), run(), _save_pdf() (+2 more)

### Community 108 - "Vault-Tools Surfaces (/mcp and /internal) and Requirements"
Cohesion: 0.19
Nodes (13): Spike 7: MCP over HTTP with a bearer token from env (pass), Statement reconciliation (statements that do not reconcile; every statement must re-read as cocok), holidays input (holiday list supplied and kept current by the owner, open item), /mcp surface (model-facing; aliases and amounts only, no tool stores or reveals a full number), Payee encryption key vault_tools_key (make secret-gen on the VPS, never overwritten, backed up with restic), Surface tokens (random, at least 32 chars, must differ, constant-time compare; unknown paths 404), vault-tools requirements.txt, cryptography 50.0.2 (+5 more)

### Community 109 - "State Snapshot: Timers, Jobs, Restic and Runs"
Cohesion: 0.09
Nodes (30): docs/runtime/README.md, State snapshot, api.notion.com (Notion API; 370 requests via squid-vault), applier journal line: #N skipped (1 in 7 days), pa-disk log line disk N% (133 runs in 7 days), pa-prune journal: unused images untagged and deleted, space reclaimed, gmail.googleapis.com (Gmail API; 428 requests via squid-vault), Host systemd timers and jobs (pa-*; pa-check and pa-forget failed on 2026-11-01, the rest succeeded) (+22 more)

### Community 110 - "Gmail API Client (GmailClient)"
Cohesion: 0.15
Nodes (3): GmailClient, GmailError, TokenError

### Community 111 - "Control Proposal Store"
Cohesion: 0.14
Nodes (4): now(), read_proposal(), Store, write_json()

### Community 113 - "Progress: Receipt Merges, Record Fixes and 1 Nov Recalibration"
Cohesion: 0.07
Nodes (53): PROGRESS.md: progress and resume point (finance / vault), jago-harian account (daily pocket), jago-utama account (one Jago statement file for every pocket), Accuracy layers (owner: 99.99% accuracy, no miscalculation), Bot calibration from the owner's real chat (2026-10-28), Branch worktree-m1-skeleton, draft PR #1, Cash budgets (listrik, internet, transport; count account payments), Cash records never merge (record_expense: exactly one of account_alias, card_alias, tunai=true) (+45 more)

### Community 114 - "Applied-Pull Host Script (applied-pull.py)"
Cohesion: 0.36
Nodes (7): fetch(), git(), load_control(), main(), problem(), pull(), sha()

### Community 116 - "Vault SOUL: Payday List and Owner Rules"
Cohesion: 0.07
Nodes (20): Auto-debit debts (upsert_debt pay_method=autodebit; one figure per account incl. the bank-held minimum), belanja_kartu (/belanja: statement lines per cycle and per card; not reading PDFs), catat_usulan (records a missing capability or number for /usulan), Daily living account (uang-harian at Jago; the owner spends daily only from it), Digital subscription rules (subscriptions_status; upsert_subscription only after the owner confirms; stored notes kept), health_check verdict (decided by the tool, not changed or softened; 2-3 concrete options), Frequently asked numbers, always labelled (no defisit unless tool output), Long-list commands (/rencana, /tagihan, /belanja, /cicilan, /anggaran, /peta, /kondisi, /data, /periksa) (+12 more)

### Community 117 - "Statement Line Counting and Completeness"
Cohesion: 0.16
Nodes (7): Counting, make_pdf(), ThroughTheTools, count_dated_lines(), count_signed_lines(), count_transactions(), _first_money_is_real()

### Community 118 - "Zone Isolation and Egress Tests"
Cohesion: 0.11
Nodes (7): Compose, Egress, HermesProfiles, leaves(), load(), mounts(), unlisted()

### Community 119 - "Report Builder and Usulan Report Tests (test_reports.py)"
Cohesion: 0.24
Nodes (5): check_html(), Reports, world(), UsulanReport, build()

### Community 121 - "Statement Reconciliation (reconcile.py)"
Cohesion: 0.36
Nodes (3): Reconcile, reconcile(), Reconciliation

### Community 122 - "Front Hermes Config"
Cohesion: 0.13
Nodes (14): approvals, destructive_slash_confirm, plugins, enabled, security, allow_lazy_installs, sessions, retention_days (+6 more)

### Community 124 - "Hermes Telegram Gateway Config"
Cohesion: 0.33
Nodes (6): allowed_chats, disable_link_previews, gateway, platforms, telegram, extra

### Community 126 - "Gmail Ingest Sender Config (load_senders)"
Cohesion: 0.31
Nodes (3): load_senders(), b64(), SenderConfig

### Community 127 - "Hermes Agent Block"
Cohesion: 0.50
Nodes (4): agent, disabled_toolsets, max_turns, reasoning_effort

### Community 128 - "Hermes Memory Settings"
Cohesion: 0.50
Nodes (4): memory, memory_enabled, user_profile_enabled, write_approval

### Community 129 - "Cardguard Plugin Manifest"
Cohesion: 0.50
Nodes (3): description, name, version

### Community 130 - "Approvals, Control Zone and Applier (Contract and Runbook)"
Cohesion: 0.11
Nodes (20): Control commands /status (counts, with the applier's outcomes), /usulan (re-post waiting proposals with their buttons), /ping, Control bot @danoecontrol_bot (M3, live since 2026-11-01, owner only), Since control v3 (deployed 2026-11-01 23:22 WIB) control posts the diff it computed itself before every card, Read control state without printing nonces (control.db opened read-only, counts and statuses only), Front submit path tested on 1 Nov with a one-shot (sudo docker exec personal-agent-front-1 hermes chat --oneshot -q; the hermes shim drops to front's unprivileged uid): proposal #2 appeared in the control bot, /ping, Proposal card (summary, permission change, files, risk, rollback; Setujui/Tolak work once), /status (waiting, approved, rejected, invalid counts) (+12 more)

### Community 131 - "Hermes Session Store and Telegram Delivery"
Cohesion: 0.10
Nodes (25): Preflight-compression log line (shows the threshold in force when it was written), Log line 'Re-anchored stale current_turn_user_idx' (agent/turn_iteration_prep.py; counts mid-turn compactions), Logger agent.context_compressor (69 INFO), Logger agent.conversation_compression (292 INFO), Gateway session keys (agent:main:local:dm 38, agent:main:telegram:dm 1, plus _README), sessions/sessions.json (gateway session key to session, with token and cost counters; 39 keys), sessions.retention_days 90 (same as the default: inactive days of ended-session history kept), state.db (sessions, messages, model usage, delivery obligations, routing, admissions, system prompts; SQLite WAL) (+17 more)

### Community 132 - "Progress: Doubled Mandiri Rows, Overlap Matching and Card-Repayment Fix"
Cohesion: 0.13
Nodes (43): Mandiri account (salary lands here; auto-debit account), apply_suggestions (stores the suggested categories; now skips a refused group and names it), periksa_data audit rule 8: the ledger gap reported as a MASALAH, Bank mutations Jan-Oct (BCA, Mandiri, Jago; verified complete, October BCA CSV reconciled), BUKU TIDAK COCOK warning (ledger_gap): the account's rows over the file's period no longer add up to its balance change, Finding: since a 2026-10-28 commit suggest.groups counted the owner's cards among the own accounts, so four September card repayments (cimb-9888, dbs-5685, hsbc-5915, mega-5855) were stored as transfer_internal and are missing from September's cashflow expenses, Data fix ops/datafix/2026-11-01-card-internal (backup ledger.db.bak-pre-card-internal; the four card rules and rows to wajib:kartu, the two pocket rules and four rows to bunga / biaya-bank; 14 change_log rows), Card-repayment fix deploy (2026-11-01 23:12:14-23:13:18 WIB on the owner's go-ahead; vault restarted 23:12:57) (+35 more)

### Community 133 - "Front Auxiliary Models"
Cohesion: 0.20
Nodes (10): auxiliary, compression, title_generation, vision, model, provider, model, provider (+2 more)

### Community 137 - "Front Change-Proposals MCP"
Cohesion: 0.20
Nodes (10): connect_timeout, headers, timeout, tools, url, Authorization, mcp_servers, change_proposals (+2 more)

### Community 138 - "Hermes Telegram Adapter, Plugins and Delivery"
Cohesion: 0.27
Nodes (8): Log line 'Cold boot: dropping Telegram updates' (Telegram adapter), Logger hermes_plugins.platforms__telegram.adapter (870 INFO, 284 WARNING, 2 ERROR), Logger plugins.platforms.telegram.telegram_network (65 INFO), state.db conversation_generations table (1 row, source telegram), state.db delivery_obligations table (196 Telegram deliveries, all delivered, 2026-10-27 to 2026-11-01), gateway.platforms.telegram.extra.disable_link_previews true (read by the Telegram adapter), Telegram platform adapter (plugins/platforms/telegram/adapter.py; state connected), telegram_update_receipts JSON file in HERMES_HOME

### Community 139 - "Bot Activity: Sessions, Context Compression and /new Resets"
Cohesion: 0.17
Nodes (16): Compression summary call and aux_model telemetry, background_review model task, busy_input_mode demoted while compression is in flight, Child sessions (a compaction or /new continues the chat), claude-sonnet-5-5 (vault bot model), Compression blocked (ineffective, structural_backoff), Compression folded away the just-delivered reply, Context compression (compaction) (+8 more)

### Community 140 - "Front Agent Persona and Setup"
Cohesion: 0.15
Nodes (8): cardblock plugin (services/hermes/front/plugins/cardblock, mounted read-only): drops every inbound message holding a Luhn-valid 13-19 digit run before Hermes dispatches it, Hermes does not bound hooks by its hook timeout; every blocking call in the plugins has its own timeout, Asisten umum pemilik (front), Gaya jawaban, Keamanan, Keuangan BUKAN di sini (tidak bisa ditawar), Mengubah dirimu sendiri, Yang kamu kerjakan

### Community 142 - "Front Telegram Chat Filter"
Cohesion: 0.33
Nodes (6): allowed_chats, disable_link_previews, gateway, platforms, telegram, extra

### Community 143 - "Statement PDF Ingest Tests"
Cohesion: 0.22
Nodes (6): make_pdf(), McpIngest, PdfIntake, file_sha256(), ingest(), sanitize()

### Community 144 - "Front Memory Settings"
Cohesion: 0.40
Nodes (5): memory, memory_enabled, nudge_interval, user_profile_enabled, write_approval

### Community 145 - "Applied-Pull Tests (test_applied_pull.py)"
Cohesion: 0.41
Nodes (3): AppliedPull, committed(), sha()

### Community 146 - "Vault Tools Module (tools.py)"
Cohesion: 0.03
Nodes (73): PotBalance, PaydayDates, Holidays, cash_spent(), commitments(), bp_of(), is_working_day(), last_working_day() (+65 more)

### Community 148 - "Hermes Engine Tools and Tool Search"
Cohesion: 0.25
Nodes (8): auxiliary.vision: claude-sonnet-5-5 via anthropic (default auto), clarify engine tool, Engine tools besides MCP (only clarify and vision_analyze; the row still counts 56 vault_tools tools from the latest tool-schema snapshot while the schema cache section lists 57), Tool names in old sessions from 27-28 Oct (tool_call, tool_search, tool_describe, terminal, session_search, skill_view, unprefixed MCP names), Logger tools.tool_search (13 INFO), Logger tools.vision_tools (114 INFO), cache/mcp_schema_cache.json (vault_tools tool-schema cache: 57 tools, no utility tools), vision_analyze engine tool

### Community 149 - "Front Agent Limits"
Cohesion: 0.50
Nodes (4): agent, disabled_toolsets, image_input_mode, max_turns

### Community 150 - "Control Bot (control.py) and Deploy Guard Tests"
Cohesion: 0.14
Nodes (8): buttons(), discard(), hidden_chars(), main(), read_installed(), review_of(), sha(), Telegram

### Community 151 - "Hermes Kanban Store (kanban.db)"
Cohesion: 0.33
Nodes (6): kanban.db (kanban store; toolset disabled, every table empty), kanban.db kanban_notify_subs table (0 rows), kanban.db task_attachments table (0 rows), kanban.db task_comments table (0 rows), kanban.db task_events table (0 rows), kanban.db tasks table (0 rows)

### Community 156 - "Front Model Setting"
Cohesion: 0.67
Nodes (3): model, default, provider

### Community 157 - "Front Cardblock Plugin (cardblock/__init__.py)"
Cohesion: 0.26
Nodes (8): _bot(), _digits_of(), find_numbers(), _luhn(), on_inbound(), _owner_ids(), register(), _tell_owner()

### Community 158 - "Vault Tool Search Setting"
Cohesion: 0.67
Nodes (3): enabled, tools, tool_search

### Community 159 - "Infrastructure Files: Dockerfiles, Compose and Squid Allowlists"
Cohesion: 0.06
Nodes (64): /opt/personal-agent-data/vault-tools (rw at /data), notion_token secret (read-only at /run/secrets), vault_tools_key secret (read-only at /run/secrets), hermes-front data dir (mode 0700, no longer empty), nousresearch/hermes-agent image (no tag, created 2026-10-23), personal-agent-ingest-gmail image (latest, created 2026-11-01 06:00 WIB), ubuntu/squid:6.6-24.04_edge image, ingest-state dir (mode 0755) (+56 more)

### Community 162 - "Deploy Drift, SOUL Mount and Skills Prompt Snapshot"
Cohesion: 0.33
Nodes (7): Bundled Hermes skills (12 categories; the skills toolset is disabled, so the model cannot load them), .skills_prompt_snapshot.json (cached skills index for the system prompt; 68-entry manifest, written 2026-10-27), SOUL.md (the bot's persona and rules; read-only bind mount of services/hermes/vault/SOUL.md, identical to the repo), state.db system_prompts table (66 prompts keyed by hash), Deploy drift at collection time (198 repo files vs 197 in /opt/personal-agent, 180 identical; runtime files that differ, not deployed yet or only on the VPS: none; 18 docs/ops/tests files not deployed or different, harmless), Runtime files that differ from /opt/personal-agent: none, Runtime files not deployed yet: none

### Community 163 - "Ingest Data Dir and Upload Relay (pa-uploads)"
Cohesion: 0.38
Nodes (6): /opt/personal-agent-data/ingest (read-only at /ingest), ingest data dir (mode 0755), Hermes vault document cache (hermes-vault/cache/documents), pa-uploads.path + service + timer (relays Telegram uploads to the ingest folder), scripts/sync-uploads.sh (upload relay and retention sweep), scripts/sync-uploads.sh (upload relay to the ingest folder and 90-day retention)

### Community 166 - "Progress: Recalibration v2, Payday Plans and Daily Money Rules"
Cohesion: 0.05
Nodes (76): fee_estimate (simulation fees after cycle 1: one per fixed cost, instalment paid by transfer, card with a bill now, pot, emergency fund and the living money), Admin fees (/usulan #4: the owner's estimates per card payment and per other transfer; the Mandiri card via the bank-app menu and the auto-debits cost nothing), atur_jadwal_pot (saves the pot schedule after the owner agrees; pola, pakai_gaji_hari_tenggat), Auto-debits from Mandiri (car instalment MTF, SPayLater), balance_reports table (bank-app balance reported by the owner), biaya_admin_mulai (fees count from the 30 Nov payday, 20261130), Bot model config (reasoning_effort high, claude-sonnet-5-5 vision and compression, Haiku titles), Car instalment (MTF, incl. admin; auto-debit on day 2) (+68 more)

### Community 167 - "Gmail Token Check Script (gmail-token-check.py)"
Cohesion: 0.39
Nodes (4): days_left(), main(), message(), notify()

### Community 168 - "Fixed Expenses and Children's Fees"
Cohesion: 0.15
Nodes (14): berhenti:trip-mancing category (1 owner keyword), komisi-allianz category (1 owner keyword), perantara:art-belanja-anak category (1 owner keyword), sekali:keluarga-istri category (1 owner keyword), wajib:ipl category (10 rules), wajib:les category (4 owner keywords), wajib:sekolah category (3 rules), Children's lesson fees (3 les-* fixed expenses due day 1, each to a BCA account payee) (+6 more)

### Community 169 - "Periksa Checks (calibration: subscriptions, statements, pots)"
Cohesion: 0.25
Nodes (7): Instalments gone from the statement check, Missing statements check, Old pot balance check, /periksa in Telegram and the periksa_data tool, ops/calibration/recurring_charges.py (per-month table of recurring merchants), Subscription checks (recorded vs charged, stopped subscriptions still charged), Unpaid past-due bills check

### Community 170 - "Mandiri Doubled Rows Data Fix (fix_data.py)"
Cohesion: 0.48
Nodes (4): files(), gap(), plan(), show()

### Community 171 - "Bot Activity: Gateway Lifecycle, Shutdowns and Restarts"
Cohesion: 0.13
Nodes (19): Hermes API server (127.0.0.1:8642, model hermes-agent), logs/container-boot.log, Hermes cron scheduler, Gateway drain timeout and runtime_draining pauses, /opt/data/.env (loaded by run_agent), Gateway control socket (/opt/data/gateway.sock), Gateway housekeeping (memory trim, agent cache idle sweep), logs/gateway.log (+11 more)

### Community 172 - "Cardblock Plugin Manifest"
Cohesion: 0.50
Nodes (3): description, name, version

### Community 176 - "Vault SOUL: Persona, Data and Card Rules"
Cohesion: 0.08
Nodes (30): tagihan_sekali tool (records a bill paid once such as arrears or a repair: alias, name, amount, due date, how it is paid), transfer_selesai (or lunas) marks a bill paid once as paid; paid in a plan's window it stays in that plan's progress, /internal/* surface (plugin only: store_payee, rincian), SOUL.md: vault bot persona (personal finance advisor and planner), Card instalment recording (x/y lines, record_card_installments, card_installments_status), Card payment method rules (Jenius and BCA to an account, Mandiri via the app menu, others to the card number), Card tokens [[CARD:num-xxxx]] map to stored cards by last 4 digits; then link_card_payees, Category scheme (wajib:, sinking:, transfer_internal, sekali:, perantara:, berhenti:, free daily spending) (+22 more)

### Community 177 - "Ingest Inputs"
Cohesion: 0.22
Nodes (9): pdf_passwords secret (read-only at /run/secrets), /ingest (read-only; filled by ingest-gmail and pa-uploads), ingest-gmail (fills /ingest), /ingest/telegram (59 files: bank statements, e-statements and mutasi sent as Telegram documents), pa-uploads (fills /ingest), PDF parsing packages (pdfplumber, pdfminer.six, pikepdf, pypdfium2), mutation_files (ledger table, 30 rows), skipped_files (ledger table, 52 rows) (+1 more)

### Community 178 - "Ledger Accounts, Payee Secrets and Sinking Funds"
Cohesion: 0.15
Nodes (17): bca-utama (BCA main account), fixed-expenses (Jago savings account), jago-harian (Jago main account), jago-utama (jago main account), jenius-akun (Jenius main account, also a payee), pot-jago (Jago pool account), jenius-0480 (jenius card; statement day 26, due day 13, transfer to jenius-akun), cryptography package (50.0.2) (+9 more)

### Community 179 - "Owner Names and Uploads"
Cohesion: 0.20
Nodes (6): Names, normalize_ref(), safe_name(), list_uploads(), resolve_ref(), list_uploads()

### Community 182 - "Front Compression Settings"
Cohesion: 0.67
Nodes (3): compression, min_tail_user_messages, threshold_tokens

### Community 183 - "Hermes Config Key Lines Probe (key_lines)"
Cohesion: 0.50
Nodes (3): key_lines(), doc(), walk()

### Community 185 - "Bank Admin Fee Estimates and Rules"
Cohesion: 0.29
Nodes (8): Admin fees (estimates, 2026-11-01: a bank fee per transfer out of the salary account), biaya_admin:<alias> (sets one item's fee; 0: none), biaya_admin_kartu (estimated fee per payment to a card number, capped), biaya_admin_mulai (payday from which fees count, YYYYMMDD; 20261130 live), biaya_admin_transfer (estimated fee per other transfer, capped), Tier 5: savings, Admin fee settings, changed only on the owner's decision (set_threshold biaya_admin_kartu or biaya_admin_transfer; biaya_admin:<alias pos> for one item, 0 = no fee), Bank admin fees (owner's estimates; the code counts them once per destination and sets them aside in the plan: BIAYA ADMIN line in generate_payday_plan, status_gajian, saldo_rekening)

### Community 186 - "Cardguard Answer Check and LLM Hooks (check_answer)"
Cohesion: 0.18
Nodes (9): amounts(), check_answer(), _is_owner(), on_llm_output(), on_pre_llm(), on_tool_result(), _owner_ids(), register() (+1 more)

### Community 188 - "Plan Invariant Checks (invariants.py)"
Cohesion: 0.12
Nodes (10): bills_of(), random_world(), RandomLedgers, rupiah(), TheChecksCatchBrokenNumbers, CalculationError, plan_errors(), require() (+2 more)

### Community 189 - "Front First Start: BotFather, Workspace Key and Spend Limits"
Cohesion: 0.10
Nodes (21): front (Hermes on Haiku, compose profile front, started once the owner's front secrets exist), Front zone (general and web, net-front), notion-mcp (front zone, later), sandbox (front zone, later), Front rendered env file (0600, 10 names; the front token differs from control's; the allowlist is the owner alone; no vault name in the container's env), cardblock plugin (built 2026-11-01): drops any message holding a card-like number before the model sees it, deletes it in Telegram and tells the owner, Front logs (/opt/personal-agent-data/hermes-front/logs/: agent.log, gateway.log, errors.log), Front memory approval (/memory pending, /memory approve <id>, /memory reject <id>) (+13 more)

### Community 193 - "Vault Model Setting"
Cohesion: 0.67
Nodes (3): model, default, provider

### Community 198 - "Control Proposal Validation"
Cohesion: 0.16
Nodes (8): submit(), card(), diff_message(), path_allowed(), quiet(), shown(), validate(), ValidateTests

### Community 199 - "Deploy 2 Script"
Cohesion: 1.00
Nodes (3): idle(), mask(), deploy.sh script

### Community 200 - "Hermes Socket Inode Probes (socket_inodes)"
Cohesion: 0.67
Nodes (3): socket_inodes(), socket_inodes_as(), sockets()

### Community 201 - "Daily Account Re-Anchor (saldo_rekening)"
Cohesion: 0.12
Nodes (10): Read the audit and the plan for the coming 1st, ops/calibration/bot_quality.py (tool errors, replies that apologise or correct themselves), jago-harian account alias, living_reserve (protected living money, the owner's choice since 2026-10-28), saldo_rekening tool (re-anchors the month's daily money to the balance given), services/hermes/vault/SOUL.md (also holds the owner rules), Anchor correction (difference with the records), health.living_anchor (+2 more)

### Community 202 - "Progress: M4 Comms Open Question, Spend Limits and Front Cost Follow-Up"
Cohesion: 0.29
Nodes (9): card-bus (the Kanban replacement in docs/ARCHITECTURE.md for one zone to hand work to another; still wanted?), Comms' Anthropic key from a third workspace with its own limit, as front has, Comms Google OAuth client (consent on the owner's laptop like the ingest token; gmail.modify, plus calendar.readonly or calendar.events), Comms permissions choice (read and label mail, write drafts, or also send; calendar read only or create events too), Follow-up: after a week, front's cost per day from its state.db against its own spend limit, M4 comms (remaining milestone; nothing built, waits for the owner's answers to open question 18), net-comms network (in the repo for the comms zone), Open question 18: M4 comms, nothing built (what it may do, Google consent, its own bot, which Anthropic key, card-bus) (+1 more)

### Community 205 - "Ledger Categories and Thresholds"
Cohesion: 0.47
Nodes (6): mandiri-utama (Mandiri main account), wajib:cicilan category (9 rules), wajib:spaylater category (3 rules), cicilan-mobil (debt to MTF, autodebit from mandiri-utama, due day 2), spaylater (debt to Shopee SPayLater, autodebit from mandiri-utama, due day 1), saldo_ditahan:mandiri-utama threshold

### Community 213 - "Cardguard Telegram Command Menu (ensure_menu)"
Cohesion: 0.29
Nodes (4): ensure_menu(), menu_is_ours(), _menu_loop(), push_menu()

## Ambiguous Edges - Review These
- `System prompts and tool-schema snapshots` → `tagihan_sekali tool (one-off bills: arrears, repairs)`  [AMBIGUOUS]
  docs/runtime/bot-activity.md · relation: conceptually_related_to
- `Turn machinery warmed (59 tool schemas materialized)` → `tagihan_sekali tool (one-off bills: arrears, repairs)`  [AMBIGUOUS]
  docs/runtime/bot-activity.md · relation: conceptually_related_to
- `belanja_kartu (per-card statement lines, long numbers masked)` → `Ended subscriptions (Catchplay, GoPro, AWS, Steam, PlayStation)`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `Card statement recording and reconciliation (7 cards)` → `/kondisi report command`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `Open question 7: GoPro charge on the CIMB October statement (annual, stop or move?)` → `Ended subscriptions (Catchplay, GoPro, AWS, Steam, PlayStation)`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `Coway arrears expense (paid 30 Oct from the Mandiri balance; receipt on mandiri-utama, category sekali:coway-tunggakan like the 13 Oct rows)` → `Open question 4: Google One and Coway on Mega vs recorded, check on the November statements`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `Number guard remembers amounts from the gateway's photo description (English number format)` → `image_input_mode: native (photos go to the model as images)`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `Hitting a limit: catat_usulan, then sudah kucatat di /usulan` → `/usulan (posts the waiting proposals again with their buttons)`  [AMBIGUOUS]
  services/hermes/vault/SOUL.md · relation: semantically_similar_to
- `cardguard TTL file (ttl/rincian.jsonl: /rincian messages to delete after expiry; 0 lines)` → `belanja_kartu (card spending breakdown per cycle from statement lines already read by code; never read the PDF for this)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `Gateway multiplex standalone (only one profile exists, nothing to multiplex)` → `state.db hosted_room tables (14 hosted-room tables, all empty)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `cache/schema_columns.json (schema hash plus versions for 17 tables)` → `state.db (sessions, messages, model usage, delivery obligations, routing, admissions, system prompts; SQLite WAL)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `cache/tool_discovery_cache.json (tool discovery cache, 287 keys, written 2026-10-27)` → `Engine tools besides MCP (only clarify and vision_analyze; the row still counts 56 vault_tools tools from the latest tool-schema snapshot while the schema cache section lists 57)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `telegram_update_receipts JSON file in HERMES_HOME` → `Messages sent while the bot restarts are dropped (platforms.telegram.extra.drop_pending_on_cold_boot, default true)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `Engine tools besides MCP (only clarify and vision_analyze; the row still counts 56 vault_tools tools from the latest tool-schema snapshot while the schema cache section lists 57)` → `tagihan_sekali (a bill paid once, outside subscriptions and fixed expenses, such as arrears or a repair; aksi picks the action, with optional alias, name, amount, due date, pay-to, method, date and note)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `cardguard plugin (services/hermes/vault, tests run by make test)` → `num-* card payees (num-0480, num-1111, num-4365, num-5685, num-5855, num-5915, num-9706, num-9888; no card in the cards table ends in 1111)`  [AMBIGUOUS]
  docs/runtime/infra-files.md · relation: conceptually_related_to
- `ingest-gmail job (services/ingest-gmail/Dockerfile, own ingest user)` → `pdf_passwords secret`  [AMBIGUOUS]
  docs/runtime/host.md · relation: conceptually_related_to
- `personal-agent-ingest-gmail image (latest, created 2026-11-01 06:00 WIB)` → `Python 3.12.16 image env (GPG_KEY, LANG C.UTF-8, PYTHON_SHA256, PYTHON_VERSION; change-proposals, control, vault-tools)`  [AMBIGUOUS]
  docs/runtime/containers.md · relation: conceptually_related_to
- `vault-tools data dir (mode 0700)` → `scripts/fetch-cuti.py (cuti bersama / holidays refresh for vault-tools, run by host python3)`  [AMBIGUOUS]
  docs/runtime/timers.md · relation: conceptually_related_to
- `/ingest (read-only; filled by ingest-gmail and pa-uploads)` → `processed_messages (ledger table, 0 rows)`  [AMBIGUOUS]
  docs/runtime/vault-tools.md · relation: conceptually_related_to
- `Denied: AWS IMDSv2 credential probes to the instance-metadata address (/latest/api/token, iam/security-credentials)` → `squid-vault (vault zone egress proxy; allows api.anthropic.com, api.notion.com, api.telegram.org, gmail.googleapis.com, oauth2.googleapis.com)`  [AMBIGUOUS]
  docs/runtime/proxies.md · relation: conceptually_related_to
- `Denied: Hermes model-catalog and provider refreshes (hermes-agent.nousresearch.com, raw.githubusercontent.com, openrouter.ai, portal.nousresearch.com)` → `squid-vault (vault zone egress proxy; allows api.anthropic.com, api.notion.com, api.telegram.org, gmail.googleapis.com, oauth2.googleapis.com)`  [AMBIGUOUS]
  docs/runtime/proxies.md · relation: conceptually_related_to
- `pa-backup.service + timer (restic backup, daily 02:00 WIB)` → `canary.txt (root-owned file in the data dir, mode 0644)`  [AMBIGUOUS]
  docs/runtime/host.md · relation: conceptually_related_to
- `Anonymous squid log and spool volumes (8, from image VOLUME lines)` → `squid exceptions (cap_add CAP_CHOWN, CAP_DAC_OVERRIDE, CAP_SETGID, CAP_SETUID; writable rootfs; tmpfs /var/log/squid)`  [AMBIGUOUS]
  docs/runtime/containers.md · relation: conceptually_related_to
- `VAULT_TOOLS_MCP_TOKEN and VAULT_TOOLS_INTERNAL_TOKEN (vault env names)` → `cardguard plugin (services/hermes/vault/plugins/cardguard, read-only at /opt/data/plugins/cardguard)`  [AMBIGUOUS]
  docs/runtime/containers.md · relation: conceptually_related_to
- `pa-check.timer + pa-check.service (restic integrity check, 1st of month 04:00 WIB, runs backup.sh check)` → `pa-forget.timer + pa-forget.service (restic retention 7d/4w/6m, Sun 04:00 WIB, runs backup.sh forget)`  [AMBIGUOUS]
  docs/runtime/timers.md · relation: conceptually_related_to
- `ledger.db.bak-pre-card-internal (ledger copy taken before the card-internal step, with -shm and -wal sidecars, 2026-11-01)` → `num-* card payees (num-0480, num-1111, num-4365, num-5685, num-5855, num-5915, num-9706, num-9888; no card in the cards table ends in 1111)`  [AMBIGUOUS]
  docs/runtime/vault-tools.md · relation: conceptually_related_to
- `ledger.db.bak-pre-m3 (ledger copy taken before the M3 step, with -shm and -wal sidecars, 2026-11-01)` → `change_log (ledger table, 34 rows)`  [AMBIGUOUS]
  docs/runtime/vault-tools.md · relation: conceptually_related_to
- `Closed: skip plus a direct Bot API reply writes nothing to the session store (closed by spike 11)` → `Spike 11: /rincian reply stays out of the session store (pass)`  [AMBIGUOUS]
  docs/assumptions.md · relation: conceptually_related_to
- `Closed: Telegram-side copy of the raw message (closed by spike 10, deleteMessage ok)` → `Spike 10: deleteMessage on the owner's incoming message (pass)`  [AMBIGUOUS]
  docs/assumptions.md · relation: conceptually_related_to
- `card_payments table (7 rows, one payment per card, last 2026-10-28 to 2026-10-30)` → `dbs-5685 card (6 statements 2026-01-25 to 2026-10-25, last due 2026-11-10; 0 marked paid; 10 instalment rows)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `cardguard plugin (appends the number-guard flag)` → `Full destination numbers are never in the plan`  [AMBIGUOUS]
  docs/calibration.md · relation: conceptually_related_to
- `cards table (7 cards; all statements reconciled, lines ok 0 per card)` → `lines_status: cocok on all 63 statements`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `owner_names table (1 row)` → `transfer_internal category (497 transactions)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `pot:hutang-teman fund (friend-debt pot; 1 fund report, 2026-10-26)` → `sinking_funds table (1 row)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to

## Knowledge Gaps
- **156 isolated node(s):** `AWS_DEFAULT_REGION`, `make runtime-map`, `mcp__vault_tools__add_owner_name`, `mcp__vault_tools__atur_jadwal_pot`, `mcp__vault_tools__belanja_kartu` (+151 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 987 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **53 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Laptop token flow (token piped over SSH into the VPS)` connect `Gmail OAuth and Sender Allowlist` to `Runbook (M1-M3): VPS Setup and Front Start`, `Front First Start: BotFather, Workspace Key and Spend Limits`, `Shared Imports, Ledger Connections and Ops Scripts`?**
  _High betweenness centrality (0.182) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `create_app()` (e.g. with `report()` and `rincian()`) actually correct?**
  _`create_app()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AWS_DEFAULT_REGION`, `make runtime-map`, `mcp__vault_tools__add_owner_name` to the rest of the system?**
  _156 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Hermes Runtime Probes` be split into smaller, more focused modules?**
  _Cohesion score 0.12317073170731707 - nodes in this community are weakly interconnected._
- **Why does `ingest-gmail (daily deterministic job, no LLM)` connect `Gmail OAuth and Sender Allowlist` to `Calibration Runbook and Reviews`, `Vault-Tools Surfaces (/mcp and /internal) and Requirements`, `Security: Egress, Squid Proxies and Sender Checks`?**
  _High betweenness centrality (0.090) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `System prompts and tool-schema snapshots` and `tagihan_sekali tool (one-off bills: arrears, repairs)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `Turn machinery warmed (59 tool schemas materialized)` and `tagihan_sekali tool (one-off bills: arrears, repairs)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._