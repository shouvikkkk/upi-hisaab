"""Categorise transactions into plain-word spending categories.

Order of evidence, strongest first:
  1. the user's nickname file (they know "Ramesh Kumar" is the milkman)
  2. the known-merchant dictionary (Swiggy, Netflix, IRCTC, ...)
  3. keyword rules on the payee/narration (milk, auto, recharge, ...)
  4. nothing matched -> category stays "" and the report says so honestly.

A category is never invented. "Uncategorised" is a real answer: it tells
the user exactly how much money they still cannot account for.
"""

from __future__ import annotations

from .merchants import lookup_keyword, lookup_merchant
from .models import Transaction
from .normalize import Nicknames


def categorise(txn: Transaction, nicknames: Nicknames | None = None) -> Transaction:
    """Fill in txn.category (and a friendlier payee) in place. Returns txn."""
    if nicknames is not None:
        hit = nicknames.lookup(txn.payee, txn.vpa)
        if hit is not None:
            label, category = hit
            txn.payee = label
            if category:
                txn.category = category
                return txn
    merchant = lookup_merchant(txn.payee)
    if merchant is not None:
        name, category = merchant
        txn.payee = name
        txn.category = category
        return txn
    keyword = lookup_keyword(txn.payee, txn.narration)
    if keyword is not None:
        txn.category = keyword
        return txn
    txn.category = ""
    return txn


def categorise_all(
    transactions: list[Transaction], nicknames: Nicknames | None = None
) -> list[Transaction]:
    return [categorise(txn, nicknames) for txn in transactions]
