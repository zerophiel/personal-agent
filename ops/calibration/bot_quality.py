"""Bot answer quality from the owner's real Telegram sessions: tool calls, tool errors, and replies that apologise or
correct themselves (each one is a calibration lead: find the root cause, fix code or SOUL with a regression test).
Run: ssh ubuntu@43.157.242.194 'sudo docker exec -i personal-agent-vault-1 python3 -' < ops/calibration/bot_quality.py
Read-only. Long digit runs are masked in the excerpts."""
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7))
mask = lambda s: re.sub(r"\d{6,}", "[angka]", s or "")  # noqa: E731
c = sqlite3.connect("file:/opt/data/state.db?mode=ro", uri=True)
c.row_factory = sqlite3.Row
tg = "SELECT id FROM sessions WHERE source='telegram'"
calls, errs = Counter(), Counter()
for r in c.execute(f"SELECT tool_calls FROM messages WHERE role='assistant' AND tool_calls IS NOT NULL AND session_id IN ({tg})"):
    try:
        for tc in json.loads(r[0]):
            calls[(tc.get("function") or {}).get("name") or tc.get("name")] += 1
    except Exception:
        pass
for r in c.execute(f"SELECT tool_name, content FROM messages WHERE role='tool' AND session_id IN ({tg})"):
    t = (r["content"] or "")[:300].lower()
    if any(k in t for k in ("error", "gagal", "traceback", "validation", "invalid")):
        errs[r["tool_name"]] += 1
print("== tool calls (telegram):", sum(calls.values()), dict(calls.most_common(30)))
print("== tool results that look like errors:", dict(errs))
pat = re.compile(r"\b(maaf|salah|keliru|koreksi|ralat|seharusnya|saya tadi)\b", re.I)
hits = []
for r in c.execute(f"SELECT session_id, timestamp, content FROM messages WHERE role='assistant' AND session_id IN ({tg}) AND content IS NOT NULL ORDER BY timestamp"):
    m = pat.search(r["content"] or "")
    if m:
        i = max(0, m.start() - 120)
        hits.append((datetime.fromtimestamp(r["timestamp"], WIB).strftime("%m-%d %H:%M"), mask(r["content"][i:i + 260]).replace("\n", " ")))
print("== assistant replies with apology/correction words:", len(hits))
for h in hits[:14]:
    print("  ", h[0], "|", h[1])
n_ass = c.execute(f"SELECT count(*) FROM messages WHERE role='assistant' AND content IS NOT NULL AND content != '' AND session_id IN ({tg})").fetchone()[0]
print("== assistant text replies (telegram):", n_ass)
