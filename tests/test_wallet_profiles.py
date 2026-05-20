import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from project_utils import wallet_profiles as wp
from project_utils.wallet_ids import DEFAULT_WALLET_ID


class TestWalletProfiles(unittest.TestCase):
    def test_create_rename_active_delete(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wallet_profiles.json'
            with patch.object(wp, '_profiles_path', return_value=str(path)):
                with patch('chain.wallets.secret_vault.list_stored_wallet_ids', return_value=[]):
                    wp.save_profiles(wp._default_data())
                    wid2 = wp.create_wallet('Trading', key_type='mnemonic')
                self.assertEqual(wid2, 'w2')
                self.assertEqual(wp.get_active_wallet_id(), 'w2')
                wp.rename_wallet(wid2, 'My Trading')
                wp.set_active_wallet(DEFAULT_WALLET_ID)
                with patch('chain.wallets.secret_vault.list_stored_wallet_ids', return_value=['w1', 'w2']):
                    with patch('chain.wallets.secret_vault.has_wallet_secret', return_value=True):
                        with patch('chain.wallets.secret_vault.delete_wallet_secrets'):
                            wp.delete_wallet(wid2)
                self.assertNotIn(wid2, wp.load_profiles()['profiles'])

    def test_migrate_legacy_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wallet_profiles.json'
            path.write_text(
                '{"active_wallet_id": "wallet_2", "profiles": {"wallet_1": {"label": "A"}, "wallet_2": {"label": "B"}}}',
                encoding='utf-8',
            )
            with patch.object(wp, '_profiles_path', return_value=str(path)):
                data = wp.load_profiles()
                self.assertEqual(data['active_wallet_id'], 'w2')
                self.assertIn('w1', data['profiles'])


if __name__ == '__main__':
    unittest.main()
