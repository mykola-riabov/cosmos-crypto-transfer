"""Persistent GUI preferences (theme, layout, custom colors)."""
import copy
import json
import os
from typing import Any, Dict

from config.config_path import ConfigPath
from gui.theme import DEFAULT_THEME, default_custom_colors


DEFAULT_SETTINGS: Dict[str, Any] = {
    'theme': DEFAULT_THEME,
    'show_log_panel': True,
    'custom_colors': default_custom_colors(),
    'ledger_link_type': 'keplr_rest_link',
    'auto_refresh_balances': True,
    'balance_refresh_seconds': 60,
    'show_fiat_prices': True,
    # Send: 'nonzero' = tokens with balance on source; 'all' = full catalog
    'send_token_list_mode': 'nonzero',
}


def _settings_path() -> str:
    data_dir = ConfigPath.data_path
    if os.path.isdir(data_dir):
        return os.path.join(data_dir, 'gui_settings.json')
    return os.path.join(ConfigPath.root_config_path, 'gui_settings.json')


def load_settings() -> Dict[str, Any]:
    path = _settings_path()
    if not os.path.isfile(path):
        return copy.deepcopy(DEFAULT_SETTINGS)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        merged = copy.deepcopy(DEFAULT_SETTINGS)
        for key in DEFAULT_SETTINGS:
            if key in data:
                merged[key] = data[key]
        if isinstance(merged.get('custom_colors'), dict):
            base = default_custom_colors()
            base.update(merged['custom_colors'])
            merged['custom_colors'] = base
        return merged
    except (OSError, json.JSONDecodeError, TypeError):
        return copy.deepcopy(DEFAULT_SETTINGS)


def save_settings(settings: Dict[str, Any]) -> str:
    path = _settings_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = copy.deepcopy(DEFAULT_SETTINGS)
    for key in DEFAULT_SETTINGS:
        if key in settings:
            payload[key] = settings[key]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    return path
