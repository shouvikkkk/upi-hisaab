import unittest
from decimal import Decimal

from upi_hisaab.amounts import inr, parse_amount, split_debit_credit


class TestParseAmount(unittest.TestCase):
    def test_indian_commas(self):
        self.assertEqual(parse_amount("1,234.50"), Decimal("1234.50"))

    def test_parentheses_negative(self):
        self.assertEqual(parse_amount("(1,234.50)"), Decimal("-1234.50"))

    def test_trailing_minus(self):
        self.assertEqual(parse_amount("1,234.50-"), Decimal("-1234.50"))

    def test_rupee_symbol(self):
        self.assertEqual(parse_amount("₹1,234"), Decimal("1234"))

    def test_empty_and_garbage_are_none(self):
        self.assertIsNone(parse_amount(""))
        self.assertIsNone(parse_amount("abc"))
        self.assertIsNone(parse_amount("--"))


class TestSplitDebitCredit(unittest.TestCase):
    def test_debit_column(self):
        self.assertEqual(split_debit_credit("500.00", "", ""), (Decimal("500.00"), "debit"))

    def test_credit_column(self):
        self.assertEqual(split_debit_credit("", "200.00", ""), (Decimal("200.00"), "credit"))

    def test_neither(self):
        self.assertIsNone(split_debit_credit("", "", ""))


class TestInr(unittest.TestCase):
    def test_whole(self):
        self.assertEqual(inr(Decimal("18450")), "₹18,450")

    def test_paise(self):
        self.assertEqual(inr(Decimal("1234.50")), "₹1,234.50")

    def test_negative(self):
        self.assertEqual(inr(Decimal("-500")), "-₹500")


if __name__ == "__main__":
    unittest.main()
