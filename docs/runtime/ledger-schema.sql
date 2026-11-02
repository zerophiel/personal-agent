-- Live ledger schema (sqlite_master of /data/ledger.db), user_version 14, collected 2026-11-02T11:18:01+07:00 by ops/runtime-map/collect.py.
-- Source of truth for changes: services/vault-tools/vault_tools/ledger.py (DDL + _migrate). Money columns are INTEGER Rupiah.

CREATE TABLE accounts (
  id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, bank TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('main','pool','savings')), last4 TEXT);

CREATE TABLE cards (
  id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, bank TEXT NOT NULL, last4 TEXT NOT NULL,
  statement_day INTEGER NOT NULL CHECK (statement_day BETWEEN 1 AND 31),
  due_day INTEGER NOT NULL CHECK (due_day BETWEEN 1 AND 31),
  credit_limit INTEGER CHECK (typeof(credit_limit)='integer') NOT NULL, pay_method TEXT NOT NULL DEFAULT 'transfer' CHECK (pay_method IN ('transfer','app_menu')), pay_to_alias TEXT, interest_bp_month INTEGER);

CREATE TABLE debts (
  id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, lender TEXT NOT NULL,
  outstanding INTEGER CHECK (typeof(outstanding)='integer') NOT NULL, installment INTEGER CHECK (typeof(installment)='integer') NOT NULL,
  tenor_left INTEGER NOT NULL, rate_bp INTEGER, due_day INTEGER NOT NULL, pay_method TEXT NOT NULL DEFAULT 'transfer' CHECK (pay_method IN ('transfer','autodebit')), pay_to_alias TEXT, debit_account_alias TEXT);

CREATE TABLE fixed_expenses (
  id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, payee_alias TEXT NOT NULL,
  amount INTEGER CHECK (typeof(amount)='integer') NOT NULL, due_day INTEGER NOT NULL);

CREATE TABLE statements (
  id INTEGER PRIMARY KEY, card_id INTEGER NOT NULL REFERENCES cards(id),
  file_hash TEXT NOT NULL UNIQUE,
  statement_date TEXT NOT NULL, due_date TEXT NOT NULL,
  previous_balance INTEGER CHECK (typeof(previous_balance)='integer') NOT NULL, payments INTEGER CHECK (typeof(payments)='integer') NOT NULL,
  charges INTEGER CHECK (typeof(charges)='integer') NOT NULL, fees INTEGER CHECK (typeof(fees)='integer') NOT NULL,
  total_due INTEGER CHECK (typeof(total_due)='integer') NOT NULL, minimum_due INTEGER CHECK (typeof(minimum_due)='integer') NOT NULL,
  reconciled INTEGER NOT NULL CHECK (reconciled IN (0,1)),
  recon_diff INTEGER NOT NULL, ingested_at TEXT NOT NULL, paid_at TEXT, paid_amount INTEGER NOT NULL DEFAULT 0 CHECK (typeof(paid_amount)='integer'), lines_status TEXT, lines_diff INTEGER);

CREATE TABLE transactions (
  id INTEGER PRIMARY KEY, statement_id INTEGER REFERENCES statements(id),
  card_id INTEGER REFERENCES cards(id), account_id INTEGER REFERENCES accounts(id),
  txn_date TEXT NOT NULL, merchant TEXT NOT NULL,
  amount INTEGER CHECK (typeof(amount)='integer') NOT NULL, category TEXT,
  status TEXT NOT NULL CHECK (status IN ('unverified','verified')),
  source TEXT NOT NULL CHECK (source IN ('statement','receipt','manual','mutation')), dedupe_key TEXT, file_hash TEXT, merged_into INTEGER);

CREATE TABLE plans (
  id INTEGER PRIMARY KEY, payday TEXT NOT NULL, snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE thresholds (
  key TEXT PRIMARY KEY, value INTEGER CHECK (typeof(value)='integer') NOT NULL);

CREATE TABLE processed_messages (
  message_id TEXT PRIMARY KEY, processed_at TEXT NOT NULL);

CREATE TABLE payee_secrets (
  alias TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('card','account','va')),
  bank TEXT NOT NULL, last4 TEXT NOT NULL,
  nonce BLOB NOT NULL, ciphertext BLOB NOT NULL, match_hash BLOB NOT NULL UNIQUE,
  created_at TEXT NOT NULL);

