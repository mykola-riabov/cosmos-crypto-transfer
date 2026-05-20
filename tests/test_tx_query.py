import unittest
from unittest.mock import patch

from project_utils.tx_query import (
    TxNotFoundYet,
    fetch_tx_by_hash,
    normalize_tx_hash,
    wait_for_tx_rest,
)


class TestTxQuery(unittest.TestCase):
    def test_normalize_tx_hash(self):
        self.assertEqual(normalize_tx_hash('0xabc'), 'ABC')
        self.assertEqual(normalize_tx_hash('AbCd'), 'ABCD')

    @patch('project_utils.tx_query.requests.get')
    def test_fetch_tx_success(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            'tx_response': {
                'code': 0,
                'raw_log': '[]',
                'gas_wanted': '500000',
                'gas_used': '400000',
            },
        }
        result = fetch_tx_by_hash('https://lcd-osmosis.example', 'ABC')
        self.assertTrue(result.is_successful)
        self.assertEqual(result.gas_used, 400000)

    @patch('project_utils.tx_query.requests.get')
    def test_fetch_tx_not_found(self, mock_get):
        mock_get.return_value.status_code = 404
        with self.assertRaises(TxNotFoundYet):
            fetch_tx_by_hash('https://lcd-osmosis.example', 'ABC')

    @patch('project_utils.tx_query.time.sleep', return_value=None)
    @patch('project_utils.tx_query.fetch_tx_by_hash')
    def test_wait_for_tx_rest(self, mock_fetch, _sleep):
        from project_utils.tx_query import TxQueryResult

        mock_fetch.side_effect = [
            TxNotFoundYet('ABC'),
            TxQueryResult(code=0, raw_log='', gas_wanted=1, gas_used=1, tx_hash='ABC'),
        ]
        result = wait_for_tx_rest('https://lcd-osmosis.example', 'abc', timeout_sec=10, poll_sec=0)
        self.assertTrue(result.is_successful)


if __name__ == '__main__':
    unittest.main()
