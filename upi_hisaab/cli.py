"""Command line interface for upi-hisaab.

Two commands:
  report  — turn a statement CSV into a plain-language monthly report
  decode  — explain one narration line ("what does this UPI line mean?")

Everything runs offline. Your statement never leaves your computer.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from . import __version__
from .categorize import categorise_all
from .dates import parse_month
from .normalize import parse_nicknames
from .reconcile import reconcile
from .recurring import find_recurring
from .report import render_json, render_text, summarise
from .statements import StatementError, read_statement_csv


def _read_file(path: str) -> str:
    """Read a text file, tolerating the encodings banks actually export.

    Most exports are UTF-8, but many Indian bank CSVs arrive as
    Windows-1252 / Latin-1 (a ₹ or é byte breaks a strict UTF-8 read).
    Try UTF-8 first, then fall back — Latin-1 can decode any byte, so
    the user gets a report instead of a traceback.
    """
    try:
        with open(path, "rb") as handle:
            raw = handle.read()
    except FileNotFoundError:
        print(f"error: no such file: {path}", file=sys.stderr)
        raise SystemExit(2)
    except OSError as exc:
        print(f"error: could not read {path}: {exc}", file=sys.stderr)
        raise SystemExit(2)
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    # Unreachable (latin-1 never fails), but never show a traceback.
    print(f"error: could not read {path} as text", file=sys.stderr)
    raise SystemExit(2)


def _month_label(transactions, month_arg: str | None) -> str:
    if month_arg:
        parsed = parse_month(month_arg)
        if parsed is None:
            print("error: --month must look like 2026-11", file=sys.stderr)
            raise SystemExit(2)
        year, month = parsed
        return date(year, month, 1).strftime("%B %Y")
    if transactions:
        first = min(t.date for t in transactions)
        last = max(t.date for t in transactions)
        if (first.year, first.month) == (last.year, last.month):
            return first.strftime("%B %Y")
        return f"{first.strftime('%B %Y')} – {last.strftime('%B %Y')}"
    return "this month"


def cmd_report(args: argparse.Namespace) -> int:
    text = _read_file(args.statement)
    try:
        transactions, warnings = read_statement_csv(text)
    except StatementError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    nicknames = None
    if args.nicknames:
        nick_text = _read_file(args.nicknames)
        nicknames, nick_warnings = parse_nicknames(nick_text)
        warnings = warnings + nick_warnings

    # Reconcile and find subscriptions on the WHOLE file first. A refund
    # often lands in the next month (buy in September, refund in
    # October) and a subscription is only "monthly" across months —
    # filtering to one month before matching would lose both, and the
    # October refund would be counted as new income. --month only
    # windows what the report shows.
    transactions = categorise_all(transactions, nicknames)
    transactions, counts, dropped = reconcile(transactions, nicknames)
    recurring = find_recurring(transactions)

    if args.month:
        parsed = parse_month(args.month)
        if parsed is None:
            print("error: --month must look like 2026-11", file=sys.stderr)
            return 2
        year, month = parsed
        month_start = date(year, month, 1)
        month_end = (
            date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        )
        windowed = [
            t for t in transactions if month_start <= t.date < month_end
        ]
        if not windowed:
            print(
                f"error: no transactions in {args.month} "
                f"({len(transactions)} in the file)",
                file=sys.stderr,
            )
            return 2
        transactions = windowed
        # Counts describe the month shown, not the whole file.
        counts = {
            "duplicates_removed": sum(
                1 for t in dropped if month_start <= t.date < month_end
            )
        }
        for kind in ("self_transfer", "refund", "reversal", "fee", "spending", "income"):
            counts[kind] = sum(1 for t in transactions if t.kind == kind)
        # Show subscriptions that were active in this month (their
        # charge range overlaps it), still judged on full history.
        recurring = [
            item
            for item in recurring
            if item.first < month_end and item.last >= month_start
        ]

    summary = summarise(transactions)
    label = _month_label(transactions, args.month)

    if args.format == "json":
        print(render_json(summary, recurring, counts, warnings, label))
    else:
        print(render_text(summary, recurring, counts, warnings, label))
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    from .narration import parse_narration

    parsed = parse_narration(args.narration)
    print(f"Narration: {args.narration}")
    print(f"Channel:   {parsed['channel']}")
    if parsed["utr"]:
        print(f"Reference: {parsed['utr']} (use this 12-digit number to find the payment in your UPI app)")
    if parsed["vpa"]:
        print(f"UPI ID:    {parsed['vpa']}")
    if parsed["payee"]:
        print(f"Paid to:   {parsed['payee']}")
    if parsed["gateway"]:
        print(f"Note:      {parsed['gateway']} is a payment gateway — the shop's name is hidden")
    if parsed["is_lite_topup"]:
        print("Note:      this is a UPI Lite top-up, not a purchase")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="upi-hisaab",
        description="Turn your bank statement into a plain-language monthly budget. Offline, free, no accounts.",
    )
    parser.add_argument("--version", action="version", version=f"upi-hisaab {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    report = sub.add_parser(
        "report",
        help="build a monthly report from a statement CSV",
    )
    report.add_argument("statement", help="statement CSV exported from net banking")
    report.add_argument(
        "--nicknames",
        help="your nickname file (who 'Ramesh Kumar' really is)",
    )
    report.add_argument("--month", help="only this month, e.g. 2026-11")
    report.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="plain words (default) or JSON",
    )
    report.set_defaults(func=cmd_report)

    decode = sub.add_parser(
        "decode",
        help="explain one narration line from your statement",
    )
    decode.add_argument("narration", help='e.g. "UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY"')
    decode.set_defaults(func=cmd_decode)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