CREATE TABLE mutation_files (
  file_hash TEXT PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id),
  period_start TEXT NOT NULL, period_end TEXT NOT NULL,
  opening_balance INTEGER CHECK (opening_balance IS NULL OR typeof(opening_balance)='integer'), closing_balance INTEGER CHECK (closing_balance IS NULL OR typeof(closing_balance)='integer'),
  row_count INTEGER NOT NULL, new_rows INTEGER NOT NULL,
  reconciled INTEGER NOT NULL CHECK (reconciled IN (0,1)), recon_diff INTEGER NOT NULL,
  ingested_at TEXT NOT NULL);

CREATE TABLE sinking_funds (
  alias TEXT PRIMARY KEY, target INTEGER CHECK (typeof(target)='integer') NOT NULL CHECK (target > 0), due_date TEXT NOT NULL,
  pool_alias TEXT NOT NULL REFERENCES accounts(alias),
  pool_pay_to TEXT NOT NULL,            -- payee alias of the pool account number (contributions go here)
  creditor_pay_to TEXT,                 -- payee alias of the creditor's account (final payment)
  saved_so_far INTEGER CHECK (typeof(saved_so_far)='integer') NOT NULL, saved_asof TEXT NOT NULL, note TEXT, low_amount INTEGER, low_until TEXT, pace TEXT NOT NULL DEFAULT 'rata' CHECK (pace IN ('rata','sisa')), due_payday INTEGER NOT NULL DEFAULT 0 CHECK (due_payday IN (0,1)));

CREATE TABLE category_rules (
  pattern TEXT PRIMARY KEY, category TEXT NOT NULL);

