"""Query transaction results via REST JSON (avoids Cosmpy proto mismatches on newer chains)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import requests


class TxNotFoundYet(Exception):
    """Tx is not indexed yet — caller should retry."""


class TxQueryTimeout(Exception):
    """Tx did not appear within the wait window."""


@dataclass
class TxQueryResult:
    code: int
    raw_log: str
    gas_wanted: int
    gas_used: int
    tx_hash: str

    @property
    def is_successful(self) -> bool:
        return self.code == 0


def normalize_tx_hash(tx_hash: str) -> str:
    h = (tx_hash or '').strip().upper()
    if h.startswith('0X'):
        h = h[2:]
    return h


def rest_base_from_client_url(url: str) -> str:
    raw = (url or '').strip()
    if raw.lower().startswith('rest+'):
        return raw[5:].rstrip('/')
    return raw.rstrip('/')


def fetch_tx_by_hash(rest_base: str, tx_hash: str, *, timeout: float = 15.0) -> TxQueryResult:
    """Load tx status from LCD/REST. Raises TxNotFoundYet if not indexed."""
    base = rest_base_from_client_url(rest_base)
    if not base:
        raise ValueError('REST base URL is empty')
    h = normalize_tx_hash(tx_hash)
    response = requests.get(f'{base}/cosmos/tx/v1beta1/txs/{h}', timeout=timeout)
    if response.status_code == 404:
        raise TxNotFoundYet(h)
    response.raise_for_status()
    data = response.json()
    tx_resp = data.get('tx_response') or data.get('txResponse') or {}
    if not tx_resp:
        raise TxNotFoundYet(h)
    code = int(tx_resp.get('code', -1))
    return TxQueryResult(
        code=code,
        raw_log=str(tx_resp.get('raw_log') or tx_resp.get('rawLog') or ''),
        gas_wanted=int(tx_resp.get('gas_wanted') or tx_resp.get('gasWanted') or 0),
        gas_used=int(tx_resp.get('gas_used') or tx_resp.get('gasUsed') or 0),
        tx_hash=h,
    )


def wait_for_tx_rest(
    rest_base: str,
    tx_hash: str,
    *,
    timeout_sec: float = 90.0,
    poll_sec: float = 2.0,
) -> TxQueryResult:
    """Poll REST until the tx is indexed or timeout."""
    deadline = time.monotonic() + max(timeout_sec, 1.0)
    last_error: Optional[Exception] = None
    while time.monotonic() < deadline:
        try:
            return fetch_tx_by_hash(rest_base, tx_hash)
        except TxNotFoundYet as exc:
            last_error = exc
            time.sleep(max(poll_sec, 0.5))
        except requests.RequestException as exc:
            last_error = exc
            time.sleep(max(poll_sec, 0.5))
    raise TxQueryTimeout(
        f'Transaction {normalize_tx_hash(tx_hash)} not found within {int(timeout_sec)}s'
    ) from last_error
