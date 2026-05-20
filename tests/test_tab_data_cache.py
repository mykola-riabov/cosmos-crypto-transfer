import json
import os
import tempfile
import unittest
from unittest.mock import patch

from project_utils import tab_data_cache


class TestTabDataCache(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(tab_data_cache, 'cache_dir', return_value=tmp):
                tab_data_cache.save_tab_cache(
                    'tokens',
                    'osmosis',
                    {'rows': [{'symbol': 'OSMO'}], 'meta': {}},
                )
                env = tab_data_cache.load_tab_cache('tokens', 'osmosis')
            self.assertIsNotNone(env)
            self.assertIn('cached_at', env)
            self.assertEqual(env['payload']['rows'][0]['symbol'], 'OSMO')
            path = os.path.join(tmp, 'tokens__osmosis.json')
            self.assertTrue(os.path.isfile(path))
            with open(path, encoding='utf-8') as f:
                raw = json.load(f)
            self.assertIn('cached_at_iso', raw)


if __name__ == '__main__':
    unittest.main()
