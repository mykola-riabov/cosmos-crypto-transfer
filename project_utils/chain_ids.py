"""Map internal network names (osmosis, cosmoshub) to chain IDs for APIs."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Dict

from config.config_path_files import PathFileName

_OSMOSIS_CHAIN_ID = 'osmosis-1'


@lru_cache(maxsize=1)
def load_chain_id_map() -> Dict[str, str]:
    path = PathFileName().list_chain_id
    if not os.path.isfile(path):
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {str(k).strip().lower(): str(v).strip() for k, v in data.items()}


def chain_id_for_network(network: str, *, default: str = '') -> str:
    key = (network or '').strip().lower()
    if not key:
        return default
    return load_chain_id_map().get(key, default)


def osmosis_chain_id() -> str:
    return chain_id_for_network('osmosis', default=_OSMOSIS_CHAIN_ID)
