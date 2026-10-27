#!/usr/bin/env python3
"""LAPTOP ONLY. Mint a gmail.readonly refresh token and write it as JSON to STDOUT (pipe it
straight to the VPS; nothing secret is printed to the terminal or stored locally).

Usage: gmail-auth.py client_secret.json | ssh vps '... cat > .../gmail_ingest_token'
Needs: pip install google-auth-oauthlib
"""
import json
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]  # read-only, nothing else


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: gmail-auth.py client_secret.json", file=sys.stderr)
        return 2
    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES)
    # access_type=offline + prompt=consent guarantees a refresh token is returned
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent",
                                  authorization_prompt_message="Buka browser untuk menyetujui akses baca Gmail...",
                                  success_message="Selesai. Boleh menutup tab ini.")
    if not creds.refresh_token:
        print("Tidak ada refresh token diterima; ulangi (cabut akses lama dulu).", file=sys.stderr)
        return 1
    if set(creds.scopes or []) != set(SCOPES):
        print("Scope tidak sesuai, dibatalkan.", file=sys.stderr)
        return 1
    json.dump({"refresh_token": creds.refresh_token, "scopes": list(creds.scopes),
               "token_uri": creds.token_uri}, sys.stdout)
    print("Token dibuat dan dikirim ke stdout.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
