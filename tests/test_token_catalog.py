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

    def test_resolve_coingecko_id_from_other_chain(self):
        cat = TokenCatalog()
        ibc = 'ibc/0471F1C4E7AFD3F07702BEF6DC365268D64570F7C1FDC98EA6098DD6DE59817B'
        cat._register('osmosis', 'uosmo', symbol='OSMO', decimals=6, coingecko_id='osmosis')
        cat._register('agoric', ibc, symbol='osmo', decimals=6)
        self.assertEqual(cat.resolve_coingecko_id('agoric', ibc), 'osmosis')

    def test_resolve_coingecko_id_fallback_ticker(self):
        cat = TokenCatalog()
        cat._register('agoric', 'ubld', symbol='BLD', decimals=6)
        self.assertEqual(cat.resolve_coingecko_id('agoric', 'ubld'), 'agoric')


if __name__ == '__main__':
    unittest.main()
