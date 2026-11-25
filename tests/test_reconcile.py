import unittest
from datetime import date
from decimal import Decimal

from upi_hisaab.categorize import categorise_all
from upi_hisaab.models import Transaction
from upi_hisaab.normalize import parse_nicknames
from upi_hisaab.reconcile import reconcile


def txn(day, amount, direction, narration, payee="", utr=""):
    return Transaction(
        date=date(2026, 11, day),
        amount=Decimal(str(amount)),
        direction=direction,
        narration=narration,
        payee=payee,
        utr=utr,
    )


class TestDedupe(unittest.TestCase):
    def test_same_utr_twice_is_one_payment(self):
        a = txn(4, 349, "debit", "UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY", "SWIGGY", "412345678901")
        b = txn(4, 349, "debit", "UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY", "SWIGGY", "412345678901")
        kept, counts = reconcile([a, b])
        self.assertEqual(counts["duplicates_removed"], 1)
        self.assertEqual(len(kept), 1)

    def test_same_amount_different_utr_is_two_payments(self):
        a = txn(4, 640, "debit", "UPI/412345678901/P2M/x/SWIGGY", "SWIGGY", "412345678901")
        b = txn(4, 640, "debit", "UPI/412345678902/P2M/x/SWIGGY", "SWIGGY", "412345678902")
        kept, counts = reconcile([a, b])
        self.assertEqual(counts["duplicates_removed"], 0)
        self.assertEqual(len(kept), 2)


class TestSelfTransfers(unittest.TestCase):
    def test_lite_topup_is_not_spending(self):
        lite = txn(15, 1000, "debit", "UPI LITE TOPUP")
        lite.kind = "lite_topup"
        kept, _ = reconcile([lite])
        self.assertEqual(kept[0].kind, "self_transfer")

    def test_own_account_by_nickname(self):
        nicknames, _ = parse_nicknames("own: 50100 23456 789 = My SBI savings\n")
        move = txn(28, 5000, "debit", "IMPS/412345678019/SELF SBI SAVINGS 50100 23456 789", "SELF SBI SAVINGS 50100 23456 789")
        kept, _ = reconcile([move], nicknames)
        self.assertEqual(kept[0].kind, "self_transfer")

    def test_self_word_in_narration(self):
        move = txn(28, 5000, "debit", "IMPS/412345678019/SELF TRANSFER", "SELF TRANSFER")
        kept, _ = reconcile([move])
        self.assertEqual(kept[0].kind, "self_transfer")


class TestRefundsAndReversals(unittest.TestCase):
    def test_refund_matched_by_payee_and_amount(self):
        debit = txn(20, 1499, "debit", "UPI/412345678008/P2M/x/FLIPKART", "FLIPKART", "412345678008")
        credit = txn(25, 1499, "credit", "UPI/412345678017/P2M/x/FLIPKART", "FLIPKART", "412345678017")
        # Dates are both in November; set the debit 5 days earlier.
        debit.date = date(2026, 10, 20)
        credit.date = date(2026, 10, 25)
        kept, _ = reconcile([debit, credit])
        self.assertEqual(kept[0].kind, "refund")
        self.assertEqual(kept[1].kind, "refund")

    def test_same_utr_credit_is_a_reversal(self):
        debit = txn(4, 500, "debit", "UPI/412345678901/P2M/x/SWIGGY", "SWIGGY", "412345678901")
        credit = txn(5, 500, "credit", "UPI/412345678901/P2M/x/SWIGGY", "SWIGGY", "412345678901")
        kept, _ = reconcile([debit, credit])
        self.assertEqual(kept[0].kind, "reversal")
        self.assertEqual(kept[1].kind, "reversal")

    def test_unmatched_credit_is_income(self):
        salary = txn(1, 25000, "credit", "NEFT-SALARY ACME PVT LTD", "SALARY ACME PVT LTD")
        kept, _ = reconcile([salary])
        self.assertEqual(kept[0].kind, "income")


class TestFees(unittest.TestCase):
    def test_sms_charges_are_fees(self):
        charge = txn(22, "17.70", "debit", "SMS CHARGES", "SMS CHARGES")
        kept, _ = reconcile(categorise_all([charge]))
        self.assertEqual(kept[0].kind, "fee")
        self.assertEqual(kept[0].category, "Bank charges")


if __name__ == "__main__":
    unittest.main()
