"""Read only: is the owner chatting with the bot right now? Exits 3 when the last message is under 2 minutes old,
so a restart never cuts a reply. Prints roles, tool names and times only, never content."""
import sqlite3, sys
from datetime import datetime, timedelta, timezone

WIB = timezone(timedelta(hours=7))
db = sqlite3.connect("file:/opt/data/state.db?mode=ro", uri=True)


def when(ts):
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, WIB)
    d = datetime.fromisoformat(str(ts))
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(WIB)


now = datetime.now(WIB)
rows = db.execute("SELECT role, tool_name, timestamp FROM messages ORDER BY id DESC LIMIT 3").fetchall()
print("now WIB", now.strftime("%m-%d %H:%M:%S"))
for role, tool, ts in rows:
    print(" ", when(ts).strftime("%m-%d %H:%M:%S"), role, tool or "")
age = (now - when(rows[0][2])).total_seconds() if rows else 1e9
if age < 120:
    print(f"BOT BUSY: last message {int(age)} s ago. Wait until the bot has replied, then run the script again.")
    sys.exit(3)
print("bot idle")
