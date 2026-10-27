#!/usr/bin/env python3
"""Host timer job (monthly): refresh /data/cuti_bersama.json for vault-tools. Stdlib only.

Writes OVERRIDE_PATH (owned by the vault-tools uid), replacing the bundled list for the years
it covers. Notifies the owner through the control bot when anything changes, or when a change
is too large to apply automatically. Silent when nothing changed.
Env: DRY_RUN=1 prints only; MY_TELEGRAM_ID for notifications.
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services", "vault-tools"))
from vault_tools import cuti_fetch as cf  # noqa: E402

OVERRIDE_PATH = os.environ.get("OVERRIDE_PATH", "/opt/personal-agent-data/vault-tools/cuti_bersama.json")
BUNDLED = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "services", "vault-tools",
                       "vault_tools", "data", "cuti_bersama.json")
TOKEN_FILE = "/opt/personal-agent-secrets/telegram_control_token"
UID = 10001


def get(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as r:
        data = r.read(2_000_001)
    if len(data) > 2_000_000:
        raise ValueError("response too large")
    return data.decode("utf-8", "replace")


def notify(text: str) -> None:
    print(text)
    if os.environ.get("DRY_RUN") == "1":
        return
    try:
        tok = open(TOKEN_FILE).read().strip()
        data = urllib.parse.urlencode({"chat_id": os.environ["MY_TELEGRAM_ID"], "text": text,
                                       "disable_web_page_preview": "true"}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data, timeout=20)
    except Exception:  # noqa: BLE001 - never print the token-bearing URL
        print("notify failed")


def read_json(path: str) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def main() -> int:
    today = date.today()
    years = [today.year] + ([today.year + 1] if today.month >= 10 else [])
    try:
        gh, ics = get(cf.GITHUB_JSON), get(cf.GOOGLE_ICS)
    except Exception as e:  # noqa: BLE001
        notify(f"Gagal mengambil data cuti bersama ({type(e).__name__}); data lama tetap dipakai.")
        return 1
    override = read_json(OVERRIDE_PATH)
    bundled = read_json(BUNDLED)
    changed = False
    for year in years:
        cand = cf.candidate_days(gh, ics, year)
        if not cand and year != today.year:
            continue  # next year not published yet
        current = cf.load_year(override, year)  # baseline = last fetched list only
        action, added, removed = cf.decide(current, cand)
        if action == "none":
            continue
        if action == "reject":
            notify(f"Data cuti bersama {year} dari sumber tidak masuk akal ({len(cand)} hari); diabaikan.")
            continue
        if action == "review":
            notify(cf.render_diff(year, added, removed) + " - terlalu banyak perubahan, TIDAK diterapkan. Mohon review.")
            continue
        override = cf.merge_file(override, year, cand, f"fetched {today.isoformat()} from github+google ics")
        changed = True
        first = not current
        notify(("Baseline libur " if first else "Perubahan ") + cf.render_diff(year, added, removed)
               + " - diterapkan ke vault-tools.")
    if changed and os.environ.get("DRY_RUN") != "1":
        tmp = OVERRIDE_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(override, f, indent=1)
        os.chown(tmp, UID, UID)
        os.chmod(tmp, 0o640)
        os.replace(tmp, OVERRIDE_PATH)
    _ = bundled  # bundled stays as the offline fallback; override wins per year
    return 0


if __name__ == "__main__":
    sys.exit(main())
