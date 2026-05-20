"""HTTP client for Skip Go API (route + msgs)."""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests

DEFAULT_SKIP_API_URL = 'https://api.skip.build'
DEFAULT_TIMEOUT_SEC = 30


class SkipApiError(RuntimeError):
    """Skip API returned an error or unreachable."""


def skip_api_base_url() -> str:
    return (os.environ.get('SKIP_API_URL') or DEFAULT_SKIP_API_URL).rstrip('/')


def _post(path: str, payload: Dict[str, Any], *, timeout: int = DEFAULT_TIMEOUT_SEC) -> Dict[str, Any]:
    url = f'{skip_api_base_url()}{path}'
    try:
        response = requests.post(
            url,
            headers={'Content-Type': 'application/json'},
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise SkipApiError(f'Skip API request failed: {exc}') from exc
    if response.status_code == 404:
        raise SkipApiError('No route found for this token pair and amount.')
    try:
        body = response.json()
    except ValueError as exc:
        raise SkipApiError(f'Skip API returned non-JSON ({response.status_code})') from exc
    if not response.ok:
        message = body.get('message') if isinstance(body, dict) else response.text
        raise SkipApiError(f'Skip API error ({response.status_code}): {message}')
    if not isinstance(body, dict):
        raise SkipApiError('Skip API returned unexpected response shape.')
    return body


def fetch_route(
    *,
    amount_in: str,
    source_denom: str,
    source_chain_id: str,
    dest_denom: str,
    dest_chain_id: str,
    allow_multi_tx: bool = False,
    split_routes: bool = False,
    osmosis_poolmanager_only: bool = True,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        'amount_in': str(amount_in),
        'source_asset_denom': source_denom,
        'source_asset_chain_id': source_chain_id,
        'dest_asset_denom': dest_denom,
        'dest_asset_chain_id': dest_chain_id,
        'cumulative_affiliate_fee_bps': '0',
        'allow_multi_tx': allow_multi_tx,
        'allow_unsafe': True,
        'smart_swap_options': {'split_routes': split_routes},
    }
    if osmosis_poolmanager_only and source_chain_id == dest_chain_id == 'osmosis-1':
        payload['swap_venues'] = [{'chain_id': 'osmosis-1', 'name': 'osmosis-poolmanager'}]
    return _post('/v2/fungible/route', payload)


def fetch_msgs(
    route: Dict[str, Any],
    *,
    address_list: List[str],
    slippage_tolerance_percent: str,
) -> Dict[str, Any]:
    required = route.get('required_chain_addresses') or [route.get('source_asset_chain_id', '')]
    addrs = list(address_list)
    if len(addrs) < len(required):
        if not addrs:
            raise SkipApiError('address_list is empty for Skip msgs request.')
        addrs = addrs + [addrs[-1]] * (len(required) - len(addrs))
    payload = {
        'source_asset_denom': route['source_asset_denom'],
        'source_asset_chain_id': route['source_asset_chain_id'],
        'dest_asset_denom': route['dest_asset_denom'],
        'dest_asset_chain_id': route['dest_asset_chain_id'],
        'amount_in': route['amount_in'],
        'amount_out': route.get('estimated_amount_out') or route.get('amount_out', ''),
        'operations': route['operations'],
        'address_list': addrs[: len(required)],
        'slippage_tolerance_percent': str(slippage_tolerance_percent),
        'chain_ids_to_affiliates': {},
    }
    return _post('/v2/fungible/msgs', payload)
