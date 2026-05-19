import unittest
from unittest.mock import MagicMock, patch

from chain.wallets.get_creds import (
    CredentialsError,
    get_mnemonic,
    is_placeholder_mnemonic,
    mnemonic_is_configured,
    require_configured_mnemonic,
)


class TestWalletCreds(unittest.TestCase):
    def test_placeholder_mnemonic(self):
        phrase = 'word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12'
        self.assertTrue(is_placeholder_mnemonic(phrase))
        self.assertFalse(is_placeholder_mnemonic('abandon ' * 11 + 'about'))

    @patch('chain.wallets.secret_vault.get_mnemonic', return_value='abandon ' * 11 + 'about')
    @patch('chain.wallets.get_creds.get_status')
    def test_get_mnemonic_from_vault(self, mock_status, mock_vault_mnemonic):
        mock_status.return_value = MagicMock(vault_initialized=True)
        self.assertEqual(get_mnemonic(), 'abandon ' * 11 + 'about')
        mock_vault_mnemonic.assert_called_once()

    @patch('chain.wallets.get_creds.get_status')
    def test_no_vault_raises(self, mock_status):
        mock_status.return_value = MagicMock(vault_initialized=False)
        with self.assertRaises(CredentialsError):
            get_mnemonic()
        with self.assertRaises(CredentialsError):
            require_configured_mnemonic()

    @patch('chain.wallets.secret_vault.mnemonic_is_configured', return_value=True)
    @patch('chain.wallets.get_creds.get_status')
    def test_mnemonic_is_configured(self, mock_status, mock_vault_configured):
        mock_status.return_value = MagicMock(vault_initialized=True)
        self.assertTrue(mnemonic_is_configured())
        mock_vault_configured.assert_called_once()

    @patch('chain.wallets.get_creds.get_status')
    def test_mnemonic_not_configured_without_vault(self, mock_status):
        mock_status.return_value = MagicMock(vault_initialized=False)
        self.assertFalse(mnemonic_is_configured())


if __name__ == '__main__':
    unittest.main()
