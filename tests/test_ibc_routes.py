import json
import unittest
from pathlib import Path

ROUTES_FILE = Path(__file__).resolve().parents[1] / 'config' / 'ibc_routes.json'
REQUIRED_KEYS = {
    'source_network',
    'destination_network',
    'sender_wallet',
    'receiver_wallet',
    'channel',
    'gas',
    'timeout_seconds',
    'client_attr',
    'wallet_attr',
}


class TestIbcRoutes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(ROUTES_FILE, encoding='utf-8') as f:
            cls.routes = json.load(f)['routes']

    def test_routes_count(self):
        self.assertGreaterEqual(len(self.routes), 60)

    def test_required_fields(self):
        for i, route in enumerate(self.routes):
            missing = REQUIRED_KEYS - route.keys()
            self.assertFalse(missing, f'route[{i}] missing keys: {missing}')

    def test_channel_format(self):
        for route in self.routes:
            self.assertTrue(
                route['channel'].startswith('channel-'),
                route,
            )

    def test_wallet_names_consistent(self):
        for route in self.routes:
            self.assertTrue(route['sender_wallet'].startswith('wallet_1_'))
            self.assertTrue(route['receiver_wallet'].startswith('wallet_1_'))
            src = route['sender_wallet'].replace('wallet_1_', '')
            self.assertEqual(route['source_network'], src)

    def test_no_duplicate_routes(self):
        keys = [
            (r['source_network'], r['destination_network'], r['channel'])
            for r in self.routes
        ]
        self.assertEqual(len(keys), len(set(keys)))


if __name__ == '__main__':
    unittest.main()
