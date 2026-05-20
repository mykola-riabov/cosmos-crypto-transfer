"""Derive LocalWallet / addresses for w1, w2, … on any enabled chain."""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple

from bip_utils import Bip32KeyIndex, Bip32Slip10Secp256k1, Bip39SeedGenerator, Bip44, Bip44Coins
from cosmpy.aerial.wallet import LocalWallet
from cosmpy.crypto.keypairs import PrivateKey

from config.config_path_files import PathFileName
from project_utils.wallet_ids import (
    address_attr_name,
    parse_wallet_attr,
    wallet_attr_name,
)
from project_utils.wallet_ids import normalize_wallet_id as norm_wid

_WALLET_CACHE: Dict[Tuple[str, str], LocalWallet] = {}
_CHAIN_SPECS: Optional[Dict[str, Tuple[str, Optional[int]]]] = None


def clear_wallet_cache(wallet_id: Optional[str] = None) -> None:
    global _WALLET_CACHE, _CHAIN_SPECS
    if wallet_id is None:
        _WALLET_CACHE.clear()
        _CHAIN_SPECS = None
        return
    wid = norm_wid(wallet_id)
    _WALLET_CACHE = {k: v for k, v in _WALLET_CACHE.items() if k[0] != wid}


def load_chain_specs(enabled_networks: Optional[set] = None) -> Dict[str, Tuple[str, Optional[int]]]:
    global _CHAIN_SPECS
    paths = PathFileName()
    if not os.path.isfile(paths.data_cosmos_file_name):
        if _CHAIN_SPECS is not None:
            return _CHAIN_SPECS
        return {}
    with open(paths.data_cosmos_file_name, 'r', encoding='utf-8') as f:
        chains = json.load(f)
    specs: Dict[str, Tuple[str, Optional[int]]] = {}
    enabled_set = set(enabled_networks) if enabled_networks is not None else None
    for row in chains:
        name = row.get('chain_name')
        if not name:
            continue
        if enabled_set is not None and name not in enabled_set:
            continue
        slip = row.get('slip44')
        specs[name] = (row.get('bech32_prefix', 'cosmos'), int(slip) if slip is not None else None)
    _CHAIN_SPECS = specs
    return specs


def _make_wallet_from_mnemonic(mnemonic: str, prefix: str, slip44: Optional[int]) -> LocalWallet:
    if slip44 is not None and slip44 != 118:
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
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()
    ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.COSMOS).DeriveDefaultPath()
    return LocalWallet(PrivateKey(ctx.PrivateKey().Raw().ToBytes()), prefix=prefix)


def _make_wallet_from_private_key(key_bytes: bytes, prefix: str) -> LocalWallet:
    return LocalWallet(PrivateKey(key_bytes), prefix=prefix)


def get_local_wallet(wallet_id: str, chain_name: str) -> LocalWallet:
    wid = norm_wid(wallet_id)
    key = (wid, chain_name)
    if key in _WALLET_CACHE:
        return _WALLET_CACHE[key]
    specs = load_chain_specs()
    if chain_name not in specs:
        raise KeyError(f'Unknown chain: {chain_name}')
    prefix, slip44 = specs[chain_name]

    from project_utils.wallet_profiles import get_profile

    key_type = get_profile(wid).get('key_type', 'mnemonic')
    if key_type == 'private_key':
        from chain.wallets.secret_vault import get_private_key_hex
        from project_utils.wallet_mnemonic import parse_private_key_hex

        key_bytes = parse_private_key_hex(get_private_key_hex(wid))
        wallet = _make_wallet_from_private_key(key_bytes, prefix)
    else:
        from chain.wallets.get_creds import get_mnemonic

        wallet = _make_wallet_from_mnemonic(get_mnemonic(wid), prefix, slip44)
    _WALLET_CACHE[key] = wallet
    return wallet


def get_address(wallet_id: str, chain_name: str) -> str:
    return str(get_local_wallet(wallet_id, chain_name).address())


def resolve_wallet_attr(wallet_attr: str) -> str:
    """Map legacy wallet_1_osmosis_chain → active w2_osmosis_chain."""
    from project_utils.wallet_profiles import get_active_wallet_id

    parsed = parse_wallet_attr(wallet_attr)
    if not parsed:
        return wallet_attr
    _wid, chain = parsed
    return wallet_attr_name(get_active_wallet_id(), chain)


def write_all_wallet_addresses_json(
    file_path: str,
    *,
    enabled_networks: Optional[set] = None,
    wallet_ids: Optional[List[str]] = None,
) -> None:
    from chain.wallets.secret_vault import list_stored_wallet_ids

    specs = load_chain_specs(enabled_networks)
    if wallet_ids is None:
        wallet_ids = list_stored_wallet_ids()
    data = {}
    for wid in wallet_ids:
        for chain_name in sorted(specs.keys(), key=str.lower):
            try:
                data[address_attr_name(wid, chain_name)] = get_address(wid, chain_name)
            except Exception:
                continue
    os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
