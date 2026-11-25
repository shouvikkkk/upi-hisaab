import unittest

from upi_hisaab.narration import is_lite_topup, parse_narration


class TestUpiNarration(unittest.TestCase):
    def test_full_upi_line(self):
        parsed = parse_narration("UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY")
        self.assertEqual(parsed["channel"], "upi")
        self.assertEqual(parsed["utr"], "412345678901")
        self.assertEqual(parsed["vpa"], "9876543210@okhdfcbank")
        self.assertEqual(parsed["payee"], "SWIGGY")

    def test_personal_qr_payee(self):
        parsed = parse_narration("UPI/412345678901/P2A/9876543210@okaxis/RAMESH KUMAR")
        self.assertEqual(parsed["channel"], "upi")
        self.assertEqual(parsed["payee"], "RAMESH KUMAR")

    def test_truncated_vpa_only(self):
        # No payee segment at all: the VPA is the only identifier we have.
        parsed = parse_narration("UPI/412345678901/P2M/9876543210@okhdfcbank")
        self.assertEqual(parsed["payee"], "9876543210@okhdfcbank")
        self.assertEqual(parsed["vpa"], "9876543210@okhdfcbank")

    def test_paytm_handle_is_not_a_gateway(self):
        # A person's Paytm handle must not mark the payment as "via Paytm".
        parsed = parse_narration("UPI/412345678901/P2M/9876543210@paytm/SWIGGY")
        self.assertEqual(parsed["payee"], "SWIGGY")
        self.assertEqual(parsed["gateway"], "")

    def test_gateway_line_hides_the_shop(self):
        parsed = parse_narration("UPI/412345678901/P2M/RAZORPAY/ORDER123")
        self.assertEqual(parsed["payee"], "Razorpay")
        self.assertEqual(parsed["gateway"], "Razorpay")


class TestOtherChannels(unittest.TestCase):
    def test_imps(self):
        parsed = parse_narration("IMPS/412345678901/RAMESH KUMAR")
        self.assertEqual(parsed["channel"], "imps")
        self.assertEqual(parsed["utr"], "412345678901")
        self.assertEqual(parsed["payee"], "RAMESH KUMAR")

    def test_neft(self):
        parsed = parse_narration("NEFT-SALARY ACME PVT LTD")
        self.assertEqual(parsed["channel"], "neft")

    def test_pos(self):
        parsed = parse_narration("POS 411111******1111 SWIGGY")
        self.assertEqual(parsed["channel"], "pos")
        self.assertEqual(parsed["payee"], "SWIGGY")

    def test_atm(self):
        parsed = parse_narration("ATM WDL 1234")
        self.assertEqual(parsed["channel"], "atm")

    def test_empty(self):
        parsed = parse_narration("")
        self.assertEqual(parsed["channel"], "other")
        self.assertEqual(parsed["payee"], "")


class TestLiteTopup(unittest.TestCase):
    def test_lite_marker(self):
        self.assertTrue(is_lite_topup("UPI LITE TOPUP"))
        self.assertFalse(is_lite_topup("UPI/412345678901/P2M/9876543210@okhdfcbank/SWIGGY"))


if __name__ == "__main__":
    unittest.main()
