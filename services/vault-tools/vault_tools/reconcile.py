"""Deterministic statement reconciliation. The LLM extracts numbers; this checks them."""
from __future__ import annotations

from dataclasses import dataclass

from .money import check_idr


@dataclass(frozen=True)
class Reconciliation:
    ok: bool
    expected_total: int
    diff: int  # stated_total - expected_total; 0 when ok


def reconcile(previous_balance: int, payments: int, charges: int, fees: int,
              stated_total: int) -> Reconciliation:
    """previous balance - payments + charges + fees (incl. interest) must equal the stated total.

    Amounts are positive magnitudes as printed on the statement. A mismatch is reported,
    never auto-corrected: the caller flags it to the owner.
    """
    for v in (previous_balance, payments, charges, fees, stated_total):
        check_idr(v)
    expected = previous_balance - payments + charges + fees
    diff = stated_total - expected
    return Reconciliation(diff == 0, expected, diff)
