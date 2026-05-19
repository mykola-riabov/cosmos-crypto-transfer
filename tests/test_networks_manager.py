import json
import os
import tempfile
import unittest
from unittest.mock import patch

from project_utils.networks_manager import (
    DEFAULT_ENABLED_NETWORKS,
    ensure_enabled_networks_file,
    filter_chains_by_enabled,
    get_enabled_networks,
    load_enabled_config,
    reset_enabled_to_defaults,
    save_enabled_config,
    set_enabled_networks,
)


class TestNetworksManager(unittest.TestCase):
    def test_default_enabled_networks(self):
        self.assertEqual(DEFAULT_ENABLED_NETWORKS, ('osmosis', 'cosmoshub'))

    def test_ensure_and_save_enabled(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'enabled_networks.json')
            ensure_enabled_networks_file(path)
            cfg = load_enabled_config(path)
            self.assertEqual(set(cfg['enabled']), set(DEFAULT_ENABLED_NETWORKS))
            set_enabled_networks(['osmosis', 'juno'], path)
            self.assertEqual(get_enabled_networks(path), {'osmosis', 'juno'})
            reset_enabled_to_defaults(path)
            self.assertEqual(get_enabled_networks(path), set(DEFAULT_ENABLED_NETWORKS))

    def test_filter_chains(self):
        chains = [
            {'chain_name': 'osmosis'},
            {'chain_name': 'juno'},
            {'chain_name': 'noble'},
        ]
        filtered = filter_chains_by_enabled(chains, {'osmosis', 'noble'})
        self.assertEqual([c['chain_name'] for c in filtered], ['osmosis', 'noble'])

    @patch('project_utils.networks_manager.requests.get')
    def test_probe_rest_ok(self, mock_get):
        from project_utils.networks_manager import probe_rest

        mock_get.return_value.status_code = 200
        ok, err = probe_rest('https://lcd.osmosis.zone')
        self.assertTrue(ok)
        self.assertIsNone(err)

    @patch('project_utils.networks_manager.requests.get')
    def test_probe_rest_fail(self, mock_get):
        from project_utils.networks_manager import probe_rest
        import requests

        mock_get.side_effect = requests.ConnectionError('down')
        ok, err = probe_rest('https://invalid.example')
        self.assertFalse(ok)
        self.assertIn('down', err)


if __name__ == '__main__':
    unittest.main()
