import unittest
from datetime import date

from upi_hisaab.dates import parse_date, parse_month


class TestParseDate(unittest.TestCase):
    def test_sbi_slash_format(self):
        self.assertEqual(parse_date("01/11/2026"), date(2026, 11, 1))

    def test_day_first_not_month_first(self):
        # Indian statements are day-first: 05/11 is 5 November.
        self.assertEqual(parse_date("05/11/2026"), date(2026, 11, 5))

    def test_hdfc_short_month(self):
        self.assertEqual(parse_date("01-Nov-26"), date(2026, 11, 1))

    def test_icici_long_month(self):
        self.assertEqual(parse_date("01-Nov-2026"), date(2026, 11, 1))

    def test_iso(self):
        self.assertEqual(parse_date("2026-11-01"), date(2026, 11, 1))

    def test_space_format(self):
        self.assertEqual(parse_date("01 Nov 2026"), date(2026, 11, 1))

    def test_garbage_is_none_not_a_guess(self):
        self.assertIsNone(parse_date("not a date"))
        self.assertIsNone(parse_date(""))
        self.assertIsNone(parse_date("32/13/2026"))

    def test_time_of_day_is_ignored(self):
        # Real exports carry a time; the report works in whole days.
        self.assertEqual(parse_date("01/11/2026 14:32"), date(2026, 11, 1))
        self.assertEqual(parse_date("01-Nov-2026 10:00:00"), date(2026, 11, 1))
        self.assertEqual(parse_date("2026-11-01T14:32:00"), date(2026, 11, 1))
        self.assertEqual(parse_date("2026-11-01 09:15"), date(2026, 11, 1))
        self.assertEqual(parse_date("1 Nov 2026 2:32 PM"), date(2026, 11, 1))

    def test_two_digit_year_with_month_word(self):
        self.assertEqual(parse_date("01 Nov 26"), date(2026, 11, 1))
        self.assertEqual(parse_date("01 November 26"), date(2026, 11, 1))

    def test_two_digit_year_numeric(self):
        self.assertEqual(parse_date("01-11-26"), date(2026, 11, 1))
        self.assertEqual(parse_date("01.11.26"), date(2026, 11, 1))


class TestParseMonth(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(parse_month("2026-11"), (2026, 11))

    def test_bad(self):
        self.assertIsNone(parse_month("2026-13"))
        self.assertIsNone(parse_month("november"))
        self.assertIsNone(parse_month("11-2026"))


if __name__ == "__main__":
    unittest.main()
