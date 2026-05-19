"""Registry token catalog and Osmosis DEX price enrichment (Numia API)."""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

import requests

from config.config_links import LinksAPIChain
from config.config_path_files import PathFileName

_osmosis_cache: Optional[Dict[str, dict]] = None


def assets_registry_path() -> str:
    return PathFileName().assets_registry


def load_registry_tokens(path: Optional[str] = None) -> List[dict]:
    path = path or assets_registry_path()
    if not os.path.isfile(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    tokens = payload.get('tokens')
    if isinstance(tokens, list):
        return tokens
    if isinstance(payload, list):
        return payload
    return []


def chains_with_tokens(path: Optional[str] = None) -> List[str]:
    names = sorted({t['chain_name'] for t in load_registry_tokens(path) if t.get('chain_name')})
    return names


def fetch_osmosis_market_index(
    api_url: Optional[str] = None,
    timeout: float = 45.0,
) -> Dict[str, dict]:
    global _osmosis_cache
    url = api_url or LinksAPIChain.link_osmosis_token
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError('Unexpected Osmosis tokens API response')
    by_denom: Dict[str, dict] = {}
    by_display: Dict[str, dict] = {}
    by_symbol: Dict[str, dict] = {}
    for item in data:
        denom = item.get('denom')
        if denom:
            by_denom[str(denom)] = item
        display = (item.get('display') or '').lower()
        if display:
            by_display[display] = item
        symbol = (item.get('symbol') or '').upper()
        if symbol:
            by_symbol[symbol] = item
    _osmosis_cache = {'by_denom': by_denom, 'by_display': by_display, 'by_symbol': by_symbol}
    return _osmosis_cache


def match_osmosis_price(token: dict, market: Dict[str, dict]) -> Optional[dict]:
    denom = token.get('denom') or ''
    if denom in market['by_denom']:
        return market['by_denom'][denom]
    display = (token.get('display') or '').lower()
    if display and display in market['by_display']:
        return market['by_display'][display]
    symbol = (token.get('symbol') or '').upper()
    if symbol and symbol in market['by_symbol']:
        return market['by_symbol'][symbol]
    return None


def enrich_with_osmosis_prices(
    tokens: List[dict],
    market: Optional[Dict[str, dict]] = None,
    api_url: Optional[str] = None,
) -> List[dict]:
    market = market or fetch_osmosis_market_index(api_url=api_url)
    rows = []
    for token in tokens:
        row = dict(token)
        price_row = match_osmosis_price(token, market)
        if price_row:
            row['price'] = price_row.get('price')
            row['liquidity'] = price_row.get('liquidity')
            row['volume_24h'] = price_row.get('volume_24h')
            row['price_24h_change'] = price_row.get('price_24h_change')
            row['price_7d_change'] = price_row.get('price_7d_change')
            row['osmosis_denom'] = price_row.get('denom')
        else:
            row.setdefault('price', None)
        rows.append(row)
    return rows


def token_display_rows(
    chain_name: Optional[str] = None,
    search: Optional[str] = None,
    with_osmosis_prices: bool = True,
    limit: int = 5000,
) -> Tuple[List[dict], dict]:
    tokens = load_registry_tokens()
    meta = {'total': len(tokens), 'shown': 0, 'registry_loaded': bool(tokens)}
    if chain_name and chain_name.lower() not in ('all', ''):
        tokens = [t for t in tokens if t.get('chain_name', '').lower() == chain_name.lower()]
    needle = (search or '').strip().lower()
    if needle:
        def _hay(token: dict) -> str:
            return ' '.join(
                str(token.get(k, ''))
                for k in ('chain_name', 'symbol', 'display', 'name', 'denom', 'contract')
            ).lower()

        tokens = [t for t in tokens if needle in _hay(t)]
    if with_osmosis_prices and tokens:
        try:
            market = fetch_osmosis_market_index()
            tokens = enrich_with_osmosis_prices(tokens, market=market)
            meta['osmosis_prices'] = True
        except requests.RequestException as exc:
            meta['osmosis_prices'] = False
            meta['osmosis_error'] = str(exc)
    if limit > 0 and len(tokens) > limit:
        tokens = tokens[:limit]
        meta['truncated'] = True
    else:
        meta['truncated'] = False
    meta['shown'] = len(tokens)
    return tokens, meta
