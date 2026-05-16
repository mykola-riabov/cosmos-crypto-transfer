import json
import os
from typing import Optional

from config.config_files import FileName
from config.config_path import ConfigPath
from config.config_path_files import PathFileName

path = ConfigPath()
filename = FileName()
path_filename = PathFileName()


class CredentialsError(RuntimeError):
    pass


def get_wallet_json_path() -> str:
    return os.environ.get(
        'COSMOS_WALLET_FILE',
        path_filename.wallet_json_filepath,
    )


def load_wallet_json(path: Optional[str] = None) -> dict:
    wallet_path = path or get_wallet_json_path()
    if not os.path.isfile(wallet_path):
        example = path_filename.wallet_json_example_filepath
        raise CredentialsError(
            f'Wallet file not found: {wallet_path}\n'
            f'Copy {example} to {wallet_path} and set your mnemonic.'
        )
    with open(wallet_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise CredentialsError(f'Wallet file must be a JSON object: {wallet_path}')
    return data


def get_mnemonic(wallet_key: Optional[str] = None) -> str:
    """Return BIP39 mnemonic for the default or named wallet."""
    data = load_wallet_json()
    key = wallet_key or filename.mnemonic_wallet_key

    mnemonic = data.get(key)
    if not mnemonic and key != 'mnemonic':
        mnemonic = data.get('mnemonic')
    if not mnemonic:
        raise CredentialsError(
            f'Mnemonic not found in wallet JSON (expected key {key!r} or "mnemonic").'
        )

    mnemonic = str(mnemonic).strip()
    if not mnemonic:
        raise CredentialsError('Mnemonic is empty.')
    return mnemonic


def get_creds_info() -> dict:
    """Backward-compatible dict for generated wallets_list.py."""
    data = load_wallet_json()
    mnemonic = get_mnemonic()
    return {
        filename.mnemonic_wallet_key: mnemonic,
        'api': data.get('api'),
    }
