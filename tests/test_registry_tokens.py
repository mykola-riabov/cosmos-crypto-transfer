import json
import os
import tempfile
import unittest
from project_utils.create_check_data.collect_data.json.collect_assets import parse_asset
from project_utils.registry_tokens import (
    _token_matches_symbol_filter,
    enrich_with_osmosis_prices,
    load_registry_tokens,
    match_osmosis_price,
    token_display_rows,
)


class TestRegistryTokens(unittest.TestCase):
    def test_parse_asset_native(self):
        row = parse_asset(
            {
                'base': 'uosmo',
                'symbol': 'OSMO',
                'display': 'osmo',
                'name': 'Osmosis',
                'denom_units': [
                    {'denom': 'uosmo', 'exponent': 0},
                    {'denom': 'osmo', 'exponent': 6},
                ],
            },
            'osmosis',
        )
        self.assertEqual(row['denom'], 'uosmo')
        self.assertEqual(row['decimals'], 6)

    def test_load_registry_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'assets_registry.json')
            payload = {
                'tokens': [
                    {
                        'chain_name': 'noble',
                        'symbol': 'USDC',
                        'display': 'usdc',
                        'denom': 'uusdc',
                        'decimals': 6,
                        'name': 'USD Coin',
                        'contract': '',
                    }
                ]
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f)
            tokens = load_registry_tokens(path)
            self.assertEqual(len(tokens), 1)
            self.assertEqual(tokens[0]['chain_name'], 'noble')

    def test_match_osmosis_price_by_denom(self):
        token = {'denom': 'uosmo', 'display': 'osmo', 'symbol': 'OSMO'}
        market = {
            'by_denom': {'uosmo': {'price': 1.23, 'denom': 'uosmo'}},
            'by_display': {},
            'by_symbol': {},
        }
        matched = match_osmosis_price(token, market)
        self.assertEqual(matched['price'], 1.23)

    def test_symbol_filter_matches_ticker_not_denom(self):
        self.assertTrue(_token_matches_symbol_filter({'symbol': 'OSMO', 'display': 'osmo'}, 'osmo'))
        self.assertFalse(
            _token_matches_symbol_filter(
                {'symbol': 'ATOM', 'denom': 'ibc/DEADBEEFOSMOHASH'},
                'osmo',
            )
        )

    def test_token_display_rows_symbol_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'assets_registry.json')
            payload = {
                'tokens': [
                    {'chain_name': 'osmosis', 'symbol': 'OSMO', 'display': 'osmo', 'denom': 'uosmo', 'decimals': 6},
                    {'chain_name': 'cosmoshub', 'symbol': 'ATOM', 'display': 'atom', 'denom': 'uatom', 'decimals': 6},
                ]
            }
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f)
            import project_utils.registry_tokens as reg_mod

            old_loader = reg_mod.load_registry_tokens
            reg_mod.load_registry_tokens = lambda p=None: old_loader(path)
            try:
                rows, meta = token_display_rows(
                    chain_name='osmosis',
                    symbol_filter='osmo',
                    with_osmosis_prices=False,
                )
            finally:
                reg_mod.load_registry_tokens = old_loader
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['symbol'], 'OSMO')
            self.assertEqual(meta['shown'], 1)

    def test_enrich_with_prices(self):
        tokens = [{'chain_name': 'osmosis', 'denom': 'uosmo', 'display': 'osmo', 'symbol': 'OSMO'}]
        market = {
            'by_denom': {'uosmo': {'price': 2.5, 'liquidity': 1000, 'volume_24h': 50}},
            'by_display': {},
            'by_symbol': {},
        }
        rows = enrich_with_osmosis_prices(tokens, market=market)
        self.assertEqual(rows[0]['price'], 2.5)
        self.assertEqual(rows[0]['liquidity'], 1000)


if __name__ == '__main__':
    unittest.main()
