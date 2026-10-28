"""Daily snapshot of the finance picture into the owner's Notion (`Agent > Finance`). No LLM involved.

Everything written comes from the ledger through deterministic code: aliases, bank names and amounts only; never a full
card or account number. The page text is rendered here, not by a model, so a prompt injection cannot reach Notion.
Run: python -m vault_tools.notion_sync   (token in /run/secrets/notion_token, page ids in /data/notion.json)."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import date

from . import card_installments, roadmap, subscriptions, tools
from .ledger import connect
from .money import format_idr

API = "https://api.notion.com/v1"
VERSION = "2022-06-28"
MAX_BLOCKS = 100          # Notion accepts at most 100 children per append
PAUSE = 0.35              # Notion allows about 3 requests a second


class NotionError(Exception):
    pass


def _urllib_http(method: str, url: str, data: bytes | None, headers: dict) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:           # honours HTTPS_PROXY (squid-vault allowlist)
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class Notion:
    def __init__(self, token: str, http=_urllib_http, sleep=time.sleep):
        self._token, self._http, self._sleep = token, http, sleep

    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        headers = {"Authorization": f"Bearer {self._token}", "Notion-Version": VERSION, "Content-Type": "application/json"}
        data = json.dumps(body).encode() if body is not None else None
        for attempt in range(4):
            status, raw = self._http(method, f"{API}/{path}", data, headers)
            if status == 429 and attempt < 3:        # rate limited: wait and retry
                self._sleep(2 * (attempt + 1))
                continue
            if status != 200:
                raise NotionError(f"{method} {path.split('/')[0]} -> {status}")   # never echo the response or the token
            self._sleep(PAUSE)
            return json.loads(raw) if raw else {}
        raise NotionError("rate limited")

    def children(self, block_id: str) -> list[dict]:
        out, cursor = [], None
        while True:
            q = f"blocks/{block_id}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            page = self._call("GET", q)
            out += page.get("results", [])
            cursor = page.get("next_cursor")
            if not page.get("has_more") or not cursor:
                return out

    def replace_content(self, page_id: str, blocks: list[dict]) -> None:
        """Append the new blocks first, then archive the old ones, so a failure never leaves an empty page."""
        old = [b["id"] for b in self.children(page_id) if b.get("type") != "child_page"]
        for i in range(0, len(blocks), MAX_BLOCKS):
            self._call("PATCH", f"blocks/{page_id}/children", {"children": blocks[i:i + MAX_BLOCKS]})
        for bid in old:
            self._call("DELETE", f"blocks/{bid}")

    def set_title(self, page_id: str, title: str) -> None:
        self._call("PATCH", f"pages/{page_id}", {"properties": {"title": {"title": [{"type": "text", "text": {"content": title}}]}}})

    def create_page(self, parent_id: str, title: str) -> str:
        return self._call("POST", "pages", {"parent": {"page_id": parent_id},
                                             "properties": {"title": {"title": [{"type": "text", "text": {"content": title}}]}}})["id"]


# ---- block builders -----------------------------------------------------------------------

def _rt(text: str) -> list[dict]:
    return [{"type": "text", "text": {"content": str(text)[:1900]}}]


def heading(text: str) -> dict:
    return {"object": "block", "type": "heading_2", "heading_2": {"rich_text": _rt(text)}}


def para(text: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rt(text)}}


def bullet(text: str) -> dict:
    return {"object": "block", "type": "bulleted_list_item", "bulleted_list_item": {"rich_text": _rt(text)}}


def table(header: list[str], rows: list[list[str]]) -> dict:
    def row(cells):
        return {"object": "block", "type": "table_row", "table_row": {"cells": [_rt(c) for c in cells]}}
    return {"object": "block", "type": "table", "table": {
        "table_width": len(header), "has_column_header": True, "has_row_header": False,
        "children": [row(header)] + [row(r) for r in rows[:90]]}}


# ---- page renderers (ledger -> blocks) ------------------------------------------------------

def _stamp(today: date) -> dict:
    return para(f"Disinkronkan otomatis dari ledger pada {today.isoformat()}. Nomor kartu dan rekening tidak pernah ditulis di sini.")


def render_plan(conn, today: date) -> tuple[str, list[dict]]:
    snap = tools.generate_payday_plan(conn, today)
    blocks = [_stamp(today), para(f"Gaji {format_idr(snap['salary'])}. Cadangan kas harian {format_idr(snap['reserve'])} ({snap.get('reserve_source')}).")]
    if snap.get("reserve_source", "").startswith("sementara"):
        blocks.append(para("Catatan: cadangan sementara hanya bagian yang diambil dari gaji; uang tunai harian sebenarnya termasuk saldo yang sudah dipegang."))
    rows = [[t["date"], t["to_alias"], format_idr(t["amount"]),
             t["reason"] + {"autodebit": f"; autodebet, saldo cukup sebelum {t.get('due')}", "app_menu": "; lewat menu aplikasi"}.get(t.get("method"), "")]
            for t in snap["transfers"]]
    blocks += [heading("Pembayaran"), table(["Tanggal", "Tujuan", "Jumlah", "Keterangan"], rows)]
    if snap["unfunded"]:
        blocks += [heading("Belum terdanai"),
                   table(["Tujuan", "Jumlah", "Estimasi biaya"], [[u["to_alias"], format_idr(u["amount"]), format_idr(u["est_delay_cost"])] for u in snap["unfunded"]])]
    if snap.get("reminders"):
        blocks += [heading("Pengingat")] + [bullet(r) for r in snap["reminders"]]
    if snap.get("advice"):
        blocks += [heading("Saran")] + [bullet(a) for a in snap["advice"]]
    blocks += [para(f"Kas ditahan {format_idr(snap['cash_to_hold'])}.")] + [para(f"Peringatan: {w}") for w in snap["warnings"]]
    return f"Rencana gajian {snap['payday']}", blocks


def render_cards(conn, today: date) -> tuple[str, list[dict]]:
    rows, total = [], 0
    for r in conn.execute(
            "SELECT k.alias, k.credit_limit, s.statement_date, s.due_date, s.total_due - s.paid_amount AS owed, MAX(0, s.minimum_due - s.paid_amount) AS minimum"
            " FROM cards k JOIN statements s ON s.card_id = k.id WHERE s.id = (SELECT id FROM statements WHERE card_id = k.id"
            " ORDER BY statement_date DESC, id DESC LIMIT 1) ORDER BY s.due_date"):
        total += max(0, r["owed"])
        rows.append([r["alias"], format_idr(r["credit_limit"]), r["statement_date"], r["due_date"], format_idr(max(0, r["owed"])), format_idr(r["minimum"])])
    blocks = [_stamp(today), table(["Kartu", "Limit", "Cetak", "Jatuh tempo", "Sisa", "Minimum"], rows),
              para(f"Total sisa tagihan terbuka: {format_idr(total)}.")]
    return "Tagihan kartu", blocks


def render_installments(conn, today: date) -> tuple[str, list[dict]]:
    inst = card_installments.active(conn)
    blocks = [_stamp(today), heading("Cicilan kartu"),
              table(["Kartu", "Cicilan", "Ke", "Per bulan", "Sisa bulan", "Selesai"],
                    [[a["card"], a["description"], f"{a['seq']}/{a['total']}", format_idr(a["per_month"]), str(a["left"]), a["ends"][:7]] for a in inst])
              if inst else para("Tidak ada cicilan kartu aktif."),
              para(f"Total cicilan kartu {format_idr(card_installments.monthly_total(conn))} per bulan; sisa {format_idr(sum(a['remaining'] for a in inst))}."),
              heading("Langganan")]
    rows = [[r["name"], r["source"], format_idr(r["amount"]), {"active": "aktif", "ended": "berhenti", "unsure": "belum pasti"}[r["status"]], r["note"] or ""]
            for r in conn.execute("SELECT * FROM subscriptions ORDER BY status, name")]
    blocks += [table(["Layanan", "Kartu", "Per bulan", "Status", "Catatan"], rows) if rows else para("Belum ada langganan tercatat."),
               para(f"Total langganan aktif {format_idr(subscriptions.active_total(conn))} per bulan.")]
    return "Cicilan kartu dan langganan", blocks


def render_roadmap(conn, today: date) -> tuple[str, list[dict]]:
    lines = roadmap.format_roadmap(roadmap.roadmap(conn, today)).splitlines()
    blocks = [_stamp(today)]
    for line in lines:
        blocks.append(bullet(line[2:]) if line.startswith("- ") else heading(line.rstrip(":")) if line.endswith(":") else para(line))
    return "Peta jalan bebas utang", blocks


def render_budgets(conn, today: date) -> tuple[str, list[dict]]:
    brows = [[r["key"][7:], format_idr(r["value"])] for r in conn.execute("SELECT key, value FROM thresholds WHERE key LIKE 'budget:%' ORDER BY key")]
    frows = [[r["alias"], format_idr(r["amount"]), f"tanggal {r['due_day']}"] for r in conn.execute("SELECT alias, amount, due_day FROM fixed_expenses ORDER BY alias")]
    reserve = tools.get_threshold(conn, "living_reserve")
    blocks = [_stamp(today), para(f"Cadangan kas harian: {format_idr(reserve) if reserve else 'belum diset'}. Anggaran 'kartu:' hanya menghitung belanja yang dibayar kartu."),
              heading("Anggaran per bulan"), table(["Kategori", "Batas"], brows) if brows else para("Belum ada anggaran."),
              heading("Pengeluaran tetap"), table(["Pos", "Per bulan", "Jatuh tempo"], frows) if frows else para("Belum ada.")]
    return "Anggaran dan batas", blocks


PAGES = (("Rencana gajian", render_plan), ("Tagihan kartu", render_cards), ("Cicilan kartu dan langganan", render_installments),
         ("Peta jalan bebas utang", render_roadmap), ("Anggaran dan batas", render_budgets))


def sync(conn, notion: Notion, finance_page_id: str, today: date) -> list[str]:
    existing = {b["child_page"]["title"]: b["id"] for b in notion.children(finance_page_id) if b.get("type") == "child_page"}
    done = []
    for prefix, render in PAGES:
        title, blocks = render(conn, today)
        page_id = next((pid for t, pid in existing.items() if t.startswith(prefix)), None)
        if page_id is None:
            page_id = notion.create_page(finance_page_id, title)
        elif next(t for t, pid in existing.items() if pid == page_id) != title:
            notion.set_title(page_id, title)
        notion.replace_content(page_id, blocks)
        done.append(title)
    return done


def main() -> int:
    secrets = os.environ.get("SECRETS_DIR", "/run/secrets")
    data = os.environ.get("DATA_DIR", "/data")
    try:
        token = open(os.path.join(secrets, "notion_token")).read().strip()
        cfg = json.load(open(os.path.join(data, "notion.json")))
        conn = connect(os.path.join(data, "ledger.db"))
        done = sync(conn, Notion(token), cfg["finance_page_id"], tools.wib_today())
    except (OSError, KeyError, ValueError, NotionError) as e:
        print(f"notion-sync gagal: {type(e).__name__}: {e}"[:200])      # no token, no response body
        return 1
    print(f"notion-sync: {len(done)} halaman diperbarui: {', '.join(done)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
