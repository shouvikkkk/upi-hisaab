"""Read bank-statement CSV exports into Transactions.

Banks do not agree on a format. SBI, HDFC and ICICI each use different
column names, date formats and debit/credit layouts, and every export has
header junk and footer rows ("Total", "Closing balance"). This module
auto-detects the layout from the header row and skips rows it cannot read,
reporting each skipped row instead of silently dropping real money.

Supported layouts:
  * separate Debit / Credit columns (SBI, ICICI)
  * single Amount column + Dr/Cr marker (HDFC)
  * single signed Amount column (generic)
Column names are matched case-insensitively and by alias, so
"Transaction Date", "Txn Date", "Value Date" and "Date" all work.
"""

from __future__ import annotations

import csv
import io
from datetime import date
from decimal import Decimal

from .amounts import parse_amount, split_debit_credit
from .dates import parse_date
from .models import Transaction
from .narration import parse_narration

_DATE_ALIASES = (
    "transaction date",
    "txn date",
    "value date",
    "date",
    "tran date",
)
_NARRATION_ALIASES = (
    "narration",
    "description",
    "particulars",
    "transaction details",
    "remarks",
    "details",
)
_DEBIT_ALIASES = ("debit", "debit amount", "withdrawal", "withdrawals", "dr amount", "amount dr")
_CREDIT_ALIASES = ("credit", "credit amount", "deposit", "deposits", "cr amount", "amount cr")
_AMOUNT_ALIASES = ("amount", "transaction amount", "txn amount")
_MARKER_ALIASES = ("dr/cr", "dr cr", "type", "dc", "debit/credit")
_BALANCE_ALIASES = ("balance", "closing balance", "running balance")

# Rows whose narration starts with one of these are summary/footer rows,
# not transactions. Checked case-insensitively after stripping.
_FOOTER_PREFIXES = (
    "total",
    "closing balance",
    "opening balance",
    "statement summary",
    "grand total",
    "account summary",
)


def _norm(header: str) -> str:
    return " ".join((header or "").strip().lower().split())


def _pick(columns: dict[str, int], aliases: tuple[str, ...]) -> int | None:
    for alias in aliases:
        if alias in columns:
            return columns[alias]
    return None


class StatementError(Exception):
    """Raised when a file cannot be read as a statement at all."""


def read_statement_csv(text: str) -> tuple[list[Transaction], list[str]]:
    """Parse statement CSV text. Returns (transactions, warnings).

    Warnings name every skipped row (line number + reason) so the user
    can check nothing real was lost. A file with no recognisable header
    raises StatementError.
    """
    reader = csv.reader(io.StringIO(text))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        raise StatementError("The file is empty.")

    header_idx = None
    columns: dict[str, int] = {}
    for i, row in enumerate(rows):
        normed = [_norm(cell) for cell in row]
        columns = {name: idx for idx, name in enumerate(normed) if name}
        if _pick(columns, _DATE_ALIASES) is not None and (
            _pick(columns, _NARRATION_ALIASES) is not None
            or _pick(columns, _AMOUNT_ALIASES) is not None
        ):
            header_idx = i
            break
    if header_idx is None:
        raise StatementError(
            "Could not find a header row with a date column and a "
            "narration/amount column. Export the statement as CSV from "
            "your bank's net banking (not a PDF)."
        )

    date_col = _pick(columns, _DATE_ALIASES)
    narr_col = _pick(columns, _NARRATION_ALIASES)
    debit_col = _pick(columns, _DEBIT_ALIASES)
    credit_col = _pick(columns, _CREDIT_ALIASES)
    amount_col = _pick(columns, _AMOUNT_ALIASES)
    marker_col = _pick(columns, _MARKER_ALIASES)

    transactions: list[Transaction] = []
    warnings: list[str] = []
    for lineno, row in enumerate(rows[header_idx + 1 :], start=header_idx + 2):

        def cell(col: int | None) -> str:
            if col is None or col >= len(row):
                return ""
            return row[col].strip()

        narration = cell(narr_col)
        if not narration:
            continue
        if narration.lower().startswith(_FOOTER_PREFIXES):
            continue
        txn_date = parse_date(cell(date_col))
        if txn_date is None:
            warnings.append(
                f"line {lineno}: could not read the date "
                f"'{cell(date_col)}' — row skipped"
            )
            continue

        amount: Decimal | None = None
        direction = ""
        both_filled = False
        if debit_col is not None or credit_col is not None:
            debit = parse_amount(cell(debit_col))
            credit = parse_amount(cell(credit_col))
            if debit is not None and credit is not None:
                both_filled = True
            result = split_debit_credit(cell(debit_col), cell(credit_col), cell(marker_col))
            if result is not None:
                amount, direction = result
        if amount is None and amount_col is not None:
            raw_amount = parse_amount(cell(amount_col))
            if raw_amount is not None:
                marker = cell(marker_col).upper()
                if raw_amount < 0:
                    amount, direction = -raw_amount, "debit"
                elif marker in ("DR", "D", "DEBIT"):
                    amount, direction = raw_amount, "debit"
                elif marker in ("CR", "C", "CREDIT"):
                    amount, direction = raw_amount, "credit"
                else:
                    amount, direction = raw_amount, "credit"
        if amount is None:
            warnings.append(
                f"line {lineno}: could not read the amount "
                f"(debit '{cell(debit_col)}', credit '{cell(credit_col)}', "
                f"amount '{cell(amount_col)}') — row skipped"
            )
            continue
        if both_filled:
            warnings.append(
                f"line {lineno}: both debit and credit are filled — "
                "treated as a debit, please check the row"
            )

        parsed = parse_narration(narration)
        txn = Transaction(
            date=txn_date,
            amount=amount,
            direction=direction,
            narration=narration,
            utr=parsed["utr"],
            payee=parsed["payee"],
            vpa=parsed["vpa"],
            channel=parsed["channel"],
        )
        if parsed["gateway"]:
            txn.note(f"paid via {parsed['gateway']} — the shop's name is hidden")
        if parsed["is_lite_topup"]:
            txn.kind = "lite_topup"
            txn.note("UPI Lite top-up — money moved into your Lite wallet, not spent")
        transactions.append(txn)

    if not transactions and not warnings:
        raise StatementError("No transaction rows found below the header.")
    return transactions, warnings
