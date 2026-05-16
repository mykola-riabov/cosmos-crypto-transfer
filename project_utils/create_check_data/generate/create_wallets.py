import json
import os
from config.config_path import ConfigPath
from config.config_files import FileName
from config.config_path_files import PathFileName

path = ConfigPath()
filename = FileName()
path_filename = PathFileName()


def create_wallets_list_code(cosmos_data_list_path, wallets_list_path):
    with open(cosmos_data_list_path, 'r') as f:
        cosmos_data_list = json.load(f)
    cosmos_data_list = sorted(cosmos_data_list, key=lambda x: x['chain_name'].lower())

    code_template = '''
import json
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins, Bip32Slip10Secp256k1, Bip32KeyIndex
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey
from chain.wallets.get_creds import get_mnemonic

_bip44_ctx_wallet_1 = None


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


def write_address_variables_to_json(file_path):
    data = {{}}
    for name, value in globals().items():
        if name.startswith('address'):
            data[name] = str(value)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
{}
'''

    wallet_chain_codes = []
    for data in cosmos_data_list:
        chain_name = data['chain_name']
        prefix = data['bech32_prefix']
        slip44 = data.get('slip44')

        if slip44 and slip44 != 118:
            wallet_chain_code = '''
# wallet {0}_chain (slip44 {1})
wallet_1_{0}_chain = _make_wallet_slip44("{2}", {1})
address_wallet_1_{0}_chain = wallet_1_{0}_chain.address()
'''.format(chain_name, slip44, prefix)
        else:
            wallet_chain_code = '''
# wallet {0}_chain
wallet_1_{0}_chain = _make_wallet("{1}")
address_wallet_1_{0}_chain = wallet_1_{0}_chain.address()
'''.format(chain_name, prefix)

        wallet_chain_codes.append(wallet_chain_code)

    code = code_template.format('\n'.join(wallet_chain_codes))

    with open(wallets_list_path, 'w') as f:
        f.write(code)
    print('wallets_list.py file has been updated.')
