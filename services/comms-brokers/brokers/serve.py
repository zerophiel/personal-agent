"""The MCP side both brokers share, as change-proposals does it: only /mcp, only with the broker's own bearer token,
on port 8000 of net-comms. The secrets come from /run/secrets (compose file secrets, root-owned on the VPS)."""
import hmac
import os

from starlette.responses import PlainTextResponse


class Auth:
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


def secured(mcp, token: str):
    app = mcp.streamable_http_app()
    app.add_middleware(Auth, token=token)
    app.state.mcp = mcp
    return app


def secret(name: str) -> str:
    with open(os.path.join(os.environ.get("SECRETS_DIR", "/run/secrets"), name), encoding="utf-8") as f:
        return f.read().strip()


def run(app) -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")   # no access log: paths and errors only
