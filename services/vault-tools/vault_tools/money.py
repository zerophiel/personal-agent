"""Money helpers. All amounts are integer Rupiah; floats are rejected."""
from __future__ import annotations


def check_idr(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"IDR amount must be int, got {type(value).__name__}")
    return value


def format_idr(value: int) -> str:
    """1234567 -> 'Rp 1.234.567' (negative: '-Rp 1.234')."""
    check_idr(value)
    sign = "-" if value < 0 else ""
    return f"{sign}Rp {abs(value):,}".replace(",", ".")


def bp_of(amount: int, basis_points: int) -> int:
    """Integer share of `amount` in basis points (1 bp = 0.01%), rounded half up, no floats."""
    check_idr(amount)
    check_idr(basis_points)
    return (amount * basis_points + 5_000) // 10_000
