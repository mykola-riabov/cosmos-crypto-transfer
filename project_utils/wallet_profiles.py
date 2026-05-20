"""Wallet profiles (w1, w2, …) and active wallet selection."""

from __future__ import annotations

import json
import os
from typing import List, Optional

from config.config_path import ConfigPath
from project_utils.wallet_ids import (
    DEFAULT_WALLET_ID,
    normalize_wallet_id,
    wallet_id_from_book_name,
    wallet_sort_key,
)

_PROFILES_FILE = 'wallet_profiles.json'


def _profiles_path() -> str:
    return os.path.join(ConfigPath.data_path, _PROFILES_FILE)


def _migrate_profile_keys(profiles: dict) -> dict:
    out = {}
    for key, val in profiles.items():
        try:
            nid = normalize_wallet_id(key)
        except ValueError:
            continue
        if not isinstance(val, dict):
            val = {'label': str(val)}
        out[nid] = val
    return out


def _default_data() -> dict:
    return {
        'active_wallet_id': DEFAULT_WALLET_ID,
        'profiles': {
            DEFAULT_WALLET_ID: {'label': 'Wallet 1', 'key_type': 'mnemonic'},
        },
    }


def load_profiles() -> dict:
    path = _profiles_path()
    if not os.path.isfile(path):
        return _default_data()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, TypeError):
        return _default_data()
    if not isinstance(data, dict):
        return _default_data()
    profiles = data.get('profiles')
    if not isinstance(profiles, dict):
        profiles = {DEFAULT_WALLET_ID: {'label': 'Wallet 1', 'key_type': 'mnemonic'}}
    profiles = _migrate_profile_keys(profiles)
    try:
        active = normalize_wallet_id(data.get('active_wallet_id') or DEFAULT_WALLET_ID)
    except ValueError:
        active = DEFAULT_WALLET_ID
    if active not in profiles:
        profiles[active] = {'label': active.upper(), 'key_type': 'mnemonic'}
    return {'active_wallet_id': active, 'profiles': profiles}


def save_profiles(data: dict) -> None:
    path = _profiles_path()
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    migrated = {
        'active_wallet_id': normalize_wallet_id(data['active_wallet_id']),
        'profiles': _migrate_profile_keys(data['profiles']),
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(migrated, f, indent=2)
        f.write('\n')


def get_profile(wallet_id: str) -> dict:
    wid = normalize_wallet_id(wallet_id)
    return load_profiles()['profiles'].get(wid, {})


def list_wallet_profiles() -> List[dict]:
    data = load_profiles()
    profiles = dict(data['profiles'])
    try:
        from chain.wallets.secret_vault import list_stored_wallet_ids

        for wid in list_stored_wallet_ids():
            profiles.setdefault(wid, {'label': wid.upper(), 'key_type': 'mnemonic'})
    except Exception:
        pass
    active = data['active_wallet_id']
    out = []
    for wid in sorted(profiles.keys(), key=wallet_sort_key):
        label = profiles[wid].get('label') or wid.upper()
        out.append({'id': wid, 'label': label, 'active': wid == active})
    return out


def get_active_wallet_id() -> str:
    return load_profiles()['active_wallet_id']


def get_active_wallet_label() -> str:
    data = load_profiles()
    wid = data['active_wallet_id']
    return data['profiles'].get(wid, {}).get('label') or wid.upper()


def set_active_wallet(wallet_id: str) -> None:
    wid = normalize_wallet_id(wallet_id)
    data = load_profiles()
    if wid not in data['profiles']:
        raise ValueError(f'Unknown wallet profile: {wid}')
    data['active_wallet_id'] = wid
    save_profiles(data)
    from project_utils.wallet_derivation import clear_wallet_cache

    clear_wallet_cache()


def rename_wallet(wallet_id: str, label: str) -> None:
    label = (label or '').strip()
    if not label:
        raise ValueError('Wallet name cannot be empty.')
    wid = normalize_wallet_id(wallet_id)
    data = load_profiles()
    if wid not in data['profiles']:
        raise ValueError(f'Unknown wallet profile: {wid}')
    data['profiles'][wid]['label'] = label
    save_profiles(data)


def next_wallet_id() -> str:
    used: set = set()
    for wid in load_profiles()['profiles']:
        try:
            used.add(normalize_wallet_id(wid))
        except ValueError:
            pass
    try:
        from chain.wallets.secret_vault import list_stored_wallet_ids

        for wid in list_stored_wallet_ids():
            used.add(wid)
    except Exception:
        pass
    for n in range(1, 1000):
        wid = f'w{n}'
        if wid not in used:
            return wid
    raise ValueError('Too many wallet profiles.')


def create_wallet(
    label: Optional[str] = None,
    wallet_id: Optional[str] = None,
    *,
    key_type: str = 'mnemonic',
) -> str:
    data = load_profiles()
    new_id = normalize_wallet_id(wallet_id) if wallet_id else next_wallet_id()
    if new_id in data['profiles']:
        raise ValueError(f'Wallet profile already exists: {new_id}')
    data['profiles'][new_id] = {
        'label': label or new_id.upper(),
        'key_type': key_type,
    }
    data['active_wallet_id'] = new_id
    save_profiles(data)
    return new_id


def ensure_default_profile() -> None:
    data = load_profiles()
    if DEFAULT_WALLET_ID not in data['profiles']:
        data['profiles'][DEFAULT_WALLET_ID] = {'label': 'Wallet 1', 'key_type': 'mnemonic'}
        save_profiles(data)


def delete_wallet(wallet_id: str) -> None:
    wid = normalize_wallet_id(wallet_id)
    data = load_profiles()
    if wid not in data['profiles']:
        raise ValueError(f'Unknown wallet profile: {wid}')
    from chain.wallets.secret_vault import has_wallet_secret, list_stored_wallet_ids

    stored = list_stored_wallet_ids()
    if has_wallet_secret(wid) and len(stored) <= 1:
        raise ValueError('Cannot delete the only wallet with stored secrets.')
    del data['profiles'][wid]
    if data['active_wallet_id'] == wid:
        remaining = sorted(data['profiles'].keys(), key=wallet_sort_key)
        data['active_wallet_id'] = remaining[0] if remaining else DEFAULT_WALLET_ID
    save_profiles(data)


def wallet_id_from_book_name_legacy(name: str) -> str:
    return wallet_id_from_book_name(name)


def row_belongs_to_active_wallet(wallet_name: str) -> bool:
    return wallet_id_from_book_name(wallet_name) == get_active_wallet_id()
