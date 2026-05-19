from chain.wallets.secret_vault import VaultLockedError, get_status


class CredentialsError(RuntimeError):
    pass


PLACEHOLDER_MNEMONIC = (
    'word1 word2 word3 word4 word5 word6 word7 word8 word9 word10 word11 word12'
)


def is_placeholder_mnemonic(mnemonic: str) -> bool:
    return mnemonic.strip() == PLACEHOLDER_MNEMONIC


def mnemonic_is_configured() -> bool:
    from chain.wallets.secret_vault import mnemonic_is_configured as vault_configured

    if not get_status().vault_initialized:
        return False
    return vault_configured()


def require_configured_mnemonic() -> str:
    return get_mnemonic()


def get_mnemonic(wallet_key: str | None = None) -> str:
    """Return BIP39 mnemonic from the KeePass vault."""
    del wallet_key  # kept for callers that pass wallet id
    from config.config_path import ConfigPath

    if not get_status().vault_initialized:
        raise CredentialsError(
            'No secret vault configured.\n'
            f'Create one under {ConfigPath.secrets_path}\n'
            '(GUI: Setup → Secret vault, or: python secrets_cli.py init)'
        )
    try:
        from chain.wallets.secret_vault import get_mnemonic as vault_mnemonic

        return vault_mnemonic()
    except VaultLockedError as exc:
        raise CredentialsError(str(exc)) from exc
    except Exception as exc:
        raise CredentialsError(f'Vault error: {exc}') from exc
