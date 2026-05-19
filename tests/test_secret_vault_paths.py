import os
import unittest
from unittest.mock import patch

from config.config_path import ConfigPath


class TestSecretVaultPaths(unittest.TestCase):
    def test_source_inside_project(self):
        self.assertTrue(ConfigPath.source_path.startswith(ConfigPath.project_path))
        self.assertIn('source', ConfigPath.source_path)

    def test_secrets_under_home(self):
        self.assertIn('.market_ai_secrets', ConfigPath.secrets_path)
        self.assertTrue(ConfigPath.secrets_path.endswith(ConfigPath.secrets_slug))

    @patch.dict(os.environ, {'MARKET_AI_SECRETS_SLUG': 'custom-slug'})
    def test_secrets_slug_override(self):
        from importlib import reload

        import config.config_path as cp

        reload(cp)
        self.assertIn('custom-slug', cp.ConfigPath.secrets_path)
        reload(cp)  # restore for other tests


if __name__ == '__main__':
    unittest.main()
