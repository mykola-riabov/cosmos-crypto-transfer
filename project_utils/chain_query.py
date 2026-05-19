"""Lightweight chain REST queries (block height for IBC timeout)."""

from __future__ import annotations

import requests

_LATEST_BLOCK = '/cosmos/base/tendermint/v1beta1/blocks/latest'


def fetch_latest_block_height(rest_base: str, timeout: float = 10.0) -> int:
    base = (rest_base or '').rstrip('/')
    if not base:
        raise ValueError('No REST URL for destination chain')
    response = requests.get(f'{base}{_LATEST_BLOCK}', timeout=timeout)
    response.raise_for_status()
    data = response.json()
    return int(data['block']['header']['height'])
