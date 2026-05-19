import unittest

from project_utils.ibc_routes import filter_routes_by_enabled, routes_by_source


class TestIbcRoutesEnabledFilter(unittest.TestCase):
    def test_filter_destinations_by_enabled(self):
        grouped = {
            'osmosis': [
                {'source_network': 'osmosis', 'destination_network': 'crescent'},
                {'source_network': 'osmosis', 'destination_network': 'cosmoshub'},
                {'source_network': 'osmosis', 'destination_network': 'noble'},
            ],
            'bostrom': [
                {'source_network': 'bostrom', 'destination_network': 'osmosis'},
            ],
        }
        enabled = {'osmosis', 'cosmoshub', 'noble'}
        out = filter_routes_by_enabled(grouped, enabled)
        self.assertEqual(set(out.keys()), {'osmosis'})
        dests = {r['destination_network'] for r in out['osmosis']}
        self.assertEqual(dests, {'cosmoshub', 'noble'})
        self.assertNotIn('crescent', dests)
        self.assertNotIn('bostrom', out)

    def test_real_routes_respect_enabled_subset(self):
        grouped = routes_by_source()
        enabled = {'osmosis', 'cosmoshub', 'noble'}
        out = filter_routes_by_enabled(grouped, enabled)
        for src, routes in out.items():
            self.assertIn(src, enabled)
            for route in routes:
                self.assertIn(route['destination_network'], enabled)


if __name__ == '__main__':
    unittest.main()
