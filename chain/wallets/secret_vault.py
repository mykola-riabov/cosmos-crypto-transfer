"""KeePass vault for mnemonic storage under ~/.market_ai_secrets/<project>/."""
from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.config_path import ConfigPath

VAULT_GROUP = 'CosmosTransfer'
VAULT_ENTRY_TITLE = 'wallet_1_mnemonic'
VAULT_ENTRY_USER = 'cosmos-crypto-transfer'

_session_database: Optional[object] = None


class VaultError(RuntimeError):
    pass


class VaultLockedError(VaultError):
    pass


@dataclass
class VaultStatus:
    secrets_dir: str
    database_exists: bool
    password_file_exists: bool
    keyfile_exists: bool
    meta_exists: bool
    unlock_files_ready: bool
    is_unlocked: bool

    @property
    def vault_initialized(self) -> bool:
        return self.database_exists and self.meta_exists


def _require_pykeepass():
    try:
        from pykeepass import PyKeePass, create_database  # noqa: F401
    except ImportError as exc:
        raise VaultError(
            'pykeepass is not installed. Run: pip install pykeepass'
        ) from exc
    from pykeepass import PyKeePass, create_database

    return PyKeePass, create_database


def ensure_secrets_dir() -> Path:
    path = Path(ConfigPath.secrets_path)
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, 0o700)
    except OSError:
        pass
    return path


def get_status() -> VaultStatus:
    return VaultStatus(
        secrets_dir=ConfigPath.secrets_path,
        database_exists=os.path.isfile(ConfigPath.vault_database_path),
        password_file_exists=os.path.isfile(ConfigPath.vault_password_path),
        keyfile_exists=os.path.isfile(ConfigPath.vault_keyfile_path),
        meta_exists=os.path.isfile(ConfigPath.vault_meta_path),
        unlock_files_ready=(
            os.path.isfile(ConfigPath.vault_password_path)
            and os.path.isfile(ConfigPath.vault_keyfile_path)
        ),
        is_unlocked=_session_database is not None,
    )


def _write_meta() -> None:
    payload = {
        'version': 1,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'entry_title': VAULT_ENTRY_TITLE,
        'group': VAULT_GROUP,
        'project_slug': ConfigPath.secrets_slug,
    }
    with open(ConfigPath.vault_meta_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
        f.write('\n')
    try:
        os.chmod(ConfigPath.vault_meta_path, 0o600)
    except OSError:
        pass


def _read_master_password(password: Optional[str] = None) -> str:
    if password is not None:
        value = password.strip()
        if not value:
            raise VaultError('Master password is empty.')
        return value
    if not os.path.isfile(ConfigPath.vault_password_path):
        raise VaultLockedError(
            f'Master password file missing: {ConfigPath.vault_password_path}\n'
            'Copy master.password from your USB stick or enter the password in the GUI.'
        )
    value = Path(ConfigPath.vault_password_path).read_text(encoding='utf-8').strip()
    if not value:
        raise VaultError('Master password file is empty.')
    return value


def _keyfile_path(keyfile: Optional[str] = None) -> Optional[str]:
    if keyfile:
        return keyfile
    if os.path.isfile(ConfigPath.vault_keyfile_path):
        return ConfigPath.vault_keyfile_path
    return None


def create_vault(
    mnemonic: str,
    master_password: str,
    *,
    write_password_file: bool = True,
    overwrite: bool = False,
) -> VaultStatus:
    """Create KeePass DB, key file, and optional master.password file."""
    PyKeePass, create_database = _require_pykeepass()
    mnemonic = mnemonic.strip()
    master_password = master_password.strip()
    if not mnemonic:
        raise VaultError('Mnemonic is empty.')
    if not master_password:
        raise VaultError('Master password is empty.')

    ensure_secrets_dir()
    db_path = ConfigPath.vault_database_path
    if os.path.isfile(db_path) and not overwrite:
        raise VaultError(f'Vault already exists: {db_path}')

    keyfile_path = ConfigPath.vault_keyfile_path
    key_bytes = secrets.token_bytes(64)
    with open(keyfile_path, 'wb') as f:
        f.write(key_bytes)
    try:
        os.chmod(keyfile_path, 0o600)
    except OSError:
        pass

    if write_password_file:
        with open(ConfigPath.vault_password_path, 'w', encoding='utf-8') as f:
            f.write(master_password + '\n')
        try:
            os.chmod(ConfigPath.vault_password_path, 0o600)
        except OSError:
            pass

    if os.path.isfile(db_path):
        os.remove(db_path)

    kp = create_database(db_path, master_password, keyfile=keyfile_path)
    group = kp.add_group(kp.root_group, VAULT_GROUP)
    kp.add_entry(group, VAULT_ENTRY_TITLE, username=VAULT_ENTRY_USER, password=mnemonic)
    kp.save()
    try:
        os.chmod(db_path, 0o600)
    except OSError:
        pass

    _write_meta()
    unlock(master_password=master_password, keyfile=keyfile_path)
    return get_status()


def unlock(
    *,
    master_password: Optional[str] = None,
    keyfile: Optional[str] = None,
) -> None:
    global _session_database
    PyKeePass, _ = _require_pykeepass()
    if not os.path.isfile(ConfigPath.vault_database_path):
        raise VaultError(f'Vault database not found: {ConfigPath.vault_database_path}')

    password = _read_master_password(master_password)
    key_path = _keyfile_path(keyfile)
    if not key_path:
        raise VaultLockedError(
            f'Key file missing: {ConfigPath.vault_keyfile_path}\n'
            'Copy wallet.key from your USB stick before unlocking.'
        )

    _session_database = PyKeePass(
        ConfigPath.vault_database_path,
        password=password,
        keyfile=key_path,
    )


def lock() -> None:
    global _session_database
    _session_database = None


def _get_open_database():
    if _session_database is None:
        if get_status().unlock_files_ready:
            unlock()
        else:
            raise VaultLockedError(
                'Vault is locked. Provide master.password and wallet.key, or unlock from the GUI.'
            )
    return _session_database


def _find_mnemonic_entry(kp):
    entries = kp.find_entries(title=VAULT_ENTRY_TITLE, first=False) or []
    if not entries:
        entries = kp.find_entries(title='wallet_1', first=False) or []
    if not entries:
        raise VaultError(f'Mnemonic entry "{VAULT_ENTRY_TITLE}" not found in vault.')
    return entries[0]


def get_mnemonic() -> str:
    kp = _get_open_database()
    entry = _find_mnemonic_entry(kp)
    value = (entry.password or '').strip()
    if not value:
        raise VaultError('Mnemonic entry in vault is empty.')
    return value


def set_mnemonic(mnemonic: str) -> None:
    mnemonic = mnemonic.strip()
    if not mnemonic:
        raise VaultError('Mnemonic is empty.')
    kp = _get_open_database()
    entry = _find_mnemonic_entry(kp)
    entry.password = mnemonic
    kp.save()


def mnemonic_is_configured() -> bool:
    return get_status().vault_initialized
