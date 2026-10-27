"""Encrypted payee numbers (full card/account/VA numbers).

ChaCha20-Poly1305 with a random nonce; the alias and kind are bound as associated data so a
ciphertext cannot be moved to another alias. A separate HKDF subkey produces an HMAC used to
match a number from a statement without decrypting anything. Never log or return plaintext
except through `reveal`, which only the deterministic /rincian path calls.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

KINDS = ("card", "account", "va")
_ALIAS = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}$")
_CVV = re.compile(r"\b(cvv|cvc|cvv2|cid)\b", re.I)
_EXPIRY = re.compile(r"\b(0[1-9]|1[0-2])\s*/\s*(\d{2}|\d{4})\b")


def _subkey(master: bytes, label: bytes) -> bytes:
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=label).derive(master)


def has_forbidden_card_data(text: str) -> bool:
    """CVV/expiry must never be stored: callers reject the message when this is True."""
    return bool(_CVV.search(text) or _EXPIRY.search(text))


def _norm(number: str) -> str:
    digits = re.sub(r"\D", "", number)
    if not 8 <= len(digits) <= 24:
        raise ValueError("number must have 8-24 digits")
    return digits


class PayeeVault:
    def __init__(self, conn: sqlite3.Connection, master_key: bytes):
        if len(master_key) != 32:
            raise ValueError("master key must be 32 bytes")
        self._conn = conn
        self._aead = ChaCha20Poly1305(_subkey(master_key, b"payee-aead-v1"))
        self._mac_key = _subkey(master_key, b"payee-match-v1")

    def _match_hash(self, digits: str) -> bytes:
        return hmac.new(self._mac_key, digits.encode(), hashlib.sha256).digest()

    @staticmethod
    def _aad(alias: str, kind: str) -> bytes:
        return f"{alias}|{kind}".encode()

    def store(self, alias: str, kind: str, bank: str, number: str) -> str:
        """Returns the display form 'alias ****last4'. Fails if alias or number already exist."""
        if kind not in KINDS:
            raise ValueError("bad kind")
        if not _ALIAS.match(alias):
            raise ValueError("alias must be lowercase letters, digits, dashes")
        digits = _norm(number)
        nonce = os.urandom(12)
        ct = self._aead.encrypt(nonce, digits.encode(), self._aad(alias, kind))
        self._conn.execute(
            "INSERT INTO payee_secrets(alias,kind,bank,last4,nonce,ciphertext,match_hash,created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (alias, kind, bank, digits[-4:], nonce, ct, self._match_hash(digits),
             datetime.now(timezone.utc).isoformat()))
        self._conn.commit()
        return f"{alias} ****{digits[-4:]}"

    def reveal(self, alias: str) -> str:
        """Plaintext number. Only for the deterministic /rincian path, never for the model."""
        row = self._conn.execute(
            "SELECT kind,nonce,ciphertext FROM payee_secrets WHERE alias=?", (alias,)).fetchone()
        if row is None:
            raise KeyError(alias)
        return self._aead.decrypt(row["nonce"], row["ciphertext"],
                                  self._aad(alias, row["kind"])).decode()

    def find_alias(self, number: str) -> str | None:
        """Match a number seen in a statement to a stored payee without decrypting."""
        row = self._conn.execute("SELECT alias FROM payee_secrets WHERE match_hash=?",
                                 (self._match_hash(_norm(number)),)).fetchone()
        return row["alias"] if row else None

    def list_display(self) -> list[str]:
        rows = self._conn.execute("SELECT alias,last4 FROM payee_secrets ORDER BY alias")
        return [f"{r['alias']} ****{r['last4']}" for r in rows]
