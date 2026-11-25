import unittest
from datetime import date
from decimal import Decimal

from upi_hisaab.models import Transaction
from upi_hisaab.recurring import find_recurring


def debit(day, month, year, amount, payee):
    return Transaction(
        date=date(year, month, day),
        amount=Decimal(str(amount)),
        direction="debit",
        narration=f"UPI/x/{payee}",
        payee=payee,
    )


class TestMonthlyRecurring(unittest.TestCase):
    def test_netflix_three_months(self):
        txns = [
            debit(2, 9, 2026, 199, "Netflix"),
            debit(2, 10, 2026, 199, "Netflix"),
            debit(2, 11, 2026, 199, "Netflix"),
        ]
        found = find_recurring(txns)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].cadence, "monthly")
        self.assertEqual(found[0].yearly_cost, Decimal("2388"))
        self.assertEqual(found[0].next_expected, date(2026, 12, 2))

    def test_price_hike_does_not_break_the_pattern(self):
        # Netflix 199 -> 249 is a 25% hike; it must still count.
        txns = [
            debit(2, 9, 2026, 199, "Netflix"),
            debit(2, 10, 2026, 199, "Netflix"),
            debit(2, 11, 2026, 249, "Netflix"),
        ]
        found = find_recurring(txns)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].cadence, "monthly")


class TestAnnualRecurring(unittest.TestCase):
    def test_yearly_premium(self):
        txns = [
            debit(2, 11, 2025, 5000, "LIC"),
            debit(2, 11, 2026, 5000, "LIC"),
        ]
        found = find_recurring(txns)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].cadence, "annual")
        self.assertEqual(found[0].yearly_cost, Decimal("5000"))


class TestNotRecurring(unittest.TestCase):
    def test_daily_milkman_is_frequent_not_scheduled(self):
        txns = [debit(d, 11, 2026, 60, "Ramesh Kumar") for d in (3, 4, 5, 10, 12)]
        self.assertEqual(find_recurring(txns), [])

    def test_two_random_charges_are_not_recurring(self):
        txns = [
            debit(5, 11, 2026, 349, "Swiggy"),
            debit(20, 11, 2026, 500, "Swiggy"),
        ]
        self.assertEqual(find_recurring(txns), [])

    def test_single_known_subscription_is_flagged_possible(self):
        txns = [debit(12, 11, 2026, 119, "Spotify")]
        found = find_recurring(txns)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].cadence, "possible annual")

    def test_single_unknown_shop_is_not_flagged(self):
        txns = [debit(12, 11, 2026, 250, "Some Random Shop")]
        self.assertEqual(find_recurring(txns), [])


if __name__ == "__main__":
    unittest.main()
