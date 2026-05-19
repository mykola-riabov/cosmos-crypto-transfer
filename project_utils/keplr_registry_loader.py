"""Load token metadata from cloned chainapsis/keplr-chain-registry (Keplr ChainInfo JSON)."""

from __future__ import annotations

import json
import os
from typing import Iterable, List

from config.config_path import ConfigPath


def _chain_name_from_keplr(data: dict, filename: str) -> str:
    chain_id = data.get('chainId') or ''
    chain_name = data.get('chainName') or ''
    if chain_name:
        return str(chain_name).strip().lower().replace(' ', '')
    ident = str(chain_id).split('-')[0].split('_')[0]
    if ident:
        return ident.lower()
    return os.path.splitext(filename)[0].lower()


def iter_keplr_currency_rows(registry_root: str | None = None) -> Iterable[dict]:
    """Yield token rows compatible with TokenCatalog.register fields."""
    if registry_root:
        root = registry_root
    else:
        root = os.path.join(os.path.dirname(ConfigPath.chain_registry_path), 'keplr-chain-registry')
        if not os.path.isdir(root):
            root = ConfigPath.keplr_chain_registry_path
    cosmos_dir = os.path.join(root, 'cosmos')
    if not os.path.isdir(cosmos_dir):
        return

    for filename in os.listdir(cosmos_dir):
        if not filename.endswith('.json'):
            continue
        path = os.path.join(cosmos_dir, filename)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        chain_name = _chain_name_from_keplr(data, filename)
        for currency in data.get('currencies') or []:
            if not isinstance(currency, dict):
                continue
            denom = currency.get('coinMinimalDenom') or currency.get('coin_minimal_denom')
            if not denom:
                continue
            yield {
                'chain_name': chain_name,
                'denom': str(denom),
                'symbol': currency.get('coinDenom') or currency.get('coin_denom') or '',
                'decimals': currency.get('coinDecimals', currency.get('coin_decimals')),
                'display': currency.get('coinDenom') or '',
                'coingecko_id': currency.get('coinGeckoId') or currency.get('coin_gecko_id'),
                'source': 'keplr_registry',
            }


def load_keplr_currency_rows(registry_root: str | None = None) -> List[dict]:
    return list(iter_keplr_currency_rows(registry_root))
