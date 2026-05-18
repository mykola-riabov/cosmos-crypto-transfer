import unittest

from project_utils.ibc_routes import find_route, load_ibc_routes, routes_by_source


class TestIbcRoutesLoader(unittest.TestCase):
    def test_load_and_group(self):
        routes = load_ibc_routes()
        grouped = routes_by_source(routes)
        self.assertGreaterEqual(len(routes), 60)
        self.assertIn('agoric', grouped)
        self.assertTrue(any(r['destination_network'] == 'osmosis' for r in grouped['agoric']))

    def test_find_route(self):
        route = find_route('agoric', 'osmosis')
        self.assertIsNotNone(route)
        self.assertEqual(route['channel'], 'channel-1')

    def test_find_missing(self):
        self.assertIsNone(find_route('agoric', 'nonexistent-chain-xyz'))


if __name__ == '__main__':
    unittest.main()
