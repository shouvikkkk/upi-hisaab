import unittest
from datetime import date
from decimal import Decimal

from upi_hisaab.categorize import categorise
from upi_hisaab.models import Transaction
from upi_hisaab.normalize import parse_nicknames


def txn(payee, narration=""):
    return Transaction(
        date=date(2026, 11, 3),
        amount=Decimal("60"),
        direction="debit",
        narration=narration or payee,
        payee=payee,
    )


class TestMerchantDictionary(unittest.TestCase):
    def test_swiggy(self):
        result = categorise(txn("SWIGGY"))
        self.assertEqual(result.category, "Food delivery")
        self.assertEqual(result.payee, "Swiggy")

    def test_longest_match_wins(self):
        # SWIGGY INSTAMART is groceries, not food delivery.
        result = categorise(txn("SWIGGY INSTAMART"))
        self.assertEqual(result.category, "Groceries")
        self.assertEqual(result.payee, "Swiggy Instamart")

    def test_netflix_subscription(self):
        result = categorise(txn("NETFLIX"))
        self.assertEqual(result.category, "Subscriptions")


class TestNicknames(unittest.TestCase):
    def test_nickname_beats_the_dictionary(self):
        nicknames, warnings = parse_nicknames("Ramesh Kumar = Milkman, Groceries\n")
        self.assertEqual(warnings, [])
        result = categorise(txn("RAMESH KUMAR"), nicknames)
        self.assertEqual(result.payee, "Milkman")
        self.assertEqual(result.category, "Groceries")

    def test_nickname_matches_vpa(self):
        nicknames, _ = parse_nicknames("9876543210@okhdfcbank = Milkman, Groceries\n")
        result = categorise(txn("RAMESH KUMAR"), nicknames)
        # The VPA is empty here, so no match — the lookup needs the VPA.
        self.assertEqual(result.category, "")
        t = txn("RAMESH KUMAR")
        t.vpa = "9876543210@okhdfcbank"
        result = categorise(t, nicknames)
        self.assertEqual(result.payee, "Milkman")

    def test_bad_line_is_reported(self):
        _, warnings = parse_nicknames("this line has no equals sign\n")
        self.assertEqual(len(warnings), 1)


class TestKeywordsAndUnknowns(unittest.TestCase):
    def test_keyword_fallback(self):
        result = categorise(txn("AUTO RICKSHAW"))
        self.assertEqual(result.category, "Local transport")

    def test_unknown_stays_unknown(self):
        # Never invent a category. The report must say so honestly.
        result = categorise(txn("SOME RANDOM SHOP"))
        self.assertEqual(result.category, "")


if __name__ == "__main__":
    unittest.main()
