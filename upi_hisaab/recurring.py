"""Find recurring payments — the subscriptions you forgot you pay for.

A payment is recurring when the same payee is charged again and again:
  * monthly — 3 or more charges, 25–35 days apart, amounts within 30%
    of each other (a price hike does not break the pattern)
  * annual — 2 or more charges about a year apart (350–380 days)
  * possible annual — one single charge from a known subscription
    merchant (Netflix, Spotify, ...) inside the window: worth checking,
    not proof

Irregular repeats (the milkman every day, the same shop twice a week)
are NOT recurring — they are frequent, not scheduled. Only a steady
cadence counts, because only a steady cadence is a subscription.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .merchants import SUBSCRIPTION_MERCHANTS
from .models import Transaction

_MONTHLY_MIN_GAP = 25
_MONTHLY_MAX_GAP = 35
_ANNUAL_MIN_GAP = 350
_ANNUAL_MAX_GAP = 380
# A price hike must not break the pattern: Netflix went 199 -> 249 (+25%).
_AMOUNT_TOLERANCE = Decimal("0.30")


@dataclass
class Recurring:
    payee: str
    category: str
    cadence: str  # "monthly" | "annual" | "possible annual"
    amount: Decimal  # typical charge
    count: int
    first: date
    last: date
    next_expected: date | None
    yearly_cost: Decimal

    @property
    def monthly_cost(self) -> Decimal:
        if self.cadence == "monthly":
            return self.amount
        if self.cadence == "annual":
            return (self.yearly_cost / 12).quantize(Decimal("1"))
        return Decimal("0")


def _typical_amount(amounts: list[Decimal]) -> Decimal:
    ordered = sorted(amounts)
    return ordered[len(ordered) // 2]


def _amounts_match(amounts: list[Decimal]) -> bool:
    typical = _typical_amount(amounts)
    if typical == 0:
        return False
    return all(abs(a - typical) / typical <= _AMOUNT_TOLERANCE for a in amounts)


def _gaps_ok(dates: list[date], min_gap: int, max_gap: int) -> bool:
    gaps = [(b - a).days for a, b in zip(dates, dates[1:])]
    return bool(gaps) and all(min_gap <= gap <= max_gap for gap in gaps)


def find_recurring(transactions: list[Transaction]) -> list[Recurring]:
    """Detect recurring charges among debit transactions."""
    by_payee: dict[str, list[Transaction]] = {}
    for txn in transactions:
        if txn.direction != "debit" or txn.kind not in ("spending", "fee"):
            continue
        key = (txn.payee or txn.narration).strip().lower()
        if not key:
            continue
        by_payee.setdefault(key, []).append(txn)

    found: list[Recurring] = []
    for txns in by_payee.values():
        txns = sorted(txns, key=lambda t: t.date)
        amounts = [t.amount for t in txns]
        dates = [t.date for t in txns]
        payee = txns[0].payee or txns[0].narration
        category = txns[0].category
        typical = _typical_amount(amounts)
        if len(txns) >= 3 and _gaps_ok(dates, _MONTHLY_MIN_GAP, _MONTHLY_MAX_GAP) and _amounts_match(amounts):
            found.append(
                Recurring(
                    payee=payee,
                    category=category,
                    cadence="monthly",
                    amount=typical,
                    count=len(txns),
                    first=dates[0],
                    last=dates[-1],
                    next_expected=dates[-1] + timedelta(days=30),
                    yearly_cost=typical * 12,
                )
            )
        elif len(txns) >= 2 and _gaps_ok(dates, _ANNUAL_MIN_GAP, _ANNUAL_MAX_GAP) and _amounts_match(amounts):
            found.append(
                Recurring(
                    payee=payee,
                    category=category,
                    cadence="annual",
                    amount=typical,
                    count=len(txns),
                    first=dates[0],
                    last=dates[-1],
                    next_expected=dates[-1] + timedelta(days=365),
                    yearly_cost=typical,
                )
            )
        elif (
            len(txns) == 1
            and payee in SUBSCRIPTION_MERCHANTS
            and (date.today() - dates[0]).days <= 365
        ):
            found.append(
                Recurring(
                    payee=payee,
                    category=category,
                    cadence="possible annual",
                    amount=typical,
                    count=1,
                    first=dates[0],
                    last=dates[-1],
                    next_expected=None,
                    yearly_cost=typical,
                )
            )
    found.sort(key=lambda r: r.yearly_cost, reverse=True)
    return found
