"""The flawed pipeline's own tests. They all pass, which is exactly the problem."""
import csv
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from demo_flawed import clean  # noqa: E402


class HappyPath(unittest.TestCase):
    def test_clean_file_loads(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "orders.csv")
        with open(path, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        out = clean(rows)
        self.assertEqual(len(out), 40)
        self.assertIsInstance(out[0]["amount"], float)
        self.assertRegex(out[0]["order_date"], r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    unittest.main()
