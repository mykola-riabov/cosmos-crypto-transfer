import json
import os

from config.config_path import ConfigPath
from config.config_path_files import PathFileName

path = ConfigPath()
path_filename = PathFileName()

_WALLETS_TEMPLATE = '''\
"""Generated chain wallets — delegates to project_utils.wallet_derivation."""

import re

from project_utils.wallet_derivation import (
    get_address,
    get_local_wallet,
    write_all_wallet_addresses_json,
)

_WALLET_ATTR_RE = re.compile(r'^(?:wallet_(\\d+)|w(\\d+))_(.+)_chain$', re.IGNORECASE)
_ADDRESS_ATTR_RE = re.compile(r'^address_(?:wallet_(\\d+)|w(\\d+))_(.+)_chain$', re.IGNORECASE)

_CHAIN_SPECS = [
{chain_specs}
]

_CHAIN_NAMES = frozenset(name for name, _prefix, _slip in _CHAIN_SPECS)


def _wallet_id_from_match(m):
    num = m.group(1) or m.group(2)
    return f"w{{int(num)}}"


def __getattr__(name):
    m = _WALLET_ATTR_RE.match(name)
    if m:
        wallet_id = _wallet_id_from_match(m)
        chain = m.group(3)
        if chain not in _CHAIN_NAMES:
            raise AttributeError(name)
        return get_local_wallet(wallet_id, chain)
    m = _ADDRESS_ATTR_RE.match(name)
    if m:
        wallet_id = _wallet_id_from_match(m)
        chain = m.group(3)
        if chain not in _CHAIN_NAMES:
            raise AttributeError(name)
        return get_address(wallet_id, chain)
    raise AttributeError(f"module {{__name__!r}} has no attribute {{name!r}}")


def write_address_variables_to_json(file_path):
    write_all_wallet_addresses_json(file_path, enabled_networks=set(_CHAIN_NAMES))
'''


def create_wallets_list_code(cosmos_data_list_path, wallets_list_path, enabled_networks=None):
    with open(cosmos_data_list_path, 'r', encoding='utf-8') as f:
        cosmos_data_list = json.load(f)
    cosmos_data_list = sorted(cosmos_data_list, key=lambda x: x['chain_name'].lower())
    enabled_set = set(enabled_networks) if enabled_networks is not None else None

    spec_lines = []
    for data in cosmos_data_list:
        if enabled_set is not None and data['chain_name'] not in enabled_set:
            continue
        chain_name = data['chain_name']
        prefix = data['bech32_prefix']
        slip44 = data.get('slip44')
        slip_repr = 'None' if slip44 is None else str(int(slip44))
        spec_lines.append(f'    ({chain_name!r}, {prefix!r}, {slip_repr}),')

    code = _WALLETS_TEMPLATE.format(chain_specs='\n'.join(spec_lines))

    with open(wallets_list_path, 'w', encoding='utf-8') as f:
        f.write(code)
    print('wallets_list.py file has been updated.')
