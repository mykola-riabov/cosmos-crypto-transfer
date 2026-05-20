"""Short wallet ids: w1, w2, … (legacy wallet_1 → w1)."""

from __future__ import annotations

import re

DEFAULT_WALLET_ID = 'w1'
_ID_RE = re.compile(r'^w(\d+)$', re.IGNORECASE)
_LEGACY_RE = re.compile(r'^wallet_(\d+)$', re.IGNORECASE)
_WALLET_ATTR_RE = re.compile(r'^(?:wallet_(\d+)|w(\d+))_(.+)_chain$', re.IGNORECASE)
_BOOK_NAME_RE = re.compile(r'^(?:wallet_(\d+)|w(\d+))_(.+)$', re.IGNORECASE)


def normalize_wallet_id(wallet_id: str) -> str:
    """Accept w1, w2, wallet_1, or bare 1 → canonical w1."""
    raw = (wallet_id or '').strip()
    if not raw:
        return DEFAULT_WALLET_ID
    m = _ID_RE.match(raw)
    if m:
        return f'w{int(m.group(1))}'
    m = _LEGACY_RE.match(raw)
    if m:
        return f'w{int(m.group(1))}'
    if raw.isdigit():
        return f'w{int(raw)}'
    raise ValueError(f'Invalid wallet id: {wallet_id!r} (use w1, w2, …)')


def wallet_sort_key(wallet_id: str) -> tuple:
    wid = normalize_wallet_id(wallet_id)
    m = _ID_RE.match(wid)
    return (int(m.group(1)) if m else 9999, wid)


def book_entry_name(wallet_id: str, network: str) -> str:
    return f'{normalize_wallet_id(wallet_id)}_{network}'


def canonical_book_name(name: str) -> str:
    """Normalize address-book row keys: ``wallet_1_osmosis`` and ``w1_osmosis`` → ``w1_osmosis``."""
    raw = (name or '').strip()
    m = _BOOK_NAME_RE.match(raw)
    if not m:
        return raw
    num = m.group(1) or m.group(2)
    net = (m.group(3) or '').lower()
    return f'w{int(num)}_{net}'


def wallet_id_from_book_name(name: str) -> str:
    """w1_agoric or legacy wallet_1_agoric → w1."""
    if not name:
        return DEFAULT_WALLET_ID
    m = _BOOK_NAME_RE.match(name.strip())
    if m:
        num = m.group(1) or m.group(2)
        return f'w{int(num)}'
    parts = name.rsplit('_', 1)
    if len(parts) == 2 and parts[1] and not parts[1][0].isdigit():
        return normalize_wallet_id(parts[0])
    return normalize_wallet_id(name)


def parse_wallet_attr(name: str):
    """Return (wallet_id, chain_name) from w1_osmosis_chain or wallet_1_osmosis_chain."""
    m = _WALLET_ATTR_RE.match((name or '').strip())
    if not m:
        return None
    num = m.group(1) or m.group(2)
    return f'w{int(num)}', m.group(3)


def wallet_attr_name(wallet_id: str, chain_name: str) -> str:
    return f'{normalize_wallet_id(wallet_id)}_{chain_name}_chain'


def address_attr_name(wallet_id: str, chain_name: str) -> str:
    return f'address_{normalize_wallet_id(wallet_id)}_{chain_name}_chain'
