import json
import os
from config.config_path import ConfigPath
from config.config_files import FileName
from config.config_path_files import PathFileName

path = ConfigPath()
filename = FileName()
path_filename = PathFileName()


def create_wallets_list_code(cosmos_data_list_path, wallets_list_path):
    # Load cosmos_data_list.json
    with open(cosmos_data_list_path, 'r') as f:
        cosmos_data_list = json.load(f)
    # Sort cosmos_data_list by chain_name in alphabetical order
    cosmos_data_list = sorted(cosmos_data_list, key=lambda x: x['chain_name'].lower())

    # Generate code template
    code_template = """
import json
from bip_utils import Bip39SeedGenerator, Bip44, Bip44Coins
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey
from chain.wallets.get_creds import get_creds_info
from config.config_files import FileName


filename = FileName()
creds_info = get_creds_info()
mnemonic_1_value = creds_info[filename.mnemonic_1_keepass]
seed_bytes_wallet_1 = Bip39SeedGenerator(mnemonic_1_value).Generate()
bip44_def_ctx_wallet_1 = Bip44.FromSeed(seed_bytes_wallet_1, Bip44Coins.COSMOS).DeriveDefaultPath()

# Generate wallet chain code for each chain in cosmos_data_list.json
def write_address_variables_to_json(file_path):
    data = {{}}
    for name, value in globals().items():
        if name.startswith('address'):
            data[name] = str(value)
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
{}
print('Successful Address book generation')
"""

    wallet_chain_codes = []

    for data in cosmos_data_list:
        chain_name = data['chain_name']
        prefix = data['bech32_prefix']

        wallet_chain_code = """
# wallet {}_chain
wallet_1_{}_chain = LocalWallet(PrivateKey(bip44_def_ctx_wallet_1.PrivateKey().Raw().ToBytes()), prefix="{}")
address_wallet_1_{}_chain = wallet_1_{}_chain.address()
""".format(chain_name, chain_name, prefix, chain_name, chain_name)

        wallet_chain_codes.append(wallet_chain_code)

    code = code_template.format("\n".join(wallet_chain_codes))

    # Check if wallets_list.py file exists in chain/wallets directory
    if os.path.exists(wallets_list_path):
        # If file exists, overwrite with the generated code
        with open(wallets_list_path, 'w') as f:
            f.write(code)
        print("wallets_list.py file has been updated.")
    else:
        # If file doesn't exist, create and write the generated code
        with open(wallets_list_path, 'w') as f:
            f.write(code)
        print("wallets_list.py file has been created.")
