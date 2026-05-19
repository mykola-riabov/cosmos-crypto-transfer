import unittest
from unittest.mock import MagicMock, patch

from project_utils.ibc_denom_resolver import fetch_denom_trace, normalize_ibc_denom
from project_utils.token_catalog import TokenCatalog


class TestIbcDenomResolver(unittest.TestCase):
    def test_normalize_ibc_denom_uppercase(self):
        self.assertEqual(
            normalize_ibc_denom('ibc/0471f1c4e7afd3f07702e758de59817b'),
            'ibc/0471F1C4E7AFD3F07702E758DE59817B',
        )

    @patch('project_utils.ibc_denom_resolver.requests.get')
    def test_fetch_tries_v1_when_v1beta1_fails(self, mock_get):
        ibc = 'ibc/0471F1C4E7AFD3F07702E758DE59817B'
        fail = MagicMock(status_code=501)
        ok = MagicMock(status_code=200)
        ok.json.return_value = {'denom_trace': {'path': 'transfer/channel-1', 'base_denom': 'uosmo'}}
        mock_get.side_effect = [fail, ok]
        trace = fetch_denom_trace('https://agoric.example', ibc)
        self.assertEqual(trace['base_denom'], 'uosmo')
        self.assertEqual(mock_get.call_count, 2)

    def test_register_ibc_osmo_on_agoric(self):
        cat = TokenCatalog()
        cat._register('osmosis', 'uosmo', symbol='OSMO', decimals=6)
        ibc = 'ibc/0471F1C4E7AFD3F07702E758DE59817B'
        cat.register_ibc_resolution('agoric', ibc, 'uosmo', persist=False)
        denom, dec = cat.resolve_denom('agoric', 'OSMO')
        self.assertEqual(denom, ibc)
        self.assertEqual(dec, 6)
        self.assertEqual(cat.label_for_denom('agoric', ibc), 'OSMO')


if __name__ == '__main__':
    unittest.main()
