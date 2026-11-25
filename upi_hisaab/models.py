"""Core data model for upi-hisaab.

One Transaction is one line of a bank statement, after parsing. Everything
downstream (categorising, reconciling, reporting) works on these objects,
never on raw text, so a bad line can be flagged instead of silently guessed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class Transaction:
    """A single parsed statement line."""

    date: date
    amount: Decimal  # always positive; direction says which way it moved
    direction: str  # "debit" (money left) or "credit" (money came in)
    narration: str  # raw narration exactly as the bank wrote it
    utr: str = ""  # 12-digit UPI reference, when the narration carries one
    payee: str = ""  # who was paid / who paid, as written
    vpa: str = ""  # UPI handle (name@bank), when present
    channel: str = ""  # upi / imps / neft / rtgs / pos / atm / ach / other
    category: str = ""  # filled in by categorise(); "" means unknown
    kind: str = "spending"  # spending | self_transfer | refund | reversal
    # | income | fee | duplicate | lite_topup
    notes: list[str] = field(default_factory=list)

    @property
    def signed_amount(self) -> Decimal:
        """Negative for money out, positive for money in."""
        return -self.amount if self.direction == "debit" else self.amount

    def note(self, text: str) -> None:
        if text not in self.notes:
            self.notes.append(text)
