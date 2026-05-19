"""User-defined token names (denom → symbol) for any network, like denoms_book entries."""

from __future__ import annotations

import json
import os
from typing import List, Optional

from config.config_path_files import PathFileName
from project_utils.ibc_denom_resolver import normalize_ibc_denom


def user_token_mappings_path() -> str:
    return PathFileName().user_token_mappings


def load_user_token_mappings(path: Optional[str] = None) -> List[dict]:
    path = path or user_token_mappings_path()
    if not os.path.isfile(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _denom_key(denom: str) -> str:
    d = (denom or '').strip()
    if d.lower().startswith('ibc/'):
        return normalize_ibc_denom(d)
    return d


def save_user_token_mapping(
    *,
    network: str,
    denom: str,
    symbol: str,
    decimals: int = 6,
    also_denoms_book: bool = True,
    path: Optional[str] = None,
) -> dict:
    """Persist mapping; optionally append to addresses/denoms/denoms_book.json."""
    network = (network or '').strip()
    symbol = (symbol or '').strip()
    denom = _denom_key(denom)
    if not network or not denom or not symbol:
        raise ValueError('Network, denom, and symbol are required.')

    entry = {
        'symbol': symbol.lower(),
        'denom_contract': denom,
        'network': network,
        'decimal': str(int(decimals)),
        'source': 'user',
    }

    path = path or user_token_mappings_path()
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    entries = load_user_token_mappings(path)
    key = (network.lower(), denom)
    entries = [
        e
        for e in entries
        if (e.get('network', '').lower(), _denom_key(e.get('denom_contract', ''))) != key
    ]
    entries.append(entry)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2)

    if also_denoms_book:
        _append_denoms_book_entry(network, symbol, denom, int(decimals))

    return entry


def _append_denoms_book_entry(network: str, symbol: str, denom: str, decimals: int) -> None:
    book_path = PathFileName().denoms_book_path
    if not os.path.isfile(book_path):
        return
    with open(book_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        data = []
    key = (network.lower(), _denom_key(denom))
    for item in data:
        if (
            item.get('network', '').lower() == key[0]
            and _denom_key(item.get('denom_contract', '')) == key[1]
        ):
            item['symbol'] = symbol.lower()
            item['decimal'] = str(decimals)
            break
    else:
        data.append(
            {
                'symbol': symbol.lower(),
                'denom_contract': denom,
                'network': network,
                'decimal': str(decimals),
            }
        )
    with open(book_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
