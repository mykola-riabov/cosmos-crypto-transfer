import json
import tempfile
import unittest
from unittest.mock import patch

from gui.settings import DEFAULT_SETTINGS, load_settings


class TestGuiSettingsMigration(unittest.TestCase):
    def test_minutes_to_seconds_migration(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = f'{tmp}/gui_settings.json'
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(
                    {
                        'tokens_auto_refresh_minutes': 5,
                        'market_auto_refresh_minutes': 2,
                    },
                    f,
                )
            with patch('gui.settings._settings_path', return_value=path):
                merged = load_settings()
        self.assertEqual(merged['tokens_auto_refresh_seconds'], 300)
        self.assertEqual(merged['market_auto_refresh_seconds'], 120)

    def test_seconds_not_overwritten_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = f'{tmp}/gui_settings.json'
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(
                    {
                        'tokens_auto_refresh_seconds': 90,
                        'tokens_auto_refresh_minutes': 60,
                    },
                    f,
                )
            with patch('gui.settings._settings_path', return_value=path):
                merged = load_settings()
        self.assertEqual(merged['tokens_auto_refresh_seconds'], 90)

    def test_default_has_seconds_keys(self):
        self.assertIn('tokens_auto_refresh_seconds', DEFAULT_SETTINGS)
        self.assertIn('market_auto_refresh_seconds', DEFAULT_SETTINGS)


if __name__ == '__main__':
    unittest.main()
