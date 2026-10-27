"""Minimal Gmail REST client (gmail.readonly) on urllib. `http` is injectable for tests."""
from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://gmail.googleapis.com/gmail/v1/users/me"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class GmailError(Exception):
    pass


class TokenError(GmailError):
    """Refresh token rejected (expired/revoked). The owner must re-run scripts/gmail-auth.py."""


def _urllib_http(method: str, url: str, data: bytes | None, headers: dict) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data, headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


class GmailClient:
    def __init__(self, client_json: dict, token_json: dict, http=_urllib_http, clock=time.time):
        c = client_json.get("installed") or client_json.get("web") or {}
        self._id, self._secret = c["client_id"], c["client_secret"]
        self._refresh = token_json["refresh_token"]
        self._http, self._clock = http, clock
        self._access, self._exp = None, 0.0

    def _access_token(self) -> str:
        if self._access and self._clock() < self._exp - 60:
            return self._access
        body = urllib.parse.urlencode({"client_id": self._id, "client_secret": self._secret,
                                       "refresh_token": self._refresh,
                                       "grant_type": "refresh_token"}).encode()
        status, raw = self._http("POST", TOKEN_URL, body,
                                 {"Content-Type": "application/x-www-form-urlencoded"})
        try:
            data = json.loads(raw)
        except ValueError:
            raise GmailError("token endpoint returned non-JSON") from None
        if status == 400 and data.get("error") == "invalid_grant":
            raise TokenError("invalid_grant")
        if status != 200 or "access_token" not in data:
            raise GmailError(f"token refresh failed ({status})")
        self._access, self._exp = data["access_token"], self._clock() + int(data.get("expires_in", 3600))
        return self._access

    def _get(self, path: str, params: dict | None = None) -> dict:
        url = f"{API}/{path}" + (f"?{urllib.parse.urlencode(params, doseq=True)}" if params else "")
        status, raw = self._http("GET", url, None, {"Authorization": f"Bearer {self._access_token()}"})
        if status != 200:
            raise GmailError(f"GET {path.split('/')[0]} -> {status}")
        return json.loads(raw)

    def label_id(self, name: str) -> str | None:
        for lab in self._get("labels").get("labels", []):
            if lab.get("name") == name:
                return lab["id"]
        return None

    def list_message_ids(self, label_id: str, limit: int = 200) -> list[str]:
        ids, token = [], None
        while len(ids) < limit:
            params = {"labelIds": label_id, "maxResults": 100}
            if token:
                params["pageToken"] = token
            page = self._get("messages", params)
            ids += [m["id"] for m in page.get("messages", [])]
            token = page.get("nextPageToken")
            if not token:
                break
        return ids[:limit]

    def get_message(self, message_id: str) -> dict:
        return self._get(f"messages/{message_id}", {"format": "full"})

    def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        data = self._get(f"messages/{message_id}/attachments/{attachment_id}")["data"]
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))
