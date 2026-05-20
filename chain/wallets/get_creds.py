from chain.wallets.secret_vault import VaultLockedError, get_status
from project_utils.wallet_ids import normalize_wallet_id


class CredentialsError(RuntimeError):
    pass


PLACEHOLDER_MNEMONIC = (
    'word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12'
)


def is_placeholder_mnemonic(mnemonic: str) -> bool:
    return mnemonic.strip() == PLACEHOLDER_MNEMONIC


def _resolve_wallet_id(wallet_key: str | None) -> str:
    if wallet_key:
        return normalize_wallet_id(wallet_key)
    from project_utils.wallet_profiles import get_active_wallet_id

    return get_active_wallet_id()


def mnemonic_is_configured(wallet_id: str | None = None) -> bool:
    from chain.wallets.secret_vault import has_wallet_secret, mnemonic_is_configured as vault_any

    if not get_status().vault_initialized:
        return False
    if wallet_id:
        return has_wallet_secret(wallet_id)
    return vault_any()


def require_configured_mnemonic(wallet_key: str | None = None) -> str:
    return get_mnemonic(wallet_key)


def get_mnemonic(wallet_key: str | None = None) -> str:
    """Return BIP39 mnemonic from vault (mnemonic wallets only)."""
    from config.config_path import ConfigPath

    wallet_id = _resolve_wallet_id(wallet_key)
    if not get_status().vault_initialized:
        raise CredentialsError(
            'No secret vault configured.\n'
            f'Create one under {ConfigPath.secrets_path}\n'
            '(GUI: Portfolio → New wallet, or Setup → Secret vault)'
        )
    from project_utils.wallet_profiles import get_profile

    if get_profile(wallet_id).get('key_type') == 'private_key':
        raise CredentialsError(
            f'Wallet {wallet_id} uses a private key, not a mnemonic. '
            'Use address derivation via wallet_derivation instead.'
        )
    try:
        from chain.wallets.secret_vault import get_mnemonic as vault_mnemonic

        return vault_mnemonic(wallet_id)
    except VaultLockedError as exc:
        raise CredentialsError(str(exc)) from exc
    except Exception as exc:
        raise CredentialsError(f'Vault error: {exc}') from exc
