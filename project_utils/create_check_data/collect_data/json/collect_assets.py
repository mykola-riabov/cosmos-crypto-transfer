"""Build a flat token list from chain-registry assetlist.json files."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

from colorama import Fore, Style


def _decimals_from_denom_units(denom_units: Iterable[dict]) -> int:
    decimals = 0
    for unit in denom_units or []:
        try:
            exp = int(unit.get('exponent', 0))
        except (TypeError, ValueError):
            exp = 0
        if exp > decimals:
            decimals = exp
    return decimals


def _contract_address(asset: dict) -> str:
    for key in ('address', 'contract'):
        value = asset.get(key)
        if value:
            return str(value)
    traces = asset.get('traces') or []
    for trace in traces:
        if not isinstance(trace, dict):
            continue
        cw = trace.get('counterparty') or {}
        if isinstance(cw, dict):
            addr = cw.get('base_denom') or cw.get('channel') or ''
            if addr and str(addr).startswith('ibc/'):
                return str(addr)
    return ''


def parse_asset(asset: dict, chain_name: str) -> Optional[dict]:
    if not isinstance(asset, dict):
        return None
    base = asset.get('base') or ''
    if not base:
        return None
    symbol = (asset.get('symbol') or '').strip()
    display = (asset.get('display') or symbol or base).strip()
    name = (asset.get('name') or symbol or display).strip()
    return {
        'chain_name': chain_name,
        'symbol': symbol,
        'display': display,
        'name': name,
        'denom': str(base),
        'decimals': _decimals_from_denom_units(asset.get('denom_units')),
        'type': asset.get('type') or 'native',
        'contract': _contract_address(asset),
    }


def collect_assets_registry(
    registry_root: str,
    output_path: str,
    chain_names: Optional[Iterable[str]] = None,
) -> int:
    """Scan chain-registry asset lists and write assets_registry.json."""
    allowed = {c.lower() for c in chain_names} if chain_names else None
    tokens: List[dict] = []
    seen: set = set()

    if not os.path.isdir(registry_root):
        print(Fore.RED + f'chain-registry not found: {registry_root}' + Style.RESET_ALL)
        return 0

    for entry in sorted(os.listdir(registry_root)):
        chain_dir = os.path.join(registry_root, entry)
        if not os.path.isdir(chain_dir):
            continue
        chain_name = entry
        if allowed is not None and chain_name.lower() not in allowed:
            continue
        assetlist_path = os.path.join(chain_dir, 'assetlist.json')
        if not os.path.isfile(assetlist_path):
            continue
        try:
            with open(assetlist_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue
        file_chain = content.get('chain_name') or chain_name
        for asset in content.get('assets') or []:
            row = parse_asset(asset, file_chain)
            if row is None:
                continue
            key = (row['chain_name'].lower(), row['denom'])
            if key in seen:
                continue
            seen.add(key)
            tokens.append(row)

    tokens.sort(key=lambda r: (r['chain_name'].lower(), r['symbol'].lower(), r['denom']))
    payload = {
        'updated_at': datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        'count': len(tokens),
        'tokens': tokens,
    }
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    print(
        Fore.GREEN
        + f'assets_registry.json written: {len(tokens)} tokens from {registry_root}'
        + Style.RESET_ALL
    )
    return len(tokens)
