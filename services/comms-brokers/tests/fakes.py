"""Fakes for the broker tests: Google's token endpoint, Gmail and Calendar as the brokers reach them over HTTP, in
memory, every API request recorded as (method, path under the API, query, body). Card-like numbers and addresses are
built at run time, so no such value is written out in the tests."""
import base64
import copy
import json
import os
import re
import sys
from datetime import datetime, timezone
from urllib.parse import parse_qs, unquote, urlsplit

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from brokers import gcal, gmail  # noqa: E402
from brokers.common import TOKEN_URL, GoogleSession  # noqa: E402

CLIENT = {"installed": {"client_id": "cid", "client_secret": "csecret"}}
BANK = "bank.example"
WHEN_MS = str(int(datetime(2026, 11, 2, 9, 30, tzinfo=timezone.utc).timestamp()) * 1000)     # 16:30 WIB
GMAIL_POLICY = {"hidden_labels": ["Keuangan"], "hidden_sender_domains": [BANK], "label_prefix": "Comms",
                "categories": ["Penting", "Perlu-Dibalas", "Info"]}


def addr(user: str, domain: str = "example.com") -> str:
    return f"{user}@{domain}"


CAL_POLICY = {"calendars": {"utama": "primary", "keluarga": addr("keluarga", "group.calendar.example")}, "max_days": 31}


def luhn_ok(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch) * (2 if i % 2 else 1)
        total += d - 9 if d > 9 else d
    return total % 10 == 0


def card(body: str = "4" + "1" * 14) -> str:
    """A made-up 16-digit number that passes the Luhn check."""
    return next(body + str(d) for d in range(10) if luhn_ok(body + str(d)))


def b64(text: str, charset: str = "utf-8") -> str:
    return base64.urlsafe_b64encode(text.encode(charset)).decode().rstrip("=")


def message(mid, frm, subject="Halo", labels=("INBOX", "UNREAD"), thread=None, text="Isi email", html=None,
            headers=(), attachments=(), msgid=None):
    """A Gmail message resource as format=full returns it."""
    hs = [{"name": "From", "value": frm}, {"name": "Subject", "value": subject},
          {"name": "Message-ID", "value": f"<{mid}.mail>" if msgid is None else msgid}]
    hs += [{"name": n, "value": v} for n, v in headers]
    parts = []
    if text is not None:
        parts.append({"mimeType": "text/plain", "body": {"data": b64(text)},
                      "headers": [{"name": "Content-Type", "value": 'text/plain; charset="utf-8"'}]})
    if html is not None:
        parts.append({"mimeType": "text/html", "body": {"data": b64(html)}})
    for name in attachments:
        parts.append({"mimeType": "application/pdf", "filename": name, "body": {"attachmentId": f"att{mid}", "size": 10}})
    return {"id": mid, "threadId": thread or mid, "labelIds": list(labels), "internalDate": WHEN_MS,
            "snippet": f"Cuplikan &amp; {subject}", "payload": {"mimeType": "multipart/mixed", "headers": hs,
                                                                "parts": parts}}


class FakeGoogle:
    """The token endpoint, granting exactly `scope`; a subclass answers the API's own calls in route()."""

    def __init__(self, api: str, scope: str):
        self.prefix, self.scope, self.token_error, self.requests = urlsplit(api).path, scope, False, []

    def __call__(self, method, url, data, headers):
        if url == TOKEN_URL:
            if self.token_error:
                return 400, b'{"error": "invalid_grant"}'
            return 200, json.dumps({"access_token": "at", "expires_in": 3600, "scope": self.scope}).encode()
        assert headers["Authorization"] == "Bearer at"
        parts = urlsplit(url)
        path = unquote(parts.path)
        assert path.startswith(self.prefix), path
        path, params, body = path[len(self.prefix):], parse_qs(parts.query), json.loads(data) if data else None
        self.requests.append((method, path, params, body))
        status, out = self.route(method, path, params, body)
        return status, json.dumps(out).encode()

    def calls(self, method: str, pattern: str = ".*") -> list:
        return [r for r in self.requests if r[0] == method and re.fullmatch(pattern, r[1])]


