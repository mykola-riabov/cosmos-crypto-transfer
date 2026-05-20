"""Fiat prices via CoinGecko (Keplr-style, uses coinGeckoId from catalog)."""

from __future__ import annotations

from typing import Dict, Set

import requests

from project_utils.data_cache import get_cache

_COINGECKO_URL = 'https://api.coingecko.com/api/v3/simple/price'
_CACHE_TTL = 300.0


def fetch_usd_prices(coin_ids: Set[str], timeout: float = 20.0) -> Dict[str, float]:
    ids = sorted({i for i in coin_ids if i})
    if not ids:
        return {}

    cache = get_cache('coingecko', default_ttl=_CACHE_TTL)
    store: Dict[str, float] = cache.get('_all') or {}

    missing = [i for i in ids if i not in store]
    if not missing:
        return {i: store[i] for i in ids if i in store}

    result: Dict[str, float] = dict(store)
    chunk_size = 120
    for offset in range(0, len(missing), chunk_size):
        chunk = missing[offset : offset + chunk_size]
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

    cache.set('_all', result, ttl=_CACHE_TTL)
    return {i: result[i] for i in ids if i in result}
