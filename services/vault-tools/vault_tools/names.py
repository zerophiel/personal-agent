"""File names from uploads are untrusted: reduce them to a harmless charset for anything the
model sees, and match the safe form back to the real file when it is read."""
import re

HERMES_DOC_CACHE = "/opt/data/cache/documents/"   # where Hermes stores Telegram documents
UPLOAD_PREFIX = "telegram/"
_UNSAFE = re.compile(r"[^A-Za-z0-9._ -]")


def safe_name(name: str, limit: int = 120) -> str:
    return _UNSAFE.sub("?", name)[:limit]


def normalize_ref(file_ref: str) -> str:
    """Accept the path Hermes shows (/opt/data/cache/documents/x) as `telegram/x`."""
    if file_ref.startswith(HERMES_DOC_CACHE):
        return UPLOAD_PREFIX + file_ref[len(HERMES_DOC_CACHE):]
    return file_ref
