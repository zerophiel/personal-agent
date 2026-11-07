"""Monthly refresh of non-working days (cuti bersama + national holidays) from public sources.

Stdlib only: runs on the host (systemd timer), outside the vault zone. Sources are untrusted
data: we only extract ISO dates, keep weekdays of the target year, sanity-check counts, and cap
how much may change per run. Anything outside those limits is reported, never applied.
"""
from __future__ import annotations

import json
import re
from datetime import date

GITHUB_JSON = "https://raw.githubusercontent.com/guangrei/APIHariLibur_V2/main/calendar.json"
GOOGLE_ICS = ("https://calendar.google.com/calendar/ical/"
              "id.indonesian%23holiday%40group.v.calendar.google.com/public/basic.ics")
MAX_CHANGE = 6          # |added| + |removed| above this is not auto-applied
MIN_DAYS, MAX_DAYS = 8, 40


def parse_github(text: str, year: int) -> set[date]:
    """Days flagged holiday=True (national holidays and cuti bersama) in the dataset."""
    out = set()
    for key, val in json.loads(text).items():
        try:
            d = date.fromisoformat(key)
        except ValueError:
            continue
        if d.year == year and isinstance(val, dict) and val.get("holiday") is True:
            out.add(d)
    return out


def parse_ics_cuti(text: str, year: int) -> set[date]:
    """Events whose summary contains 'Cuti Bersama' in the Google public holiday calendar."""
    text = text.replace("\r\n ", "").replace("\r\n", "\n")
    out = set()
    for ev in text.split("BEGIN:VEVENT")[1:]:
        d = re.search(r"DTSTART(?:;VALUE=DATE)?:(\d{8})", ev)
        s = re.search(r"SUMMARY:(.*)", ev)
        if d and s and "cuti bersama" in s.group(1).lower():
            try:
                day = date(int(d.group(1)[:4]), int(d.group(1)[4:6]), int(d.group(1)[6:8]))
            except ValueError:
                continue
            if day.year == year:
                out.add(day)
    return out


def candidate_days(github_text: str, ics_text: str, year: int) -> set[date]:
    days = parse_github(github_text, year) | parse_ics_cuti(ics_text, year)
    return {d for d in days if d.weekday() < 5}  # weekends are non-working anyway


def decide(current: set[date], candidate: set[date]) -> tuple[str, set[date], set[date]]:
    """Return (action, added, removed). action: 'none' | 'apply' | 'review' | 'reject'."""
    if not MIN_DAYS <= len(candidate) <= MAX_DAYS:
        return "reject", set(), set()
    added, removed = candidate - current, current - candidate
    if not added and not removed:
        return "none", set(), set()
    if not current:  # first baseline for this year
        return "apply", added, removed
    if len(added) + len(removed) > MAX_CHANGE:
        return "review", added, removed
    return "apply", added, removed


def merge_file(existing: dict, year: int, days: set[date], source_note: str) -> dict:
    out = {k: v for k, v in existing.items() if k != "_source"}
    out[str(year)] = sorted(d.isoformat() for d in days)
    out["_source"] = source_note
    return out


def load_year(data: dict, year: int) -> set[date]:
    return {date.fromisoformat(d) for d in data.get(str(year), [])}


def render_diff(year: int, added: set[date], removed: set[date]) -> str:
    fmt = lambda s: ", ".join(d.isoformat() for d in sorted(s)) or "-"  # noqa: E731
    return f"Libur/cuti bersama {year}: tambah [{fmt(added)}]; hapus [{fmt(removed)}]"
