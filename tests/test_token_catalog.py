import unittest

from project_utils.token_catalog import TokenCatalog


class TestTokenCatalog(unittest.TestCase):
    def test_format_amount(self):
        cat = TokenCatalog()
        cat._register('osmosis', 'uosmo', symbol='OSMO', decimals=6)
        self.assertEqual(cat.format_amount('1500000', 'osmosis', 'uosmo'), '1.5 OSMO')

    def test_resolve_symbol(self):
        cat = TokenCatalog()
        cat._register('noble', 'uusdc', symbol='USDC', decimals=6)
        denom, dec = cat.resolve_denom('noble', 'usdc')
        self.assertEqual(denom, 'uusdc')
        self.assertEqual(dec, 6)


if __name__ == '__main__':
    unittest.main()
