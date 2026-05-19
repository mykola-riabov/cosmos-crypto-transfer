import json
import tempfile
import unittest
from pathlib import Path

from project_utils.ibc_route_builder import build_routes_for_enabled, routes_for_pair


SAMPLE_IBC = {
    '$schema': '../ibc_data.schema.json',
    'chain_1': {
        'chain_name': 'cosmoshub',
        'chain_id': 'cosmoshub-4',
    },
    'chain_2': {
        'chain_name': 'osmosis',
        'chain_id': 'osmosis-1',
    },
    'channels': [
        {
            'chain_1': {'channel_id': 'channel-141', 'port_id': 'transfer'},
            'chain_2': {'channel_id': 'channel-0', 'port_id': 'transfer'},
            'ordering': 'unordered',
            'version': 'ics20-1',
            'tags': {'preferred': True, 'status': 'ACTIVE'},
        }
    ],
}


class TestIbcRouteBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ibc_dir = Path(self.tmp.name)
        path = self.ibc_dir / 'cosmoshub-osmosis.json'
        path.write_text(json.dumps(SAMPLE_IBC), encoding='utf-8')

    def tearDown(self):
        self.tmp.cleanup()

    def test_routes_for_pair_bidirectional(self):
        routes = routes_for_pair('osmosis', 'cosmoshub', ibc_dir=str(self.ibc_dir))
        self.assertEqual(len(routes), 2)
        by_dest = {r['destination_network']: r for r in routes}
        self.assertEqual(by_dest['cosmoshub']['channel'], 'channel-0')
        self.assertEqual(by_dest['osmosis']['channel'], 'channel-141')
        self.assertEqual(by_dest['cosmoshub']['sender_wallet'], 'wallet_1_osmosis')

    def test_build_for_enabled_pair(self):
        routes = build_routes_for_enabled(['osmosis', 'cosmoshub'], ibc_dir=str(self.ibc_dir))
        self.assertEqual(len(routes), 2)

    def test_missing_pair_returns_empty(self):
        routes = routes_for_pair('osmosis', 'nonexistent-chain', ibc_dir=str(self.ibc_dir))
        self.assertEqual(routes, [])


if __name__ == '__main__':
    unittest.main()
