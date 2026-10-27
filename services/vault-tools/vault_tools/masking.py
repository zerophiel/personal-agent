"""Mask card/account numbers before any text reaches the model.

Masks every 13-19 digit run (spaces/dashes allowed) that passes Luhn, keeping the last 4,
plus any extra regex patterns configured for account/VA numbers.
"""
from __future__ import annotations

import re
from typing import Iterable

_CANDIDATE = re.compile(r"(?<![\d])(?:\d[ -]?){13,19}(?![\d])")


def luhn_valid(digits: str) -> bool:
    if not digits.isdigit():
        return False
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _mask_digits(raw: str) -> str:
    digits = re.sub(r"\D", "", raw)
    return f"[[NUM:****{digits[-4:]}]]"


def mask_sensitive(text: str, extra_patterns: Iterable[str] = ()) -> str:
    def repl(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and luhn_valid(digits):
            return _mask_digits(m.group(0))
        return m.group(0)

    out = _CANDIDATE.sub(repl, text)
    for pat in extra_patterns:
        out = re.sub(pat, lambda m: _mask_digits(m.group(0)), out)
    return out
