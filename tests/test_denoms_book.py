import json
import tempfile
import unittest
from pathlib import Path

from project_utils.denoms_book import delete_entry, load_entries, upsert_entry
from project_utils.token_catalog import TokenCatalog


class TestDenomsBook(unittest.TestCase):
    def test_upsert_load_and_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = str(Path(tmp) / 'denoms_book.json')
            upsert_entry('agoric', 'OSMO', 'ibc/ABC123', 6, path=path)
            entries = load_entries(path, migrate_legacy=False)
            self.assertEqual(len(entries), 1)
            self.assertEqual(entries[0]['symbol'], 'osmo')

            cat = TokenCatalog()
            cat.reload()
            for item in load_entries(path, migrate_legacy=False):
                cat._register(
                    item.get('network', ''),
                    item.get('denom_contract', ''),
                    symbol=item.get('symbol'),
                    decimals=item.get('decimal'),
                    source='denoms_book',
                )
            denom, dec = cat.resolve_denom('agoric', 'OSMO')
            self.assertEqual(denom, 'ibc/ABC123')
            self.assertEqual(dec, 6)

            self.assertTrue(delete_entry('agoric', 'ibc/ABC123', path=path))
            self.assertEqual(len(load_entries(path, migrate_legacy=False)), 0)


if __name__ == '__main__':
    unittest.main()
