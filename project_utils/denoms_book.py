"""Single token mapping file: addresses/denoms/denoms_book.json."""

from __future__ import annotations

import json
import os
from typing import List, Optional

from config.config_path_files import PathFileName
from project_utils.ibc_denom_resolver import normalize_ibc_denom

_LEGACY_USER = 'user_token_mappings.json'
_LEGACY_IBC = 'resolved_ibc_denoms.json'


def denoms_book_path() -> str:
    return PathFileName().denoms_book_path


def _entry_key(network: str, denom: str) -> tuple[str, str]:
    return (network.strip().lower(), _norm_denom(denom))


def _norm_denom(denom: str) -> str:
    d = (denom or '').strip()
    if d.lower().startswith('ibc/'):
        return normalize_ibc_denom(d)
    return d


def load_entries(path: Optional[str] = None, *, migrate_legacy: bool = True) -> List[dict]:
    path = path or denoms_book_path()
    if migrate_legacy:
        _migrate_legacy_files(path)
    if not os.path.isfile(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        return []
    return data


def save_entries(entries: List[dict], path: Optional[str] = None) -> None:
    path = path or denoms_book_path()
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2)
        f.write('\n')


def upsert_entry(
    network: str,
    symbol: str,
    denom_contract: str,
    decimal: int = 6,
    path: Optional[str] = None,
) -> dict:
    """Add or update one mapping (symbol + network → denom)."""
    network = (network or '').strip()
    symbol = (symbol or '').strip().lower()
    denom_contract = _norm_denom(denom_contract)
    if not network or not symbol or not denom_contract:
        raise ValueError('Network, symbol, and denom are required.')

    entry = {
        'symbol': symbol,
        'denom_contract': denom_contract,
        'network': network,
        'decimal': str(int(decimal)),
    }
    path = path or denoms_book_path()
    entries = load_entries(path, migrate_legacy=False)
    key = _entry_key(network, denom_contract)
    entries = [
        e
        for e in entries
        if _entry_key(e.get('network', ''), e.get('denom_contract', '')) != key
    ]
    entries.append(entry)
    entries.sort(key=lambda e: (e.get('network', '').lower(), e.get('symbol', '').lower()))
    save_entries(entries, path)
    return entry


def delete_entry(network: str, denom_contract: str, path: Optional[str] = None) -> bool:
    path = path or denoms_book_path()
    key = _entry_key(network, denom_contract)
    entries = load_entries(path, migrate_legacy=False)
    new_entries = [
        e
        for e in entries
        if _entry_key(e.get('network', ''), e.get('denom_contract', '')) != key
    ]
    if len(new_entries) == len(entries):
        return False
    save_entries(new_entries, path)
    return True


def entries_for_network(network: str, path: Optional[str] = None) -> List[dict]:
    net = (network or '').strip().lower()
    return [e for e in load_entries(path) if e.get('network', '').lower() == net]


def _migrate_legacy_files(book_path: str) -> None:
    """Merge old user_token_mappings.json / resolved_ibc_denoms.json into denoms_book once."""
    from config.config_path import ConfigPath

    data_dir = ConfigPath.data_path
    changed = False
    entries = load_entries(book_path, migrate_legacy=False) if os.path.isfile(book_path) else []
    existing = {_entry_key(e.get('network', ''), e.get('denom_contract', '')) for e in entries}

    user_path = os.path.join(data_dir, _LEGACY_USER)
    if os.path.isfile(user_path):
        with open(user_path, 'r', encoding='utf-8') as f:
            legacy = json.load(f)
        if isinstance(legacy, list):
            for item in legacy:
                key = _entry_key(item.get('network', ''), item.get('denom_contract', ''))
                if key in existing:
                    continue
                entries.append(
                    {
                        'symbol': str(item.get('symbol', '')).lower(),
                        'denom_contract': _norm_denom(item.get('denom_contract', '')),
                        'network': item.get('network', ''),
                        'decimal': str(item.get('decimal', 6)),
                    }
                )
                existing.add(key)
                changed = True

    ibc_path = os.path.join(data_dir, _LEGACY_IBC)
    if os.path.isfile(ibc_path):
        with open(ibc_path, 'r', encoding='utf-8') as f:
            legacy = json.load(f)
        if isinstance(legacy, list):
            for item in legacy:
                ibc = item.get('ibc_denom', '')
                key = _entry_key(item.get('network', ''), ibc)
                if key in existing:
                    continue
                entries.append(
                    {
                        'symbol': str(item.get('symbol', '')).lower(),
                        'denom_contract': _norm_denom(ibc),
                        'network': item.get('network', ''),
                        'decimal': str(item.get('decimals', 6)),
                    }
                )
                existing.add(key)
                changed = True

    if changed:
        entries.sort(key=lambda e: (e.get('network', '').lower(), e.get('symbol', '').lower()))
        save_entries(entries, book_path)
