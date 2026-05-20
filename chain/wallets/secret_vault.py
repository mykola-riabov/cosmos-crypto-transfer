"""KeePass vault: per-wallet mnemonic (w1_mnemonic) or private key (w1_private_key)."""
from __future__ import annotations

import json
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

from config.config_path import ConfigPath
from project_utils.wallet_ids import DEFAULT_WALLET_ID, normalize_wallet_id

VAULT_GROUP = 'CosmosTransfer'
VAULT_ENTRY_USER = 'cosmos-crypto-transfer'
_MNEMONIC_TITLE_RE = re.compile(r'^(?:wallet_(\d+)|w(\d+))_mnemonic$', re.IGNORECASE)
_PRIVATE_KEY_TITLE_RE = re.compile(r'^(?:wallet_(\d+)|w(\d+))_private_key$', re.IGNORECASE)

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


def _entry_title(wallet_id: str, kind: str) -> str:
    wid = normalize_wallet_id(wallet_id)
    if kind not in ('mnemonic', 'private_key'):
        raise VaultError(f'Unknown secret kind: {kind}')
    return f'{wid}_{kind}'


def wallet_id_from_entry_title(title: str) -> Optional[Tuple[str, str]]:
    title = (title or '').strip()
    for pattern, kind in ((_MNEMONIC_TITLE_RE, 'mnemonic'), (_PRIVATE_KEY_TITLE_RE, 'private_key')):
        m = pattern.match(title)
        if m:
            num = m.group(1) or m.group(2)
            return f'w{int(num)}', kind
    if title in ('wallet_1', 'wallet_1_mnemonic'):
        return DEFAULT_WALLET_ID, 'mnemonic'
    return None


def _require_pykeepass():
    try:
        from pykeepass import PyKeePass, create_database  # noqa: F401
    except ImportError as exc:
        raise VaultError('pykeepass is not installed. Run: pip install pykeepass') from exc
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
        'version': 3,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'group': VAULT_GROUP,
        'project_slug': ConfigPath.secrets_slug,
        'wallet_id_format': 'w1',
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


def _vault_group(kp):
    group = kp.find_groups(name=VAULT_GROUP, first=True)
    if group is None:
        group = kp.add_group(kp.root_group, VAULT_GROUP)
    return group


def create_vault(
    mnemonic: str,
    master_password: str,
    *,
    wallet_id: str = DEFAULT_WALLET_ID,
    write_password_file: bool = True,
    overwrite: bool = False,
) -> VaultStatus:
    """Create KeePass DB and store first wallet mnemonic."""
    store_wallet_secret(wallet_id, 'mnemonic', mnemonic, master_password=master_password,
                        write_password_file=write_password_file, create_vault=True, overwrite=overwrite)
    return get_status()


def unlock(*, master_password: Optional[str] = None, keyfile: Optional[str] = None) -> None:
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


def store_wallet_secret(
    wallet_id: str,
    kind: str,
    secret: str,
    *,
    master_password: Optional[str] = None,
    write_password_file: bool = True,
    create_vault: bool = False,
    overwrite: bool = False,
) -> None:
    secret = secret.strip()
    if not secret:
        raise VaultError('Secret is empty.')
    wid = normalize_wallet_id(wallet_id)
    title = _entry_title(wid, kind)

    if create_vault:
        PyKeePass, create_database = _require_pykeepass()
        mp = (master_password or '').strip()
        if not mp:
            raise VaultError('Master password is required to create the vault.')
        ensure_secrets_dir()
        db_path = ConfigPath.vault_database_path
        if os.path.isfile(db_path) and not overwrite:
            raise VaultError(f'Vault already exists: {db_path}')
        keyfile_path = ConfigPath.vault_keyfile_path
        with open(keyfile_path, 'wb') as f:
            f.write(secrets.token_bytes(64))
        try:
            os.chmod(keyfile_path, 0o600)
        except OSError:
            pass
        if write_password_file:
            with open(ConfigPath.vault_password_path, 'w', encoding='utf-8') as f:
                f.write(mp + '\n')
        if os.path.isfile(db_path):
            os.remove(db_path)
        kp = create_database(db_path, mp, keyfile=keyfile_path)
        group = kp.add_group(kp.root_group, VAULT_GROUP)
        kp.add_entry(group, title, username=VAULT_ENTRY_USER, password=secret)
        kp.save()
        _write_meta()
        unlock(master_password=mp, keyfile=keyfile_path)
        return

    kp = _get_open_database()
    group = _vault_group(kp)
    entries = kp.find_entries(title=title, first=False) or []
    if entries:
        entries[0].password = secret
    else:
        kp.add_entry(group, title, username=VAULT_ENTRY_USER, password=secret)
    kp.save()


