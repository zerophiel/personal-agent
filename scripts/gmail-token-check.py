#!/usr/bin/env python3
"""Daily host job: warn via the control bot before the Gmail token (Testing mode, 7-day
lifetime) expires. Stdlib only. Silent when the token is fresh. Never prints the token."""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", "/opt/personal-agent-secrets/gmail_ingest_token")
BOT_TOKEN_FILE = "/opt/personal-agent-secrets/telegram_control_token"
LIFETIME_DAYS = 7
WARN_AT_DAYS = 5   # start warning with 2 days left


def days_left(issued_at: str, now: datetime) -> float:
    return LIFETIME_DAYS - (now - datetime.fromisoformat(issued_at)).total_seconds() / 86400


def message(left: float) -> str | None:
    if left <= 0:
        return ("Token Gmail SUDAH kedaluwarsa. Ingest statement berhenti. Jalankan scripts/gmail-auth.py "
                "di laptop (lihat docs/GMAIL_OAUTH.md).")
    if left <= LIFETIME_DAYS - WARN_AT_DAYS:
        return (f"Token Gmail habis dalam {left:.1f} hari. Perbarui dengan scripts/gmail-auth.py "
                "di laptop (satu menit) supaya ingest statement tidak berhenti.")
    return None


def notify(text: str) -> None:
    print(text)
    try:
        tok = open(BOT_TOKEN_FILE).read().strip()
        data = urllib.parse.urlencode({"chat_id": os.environ["MY_TELEGRAM_ID"], "text": text}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data, timeout=20)
    except Exception:  # noqa: BLE001 - never print the token-bearing URL
        print("notify failed")


def main() -> int:
    try:
        with open(TOKEN_FILE) as f:
            issued = json.load(f)["issued_at"]
    except FileNotFoundError:
        notify("Token Gmail belum dibuat. Ikuti docs/GMAIL_OAUTH.md.")
        return 1
    except (ValueError, KeyError):
        notify("File token Gmail rusak atau tanpa tanggal terbit. Buat ulang dengan scripts/gmail-auth.py.")
        return 1
    msg = message(days_left(issued, datetime.now(timezone.utc)))
    if msg:
        notify(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
