import unittest
from unittest.mock import patch

from action_crypto.bank.balance_query import BalanceRow
from gui import services
from project_utils.data_cache import get_cache


class TestBalanceCache(unittest.TestCase):
    def setUp(self):
        services.invalidate_balance_cache()

    def test_fetch_balances_uses_cache(self):
        row = BalanceRow('w1', 'osmosis', 'addr', 'uosmo', '1000')

        with patch('gui.services.query_all_balances', return_value=([row], [])) as mock_q:
            with patch('gui.services.get_wallet_networks', return_value=['osmosis']):
                with patch('gui.services.get_paths') as mock_paths:
                    mock_paths.return_value.ledger_client_mapping = '/m.json'
                    mock_paths.return_value.address_book = '/a.json'
                    with patch('os.path.isfile', return_value=True):
                        with patch(
                            'project_utils.wallet_profiles.get_active_wallet_id',
                            return_value='w1',
                        ):
                            with patch(
                                'gui.services.balance_cache_ttl_seconds',
                                return_value=60.0,
                            ):
                                r1, _ = services.fetch_balances()
                                r2, _ = services.fetch_balances()
        self.assertEqual(len(r1), 1)
        self.assertEqual(r1[0].amount, '1000')
        self.assertEqual(len(r2), 1)
        self.assertEqual(mock_q.call_count, 1)

    def test_force_bypasses_cache(self):
        row = BalanceRow('w1', 'osmosis', 'addr', 'uosmo', '1')

        with patch('gui.services.query_all_balances', return_value=([row], [])) as mock_q:
            with patch('gui.services.get_wallet_networks', return_value=['osmosis']):
                with patch('gui.services.get_paths') as mock_paths:
                    mock_paths.return_value.ledger_client_mapping = '/m.json'
                    mock_paths.return_value.address_book = '/a.json'
                    with patch('os.path.isfile', return_value=True):
                        with patch(
                            'project_utils.wallet_profiles.get_active_wallet_id',
                            return_value='w1',
                        ):
                            with patch(
                                'gui.services.balance_cache_ttl_seconds',
                                return_value=60.0,
                            ):
                                services.fetch_balances()
                                services.fetch_balances(force=True)
        self.assertEqual(mock_q.call_count, 2)

    def test_filter_subset_from_cached_snapshot(self):
        rows = [
            BalanceRow('w1', 'osmosis', 'a1', 'uosmo', '1'),
            BalanceRow('w1', 'cosmos', 'a2', 'uatom', '2'),
        ]

        with patch('gui.services.query_all_balances', return_value=(rows, [])):
            with patch('gui.services.get_wallet_networks', return_value=['osmosis', 'cosmos']):
                with patch('gui.services.get_paths') as mock_paths:
                    mock_paths.return_value.ledger_client_mapping = '/m.json'
                    mock_paths.return_value.address_book = '/a.json'
                    with patch('os.path.isfile', return_value=True):
                        with patch(
                            'project_utils.wallet_profiles.get_active_wallet_id',
                            return_value='w1',
                        ):
                            with patch(
                                'gui.services.balance_cache_ttl_seconds',
                                return_value=60.0,
                            ):
                                services.fetch_balances()
                                filtered, _ = services.fetch_balances(networks={'osmosis'})
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].network, 'osmosis')

    def test_invalidate_clears_named_cache(self):
        cache = get_cache('balances')
        cache.set('k', 'v', ttl=60)
        services.invalidate_balance_cache()
        self.assertIsNone(cache.get('k'))


if __name__ == '__main__':
    unittest.main()
