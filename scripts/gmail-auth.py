#!/usr/bin/env python3
"""LAPTOP ONLY. Mint a Google refresh token for one token secret and write it as JSON to STDOUT (pipe it straight to
the VPS; nothing secret is printed to the terminal or stored locally).

Usage: run by scripts/gmail-renew.sh, which pipes it to the VPS and replaces the old token only once the new one is
complete. Refuses a terminal as stdout (the token would be printed).
  gmail-auth.py client_secret.json [token name]      (default gmail_ingest_token; the names are SCOPES' keys)
Needs: pip install google-auth-oauthlib
"""
import contextlib
import datetime
import json
import sys

# One scope per token secret, nothing else. The ingest reads statements. The comms gmail-broker labels and drafts:
# gmail.modify could send as well, so the broker's call list (services/comms-brokers) is what keeps comms from sending.
# The comms calendar-broker reads events.
SCOPES = {
    "gmail_ingest_token": ["https://www.googleapis.com/auth/gmail.readonly"],
    "gmail_comms_token": ["https://www.googleapis.com/auth/gmail.modify"],
    "calendar_comms_token": ["https://www.googleapis.com/auth/calendar.events.readonly"],
}
ASK = {   # what the owner is asked to approve in the browser
    "gmail_ingest_token": "setujui akses baca Gmail",
    "gmail_comms_token": "setujui akses Gmail untuk comms (baca, label, draf; comms tidak bisa mengirim)",
    "calendar_comms_token": "setujui akses baca Kalender untuk comms",
}


def main() -> int:
    name = sys.argv[2] if len(sys.argv) == 3 else "gmail_ingest_token"
    if len(sys.argv) not in (2, 3) or name not in SCOPES:
        print(f"usage: gmail-auth.py client_secret.json [{'|'.join(SCOPES)}]", file=sys.stderr)
        return 2
    if sys.stdout.isatty():
        print("Jangan dijalankan langsung (token akan tercetak di layar). Pakai: bash scripts/gmail-renew.sh",
              file=sys.stderr)
        return 2
    from google_auth_oauthlib.flow import InstalledAppFlow   # here: the table above loads without the library

    flow = InstalledAppFlow.from_client_secrets_file(sys.argv[1], SCOPES[name])
    # The library print()s its prompt to STDOUT, which is piped into the token file on the VPS.
    # Send everything it prints to stderr so only the JSON below reaches stdout.
    with contextlib.redirect_stdout(sys.stderr):
        # access_type=offline + prompt=consent guarantees a refresh token is returned.
        # open_browser=False: WSL cannot launch a browser; open the printed URL yourself.
        creds = flow.run_local_server(
            port=0, open_browser=False, access_type="offline", prompt="consent",
            authorization_prompt_message=f"\nBuka URL ini di browser Anda dan {ASK[name]}:\n{{url}}\n",
            success_message="Selesai. Boleh menutup tab ini.")
    if not creds.refresh_token:
        print("Tidak ada refresh token diterima; ulangi (cabut akses lama dulu).", file=sys.stderr)
        return 1
    if set(creds.scopes or []) != set(SCOPES[name]):
        print("Scope tidak sesuai, dibatalkan.", file=sys.stderr)
        return 1
    # issued_at lets the VPS warn before a Testing-mode token (7-day lifetime) expires; client_id lets gmail-renew.sh
    # refuse a token minted with another OAuth client than the one the VPS refreshes it with
    json.dump({"refresh_token": creds.refresh_token, "scopes": list(creds.scopes),
               "token_uri": creds.token_uri, "client_id": creds.client_id,
               "issued_at": datetime.datetime.now(datetime.timezone.utc).isoformat()}, sys.stdout)
    print("Token dibuat dan dikirim ke stdout.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
