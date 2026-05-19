"""Resolve IBC denoms via LCD denom_traces (Keplr-style)."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

import requests

_trace_cache: Dict[str, dict] = {}


def normalize_ibc_denom(denom: str) -> str:
    """Canonical form for ibc/HASH (uppercase hex)."""
    d = (denom or '').strip()
    if d.lower().startswith('ibc/'):
        return 'ibc/' + d.split('/', 1)[-1].upper()
    return d


def ibc_hash_from_denom(ibc_denom: str) -> Optional[str]:
    if not ibc_denom or not ibc_denom.lower().startswith('ibc/'):
        return None
    return ibc_denom.split('/', 1)[-1].strip().upper()


def fetch_denom_trace(rest_base: str, ibc_denom: str, timeout: float = 10.0) -> Optional[dict]:
    hash_part = ibc_hash_from_denom(ibc_denom)
    if not hash_part:
        return None
    cache_key = f'{rest_base}|{hash_part}'
    if cache_key in _trace_cache:
        return _trace_cache[cache_key]

    base = rest_base.rstrip('/')
    urls = (
        f'{base}/ibc/apps/transfer/v1/denom_traces/{hash_part}',
        f'{base}/ibc/apps/transfer/v1beta1/denom_traces/{hash_part}',
    )
    for url in urls:
        try:
            response = requests.get(url, timeout=timeout)
            if response.status_code != 200:
                continue
            payload = response.json()
            trace = payload.get('denom_trace') or payload
            if trace:
                _trace_cache[cache_key] = trace
                return trace
        except requests.RequestException:
            continue
    return None


def origin_denom_from_trace(trace: dict) -> Optional[str]:
    if not trace:
        return None
    base = trace.get('base_denom')
    if base:
        return str(base)
    path = trace.get('path') or ''
    if path:
        parts = path.split('/')
        if parts:
            return parts[-1]
    return None


def infer_symbol_decimals_from_base_denom(base_denom: str) -> tuple[str, int]:
    """Guess display symbol/decimals when origin chain is not in the catalog."""
    d = (base_denom or '').strip()
    if d.startswith('u') and len(d) > 1:
        return d[1:].upper(), 6
    if d.startswith('a') and len(d) > 1 and d[1:].isalpha():
        return d[1:].upper(), 6
    return d.upper(), 6
