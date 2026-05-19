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


PLACEHOLDER_MNEMONIC = (
    'word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12'
)


def is_placeholder_mnemonic(mnemonic: str) -> bool:
    return mnemonic.strip() == PLACEHOLDER_MNEMONIC


def _mnemonic_from_legacy_wallet() -> Optional[str]:
    wallet_path = get_wallet_json_path()
    if not os.path.isfile(wallet_path):
        return None
    data = load_wallet_json(wallet_path)
    mnemonic = (data.get(filename.mnemonic_wallet_key) or data.get('mnemonic') or '').strip()
    if not mnemonic or is_placeholder_mnemonic(mnemonic):
        return None
    return mnemonic


def mnemonic_is_configured() -> bool:
    from chain.wallets.secret_vault import get_status, mnemonic_is_configured as vault_configured

    if get_status().vault_initialized:
        return vault_configured()
    return _mnemonic_from_legacy_wallet() is not None


def require_configured_mnemonic() -> str:
    return get_mnemonic()


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
            f'Use the secret vault (~/.market_ai_secrets/) or copy {example} for legacy mode.'
        )
    with open(wallet_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise CredentialsError(f'Wallet file must be a JSON object: {wallet_path}')
    return data


def get_mnemonic(wallet_key: Optional[str] = None) -> str:
    """Return BIP39 mnemonic from KeePass vault or legacy wallet.json."""
    from chain.wallets.secret_vault import VaultLockedError, get_status

    status = get_status()
    if status.vault_initialized:
        try:
            from chain.wallets.secret_vault import get_mnemonic as vault_mnemonic

            return vault_mnemonic()
        except VaultLockedError as exc:
            raise CredentialsError(str(exc)) from exc
        except Exception as exc:
            raise CredentialsError(f'Vault error: {exc}') from exc

    legacy = _mnemonic_from_legacy_wallet()
    if legacy:
        return legacy

    raise CredentialsError(
        'No mnemonic configured.\n'
        f'Create a vault under {ConfigPath.secrets_path} (GUI: Setup → Secret vault)\n'
        'or set a mnemonic in source/creds/wallet.json (legacy).'
    )


def get_creds_info() -> dict:
    data = {}
    if os.path.isfile(get_wallet_json_path()):
        try:
            data = load_wallet_json()
        except CredentialsError:
            pass
    return {
        filename.mnemonic_wallet_key: get_mnemonic(),
        'api': data.get('api'),
    }
