"""SQLite ledger. Money columns are INTEGER Rupiah, enforced by CHECK(typeof(x)='integer')."""
from __future__ import annotations

import sqlite3

SCHEMA_VERSION = 1


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
  {_money('credit_limit')} NOT NULL);
CREATE TABLE IF NOT EXISTS debts (
  id INTEGER PRIMARY KEY, alias TEXT NOT NULL UNIQUE, lender TEXT NOT NULL,
  {_money('outstanding')} NOT NULL, {_money('installment')} NOT NULL,
  tenor_left INTEGER NOT NULL, rate_bp INTEGER, due_day INTEGER NOT NULL);
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
  recon_diff INTEGER NOT NULL, ingested_at TEXT NOT NULL, paid_at TEXT);
CREATE TABLE IF NOT EXISTS transactions (
  id INTEGER PRIMARY KEY, statement_id INTEGER REFERENCES statements(id),
  card_id INTEGER REFERENCES cards(id), account_id INTEGER REFERENCES accounts(id),
  txn_date TEXT NOT NULL, merchant TEXT NOT NULL,
  {_money('amount')} NOT NULL, category TEXT,
  status TEXT NOT NULL CHECK (status IN ('unverified','verified')),
  source TEXT NOT NULL CHECK (source IN ('statement','receipt','manual','mutation')));
CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(txn_date);
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
    return conn
