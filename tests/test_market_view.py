import unittest

from gui.market_view import (
    MARKET_COLUMN_IDS,
    market_row_display_values,
    normalize_column_widths,
    normalize_sort_column,
    normalize_visible_columns,
)


class TestMarketView(unittest.TestCase):
    def test_normalize_visible_preserves_order(self):
        out = normalize_visible_columns(['price', 'symbol', 'bad'])
        self.assertEqual(out, ['price', 'symbol'])

    def test_normalize_sort_column(self):
        self.assertEqual(normalize_sort_column('chg24'), 'chg24')
        self.assertEqual(normalize_sort_column('nope'), 'volume')

    def test_normalize_column_widths_clamps(self):
        w = normalize_column_widths({'symbol': 10, 'price': 9999})
        self.assertEqual(w['symbol'], 40)
        self.assertEqual(w['price'], 800)

    def test_row_values_length_matches_columns(self):
        row = {
            'symbol': 'X',
            'denom': 'd',
            'price': 1.0,
            '_liquidity_fmt': '1',
            '_volume_fmt': '2',
            'price_24h_change': 0.5,
            'price_7d_change': -1.0,
        }
        vals = market_row_display_values(row)
        self.assertEqual(len(vals), len(MARKET_COLUMN_IDS))


if __name__ == '__main__':
    unittest.main()
