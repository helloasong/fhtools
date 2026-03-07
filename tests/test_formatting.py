import unittest
import pandas as pd

from src.utils.formatting import format_number, format_interval, format_bin_label, get_precision_step, parse_precision_step, snap_value_to_precision


class TestFormatting(unittest.TestCase):
    def test_format_number_unit_and_precision(self):
        self.assertEqual(format_number(12345, precision="0.1"), "12345")
        self.assertEqual(format_number(15000, precision="1"), "15000")
        self.assertEqual(format_number(999, precision="10"), "1000")

    def test_format_interval(self):
        itv = pd.Interval(left=0.12, right=12.34, closed="right")
        s = format_interval(itv, precision="0.01")
        self.assertEqual(s, "(0.12, 12.34]")

    def test_format_bin_label_passthrough(self):
        self.assertEqual(format_bin_label("Missing", precision="0.1"), "Missing")

    def test_precision_step_helpers(self):
        self.assertEqual(get_precision_step("decimal", 2), "0.01")
        self.assertEqual(get_precision_step("integer", 3), "1000")
        self.assertEqual(parse_precision_step("0.001"), ("decimal", 3))
        self.assertEqual(parse_precision_step("100"), ("integer", 2))

    def test_snap_value_to_precision(self):
        self.assertEqual(snap_value_to_precision(12345, precision_mode="decimal", precision_digits=1), 12345.0)
        self.assertEqual(snap_value_to_precision(15000, precision_mode="integer", precision_digits=0), 15000.0)

if __name__ == "__main__":
    unittest.main()
