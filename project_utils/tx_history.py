"""Persist IBC transfer attempts for the History tab."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import List, Optional

from config.config_path_files import PathFileName

_MAX_ENTRIES = 2000


def tx_history_path() -> str:
    return PathFileName().tx_history


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_tx_history(path: Optional[str] = None) -> List[dict]:
    path = path or tx_history_path()
    if not os.path.isfile(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return []


def append_tx_record(
    *,
    status: str,
    source: str,
    destination: str,
    symbol: str,
    amount: str,
    gas: int,
    channel: str,
    tx_hash: str = '',
    error: str = '',
    sender_address: str = '',
    receiver_address: str = '',
    timeout_mode: str = 'time',
    timeout_value: str = '120',
    timeout_display: str = '',
    path: Optional[str] = None,
) -> dict:
    path = path or tx_history_path()
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    record = {
        'time': _utc_now(),
        'status': status,
        'source': source,
        'destination': destination,
        'symbol': symbol,
        'amount': str(amount),
        'gas': int(gas),
        'channel': channel,
        'tx_hash': tx_hash or '',
        'error': (error or '')[:4000],
        'sender_address': sender_address,
        'receiver_address': receiver_address,
        'timeout_mode': timeout_mode,
        'timeout_value': str(timeout_value),
        'timeout_display': timeout_display,
    }
    entries = load_tx_history(path)
    if tx_hash and entries:
        last = entries[0]
        if last.get('tx_hash') == tx_hash and last.get('status') == status:
            return last
    entries.insert(0, record)
    entries = entries[:_MAX_ENTRIES]
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2)
    return record
