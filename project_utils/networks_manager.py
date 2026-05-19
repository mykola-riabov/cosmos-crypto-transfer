"""Enabled Cosmos networks, REST health checks, and chain list helpers."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

import requests

from config.config_files import FileName
from config.config_path import ConfigPath
from config.config_path_files import PathFileName

DEFAULT_ENABLED_NETWORKS: Tuple[str, ...] = ('osmosis', 'cosmoshub')

_PROBE_PATHS = (
    '/cosmos/base/tendermint/v1beta1/node_info',
    '/cosmos/staking/v1beta1/params',
    '/',
)

_filename = FileName()


def enabled_networks_path() -> str:
    return PathFileName().enabled_networks


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_enabled_networks_file(path: Optional[str] = None) -> str:
    path = path or enabled_networks_path()
    if os.path.isfile(path):
        return path
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    save_enabled_config(list(DEFAULT_ENABLED_NETWORKS), health={}, path=path)
    return path


def load_enabled_config(path: Optional[str] = None) -> dict:
    path = ensure_enabled_networks_file(path)
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    enabled = data.get('enabled')
    if not isinstance(enabled, list):
        enabled = list(DEFAULT_ENABLED_NETWORKS)
    health = data.get('health')
    if not isinstance(health, dict):
        health = {}
    return {'enabled': enabled, 'health': health}


def save_enabled_config(
    enabled: Iterable[str],
    health: Optional[dict] = None,
    path: Optional[str] = None,
) -> None:
    path = path or enabled_networks_path()
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    current = load_enabled_config(path) if os.path.isfile(path) else {'health': {}}
    payload = {
        'enabled': sorted({str(name) for name in enabled}),
        'health': health if health is not None else current.get('health', {}),
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)


def get_enabled_networks(path: Optional[str] = None) -> Set[str]:
    return set(load_enabled_config(path)['enabled'])


def set_enabled_networks(names: Iterable[str], path: Optional[str] = None) -> None:
    cfg = load_enabled_config(path)
    save_enabled_config(names, health=cfg.get('health', {}), path=path)


def reset_enabled_to_defaults(path: Optional[str] = None) -> Set[str]:
    names = set(DEFAULT_ENABLED_NETWORKS)
    cfg = load_enabled_config(path)
    # Keep health only for enabled networks (avoids hundreds of stale keys in JSON).
    health = {k: v for k, v in cfg.get('health', {}).items() if k in names}
    save_enabled_config(names, health=health, path=path)
    return names


def load_all_chains(cosmos_data_path: Optional[str] = None) -> List[dict]:
    cosmos_data_path = cosmos_data_path or PathFileName().data_cosmos_file_name
    if not os.path.isfile(cosmos_data_path):
        return []
    with open(cosmos_data_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return sorted(data, key=lambda row: row.get('chain_name', '').lower())


def get_rest_url(chain: dict, link_type: str = 'rest_link') -> Optional[str]:
    link = chain.get(link_type)
    if not link:
        link = chain.get('rest_link') or chain.get('keplr_rest_link')
    if not link:
        return None
    return str(link).rstrip('/')


def filter_chains_by_enabled(
    chains: Iterable[dict],
    enabled_networks: Optional[Set[str]] = None,
) -> List[dict]:
    if enabled_networks is None:
        enabled_networks = get_enabled_networks()
    return [c for c in chains if c.get('chain_name') in enabled_networks]


def probe_rest(rest_url: Optional[str], timeout: float = 8.0) -> Tuple[bool, Optional[str]]:
    if not rest_url:
        return False, 'No REST URL'
    base = rest_url.rstrip('/')
    last_error: Optional[str] = None
    for suffix in _PROBE_PATHS:
        try:
            response = requests.get(f'{base}{suffix}', timeout=timeout)
            if response.status_code < 500:
                return True, None
            last_error = f'HTTP {response.status_code}'
        except requests.RequestException as exc:
            last_error = str(exc)
    return False, last_error or 'Unreachable'


def probe_chain(chain: dict, link_type: str = 'rest_link', timeout: float = 8.0) -> dict:
    rest = get_rest_url(chain, link_type=link_type)
    ok, error = probe_rest(rest, timeout=timeout)
    return {
        'ok': ok,
        'error': error,
        'rest': rest,
        'checked_at': _utc_now_iso(),
    }


def update_health_cache(
    health_results: Dict[str, dict],
    path: Optional[str] = None,
) -> None:
    cfg = load_enabled_config(path)
    health = dict(cfg.get('health', {}))
    health.update(health_results)
    save_enabled_config(cfg['enabled'], health=health, path=path)


def probe_all_chains(
    chains: Iterable[dict],
    link_type: str = 'rest_link',
    timeout: float = 8.0,
    on_progress: Optional[Callable[[str, dict], None]] = None,
) -> Dict[str, dict]:
    results: Dict[str, dict] = {}
    for chain in chains:
        name = chain.get('chain_name')
        if not name:
            continue
        result = probe_chain(chain, link_type=link_type, timeout=timeout)
        results[name] = result
        if on_progress:
            on_progress(name, result)
    return results


def network_rows(
    cosmos_data_path: Optional[str] = None,
    enabled_path: Optional[str] = None,
) -> List[dict]:
    chains = load_all_chains(cosmos_data_path)
    enabled = get_enabled_networks(enabled_path)
    cfg = load_enabled_config(enabled_path)
    health = cfg.get('health', {})
    rows = []
    for chain in chains:
        name = chain['chain_name']
        h = health.get(name, {})
        rest = get_rest_url(chain)
        if h:
            if h.get('ok'):
                status = 'OK'
            elif rest is None:
                status = 'No REST'
            else:
                status = 'Offline'
        else:
            status = 'Not tested' if rest else 'No REST'
        rows.append(
            {
                'chain_name': name,
                'chain_id': chain.get('chain_id', ''),
                'enabled': name in enabled,
                'status': status,
                'rest': rest or '',
                'health': h,
            }
        )
    return rows


def test_all_network_health(link_type: str = 'rest_link') -> str:
    """Probe REST for all chains in cosmos_data_list.json; update enabled_networks health cache."""
    chains = load_all_chains()
    if not chains:
        return 'No chain data. Run Setup → Collect chain-registry JSON first.\n'

    lines = [f'Probing {len(chains)} networks…\n']
    results = probe_all_chains(chains, link_type=link_type)
    update_health_cache(results)
    ok_count = sum(1 for r in results.values() if r.get('ok'))
    lines.append(f'Done: {ok_count}/{len(results)} reachable.\n')
    for name in sorted(results):
        row = results[name]
        mark = 'OK' if row.get('ok') else 'FAIL'
        err = row.get('error') or ''
        lines.append(f'  {mark:4} {name:20} {err}\n')
    return ''.join(lines)
