import json
import os
import tempfile
import unittest

from project_utils.create_check_data.collect_data.json.json_scanner import traverse_directory_chain_data


class TestJsonScannerMerge(unittest.TestCase):
    def test_merge_keplr_without_chain_name_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            registry = os.path.join(tmp, 'chain-registry')
            keplr = os.path.join(tmp, 'keplr')
            os.makedirs(os.path.join(registry, 'osmosis'))
            os.makedirs(os.path.join(keplr, 'osmosis'))
            out = os.path.join(tmp, 'out.json')

            with open(os.path.join(registry, 'osmosis', 'chain.json'), 'w', encoding='utf-8') as f:
                json.dump(
                    {
                        '$schema': '../chain.schema.json',
                        'chain_name': 'osmosis',
                        'chain_id': 'osmosis-1',
                        'network_type': 'mainnet',
                        'status': 'live',
                        'bech32_prefix': 'osmo',
                        'fees': {'fee_tokens': [{'denom': 'uosmo', 'low_gas_price': 0.01}]},
                        'apis': {'rest': [{'address': 'https://lcd.osmosis.zone'}]},
                    },
                    f,
                )
            with open(os.path.join(keplr, 'osmosis', 'foo.json'), 'w', encoding='utf-8') as f:
                json.dump({'chainId': 'osmosis-1', 'rest': 'https://keplr.example'}, f)

            traverse_directory_chain_data(
                registry,
                keplr,
                out,
                ['chain_name', 'chain_id', 'bech32_prefix', 'denom'],
                ['chainId', 'rest'],
                ['osmosis-1'],
                verify_rest=False,
            )
            with open(out, encoding='utf-8') as f:
                data = json.load(f)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['chain_name'], 'osmosis')
            self.assertEqual(data[0]['keplr_rest_link'], 'https://keplr.example')


if __name__ == '__main__':
    unittest.main()
