# Graph Report - m1-skeleton  (2026-11-02)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 5283 nodes · 13484 edges · 258 communities (187 shown, 71 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 2020 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5b9586c4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Runtime Map Overview: Collector, Sanitization Rules, Drift, Map Files and the Project Graphs
- Hermes Runtime Probe (probe_hermes.py) and Regex-Based Parsers (re)
- Payee Vault Store (payee_vault.py) and Its Tests: Encrypted Numbers, Payee Links, Report and Migration Tests
- Cardguard Plugin (Number Guard, Menu, Control Bot)
- Runtime Map: Host Timers and pa-* Units, With the Ingest Failure Alert
- Vault-Tools Data Dir, Ledger Backups and Change Log
- Hermes Telegram Adapter, Plugins and Delivery
- Shared Imports and Modules: Ledger connect(), Standard Library, Test Modules and Ops Scripts
- Front Change Applier: Self-Check, Prechecks, Squid Parse, Zone Tests, File Writes and Recreate Checks (applier.py)
- Live MCP Tool Catalog (Vault Tools, Including the Payday, Bill and Instalment Tools)
- Bot Activity: Tool Calls, Tool Usage, Prompt Snapshots, Sessions, Context Compression and /new Resets (state.db)
- Bank Mutation Recording, Category Rules and Their Tests (mutations.py)
- Hermes Gateway Process, s6 Supervision, Runtime Files and Logs (Runtime)
- Payday Dates and Holidays (next_payday, last_working_day, current_payday, id_holidays, Joint-Leave Days) and Their Tests
- Gateway Lifecycle and Messages
- Cardguard Tests and Cardblock Plugin
- Control Bot Module (control.py): Proposal Validation, Hidden Characters, Reviews, Diff Messages, Cards, Outcome Texts, Buttons and Quiet Hours, with Its Tests
- Payday Plan Generation (generate_payday_plan), Card Payment Recording, the Living-Reserve Estimate, and the Advisor and Plan-in-Force Tests
- Payday Plan Builder (payday.py) and Its Tests: Worked Example, Fees, Reserve and Properties
- Gmail-Broker Tests and the Shared Fakes (test_gmail.py, fakes.py: Drafts, Labels, Read, Header Injection)
- Comms Broker Modules (gmail.py, gcal.py, common.py, serve.py): Text Cleaning, Number Masking, Replies and Entry Points, with the Cleaning Tests
- Debt Roadmap (roadmap.py) and the Calibration, Roadmap and Admin-Fee Tests With Threshold, Card, Pot and Emergency-Fund Setters
- Runtime Map Collector
- Ledger Schema (v13 Tables)
- Progress: Resume Point, Open Questions, Calibration From the Owner's Chat, Recalibrations, Subscriptions and Budgets
- Pot Simulation and Projection (simulate.py) and Its Tests
- Makefile Targets, VPS Connection Settings, Deploy Guard and Secrets Handling (the Secrets Dir, secret-gen and the Front Bot Secrets)
- Hermes Home and Stores: api_server Response and Run Stores, Caches, Skills and Prompts, the Projects, Kanban and Cron Stores, and Cardguard (Runtime)
- Applier Tests (test_applier.py)
- Spending Analysis (Budget Baseline)
- Progress: Card Statements, Payment Targets, Payees and Instalments, Scenario A, Category Suggestions and the Card Open Questions
- Receipt Merge Rules and Resent Screenshots
- Payday Progress and Two-Open-Plans Tests, Debt Payment Recording and Undo
- Host Runtime Probe (probe_host.py) and the Pre-Deploy Ledger Backup Scripts (os)
- MCP Server App (server.py), Tool Wrappers, Pending Statements and Through-the-Tools Flow Tests
- Egress Proxies, Containers, Deploy History and Jobs (State)
- Holiday Fetch: Sources, Parsing, Candidate Days and Overrides, with Their Tests (cuti_fetch.py)
- Health Check, Pace, Budget and Expense Tests (test_health.py, set_budget)
- Ingest Inputs
- Sinking Fund Tests
- Gmail Ingest run() and Its Job Tests (FakeClient, test_ingest.py)
- Vault SOUL: Bills Paid Once, Recording After Paying, Bound Funds, Expenses From Screenshots, Categories and Record Corrections
- Runbook: VPS Setup, M1 Gate Checks, Front First Start and Operation, the Comms Zone and Its First Start, Restore and Egress Tests
- Host (VPS) Runtime Map: Docker Images and Disk Use, Firewall, sshd, Cron and fail2ban
- Progress Hub: Bots, Zones and Milestones, M3 (Control v3, the Applier and Front Live), Zone Rules and Prune
- Statement Line Counting and Completeness Tests (count_dated_lines)
- Egress Proxies (squid) Runtime Map
- Notion Sync (notion_sync.py): Client, Plan, Installment, Budget and Roadmap Pages, and Its Tests
- Control Bot Approval Tests (ApprovalTests: tick, Proposals, Forged Buttons)
- Hermes Agent Settings, Toolsets, Engine Tools and Auxiliary Models (Live)
- Card Lines: Text Parsing, Storing, Netting, Instalment Recovery and Accuracy, with Their Tests (card_lines.py)
- Host Scripts: fetch-cuti, gmail-token-check, pdf-passwords-set and the graph_first Hook, with the Control Inbox Reader (json, urllib)
- Bills Paid Once (one_off.py) and Placement Tests
- Security (M1): Egress, Internal Networks, Squid Proxies, Zone Rules and Container Hardening
- Deploys and the Deploy Guard (make deploy, Rsync and Restart Rules), the Ledger and Data-Fix Backups, and the Vault Cardguard Owner Check
- Recording Completeness Tests
- Vault-Tools Probe Script (probe_vault_tools.py)
- Hermes Engine Image, Install and Bundled Plugins
- Hermes Gateway Containers (Vault and Front): Image, Env, Read-Only Config, SOUL and Plugin Mounts (Runtime)
- Compose Secrets
- Front Cardblock Plugin Tests (CardBlock)
- Control Bot Entry Point and Telegram Client (main, Telegram)
- Statement PDF Intake (statement_pdf.py): Decrypt, Text Extraction, Sanitizing, Untrusted Wrapping and File Parts
- Hermes config.yaml (Repo)
- Ledger Tables: Cards, Card Payees, Transactions and Subscriptions (Runtime)
- Plan Invariants (invariants.py: plan_errors, simulation_errors, require) and Their Tests, with the Plan-Bills Check (bills_of)
- Ledger Thresholds, Budgets and Plans
- Hermes Assumptions, Architecture, Vault-Tools Surfaces (/mcp and /internal) and Requirements
- Payday Plan Spec: Funding Order and Tiers, Worked Example, Payday Window and Bills Paid Once
- Control Bot Auth and Applied-Outcome Tests
- Progress: M4 Comms Built in the Repo (Not Deployed), Open Question 18 and the Owner's Choices, the Brokers, Proxies and First-Start Steps
- Compose Logging Options
- Compose: ingest-gmail Service and Env Settings
- Compose: vault-tools and ingest-gmail Services
- Bot Activity: Gateway Lifecycle, Shutdowns and Restarts
- Report Renderers for /rencana, /anggaran, /cicilan and /tagihan (reports.py)
- Google Session and Token Refresh (GoogleSession, the Token Loader) and Its Tests (FakeToken)
- Compose Service: control
- Compose Service: vault (Hermes)
- Weekly Docker Prune Script
- Compose Project and Containers (Runtime): Squid Proxies, Change-Proposals and Control With Their Env, Secrets and Approval Dirs, Networks and Hardening
- Payday Plan Output (Transfers, Fees, Cash to Hold, Living Money) and the Daily-Account Re-Anchor Rule
- Front Compose Service
- Debt Upserts With Autodebit and Their Tests (upsert_debt, test_autodebit.py)
- Graph-First Hook Tests
- Compose Service: squid-comms
- Compose Service: squid-ctl
- Compose Service: squid-front
- Compose Service: squid-vault
- Gmail OAuth Guide, Token Renewal and Sender Allowlist, the Comms Tokens and Consents, and the Ingest-Failure Alert (2 Nov Deploy)
- State Snapshot: the Ledger Database, Card, Statement and Instalment Tables, Card Payments, Payday Plans and Their Progress, Pots and the Usulan Items
- Category Suggestions: Groups, Apply and Their Tests (suggest.py, test_living.py)
- Expense Corrections (Edit, Delete and List) and Receipt Merging (merge_receipts), with the Corrected-Source Merge Tests (test_corrections.py)
- Upload Sync Tests
- State Snapshot: Accounts, Transactions and Mutation Files, Categories, the Change Log, Debts, Balance Reports, the Usulan Table, Data Fixes and Ledger Backups
- Ledger Audit (/periksa) and the Subscriptions Store, with Their Tests (audit.py, subscriptions.py)
- Deploy 2 Data Fix
- Control Bot Class: Updates, Diff Posting, Decisions and Buttons (Control, control.py)
- Compose Networks
- Compose Squid Template
- Progress: Bank Mutations, Doubled Rows and the Data Fixes, Receipt Merges, the Card-Repayment Fix, Record Corrections, the /periksa Audit and the Category Scheme
- Gmail Sender Authentication Checks and Tests (auth.py)
- Change-Proposal Submission Tests
- Hermes Auxiliary Models
- Hermes MCP Server Config
- Change-Proposals Compose Service
- Gmail Ingest Run Module: Config, Message Processing and Retention (run.py)
- Host Systemd Units and Their Scripts (pa-* Services and Timers incl. the Ingest Alert) and Stack Settings
- Calibration Runbook: Overview, Number Rules, Spend, Quality and Data Reviews, One-Shot Tests and the /periksa Checks
- State Snapshot: Timers, Jobs, Restic, Runs and the Pre-Deploy Ledger Backups
- Masking (masking.py: mask_sensitive, Luhn Check), Basis Points (bp_of) and Their Tests
- Control Proposal Store
- Card Installments (card_installments.py)
- Gmail Broker Class: Search, Read, Labels, Draft Replies, Hidden Finance Mail and the Call Budget (Broker, Budget)
- Front SOUL (Persona, Tasks, Answer Style, Security, Change Submission) and the Card-Number and Finance Rules of Front and Comms
- Expense, Pace and Health Core (health.py: record_expense, spending_pace, health_check), Balance Readings, Set Category, the Unsorted-Elsewhere Rule and Their Tests
- Vault SOUL: Owner Rules, Auto-Debits, Balances, Subscriptions, the Payday List on the 1st, Long-List Commands and Telegram Answer Style
- Front Cardblock Plugin (cardblock) and the Change-Proposals Module (proposals.py: ProposedFile, submit, the _Auth Middleware and MCP Imports)
- Zone Isolation, Egress Allowlist and Comms Zone Tests (test_zones.py), with the Deploy Rsync and Build-Context Tests (test_deploy.py)
- Front Change Applier (applier.py): Applier Class, Run Loop, Install Time, Lock, Recovery, Outcomes and DB Rows
- Number Guard Tests
- Rupiah Formatting and Fee Lines (format_idr, fee_parts) and the Rincian Builder (rincian.py: build, describe)
- Front Hermes Config
- Host-Script and Plugin Test Modules: Cardblock and Cardguard Same Detection, Gmail Token Check, PDF Password Collection, In-Place Rewrite and Token Scopes
- Hermes Telegram Gateway Config
- Progress: Plan in Force, Marking Transfers Done With Two Open Plans, the Payday Window and the Daily-Account Balance Reading
- Report Builder and Usulan Report Tests with the Telegram HTML Tag Balance Check (test_reports.py)
- Hermes Agent Block
- Hermes Memory Settings
- Cardguard Plugin Manifest
- Approvals Flow and the Applier (M3): Control Bot and Its Sender Check, Proposal Cards, Change-Proposals, Install and Uninstall, Trust Rules and Rollback
- Hermes Session Store and Telegram Delivery
- Progress: Daily-Money Pace, Uncategorized Payday Transfers, No Per-Day Figure, the Health Check and the Report Commands
- Front Auxiliary Models
- Vault Env Renderer
- Front Change-Proposals MCP
- Tools-Server Tests: Auth Separation and CVV Rejection (test_tools_server.py)
- Persistent Data Dir (/opt/personal-agent-data): Ingest Data and the Upload Relay (the pa-uploads Timer and Its Sync Script), Hermes Data Dirs and Env Files
- Comms Service (docker-compose.comms.yml: Env File, Capabilities, Limits, Command)
- Ingest Alert Tests: Main Run, Dry Run and Reasons (test_ingest_alert.py)
- Front Telegram Chat Filter
- Gmail API Client and Its Errors (client.py)
- Front Memory Settings
- Applied-Pull Tests (test_applied_pull.py)
- Vault Tools Module (tools.py): Obligations, Payday Plan and Status, Bills, Cards, Emergency Fund, Auto-Debit Check and Pot Balances
- Cashflow Summary, Recurring Payments, Uncategorized Rows and the Merchant Key (mutations.py: cashflow, recurring, normalize)
- Card Lines: Per-Card Detail (card_detail, format_detail, belanja_kartu) and Its Tests
- Front Agent Limits
- Hermes Vault Env and Credentials: Telegram Allowlist, Stranger Handling, Credential Pool and the Vault-Tools MCP Config (Live)
- Calibration Runbook: Owner Rules, Change-and-Verify, Dry Run, Root Causes and Worktree-Only Changes
- Control Bot Diff Review Tests (ReviewTests)
- Pace-Fix Deploy Script (31 Oct)
- Pocket-Balance Deploy Script (1 Nov)
- Recalibration Deploy Script (1 Nov)
- Front Model Setting
- Comms Zone (M4, Not Deployed): Architecture and Rules, the Comms SOUL, the Gmail and Calendar Brokers, squid-comms and the Trust-Boundary Split of the Zones
- Vault Tool Search Setting
- Infrastructure Files: Dockerfiles, Compose and Squid Allowlists
- Data Dirs Script
- Front Env Render Script
- Calendar Broker (gcal.py: Broker, Calendar, Policy) and Its Tests (test_gcal.py, Events, CalendarPolicy)
- Vault-Tools Container and MCP Server (Runtime): Env, Proxy, Surface Tokens and the Notion Sync
- Gmail Client Tests: Pagination and Attachment Decoding (test_ingest.py), and the Sender Config Loader (load_senders, SenderConfig)
- Payment-Mutation Server-Flow Tests (ServerFlows, test_mutations_pay.py)
- Progress: Payday Plans, Admin Fees, Daily Money Rules, the 30 Nov Rehearsal, Deploy 2, Pots and the Emergency Fund
- Deploy Guard Tests (test_deploy_guard.py)
- Fixed Expenses and Children's Fees
- Control Bot Fake Telegram Test Double (FakeTelegram)
- Mandiri Doubled Rows Data Fix (fix_data.py)
- Broker MCP Servers and Their Tests (GmailServer, CalendarServer, create_app, Served, test_server.py)
- Cardblock Plugin Manifest
- Ingest Alert Message Tests (Message: Renewal, Missing Label, Unknown Reason, Journal, Urgency)
- Statement Recording and Its Tests (record_statement, RecordStatement)
- MCP Row Models (Installment, Txn: pydantic BaseModel)
- Ingest Alert Run-Start Tests (RunStarted: systemd Unix Time)
- Statement Intake Tests (PdfIntake: ingest, file_sha256, make_pdf)
- Ledger Accounts, Payee Secrets and Sinking Funds
- Deterministic Statement Reconciliation (reconcile.py) and Its Tests
- Hermes Pending Skill Proposals and Curator, Uploads Cache and the Upload and Usulan Tools (Live)
- Roadmap Date Helpers (add_months, next_due, _clamp) and Their Tests
- Front Compression Settings
- Statement Reread Guard Tests (RereadGuard)
- Gmail Token Renewal Tests (test_gmail_renew.py)
- Bank Admin Fee Estimates and Rules
- Ledger Categories and Thresholds
- Change-Proposals and Comms-Broker Requirements (Pinned mcp and uvicorn), Surface Tokens and Comms Holding No Google Token
- Vault SOUL: Persona and the Owner's Goal, Security and Data Rules, the Living Reserve, Card Payments, /rincian, Uploads and Statements, Emergency Fund and Onboarding
- Comms Hermes Config (comms/config.yaml): Agent, Model, Approvals, Plugins, Security and Sessions
- Preflight Script
- Backup Script
- Disk Check Script
- Vault Model Setting
- Timer Install Script
- Secret Generation Script
- Secret Set Script
- Upload Sync Script
- Vault-Tools ASGI Token Middleware (_Auth, server.py)
- Deploy 2 Script
- Ingest Alert Unit Tests (Units: OnFailure Starts the Alert)
- Front Change Applier: Tree Files and Control Loading (regular, load_control)
- Gmail-Broker MCP Tools (create_app: search, read, label, create_draft, answer)
- Receipt-Merge Tests (Merge: Receipts Seen in Bank Mutations)
- Card Payment-Rule Tests (PayRules, test_mutations_pay.py)
- Calendar-Broker Service (docker-compose.comms.yml)
- Gmail Search Client Test Double (SearchedClient)
- Deploy Guard Script (deploy-guard.sh)
- Applier Install Script (install.sh)
- Gmail-Broker Service (docker-compose.comms.yml)
- Vault SOUL: Number Rules, Frequently Asked Numbers, Payday Progress, Pots and Simulations, Usulan and Conversation Calibration
- Card-Internal Data Fix Deploy (deploy.sh)
- Card Lines: Statement Processing, Summary, Netting and Reconcile (card_lines.py: process_statement, summary, reconcile)
- Card Line Parsing Tests (Parsing: Real Layouts, Month-First Dates, Year Rollover)
- Comms Compose Hardening Anchor and Logging (x-hardened, logging, options)
- Applier Squid-Complaint Agreement Tests (squid_complaints)
- Applier Real-Zone Tests (RealZoneTests With This Repo's tests/test_zones.py)
- Ledger Schema Migrations (_migrate, v1-to-v2 Card Payment Columns, v13 Backfill)
- squid-google Service (docker-compose.comms.yml)
- Mandiri Doubled Rows Deploy Script (deploy.sh)
- Gmail Token Renewal Script (gmail-renew.sh)
- Google API Fakes (FakeGoogle, FakeGmail, FakeCalendar: route, meta)
- Comms Compose File, Services and the Squid Anchor (x-squid)
- Host-Script Modules and Their Tests: Ingest Alert, Applied-Pull, Applier, Deploy Guard, Sync-Uploads, the Graph-First Hook, Completeness and the Runtime-Map Scrub
- Google API Errors and the Gmail Client (GoogleError, TokenError, Gmail._call), with the Short-Reply Tests
- Comms Hermes MCP Servers (gmail_broker, calendar_broker: Headers, Authorization, Timeouts)
- Statement Ingest Through the Server (ingest_statement, record_statement), Reference Resolving, PDF Passwords and Upload Listing (list_uploads)
- Comms Compose Secrets (Broker MCP Tokens, Comms Google Tokens and the OAuth Client)
- Calibration Through-the-Tools Test (ThroughTheTools, test_calibration.py)
- Gmail Hiding Policy (Policy: Finance Labels and Bank Senders) and Its Tests
- Card Line Kind Classification (classify) and Its Tests
- Comms Env Render Tests (Render, test_render_comms_env.py)
- Card Line Amount Parsing (parse_amount) and the Bank Number-Style Tests
- Comms Hermes Auxiliary Models (Compression, Title Generation, Vision)
- Admin-Fee Invariant Tests (a Fee Not Counted, Not Whole or Twice)
- Holiday Fetch Change Decisions (decide) and Their Tests
- WIB Date Tests (Wib: Today and After Midnight)
- Ledger Access Lock (locked: One SQLite Connection at a Time)
- Pot Deposit Schedule (pot_schedule) and Its Engine Tests
- Rincian Savings-Line Through-the-Tools Test (test_advisor.py)
- Comms Hermes Telegram Gateway (allowed_chats, Link Previews)
- Rincian Auto-Debit Reminder Through-the-Tools Test (test_autodebit.py)
- Card-Lines Statement Recording Through-the-Tools Test (test_card_lines.py)
- Comms Hermes Memory Settings (memory_enabled, nudge_interval, write_approval)
- Expense Corrections Through-the-Tools Test (List, Edit and Delete From a New Session)
- Health Screenshot-Flow Through-the-Tools Test (test_health.py)
- Living-Cost Through-the-Tools Test (test_living.py)
- Usulan and Simulation Through-the-Tools Tests (test_simulate.py)
- Comms Compose Proxy Environment (HTTPS_PROXY, NO_PROXY)
- Broker ASGI Token Middleware (Auth, serve.py)
- Comms Hermes MCP Tool, Prompt and Resource Switches
- Comms Hermes Compression Thresholds (threshold_tokens, min_tail_user_messages)
- Comms Hermes Skill Guard (guard_agent_created, write_approval)
- Comms Hermes Tool Search Setting (tool_search)
- Vault-Tools Server Entry Point and Its Read Helper (main, read)
- Comms Env Render Script (render-comms-env.sh)

## God Nodes (most connected - your core abstractions)
1. `generate_payday_plan()` - 111 edges
2. `create_app()` - 99 edges
3. `format_idr()` - 93 edges
4. `connect()` - 87 edges
5. `Bot activity snapshot` - 73 edges
6. `MCP server vault_tools (57 tools at http://vault-tools:8000/mcp, named mcp__vault_tools__<name> for the model)` - 66 edges
7. `PayeeVault` - 58 edges
8. `simulate()` - 56 edges
9. `set_threshold()` - 51 edges
10. `record_mutations()` - 46 edges

## Surprising Connections (you probably didn't know these)
- `Hitting a limit: catat_usulan, then sudah kucatat di /usulan` --semantically_similar_to--> `/usulan (posts the waiting proposals again with their buttons)`  [AMBIGUOUS] [semantically similar]
  services/hermes/vault/SOUL.md → docs/RUNBOOK.md
- `A rejected submit is fixed per its reason, never gamed; new services, host scripts, plugins and secret values are the owner's own work` --semantically_similar_to--> `Never in a proposal: host scripts, compose, plugins, control itself, secrets (new service = escalation; secret via make secret-set); at most five wait`  [INFERRED] [semantically similar]
  services/hermes/front/SOUL.md → docs/SECURITY.md
- `/rincian handled in pre_gateway_dispatch with skip plus direct Bot API send` --semantically_similar_to--> `/rincian (destination numbers grouped per destination; the only place full numbers appear)`  [INFERRED] [semantically similar]
  docs/ARCHITECTURE.md → services/hermes/vault/SOUL.md
- `/mcp surface (model-facing; aliases and amounts only, no tool stores or reveals a full number)` --semantically_similar_to--> `Security and data rules (no re-reading recorded documents, max 2 reads per answer, alias plus last 4 digits only, no CVV or expiry, no URLs)`  [INFERRED] [semantically similar]
  docs/SECURITY.md → services/hermes/vault/SOUL.md
- `After submit: say it went to the control bot; never say a change is in effect` --conceptually_related_to--> `Approved means recorded in control-state/approved/; since the applier's install (2026-11-01 23:23 WIB, section Applier) an approved front change is applied, and the card says whether a tap applies it`  [INFERRED]
  services/hermes/front/SOUL.md → docs/RUNBOOK.md

## Import Cycles
- 2-file cycle: `services/vault-tools/vault_tools/roadmap.py -> services/vault-tools/vault_tools/simulate.py -> services/vault-tools/vault_tools/roadmap.py`
- 2-file cycle: `services/vault-tools/vault_tools/simulate.py -> services/vault-tools/vault_tools/tools.py -> services/vault-tools/vault_tools/simulate.py`
- 3-file cycle: `services/vault-tools/vault_tools/roadmap.py -> services/vault-tools/vault_tools/tools.py -> services/vault-tools/vault_tools/simulate.py -> services/vault-tools/vault_tools/roadmap.py`

## Hyperedges (group relationships)
- **Calibration deploy flow (ledger backup first, then make deploy with its guard, rsync and rebuild, data scripts, a restart of vault while idle and /new)** — docs_calibration_ledger_backup, docs_calibration_make_deploy, docs_calibration_deploy_guard, docs_calibration_rsync_step, docs_calibration_compose_rebuild, docs_calibration_data_change_scripts, docs_calibration_restart_vault, docs_calibration_new_command [EXTRACTED 1.00]
- **Admin fee accounting in the payday plan (estimated fees once per destination, paid with their payment, listed apart, inside the salary invariant, counted from biaya_admin_mulai, estimated in the simulation)** — docs_payday_admin_fees, docs_payday_biaya_admin_kartu, docs_payday_biaya_admin_transfer, docs_payday_biaya_admin_alias, docs_payday_no_fee_payments, docs_payday_fee_paid_with_payment, docs_payday_fee_once_per_destination, docs_payday_fees, docs_payday_fee_salary_invariant, docs_payday_biaya_admin_mulai, docs_payday_fee_estimate, docs_payday_cash_to_hold [EXTRACTED 1.00]
- **Bill paid once lifecycle (recorded on the server's day, funded as an essential or overdue item in the first plan whose window reaches its due date, marked paid, or recorded as an expense when already paid)** — docs_payday_tagihan_sekali, docs_payday_bills_paid_once, docs_payday_recorded_on, docs_payday_first_plan_rule, docs_payday_late_recorded_bill, docs_payday_transfer_selesai, docs_payday_bill_paid_is_expense, docs_payday_essentials_tier, docs_payday_overdue_tier [EXTRACTED 1.00]
- **Payday funding tiers 0 to 5 in strict order** — docs_payday_funding_order, docs_payday_overdue_tier, docs_payday_card_minimum_tier, docs_payday_essentials_tier, docs_payday_debt_and_pool_tier, docs_payday_card_balance_tier, docs_payday_savings_tier [EXTRACTED 1.00]
- **Living money accounting and re-anchoring from the daily account balance** — docs_payday_living_money, docs_payday_cash_to_hold, docs_payday_living_leftover, docs_payday_living_leftover_spent, docs_payday_set_leftover_living_cash, docs_payday_saldo_rekening, docs_payday_health_living_anchor, docs_payday_living_anchor_rule, docs_payday_anchor_correction [EXTRACTED 1.00]
- **Accuracy layers that keep the bot's numbers correct** — docs_progress_invariants_self_checks, docs_progress_property_tests, docs_progress_number_guard, docs_progress_duplicate_expense_rule [EXTRACTED 1.00]
- **Card-repayment remedy (the finding, mutations.card_paid, wajib:kartu, own_last4 accounts only, the transfer_internal guard, the data fix, deploy.sh and the deploy)** — docs_progress_card_as_own_account_finding, docs_progress_card_repayment_fix, docs_progress_mutations_card_paid, docs_progress_wajib_kartu, docs_progress_own_last4, docs_progress_card_payment_transfer_internal_guard, docs_progress_card_internal_data_fix, docs_progress_card_internal_deploy_sh, docs_progress_card_internal_deploy [EXTRACTED 1.00]
- **Doubled Mandiri rows remedy (the finding, record_mutations overlap matching, the BUKU TIDAK COCOK ledger check and audit rule 8, the data fix, deploy.sh and the deploy)** — docs_progress_doubled_mandiri_rows_finding, docs_progress_overlap_date_amount_matching, docs_progress_buku_tidak_cocok_ledger_gap, docs_progress_audit_rule_8_ledger_gap, docs_progress_mandiri_dupes_data_fix, docs_progress_mandiri_dupes_deploy_sh, docs_progress_mandiri_dupes_deploy [EXTRACTED 1.00]
- **Front go-live on 2026-11-01 (secrets set, prune fixed, start, rendered env checked, one-shot submit test, test proposal #2)** — docs_progress_front_live, docs_progress_telegram_front_token, docs_progress_anthropic_front_key, docs_progress_prune_sh_fix, docs_progress_front_start, docs_progress_front_rendered_env, docs_progress_front_oneshot_submit_test, docs_progress_test_proposal_2 [EXTRACTED 1.00]
- **Ingest failure alert flow (the ingest exits 1 on an error event, pa-ingest.service's OnFailure starts pa-ingest-alert, scripts/ingest-alert.py reads the run's ingest_events and sends the cause and what to do via the control bot)** — docs_progress_ingest_exits_1_on_error, docs_progress_pa_ingest_service, docs_progress_pa_ingest_alert_service, docs_progress_ingest_alert_py, docs_progress_ingest_events, docs_progress_ingest_alert_messages, docs_progress_control_bot, docs_gmail_oauth_pa_ingest_alert [EXTRACTED 1.00]
- **M3 approval flow (front asks, control posts its own diff, the owner taps, the applier applies; live since 2026-11-01 23:24 WIB)** — docs_progress_front_agent, docs_progress_change_proposals, docs_progress_submit_tool, docs_progress_proposals_inbox, docs_progress_control_v3, docs_progress_proposal_review, docs_progress_control_state, docs_progress_applier, docs_progress_setujui_applies_front_diff [EXTRACTED 1.00]
- **M3 install steps on 2026-11-01 (pre-checks, make deploy with the data folders, install.sh with its host checks and units, control v3 migrated)** — docs_progress_m3_install_prechecks, docs_progress_m3_make_deploy, docs_progress_applier_data_folders, docs_progress_applier_units_install_sh, docs_progress_applier_install_host_checks, docs_progress_pa_applier_units, docs_progress_applier_outcome_files, docs_progress_control_v3_after_install [EXTRACTED 1.00]
- **M4 comms choices the owner makes before a first start, each default already built (mail and calendar permissions, sending kept out by gmail-broker's call list, labels, hidden mail, the daily summary, Google mode and one token per scope, its own bot or card-bus, the Anthropic workspace, then the owner's steps)** — docs_progress_oq18_m4_comms, docs_progress_m4_comms, docs_progress_comms_permissions_choice, docs_progress_comms_broker_blocks_sending, docs_progress_comms_labels, docs_progress_comms_hidden_finance_mail, docs_progress_comms_daily_summary_choice, docs_progress_comms_google_mode_choice, docs_progress_comms_google_oauth_client, docs_progress_comms_own_bot, docs_progress_card_bus, docs_progress_comms_anthropic_workspace, docs_progress_comms_owner_steps [EXTRACTED 1.00]
- **Own-record merge rules (same bank, coverage gate, merged duplicates, correction, lepas, cash never merges)** — docs_progress_merge_receipts_same_bank, docs_progress_record_merge_coverage_gate, docs_progress_duplicate_check_merged, docs_progress_merged_record_correction, docs_progress_lepas_unmerge, docs_progress_cash_never_merges_tunai, docs_progress_id_reuse_fix_45dfc1e [EXTRACTED 1.00]
- **Plan-in-force remedy (the 30 Nov rehearsal, the newest-row readers finding, plan_in_force and stored_plan, the three readers, the fix and the 2 Nov 01:23 WIB deploy)** — docs_progress_payday_30_nov_rehearsal, docs_progress_newest_plan_row_readers_finding, docs_progress_plan_in_force, docs_progress_stored_plan, docs_progress_spending_pace, docs_progress_living_balance, docs_progress_open_transfers, docs_progress_plan_in_force_fix, docs_progress_deploy_2_nov_0123 [EXTRACTED 1.00]
- **q21 __pycache__ remedy (rsync exclude, .dockerignore, tests/test_deploy.py, the one-time ingest-gmail rebuild and folder cleanup, the jobs-profile build note)** — docs_progress_oq21_pycache_rsync, docs_progress_rsync_exclude_pycache, docs_progress_dockerignore_vault_tools_ingest_gmail, docs_progress_test_deploy_py, docs_progress_q21_one_time_part, docs_progress_rsync_delete_keeps_excluded, docs_progress_ingest_gmail_build_after_change, docs_calibration_rsync_step [EXTRACTED 1.00]
- **Vault zone on internal net-vault: Hermes gateway, vault-tools MCP server and squid-vault** — docs_runtime_containers_personal_agent_vault_1, docs_runtime_containers_personal_agent_vault_tools_1, docs_runtime_containers_personal_agent_squid_vault_1, docs_runtime_containers_personal_agent_net_vault, docs_runtime_vault_tools_mcp_server [EXTRACTED 1.00]
- **Applier changes and deploys: deploy-guard holds the applier around make deploy, make applied-pull brings its VPS-side changes into the checkout as commits** — docs_runtime_infra_files_services_applier, docs_runtime_infra_files_make_applied_pull, docs_runtime_infra_files_scripts_applied_pull_py, docs_runtime_infra_files_make_deploy, docs_runtime_infra_files_scripts_deploy_guard_sh, docs_runtime_infra_files_deploy_guard_holds_applier [EXTRACTED 1.00]
- **comms zone (M4): comms reaches only Anthropic and Telegram; Google only through gmail-broker and calendar-broker over squid-google, their policy baked into the image** — docs_runtime_infra_files_config_squid_comms_conf, docs_runtime_infra_files_config_squid_google_conf, docs_runtime_infra_files_comms_holds_no_google_token, docs_runtime_infra_files_gmail_broker, docs_runtime_infra_files_calendar_broker, docs_runtime_infra_files_services_comms_brokers_dockerfile, docs_runtime_infra_files_brokers_policy_json [EXTRACTED 1.00]
- **make deploy never syncs plaintext secrets, the local project map or the Python caches of local test runs (rsync excludes)** — docs_runtime_infra_files_make_deploy, docs_runtime_infra_files_plaintext_secrets_stay_on_vps, docs_runtime_infra_files_graphify_out_shared_map, docs_runtime_infra_files_pycache_never_synced [EXTRACTED 1.00]
- **Plan and pot computed from the pre-salary state (usulan #9 and #10)** — docs_runtime_state_usulan_9, docs_runtime_state_usulan_10, docs_runtime_state_pre_salary_baseline, docs_runtime_state_pot_simulation, docs_runtime_state_tunda_pot_bulan, docs_runtime_state_rincian_rencana_commands, docs_runtime_state_payday_plan [EXTRACTED 1.00]
- **Statement-ingest failure alert: pa-ingest.service (the daily 06:00 WIB ingest-gmail run) names pa-ingest-alert.service in OnFailure, which runs scripts/ingest-alert.py on the host with config/stack.env to tell the owner** — docs_runtime_timers_pa_ingest, docs_runtime_timers_ingest_on_failure, docs_runtime_timers_pa_ingest_alert, docs_runtime_timers_ingest_alert_py, docs_runtime_timers_stack_env, docs_runtime_infra_files_host_pa_ingest, docs_runtime_infra_files_host_pa_ingest_alert, docs_runtime_infra_files_scripts_ingest_alert_py [EXTRACTED 1.00]
- **restic backup lifecycle through backup.sh (daily backup, monthly integrity check, weekly retention)** — docs_runtime_timers_pa_backup, docs_runtime_timers_pa_check, docs_runtime_timers_pa_forget, docs_runtime_timers_backup_sh, docs_runtime_timers_restic [EXTRACTED 1.00]
- **Applier gates before an approved front change is written (approved file matching control.db, front files only, the diff the owner saw whole and unchanged since, zone rules and squid parse, backup then recreate and check)** — docs_security_applier_input, docs_security_applier_front_files, docs_security_applier_exactly_what_owner_saw, docs_security_applier_rules_before_writing, docs_security_applier_writing_and_checking [EXTRACTED 1.00]
- **M3 change approval chain (front submit, change-proposals, proposals-inbox, control shows its own diff and decides on the owner's tap, the applier applies an approved front change and reports the outcome once)** — services_hermes_front_soul_submit_tool, docs_security_change_proposals, docs_architecture_proposals_inbox, docs_security_owner_sees_control_diff, docs_security_only_control_decides, docs_architecture_control_state, docs_security_applier_contract, docs_security_applier_reporting [EXTRACTED 1.00]
- **Payday cycle on the 1st (status_gajian, sisa_uang_harian, generate_payday_plan, periksa_data, recording tools, saldo_rekening)** — services_hermes_vault_soul_payday_list_flow, services_hermes_vault_soul_status_gajian, services_hermes_vault_soul_sisa_uang_harian, services_hermes_vault_soul_generate_payday_plan, services_hermes_vault_soul_periksa_data, services_hermes_vault_soul_payday_recording_tools, services_hermes_vault_soul_saldo_rekening [EXTRACTED 1.00]
- **The squid proxies are the only members of the egress network (squid-vault, squid-front, squid-comms, squid-ctl, and squid-google with the comms zone)** — docs_architecture_squid_vault, docs_architecture_squid_front, docs_architecture_squid_comms, docs_architecture_squid_ctl, docs_architecture_squid_google, docs_architecture_egress_network [EXTRACTED 1.00]
- **Purchases captured from Telegram photos: photo-burst batches, text-mode image routing through vision_analyze and the cached images, then record_expense (from a screenshot, receipt or the owner's words) and daftar_belanja** — docs_runtime_bot_activity_telegram_batching, docs_runtime_bot_activity_image_routing, docs_runtime_bot_activity_vision_analyze, docs_runtime_hermes_uploads_cache, docs_runtime_bot_activity_record_expense, docs_runtime_bot_activity_daftar_belanja, docs_runtime_hermes_record_expense [INFERRED 0.75]
- **Statement import tool flow** — docs_runtime_bot_activity_list_uploads, docs_runtime_bot_activity_pending_statements, docs_runtime_bot_activity_ingest_statement, docs_runtime_bot_activity_skip_statement_file, docs_runtime_bot_activity_record_statement, docs_runtime_bot_activity_list_statements, docs_runtime_bot_activity_record_mutations, docs_runtime_bot_activity_record_card_installments [INFERRED 0.75]
- **Which payday's plan a tool works on: the running payday plan unless a payday is named (generate_payday_plan payday, transfer_selesai gajian, status_gajian), next_payday for the next one** — docs_runtime_hermes_generate_payday_plan, docs_runtime_hermes_transfer_selesai, docs_runtime_hermes_transfer_selesai_gajian, docs_runtime_hermes_status_gajian, docs_runtime_hermes_next_payday [INFERRED 0.75]
- **Marking payday-plan payments as done by kind (cards, debt installments, other transfers, one-off bills), read back by status_gajian** — docs_runtime_hermes_record_card_payment, docs_runtime_hermes_cicilan_dibayar, docs_runtime_hermes_transfer_selesai, docs_runtime_hermes_tagihan_sekali, docs_runtime_hermes_status_gajian, docs_runtime_hermes_generate_payday_plan [INFERRED 0.75]
- **Per-message gateway bookkeeping in state.db: an inbound Telegram message gets a session admission, an admission-result key in state_meta and a delivery obligation for the reply (inference)** — docs_runtime_bot_activity_inbound_message, docs_runtime_hermes_state_db_session_admissions, docs_runtime_hermes_state_db_state_meta, docs_runtime_hermes_state_db_delivery_obligations, docs_runtime_bot_activity_delivery_obligations [INFERRED 0.75]
- **Daily spending from receipts on 2 Nov: 4 new jago-harian receipt rows (makan and listrik), unverified, with 2 more balance reports** — docs_runtime_state_source_receipt, docs_runtime_state_jago_harian, docs_runtime_state_category_listrik, docs_runtime_state_transaction_flags, docs_runtime_state_balance_reports_table [INFERRED 0.75]
- **Front stack up on 2026-11-01 04:34 UTC: front and change-proposals containers, first squid-front traffic** — docs_runtime_state_front_container, docs_runtime_state_change_proposals_container, docs_runtime_state_squid_front, docs_runtime_state_squid_front_startup_hosts, docs_runtime_state_containers_now [INFERRED 0.75]
- **Weekly prune removes the idle ingest-gmail image and the next daily ingest rebuilds it** — docs_runtime_state_pa_prune, docs_runtime_state_docker_prune_log, docs_runtime_state_ingest_gmail_image_build, docs_runtime_state_pa_ingest, docs_runtime_state_ingest_gmail_container [INFERRED 0.75]
- **Guards that keep the daily Gmail statement ingest running: token expiry warning and ingest-failure alert unit** — docs_runtime_state_pa_gmail_token, docs_runtime_state_gmail_token_expiry_warning, docs_runtime_state_pa_ingest_alert, docs_runtime_state_pa_ingest, docs_runtime_state_oauth2_googleapis_com [INFERRED 0.75]
- **Morning statement ingest (06:00 WIB) followed by the Notion snapshot (06:30 WIB) from vault-tools through squid-vault** — docs_runtime_timers_pa_ingest, docs_runtime_timers_ingest_gmail, docs_runtime_timers_pa_notion, docs_runtime_timers_vault_tools_notion_sync, docs_runtime_timers_personal_agent_vault_tools_1, docs_runtime_proxies_api_notion_com, docs_runtime_proxies_squid_vault [INFERRED 0.75]
- **Card-internal step on the live ledger (2026-11-01): the pre-card-internal backup with, in the same snapshot, transfer_internal rules down from 249 to 243, wajib:kartu rules up from 6 to 10 and change_log up from 20 to 34 rows** — docs_runtime_vault_tools_ledger_bak_pre_card_internal, docs_runtime_vault_tools_ledger_db, docs_runtime_vault_tools_category_transfer_internal, docs_runtime_vault_tools_category_wajib_kartu, docs_runtime_vault_tools_table_category_rules, docs_runtime_vault_tools_table_change_log [INFERRED 0.75]
- **Deploy 2 on the live ledger (2026-11-01): pre-deploy2 backup, schema user_version 14 with the new one_off_bills table, biaya_admin_* thresholds, vault-tools image rebuilt 10:26 WIB** — docs_runtime_vault_tools_ledger_bak_pre_deploy2, docs_runtime_vault_tools_ledger_db, docs_runtime_vault_tools_table_one_off_bills, docs_runtime_vault_tools_threshold_biaya_admin, docs_runtime_vault_tools_ledger_py, docs_runtime_host_image_personal_agent_vault_tools, docs_runtime_containers_personal_agent_vault_tools_1 [INFERRED 0.75]
- **Ingest-alert step on the live system (2026-11-02): the pre-ingest-alert ledger backup (with -shm and -wal sidecars) next to the new pa-ingest-alert unit, live and the same as its repo copy (25 pa-* units, none drifting), with the deploy drift at 206 repo files and 205 deployed, all identical** — docs_runtime_vault_tools_ledger_bak_pre_ingest_alert, docs_runtime_vault_tools_ledger_db, docs_runtime_timers_pa_ingest_alert, docs_runtime_timers_live_vs_repo_unit_drift, docs_runtime_readme_deploy_drift, docs_runtime_infra_files_host_pa_ingest_alert [INFERRED 0.75]
- **Mandiri duplicate-rows data fix on the live ledger (2026-11-01): pre-mandiri-dupes backup, mandiri-utama rows in transactions and mutation_files, change_log entries** — docs_runtime_vault_tools_ledger_bak_pre_mandiri_dupes, docs_runtime_vault_tools_ledger_db, docs_runtime_vault_tools_account_mandiri_utama, docs_runtime_vault_tools_table_transactions, docs_runtime_vault_tools_table_mutation_files, docs_runtime_vault_tools_table_change_log [INFERRED 0.75]
- **Plan-in-force step on the live ledger (2026-11-02): the pre-plan-in-force backup of ledger.db next to the plans and plan_progress tables, whose row counts did not change since the 23:32 WIB snapshot of 2026-11-01** — docs_runtime_vault_tools_ledger_bak_pre_plan_in_force, docs_runtime_vault_tools_ledger_db, docs_runtime_vault_tools_table_plans, docs_runtime_vault_tools_table_plan_progress [INFERRED 0.75]
- **DNS-over-HTTPS fallback containment (no route out of the zone containers, squid-vault denies DoH, the fallback transport uses the zone proxy)** — docs_assumptions_open_doh_fallback, docs_assumptions_zone_containers_no_route, docs_assumptions_telegram_fallback_proxy, docs_architecture_squid_vault, docs_architecture_internal_only_networks [INFERRED 0.85]
- **Comms Google token lifecycle (the comms project, consent screen and client, two consents through gmail-renew.sh with its token-name and client checks, the brokers re-reading the token file, weekly renewals in Testing mode, revocation) and the two findings that shaped it** — docs_gmail_oauth_comms_google_cloud_project, docs_gmail_oauth_comms_consent_screen, docs_gmail_oauth_comms_desktop_client, docs_gmail_oauth_comms_two_consents, docs_gmail_oauth_gmail_renew_sh, docs_gmail_oauth_token_client_check, docs_gmail_oauth_brokers_reread_token_file, docs_gmail_oauth_comms_testing_mode_renewals, docs_gmail_oauth_comms_revocation, docs_progress_brokers_token_read_once_finding, docs_progress_gmail_renew_comms_client_finding [INFERRED 0.85]
- **Applier safety chain (control's own diff as the review, zone rules, squid -k parse, old files back on failure, outcomes through control, the make deploy guard and applied-pull)** — docs_progress_control_v3, docs_progress_proposal_review, docs_progress_zone_rules, docs_progress_squid_parse_check, docs_progress_applier_restore_on_failure, docs_progress_applier, docs_progress_make_deploy_applied_guard, docs_progress_make_applied_pull [INFERRED 0.85]
- **Vault cardguard owner check rollout (built, found never on the VPS, pre-checked, synced and restarted by the doubled-rows deploy, live since 2026-11-01 20:13 WIB, with the sweep_ttl delete count)** — docs_progress_cardguard_owner_check, docs_progress_cardguard_owner_check_not_on_vps, docs_progress_cardguard_is_owner_precheck, docs_progress_mandiri_dupes_deploy_sh, docs_progress_mandiri_dupes_deploy, docs_security_cardguard_owner_check_live, docs_security_earlier_cardguard_any_private_chat, docs_assumptions_sweep_ttl_delete_count, docs_progress_ttl_sweep_check [INFERRED 0.85]
- **Daily money computation (top-up plus leftover, anchored by the daily-account reading)** — docs_progress_payday_living_money, docs_progress_cash_to_hold, docs_progress_living_leftover_spent, docs_progress_living_account_constant, docs_progress_living_balance_report, docs_progress_living_balance_mark, docs_progress_spending_pace, docs_progress_uang_harian_bulan_ini [INFERRED 0.85]
- **Deploy 2 delivered across the progress log, the payday spec and SOUL (admin fees, bills paid once, instalment undo, grace period, data fix, schema 14)** — docs_progress_deploy_2, docs_progress_admin_fees, docs_progress_tagihan_sekali, docs_progress_cicilan_dibayar_batal, docs_progress_stop_grace_period, docs_progress_deploy_2_data_fix, docs_progress_schema_v14_one_off_bills, docs_progress_deploy_2_deploy, docs_payday_admin_fees, docs_payday_bills_paid_once, services_hermes_vault_soul_admin_fees, services_hermes_vault_soul_tagihan_sekali, services_hermes_vault_soul_cicilan_dibayar_batal [INFERRED 0.85]
- **The control bot's Gmail ingest messages (the 08:00 token expiry warning and the failed-ingest alert, in the progress log and the OAuth guide; never started by hand, a dry run instead)** — docs_progress_pa_gmail_token, docs_gmail_oauth_pa_gmail_token_timer, docs_progress_pa_ingest_alert_service, docs_gmail_oauth_pa_ingest_alert, docs_progress_control_bot, docs_progress_never_start_ingest_units_by_hand, docs_progress_ingest_alert_dry_run [INFERRED 0.85]
- **Safe Gmail token renewal (the 2 Nov expiry warning, the finding, gmail-renew.sh with its check and in-place rewrite, gmail-auth.py refusing a terminal, the tests, the pa-gmail-token messages, the guide's step 4 and the owner's next step)** — docs_progress_gmail_token_expiry_warning_2_nov, docs_progress_gmail_renewal_empties_token_finding, docs_progress_gmail_renew_sh, docs_progress_gmail_token_inplace_rewrite, docs_progress_gmail_auth_refuses_terminal, docs_progress_test_gmail_renew_py, docs_progress_gmail_renew_vps_fake_token_test, docs_progress_pa_gmail_token, docs_progress_next_step_gmail_renew, docs_gmail_oauth_laptop_token_flow, docs_gmail_oauth_gmail_renew_sh, docs_gmail_oauth_old_token_kept_until_new_complete [INFERRED 0.85]
- **M4 comms zone as built in the repo (comms with its SOUL and own bot, gmail-broker and calendar-broker holding the two Google tokens, squid-comms and squid-google, the comms profile that make deploy never starts)** — docs_progress_m4_comms_built, docs_progress_comms_agent, docs_progress_comms_soul, docs_progress_gmail_broker, docs_progress_calendar_broker, docs_progress_squid_comms, docs_progress_squid_google, docs_progress_comms_profile, docs_gmail_oauth_gmail_broker_token, docs_gmail_oauth_calendar_comms_token [INFERRED 0.85]
- **Marking the open 30 Oct lesson fee once it is paid (the open transfer, transfer_selesai with gajian, the 7-day current_payday window, the two open plans, the plan in force, the owner's next step)** — docs_progress_les_mandarin_open, docs_progress_transfer_selesai, docs_progress_transfer_selesai_gajian, docs_progress_payday_window_current_payday, docs_progress_transfer_selesai_two_open_plans, docs_progress_plan_in_force, docs_progress_next_owner_steps_after_2_nov_deploy [INFERRED 0.85]
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
- **2026-11-02 01:23 WIB image builds: personal-agent-vault-tools and personal-agent-ingest-gmail rebuilt 17 seconds apart, personal-agent-vault-tools-1 recreated on that vault-tools build, build cache at 131 entries; in the 11:17 WIB snapshot the vault-tools latest tag shows a different image id with the same creation time while personal-agent-vault-tools-1 keeps the earlier one** — docs_runtime_host_image_personal_agent_vault_tools, docs_runtime_host_image_personal_agent_ingest_gmail, docs_runtime_containers_personal_agent_vault_tools_1, docs_runtime_host_docker_disk_use [INFERRED 0.85]
- **Secret provisioning path (entered or generated on the VPS, kept in the secrets dir, mounted as compose secrets)** — docs_runtime_infra_files_make_secret_set, docs_runtime_infra_files_make_secret_gen, docs_runtime_infra_files_make_pdf_passwords, docs_runtime_infra_files_plaintext_secrets_stay_on_vps, docs_runtime_host_opt_personal_agent_secrets, docs_runtime_host_compose_secrets_mount [INFERRED 0.85]
- **restic backup lifecycle (backup, integrity check, retention of the data dir)** — docs_runtime_infra_files_host_pa_backup, docs_runtime_infra_files_host_pa_check, docs_runtime_infra_files_host_pa_forget, docs_runtime_infra_files_scripts_backup_sh, docs_runtime_infra_files_make_backup, docs_runtime_host_opt_personal_agent_data, docs_runtime_host_secret_restic_env [INFERRED 0.85]
- **Telegram upload relay flow (Hermes document cache to the ingest folder, 90-day retention)** — docs_runtime_infra_files_hermes_vault_document_cache, docs_runtime_infra_files_host_pa_uploads, docs_runtime_infra_files_scripts_sync_uploads_sh, docs_runtime_infra_files_upload_retention_90_days, docs_runtime_host_hermes_vault_dir, docs_runtime_host_ingest_dir [INFERRED 0.85]
- **Live-vs-repo drift checks made by the runtime map collector (deployed files, systemd units, squid configs)** — docs_runtime_readme_collect_py, docs_runtime_readme_deploy_drift, docs_runtime_timers_live_vs_repo_unit_drift, docs_runtime_proxies_live_configs_match_repo [INFERRED 0.85]
- **Card-internal data fix on 2026-11-01 23:12 WIB: backup, change_log edits of category_rules and transactions, internal transfers recategorised** — docs_runtime_state_card_internal_fix, docs_runtime_state_backup_pre_card_internal, docs_runtime_state_change_log_table, docs_runtime_state_category_rules_table, docs_runtime_state_transactions_table, docs_runtime_state_category_transfer_internal, docs_runtime_state_category_wajib [INFERRED 0.85]
- **Deploy 2: admin fees and one-off bills shipped (usulan #4 and #6)** — docs_runtime_state_deploy_2, docs_runtime_state_usulan_4, docs_runtime_state_usulan_6, docs_runtime_state_admin_fee_estimate, docs_runtime_state_tagihan_sekali, docs_runtime_state_one_off_bills_table, docs_runtime_state_backup_pre_deploy2, docs_runtime_state_payday_plan [INFERRED 0.85]
- **Daily Gmail statement ingest path (pa-ingest, ingest-gmail run, squid-vault, Google APIs)** — docs_runtime_state_pa_ingest, docs_runtime_state_ingest_gmail_container, docs_runtime_state_squid_vault, docs_runtime_state_gmail_googleapis_com, docs_runtime_state_oauth2_googleapis_com, docs_runtime_state_pa_gmail_token, docs_runtime_state_doc_files_table, docs_runtime_state_processed_messages_table [INFERRED 0.85]
- **Ingest-alert deploy on 2026-11-02: pre-ingest-alert backup, new pa-ingest-alert unit, no container restart, 205 files identical** — docs_runtime_state_ingest_alert_deploy, docs_runtime_state_backup_pre_ingest_alert, docs_runtime_state_pa_ingest_alert, docs_runtime_state_host_timers, docs_runtime_state_deploy_drift, docs_runtime_state_containers_now [INFERRED 0.85]
- **M3 deploy on 2026-11-01 about 23:22 WIB: pre-m3 backup, control, vault-tools and vault restart, applier installed, no deploy drift left** — docs_runtime_state_m3_deploy, docs_runtime_state_backup_pre_m3, docs_runtime_state_control_container, docs_runtime_state_vault_tools_container, docs_runtime_state_vault_container, docs_runtime_state_pa_applier, docs_runtime_state_deploy_drift, docs_runtime_bot_activity_hermes_gateway [INFERRED 0.85]
- **Mandiri duplicates data fix on 2026-11-01: backup, change_log deletions and the mutation file edit** — docs_runtime_state_mandiri_dupes_fix, docs_runtime_state_backup_pre_mandiri_dupes, docs_runtime_state_change_log_table, docs_runtime_state_transactions_table, docs_runtime_state_mutation_files_table, docs_runtime_state_mandiri_utama [INFERRED 0.85]
- **Autodebit debts paid manually before the debit date (usulan #5, #7, #8)** — docs_runtime_state_usulan_5, docs_runtime_state_usulan_7, docs_runtime_state_usulan_8, docs_runtime_state_autodebit, docs_runtime_state_spaylater_debt, docs_runtime_state_car_instalment_debt, docs_runtime_state_debt_payments_table, docs_runtime_state_held_balance [INFERRED 0.85]
- **Plan-in-force deploy on 2026-11-02 about 01:23 WIB: pre-plan-in-force backup, vault-tools and vault restart, gateway start, no runtime deploy drift** — docs_runtime_state_plan_in_force_deploy, docs_runtime_state_backup_pre_plan_in_force, docs_runtime_state_vault_tools_container, docs_runtime_state_vault_container, docs_runtime_bot_activity_hermes_gateway, docs_runtime_state_deploy_drift [INFERRED 0.85]
- **restic check and retention locked out at 04:00 on 2026-11-01** — docs_runtime_state_pa_check, docs_runtime_state_pa_forget, docs_runtime_state_restic_repo_lock, docs_runtime_state_restic_backup, docs_runtime_state_restic_check_temp_cache, docs_runtime_state_restic_cache_warning, docs_runtime_state_host_timers [INFERRED 0.85]
- **Owner-approved front change flow: control writes an approval into control-state/approved, pa-applier.path (or the 5-minute timer) starts applier.py on the host, and its outcome comes back to control read-only at /outcome** — docs_runtime_containers_personal_agent_control_1, docs_runtime_timers_control_state_approved, docs_runtime_timers_pa_applier, docs_runtime_timers_applier_py, docs_runtime_host_applier_dir, docs_runtime_containers_mount_applier_outcome [INFERRED 0.85]
- **Encrypted payee secrets: payee_secrets nonce, ciphertext and match_hash with vault_tools_key and cryptography** — docs_runtime_vault_tools_table_payee_secrets, docs_runtime_containers_secret_vault_tools_key, docs_runtime_vault_tools_cryptography_package [INFERRED 0.85]
- **Statement ingest: ingest-gmail and pa-uploads fill /ingest, PDFs become statements and mutation files** — docs_runtime_vault_tools_ingest_gmail, docs_runtime_vault_tools_pa_uploads, docs_runtime_vault_tools_ingest, docs_runtime_vault_tools_pdf_parsing_packages, docs_runtime_vault_tools_table_doc_files, docs_runtime_vault_tools_table_statements, docs_runtime_vault_tools_table_mutation_files [INFERRED 0.85]
- **Finance stays out of comms (finance mail hidden by the broker on every call, numbers masked in every text, cardblock drops card-number messages, the SOUL sends finance questions to @danoevault_agent, the first-start test checks that a bank email does not come up)** — docs_security_comms_finance_mail_hidden, docs_security_comms_text_cleaning, docs_security_comms_cardblock, services_hermes_comms_soul_finance_not_here, services_hermes_comms_soul_forward_to_vault_bot, docs_runbook_comms_smoke_test [INFERRED 0.85]
- **Comms cannot send mail (gmail-broker's fixed call list, create_draft only as a reply to the address the message names, caps on drafts and label changes, every draft sent by the owner from Gmail, the SOUL drafting only on the owner's request)** — docs_architecture_gmail_broker, docs_security_comms_sending_guard, docs_security_comms_create_draft_reply_only, docs_security_comms_rate_caps, docs_security_comms_draft_owner_sends, services_hermes_comms_soul_cannot_send_email, services_hermes_comms_soul_draft_only_on_owner_request [INFERRED 0.85]
- **Front card-number defense (cardblock drops card-like digit runs before dispatch, front's SOUL handles card photos and other numbers, detection kept equal to vault's cardguard)** — docs_security_cardblock_plugin, docs_progress_cardblock_plugin, docs_runbook_cardblock_plugin, docs_security_cardblock_limits, services_hermes_front_soul_card_messages_removed, services_hermes_front_soul_sensitive_numbers_rule, docs_progress_cardguard_plugin [INFERRED 0.85]
- **Test approvals the applier never applied (#1 approved with Setujui and skipped at the install as skipped/1.json; #2 front's test skill, rejected by the owner on 1 Nov)** — docs_progress_test_proposal_1, docs_progress_test_proposal_2, docs_security_test_approvals_never_applied, docs_progress_applier, docs_security_applier_contract, docs_security_test_1_skip_record [INFERRED 0.85]

## Communities (258 total, 71 thin omitted)

### Community 0 - "Runtime Map Overview: Collector, Sanitization Rules, Drift, Map Files and the Project Graphs"
Cohesion: 0.13
Nodes (22): Hermes .env in HERMES_HOME (mode 0600, never opened by the collector), Runtime-map collector (ops/runtime-map/collect.py, regenerated with make runtime-map), bot-activity.md (daily snapshot: sessions, messages, tool calls, tool errors, tokens and cost, log templates, restarts), Runtime map collector (ops/runtime-map/collect.py), containers.md (every container: image, user, command, env names, mounts, networks, limits, hardening; changes on deploy), Deploy drift at collection time (206 repo files vs 205 in /opt/personal-agent, 205 identical; runtime files that differ, not deployed yet or only on the VPS: none; 1 docs/ops/tests file not deployed or different, harmless), graphify-out/GRAPH_REPORT.md (where to start in the project graph), graphify query, path and explain commands (+14 more)

### Community 1 - "Hermes Runtime Probe (probe_hermes.py) and Regex-Based Parsers (re)"
Cohesion: 0.09
Nodes (35): activity(), config(), day(), db_profile(), engine(), fkind(), flatten(), free() (+27 more)

### Community 2 - "Payee Vault Store (payee_vault.py) and Its Tests: Encrypted Numbers, Payee Links, Report and Migration Tests"
Cohesion: 0.10
Nodes (9): LinkPayees, Vault, Migration, stmt(), world(), Rincian, _norm(), PayeeVault (+1 more)

### Community 3 - "Cardguard Plugin (Number Guard, Menu, Control Bot)"
Cohesion: 0.09
Nodes (31): amounts(), _bot(), check_answer(), _chunks(), _delete_async(), _digits_of(), ensure_menu(), find_numbers() (+23 more)

### Community 4 - "Runtime Map: Host Timers and pa-* Units, With the Ingest Failure Alert"
Cohesion: 0.15
Nodes (31): host.md (VPS: OS, ports, firewall, SSH, cron, /opt layout, secret names, images; changes rarely), state.md (daily snapshot: ledger coverage, /usulan, plans, backups, timer results, deploy drift, proxy traffic), After docker.service (pa-applier.service, pa-ingest.service and pa-notion.service; pa-applier.service also Requires it), Applier install.sh (installs the pa-applier units from services/applier/systemd/ into /etc/systemd/system), scripts/backup.sh (backup, check and forget subcommands), scripts/disk-check.sh (disk usage check), scripts/fetch-cuti.py (cuti bersama / holidays refresh for vault-tools, run by host python3), scripts/gmail-token-check.py (Gmail OAuth token expiry warning, run by host python3) (+23 more)

### Community 5 - "Vault-Tools Data Dir, Ledger Backups and Change Log"
Cohesion: 0.23
Nodes (21): transfer_internal category (243 rules), wajib:kartu category (10 rules), /data/cuti_bersama.json (cuti bersama: 21 entries for 2026, 19 for 2027), /data (vault-tools data directory), holidays package (0.107), ledger.db.bak-pre-card-internal (ledger copy taken before the card-internal step, with -shm and -wal sidecars, 2026-11-01), ledger.db.bak-pre-* backups (49 copies dated 2026-10-27 to 2026-11-02), ledger.db.bak-pre-deploy2 (ledger copy taken before Deploy 2, with -shm and -wal sidecars, 2026-11-01) (+13 more)

### Community 6 - "Hermes Telegram Adapter, Plugins and Delivery"
Cohesion: 0.27
Nodes (8): channel_directory.json (chats the gateway knows: one telegram entry), Log line 'Cold boot: dropping Telegram updates' (Telegram adapter), Logger hermes_plugins.platforms__telegram.adapter (891 INFO, 287 WARNING, 2 ERROR), Logger plugins.platforms.telegram.telegram_network (66 INFO), state.db delivery_obligations table (204 Telegram deliveries, all delivered, 2026-10-27 to 2026-11-02), gateway.platforms.telegram.extra.disable_link_previews true (read by the Telegram adapter), Telegram platform adapter (plugins/platforms/telegram/adapter.py; state connected), telegram_update_receipts JSON file in HERMES_HOME

### Community 7 - "Shared Imports and Modules: Ledger connect(), Standard Library, Test Modules and Ops Scripts"
Cohesion: 0.06
Nodes (11): Migration, PotBalance, Migration, RandomLedgers, Migration, StoredPlans, Fund, LatestStatement (+3 more)

### Community 9 - "Live MCP Tool Catalog (Vault Tools, Including the Payday, Bill and Instalment Tools)"
Cohesion: 0.07
Nodes (61): add_owner_name (add the owner's name exactly as printed in account transactions), apply_suggestions (apply category suggestions for the named descriptions; empty applies all), atur_jadwal_pot (set how a pot, an earmarked fund with a deadline, is filled), Bank admin fees (estimates given by the owner, kept as thresholds through set_threshold), belanja_kartu (card spending breakdown per cycle from statement lines already read by code; never read the PDF for this), budget_status (budget use per category for a month, default the current one), card_installments_status (running card installments: x of y, months left and total remaining), cashflow_summary (monthly cash flow: income, spending, difference, savings ratio, per category; computed by code) (+53 more)

### Community 10 - "Bot Activity: Tool Calls, Tool Usage, Prompt Snapshots, Sessions, Context Compression and /new Resets (state.db)"
Cohesion: 0.04
Nodes (83): Bot activity snapshot, mcp__vault_tools__add_owner_name, mcp__vault_tools__apply_suggestions, mcp__vault_tools__atur_jadwal_pot, Compression summary call and aux_model telemetry, background_review model task, Vault tool names called without the MCP prefix, mcp__vault_tools__belanja_kartu (+75 more)

### Community 11 - "Bank Mutation Recording, Category Rules and Their Tests (mutations.py)"
Cohesion: 0.14
Nodes (14): show(), acct_db(), Mutations, rows(), cashflow(), format_cashflow(), ledger_gap(), _month_rows() (+6 more)

### Community 12 - "Hermes Gateway Process, s6 Supervision, Runtime Files and Logs (Runtime)"
Cohesion: 0.08
Nodes (37): Gateway housekeeping (memory trim, agent cache idle sweep), Image cache cleanup (gateway.run_housekeeping_disk), runtime/active_sessions.json (active-session entries), logs/agent.log (INFO and above: 9 ERROR, 477 WARNING, 767 distinct templates), api_server platform (OpenAI-compatible, 127.0.0.1:8642, reachable only inside the container; connected, no requests), logs/container-boot.log (boot diagnostics, 65 lines), logs/errors.log (WARNING and above: 715 lines, 152 distinct templates), Hermes gateway process (the Telegram bot: hermes gateway run --replace, uid 10000, kind hermes-gateway, state running) (+29 more)

### Community 13 - "Payday Dates and Holidays (next_payday, last_working_day, current_payday, id_holidays, Joint-Leave Days) and Their Tests"
Cohesion: 0.10
Nodes (12): PaydayWindow, PaydayDates, Holidays, commitments(), is_working_day(), last_working_day(), next_payday(), next_payday() (+4 more)

### Community 14 - "Gateway Lifecycle and Messages"
Cohesion: 0.09
Nodes (29): Agent budget: max_iterations=40, agent.deadline: task timed out and abandoned, logs/agent.log, cardguard capability_check: tools.override denied, cardguard number guard (amounts not from the tools), Config migration skipped (hermes_cli.post_update), Conversation loop API calls and turn re-anchoring, Credential pool: no available entries (+21 more)

### Community 15 - "Cardguard Tests and Cardblock Plugin"
Cohesion: 0.08
Nodes (3): CardGuard, ev(), Fake

### Community 16 - "Control Bot Module (control.py): Proposal Validation, Hidden Characters, Reviews, Diff Messages, Cards, Outcome Texts, Buttons and Quiet Hours, with Its Tests"
Cohesion: 0.11
Nodes (13): buttons(), card(), diff_message(), discard(), hidden_chars(), outcome_text(), path_allowed(), quiet() (+5 more)

### Community 17 - "Payday Plan Generation (generate_payday_plan), Card Payment Recording, the Living-Reserve Estimate, and the Advisor and Plan-in-Force Tests"
Cohesion: 0.07
Nodes (17): Plan, Advice, amounts(), DueBeforePayday, LivingReserveEstimate, statement(), world(), DailyAccount (+9 more)

### Community 18 - "Payday Plan Builder (payday.py) and Its Tests: Worked Example, Fees, Reserve and Properties"
Cohesion: 0.12
Nodes (13): BuildPlan, fixed(), amounts_of(), Engine, dummy(), Properties, WorkedExample, build_plan() (+5 more)

### Community 19 - "Gmail-Broker Tests and the Shared Fakes (test_gmail.py, fakes.py: Drafts, Labels, Read, Header Injection)"
Cohesion: 0.11
Nodes (12): addr(), b64(), card(), gmail_broker(), luhn_ok(), message(), Calls, Drafts (+4 more)

### Community 20 - "Comms Broker Modules (gmail.py, gcal.py, common.py, serve.py): Text Cleaning, Number Masking, Replies and Entry Points, with the Cleaning Tests"
Cohesion: 0.08
Nodes (22): clean(), html_to_text(), _luhn(), mask_numbers(), one_address(), one_line(), plain(), reply() (+14 more)

### Community 21 - "Debt Roadmap (roadmap.py) and the Calibration, Roadmap and Admin-Fee Tests With Threshold, Card, Pot and Emergency-Fund Setters"
Cohesion: 0.06
Nodes (25): fees_world(), Gate, Rule, Simulation, amounts(), bill(), Emergency, LeftoverLivingCash (+17 more)

### Community 22 - "Runtime Map Collector"
Cohesion: 0.16
Nodes (29): amounts(), cell(), deep_scrub(), engine_refs(), fence(), header(), listener_note(), local_tree() (+21 more)

### Community 23 - "Ledger Schema (v13 Tables)"
Cohesion: 0.08
Nodes (34): accounts, balance_reports, card_installment_scans, card_installments, card_lines, card_payments, cards, category_keywords (+26 more)

### Community 24 - "Progress: Resume Point, Open Questions, Calibration From the Owner's Chat, Recalibrations, Subscriptions and Budgets"
Cohesion: 0.07
Nodes (53): PROGRESS.md: progress and resume point (finance / vault), Accuracy layers (owner: 99.99% accuracy, no miscalculation), atur_jadwal_pot (saves the pot schedule after the owner agrees; pola, pakai_gaji_hari_tenggat), Biggest avoidable costs (game/digital top-ups; late/overlimit fees and interest), Bot calibration from the owner's real chat (2026-10-28), Bot model config (reasoning_effort high, claude-sonnet-5-5 vision and compression, Haiku titles), Branch worktree-m1-skeleton, draft PR #1, Card spending budgets (kartu:<category>, owner approved 2026-10-28) (+45 more)

### Community 25 - "Pot Simulation and Projection (simulate.py) and Its Tests"
Cohesion: 0.09
Nodes (13): PlanStaysAfterPaying, Consumers, CardsFirstPot, EmergencyFund, Simulate, simulasi_skenario(), _bln(), format_result() (+5 more)

### Community 26 - "Makefile Targets, VPS Connection Settings, Deploy Guard and Secrets Handling (the Secrets Dir, secret-gen and the Front Bot Secrets)"
Cohesion: 0.08
Nodes (45): pdf_passwords secret (read-only at /run/secrets), vault_tools_key secret (read-only at /run/secrets), hermes-front data dir (mode 0700, no longer empty), /opt/personal-agent-secrets (secret files, mode 0700), anthropic_front_key secret, pdf_passwords secret, telegram_front_token secret, telegram_vault_token secret (+37 more)

### Community 27 - "Hermes Home and Stores: api_server Response and Run Stores, Caches, Skills and Prompts, the Projects, Kanban and Cron Stores, and Cardguard (Runtime)"
Cohesion: 0.07
Nodes (32): Bundled Hermes skills (12 categories; the skills toolset is disabled, so the model cannot load them), cardguard plugin v0.1 (replaces card numbers in inbound Telegram text with tokens before dispatch; spike), cardguard TTL file (ttl/rincian.jsonl: /rincian messages to delete after expiry; 0 lines), cron/executions.db executions table (0 rows), Hermes cron store (cron/: executions.db, job and tick locks, ticker heartbeat; no jobs), gateway.lock, gateway.pid, gateway.sock and gateway-starts.log in HERMES_HOME, /opt/data (HERMES_HOME, read-write mount), kanban.db (kanban store; toolset disabled, every table empty) (+24 more)

### Community 28 - "Applier Tests (test_applier.py)"
Cohesion: 0.12
Nodes (5): Apply, Base, FakeDocker, Install, proposal()

### Community 29 - "Spending Analysis (Budget Baseline)"
Cohesion: 0.18
Nodes (10): Analysis, Monthly, tx(), world(), analyse(), card_charges(), format_analysis(), monthly() (+2 more)

### Community 30 - "Progress: Card Statements, Payment Targets, Payees and Instalments, Scenario A, Category Suggestions and the Card Open Questions"
Cohesion: 0.16
Nodes (23): apply_suggestions (stores the suggested categories; now skips a refused group and names it), Rehearsal C: the BCA bill due 28 Nov (a Saturday) comes before the 30 Nov payday, like 28 Oct, so its minimum comes from the balance on hand, belanja_kartu (per-card statement lines, long numbers masked), Finding: since a 2026-10-28 commit suggest.groups counted the owner's cards among the own accounts, so four September card repayments (cimb-9888, dbs-5685, hsbc-5915, mega-5855) were stored as transfer_internal and are missing from September's cashflow expenses, BCA card, CIMB card, HSBC card, Card installments (x/y) tracking per scanned statement (+15 more)

### Community 31 - "Receipt Merge Rules and Resent Screenshots"
Cohesion: 0.17
Nodes (4): _Banks, LateRecordsAndResentScreenshots, MergeRules, spend()

### Community 32 - "Payday Progress and Two-Open-Plans Tests, Debt Payment Recording and Undo"
Cohesion: 0.08
Nodes (15): UndoInstalment, CardPayment, Instalments, pay_as_on_30_oct(), plan_of(), Progress, TwoPlansOpen, cicilan_dibayar() (+7 more)

### Community 33 - "Host Runtime Probe (probe_host.py) and the Pre-Deploy Ledger Backup Scripts (os)"
Cohesion: 0.13
Nodes (22): containers(), deployed_tree(), docker_logs(), images(), listening(), mixed(), networks(), opt_layout() (+14 more)

### Community 34 - "MCP Server App (server.py), Tool Wrappers, Pending Statements and Through-the-Tools Flow Tests"
Cohesion: 0.06
Nodes (26): ThroughTheTools, ThroughTheTools, PendingStatements, create_app(), atur_jadwal_pot(), daftar_belanja(), hapus_belanja(), ingest_events() (+18 more)

### Community 35 - "Egress Proxies, Containers, Deploy History and Jobs (State)"
Cohesion: 0.10
Nodes (48): Telegram fallback-IP discovery via DNS-over-HTTPS, Hermes model catalog fetch failing (urlopen Tunnel error), api.anthropic.com (Anthropic API; 1088 requests via squid-vault, 37 via squid-front), api.notion.com (Notion API; 450 requests via squid-vault, 80 of them from vault-tools), api.telegram.org (Telegram Bot API; the busiest allowed host on squid-vault, squid-ctl and squid-front, 9050 requests via squid-front), change-proposals container (personal-agent-change-proposals-1; running and healthy since 2026-11-01), Containers now: 9 running, 0 restarts, no OOM, exit 0, control container (personal-agent-control-1; running since 2026-11-01 16:22 UTC, 0 log lines in 7 days) (+40 more)

### Community 36 - "Holiday Fetch: Sources, Parsing, Candidate Days and Overrides, with Their Tests (cuti_fetch.py)"
Cohesion: 0.17
Nodes (8): Override, Parse, candidate_days(), load_year(), merge_file(), parse_github(), parse_ics_cuti(), render_diff()

### Community 37 - "Health Check, Pace, Budget and Expense Tests (test_health.py, set_budget)"
Cohesion: 0.11
Nodes (8): Budgets, cash_month(), Health, Pace, planned(), RecordExpense, set_budget(), set_budget()

### Community 38 - "Ingest Inputs"
Cohesion: 0.23
Nodes (11): /ingest (read-only; filled by ingest-gmail and pa-uploads), ingest-gmail (fills /ingest), /ingest/telegram (59 files: bank statements, e-statements and mutasi sent as Telegram documents), pa-uploads (fills /ingest), doc_files (ledger table, 150 rows), ingest_checks (ledger table, 146 rows), mutation_files (ledger table, 30 rows), skipped_files (ledger table, 52 rows) (+3 more)

### Community 39 - "Sinking Fund Tests"
Cohesion: 0.17
Nodes (9): fund(), InThePlan, Math, row(), setup(), Validation, upsert_sinking_fund(), sinking_paydays_left() (+1 more)

### Community 40 - "Gmail Ingest run() and Its Job Tests (FakeClient, test_ingest.py)"
Cohesion: 0.26
Nodes (4): run(), FakeClient, message(), Run

### Community 41 - "Vault SOUL: Bills Paid Once, Recording After Paying, Bound Funds, Expenses From Screenshots, Categories and Record Corrections"
Cohesion: 0.14
Nodes (14): tagihan_sekali tool (records a bill paid once such as arrears or a repair: alias, name, amount, due date, how it is paid), transfer_selesai (or lunas) marks a bill paid once as paid; paid in a plan's window it stays in that plan's progress, /internal/* surface (plugin only: store_payee, rincian), Category scheme (wajib:, sinking:, transfer_internal, sekali:, perantara:, berhenti:, free daily spending), Undoing a wrong instalment record (repeat the record, wait for ya, then cicilan_dibayar(alias, jumlah, batal=true); jatuh_tempo when not the last record), generate_payday_plan (payday plan, uses the new salary up to 7 days after payday), Instalments the owner pays himself early (cicilan_dibayar; jatuh_tempo for late payments; not counted again), Recording after paying (record_card_payment per card, cicilan_dibayar, transfer_selesai, dana_darurat, saldo_pot) (+6 more)

### Community 42 - "Runbook: VPS Setup, M1 Gate Checks, Front First Start and Operation, the Comms Zone and Its First Start, Restore and Egress Tests"
Cohesion: 0.07
Nodes (45): Comms in a compose file of its own (compose/docker-compose.comms.yml), so make deploy (the main file alone) never builds or starts it, front (Hermes on Haiku, compose profile front, started once the owner's front secrets exist), Front zone (general and web, net-front), notion-mcp (front zone, later), sandbox (front zone, later), Front rendered env file (0600, 10 names; the front token differs from control's; the allowlist is the owner alone; no vault name in the container's env), telegram_front_token secret (set by the owner on 2026-11-01 09:08 WIB), Runbook (M1) (+37 more)

### Community 43 - "Host (VPS) Runtime Map: Docker Images and Disk Use, Firewall, sshd, Cron and fail2ban"
Cohesion: 0.15
Nodes (22): Python 3.12.16 image env (GPG_KEY, LANG C.UTF-8, PYTHON_SHA256, PYTHON_VERSION; change-proposals, control, vault-tools), restart unless-stopped (every container), authorized_keys (root: 0 entries, ubuntu: 1), docker daemon.json (json-file log driver, max-size 10m, max-file 3), Docker disk use (6 images, 9 containers, 8 local volumes, 131 build cache entries), Docker 29.9.2 and Compose 5.6.1 on the VPS, /etc/cron.d entries (e2scrub_all, sgagenttask, sysstat, yunjing), fail2ban (inactive) (+14 more)

### Community 44 - "Progress Hub: Bots, Zones and Milestones, M3 (Control v3, the Applier and Front Live), Zone Rules and Prune"
Cohesion: 0.08
Nodes (66): allowed_chats: none (both Hermes configs; drops every group, keeps DMs), anthropic_front_key secret (set by the owner on 2026-11-01 09:09 WIB), Applier (services/applier: writes, deploys and health-checks an approved front change; built 2026-11-01, installed 2026-11-01 23:23 WIB), The applier, built (M3, 2026-11-01 afternoon); installed 23:23 WIB, Applier data folders (applier/ root 0700, applier/outcome/ root 0755; made by make deploy), Applier install's eight host checks (control.db read-only with the review column, approved/ a folder, regular files, tests/test_zones.py on the installed tree, front and squid-front running, squid -k parse on front.conf, front's Telegram state, root's state folders), Applier outcome files (outcome/applier.json with the install time; applied/ and failed/, empty after the install), Applier tests (22 with a fake docker; the zone-rule test runs the real tests/test_zones.py against named mutations of the front files) (+58 more)

### Community 45 - "Statement Line Counting and Completeness Tests (count_dated_lines)"
Cohesion: 0.22
Nodes (5): Counting, count_dated_lines(), count_signed_lines(), count_transactions(), _first_money_is_real()

### Community 46 - "Egress Proxies (squid) Runtime Map"
Cohesion: 0.26
Nodes (17): api.anthropic.com, api.telegram.org, Denied: AWS IMDSv2 credential probes to the instance-metadata address (/latest/api/token, iam/security-credentials), Denied: DNS-over-HTTPS fallbacks of the HTTP clients (dns.google, cloudflare-dns.com), Denied: Hermes model-catalog and provider refreshes (hermes-agent.nousresearch.com, raw.githubusercontent.com, openrouter.ai, portal.nousresearch.com), Docker DNS (name resolution used instead of DNS-over-HTTPS), Egress proxies (squid) runtime map, gmail.googleapis.com (+9 more)

### Community 47 - "Notion Sync (notion_sync.py): Client, Plan, Installment, Budget and Roadmap Pages, and Its Tests"
Cohesion: 0.12
Nodes (19): FakeNotion, Sync, world(), bullet(), heading(), main(), Notion, NotionError (+11 more)

### Community 49 - "Hermes Agent Settings, Toolsets, Engine Tools and Auxiliary Models (Live)"
Cohesion: 0.11
Nodes (21): agent.reasoning_effort high (not in DEFAULT_CONFIG; a per-model override would win), auxiliary.compression: claude-sonnet-5-5 via anthropic (default auto), auxiliary config section (139 keys; our compression, title_generation and vision models on anthropic), auxiliary.title_generation: claude-haiku-5-5 via anthropic (default auto), auxiliary.vision: claude-sonnet-5-5 via anthropic (default auto), clarify engine tool, Hermes config backups (backups/config.yaml.good.*, five from 2026-10-28 to 2026-11-01), DEFAULT_CONFIG sections table (100 top-level sections with line, key count and the keys we set) (+13 more)

### Community 50 - "Card Lines: Text Parsing, Storing, Netting, Instalment Recovery and Accuracy, with Their Tests (card_lines.py)"
Cohesion: 0.24
Nodes (9): Accuracy, add_statement(), card_world(), Recovery, Store, categorize(), format_summary(), parse_text() (+1 more)

### Community 51 - "Host Scripts: fetch-cuti, gmail-token-check, pdf-passwords-set and the graph_first Hook, with the Control Inbox Reader (json, urllib)"
Cohesion: 0.09
Nodes (20): behind(), ignore_patterns(), ignored(), main(), md5(), snapshot(), wib(), get() (+12 more)

### Community 52 - "Bills Paid Once (one_off.py) and Placement Tests"
Cohesion: 0.09
Nodes (22): random_world(), rupiah(), amounts(), bill_world(), catat(), Flows, Placement, Simulation (+14 more)

### Community 53 - "Security (M1): Egress, Internal Networks, Squid Proxies, Zone Rules and Container Hardening"
Cohesion: 0.16
Nodes (19): squid-front proxy (web, private ranges blocked), Closed: the DNS-over-HTTPS fallback cannot bypass the proxy, Spike 5: Hermes reaches Telegram via the zone proxy from an internal network (pass), Hermes' Telegram fallback transport takes its proxy from TELEGRAM_PROXY/HTTPS_PROXY (v0.22.5 plugins/platforms/telegram/telegram_network.py), No direct route out of the zone containers (ENETUNREACH to Hermes' seed Telegram IPs from vault, front, vault-tools, control and change-proposals; external names do not resolve), Squid-front at boot, before any chat: model catalogs (models.dev, openrouter.ai), Nous pages and two DNS-over-HTTPS resolvers; afterwards only api.telegram.org and api.anthropic.com, Front memory approval (/memory pending, /memory approve <id>, /memory reject <id>), Install FAIL on tests/test_zones.py with No module named 'yaml': sudo apt install python3-yaml (present on 2026-11-01: PyYAML 6.0.1) (+11 more)

### Community 54 - "Deploys and the Deploy Guard (make deploy, Rsync and Restart Rules), the Ledger and Data-Fix Backups, and the Vault Cardguard Owner Check"
Cohesion: 0.08
Nodes (60): sweep_ttl logs how many deletes Telegram accepted (counts only), up -d --build (the rebuild step of make deploy), Deploy guard of make deploy (when it refuses: make applied-pull, push, then deploy again), Deploy procedure (from the worktree root, committed and pushed), Ledger (SQLite /data/ledger.db in the vault-tools container), make applied-pull, push, then deploy again (when the deploy guard refuses), make deploy (the deploy guard, the rsync, timers, data folders and up -d --build), rsync of the worktree by make deploy (leaves .git, .claude, decrypted secrets, graphify-out, CLAUDE.md and __pycache__ here) (+52 more)

### Community 55 - "Recording Completeness Tests"
Cohesion: 0.47
Nodes (3): acct_db(), Completeness, r()

### Community 56 - "Vault-Tools Probe Script (probe_vault_tools.py)"
Cohesion: 0.15
Nodes (12): cuti(), data_files(), day(), fkind(), fname(), free(), ledger(), money_free() (+4 more)

### Community 57 - "Hermes Engine Image, Install and Bundled Plugins"
Cohesion: 0.17
Nodes (12): Bundled engine plugins (browser, computer_use, context_engine, cron_providers, delegation, image_gen, kanban, memory, model-providers, platforms, web and others), TZ Asia/Jakarta (container timezone), Docker embedded DNS (container-local tcp and udp listeners), Engine image nousresearch/hermes-agent (release date 2026.9.24), Hermes Agent v0.22.5 (vault bot engine, Telegram bot @danoevault_agent, container personal-agent-vault-1), Install stamp (baseVersion 0.22.5, branch main, distribution docker, source ci, updateMechanism external, built 2026-10-23), installs/ and install_id (install bootstrap metadata), Log line 'router: catalog fetch failed / Model catalog' (plugins/model-providers/router; harmless) (+4 more)

### Community 58 - "Hermes Gateway Containers (Vault and Front): Image, Env, Read-Only Config, SOUL and Plugin Mounts (Runtime)"
Cohesion: 0.22
Nodes (18): cardblock plugin (services/hermes/front/plugins/cardblock, read-only at /opt/data/plugins/cardblock), cardguard plugin (services/hermes/vault/plugins/cardguard, read-only at /opt/data/plugins/cardguard), ANTHROPIC_API_KEY (vault and front env name), Hermes path env (HERMES_HOME and HERMES_WRITE_SAFE_ROOT /opt/data, HERMES_PYTHON, HERMES_RUNTIME_DIR, HERMES_TUI_DIR, HERMES_WEB_DIST, PLAYWRIGHT_BROWSERS_PATH, XDG_RUNTIME_DIR), HERMES_SKIP_CONFIG_MIGRATION=1 (vault and front env), Hermes Telegram env (TELEGRAM_BOT_TOKEN; TELEGRAM_ALLOWED_USERS and TELEGRAM_HOME_CHANNEL values masked), TZ (vault and front Asia/Jakarta; squids UTC), services/hermes/front/config.yaml (read-only at /opt/data/config.yaml) (+10 more)

### Community 59 - "Compose Secrets"
Cohesion: 0.11
Nodes (19): file, file, file, file, file, secrets, change_proposals_mcp_token, gmail_ingest_client (+11 more)

### Community 60 - "Front Cardblock Plugin Tests (CardBlock)"
Cohesion: 0.17
Nodes (6): fn(), CardBlock, failing(), slow(), ev(), wrapper()

### Community 62 - "Statement PDF Intake (statement_pdf.py): Decrypt, Text Extraction, Sanitizing, Untrusted Wrapping and File Parts"
Cohesion: 0.14
Nodes (9): decrypt(), _extract_clean(), extract_text(), ingest_file(), ingest_file_parts(), PdfError, sanitize(), split_parts() (+1 more)

### Community 63 - "Hermes config.yaml (Repo)"
Cohesion: 0.13
Nodes (14): approvals, destructive_slash_confirm, compression, min_tail_user_messages, threshold_tokens, plugins, enabled, security (+6 more)

### Community 64 - "Ledger Tables: Cards, Card Payees, Transactions and Subscriptions (Runtime)"
Cohesion: 0.16
Nodes (18): bca-9706 (bca card; statement day 12, due day 28, transfer to num-9706), cimb-9888 (cimb card; statement day 19, due day 7, transfer to num-9888), dbs-5685 (DBS card; statement day 25, due day 10, transfer to num-5685), hsbc-5915 (HSBC card; statement day 19, due day 4, transfer to num-5915), mandiri-4365 (mandiri card; statement day 16, due day 5, paid via app_menu), mega-5855 (Mega card; statement day 22, due day 7, transfer to num-5855), langganan category (1 rule), num-* card payees (num-0480, num-1111, num-4365, num-5685, num-5855, num-5915, num-9706, num-9888; no card in the cards table ends in 1111) (+10 more)

### Community 65 - "Plan Invariants (invariants.py: plan_errors, simulation_errors, require) and Their Tests, with the Plan-Bills Check (bills_of)"
Cohesion: 0.15
Nodes (7): bills_of(), TheChecksCatchBrokenNumbers, CalculationError, plan_errors(), require(), simulation_errors(), _whole()

### Community 66 - "Ledger Thresholds, Budgets and Plans"
Cohesion: 0.11
Nodes (23): jago-darurat (Jago savings account), belanja-harian category (3 rules), belanja-online category (15 rules), berhenti:supir category (12 rules), biaya-bank category (48 rules), bunga category (24 rules), donasi category (7 rules), gaji category (9 rules) (+15 more)

### Community 67 - "Hermes Assumptions, Architecture, Vault-Tools Surfaces (/mcp and /internal) and Requirements"
Cohesion: 0.08
Nodes (43): Architecture (M1 skeleton), Hermes pin: nousresearch/hermes-agent v0.22.5 (manifest digest recorded, checked 2026-10-27), /rincian handled in pre_gateway_dispatch with skip plus direct Bot API send, vault (Hermes finance bot container), vault-tools (vault zone tool service), Assumption spikes (Hermes v0.22.5), Card token placeholder [[CARD:****last4]], cardguard plugin (card-number rewrite in pre_gateway_dispatch) (+35 more)

### Community 68 - "Payday Plan Spec: Funding Order and Tiers, Worked Example, Payday Window and Bills Paid Once"
Cohesion: 0.14
Nodes (17): Payday plan spec (vault_tools/payday.py), Bills paid once (2026-11-01): an open one is an essential in the plan of every payday after the day it was recorded whose window reaches its due date, Estimated cost of delay per shortfall (amount * late_cost_bp / 10000, rounded half up), daily_allowance (cash_to_hold // days_in_window, salary part only, stored never shown), Tier 3: debt installments and pool-account transfers, Tier 2: essentials (fixed expenses, e.g. school; bills paid once), late_cost_bp input (late cost in basis points), Tier 0: overdue (due before payday) (+9 more)

### Community 69 - "Control Bot Auth and Applied-Outcome Tests"
Cohesion: 0.16
Nodes (6): handle(), is_authorized(), AppliedTests, AuthTests, HandleTests, msg()

### Community 70 - "Progress: M4 Comms Built in the Repo (Not Deployed), Open Question 18 and the Owner's Choices, the Brokers, Proxies and First-Start Steps"
Cohesion: 0.17
Nodes (26): api.notion.com (allowed through squid-vault), calendar-broker (calendar.events.readonly: the primary calendar, read-only, at most 31 days a request, no attendee addresses or links), card-bus (to hand work between zones; deferred, comms has its own bot instead), comms (the mail and calendar assistant: Hermes on Haiku 5.5 with its own bot and its own Anthropic key, only the six tools of the two brokers), Comms' Anthropic key from a third workspace with its own limit, as front has, Backups already cover hermes-comms and the new secrets (scripts/backup.sh takes all of /opt/personal-agent-data and /opt/personal-agent-secrets), comms brokers test suite (64 tests; 765 pass across all suites, 480 in vault-tools), Comms daily mail summary on a schedule (it would message the owner unasked) or only when asked (built: cron off) (+18 more)

### Community 71 - "Compose Logging Options"
Cohesion: 0.22
Nodes (16): logging, logging, logging, logging, driver, options, max-file, max-size (+8 more)

### Community 72 - "Compose: ingest-gmail Service and Env Settings"
Cohesion: 0.14
Nodes (14): build, cap_drop, cpus, depends_on, mem_limit, networks, profiles, read_only (+6 more)

### Community 73 - "Compose: vault-tools and ingest-gmail Services"
Cohesion: 0.08
Nodes (26): environment, environment, APPLIER_OUTCOME_DIR, CONTROL_REPO_DIR, CONTROL_STATE_DIR, HTTPS_PROXY, MY_TELEGRAM_ID, NO_PROXY (+18 more)

### Community 74 - "Bot Activity: Gateway Lifecycle, Shutdowns and Restarts"
Cohesion: 0.12
Nodes (21): Hermes API server (127.0.0.1:8642, model hermes-agent), logs/container-boot.log, Hermes cron scheduler, Delivery obligations, Gateway drain timeout and runtime_draining pauses, /opt/data/.env (loaded by run_agent), Gateway control socket (/opt/data/gateway.sock), logs/gateway.log (+13 more)

### Community 75 - "Report Renderers for /rencana, /anggaran, /cicilan and /tagihan (reports.py)"
Cohesion: 0.32
Nodes (20): _anggaran(), b(), _banks(), _belanja(), bln(), build(), _cicilan(), _data() (+12 more)

### Community 76 - "Google Session and Token Refresh (GoogleSession, the Token Loader) and Its Tests (FakeToken)"
Cohesion: 0.14
Nodes (5): GoogleSession, FakeToken, Session, session(), Failures

### Community 77 - "Compose Service: control"
Cohesion: 0.14
Nodes (14): build, cap_drop, cpus, depends_on, mem_limit, networks, oom_score_adj, read_only (+6 more)

### Community 78 - "Compose Service: vault (Hermes)"
Cohesion: 0.14
Nodes (14): vault, command, cpu_shares, cpus, depends_on, env_file, image, mem_limit (+6 more)

### Community 80 - "Compose Project and Containers (Runtime): Squid Proxies, Change-Proposals and Control With Their Env, Secrets and Approval Dirs, Networks and Hardening"
Cohesion: 0.09
Nodes (47): Anonymous squid log and spool volumes (8, from image VOLUME lines), cap_drop ALL (every container except vault: change-proposals, control, front, the four squids, vault-tools), change-proposals healthcheck (Python TCP connect to 127.0.0.1:8000, 3 s timeout), Compose project personal-agent (compose/docker-compose.yml), control.py (python -I control.py, workdir /app), change-proposals env (PROPOSALS_INBOX_DIR; no proxy env), CHANGE_PROPOSALS_MCP_TOKEN (front env name), Control env (MY_TELEGRAM_ID value masked, TELEGRAM_TOKEN_FILE, PROPOSALS_INBOX_DIR, CONTROL_STATE_DIR, APPLIER_OUTCOME_DIR, CONTROL_REPO_DIR) (+39 more)

### Community 81 - "Payday Plan Output (Transfers, Fees, Cash to Hold, Living Money) and the Daily-Account Re-Anchor Rule"
Cohesion: 0.13
Nodes (18): jago-harian account alias, living_reserve (protected living money, the owner's choice since 2026-10-28), saldo_rekening tool (re-anchors the month's daily money to the balance given), Anchor correction (difference with the records), cash_to_hold (salary minus funded minus fees), fees (plan output list: date, destination, amount, kind kartu or transfer), health.living_anchor, jago-harian daily account (+10 more)

### Community 82 - "Front Compose Service"
Cohesion: 0.10
Nodes (20): path, required, cap_add, cap_drop, command, cpu_shares, cpus, depends_on (+12 more)

### Community 83 - "Debt Upserts With Autodebit and Their Tests (upsert_debt, test_autodebit.py)"
Cohesion: 0.23
Nodes (6): car(), InThePlan, Rules, setup(), upsert_debt(), upsert_debt()

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

### Community 89 - "Gmail OAuth Guide, Token Renewal and Sender Allowlist, the Comms Tokens and Consents, and the Ingest-Failure Alert (2 Nov Deploy)"
Cohesion: 0.10
Nodes (50): Control zone and control service (approvals, no LLM, net-ctl), squid-ctl proxy (api.telegram.org only), Gmail OAuth guide (readonly) for ingest-gmail, Bank sender allowlist with DKIM/DMARC pass (DBS, CIMB Niaga, HSBC, Mandiri, Mega), The brokers read the token file again before every refresh, so a renewal needs no restart, calendar_comms_token (calendar-broker's token in the comms zone, calendar.events.readonly, M4), Comms consent screen (External, app personal-agent-comms, Testing, the owner as the only test user; scopes gmail.modify and calendar.events.readonly only), comms-desktop OAuth client (stored on the VPS as google_comms_client) (+42 more)

### Community 90 - "State Snapshot: the Ledger Database, Card, Statement and Instalment Tables, Card Payments, Payday Plans and Their Progress, Pots and the Usulan Items"
Cohesion: 0.07
Nodes (58): mcp__vault_tools__simulasi_skenario, Ledger backups made 2026-10-27: pre-v4, v5, v6, v8, v9, categorize, completeness, instkey, owner-names, pending, perantara, pocketfix, scans, subs, bca-9706 card (10 statements 2026-01-12 to 2026-10-12, last due 2026-10-28; 8 instalment rows), card_installment_scans table (25 rows, 25 scanned statements), card_installments table (26 instalment rows across 5 cards), Card line kinds (belanja 493, biaya 134, bunga 36, cicilan 109, langganan 181, pembayaran 78, refund 35), card_lines table (1066 card statement lines), card_payments table (7 rows, one payment per card, last 2026-10-28 to 2026-10-30) (+50 more)

### Community 91 - "Category Suggestions: Groups, Apply and Their Tests (suggest.py, test_living.py)"
Cohesion: 0.08
Nodes (16): plan(), Suggestions, card_paid(), _not_a_card_bill(), own_cards(), set_category_keyword(), add_owner_name(), apply_suggestions() (+8 more)

### Community 92 - "Expense Corrections (Edit, Delete and List) and Receipt Merging (merge_receipts), with the Corrected-Source Merge Tests (test_corrections.py)"
Cohesion: 0.06
Nodes (24): CorrectedSourceFindsItsStatementRow, Edit, log(), MergedRecords, OnlyTheOwnersRecords, pho(), world(), log() (+16 more)

### Community 94 - "State Snapshot: Accounts, Transactions and Mutation Files, Categories, the Change Log, Debts, Balance Reports, the Usulan Table, Data Fixes and Ledger Backups"
Cohesion: 0.12
Nodes (40): mcp__vault_tools__periksa_data, mcp__vault_tools__record_expense, mcp__vault_tools__record_mutations, mcp__vault_tools__saldo_rekening, accounts table (8 rows), Autodebit (autodebet) of debt instalments, Ledger backups made 2026-10-28: pre-answers, calibrate, cardbudget, cardlines, daily-account, dedupe, dedupe-cards, ef-pocket, flazz-fix, held-balance, invariants, keywords, latest, notion, pot-schedule, recal-v2, recurring, rules2, scenarioA, balance_reports table (8 rows: mandiri-utama 4, jago-harian 4) (+32 more)

### Community 95 - "Ledger Audit (/periksa) and the Subscriptions Store, with Their Tests (audit.py, subscriptions.py)"
Cohesion: 0.10
Nodes (18): Audit, found(), line(), stmt(), world(), SubscriptionLog, Recurring, OwnerRules (+10 more)

### Community 96 - "Deploy 2 Data Fix"
Cohesion: 0.24
Nodes (5): allocation(), copy(), plan(), report(), say()

### Community 98 - "Compose Networks"
Cohesion: 0.20
Nodes (10): internal, internal, internal, internal, networks, egress, net-comms, net-ctl (+2 more)

### Community 99 - "Compose Squid Template"
Cohesion: 0.20
Nodes (10): x-squid, cap_add, cap_drop, cpus, image, mem_limit, oom_score_adj, restart (+2 more)

### Community 100 - "Progress: Bank Mutations, Doubled Rows and the Data Fixes, Receipt Merges, the Card-Repayment Fix, Record Corrections, the /periksa Audit and the Category Scheme"
Cohesion: 0.09
Nodes (56): jago-harian account (daily pocket), jago-utama account (one Jago statement file for every pocket), periksa_data audit rule 8: the ledger gap reported as a MASALAH, Bank mutations Jan-Oct (BCA, Mandiri, Jago; verified complete, October BCA CSV reconciled), BUKU TIDAK COCOK warning (ledger_gap): the account's rows over the file's period no longer add up to its balance change, _by_balance (holds the UNSORTED_ELSEWHERE fragment; dropping it undoes the rule), Data fix ops/datafix/2026-11-01-card-internal (backup ledger.db.bak-pre-card-internal; the four card rules and rows to wajib:kartu, the two pocket rules and four rows to bunga / biaya-bank; 14 change_log rows), Guard: transfer_internal refused for an own card's payment (set_category, set_category_rule; set_category_keyword skips those rows and says how many; apply_suggestions skips a refused group and names it) (+48 more)

### Community 101 - "Gmail Sender Authentication Checks and Tests (auth.py)"
Cohesion: 0.17
Nodes (6): auth_ok(), _clauses(), from_address(), safe_label(), Auth, hdrs()

### Community 102 - "Change-Proposal Submission Tests"
Cohesion: 0.22
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

### Community 106 - "Gmail Ingest Run Module: Config, Message Processing and Retention (run.py)"
Cohesion: 0.24
Nodes (8): main(), Config, emit(), _headers(), _pdf_parts(), process_message(), _state(), sweep_retention()

### Community 107 - "Host Systemd Units and Their Scripts (pa-* Services and Timers incl. the Ingest Alert) and Stack Settings"
Cohesion: 0.12
Nodes (25): gmail_ingest_token secret, restic.env secret (mode 0600), config/stack.env (non-secret stack settings), pa-backup.service + timer (restic backup, daily 02:00 WIB), pa-check.service + timer (restic integrity check, 1st of month 04:00 WIB), pa-disk.service + timer (disk usage check, hourly), pa-forget.service + timer (restic retention 7d/4w/6m, Sun 04:00 WIB), pa-gmail-token.service + timer (warns before the Gmail OAuth token expires, daily 08:00 WIB) (+17 more)

### Community 108 - "Calibration Runbook: Overview, Number Rules, Spend, Quality and Data Reviews, One-Shot Tests and the /periksa Checks"
Cohesion: 0.07
Nodes (29): Bot calibration runbook (manual, on the owner's request), ops/calibration/bot_quality.py (tool errors, replies that apologise or correct themselves), ops/calibration/bot_usage.py (cost per day and source at list prices), cardguard plugin (appends the number-guard flag), Hermes cost_status unknown for claude-sonnet-5-5 (compare by hand), Data review (read-only), hermes chat --oneshot with the UJI KALIBRASI prefix (no recording or changes), Instalments gone from the statement check (+21 more)

### Community 109 - "State Snapshot: Timers, Jobs, Restic, Runs and the Pre-Deploy Ledger Backups"
Cohesion: 0.12
Nodes (27): docs/runtime/README.md, State snapshot, applier journal line: #N skipped (1 in 7 days), ledger.db.bak-pre-card-internal (with -shm and -wal copies), ledger.db.bak-pre-deploy2 (with -shm and -wal copies), ledger.db.bak-pre-ingest-alert (made 2026-11-02, with -shm and -wal copies), ledger.db.bak-pre-m3 (with -shm and -wal copies), ledger.db.bak-pre-mandiri-dupes (with -shm and -wal copies) (+19 more)

### Community 110 - "Masking (masking.py: mask_sensitive, Luhn Check), Basis Points (bp_of) and Their Tests"
Cohesion: 0.13
Nodes (8): Masking, Masking, Money, luhn_valid(), _mask_digits(), mask_sensitive(), repl(), bp_of()

### Community 112 - "Card Installments (card_installments.py)"
Cohesion: 0.15
Nodes (11): Installments, OneCardOneAlias, Overview, world(), active(), _add_months(), format_list(), monthly_total() (+3 more)

### Community 113 - "Gmail Broker Class: Search, Read, Labels, Draft Replies, Hidden Finance Mail and the Call Budget (Broker, Budget)"
Cohesion: 0.19
Nodes (4): Budget, Broker, headers(), when()

### Community 114 - "Front SOUL (Persona, Tasks, Answer Style, Security, Change Submission) and the Card-Number and Finance Rules of Front and Comms"
Cohesion: 0.09
Nodes (18): Finding 2026-11-01: getMe showed Allow Groups still on for @danoevault_agent and @danoecontrol_bot, Hermes configs drop groups (allowed_chats: none); control drops them in code, Comms step 8: /start to the comms bot, then ask for this week's mail and tomorrow's events: a bank email must not come up, Finding: BotFather Allow Groups still on for the vault and control bots (getMe 2026-11-01), cardblock plugin (services/hermes/front/plugins/cardblock, mounted read-only): drops every inbound message holding a Luhn-valid 13-19 digit run before Hermes dispatches it, Comms card numbers: front's cardblock plugin, the same code mounted read-only, drops an inbound message with a Luhn-valid run before dispatch, Finance mail hidden from comms, decided on every call: a Keuangan or Keuangan/* label, or the bank domains of ingest-gmail (labelled or not; a sender that is not one plain address counts as hidden), Hermes zones answer only TELEGRAM_ALLOWED_USERS and drop every group (allowed_chats: none, checked against v0.22.5) (+10 more)

### Community 115 - "Expense, Pace and Health Core (health.py: record_expense, spending_pace, health_check), Balance Readings, Set Category, the Unsorted-Elsewhere Rule and Their Tests"
Cohesion: 0.05
Nodes (33): BalanceCheck, LivingMoneyPace, PlanInForce, UnsortedElsewhere, account_balances(), alerts_for(), budget_status(), _by_balance() (+25 more)

### Community 116 - "Vault SOUL: Owner Rules, Auto-Debits, Balances, Subscriptions, the Payday List on the 1st, Long-List Commands and Telegram Answer Style"
Cohesion: 0.10
Nodes (15): Auto-debit debts (upsert_debt pay_method=autodebit; one figure per account incl. the bank-held minimum), belanja_kartu (/belanja: statement lines per cycle and per card; not reading PDFs), Daily living account (uang-harian at Jago; the owner spends daily only from it), Digital subscription rules (subscriptions_status; upsert_subscription only after the owner confirms; stored notes kept), Financial analysis (cashflow_summary, recurring_payments, suggest_salary, list_uncategorized, set_category_rule), Long-list commands (/rencana, /tagihan, /belanja, /cicilan, /anggaran, /peta, /kondisi, /data, /periksa), Payday list on the 1st (main flow, steps 0-5; no automatic reminders), periksa_data (data check: MASALAH and PERHATIAN; compares subscriptions with card charges) (+7 more)

### Community 117 - "Front Cardblock Plugin (cardblock) and the Change-Proposals Module (proposals.py: ProposedFile, submit, the _Auth Middleware and MCP Imports)"
Cohesion: 0.09
Nodes (13): _Auth, create_app(), submit(), main(), ProposedFile, _bot(), _digits_of(), find_numbers() (+5 more)

### Community 118 - "Zone Isolation, Egress Allowlist and Comms Zone Tests (test_zones.py), with the Deploy Rsync and Build-Context Tests (test_deploy.py)"
Cohesion: 0.06
Nodes (12): BuildContexts, deploy_rsync(), read(), Rsync, Compose, compose(), Egress, HermesProfiles (+4 more)

### Community 119 - "Front Change Applier (applier.py): Applier Class, Run Loop, Install Time, Lock, Recovery, Outcomes and DB Rows"
Cohesion: 0.15
Nodes (5): Applier, main(), sha(), stamp(), write_json()

### Community 121 - "Rupiah Formatting and Fee Lines (format_idr, fee_parts) and the Rincian Builder (rincian.py: build, describe)"
Cohesion: 0.12
Nodes (16): format_idr(), describe(), _bank(), build(), account(), describe(), mark(), _nice() (+8 more)

### Community 122 - "Front Hermes Config"
Cohesion: 0.13
Nodes (14): approvals, destructive_slash_confirm, plugins, enabled, security, allow_lazy_installs, sessions, retention_days (+6 more)

### Community 123 - "Host-Script and Plugin Test Modules: Cardblock and Cardguard Same Detection, Gmail Token Check, PDF Password Collection, In-Place Rewrite and Token Scopes"
Cohesion: 0.09
Nodes (8): defaults_module(), load(), SameDetectionAsVault, Scopes, issued(), TokenCheck, Collect, InPlace

### Community 124 - "Hermes Telegram Gateway Config"
Cohesion: 0.33
Nodes (6): allowed_chats, disable_link_previews, gateway, platforms, telegram, extra

### Community 125 - "Progress: Plan in Force, Marking Transfers Done With Two Open Plans, the Payday Window and the Daily-Account Balance Reading"
Cohesion: 0.25
Nodes (17): les Mandarin transfer (left in Mandiri on 30 Oct; not paid yet on 2 Nov, its money set aside outside the daily account, still open in the 30 Oct plan), _living_balance (a daily-account balance correcting the month; reads the plan in force while today is before its next payday), living_balance_mark (system key: last transaction id at the reading), living_balance_report (system key: the balance_reports row of the reading), Finding (latent since the bot went live): three readers took the newest row of plans as the plan in force (spending_pace, _living_balance, _open_transfers), Next step done 2 Nov morning: the owner's /new to vault after the 2 Nov 01:23 WIB deploy (transfer_selesai has gajian); the 30 Oct lesson fee is not paid yet, its money set aside outside the daily account (no correction): tell the bot once it is paid, PAYDAY_LOOKBACK_DAYS (7 days after a payday current_payday turns to the coming one), Payday window (current_payday, 7 days after payday) (+9 more)

### Community 126 - "Report Builder and Usulan Report Tests with the Telegram HTML Tag Balance Check (test_reports.py)"
Cohesion: 0.16
Nodes (4): Balanced, check_html(), Reports, world()

### Community 127 - "Hermes Agent Block"
Cohesion: 0.50
Nodes (4): agent, disabled_toolsets, max_turns, reasoning_effort

### Community 128 - "Hermes Memory Settings"
Cohesion: 0.50
Nodes (4): memory, memory_enabled, user_profile_enabled, write_approval

### Community 129 - "Cardguard Plugin Manifest"
Cohesion: 0.50
Nodes (3): description, name, version

### Community 130 - "Approvals Flow and the Applier (M3): Control Bot and Its Sender Check, Proposal Cards, Change-Proposals, Install and Uninstall, Trust Rules and Rollback"
Cohesion: 0.08
Nodes (44): Applier (services/applier, a root host unit; installed 2026-11-01 23:23 WIB): applies an approved front change and writes applier/outcome/<id>.json, applier/outcome folder (the applier, a root host unit, writes; control reads it read-only), Approvals flow (M3): front submit -> proposals-inbox -> control re-validates, posts its own diff against the installed files, then the card -> the owner's tap recorded in control-state -> the applier applies an approved front change and writes applier/outcome/<id>.json, which control reports once, Control commands /status (counts, with the applier's outcomes), /usulan (re-post waiting proposals with their buttons), /ping, Control posts the diff it computes itself against the installed files (read-only mounts of services/hermes/front/ and config/squid/), then the card, control-state folder (control only writes; the applier reads approved/ and control.db read-only), scripts/data-dirs.sh (creates the M3 folders), proposals-inbox folder (change-proposals writes, control reads and empties it) (+36 more)

### Community 131 - "Hermes Session Store and Telegram Delivery"
Cohesion: 0.11
Nodes (24): failed_turn messages, Preflight-compression log line (shows the threshold in force when it was written), Log line 'Re-anchored stale current_turn_user_idx' (agent/turn_iteration_prep.py; counts mid-turn compactions), Logger agent.context_compressor (69 INFO), Logger agent.conversation_compression (292 INFO), Gateway session keys (agent:main:local:dm 38, agent:main:telegram:dm 1, plus _README), sessions/sessions.json (gateway session key to session, with token and cost counters; 39 keys), sessions.retention_days 90 (same as the default: inactive days of ended-session history kept) (+16 more)

### Community 132 - "Progress: Daily-Money Pace, Uncategorized Payday Transfers, No Per-Day Figure, the Health Check and the Report Commands"
Cohesion: 0.14
Nodes (18): BELUM DIHITUNG line (outgoing mutations waiting for a category) in ringkasan_data, belum dihitung in /anggaran, an info finding in health_check, /anggaran report command (budgets), /bantuan report command (help), /cicilan report command (instalments), /data report command, /kondisi report command, daily_allowance (stored salary part; stored plans not rewritten, never shown), Daily money alerts (80% and over 100%) stay (+10 more)

### Community 133 - "Front Auxiliary Models"
Cohesion: 0.20
Nodes (10): auxiliary, compression, title_generation, vision, model, provider, model, provider (+2 more)

### Community 137 - "Front Change-Proposals MCP"
Cohesion: 0.20
Nodes (10): connect_timeout, headers, timeout, tools, url, Authorization, mcp_servers, change_proposals (+2 more)

### Community 139 - "Persistent Data Dir (/opt/personal-agent-data): Ingest Data and the Upload Relay (the pa-uploads Timer and Its Sync Script), Hermes Data Dirs and Env Files"
Cohesion: 0.15
Nodes (18): /opt/personal-agent-data/hermes-vault (rw at /opt/data), /opt/personal-agent-data/ingest (read-only at /ingest), canary.txt (root-owned file in the data dir, mode 0644), front.env (root-only env file, mode 0600), hermes-vault data dir (mode 0700), ingest data dir (mode 0755), ingest-state dir (mode 0755), /opt/personal-agent-data (persistent state, root-owned, restic-backed) (+10 more)

### Community 140 - "Comms Service (docker-compose.comms.yml: Env File, Capabilities, Limits, Command)"
Cohesion: 0.10
Nodes (20): cap_add, cap_drop, command, cpu_shares, cpus, depends_on, env_file, image (+12 more)

### Community 141 - "Ingest Alert Tests: Main Run, Dry Run and Reasons (test_ingest_alert.py)"
Cohesion: 0.33
Nodes (3): ev(), Main, Reasons

### Community 142 - "Front Telegram Chat Filter"
Cohesion: 0.33
Nodes (6): allowed_chats, disable_link_previews, gateway, platforms, telegram, extra

### Community 143 - "Gmail API Client and Its Errors (client.py)"
Cohesion: 0.16
Nodes (3): GmailClient, GmailError, TokenError

### Community 144 - "Front Memory Settings"
Cohesion: 0.40
Nodes (5): memory, memory_enabled, nudge_interval, user_profile_enabled, write_approval

### Community 145 - "Applied-Pull Tests (test_applied_pull.py)"
Cohesion: 0.41
Nodes (3): AppliedPull, committed(), sha()

### Community 146 - "Vault Tools Module (tools.py): Obligations, Payday Plan and Status, Bills, Cards, Emergency Fund, Auto-Debit Check and Pot Balances"
Cohesion: 0.05
Nodes (52): Plan, dana_darurat(), paid(), saldo_pot(), status_gajian(), _rata_deposit(), autodebit_check(), bill_status() (+44 more)

### Community 147 - "Cashflow Summary, Recurring Payments, Uncategorized Rows and the Merchant Key (mutations.py: cashflow, recurring, normalize)"
Cohesion: 0.12
Nodes (9): excluded(), list_uncategorized(), normalize(), recurring(), _reworded(), set_category_rule(), list_uncategorized(), recurring_payments() (+1 more)

### Community 148 - "Card Lines: Per-Card Detail (card_detail, format_detail, belanja_kartu) and Its Tests"
Cohesion: 0.33
Nodes (4): PerCard, card_detail(), format_detail(), belanja_kartu()

### Community 149 - "Front Agent Limits"
Cohesion: 0.50
Nodes (4): agent, disabled_toolsets, image_input_mode, max_turns

### Community 150 - "Hermes Vault Env and Credentials: Telegram Allowlist, Stranger Handling, Credential Pool and the Vault-Tools MCP Config (Live)"
Cohesion: 0.20
Nodes (11): auth.json (Hermes credential store and pool, empty; the API key comes from env; never opened by the collector), Vault container environment variable names (values never read), ANTHROPIC_API_KEY env var (where the Anthropic key comes from; value never read), HERMES_SKIP_CONFIG_MIGRATION env var, TELEGRAM_ALLOWED_USERS env var (Telegram user allowlist; value never read), VAULT_TOOLS_MCP_TOKEN env var (Bearer for the vault_tools MCP server; value never read), Log line 'credential pool: no available entries' (agent/credential_pool.py; benign), Logger agent.credential_pool (72 INFO) (+3 more)

### Community 151 - "Calibration Runbook: Owner Rules, Change-and-Verify, Dry Run, Root Causes and Worktree-Only Changes"
Cohesion: 0.20
Nodes (4): Read the audit and the plan for the coming 1st, Change and verify, ops/calibration/dry_run.py on a copy of the live ledger, Unit test suites (vault-tools, hermes vault, ingest-gmail, root tests)

### Community 156 - "Front Model Setting"
Cohesion: 0.67
Nodes (3): model, default, provider

### Community 157 - "Comms Zone (M4, Not Deployed): Architecture and Rules, the Comms SOUL, the Gmail and Calendar Brokers, squid-comms and the Trust-Boundary Split of the Zones"
Cohesion: 0.07
Nodes (41): brokers: gmail-broker and calendar-broker (comms zone, M4, not deployed; services/comms-brokers, no LLM), calendar-broker: list_events and search_events on the calendars brokers/policy.json names (the primary one), read-only, card-bus MCP (replaces Kanban; not built with M4, 2026-11-02), comms (Hermes on Haiku, services/hermes/comms; its own bot, its own Anthropic key and the two broker tokens from scripts/render-comms-env.sh), Comms flow (M4, in the repo since 2026-11-02, not deployed): the owner -> comms's own bot -> comms -> MCP over net-comms with a bearer token each -> gmail-broker or calendar-broker -> squid-google -> the Gmail and Calendar APIs, Only the brokers hold a Google token, one scope each (gmail_comms_token: gmail.modify; calendar_comms_token: calendar.events.readonly), Comms zone (email and calendar, net-comms: comms, gmail-broker, calendar-broker and squid-google; M4, in the repo since 2026-11-02, not deployed: compose/docker-compose.comms.yml, compose profile comms), egress network (the squid proxies only, squid-google with the comms zone; to the internet) (+33 more)

### Community 158 - "Vault Tool Search Setting"
Cohesion: 0.67
Nodes (3): enabled, tools, tool_search

### Community 159 - "Infrastructure Files: Dockerfiles, Compose and Squid Allowlists"
Cohesion: 0.11
Nodes (35): /opt/personal-agent-data/vault-tools (rw at /data), nousresearch/hermes-agent image (no tag, created 2026-10-23), proposals-inbox dir (mode 0700, empty), anthropic_vault_key secret, notion_token secret, vault_tools_mcp_token secret, vault-tools data dir (mode 0700), calendar-broker (brokers.gcal, module named by compose) (+27 more)

### Community 162 - "Calendar Broker (gcal.py: Broker, Calendar, Policy) and Its Tests (test_gcal.py, Events, CalendarPolicy)"
Cohesion: 0.07
Nodes (15): Broker, Calendar, _events_path(), Policy, calendar_broker(), CalendarPolicy, Events, Asisten email dan kalender pemilik (comms) (+7 more)

### Community 163 - "Vault-Tools Container and MCP Server (Runtime): Env, Proxy, Surface Tokens and the Notion Sync"
Cohesion: 0.14
Nodes (21): Containers runtime map (compose project personal-agent), front NO_PROXY: localhost, 127.0.0.1, change-proposals (proxy env HTTPS_PROXY and HTTP_PROXY point at squid-front:3128), LEDGER_DB=/data/ledger.db (vault-tools env), vault NO_PROXY: localhost, 127.0.0.1, vault-tools, vault-tools proxy env (HTTPS_PROXY http://squid-vault:3128, NO_PROXY localhost, 127.0.0.1), VAULT_TOOLS_MCP_TOKEN and VAULT_TOOLS_INTERNAL_TOKEN (vault env names), make runtime-map (regenerates the runtime map), ops/runtime-map/collect.py (runtime map generator) (+13 more)

### Community 164 - "Gmail Client Tests: Pagination and Attachment Decoding (test_ingest.py), and the Sender Config Loader (load_senders, SenderConfig)"
Cohesion: 0.20
Nodes (4): load_senders(), b64(), Client, SenderConfig

### Community 166 - "Progress: Payday Plans, Admin Fees, Daily Money Rules, the 30 Nov Rehearsal, Deploy 2, Pots and the Emergency Fund"
Cohesion: 0.07
Nodes (65): fee_estimate (simulation fees after cycle 1: one per fixed cost, instalment paid by transfer, card with a bill now, pot, emergency fund and the living money), Mandiri account (salary lands here; auto-debit account), Admin fees (/usulan #4: the owner's estimates per card payment and per other transfer; the Mandiri card via the bank-app menu and the auto-debits cost nothing), Auto-debits from Mandiri (car instalment MTF, SPayLater), balance_reports table (bank-app balance reported by the owner), biaya_admin_mulai (fees count from the 30 Nov payday, 20261130), Car instalment (MTF, incl. admin; auto-debit on day 2), card_advice (no longer offers cutting the living money) (+57 more)

### Community 168 - "Fixed Expenses and Children's Fees"
Cohesion: 0.15
Nodes (14): berhenti:trip-mancing category (1 owner keyword), komisi-allianz category (1 owner keyword), perantara:art-belanja-anak category (1 owner keyword), sekali:keluarga-istri category (1 owner keyword), wajib:ipl category (10 rules), wajib:les category (4 owner keywords), wajib:sekolah category (3 rules), Children's lesson fees (3 les-* fixed expenses due day 1, each to a BCA account payee) (+6 more)

### Community 170 - "Mandiri Doubled Rows Data Fix (fix_data.py)"
Cohesion: 0.48
Nodes (4): files(), gap(), plan(), show()

### Community 171 - "Broker MCP Servers and Their Tests (GmailServer, CalendarServer, create_app, Served, test_server.py)"
Cohesion: 0.13
Nodes (8): answer(), create_app(), list_events(), search_events(), CalendarServer, enums(), GmailServer, Served

### Community 172 - "Cardblock Plugin Manifest"
Cohesion: 0.50
Nodes (3): description, name, version

### Community 174 - "Statement Recording and Its Tests (record_statement, RecordStatement)"
Cohesion: 0.32
Nodes (3): card_db(), RecordStatement, record_statement()

### Community 177 - "Statement Intake Tests (PdfIntake: ingest, file_sha256, make_pdf)"
Cohesion: 0.26
Nodes (5): make_pdf(), McpIngest, PdfIntake, file_sha256(), ingest()

### Community 178 - "Ledger Accounts, Payee Secrets and Sinking Funds"
Cohesion: 0.15
Nodes (17): bca-utama (BCA main account), fixed-expenses (Jago savings account), jago-harian (Jago main account), jago-utama (jago main account), jenius-akun (Jenius main account, also a payee), pot-jago (Jago pool account), jenius-0480 (jenius card; statement day 26, due day 13, transfer to jenius-akun), cryptography package (50.0.2) (+9 more)

### Community 179 - "Deterministic Statement Reconciliation (reconcile.py) and Its Tests"
Cohesion: 0.13
Nodes (6): Ledger, Reconcile, has_forbidden_card_data(), reconcile(), Reconciliation, store_payee()

### Community 180 - "Hermes Pending Skill Proposals and Curator, Uploads Cache and the Upload and Usulan Tools (Live)"
Cohesion: 0.19
Nodes (14): Image routing: text mode (pre-analysis via vision_analyze), Telegram text and photo-burst batch flushing, vision_analyze (engine image tool), Proposed skill card-spend-breakdown-advisory (productivity, created 2026-10-28, pending approval), catat_usulan (record a proposal when the bot hits a limit: a missing tool, calculation or command, instead of a workaround), Proposed skill credit-card-statement-intake (productivity, created 2026-10-28, pending approval), ingest_statement (read a financial file, PDF, CSV or TXT, from the ingest folder or a Telegram upload, decrypting it), list_uploads (files the owner recently uploaded via Telegram, newest first, as file_ref for ingest_statement) (+6 more)

### Community 181 - "Roadmap Date Helpers (add_months, next_due, _clamp) and Their Tests"
Cohesion: 0.42
Nodes (4): Dates, add_months(), _clamp(), next_due()

### Community 182 - "Front Compression Settings"
Cohesion: 0.67
Nodes (3): compression, min_tail_user_messages, threshold_tokens

### Community 185 - "Bank Admin Fee Estimates and Rules"
Cohesion: 0.19
Nodes (12): Admin fees (estimates, 2026-11-01: a bank fee per transfer out of the salary account), biaya_admin:<alias> (sets one item's fee; 0: none), biaya_admin_kartu (estimated fee per payment to a card number, capped), biaya_admin_mulai (payday from which fees count, YYYYMMDD; 20261130 live), biaya_admin_transfer (estimated fee per other transfer, capped), Tier 4: card remaining balance (default: pay in full), Tier 1: card minimum due, Kartu dbs-1111 (dummy card alias in the example) (+4 more)

### Community 186 - "Ledger Categories and Thresholds"
Cohesion: 0.31
Nodes (9): mandiri-utama (Mandiri main account), wajib:cicilan category (9 rules), wajib:spaylater category (3 rules), cicilan-mobil (debt to MTF, autodebit from mandiri-utama, due day 2), spaylater (debt to Shopee SPayLater, autodebit from mandiri-utama, due day 1), debt_payments (ledger table, 2 rows), debts (ledger table, 2 rows), net_snapshots (ledger table, 2 rows) (+1 more)

### Community 187 - "Change-Proposals and Comms-Broker Requirements (Pinned mcp and uvicorn), Surface Tokens and Comms Holding No Google Token"
Cohesion: 0.26
Nodes (12): change-proposals (front zone, M3, submit tool), Comms step 4: make secret-gen NAME=gmail_broker_mcp_token TYPE=token and NAME=calendar_broker_mcp_token TYPE=token, change-proposals (one tool submit, bearer token change_proposals_mcp_token, inbox mount only; caps five waiting and ten per 24 hours), comms holds no Google token or client; it reaches each broker over net-comms with that broker's own bearer token (/mcp only, constant-time compare), Surface tokens (random, at least 32 chars, must differ, constant-time compare; unknown paths 404), change-proposals requirements.txt, mcp==1.30.0, uvicorn==0.54.0 (+4 more)

### Community 188 - "Vault SOUL: Persona and the Owner's Goal, Security and Data Rules, the Living Reserve, Card Payments, /rincian, Uploads and Statements, Emergency Fund and Onboarding"
Cohesion: 0.15
Nodes (14): SOUL.md: vault bot persona (personal finance advisor and planner), Card instalment recording (x/y lines, record_card_installments, card_installments_status), Card payment method rules (Jenius and BCA to an account, Mandiri via the app menu, others to the card number), Card tokens [[CARD:num-xxxx]] map to stored cards by last 4 digits; then link_card_payees, Chat uploads (list_uploads, ingest_statement, record_mutations; BARIS KURANG means resend with replace=true), dana_darurat (emergency fund status and recorded balance), Email ingest events (ingest_events: new_statement, rejected, skipped, error), Emergency fund (filled each payday before pot and card balances; unexpected events only; dana_darurat records the read balance) (+6 more)

### Community 189 - "Comms Hermes Config (comms/config.yaml): Agent, Model, Approvals, Plugins, Security and Sessions"
Cohesion: 0.12
Nodes (16): agent, disabled_toolsets, image_input_mode, max_turns, approvals, destructive_slash_confirm, model, default (+8 more)

### Community 193 - "Vault Model Setting"
Cohesion: 0.67
Nodes (3): model, default, provider

### Community 199 - "Deploy 2 Script"
Cohesion: 1.00
Nodes (3): idle(), mask(), deploy.sh script

### Community 202 - "Gmail-Broker MCP Tools (create_app: search, read, label, create_draft, answer)"
Cohesion: 0.53
Nodes (6): answer(), create_app(), create_draft(), label(), read(), search()

### Community 205 - "Calendar-Broker Service (docker-compose.comms.yml)"
Cohesion: 0.13
Nodes (15): build, cap_drop, command, cpu_shares, cpus, depends_on, mem_limit, networks (+7 more)

### Community 209 - "Gmail-Broker Service (docker-compose.comms.yml)"
Cohesion: 0.13
Nodes (15): build, cap_drop, command, cpu_shares, cpus, depends_on, mem_limit, networks (+7 more)

### Community 210 - "Vault SOUL: Number Rules, Frequently Asked Numbers, Payday Progress, Pots and Simulations, Usulan and Conversation Calibration"
Cohesion: 0.14
Nodes (7): catat_usulan (records a missing capability or number for /usulan), health_check verdict (decided by the tool, not changed or softened; 2-3 concrete options), Frequently asked numbers, always labelled (no defisit unless tool output), Pot shortfall options (cut games or non-mandatory apps, count the due-day salary, talk to the friend), each tested with simulasi_skenario, simulasi_skenario (what-if: bayar_ekstra_sekarang, hemat_per_bulan, belanja_kartu_per_bulan, pola_pot), sinking_status (pot pattern and forecast at the deadline), status_gajian (payday progress: SUDAH, SUDAH TERCATAT, BELUM MENURUT LEDGER)

### Community 212 - "Card Lines: Statement Processing, Summary, Netting and Reconcile (card_lines.py: process_statement, summary, reconcile)"
Cohesion: 0.15
Nodes (10): _all_instalments(), _card(), _date(), find_file(), _netted(), process_statement(), reconcile(), remember_file() (+2 more)

### Community 214 - "Comms Compose Hardening Anchor and Logging (x-hardened, logging, options)"
Cohesion: 0.20
Nodes (14): logging, logging, logging, driver, options, max-file, max-size, logging (+6 more)

### Community 218 - "squid-google Service (docker-compose.comms.yml)"
Cohesion: 0.15
Nodes (13): squid-google, cap_add, cap_drop, cpus, image, mem_limit, networks, oom_score_adj (+5 more)

### Community 221 - "Google API Fakes (FakeGoogle, FakeGmail, FakeCalendar: route, meta)"
Cohesion: 0.19
Nodes (3): FakeCalendar, FakeGmail, FakeGoogle

### Community 222 - "Comms Compose File, Services and the Squid Anchor (x-squid)"
Cohesion: 0.17
Nodes (11): services, x-squid, cap_add, cap_drop, cpus, image, mem_limit, oom_score_adj (+3 more)

### Community 223 - "Host-Script Modules and Their Tests: Ingest Alert, Applied-Pull, Applier, Deploy Guard, Sync-Uploads, the Graph-First Hook, Completeness and the Runtime-Map Scrub"
Cohesion: 0.05
Nodes (21): fetch(), git(), load_control(), main(), problem(), pull(), sha(), main() (+13 more)

### Community 224 - "Google API Errors and the Gmail Client (GoogleError, TokenError, Gmail._call), with the Short-Reply Tests"
Cohesion: 0.15
Nodes (5): GoogleError, TokenError, Gmail, Replies, run()

### Community 225 - "Comms Hermes MCP Servers (gmail_broker, calendar_broker: Headers, Authorization, Timeouts)"
Cohesion: 0.18
Nodes (12): connect_timeout, headers, timeout, url, connect_timeout, headers, timeout, url (+4 more)

### Community 226 - "Statement Ingest Through the Server (ingest_statement, record_statement), Reference Resolving, PDF Passwords and Upload Listing (list_uploads)"
Cohesion: 0.13
Nodes (9): Names, normalize_ref(), safe_name(), ingest_statement(), list_uploads(), record_statement(), load_passwords(), resolve_ref() (+1 more)

### Community 227 - "Comms Compose Secrets (Broker MCP Tokens, Comms Google Tokens and the OAuth Client)"
Cohesion: 0.18
Nodes (11): file, file, file, file, file, secrets, calendar_broker_mcp_token, calendar_comms_token (+3 more)

### Community 233 - "Comms Hermes Auxiliary Models (Compression, Title Generation, Vision)"
Cohesion: 0.20
Nodes (10): auxiliary, compression, title_generation, vision, model, provider, model, provider (+2 more)

### Community 241 - "Comms Hermes Telegram Gateway (allowed_chats, Link Previews)"
Cohesion: 0.33
Nodes (6): allowed_chats, disable_link_previews, gateway, platforms, telegram, extra

### Community 244 - "Comms Hermes Memory Settings (memory_enabled, nudge_interval, write_approval)"
Cohesion: 0.40
Nodes (5): memory, memory_enabled, nudge_interval, user_profile_enabled, write_approval

### Community 249 - "Comms Compose Proxy Environment (HTTPS_PROXY, NO_PROXY)"
Cohesion: 0.67
Nodes (4): environment, HTTPS_PROXY, NO_PROXY, environment

### Community 251 - "Comms Hermes MCP Tool, Prompt and Resource Switches"
Cohesion: 0.67
Nodes (4): tools, tools, prompts, resources

### Community 252 - "Comms Hermes Compression Thresholds (threshold_tokens, min_tail_user_messages)"
Cohesion: 0.67
Nodes (3): compression, min_tail_user_messages, threshold_tokens

### Community 253 - "Comms Hermes Skill Guard (guard_agent_created, write_approval)"
Cohesion: 0.67
Nodes (3): skills, guard_agent_created, write_approval

### Community 254 - "Comms Hermes Tool Search Setting (tool_search)"
Cohesion: 0.67
Nodes (3): enabled, tools, tool_search

## Ambiguous Edges - Review These
- `Deploy drift at collection time (206 repo files vs 205 in /opt/personal-agent, 205 identical; runtime files that differ, not deployed yet or only on the VPS: none; 1 docs/ops/tests file not deployed or different, harmless)` → `personal-agent-control image (latest, created 2026-11-01 23:22 WIB; latest now a new image id, personal-agent-control-1 still on an earlier one)`  [AMBIGUOUS]
  docs/runtime/host.md · relation: conceptually_related_to
- `System prompts and tool-schema snapshots` → `tagihan_sekali tool (one-off bills: arrears, repairs)`  [AMBIGUOUS]
  docs/runtime/bot-activity.md · relation: conceptually_related_to
- `Turn machinery warmed (59 tool schemas materialized)` → `tagihan_sekali tool (one-off bills: arrears, repairs)`  [AMBIGUOUS]
  docs/runtime/bot-activity.md · relation: conceptually_related_to
- `pa-backup.service + timer (restic backup, daily 02:00 WIB)` → `canary.txt (root-owned file in the data dir, mode 0644)`  [AMBIGUOUS]
  docs/runtime/host.md · relation: conceptually_related_to
- `pa-gmail-token.service + timer (warns before the Gmail OAuth token expires, daily 08:00 WIB)` → `gmail-broker (brokers.gmail, the broker image's default CMD)`  [AMBIGUOUS]
  docs/runtime/infra-files.md · relation: conceptually_related_to
- `scripts/ingest-alert.py (statement-ingest failure alert to the owner)` → `BOT_CONTROL (control Telegram bot username)`  [AMBIGUOUS]
  docs/runtime/infra-files.md · relation: conceptually_related_to
- `cardguard plugin (appends the number-guard flag)` → `Full destination numbers are never in the plan`  [AMBIGUOUS]
  docs/calibration.md · relation: conceptually_related_to
- `Image cache cleanup (gateway.run_housekeeping_disk)` → `Telegram uploads cache (cache/documents 1 e-statement PDF, newest 2026-11-01; cache/images 5 images, newest 2026-11-02; cache/spillover 2 text files; counted, never read)`  [AMBIGUOUS]
  docs/runtime/bot-activity.md · relation: conceptually_related_to
- `Gateway multiplex standalone (only one profile exists, nothing to multiplex)` → `state.db hosted_room tables (14 hosted-room tables, all empty)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `/usulan (posts the waiting proposals again with their buttons)` → `Hitting a limit: catat_usulan, then sudah kucatat di /usulan`  [AMBIGUOUS]
  services/hermes/vault/SOUL.md · relation: semantically_similar_to
- `state.db (sessions, messages, model usage, delivery obligations, routing, admissions, system prompts; SQLite WAL)` → `cache/schema_columns.json (schema hash plus versions for 17 tables)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `/kondisi report command` → `Card statement recording and reconciliation (7 cards)`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `cardguard plugin (services/hermes/vault, tests run by make test)` → `num-* card payees (num-0480, num-1111, num-4365, num-5685, num-5855, num-5915, num-9706, num-9888; no card in the cards table ends in 1111)`  [AMBIGUOUS]
  docs/runtime/infra-files.md · relation: conceptually_related_to
- `compose/docker-compose.yml (Docker Compose stack)` → `services/comms-brokers/Dockerfile (one image, two containers: gmail-broker and calendar-broker)`  [AMBIGUOUS]
  docs/runtime/infra-files.md · relation: conceptually_related_to
- `ingest-gmail job (services/ingest-gmail/Dockerfile, own ingest user)` → `pdf_passwords secret`  [AMBIGUOUS]
  docs/runtime/host.md · relation: conceptually_related_to
- `vault-tools data dir (mode 0700)` → `scripts/fetch-cuti.py (cuti bersama / holidays refresh for vault-tools, run by host python3)`  [AMBIGUOUS]
  docs/runtime/timers.md · relation: conceptually_related_to
- `VAULT_TOOLS_MCP_TOKEN and VAULT_TOOLS_INTERNAL_TOKEN (vault env names)` → `cardguard plugin (services/hermes/vault/plugins/cardguard, read-only at /opt/data/plugins/cardguard)`  [AMBIGUOUS]
  docs/runtime/containers.md · relation: conceptually_related_to
- `Coway arrears expense (paid 30 Oct from the Mandiri balance; receipt on mandiri-utama, category sekali:coway-tunggakan like the 13 Oct rows)` → `Open question 4: Google One and Coway on Mega vs recorded, check on the November statements`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `Ended subscriptions (Catchplay, GoPro, AWS, Steam, PlayStation)` → `belanja_kartu (per-card statement lines, long numbers masked)`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `Ended subscriptions (Catchplay, GoPro, AWS, Steam, PlayStation)` → `Open question 7: GoPro charge on the CIMB October statement (annual, stop or move?)`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `Number guard remembers amounts from the gateway's photo description (English number format)` → `image_input_mode: native (photos go to the model as images)`  [AMBIGUOUS]
  docs/PROGRESS.md · relation: conceptually_related_to
- `make deploy (deploy-guard start, rsync to the VPS, install timers, data dirs, compose up --build, deploy-guard end)` → `personal-agent-control image (latest, created 2026-11-01 23:22 WIB; latest now a new image id, personal-agent-control-1 still on an earlier one)`  [AMBIGUOUS]
  docs/runtime/host.md · relation: conceptually_related_to
- `make deploy (deploy-guard start, rsync to the VPS, install timers, data dirs, compose up --build, deploy-guard end)` → `personal-agent-vault-tools image (latest, created 2026-11-02 01:23 WIB; latest now a new image id, personal-agent-vault-tools-1 still on the earlier one)`  [AMBIGUOUS]
  docs/runtime/host.md · relation: conceptually_related_to
- `cardguard TTL file (ttl/rincian.jsonl: /rincian messages to delete after expiry; 0 lines)` → `belanja_kartu (card spending breakdown per cycle from statement lines already read by code; never read the PDF for this)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `cache/tool_discovery_cache.json (tool discovery cache, 287 keys, written 2026-10-27)` → `Engine tools besides MCP (only clarify and vision_analyze; the row still counts 56 vault_tools tools from the latest tool-schema snapshot while the schema cache section lists 57)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `pa-ingest-alert.service (new host unit: inactive, result success, exit 0, never run, no timer)` → `ingest_checks table (146 rows)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `/ingest (read-only; filled by ingest-gmail and pa-uploads)` → `processed_messages (ledger table, 0 rows)`  [AMBIGUOUS]
  docs/runtime/vault-tools.md · relation: conceptually_related_to
- `pa-check.timer + pa-check.service (restic integrity check, 1st of month 04:00 WIB, runs backup.sh check)` → `pa-forget.timer + pa-forget.service (restic retention 7d/4w/6m, Sun 04:00 WIB, runs backup.sh forget)`  [AMBIGUOUS]
  docs/runtime/timers.md · relation: conceptually_related_to
- `Python 3.12.16 image env (GPG_KEY, LANG C.UTF-8, PYTHON_SHA256, PYTHON_VERSION; change-proposals, control, vault-tools)` → `personal-agent-ingest-gmail image (latest, created 2026-11-02 01:23 WIB)`  [AMBIGUOUS]
  docs/runtime/containers.md · relation: conceptually_related_to
- `Denied: AWS IMDSv2 credential probes to the instance-metadata address (/latest/api/token, iam/security-credentials)` → `squid-vault (vault zone egress proxy; allows api.anthropic.com, api.notion.com, api.telegram.org, gmail.googleapis.com, oauth2.googleapis.com)`  [AMBIGUOUS]
  docs/runtime/proxies.md · relation: conceptually_related_to
- `Denied: Hermes model-catalog and provider refreshes (hermes-agent.nousresearch.com, raw.githubusercontent.com, openrouter.ai, portal.nousresearch.com)` → `squid-vault (vault zone egress proxy; allows api.anthropic.com, api.notion.com, api.telegram.org, gmail.googleapis.com, oauth2.googleapis.com)`  [AMBIGUOUS]
  docs/runtime/proxies.md · relation: conceptually_related_to
- `Engine tools besides MCP (only clarify and vision_analyze; the row still counts 56 vault_tools tools from the latest tool-schema snapshot while the schema cache section lists 57)` → `tagihan_sekali (a bill paid once, outside subscriptions and fixed expenses, such as arrears or a repair; aksi picks the action, with optional alias, name, amount, due date, pay-to, method, date and note)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `ledger.db.bak-pre-card-internal (ledger copy taken before the card-internal step, with -shm and -wal sidecars, 2026-11-01)` → `num-* card payees (num-0480, num-1111, num-4365, num-5685, num-5855, num-5915, num-9706, num-9888; no card in the cards table ends in 1111)`  [AMBIGUOUS]
  docs/runtime/vault-tools.md · relation: conceptually_related_to
- `ledger.db.bak-pre-m3 (ledger copy taken before the M3 step, with -shm and -wal sidecars, 2026-11-01)` → `change_log (ledger table, 34 rows)`  [AMBIGUOUS]
  docs/runtime/vault-tools.md · relation: conceptually_related_to
- `ledger.db.bak-pre-plan-in-force (ledger copy taken before the plan-in-force step, 2026-11-02, no -shm or -wal sidecars)` → `living_* thresholds (living_balance_mark, living_balance_report, living_leftover, living_leftover_at, living_leftover_payday, living_leftover_spent, living_reserve)`  [AMBIGUOUS]
  docs/runtime/vault-tools.md · relation: conceptually_related_to
- `telegram_update_receipts JSON file in HERMES_HOME` → `Messages sent while the bot restarts are dropped (platforms.telegram.extra.drop_pending_on_cold_boot, default true)`  [AMBIGUOUS]
  docs/runtime/hermes.md · relation: conceptually_related_to
- `Closed: skip plus a direct Bot API reply writes nothing to the session store (closed by spike 11)` → `Spike 11: /rincian reply stays out of the session store (pass)`  [AMBIGUOUS]
  docs/assumptions.md · relation: conceptually_related_to
- `Closed: Telegram-side copy of the raw message (closed by spike 10, deleteMessage ok)` → `Spike 10: deleteMessage on the owner's incoming message (pass)`  [AMBIGUOUS]
  docs/assumptions.md · relation: conceptually_related_to
- `Anonymous squid log and spool volumes (8, from image VOLUME lines)` → `squid exceptions (cap_add CAP_CHOWN, CAP_DAC_OVERRIDE, CAP_SETGID, CAP_SETUID; writable rootfs; tmpfs /var/log/squid)`  [AMBIGUOUS]
  docs/runtime/containers.md · relation: conceptually_related_to
- `card_payments table (7 rows, one payment per card, last 2026-10-28 to 2026-10-30)` → `dbs-5685 card (6 statements 2026-01-25 to 2026-10-25, last due 2026-11-10; 0 marked paid; 10 instalment rows)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `cards table (7 cards; all statements reconciled, lines ok 0 per card)` → `lines_status: cocok on all 63 statements`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `owner_names table (1 row)` → `transfer_internal category (497 transactions)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to
- `pot:hutang-teman fund (friend-debt pot; 1 fund report, 2026-10-26)` → `sinking_funds table (1 row)`  [AMBIGUOUS]
  docs/runtime/state.md · relation: conceptually_related_to

## Knowledge Gaps
- **152 isolated node(s):** `AWS_DEFAULT_REGION`, `graphify-out/GRAPH_REPORT.md (where to start in the project graph)`, `Runtime files that differ from /opt/personal-agent: none`, `Runtime files not deployed yet: none`, `make runtime-map` (+147 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 1190 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **71 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `State snapshot` connect `State Snapshot: Timers, Jobs, Restic, Runs and the Pre-Deploy Ledger Backups` to `State Snapshot: the Ledger Database, Card, Statement and Instalment Tables, Card Payments, Payday Plans and Their Progress, Pots and the Usulan Items`, `Egress Proxies, Containers, Deploy History and Jobs (State)`, `Runtime Map Collector`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `create_app()` (e.g. with `report()` and `rincian()`) actually correct?**
  _`create_app()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `AWS_DEFAULT_REGION`, `graphify-out/GRAPH_REPORT.md (where to start in the project graph)`, `Runtime files that differ from /opt/personal-agent: none` to the rest of the system?**
  _152 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Runtime Map Overview: Collector, Sanitization Rules, Drift, Map Files and the Project Graphs` be split into smaller, more focused modules?**
  _Cohesion score 0.12561576354679804 - nodes in this community are weakly interconnected._
- **Why does `Bot activity snapshot` connect `Bot Activity: Tool Calls, Tool Usage, Prompt Snapshots, Sessions, Context Compression and /new Resets (state.db)` to `Runtime Map Overview: Collector, Sanitization Rules, Drift, Map Files and the Project Graphs`, `Hermes Session Store and Telegram Delivery`, `Bot Activity: Gateway Lifecycle, Shutdowns and Restarts`, `Gateway Lifecycle and Messages`, `State Snapshot: the Ledger Database, Card, Statement and Instalment Tables, Card Payments, Payday Plans and Their Progress, Pots and the Usulan Items`, `State Snapshot: Accounts, Transactions and Mutation Files, Categories, the Change Log, Debts, Balance Reports, the Usulan Table, Data Fixes and Ledger Backups`?**
  _High betweenness centrality (0.113) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Deploy drift at collection time (206 repo files vs 205 in /opt/personal-agent, 205 identical; runtime files that differ, not deployed yet or only on the VPS: none; 1 docs/ops/tests file not deployed or different, harmless)` and `personal-agent-control image (latest, created 2026-11-01 23:22 WIB; latest now a new image id, personal-agent-control-1 still on an earlier one)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `System prompts and tool-schema snapshots` and `tagihan_sekali tool (one-off bills: arrears, repairs)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._