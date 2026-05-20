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
    # Reuse on-chain balance snapshot for Portfolio / Send (seconds); 0 = always fetch
    'balance_cache_seconds': 30,
    'show_fiat_prices': True,
    # Send: 'nonzero' = tokens with balance on source; 'all' = full catalog
    'send_token_list_mode': 'nonzero',
    # Address book: show every wallet in file vs active wallet only
    'address_book_all_wallets': False,
    # Receive tab: same scope (active wallet vs all wallets in address book)
    'receive_all_wallets': False,
    'history_visible_columns': None,
    'history_status_filter': None,
    # Market tab: subset of column ids (order = display order); None = all default order
    'market_visible_columns': None,
    'market_sort_column': 'volume',
    'market_sort_reverse': True,
    # Market: {column_id: width_px}; None = defaults from MARKET_COLUMN_LAYOUT
    'market_column_widths': None,
    # Market: False = all loaded rows; True = only liquidity > 0
    'market_liquidity_only': False,
    'tokens_auto_refresh': False,
    'market_auto_refresh': False,
    # Auto-refresh interval when enabled (seconds); min 30, max 86400
    'tokens_auto_refresh_seconds': 3600,
    'market_auto_refresh_seconds': 3600,
    # Market Numia rows: 'all' = full sorted list; 'limit' = top N by 24h volume
    'market_tokens_limit_mode': 'limit',
    'market_tokens_limit_count': 500,
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
        # Migrate legacy minute-based intervals (only if seconds absent in file)
        if isinstance(data, dict):
            if 'tokens_auto_refresh_seconds' not in data and 'tokens_auto_refresh_minutes' in data:
                try:
                    merged['tokens_auto_refresh_seconds'] = max(
                        30,
                        min(86400, int(data['tokens_auto_refresh_minutes']) * 60),
                    )
                except (TypeError, ValueError):
                    pass
            if 'market_auto_refresh_seconds' not in data and 'market_auto_refresh_minutes' in data:
                try:
                    merged['market_auto_refresh_seconds'] = max(
                        30,
                        min(86400, int(data['market_auto_refresh_minutes']) * 60),
                    )
                except (TypeError, ValueError):
                    pass
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
