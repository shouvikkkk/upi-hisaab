"""Parse the date formats Indian bank statements actually use.

Real exports mix formats, sometimes inside one file: 01/11/2026 (SBI),
01-Nov-26 (HDFC), 01-Nov-2026 (ICICI), 2026-11-01, 01 Nov 2026. Many
exports also carry a time of day ("01/11/2026 14:32",
"01-Nov-2026 10:00:00", "2026-11-01T14:32:00") — the date part is what
matters for a monthly report, so a trailing time is stripped before
parsing. A date we cannot parse is reported as a failure, never
guessed — guessing a date would silently move money into the wrong
month.
"""

from __future__ import annotations

import re
from datetime import date, datetime

_FORMATS = (
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d-%b-%y",
    "%d-%b-%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%d %b %y",
    "%d %B %y",
    "%Y-%m-%d",
    "%d.%m.%Y",
    "%d/%m/%y",
    "%d-%m-%y",
    "%d.%m.%y",
    "%Y/%m/%d",
)

# A trailing time of day: " 14:32", " 10:00:00", " 2:32 PM", ".123".
_TIME_SUFFIX = re.compile(
    r"\s+\d{1,2}:\d{2}(:\d{2})?(\.\d+)?(\s*[AaPp][Mm])?$"
)

_MONTH_WORD = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", re.I)


def _strip_time(text: str) -> str:
    """Remove a trailing time of day, keeping only the date part."""
    # ISO datetime: "2026-11-01T14:32:00" -> "2026-11-01".
    if "T" in text:
        head, _, _ = text.partition("T")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", head.strip()):
            return head.strip()
    return _TIME_SUFFIX.sub("", text).strip()


def parse_date(raw: str) -> date | None:
    """Parse one date string. Returns None when nothing matches.

    Two-digit years are read as 2000s (a statement dated 01-Nov-26 is
    2026, never 1926). Ambiguous day-first formats win: Indian statements
    are day-first, so 05/11/2026 is 5 November, never 11 May. A trailing
    time of day ("01/11/2026 14:32") is ignored — the report works in
    whole days.
    """
    text = (raw or "").strip()
    if not text:
        return None
    # Normalise separators inside month-word dates: "01 Nov, 2026".
    text = text.replace(",", " ")
    text = re.sub(r"\s+", " ", text).strip()
    text = _strip_time(text)

    for fmt in _FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_month(raw: str) -> tuple[int, int] | None:
    """Parse a YYYY-MM month argument (e.g. --month 2026-11)."""
    text = (raw or "").strip()
    match = re.fullmatch(r"(\d{4})-(\d{1,2})", text)
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        return None
    return year, month
