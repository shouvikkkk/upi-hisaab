import unittest
from decimal import Decimal

from upi_hisaab.statements import StatementError, read_statement_csv

SBI_CSV = """Transaction Date,Narration,Debit,Credit,Balance
01/11/2026,UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY,349.00,,24500.00
01/11/2026,NEFT-SALARY ACME PVT LTD,,25000.00,49500.00
Total,,,,
"""

HDFC_CSV = """Txn Date,Description,Amount,Dr/Cr
01-Nov-26,UPI/412345678901/P2M/9876543210@okhdfcbank/ZOMATO,215.00,Dr
02-Nov-26,IMPS/412345678902/RAMESH KUMAR,60.00,Dr
"""

ICICI_CSV = """Value Date,Particulars,Debit,Credit
01-Nov-2026,UPI/412345678901/P2M/9876543210@okhdfcbank/OLA,140.00,
02-Nov-2026,Interest Credit,,45.00
"""

SIGNED_CSV = """Date,Narration,Amount
01/11/2026,UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY,-349.00
02/11/2026,NEFT-SALARY ACME PVT LTD,25000.00
"""


class TestStatementFormats(unittest.TestCase):
    def test_sbi_debit_credit_columns(self):
        txns, warnings = read_statement_csv(SBI_CSV)
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0].direction, "debit")
        self.assertEqual(txns[0].amount, Decimal("349.00"))
        self.assertEqual(txns[0].payee, "SWIGGY")
        self.assertEqual(txns[1].direction, "credit")
        self.assertEqual(txns[1].amount, Decimal("25000.00"))

    def test_hdfc_amount_plus_marker(self):
        txns, warnings = read_statement_csv(HDFC_CSV)
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0].direction, "debit")
        self.assertEqual(txns[0].payee, "ZOMATO")
        self.assertEqual(txns[1].payee, "RAMESH KUMAR")

    def test_icici_value_date(self):
        txns, warnings = read_statement_csv(ICICI_CSV)
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[1].direction, "credit")

    def test_signed_amount_column(self):
        txns, warnings = read_statement_csv(SIGNED_CSV)
        self.assertEqual(txns[0].direction, "debit")
        self.assertEqual(txns[1].direction, "credit")

    def test_semicolon_separator(self):
        csv_text = (
            "Date;Narration;Debit;Credit\n"
            "01/11/2026;UPI/412345678901/P2M/test@okaxis/SWIGGY;350;\n"
            "02/11/2026;NEFT-SALARY ACME;;25000\n"
        )
        txns, warnings = read_statement_csv(csv_text)
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0].payee, "SWIGGY")
        self.assertEqual(txns[1].direction, "credit")

    def test_tab_separator(self):
        csv_text = (
            "Date\tNarration\tDebit\tCredit\n"
            "01/11/2026\tUPI/412345678901/P2M/test@okaxis/SWIGGY\t350\t\n"
        )
        txns, warnings = read_statement_csv(csv_text)
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0].amount, Decimal("350"))

    def test_pipe_separator(self):
        csv_text = (
            "Date|Narration|Debit|Credit\n"
            "01/11/2026|UPI/412345678901/P2M/test@okaxis/SWIGGY|350|\n"
        )
        txns, warnings = read_statement_csv(csv_text)
        self.assertEqual(len(txns), 1)
        self.assertEqual(txns[0].payee, "SWIGGY")

    def test_dates_with_time_are_read(self):
        csv_text = (
            "Date,Narration,Debit,Credit\n"
            "01/11/2026 14:32,UPI/412345678901/P2M/test@okaxis/SWIGGY,350,\n"
            "02-Nov-2026 10:00:00,NEFT-SALARY ACME,,25000\n"
        )
        txns, warnings = read_statement_csv(csv_text)
        self.assertEqual(len(txns), 2)
        self.assertEqual(warnings, [])


class TestStatementWarnings(unittest.TestCase):
    def test_bad_date_row_is_reported_not_dropped_silently(self):
        csv_text = (
            "Date,Narration,Debit,Credit\n"
            "not-a-date,UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY,349.00,\n"
            "01/11/2026,UPI/412345678901/P2M/9876543210@okhdfcbank/ZOMATO,215.00,\n"
        )
        txns, warnings = read_statement_csv(csv_text)
        self.assertEqual(len(txns), 1)
        self.assertEqual(len(warnings), 1)
        self.assertIn("could not read the date", warnings[0])

    def test_bad_amount_row_is_reported(self):
        csv_text = (
            "Date,Narration,Debit,Credit\n"
            "01/11/2026,UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY,abc,\n"
        )
        txns, warnings = read_statement_csv(csv_text)
        self.assertEqual(len(txns), 0)
        self.assertEqual(len(warnings), 1)
        self.assertIn("could not read the amount", warnings[0])

    def test_no_header_raises(self):
        with self.assertRaises(StatementError):
            read_statement_csv("hello\nworld\n")

    def test_both_columns_filled_is_flagged(self):
        csv_text = (
            "Date,Narration,Debit,Credit\n"
            "01/11/2026,UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY,349.00,349.00\n"
        )
        txns, warnings = read_statement_csv(csv_text)
        self.assertEqual(len(txns), 1)
        self.assertTrue(any("both debit and credit" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
