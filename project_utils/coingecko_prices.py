"""Fiat prices via CoinGecko (Keplr-style, uses coinGeckoId from catalog)."""

from __future__ import annotations

import time
from typing import Dict, Optional, Set

import requests

_COINGECKO_URL = 'https://api.coingecko.com/api/v3/simple/price'
_cache: Dict[str, float] = {}
_cache_at: float = 0.0
_CACHE_TTL = 300.0


def fetch_usd_prices(coin_ids: Set[str], timeout: float = 20.0) -> Dict[str, float]:
    global _cache_at
    ids = sorted({i for i in coin_ids if i})
    if not ids:
        return {}
    if time.time() - _cache_at < _CACHE_TTL and all(i in _cache for i in ids):
        return {i: _cache[i] for i in ids if i in _cache}

    result: Dict[str, float] = {}
    chunk_size = 120
    for offset in range(0, len(ids), chunk_size):
        chunk = ids[offset : offset + chunk_size]
        params = {
            'ids': ','.join(chunk),
            'vs_currencies': 'usd',
        }
        try:
            response = requests.get(_COINGECKO_URL, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException:
            continue
        for coin_id, row in data.items():
            usd = row.get('usd')
            if usd is not None:
                result[coin_id] = float(usd)
                _cache[coin_id] = float(usd)
    _cache_at = time.time()
    return result
