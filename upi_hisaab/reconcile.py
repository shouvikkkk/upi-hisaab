"""Reconcile: separate real spending from money that only looks spent.

Four traps from real statements, all handled here:
  1. DUPLICATES — the same payment appears in a UPI-app export and in
     the bank statement. Same 12-digit UTR + same amount = one payment.
  2. SELF-TRANSFERS — moving money between your own accounts looks like
     an outgoing payment in the feed. It is not spending.
  3. REFUNDS — a credit days later, same amount and same merchant as an
     earlier debit, is your money coming back, not new income.
  4. UPI LITE — a ₹1,000 top-up plus ten ₹100 Lite purchases is ₹1,000
     of spending, not ₹2,000. The top-up is a transfer, never spending.

A failed payment that was debited and then reversed shows up as a debit
plus a matching credit; the pair is marked "reversal" so neither counts
as spending nor income.
"""

from __future__ import annotations

from decimal import Decimal

from .models import Transaction
from .normalize import Nicknames, looks_like_self_transfer

_REFUND_WINDOW_DAYS = 30


def _same_payee(a: str, b: str) -> bool:
    a, b = (a or "").strip().lower(), (b or "").strip().lower()
    if not a or not b:
        return False
    return a == b or a in b or b in a


def dedupe(transactions: list[Transaction]) -> tuple[list[Transaction], int]:
    """Drop exact duplicates (same UTR + amount + date). Returns (kept, dropped)."""
    seen: dict[tuple[str, Decimal, str], Transaction] = {}
    kept: list[Transaction] = []
    dropped = 0
    for txn in transactions:
        if txn.utr:
            key = (txn.utr, txn.amount, txn.direction)
            if key in seen:
                dropped += 1
                seen[key].note(f"same payment also listed as '{txn.narration[:40]}'")
                continue
            seen[key] = txn
        kept.append(txn)
    return kept, dropped


def mark_self_transfers(
    transactions: list[Transaction], nicknames: Nicknames | None = None
) -> None:
    """Mark transfers to the user's own accounts (in place)."""
    for txn in transactions:
        if txn.kind == "lite_topup":
            txn.kind = "self_transfer"
            continue
        if txn.direction != "debit":
            continue
        if looks_like_self_transfer(txn.payee, txn.vpa, txn.narration) or (
            nicknames is not None
            and nicknames.is_own_account(txn.payee, txn.vpa, txn.narration)
        ):
            txn.kind = "self_transfer"
            txn.note("transfer to your own account — not spending")


def mark_refunds_and_reversals(transactions: list[Transaction]) -> None:
    """Match credits back to earlier debits (in place).

    A credit is a refund when it matches an earlier debit on amount and
    (same UTR, or same payee within 30 days). A debit+credit pair with the
    same UTR is a failed payment that was reversed.
    """
    debits = [t for t in transactions if t.direction == "debit"]
    for credit in [t for t in transactions if t.direction == "credit"]:
        match: Transaction | None = None
        for debit in debits:
            if debit.amount != credit.amount:
                continue
            if credit.utr and debit.utr and credit.utr == debit.utr:
                match = debit
                break
            if (
                _same_payee(credit.payee, debit.payee)
                and 0 <= (credit.date - debit.date).days <= _REFUND_WINDOW_DAYS
            ):
                match = debit
                break
        if match is None:
            continue
        if credit.utr and match.utr and credit.utr == match.utr:
            match.kind = "reversal"
            credit.kind = "reversal"
            match.note("failed payment — debited then reversed")
            credit.note("reversal of the failed payment")
        else:
            match.kind = "refund"
            credit.kind = "refund"
            match.note("refunded — this money came back")
            credit.note(f"refund of the {match.date} payment to {match.payee or 'the same payee'}")


def mark_fees(transactions: list[Transaction]) -> None:
    """Mark bank charges (in place)."""
    for txn in transactions:
        if txn.direction != "debit":
            continue
        text = f"{txn.payee} {txn.narration}".upper()
        if any(word in text for word in ("CHARGES", "CHARGE", "FEE", "GST ON")):
            if txn.category in ("", "Bank charges"):
                txn.category = "Bank charges"
                txn.kind = "fee"


def reconcile(
    transactions: list[Transaction], nicknames: Nicknames | None = None
) -> tuple[list[Transaction], dict[str, int]]:
    """Run every reconciliation step. Returns (transactions, counts)."""
    kept, dropped = dedupe(transactions)
    mark_self_transfers(kept, nicknames)
    mark_refunds_and_reversals(kept)
    mark_fees(kept)
    # A credit that is not a refund or a reversal is money in.
    for txn in kept:
        if txn.direction == "credit" and txn.kind == "spending":
            txn.kind = "income"
    counts = {"duplicates_removed": dropped}
    for kind in ("self_transfer", "refund", "reversal", "fee", "spending", "income"):
        counts[kind] = sum(1 for t in kept if t.kind == kind)
    return kept, counts
