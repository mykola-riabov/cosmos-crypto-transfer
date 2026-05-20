import unittest
from datetime import date

from gui.history_view import HISTORY_COLUMN_IDS, _route_display, filter_tx_history, parse_filter_date, row_values


class TestHistoryView(unittest.TestCase):
    def test_date_and_status_filter(self):
        rows = [
            {'time': '2026-05-19T10:00:00+00:00', 'status': 'success', 'source': 'a', 'destination': 'b'},
            {'time': '2026-05-20T10:00:00+00:00', 'status': 'failed', 'source': 'a', 'destination': 'c'},
            {'time': '2026-05-20T12:00:00+00:00', 'status': 'preview', 'source': 'x', 'destination': 'y'},
        ]
        out = filter_tx_history(
            rows,
            date_from=date(2026, 5, 20),
            date_to=date(2026, 5, 20),
            statuses={'failed', 'preview'},
        )
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0]['status'], 'failed')

    def test_parse_filter_date(self):
        self.assertEqual(parse_filter_date('2026-05-19'), date(2026, 5, 19))
        self.assertIsNone(parse_filter_date(''))

    def test_empty_status_set_shows_nothing(self):
        rows = [{'time': '2026-05-19T10:00:00+00:00', 'status': 'success'}]
        self.assertEqual(filter_tx_history(rows, statuses=set()), [])

    def test_route_display_swap(self):
        row = {'tx_kind': 'swap', 'source': 'osmosis', 'destination': 'osmosis'}
        self.assertEqual(_route_display(row), 'Swap · osmosis → osmosis')

    def test_row_values_full_column_order(self):
        row = {
            'time': 't1',
            'status': 'success',
            'symbol': 'OSMO',
            'amount': '1',
            'channel': 'channel-0',
            'timeout_mode': 'time',
            'timeout_value': '120',
            'tx_hash': 'ABC123',
            'error': 'oops',
        }
        vals = row_values(row)
        self.assertEqual(len(vals), len(HISTORY_COLUMN_IDS))
        self.assertEqual(vals[HISTORY_COLUMN_IDS.index('tx_hash')], 'ABC123')
        self.assertEqual(vals[HISTORY_COLUMN_IDS.index('error')], 'oops')


if __name__ == '__main__':
    unittest.main()
