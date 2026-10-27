"""Sender and authentication checks for incoming statement emails (pure functions)."""
from __future__ import annotations

import re
from email.utils import parseaddr

TRUSTED_AUTHSERV = "mx.google.com"   # only the receiving server's verdict counts
_SAFE = re.compile(r"[^a-z0-9@._+-]")


def safe_label(value: str, limit: int = 80) -> str:
    """Untrusted strings are reduced to a harmless charset before they go into events."""
    return _SAFE.sub("?", value.lower())[:limit]


def from_address(headers: dict[str, list[str]]) -> tuple[str, str]:
    """(address, domain) from the From header; ('', '') if missing or ambiguous."""
    values = headers.get("from", [])
    if len(values) != 1:        # several From headers = spoofing trick
        return "", ""
    addr = parseaddr(values[0])[1].lower()
    if addr.count("@") != 1:
        return "", ""
    return addr, addr.split("@")[1]


def _clauses(value: str) -> list[str]:
    return [c.strip() for c in value.split(";")[1:]]


def auth_ok(headers: dict[str, list[str]], from_domain: str) -> tuple[bool, str]:
    """Require, in an Authentication-Results header written by mx.google.com: dkim=pass AND
    dmarc=pass whose header.from equals the From domain. Headers from any other authserv-id
    (e.g. ones a sender injected) are ignored. Returns (ok, short reason)."""
    seen_trusted = False
    for value in headers.get("authentication-results", []):
        authserv = value.split(";", 1)[0].strip().split(" ")[0].lower()
        if authserv != TRUSTED_AUTHSERV:
            continue
        seen_trusted = True
        clauses = _clauses(value)
        dkim = any(re.match(r"dkim=pass\b", c) for c in clauses)
        dmarc_domains = [m.group(1).lower() for c in clauses if re.match(r"dmarc=pass\b", c)
                         for m in [re.search(r"header\.from=([A-Za-z0-9.\-]+)", c)] if m]
        if dkim and from_domain in dmarc_domains:
            return True, "ok"
    return False, "no_trusted_pass" if seen_trusted else "no_trusted_header"
