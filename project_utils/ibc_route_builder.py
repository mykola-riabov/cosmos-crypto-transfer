"""Build IBC transfer routes from chain-registry _IBC/*.json for enabled network pairs."""

from __future__ import annotations

import json
import os
from itertools import combinations
from typing import Dict, Iterable, List, Optional, Set, Tuple

from config.config_path import ConfigPath
from project_utils.create_check_data.generate.create_ledger_clients import to_python_identifier

DEFAULT_GAS = 200000
DEFAULT_TIMEOUT = 120


def registry_ibc_dir() -> str:
    return os.path.join(ConfigPath().chain_registry_path, '_IBC')


def _pair_ibc_path(chain_a: str, chain_b: str, ibc_dir: str) -> Optional[str]:
    for a, b in ((chain_a, chain_b), (chain_b, chain_a)):
        path = os.path.join(ibc_dir, f'{a}-{b}.json')
        if os.path.isfile(path):
            return path
    return None


def _pick_channel(channels: List[dict]) -> Optional[dict]:
    if not channels:
        return None
    for ch in channels:
        tags = ch.get('tags') or {}
        if tags.get('status') == 'ACTIVE' and tags.get('preferred'):
            return ch
    for ch in channels:
        tags = ch.get('tags') or {}
        if tags.get('status') == 'ACTIVE':
            return ch
    return channels[0]


def _make_route(source: str, destination: str, channel: str) -> dict:
    py_src = to_python_identifier(source)
    return {
        'source_network': source,
        'destination_network': destination,
        'sender_wallet': f'wallet_1_{source}',
        'receiver_wallet': f'wallet_1_{destination}',
        'channel': channel,
        'gas': DEFAULT_GAS,
        'timeout_seconds': DEFAULT_TIMEOUT,
        'client_attr': f'{py_src}_client',
        'wallet_attr': f'wallet_1_{py_src}_chain',
    }


def routes_for_pair(chain_a: str, chain_b: str, ibc_dir: Optional[str] = None) -> List[dict]:
    """Bidirectional ICS-20 routes for one registry IBC pair file, or []."""
    ibc_dir = ibc_dir or registry_ibc_dir()
    path = _pair_ibc_path(chain_a, chain_b, ibc_dir)
    if not path:
        return []

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    channel = _pick_channel(data.get('channels') or [])
    if not channel:
        return []

    c1_name = data['chain_1']['chain_name']
    c2_name = data['chain_2']['chain_name']
    ch1 = channel['chain_1']['channel_id']
    ch2 = channel['chain_2']['channel_id']
    return [
        _make_route(c1_name, c2_name, ch1),
        _make_route(c2_name, c1_name, ch2),
    ]


def build_routes_for_enabled(
    enabled: Iterable[str],
    ibc_dir: Optional[str] = None,
) -> List[dict]:
    """Routes between every enabled pair that has a chain-registry _IBC file."""
    names = sorted({str(n) for n in enabled})
    routes: List[dict] = []
    seen: Set[Tuple[str, str]] = set()
    for a, b in combinations(names, 2):
        for route in routes_for_pair(a, b, ibc_dir=ibc_dir):
            key = (route['source_network'], route['destination_network'])
            if key in seen:
                continue
            seen.add(key)
            routes.append(route)
    return sorted(routes, key=lambda r: (r['source_network'], r['destination_network']))


def merge_route_lists(manual: List[dict], generated: List[dict]) -> List[dict]:
    """Manual routes override generated for the same source → destination."""
    merged: Dict[Tuple[str, str], dict] = {}
    for route in generated:
        merged[(route['source_network'], route['destination_network'])] = route
    for route in manual:
        merged[(route['source_network'], route['destination_network'])] = route
    return sorted(merged.values(), key=lambda r: (r['source_network'], r['destination_network']))
