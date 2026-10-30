"""Rows changed or removed by hand (a corrected expense, an updated subscription): the whole row before and after, the
reason in the owner's words, and when. Written in the caller's transaction, so the change and its record land together;
a deleted row survives only here."""
from __future__ import annotations

import json
from datetime import datetime, timezone


def log(conn, table: str, key, action: str, before: dict | None, after: dict | None, reason: str | None = None) -> None:
    conn.execute("INSERT INTO change_log(at,tbl,row_key,action,before_json,after_json,reason) VALUES (?,?,?,?,?,?,?)",
                 (datetime.now(timezone.utc).isoformat(), table, str(key), action,
                  None if before is None else json.dumps(before, ensure_ascii=False),
                  None if after is None else json.dumps(after, ensure_ascii=False), reason or None))
