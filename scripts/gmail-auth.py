#!/usr/bin/env python3
"""LAPTOP ONLY. Mint a gmail.readonly refresh token and write it as JSON to STDOUT (pipe it
straight to the VPS; nothing secret is printed to the terminal or stored locally).

Usage: run by scripts/gmail-renew.sh, which pipes it to the VPS and replaces the old token only
once the new one is complete. Refuses a terminal as stdout (the token would be printed).
Needs: pip install google-auth-oauthlib
"""
import contextlib
import datetime
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]  # read-only, nothing else


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: gmail-auth.py client_secret.json", file=sys.stderr)
        return 2
    if sys.stdout.isatty():
        print("Jangan dijalankan langsung (token akan tercetak di layar). Pakai: bash scripts/gmail-renew.sh",
              file=sys.stderr)
        return 2
    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    # The library print()s its prompt to STDOUT, which is piped into the token file on the VPS.
    # Send everything it prints to stderr so only the JSON below reaches stdout.
    with contextlib.redirect_stdout(sys.stderr):
        # access_type=offline + prompt=consent guarantees a refresh token is returned.
        # open_browser=False: WSL cannot launch a browser; open the printed URL yourself.
        creds = flow.run_local_server(
            port=0, open_browser=False, access_type="offline", prompt="consent",
            authorization_prompt_message="\nBuka URL ini di browser Anda dan setujui akses baca Gmail:\n{url}\n",
            success_message="Selesai. Boleh menutup tab ini.")
    if not creds.refresh_token:
        print("Tidak ada refresh token diterima; ulangi (cabut akses lama dulu).", file=sys.stderr)
        return 1
    if set(creds.scopes or []) != set(SCOPES):
        print("Scope tidak sesuai, dibatalkan.", file=sys.stderr)
        return 1
    # issued_at lets the VPS warn before a Testing-mode token (7-day lifetime) expires
    json.dump({"refresh_token": creds.refresh_token, "scopes": list(creds.scopes),
               "token_uri": creds.token_uri,
               "issued_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}, sys.stdout)
    print("Token dibuat dan dikirim ke stdout.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