def _find_entry(kp, wallet_id: str, kind: str):
    title = _entry_title(wallet_id, kind)
    entries = kp.find_entries(title=title, first=False) or []
    if entries:
        return entries[0]
    if kind == 'mnemonic' and normalize_wallet_id(wallet_id) == DEFAULT_WALLET_ID:
        legacy = kp.find_entries(title='wallet_1_mnemonic', first=False) or []
        if legacy:
            return legacy[0]
        legacy = kp.find_entries(title='wallet_1', first=False) or []
        if legacy:
            return legacy[0]
    raise VaultError(f'Secret "{title}" not found in vault.')


def list_stored_wallet_ids() -> List[str]:
    if not get_status().vault_initialized:
        return []
    try:
        kp = _get_open_database()
    except VaultLockedError:
        return []
    ids = set()
    for entry in kp.find_entries(group=_vault_group(kp), first=False) or []:
        parsed = wallet_id_from_entry_title(entry.title)
        if parsed:
            ids.add(parsed[0])
    return sorted(ids, key=lambda w: int(w[1:]) if w.startswith('w') and w[1:].isdigit() else 9999)


def get_wallet_key_type(wallet_id: str) -> str:
    wid = normalize_wallet_id(wallet_id)
    if has_mnemonic(wid):
        return 'mnemonic'
    if has_private_key(wid):
        return 'private_key'
    raise VaultError(f'No secret stored for {wid}')


def has_mnemonic(wallet_id: str) -> bool:
    return _has_kind(wallet_id, 'mnemonic')


def has_private_key(wallet_id: str) -> bool:
    return _has_kind(wallet_id, 'private_key')


def has_wallet_secret(wallet_id: str) -> bool:
    return has_mnemonic(wallet_id) or has_private_key(wallet_id)


def _has_kind(wallet_id: str, kind: str) -> bool:
    if not get_status().vault_initialized:
        return False
    try:
        kp = _get_open_database()
        _find_entry(kp, wallet_id, kind)
        return True
    except VaultError:
        return False


def get_mnemonic(wallet_id: str = DEFAULT_WALLET_ID) -> str:
    kp = _get_open_database()
    entry = _find_entry(kp, wallet_id, 'mnemonic')
    value = (entry.password or '').strip()
    if not value:
        raise VaultError('Mnemonic entry in vault is empty.')
    return value


def get_private_key_hex(wallet_id: str) -> str:
    kp = _get_open_database()
    entry = _find_entry(kp, wallet_id, 'private_key')
    value = (entry.password or '').strip()
    if not value:
        raise VaultError('Private key entry in vault is empty.')
    return value


def store_mnemonic(wallet_id: str, mnemonic: str) -> None:
    store_wallet_secret(wallet_id, 'mnemonic', mnemonic)


def store_private_key(wallet_id: str, private_key_hex: str) -> None:
    from project_utils.wallet_mnemonic import parse_private_key_hex

    store_wallet_secret(wallet_id, 'private_key', parse_private_key_hex(private_key_hex).hex())


def set_mnemonic(mnemonic: str, wallet_id: str = DEFAULT_WALLET_ID) -> None:
    store_mnemonic(wallet_id, mnemonic)


def delete_wallet_secrets(wallet_id: str) -> None:
    wid = normalize_wallet_id(wallet_id)
    stored = list_stored_wallet_ids()
    if wid in stored and len(stored) <= 1:
        raise VaultError('Cannot delete the only wallet in the vault.')
    kp = _get_open_database()
    for kind in ('mnemonic', 'private_key'):
        try:
            entry = _find_entry(kp, wid, kind)
            kp.delete_entry(entry)
        except VaultError:
            pass
    kp.save()


def delete_mnemonic(wallet_id: str) -> None:
    delete_wallet_secrets(wallet_id)


def mnemonic_is_configured(wallet_id: Optional[str] = None) -> bool:
    if not get_status().vault_initialized:
        return False
    if wallet_id:
        return has_wallet_secret(wallet_id)
    return bool(list_stored_wallet_ids())
