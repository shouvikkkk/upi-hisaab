"""Build the plain-language monthly report.

Two shapes: a text report a normal person can read on their phone, and a
JSON report for spreadsheets and further analysis. Both carry the same
numbers — the text one just says them in words.

The report answers, in order: how much came in, how much really went out,
what it went on, what repeats every month, and what still needs checking.
"""

from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal

from .amounts import inr
from .models import Transaction
from .recurring import Recurring


def summarise(transactions: list[Transaction]) -> dict:
    """Aggregate the reconciled transactions into report numbers."""
    spending = [
        t
        for t in transactions
        if t.kind in ("spending", "fee", "refund") and t.direction == "debit"
    ]
    # A refunded purchase still counts as money out in the month it was
    # paid — the refund is shown separately as money that came back.
    # A reversal (failed payment debited then reversed) never bought
    # anything, so it stays out of spending.
    # Any credit that is not a refund or a reversal is money in (salary,
    # interest, a friend paying you back). Refunds/reversals are your own
    # money returning, not new income.
    income = [t for t in transactions if t.direction == "credit" and t.kind not in ("refund", "reversal")]

    by_category: dict[str, Decimal] = defaultdict(Decimal)
    by_payee: dict[str, Decimal] = defaultdict(Decimal)
    uncategorised_total = Decimal("0")
    uncategorised_count = 0
    for txn in spending:
        category = txn.category or "Uncategorised"
        by_category[category] += txn.amount
        by_payee[txn.payee or txn.narration] += txn.amount
        if not txn.category:
            uncategorised_total += txn.amount
            uncategorised_count += 1

    return {
        "income_total": sum((t.amount for t in income), Decimal("0")),
        "income_count": len(income),
        "spending_total": sum((t.amount for t in spending), Decimal("0")),
        "spending_count": len(spending),
        "by_category": dict(sorted(by_category.items(), key=lambda kv: kv[1], reverse=True)),
        "by_payee": dict(sorted(by_payee.items(), key=lambda kv: kv[1], reverse=True)),
        "uncategorised_total": uncategorised_total,
        "uncategorised_count": uncategorised_count,
        "transfers_total": sum(
            (t.amount for t in transactions if t.kind == "self_transfer"), Decimal("0")
        ),
        "refunds_total": sum(
            (t.amount for t in transactions if t.kind == "refund" and t.direction == "credit"),
            Decimal("0"),
        ),
    }


def render_text(
    summary: dict,
    recurring: list[Recurring],
    counts: dict[str, int],
    warnings: list[str],
    month_label: str,
) -> str:
    """Render the human-readable report."""
    lines: list[str] = []
    lines.append(f"Your money in {month_label}")
    lines.append("=" * (len(lines[0])))
    lines.append("")
    lines.append(f"Money in:  {inr(summary['income_total'])} ({summary['income_count']} credits)")
    lines.append(f"Money out: {inr(summary['spending_total'])} ({summary['spending_count']} payments)")
    if summary["transfers_total"]:
        lines.append(
            f"Moved between your own accounts: {inr(summary['transfers_total'])} "
            "(not counted as spending)"
        )
    if summary["refunds_total"]:
        lines.append(f"Refunds that came back: {inr(summary['refunds_total'])}")
    lines.append("")
    lines.append("What it went on:")
    for category, total in summary["by_category"].items():
        share = (
            (total / summary["spending_total"] * 100)
            if summary["spending_total"]
            else Decimal("0")
        )
        lines.append(f"  {category:<22} {inr(total):>12}  ({share:.0f}%)")
    lines.append("")
    lines.append("Biggest payees:")
    for payee, total in list(summary["by_payee"].items())[:8]:
        lines.append(f"  {payee[:34]:<34} {inr(total):>12}")
    lines.append("")
    if recurring:
        lines.append("Repeats every month (check these — subscriptions hide here):")
        for item in recurring:
            when = (
                f", next around {item.next_expected:%d %b %Y}"
                if item.next_expected
                else ""
            )
            charges = "charge" if item.count == 1 else "charges"
            lines.append(
                f"  {item.payee} — {inr(item.amount)} {item.cadence} "
                f"({item.count} {charges}, {inr(item.yearly_cost)}/year{when})"
            )
        lines.append("")
    if summary["uncategorised_count"]:
        payments = "payment" if summary["uncategorised_count"] == 1 else "payments"
        lines.append(
            f"Money you still cannot account for: {inr(summary['uncategorised_total'])} "
            f"across {summary['uncategorised_count']} {payments}. Add nicknames for "
            "those payees and run it again."
        )
        lines.append("")
    if counts.get("duplicates_removed"):
        lines.append(
            f"Removed {counts['duplicates_removed']} duplicate line(s) — the same "
            "payment listed twice (UPI app + bank statement)."
        )
        lines.append("")
    if warnings:
        lines.append("Rows we could not read (check your statement file):")
        for warning in warnings:
            lines.append(f"  - {warning}")
        lines.append("")
    return "\n".join(lines)


def render_json(
    summary: dict,
    recurring: list[Recurring],
    counts: dict[str, int],
    warnings: list[str],
    month_label: str,
) -> str:
    """Render the machine-readable report."""
    data = {
        "month": month_label,
        "income_total": str(summary["income_total"]),
        "spending_total": str(summary["spending_total"]),
        "by_category": {k: str(v) for k, v in summary["by_category"].items()},
        "by_payee": {k: str(v) for k, v in summary["by_payee"].items()},
        "uncategorised_total": str(summary["uncategorised_total"]),
        "uncategorised_count": summary["uncategorised_count"],
        "transfers_total": str(summary["transfers_total"]),
        "refunds_total": str(summary["refunds_total"]),
        "recurring": [
            {
                "payee": r.payee,
                "category": r.category,
                "cadence": r.cadence,
                "amount": str(r.amount),
                "count": r.count,
                "first": r.first.isoformat(),
                "last": r.last.isoformat(),
                "next_expected": r.next_expected.isoformat() if r.next_expected else None,
                "yearly_cost": str(r.yearly_cost),
            }
            for r in recurring
        ],
        "counts": counts,
        "warnings": warnings,
    }
    return json.dumps(data, indent=2, ensure_ascii=False)
