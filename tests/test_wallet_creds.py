import json
import os
import tempfile
import unittest
from pathlib import Path

from chain.wallets.get_creds import CredentialsError, get_mnemonic, load_wallet_json
from config.config_files import FileName

filename = FileName()


class TestWalletCreds(unittest.TestCase):
    def test_load_and_get_mnemonic(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wallet.json'
            phrase = 'abandon ' * 11 + 'about'
            path.write_text(
                json.dumps({filename.mnemonic_wallet_key: phrase}),
                encoding='utf-8',
            )
            os.environ['COSMOS_WALLET_FILE'] = str(path)
            self.assertEqual(get_mnemonic(), phrase)
            del os.environ['COSMOS_WALLET_FILE']

    def test_fallback_mnemonic_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'wallet.json'
            path.write_text(json.dumps({'mnemonic': 'test seed phrase here'}), encoding='utf-8')
            data = load_wallet_json(str(path))
            mnemonic = data.get('mnemonic')
            self.assertEqual(mnemonic, 'test seed phrase here')

    def test_missing_file(self):
        with self.assertRaises(CredentialsError):
            load_wallet_json('/nonexistent/wallet.json')


if __name__ == '__main__':
    unittest.main()
