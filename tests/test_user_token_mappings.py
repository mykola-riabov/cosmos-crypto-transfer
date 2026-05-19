import json
import tempfile
import unittest
from pathlib import Path

from project_utils.token_catalog import TokenCatalog
from project_utils.user_token_mappings import load_user_token_mappings, save_user_token_mapping


class TestUserTokenMappings(unittest.TestCase):
    def test_save_and_catalog_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'user_token_mappings.json')
            save_user_token_mapping(
                network='agoric',
                denom='ibc/ABC123',
                symbol='OSMO',
                decimals=6,
                also_denoms_book=False,
                path=path,
            )
            entries = load_user_token_mappings(path)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['symbol'], 'osmo')

            cat = TokenCatalog()
            cat._load_user_token_mappings = lambda: load_user_token_mappings(path)
            cat.reload()
            cat._register(
                'agoric',
                'ibc/ABC123',
                symbol='OSMO',
                decimals=6,
                source='user',
            )
            denom, dec = cat.resolve_denom('agoric', 'OSMO')
            self.assertEqual(denom, 'ibc/ABC123')
            self.assertEqual(dec, 6)


if __name__ == '__main__':
    unittest.main()
