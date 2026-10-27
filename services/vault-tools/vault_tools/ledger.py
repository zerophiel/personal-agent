"""SQLite ledger. Money columns are INTEGER Rupiah, enforced by CHECK(typeof(x)='integer')."""
from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 9   # 9: card_installments, skipped_files; 8: statements.paid_amount; 7: cards.interest_bp_month; 6: transactions.merged_into, net_snapshots; 5: debts.pay_method/pay_to_alias/debit_account_alias; 2: cards.pay_method/pay_to_alias; 3: transaction dedupe, mutation_files, category_rules; 4: sinking_funds


def _money(col: str, nullable: bool = False) -> str:
    null = f"{col} IS NULL OR " if nullable else ""
    return f"{col} INTEGER CHECK ({null}typeof({col})='integer')"


DDL = f"""
CREATE TABLE IF NOT EXISTS accounts (
  id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, bank TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('main','pool','savings')), last4 TEXT);
CREATE TABLE IF NOT EXISTS cards (
  id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, bank TEXT NOT NULL, last4 TEXT NOT NULL,
  statement_day INTEGER NOT NULL CHECK (statement_day BETWEEN 1 AND 31),
  due_day INTEGER NOT NULL CHECK (due_day BETWEEN 1 AND 31),
  {_money('credit_limit')} NOT NULL,
  pay_method TEXT NOT NULL DEFAULT 'transfer' CHECK (pay_method IN ('transfer','app_menu')),
  pay_to_alias TEXT,
  interest_bp_month INTEGER);   -- monthly interest on an unpaid balance (basis points); NULL = default
CREATE TABLE IF NOT EXISTS debts (
  id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, lender TEXT NOT NULL,
  {_money('outstanding')} NOT NULL, {_money('installment')} NOT NULL,
  tenor_left INTEGER NOT NULL, rate_bp INTEGER, due_day INTEGER NOT NULL,
  pay_method TEXT NOT NULL DEFAULT 'transfer' CHECK (pay_method IN ('transfer','autodebit')),
  pay_to_alias TEXT,            -- payee alias to transfer to (pay_method=transfer)
  debit_account_alias TEXT);    -- accounts.alias that is auto-debited (pay_method=autodebit)
CREATE TABLE IF NOT EXISTS fixed_expenses (
  id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, payee_alias TEXT NOT NULL,
  {_money('amount')} NOT NULL, due_day INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS statements (
  id INTEGER PRIMARY KEY, card_id INTEGER NOT NULL REFERENCES cards(id),
  file_hash TEXT NOT NULL UNIQUE,
  statement_date TEXT NOT NULL, due_date TEXT NOT NULL,
  {_money('previous_balance')} NOT NULL, {_money('payments')} NOT NULL,
  {_money('charges')} NOT NULL, {_money('fees')} NOT NULL,
  {_money('total_due')} NOT NULL, {_money('minimum_due')} NOT NULL,
  reconciled INTEGER NOT NULL CHECK (reconciled IN (0,1)),
  recon_diff INTEGER NOT NULL, ingested_at TEXT NOT NULL, paid_at TEXT,
  {_money('paid_amount')} NOT NULL DEFAULT 0);   -- payments the owner made against this statement (partial or full)
CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY, statement_id INTEGER REFERENCES statements(id),
  card_id INTEGER REFERENCES cards(id), account_id INTEGER REFERENCES accounts(id),
  txn_date TEXT NOT NULL, merchant TEXT NOT NULL,
  {_money('amount')} NOT NULL, category TEXT,
  status TEXT NOT NULL CHECK (status IN ('unverified','verified')),
  source TEXT NOT NULL CHECK (source IN ('statement','receipt','manual','mutation')),
  dedupe_key TEXT, file_hash TEXT,
  merged_into INTEGER);   -- a receipt later seen in a bank mutation points at that row (never counted twice)
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(txn_date);
CREATE TABLE IF NOT EXISTS mutation_files (
  file_hash TEXT PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id),
  period_start TEXT NOT NULL, period_end TEXT NOT NULL,
  {_money('opening_balance', True)}, {_money('closing_balance', True)},
  row_count INTEGER NOT NULL, new_rows INTEGER NOT NULL,
  reconciled INTEGER NOT NULL CHECK (reconciled IN (0,1)), recon_diff INTEGER NOT NULL,
  ingested_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sinking_funds (
  alias TEXT PRIMARY KEY, {_money('target')} NOT NULL CHECK (target > 0), due_date TEXT NOT NULL,
  pool_alias TEXT NOT NULL REFERENCES accounts(alias),
  pool_pay_to TEXT NOT NULL,            -- payee alias of the pool account number (contributions go here)
  creditor_pay_to TEXT,                 -- payee alias of the creditor's account (final payment)
  {_money('saved_so_far')} NOT NULL, saved_asof TEXT NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS net_snapshots (
  month TEXT PRIMARY KEY, {_money('total_debt')} NOT NULL, {_money('accounts_balance', True)},
  {_money('saved_funds')} NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ingest_checks (   -- what the PDF itself contains, to catch rows the model forgot to send
  file_hash TEXT PRIMARY KEY, dated_lines INTEGER NOT NULL, parts INTEGER NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS owner_names (name TEXT PRIMARY KEY);   -- lowercase; a transfer to one of these is the owner's own move
CREATE TABLE IF NOT EXISTS category_rules (
  pattern TEXT PRIMARY KEY, category TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS card_installments (   -- "03/12" on a card statement: payment 3 of 12
  card_id INTEGER NOT NULL REFERENCES cards(id), key TEXT NOT NULL, description TEXT NOT NULL,
  {_money('per_month')} NOT NULL CHECK (per_month > 0),
  seq INTEGER NOT NULL, total INTEGER NOT NULL CHECK (total >= 2 AND seq BETWEEN 1 AND total),
  as_of TEXT NOT NULL,                  -- statement date that printed seq/total
  PRIMARY KEY (card_id, key));
CREATE TABLE IF NOT EXISTS subscriptions (
  alias TEXT PRIMARY KEY, name TEXT NOT NULL, {_money('amount')} NOT NULL,   -- IDR per month (USD ones: approximate)
  source TEXT NOT NULL,                 -- card or account alias it is charged to
  status TEXT NOT NULL CHECK (status IN ('active','ended','unsure')), note TEXT, updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS skipped_files (   -- ingest files the owner chose not to record (out of range, duplicate, unreadable)
  file_ref TEXT PRIMARY KEY, reason TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plans (
  id INTEGER PRIMARY KEY, payday TEXT NOT NULL, snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS thresholds (
  key TEXT PRIMARY KEY, {_money('value')} NOT NULL);
CREATE TABLE IF NOT EXISTS processed_messages (
  message_id TEXT PRIMARY KEY, processed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payee_secrets (
  alias TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK (kind IN ('card','account','va')),
  bank TEXT NOT NULL, last4 TEXT NOT NULL,
  nonce BLOB NOT NULL, ciphertext BLOB NOT NULL, match_hash BLOB NOT NULL UNIQUE,
  created_at TEXT NOT NULL);
PRAGMA user_version = {SCHEMA_VERSION};
"""


