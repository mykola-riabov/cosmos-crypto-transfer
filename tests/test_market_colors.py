import unittest

from gui.market_colors import change_row_tag, format_signed_change


class TestMarketColors(unittest.TestCase):
    def test_change_row_tag_levels(self):
        self.assertEqual(change_row_tag(5.0, 10.0), 'chg_pos_2')
        self.assertEqual(change_row_tag(-8.0, 10.0), 'chg_neg_4')
        self.assertEqual(change_row_tag(0.0, 10.0), 'chg_zero')

    def test_format_signed_change(self):
        self.assertEqual(format_signed_change(1.5), '+1.5')
        self.assertEqual(format_signed_change(-2), '-2')


if __name__ == '__main__':
    unittest.main()
