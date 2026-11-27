import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from upi_hisaab.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
STATEMENT = str(EXAMPLES / "sample-statement.csv")
NICKNAMES = str(EXAMPLES / "sample-nicknames.txt")


def run_cli(argv):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main(argv)
    return code, buffer.getvalue()


class TestCliEndToEnd(unittest.TestCase):
    def test_sample_report(self):
        code, out = run_cli(["report", STATEMENT, "--nicknames", NICKNAMES])
        self.assertEqual(code, 0)
        # Money in: 3 x 25,000 salary.
        self.assertIn("Money in:  ₹75,000", out)
        # Real spending: 8,405.70 across Sep-Nov (see README for the maths).
        self.assertIn("Money out: ₹8,405.70", out)
        # The duplicate Swiggy payment is removed, not counted twice.
        self.assertIn("Removed 1 duplicate line(s)", out)
        # The Flipkart refund came back.
        self.assertIn("Refunds that came back: ₹1,499", out)
        # Self-transfers + Lite top-ups are not spending.
        self.assertIn("Moved between your own accounts: ₹7,000", out)
        # Netflix repeats monthly: 199 x 12 = 2,388 a year.
        self.assertIn("Netflix", out)
        self.assertIn("₹2,388/year", out)
        # One payment nobody can identify.
        self.assertIn("Money you still cannot account for: ₹250", out)
        # The milkman is milk, not a mystery name.
        self.assertIn("Milkman", out)

    def test_sample_report_json(self):
        code, out = run_cli(["report", STATEMENT, "--nicknames", NICKNAMES, "--format", "json"])
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["income_total"], "75000.00")
        self.assertEqual(data["spending_total"], "8405.70")
        self.assertEqual(data["uncategorised_total"], "250.00")
        self.assertEqual(data["counts"]["duplicates_removed"], 1)
        recurring = {r["payee"]: r for r in data["recurring"]}
        self.assertEqual(recurring["Netflix"]["cadence"], "monthly")
        self.assertEqual(recurring["Netflix"]["yearly_cost"], "2388.00")

    def test_month_filter(self):
        code, out = run_cli(
            ["report", STATEMENT, "--nicknames", NICKNAMES, "--month", "2026-11", "--format", "json"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["month"], "November 2026")
        self.assertEqual(data["spending_total"], "2693.70")
        self.assertEqual(data["income_total"], "25000.00")

    def test_empty_month_is_an_error(self):
        code, out = run_cli(["report", STATEMENT, "--month", "2027-01"])
        self.assertEqual(code, 2)

    def test_month_report_keeps_cross_month_refund(self):
        # The Flipkart purchase is in September, its refund in October.
        # The October report must show the refund as money back, not as
        # new income — matching runs on the whole file, --month only
        # windows the report.
        code, out = run_cli(
            ["report", STATEMENT, "--nicknames", NICKNAMES, "--month", "2026-10", "--format", "json"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        self.assertEqual(data["refunds_total"], "1499.00")
        self.assertEqual(data["income_total"], "25000.00")

    def test_month_report_keeps_monthly_subscription(self):
        # Netflix charges Sep/Oct/Nov. The September report must still
        # call it monthly (₹2,388/year), not "possible annual".
        code, out = run_cli(
            ["report", STATEMENT, "--nicknames", NICKNAMES, "--month", "2026-09", "--format", "json"]
        )
        self.assertEqual(code, 0)
        data = json.loads(out)
        recurring = {r["payee"]: r for r in data["recurring"]}
        self.assertEqual(recurring["Netflix"]["cadence"], "monthly")
        self.assertEqual(recurring["Netflix"]["yearly_cost"], "2388.00")
        # Spotify's single charge is in November — not in September's list.
        self.assertNotIn("Spotify", recurring)

    def test_latin1_statement_is_read(self):
        # Bank exports in Windows-1252/Latin-1 (é byte) must not crash.
        text = "Date,Narration,Debit,Credit\n01/11/2026,Café Payment,500,\n"
        with tempfile.NamedTemporaryFile("wb", suffix=".csv", delete=False) as handle:
            handle.write(text.encode("latin-1"))
            path = handle.name
        code, out = run_cli(["report", path])
        self.assertEqual(code, 0)
        self.assertIn("Money out: ₹500", out)

    def test_semicolon_statement_is_read(self):
        text = (
            "Date;Narration;Debit;Credit\n"
            "01/11/2026;UPI/412345678901/P2M/test@okaxis/SWIGGY;350;\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as handle:
            handle.write(text)
            path = handle.name
        code, out = run_cli(["report", path])
        self.assertEqual(code, 0)
        self.assertIn("Money out: ₹350", out)

    def test_missing_file_is_an_error(self):
        with self.assertRaises(SystemExit):
            main(["report", "no-such-file.csv"])

    def test_decode(self):
        code, out = run_cli(
            ["decode", "UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY"]
        )
        self.assertEqual(code, 0)
        self.assertIn("Paid to:   SWIGGY", out)
        self.assertIn("Reference: 412345678901", out)


if __name__ == "__main__":
    unittest.main()