def connect(path: str) -> sqlite3.Connection:
    # Handlers run on different threads; server.py serializes every access with one lock.
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if path != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(DDL)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """v1 -> v2: add the card payment columns to an existing ledger (CREATE IF NOT EXISTS skips them)."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(cards)")}
    if "pay_method" not in cols:
        conn.execute("ALTER TABLE cards ADD COLUMN pay_method TEXT NOT NULL DEFAULT 'transfer'"
                     " CHECK (pay_method IN ('transfer','app_menu'))")
    if "pay_to_alias" not in cols:
        conn.execute("ALTER TABLE cards ADD COLUMN pay_to_alias TEXT")
    scols = {r["name"] for r in conn.execute("PRAGMA table_info(statements)")}
    if "paid_amount" not in scols:          # v8
        conn.execute("ALTER TABLE statements ADD COLUMN paid_amount INTEGER NOT NULL DEFAULT 0"
                     " CHECK (typeof(paid_amount)='integer')")
    if "interest_bp_month" not in cols:     # v7
        conn.execute("ALTER TABLE cards ADD COLUMN interest_bp_month INTEGER")
    # v4 -> v5: how a debt is paid (transfer to a payee, or auto-debit from one of the owner's accounts)
    dcols = {r["name"] for r in conn.execute("PRAGMA table_info(debts)")}
    if "pay_method" not in dcols:
        conn.execute("ALTER TABLE debts ADD COLUMN pay_method TEXT NOT NULL DEFAULT 'transfer'"
                     " CHECK (pay_method IN ('transfer','autodebit'))")
    for col in ("pay_to_alias", "debit_account_alias"):
        if col not in dcols:
            conn.execute(f"ALTER TABLE debts ADD COLUMN {col} TEXT")
    # v2 -> v3: transaction dedupe + provenance (mutation_files/category_rules come from DDL)
    tcols = {r["name"] for r in conn.execute("PRAGMA table_info(transactions)")}
    for col, typ in (("dedupe_key", "TEXT"), ("file_hash", "TEXT"), ("merged_into", "INTEGER")):   # v6 adds merged_into
        if col not in tcols:
            conn.execute(f"ALTER TABLE transactions ADD COLUMN {col} {typ}")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_txn_dedupe ON transactions(dedupe_key)"
                 " WHERE dedupe_key IS NOT NULL")
    conn.commit()
