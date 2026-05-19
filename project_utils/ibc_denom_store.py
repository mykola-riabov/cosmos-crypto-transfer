"""Persist IBC denom → symbol mappings discovered via LCD denom_traces."""

from __future__ import annotations

import json
import os
from typing import List, Optional

from config.config_path_files import PathFileName


def resolved_ibc_denoms_path() -> str:
    return PathFileName().resolved_ibc_denoms


def load_resolved_ibc_denoms(path: Optional[str] = None) -> List[dict]:
    path = path or resolved_ibc_denoms_path()
    if not os.path.isfile(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def save_resolved_ibc_entry(
    *,
    network: str,
    ibc_denom: str,
    symbol: str,
    decimals: int,
    origin_denom: str = '',
    origin_network: str = '',
    path: Optional[str] = None,
) -> dict:
    path = path or resolved_ibc_denoms_path()
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    entry = {
        'network': network,
        'ibc_denom': ibc_denom,
        'symbol': symbol,
        'decimals': int(decimals),
        'origin_denom': origin_denom,
        'origin_network': origin_network,
    }
    entries = load_resolved_ibc_denoms(path)
    key = (network.strip().lower(), ibc_denom.strip())
    entries = [e for e in entries if (e.get('network', '').lower(), e.get('ibc_denom', '')) != key]
    entries.append(entry)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2)
    return entry
