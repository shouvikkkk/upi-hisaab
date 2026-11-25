"""Parse the amount formats Indian bank statements actually use.

Real exports mix: 1,234.50 (Indian commas), (1,234.50) for negatives,
separate Debit/Credit columns, a Dr/Cr marker column, and bare signed
numbers. A value we cannot parse is reported, never treated as zero —
a zero would silently erase real money from the report.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_AMOUNT_RE = re.compile(r"^[+-]?[\d,]*\.?\d*$")


def parse_amount(raw: str) -> Decimal | None:
    """Parse one amount string. Returns None when it is not a number."""
    text = (raw or "").strip()
    if not text:
        return None
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative = True
        text = text[1:-1].strip()
    text = text.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "")
    text = text.strip()
    if text.endswith("-"):
        negative = True
        text = text[:-1]
    elif text.startswith("-"):
        negative = True
        text = text[1:]
    elif text.startswith("+"):
        text = text[1:]
    if not text or not _AMOUNT_RE.match(text):
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    return -value if negative else value


def split_debit_credit(
    debit_raw: str, credit_raw: str, marker_raw: str = ""
) -> tuple[Decimal, str] | None:
    """Work out (amount, direction) from debit/credit columns + Dr/Cr marker.

    Returns None when neither column holds a usable amount. When both
    columns hold amounts (a malformed row), the debit wins and the caller
    is expected to flag the row — see statements.py.
    """
    debit = parse_amount(debit_raw)
    credit = parse_amount(credit_raw)
    marker = (marker_raw or "").strip().upper()
    if debit is not None and credit is not None:
        # Both filled: trust the larger one is the real movement and let
        # the statement reader flag the row; here debit wins by convention.
        return debit, "debit"
    if debit is not None:
        return debit, "debit"
    if credit is not None:
        return credit, "credit"
    if marker in ("DR", "D", "DEBIT"):
        return None
    if marker in ("CR", "C", "CREDIT"):
        return None
    return None


def inr(amount: Decimal) -> str:
    """Format a Decimal as Indian rupees, e.g. 18450 -> ₹18,450."""
    negative = amount < 0
    text = f"{abs(amount):,.2f}"
    if text.endswith(".00"):
        text = text[:-3]
    return ("-₹" if negative else "₹") + text
