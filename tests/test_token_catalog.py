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

    def test_denoms_book_symbol_not_overwritten_by_registry(self):
        ibc = 'ibc/498A0751C798A0D9A389AA3691123DADA57DAA4FE165D5C75894505B876BA6E4'
        cat = TokenCatalog()
        cat._register('osmosis', ibc, symbol='usdc_noble', decimals=6, source='denoms_book')
        cat._register('osmosis', ibc, symbol='USDC', decimals=6, source='registry')
        row = cat.get_row('osmosis', ibc)
        self.assertEqual(row.get('symbol'), 'usdc_noble')
        self.assertEqual(row.get('source'), 'denoms_book')
        self.assertEqual(cat.symbol_for_denom('osmosis', ibc), 'usdc_noble')

    def test_registry_fills_decimals_when_denoms_has_symbol_only(self):
        ibc = 'ibc/0471F1C4E7AFD3F07702BEF6DC365268D64570F7C1FDC98EA6098DD6DE59817B'
        cat = TokenCatalog()
        cat._register('osmosis', ibc, symbol='my_osmo', decimals=None, source='denoms_book')
        cat._register('osmosis', ibc, symbol='OSMO', decimals=6, source='registry')
        row = cat.get_row('osmosis', ibc)
        self.assertEqual(row.get('symbol'), 'my_osmo')
        self.assertEqual(row.get('decimals'), 6)


if __name__ == '__main__':
    unittest.main()
