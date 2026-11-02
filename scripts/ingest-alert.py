#!/usr/bin/env python3
"""Host job, started by pa-ingest.service's OnFailure: tell the owner via the control bot that the statement ingest
failed, and why when the failed run wrote an error event. Stdlib only. Reads only the type, time and reason of the
events (they hold no email content); never prints the bot token. --dry-run prints the message instead of sending it."""
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

EVENTS_FILE = os.environ.get("INGEST_EVENTS_FILE", "/opt/personal-agent-data/ingest/_events.jsonl")
BOT_TOKEN_FILE = "/opt/personal-agent-secrets/telegram_control_token"
UNIT = "pa-ingest.service"
FALLBACK_WINDOW = 6 * 3600   # without a start time from systemd: a run's events are minutes old, the last run a day

# most urgent first
REASONS = {
    "token_expired": ("Google menolak token Gmail, jadi statement baru tidak terambil. Jalankan bash "
                      "scripts/gmail-renew.sh di laptop (docs/GMAIL_OAUTH.md bagian 4)."),
    "label_not_found": ('Label Gmail "Keuangan/Kartu Kredit" tidak ditemukan, jadi tidak ada statement yang diambil. '
                        "Buat lagi label itu (docs/GMAIL_OAUTH.md bagian 5)."),
    "gmail_error": ("Gmail sedang bermasalah. Email yang gagal diambil dicoba lagi besok jam 06:00; kalau besok pesan "
                    "ini tidak muncul lagi, tidak perlu tindakan."),
}
UNKNOWN = ("Penyebabnya tidak tercatat di event ingest (misalnya Docker, image, file token, atau gangguan Gmail saat "
           "membaca label). Perlu dicek di VPS: journalctl -u pa-ingest.")
SAFE_REASON = re.compile(r"[a-z_:]{1,40}")


def run_started(unit: str = UNIT) -> int | None:
    """Start of the unit's last run (unix seconds) as systemd reports it; None when it does not say."""
    try:
        out = subprocess.run(["systemctl", "show", unit, "-p", "ExecMainStartTimestamp", "--timestamp=unix", "--value"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.fullmatch(r"@(\d+)", out)
    return int(m.group(1)) if m and int(m.group(1)) > 0 else None


def reasons_since(lines, since: int) -> list[str]:
    """Reasons of the error events written at or after `since`, each once; other and malformed lines are skipped."""
    out = []
    for line in lines:
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if not isinstance(ev, dict) or ev.get("type") != "error" or not isinstance(ev.get("ts"), int):
            continue
        r = ev.get("reason")
        if ev["ts"] >= since and isinstance(r, str) and r not in out:
            out.append(r)
    return out


def message(reasons: list[str]) -> str:
    known = [REASONS[r] for r in REASONS if r in reasons]
    other = [f"Penyebab tercatat: {r}. Perlu dicek di VPS: journalctl -u pa-ingest."
             for r in reasons if r not in REASONS and SAFE_REASON.fullmatch(r)]
    return "\n".join(["Ingest statement Gmail barusan gagal."] + (known + other or [UNKNOWN]))


def notify(text: str) -> None:
    print(text)
    try:
        tok = open(BOT_TOKEN_FILE).read().strip()
        data = urllib.parse.urlencode({"chat_id": os.environ["MY_TELEGRAM_ID"], "text": text}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data, timeout=20)
    except Exception:  # noqa: BLE001 - never print the token-bearing URL
        print("notify failed")


def main(argv: list[str]) -> int:
    since = run_started()
    if since is None:
        since = int(time.time()) - FALLBACK_WINDOW
    try:
        with open(EVENTS_FILE, encoding="utf-8", errors="replace") as f:
            reasons = reasons_since(f, since)
    except OSError:
        reasons = []
    text = message(reasons)
    if "--dry-run" in argv:
        print(text)
    else:
        notify(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
