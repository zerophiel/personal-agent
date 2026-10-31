"""change-proposals (M3): the front agent's one way to ask for a change. It applies nothing and reads nothing back.

One MCP tool, submit, on net-front behind a bearer token. A proposal that passes control's own rules (validate, imported
from services/control/control.py so the two never drift) is written as one JSON file into the inbox folder; control, on
net-ctl and with no LLM, takes it from there, checks it again and posts it to the owner with one-time Setujui/Tolak
buttons. This container mounts the inbox and nothing else: no decision, no state, no secret but its own token.
"""
from __future__ import annotations

import hmac
import json
import os
import secrets
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import BaseModel, Field
from starlette.responses import PlainTextResponse

from control import MAX_FILE_CHARS, MAX_FILES, MAX_INBOX_BYTES, PATHS, TEXT_LIMITS, validate

MAX_WAITING = 5         # files still in the inbox (control holds at most five more as pending)
MAX_PER_DAY = 10        # submissions per rolling 24 hours: a looping model cannot flood the owner


class ProposedFile(BaseModel):
    path: str = Field(description="path relatif di repo, mis. services/hermes/front/skills/cuaca/SKILL.md")
    content: str = Field(max_length=MAX_FILE_CHARS, description="isi LENGKAP file sesudah perubahan, bukan diff")


class _Auth:
    """Pure ASGI middleware: only /mcp, only with the bearer token (constant-time compare)."""

    def __init__(self, app, token: str):
        self.app, self.token = app, token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            if not scope["path"].startswith("/mcp"):
                return await PlainTextResponse("not found", 404)(scope, receive, send)
            sent = dict(scope["headers"]).get(b"authorization", b"").decode()
            if not hmac.compare_digest(sent, f"Bearer {self.token}"):
                return await PlainTextResponse("unauthorized", 401)(scope, receive, send)
        await self.app(scope, receive, send)


def create_app(inbox: str, token: str, allowed_hosts: list[str] | None = None, clock=time.time):
    if len(token) < 32:
        raise ValueError("token must be >= 32 chars")
    folder = Path(inbox)
    sent_at: list[float] = []
    lock = threading.Lock()
    paths = "; ".join(f"{k}: {', '.join(v) or 'tanpa file'}" for k, v in PATHS.items())
    mcp = FastMCP("change-proposals", stateless_http=True, json_response=True,
                  transport_security=TransportSecuritySettings(
                      enable_dns_rebinding_protection=True,
                      allowed_hosts=allowed_hosts or ["change-proposals:8000", "change-proposals"]))

    @mcp.tool(description=(
        "Kirim usulan perubahan ke pemilik. Pemilik memutuskan lewat tombol di control bot; tidak ada yang berubah sebelum "
        "disetujui DAN diterapkan, dan kamu tidak bisa melihat keputusannya. Satu usulan = satu perubahan yang utuh. "
        f"Batas teks: summary {TEXT_LIMITS['summary']}, permission_diff {TEXT_LIMITS['permission_diff']}, risk_notes "
        f"{TEXT_LIMITS['risk_notes']}, rollback {TEXT_LIMITS['rollback']} karakter; paling banyak {MAX_FILES} file. "
        f"File yang boleh diubah per change_type ({{zone}} = zona): {paths}. Layanan baru, skrip host, plugin dan nilai "
        "rahasia tidak lewat sini: tulis eskalasi untuk pemilik."))
    def submit(
        summary: Annotated[str, Field(description="apa yang diubah dan mengapa, untuk pemilik (bahasa Indonesia)")],
        zone: Annotated[Literal["front", "comms", "vault"], Field(description="zona yang berubah")],
        change_type: Annotated[Literal["skill", "mcp", "tool", "toolset", "egress_domain", "schedule", "config",
                                       "credential"], Field(description="jenis perubahan; menentukan file yang boleh")],
        permission_diff: Annotated[str, Field(description="izin/akses yang bertambah atau berkurang; 'tidak ada' bila tidak ada")],
        risk_notes: Annotated[str, Field(description="risikonya, terus terang")],
        rollback: Annotated[str, Field(description="cara membatalkannya")],
        files: Annotated[list[ProposedFile] | None, Field(description="file yang diubah, isi lengkap; kosong untuk credential")] = None,
    ) -> str:
        raw = {"summary": summary, "zone": zone, "change_type": change_type, "permission_diff": permission_diff,
               "risk_notes": risk_notes, "rollback": rollback, "files": [f.model_dump() for f in files or []]}
        try:
            body = validate(raw)
        except ValueError as e:
            return f"Usulan TIDAK dikirim: {e}. Perbaiki lalu kirim lagi."
        data = json.dumps(body, ensure_ascii=False).encode()
        if len(data) > MAX_INBOX_BYTES:
            return f"Usulan TIDAK dikirim: lebih dari {MAX_INBOX_BYTES:,} byte. Pecah jadi usulan yang lebih kecil.".replace(",", ".")
        with lock:
            now = clock()
            sent_at[:] = [t for t in sent_at if now - t < 86_400]
            if len(sent_at) >= MAX_PER_DAY:
                return f"Usulan TIDAK dikirim: sudah {MAX_PER_DAY} usulan dalam 24 jam. Tunggu keputusan pemilik."
            if len(list(folder.glob("*.json"))) >= MAX_WAITING:
                return "Usulan TIDAK dikirim: masih ada usulan yang belum diambil control. Tunggu keputusan pemilik."
            name = f"{datetime.fromtimestamp(now, timezone.utc):%Y%m%dT%H%M%SZ}-{secrets.token_hex(4)}.json"
            tmp = folder / f"{name}.tmp"         # control only reads *.json: the rename makes it whole at once
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as f:
                f.write(data)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, folder / name)
            sent_at.append(now)
        return ("Usulan terkirim ke pemilik (control bot, tombol Setujui/Tolak). BELUM ada yang berubah: jangan bilang "
                "perubahan sudah berlaku; bila pemilik bertanya, katakan menunggu keputusannya di control bot.")

    app = mcp.streamable_http_app()
    app.add_middleware(_Auth, token=token)
    app.state.mcp = mcp
    return app


def main() -> None:
    import uvicorn

    with open(os.path.join(os.environ.get("SECRETS_DIR", "/run/secrets"), "change_proposals_mcp_token")) as f:
        token = f.read().strip()
    app = create_app(os.environ.get("PROPOSALS_INBOX_DIR", "/inbox"), token)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    sys.exit(main())
