"""Nicknames: the user's own plain-words map for personal QR payees.

A bank statement shows "Ramesh Kumar" where a person means "the milkman".
Nobody else can know that — so the user keeps one small text file:

    Ramesh Kumar = Milkman, Groceries
    9876543210@okhdfcbank = Milkman, Groceries
    own: 50100 23456 789 = My SBI savings

Lines starting with # are comments. The part before "=" is matched
(case-insensitively) against the payee name or the VPA handle. A line
starting with "own:" marks one of the user's own accounts, so transfers
to it are recognised as self-transfers, not spending.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Nicknames:
    """Parsed nickname file."""

    entries: list[tuple[str, str, str]] = field(default_factory=list)
    # (match text lower-cased, label, category)
    own_accounts: list[str] = field(default_factory=list)

    def lookup(self, payee: str, vpa: str = "") -> tuple[str, str] | None:
        """Return (label, category) for a payee/VPA, or None."""
        for needle in (payee, vpa):
            if not needle:
                continue
            hay = needle.strip().lower()
            for match_text, label, category in self.entries:
                if match_text and match_text in hay:
                    return label, category
        return None

    def is_own_account(self, payee: str, vpa: str = "", narration: str = "") -> bool:
        """True when the payee looks like one of the user's own accounts."""
        text = f"{payee} {vpa} {narration}".lower()
        for marker in self.own_accounts:
            if marker and marker in text:
                return True
        return looks_like_self_transfer(payee, vpa, narration)


_SELF_WORDS = re.compile(
    r"\b(self|own account|own ac|to self|my account|self transfer)\b", re.I
)


def looks_like_self_transfer(payee: str, vpa: str = "", narration: str = "") -> bool:
    """True when the wording says the money went to the user themselves.

    Works with no nickname file at all — "SELF", "OWN ACCOUNT" and
    "TO SELF" are how banks write it.
    """
    text = f"{payee} {vpa} {narration}"
    return bool(_SELF_WORDS.search(text))


def parse_nicknames(text: str) -> tuple[Nicknames, list[str]]:
    """Parse nickname file text. Returns (nicknames, warnings)."""
    result = Nicknames()
    warnings: list[str] = []
    for lineno, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            warnings.append(f"line {lineno}: no '=' — skipped ('{line}')")
            continue
        left, right = line.split("=", 1)
        left = left.strip()
        right = right.strip()
        if left.lower().startswith("own:"):
            marker = left[4:].strip().lower()
            if marker:
                result.own_accounts.append(marker)
            continue
        if "," in right:
            label, category = [part.strip() for part in right.rsplit(",", 1)]
        else:
            label, category = right, ""
        if not left or not label:
            warnings.append(f"line {lineno}: empty payee or label — skipped")
            continue
        result.entries.append((left.lower(), label, category))
    return result, warnings
