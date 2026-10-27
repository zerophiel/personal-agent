"""vault-tools server: one process, two separately-authenticated surfaces.

/mcp          model-facing (bearer MCP token). Tools only read/write aliases and amounts.
              There is deliberately NO tool that stores or reveals a full number.
/internal/*   plugin-facing (bearer INTERNAL token): store_payee, rincian. The model never
              holds this token.
"""
from __future__ import annotations

import functools
import hmac
import json
import os
import sys
import threading
from datetime import date

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse

from . import tools
from .ledger import connect
from .money import format_idr
from .payee_vault import PayeeVault, has_forbidden_card_data
from .payday import last_working_day

MCP_TOOL_NAMES = ("upsert_card", "upsert_debt", "upsert_expense", "set_threshold",
                  "generate_payday_plan", "list_payees", "next_payday")


_LOCK = threading.RLock()


def locked(fn):
    """Serialize ledger access: one SQLite connection is shared across handler threads."""
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        with _LOCK:
            return fn(*a, **kw)
    return wrapper


class _Auth:
    """Pure ASGI middleware: path prefix -> bearer token, constant-time compare."""

    def __init__(self, app, rules: dict[str, str]):
        self.app, self.rules = app, rules

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope["path"]
            token = next((t for p, t in self.rules.items() if path.startswith(p)), None)
            if token is None:  # unknown path: deny, no information
                return await PlainTextResponse("not found", 404)(scope, receive, send)
            sent = dict(scope["headers"]).get(b"authorization", b"").decode()
            if not hmac.compare_digest(sent, f"Bearer {token}"):
                return await PlainTextResponse("unauthorized", 401)(scope, receive, send)
        await self.app(scope, receive, send)


def create_app(db_path: str, master_key: bytes, mcp_token: str, internal_token: str,
               allowed_hosts: list[str] | None = None, today=date.today):
    if len(mcp_token) < 32 or len(internal_token) < 32 or mcp_token == internal_token:
        raise ValueError("tokens must be >= 32 chars and different")
    conn = connect(db_path)
    vault = PayeeVault(conn, master_key)
    hosts = allowed_hosts or ["vault-tools:8000", "vault-tools"]
    mcp = FastMCP("vault-tools", stateless_http=True, json_response=True,
                  transport_security=TransportSecuritySettings(
                      enable_dns_rebinding_protection=True, allowed_hosts=hosts))

    @mcp.tool()
    @locked
    def upsert_card(alias: str, bank: str, last4: str, statement_day: int, due_day: int,
                    credit_limit: int) -> str:
        """Simpan/ubah kartu kredit (alias + 4 digit terakhir; nomor lengkap tidak lewat sini)."""
        return tools.upsert_card(conn, alias, bank, last4, statement_day, due_day, credit_limit)

    @mcp.tool()
    @locked
    def upsert_debt(alias: str, lender: str, outstanding: int, installment: int,
                    tenor_left: int, due_day: int, rate_bp: int | None = None) -> str:
        """Simpan/ubah utang. Semua uang dalam Rupiah bulat."""
        return tools.upsert_debt(conn, alias, lender, outstanding, installment, tenor_left,
                                 due_day, rate_bp)

    @mcp.tool()
    @locked
    def upsert_expense(alias: str, payee_alias: str, amount: int, due_day: int) -> str:
        """Simpan/ubah pengeluaran tetap bulanan (mis. uang sekolah)."""
        return tools.upsert_expense(conn, alias, payee_alias, amount, due_day)

    @mcp.tool()
    @locked
    def set_threshold(key: str, value: int) -> str:
        """Set ambang/angka tetap, mis. net_salary, cash_buffer, dsr_max_bp."""
        return tools.set_threshold(conn, key, value)

    @mcp.tool()
    @locked
    def generate_payday_plan(payday: str | None = None) -> str:
        """Hitung rencana gajian (deterministik). payday opsional, format YYYY-MM-DD."""
        snap = tools.generate_payday_plan(conn, today(), date.fromisoformat(payday) if payday else None)
        return tools.summarize_plan(snap)

    @mcp.tool()
    @locked
    def list_payees() -> list[str]:
        """Daftar penerima tersimpan sebagai 'alias ****last4'."""
        return vault.list_display()

    @mcp.tool()
    @locked
    def next_payday() -> str:
        """Tanggal gajian berikutnya (hari kerja terakhir bulan, WIB)."""
        t = today()
        hol = tools.id_holidays(t.year) | tools.id_holidays(t.year + 1)
        p = last_working_day(t.year, t.month, hol)
        return (p if p >= t else tools.next_payday(p, hol)).isoformat()

    app = mcp.streamable_http_app()

    async def store_payee(request: Request):
        body = await request.json()
        if has_forbidden_card_data(json.dumps(body.get("raw_text", ""))):
            return JSONResponse({"ok": False, "error": "cvv_or_expiry_rejected"}, status_code=422)
        try:
            with _LOCK:
                shown = vault.store(body["alias"], body["kind"], body["bank"], body["number"])
        except Exception as e:  # never echo the number back
            return JSONResponse({"ok": False, "error": type(e).__name__}, status_code=422)
        return JSONResponse({"ok": True, "display": shown})

    async def rincian(request: Request):
        with _LOCK:
            row = conn.execute("SELECT snapshot_json FROM plans ORDER BY id DESC LIMIT 1").fetchone()
            if row is None:
                return PlainTextResponse("Belum ada rencana gajian.")
            snap, lines = json.loads(row["snapshot_json"]), []
            for t in snap["transfers"]:
                try:
                    num = vault.reveal(t["to_alias"])
                except KeyError:
                    num = "(nomor belum disimpan)"
                lines.append(f"{t['date']} {t['to_alias']}\n  {format_idr(t['amount'])}\n  `{num}`")
        return PlainTextResponse("\n\n".join(lines) or "Tidak ada transfer.")

    app.add_route("/internal/store_payee", store_payee, methods=["POST"])
    app.add_route("/internal/rincian", rincian, methods=["POST"])
    app.add_middleware(_Auth, rules={"/mcp": mcp_token, "/internal/": internal_token})
    app.state.mcp = mcp
    return app


def main() -> None:
    import base64

    import uvicorn

    def read(name: str) -> str:
        with open(os.path.join(os.environ.get("SECRETS_DIR", "/run/secrets"), name)) as f:
            return f.read().strip()

    key = base64.b64decode(read("vault_tools_key"))
    app = create_app(os.environ.get("LEDGER_DB", "/data/ledger.db"), key,
                     read("vault_tools_mcp_token"), read("vault_tools_internal_token"))
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    sys.exit(main())
