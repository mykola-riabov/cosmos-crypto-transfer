import json
import os
import tempfile
import unittest

from project_utils.tx_history import append_tx_record, load_tx_history


class TestTxHistory(unittest.TestCase):
    def test_append_swap_kind(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'tx_history.json')
            append_tx_record(
                status='preview',
                source='osmosis',
                destination='osmosis',
                symbol='OSMO→USDC',
                amount='0.01',
                gas=600000,
                channel='skip-swap',
                tx_kind='swap',
                path=path,
            )
            rows = load_tx_history(path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['tx_kind'], 'swap')
            self.assertEqual(rows[0]['channel'], 'skip-swap')


if __name__ == '__main__':
    unittest.main()
