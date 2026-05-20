import unittest
from unittest.mock import patch

from project_utils.wallet_derivation import resolve_wallet_attr


class TestWalletDerivation(unittest.TestCase):
    @patch('project_utils.wallet_profiles.get_active_wallet_id', return_value='w2')
    def test_resolve_wallet_attr(self, _mock_active):
        self.assertEqual(
            resolve_wallet_attr('wallet_1_osmosis_chain'),
            'w2_osmosis_chain',
        )


if __name__ == '__main__':
    unittest.main()