class FakeGmail(FakeGoogle):
    """Gmail with the given messages, the system labels, the finance labels and any a test adds."""

    def __init__(self, messages, labels=()):
        super().__init__(gmail.API, gmail.SCOPES[0])
        self.messages = {m["id"]: m for m in messages}
        self.labels = [{"id": "INBOX", "name": "INBOX", "type": "system"},
                       {"id": "UNREAD", "name": "UNREAD", "type": "system"},
                       {"id": "Label_K", "name": "Keuangan", "type": "user"},
                       {"id": "Label_KK", "name": "Keuangan/Kartu Kredit", "type": "user"}, *labels]
        self.drafts, self.after_metadata = [], None

    @staticmethod
    def meta(msg, names):
        wanted = {n.lower() for n in names}
        out = copy.deepcopy(msg)
        out["payload"] = {"headers": [h for h in msg["payload"]["headers"] if h["name"].lower() in wanted]}
        return out

    def route(self, method, path, params, body):
        if path == "labels":
            if method == "GET":
                return 200, {"labels": self.labels}
            label = {"id": f"Label_{len(self.labels)}", "name": body["name"], "type": "user"}
            self.labels.append(label)
            return 200, label
        if (method, path) == ("GET", "messages"):
            ids = list(self.messages)[: int(params["maxResults"][0])]
            return 200, {"messages": [{"id": i, "threadId": self.messages[i]["threadId"]} for i in ids]}
        if (method, path) == ("POST", "drafts"):
            self.drafts.append(body)
            return 200, {"id": f"r{len(self.drafts)}", "message": {"id": "d1", "threadId": body["message"]["threadId"]}}
        kind, _, rest = path.partition("/")
        if (method, kind) == ("GET", "threads"):
            found = [self.meta(m, params.get("metadataHeaders", [])) for m in self.messages.values()
                     if m["threadId"] == rest]
            return (200, {"id": rest, "messages": found}) if found else (404, {})
        mid, _, action = rest.partition("/")
        msg = self.messages.get(mid)
        if kind != "messages" or msg is None:
            return 404, {}
        if (method, action) == ("POST", "modify"):
            keep = [x for x in msg["labelIds"] if x not in body["removeLabelIds"]]
            msg["labelIds"] = keep + [x for x in body["addLabelIds"] if x not in keep]
            return 200, {"id": mid, "labelIds": msg["labelIds"]}
        if (method, action) == ("GET", ""):
            if params["format"] == ["metadata"]:
                out = self.meta(msg, params.get("metadataHeaders", []))
                if self.after_metadata:
                    self.after_metadata(mid)
                return 200, out
            return 200, copy.deepcopy(msg)
        raise AssertionError(f"unexpected Gmail call {method} {path}")


class FakeCalendar(FakeGoogle):
    def __init__(self, items=(), more=False):
        super().__init__(gcal.API, gcal.SCOPES[0])
        self.items, self.more = list(items), more

    def route(self, method, path, params, body):
        if method == "GET" and re.fullmatch(r"calendars/[^/]+/events", path):
            return 200, {"items": self.items, **({"nextPageToken": "p2"} if self.more else {})}
        raise AssertionError(f"unexpected Calendar call {method} {path}")


def gmail_broker(messages, labels=(), clock=lambda: 1000.0):
    fake = FakeGmail(messages, labels)
    session = GoogleSession(CLIENT, {"refresh_token": "rt", "scopes": list(gmail.SCOPES)}, gmail.SCOPES, http=fake,
                            clock=clock)
    return fake, gmail.Broker(gmail.Gmail(session), gmail.Policy(GMAIL_POLICY), clock=clock)


def calendar_broker(items=(), more=False):
    fake = FakeCalendar(items, more)
    session = GoogleSession(CLIENT, {"refresh_token": "rt", "scopes": list(gcal.SCOPES)}, gcal.SCOPES, http=fake)
    policy = gcal.Policy(CAL_POLICY)
    return fake, gcal.Broker(gcal.Calendar(session, policy), policy)