CREATE TABLE net_snapshots (
  month TEXT PRIMARY KEY, total_debt INTEGER CHECK (typeof(total_debt)='integer') NOT NULL, accounts_balance INTEGER CHECK (accounts_balance IS NULL OR typeof(accounts_balance)='integer'),
  saved_funds INTEGER CHECK (typeof(saved_funds)='integer') NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE owner_names (name TEXT PRIMARY KEY);

CREATE TABLE ingest_checks (   -- what the PDF itself contains, to catch rows the model forgot to send
  file_hash TEXT PRIMARY KEY, dated_lines INTEGER NOT NULL, parts INTEGER NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE card_installments (   -- "03/12" on a card statement: payment 3 of 12
  card_id INTEGER NOT NULL REFERENCES cards(id), key TEXT NOT NULL, description TEXT NOT NULL,
  per_month INTEGER CHECK (typeof(per_month)='integer') NOT NULL CHECK (per_month > 0),
  seq INTEGER NOT NULL, total INTEGER NOT NULL CHECK (total >= 2 AND seq BETWEEN 1 AND total),
  as_of TEXT NOT NULL,                  -- statement date that printed seq/total
  PRIMARY KEY (card_id, key));

CREATE TABLE skipped_files (   -- ingest files the owner chose not to record (out of range, duplicate, unreadable)
  file_ref TEXT PRIMARY KEY, reason TEXT NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE subscriptions (
  alias TEXT PRIMARY KEY, name TEXT NOT NULL, amount INTEGER CHECK (typeof(amount)='integer') NOT NULL,   -- IDR per month (USD ones: approximate)
  source TEXT NOT NULL,                 -- card or account alias it is charged to
  status TEXT NOT NULL CHECK (status IN ('active','ended','unsure')), note TEXT, updated_at TEXT NOT NULL, ends TEXT, essential INTEGER NOT NULL DEFAULT 0 CHECK (essential IN (0,1)));

CREATE TABLE card_installment_scans (   -- statements already read for installments (an empty one = none printed)
  card_id INTEGER NOT NULL REFERENCES cards(id), statement_date TEXT NOT NULL, PRIMARY KEY (card_id, statement_date));

CREATE TABLE category_keywords (   -- owner's own words (a teacher's or helper's name): kept in the ledger, not in the code
  keyword TEXT PRIMARY KEY, category TEXT NOT NULL);

CREATE TABLE feature_requests (   -- what the bot could not do; the owner decides, a human builds it
  id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, title TEXT NOT NULL, detail TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'baru' CHECK (status IN ('baru','dikerjakan','selesai','ditolak')), resolution TEXT);

CREATE TABLE card_lines (   -- every transaction line of a card statement, read by code; amount > 0 = charge, < 0 = credit
  id INTEGER PRIMARY KEY, statement_id INTEGER NOT NULL REFERENCES statements(id), card_id INTEGER NOT NULL REFERENCES cards(id),
  cycle TEXT NOT NULL, txn_date TEXT, description TEXT NOT NULL, amount INTEGER CHECK (typeof(amount)='integer') NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('belanja','langganan','cicilan','bunga','biaya','pembayaran','refund')), category TEXT NOT NULL);

CREATE TABLE doc_files (hash TEXT PRIMARY KEY, path TEXT NOT NULL);

CREATE TABLE change_log (   -- rows changed or removed by hand: the row before and after, so a human can trace or undo it
  id INTEGER PRIMARY KEY, at TEXT NOT NULL, tbl TEXT NOT NULL, row_key TEXT NOT NULL,
  action TEXT NOT NULL CHECK (action IN ('baru','ubah','hapus')), before_json TEXT, after_json TEXT, reason TEXT);

CREATE TABLE balance_reports (   -- an account balance as the owner read it in the bank app (not a mutation file)
  id INTEGER PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id),
  as_of TEXT NOT NULL, at TEXT NOT NULL, balance INTEGER CHECK (typeof(balance)='integer') NOT NULL);

CREATE TABLE card_payments (   -- each payment towards a statement, dated: a plan subtracts only those made BEFORE its payday
  id INTEGER PRIMARY KEY, statement_id INTEGER NOT NULL REFERENCES statements(id), paid_on TEXT NOT NULL,
  amount INTEGER CHECK (typeof(amount)='integer') NOT NULL CHECK (amount > 0), created_at TEXT NOT NULL);

CREATE TABLE debt_payments (   -- an instalment recorded as paid (early by hand, or an auto-debit the owner reported)
  id INTEGER PRIMARY KEY, debt_alias TEXT NOT NULL, due_date TEXT NOT NULL, amount INTEGER CHECK (typeof(amount)='integer') NOT NULL,
  paid_on TEXT NOT NULL, how TEXT NOT NULL CHECK (how IN ('manual','autodebit')), created_at TEXT NOT NULL,
  UNIQUE (debt_alias, due_date));

CREATE TABLE plan_progress (   -- a transfer of a payday's plan the owner said is done (cards: card_payments)
  payday TEXT NOT NULL, item TEXT NOT NULL, amount INTEGER CHECK (typeof(amount)='integer') NOT NULL, done_on TEXT NOT NULL, created_at TEXT NOT NULL,
  PRIMARY KEY (payday, item));

CREATE TABLE fund_reports (   -- emergency fund / pot balances as the owner read them: a plan uses the last one BEFORE its payday
  id INTEGER PRIMARY KEY, fund TEXT NOT NULL, reported_on TEXT NOT NULL, balance INTEGER CHECK (typeof(balance)='integer') NOT NULL, created_at TEXT NOT NULL);

CREATE TABLE one_off_bills (   -- a bill paid once (arrears, a repair): planned by the payday it was recorded before
  id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, name TEXT NOT NULL, amount INTEGER CHECK (typeof(amount)='integer') NOT NULL CHECK (amount > 0),
  due_date TEXT NOT NULL, method TEXT NOT NULL DEFAULT 'transfer' CHECK (method IN ('transfer','app_menu')),
  pay_to_alias TEXT,                    -- payee alias of the number it is paid to (registered with /rekening or /va)
  status TEXT NOT NULL DEFAULT 'terbuka' CHECK (status IN ('terbuka','lunas','batal')), paid_on TEXT, note TEXT,
  recorded_on TEXT NOT NULL,            -- the server's day it was first recorded: which payday plans have it
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL);

CREATE INDEX idx_txn_date ON transactions(txn_date);

CREATE UNIQUE INDEX idx_txn_dedupe ON transactions(dedupe_key) WHERE dedupe_key IS NOT NULL;

CREATE INDEX idx_card_lines_cycle ON card_lines(cycle);
