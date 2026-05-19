import json
import os

from config.config_files import FileName
from config.config_path import ConfigPath
from config.config_path_files import PathFileName

path = ConfigPath()
filename = FileName()
path_filename = PathFileName()

_WALLETS_TEMPLATE = '''\
import json

from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip32Slip10Secp256k1, Bip32KeyIndex
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey

from chain.wallets.get_creds import get_mnemonic

_bip44_ctx_wallet_1 = None
_wallet_cache = {{}}

# (chain_name, bech32_prefix, slip44 or None)
_CHAIN_SPECS = [
{chain_specs}
]

_CHAIN_SPEC_BY_NAME = {{name: (prefix, slip) for name, prefix, slip in _CHAIN_SPECS}}


def _wallet_attr(chain_name):
    return f"wallet_1_{{chain_name}}_chain"


def _address_attr(chain_name):
    return f"address_wallet_1_{{chain_name}}_chain"


def _bip44_context_wallet_1():
    global _bip44_ctx_wallet_1
    if _bip44_ctx_wallet_1 is None:
        mnemonic = get_mnemonic()
        seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
        _bip44_ctx_wallet_1 = Bip44.FromSeed(seed_bytes, Bip44Coins.COSMOS).DeriveDefaultPath()
    return _bip44_ctx_wallet_1


def _make_wallet(prefix):
    ctx = _bip44_context_wallet_1()
    return LocalWallet(PrivateKey(ctx.PrivateKey().Raw().ToBytes()), prefix=prefix)


def _make_wallet_slip44(prefix, slip44):
    mnemonic = get_mnemonic()
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
    ctx = Bip32Slip10Secp256k1.FromSeed(seed_bytes)
    for index in (
        Bip32KeyIndex.HardenIndex(44),
        Bip32KeyIndex.HardenIndex(slip44),
        Bip32KeyIndex.HardenIndex(0),
        Bip32KeyIndex.UnhardenIndex(0),
        Bip32KeyIndex.UnhardenIndex(0),
    ):
        ctx = ctx.ChildKey(index)
    return LocalWallet(PrivateKey(ctx.PrivateKey().Raw().ToBytes()), prefix=prefix)


def _get_wallet_for_chain(chain_name):
    if chain_name not in _wallet_cache:
        prefix, slip44 = _CHAIN_SPEC_BY_NAME[chain_name]
        if slip44 is not None and slip44 != 118:
            _wallet_cache[chain_name] = _make_wallet_slip44(prefix, slip44)
        else:
            _wallet_cache[chain_name] = _make_wallet(prefix)
    return _wallet_cache[chain_name]


def __getattr__(name):
    for chain_name in _CHAIN_SPEC_BY_NAME:
        if name == _wallet_attr(chain_name):
            return _get_wallet_for_chain(chain_name)
        if name == _address_attr(chain_name):
            return str(_get_wallet_for_chain(chain_name).address())
    raise AttributeError(f"module {{__name__!r}} has no attribute {{name!r}}")


def write_address_variables_to_json(file_path):
    data = {{}}
    for chain_name in _CHAIN_SPEC_BY_NAME:
        data[_address_attr(chain_name)] = str(_get_wallet_for_chain(chain_name).address())
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=4)
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
