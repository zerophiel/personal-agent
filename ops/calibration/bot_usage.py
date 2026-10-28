"""Bot cost and usage per WIB day and source (telegram = the owner, oneshot = calibration tests), priced at list rates.
Hermes reports cost_status=unknown for claude-sonnet-5-5, so this is the only spend view besides the Console limit.
Run: ssh ubuntu@43.157.242.194 'sudo docker exec -i personal-agent-vault-1 python3 -' < ops/calibration/bot_usage.py
Read-only (state.db opened with mode=ro). Prints token counts only, never message text."""
import sqlite3
from datetime import datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7))
c = sqlite3.connect("file:/opt/data/state.db?mode=ro", uri=True)
c.row_factory = sqlite3.Row
SON = {"5m": (2.0, 10.0, 0.20, 2.50), "1h": (2.0, 10.0, 0.20, 4.0)}


def cost(r, ttl):
    p = SON[ttl]
    return ((r["i"] or 0) * p[0] + (r["o"] or 0) * p[1] + (r["cr"] or 0) * p[2] + (r["cw"] or 0) * p[3]) / 1e6


day = {}
for r in c.execute("SELECT s.source, u.first_seen f, u.api_call_count calls, u.input_tokens i, u.output_tokens o, u.cache_read_tokens cr,"
                   " u.cache_write_tokens cw FROM session_model_usage u JOIN sessions s ON s.id = u.session_id"):
    d = datetime.fromtimestamp(r["f"], WIB).strftime("%Y-%m-%d")
    k = (d, r["source"])
    a = day.setdefault(k, {"calls": 0, "c5": 0.0, "c1": 0.0, "cw": 0, "cr": 0, "o": 0, "sessions": 0})
    a["calls"] += r["calls"] or 0
    a["c5"] += cost(r, "5m")
    a["c1"] += cost(r, "1h")
    a["cw"] += r["cw"] or 0
    a["cr"] += r["cr"] or 0
    a["o"] += r["o"] or 0
    a["sessions"] += 1
print("== per WIB day and source: sessions, API calls, cache write/read, output, cost if TTL 5m / 1h")
for k in sorted(day):
    a = day[k]
    print(f"  {k[0]} {k[1]:10s} sess {a['sessions']:3d} calls {a['calls']:4d} cw {a['cw']:>10,} cr {a['cr']:>11,} out {a['o']:>8,}  ${a['c5']:6.2f} / ${a['c1']:6.2f}")
print("== owner messages per WIB day")
n = {}
for r in c.execute("SELECT timestamp FROM messages WHERE role='user'"):
    d = datetime.fromtimestamp(r[0], WIB).strftime("%Y-%m-%d")
    n[d] = n.get(d, 0) + 1
print("  ", n)
print("== system prompt sizes (chars) of recent sessions")
for r in c.execute("SELECT s.id, length(s.system_prompt) L, s.tool_names FROM sessions s ORDER BY s.started_at DESC LIMIT 3"):
    print("  ", r["L"], "tools:", len((r["tool_names"] or "").split(",")))
print("== one-call sessions (prefix written fresh):", [ (r["cw"]) for r in c.execute("SELECT cache_write_tokens cw FROM session_model_usage WHERE api_call_count=1")])
