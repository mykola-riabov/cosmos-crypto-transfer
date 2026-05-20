"""Osmosis swaps via Skip route/msgs + Cosmpy signing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from cosmpy.aerial.client.utils import prepare_and_broadcast_basic_transaction
from cosmpy.aerial.tx import Transaction, TxFee
from cosmpy.protos.cosmos.base.v1beta1.coin_pb2 import Coin
from cosmpy.protos.cosmwasm.wasm.v1.tx_pb2 import MsgExecuteContract

from project_utils.chain_ids import osmosis_chain_id
from project_utils.denoms_lookup import convert_amount
from project_utils.skip_client import SkipApiError, fetch_msgs, fetch_route
from project_utils.token_catalog import get_token_catalog
from project_utils.logging_setup import setup_logging

SWAP_NETWORK = 'osmosis'
DEFAULT_SLIPPAGE_PERCENT = 1.5
DEFAULT_SWAP_GAS = 1_000_000


def _raw_to_token(amount_raw: int, decimals: int) -> float:
    return float(Decimal(amount_raw) / (Decimal(10) ** int(decimals)))


@dataclass
class SwapPreview:
    network: str
    chain_id: str
    symbol_in: str
    symbol_out: str
    denom_in: str
    denom_out: str
    decimal_in: int
    decimal_out: int
    amount_in_token: float
    amount_in_raw: str
    estimated_out_raw: str
    estimated_out_token: float
    min_amount_out_raw: str
    min_amount_out_token: float
    slippage_percent: float
    sender_name: str
    sender_address: str
    wallet_attr: str
    gas: int
    pool_ids: List[str]
    price_impact_percent: str
    txs_required: int
    transaction: Transaction
    route: Dict[str, Any]
    msgs: Dict[str, Any]

    def summary_lines(self) -> List[str]:
        pools = ', '.join(self.pool_ids) if self.pool_ids else '—'
        return [
            f'Network: {self.network} ({self.chain_id})',
            f'Sender: {self.sender_name} ({self.sender_address})',
            f'Swap: {self.amount_in_token:g} {self.symbol_in} → ~{self.estimated_out_token:g} {self.symbol_out}',
            f'Min receive ({self.slippage_percent:g}% slippage): {self.min_amount_out_token:g} {self.symbol_out}',
            f'Raw in: {self.amount_in_raw} | est. out: {self.estimated_out_raw} | min out: {self.min_amount_out_raw}',
            f'Pools: {pools}',
            f'Price impact: {self.price_impact_percent or "—"}% | Txs required: {self.txs_required}',
        ]


def _resolve_sender(
    path_address_book: str,
    wallet_key: str,
) -> Tuple[str, str]:
    with open(path_address_book, 'r', encoding='utf-8') as f:
        data_address = json.load(f)
    from project_utils.address_book import resolve_wallets

    sender_name, sender_address, _, _ = resolve_wallets(
        data_address, wallet_key, wallet_key
    )
    return sender_name, sender_address


def _resolve_denoms(network: str, symbol_in: str, symbol_out: str, path_denoms_book: str):
    catalog = get_token_catalog()
    try:
        denom_in, decimal_in = catalog.resolve_denom(network, symbol_in)
        denom_out, decimal_out = catalog.resolve_denom(network, symbol_out)
    except ValueError:
        from project_utils.denoms_lookup import load_denoms_index, resolve_denom

        denom_index = load_denoms_index(path_denoms_book)
        denom_in, decimal_in = resolve_denom(denom_index, symbol_in, network)
        denom_out, decimal_out = resolve_denom(denom_index, symbol_out, network)
    return denom_in, decimal_in, denom_out, decimal_out


def _extract_pool_ids(route: Dict[str, Any]) -> List[str]:
    pools: List[str] = []
    for op in route.get('operations') or []:
        swap = op.get('swap') or {}
        swap_in = swap.get('swap_in') or swap.get('smart_swap_in') or {}
        for hop in swap_in.get('swap_operations') or []:
            pool = hop.get('pool')
            if pool is not None:
                pools.append(str(pool))
    return pools


def _price_impact(route: Dict[str, Any]) -> str:
    value = route.get('swap_price_impact_percent')
    if value is None or value == '':
        return ''
    return str(value)


def build_transaction_from_skip_msgs(
    msgs_response: Dict[str, Any],
    *,
    chain_id: str,
    signer_address: str,
) -> Transaction:
    """Turn Skip /msgs cosmos_tx entries into a Cosmpy Transaction."""
    tx = Transaction()
    added = 0
    for skip_tx in msgs_response.get('txs') or []:
        cosmos = skip_tx.get('cosmos_tx') or {}
        if cosmos.get('chain_id') and cosmos['chain_id'] != chain_id:
            raise ValueError(
                f'Skip returned tx for {cosmos["chain_id"]}, expected {chain_id}. '
                'Multi-chain swaps are not supported yet.'
            )
        signer = (cosmos.get('signer_address') or signer_address).strip()
        if signer.lower() != signer_address.lower():
            raise ValueError(
                f'Skip signer {signer} does not match wallet address {signer_address}.'
            )
        for raw in cosmos.get('msgs') or []:
            type_url = raw.get('msg_type_url', '')
            if type_url != '/cosmwasm.wasm.v1.MsgExecuteContract':
                raise ValueError(
                    f'Unsupported Skip message type {type_url}. '
                    'Update the app or try a simpler token pair on Osmosis.'
                )
            body = json.loads(raw['msg'])
            inner = body.get('msg')
            if inner is None:
                raise ValueError('Skip MsgExecuteContract missing inner msg payload.')
            funds = [
                Coin(denom=item['denom'], amount=str(item['amount']))
                for item in body.get('funds') or []
            ]
            tx.add_message(
                MsgExecuteContract(
                    sender=signer_address,
                    contract=body['contract'],
                    msg=json.dumps(inner).encode('utf-8'),
                    funds=funds,
                )
            )
            added += 1
    if added == 0:
        raise ValueError('Skip msgs response contained no signable Cosmos messages.')
    return tx


def prepare_skip_swap(
    symbol_in: str,
    symbol_out: str,
    amount_in: float,
    path_address_book: str,
    path_denoms_book: str,
    wallet_key: str,
    wallet_attr: str,
    *,
    slippage_percent: float = DEFAULT_SLIPPAGE_PERCENT,
    gas: int = DEFAULT_SWAP_GAS,
    split_routes: bool = False,
    network: str = SWAP_NETWORK,
) -> SwapPreview:
    """Quote via Skip and build an unsigned Cosmpy transaction."""
    symbol_in = (symbol_in or '').strip()
    symbol_out = (symbol_out or '').strip()
    if not symbol_in or not symbol_out:
        raise ValueError('Select tokens to swap.')
    if symbol_in.upper() == symbol_out.upper():
        raise ValueError('Input and output token must differ.')

    chain_id = osmosis_chain_id()
    if network != SWAP_NETWORK:
        raise ValueError(f'Swap is only supported on {SWAP_NETWORK} for now.')

    denom_in, decimal_in, denom_out, decimal_out = _resolve_denoms(
        network, symbol_in, symbol_out, path_denoms_book
    )
    amount_raw = str(convert_amount(float(amount_in), decimal_in))
    if int(amount_raw) <= 0:
        raise ValueError('Amount must be greater than zero.')

    sender_name, sender_address = _resolve_sender(path_address_book, wallet_key)

    try:
        route = fetch_route(
            amount_in=amount_raw,
            source_denom=denom_in,
            source_chain_id=chain_id,
            dest_denom=denom_out,
            dest_chain_id=chain_id,
            split_routes=split_routes,
        )
    except SkipApiError:
        raise
    except Exception as exc:
        raise RuntimeError(f'Skip route failed: {exc}') from exc

    txs_required = int(route.get('txs_required') or 1)
    if txs_required > 1:
        raise ValueError(
            f'This swap needs {txs_required} transactions. '
            'Use a direct pair or enable fewer hops (same-chain only for now).'
        )

    try:
        msgs = fetch_msgs(
            route,
            address_list=[sender_address],
            slippage_tolerance_percent=str(slippage_percent),
        )
    except SkipApiError:
        raise
    except Exception as exc:
        raise RuntimeError(f'Skip msgs failed: {exc}') from exc

    estimated_raw = str(
        msgs.get('min_amount_out')
        or route.get('estimated_amount_out')
        or route.get('amount_out')
        or '0'
    )
    # min_amount_out from msgs is after slippage; estimated from route is pre-slippage
    est_out_raw = str(route.get('estimated_amount_out') or route.get('amount_out') or estimated_raw)
    min_out_raw = str(msgs.get('min_amount_out') or estimated_raw)

    transaction = build_transaction_from_skip_msgs(
        msgs,
        chain_id=chain_id,
        signer_address=sender_address,
    )

    return SwapPreview(
        network=network,
        chain_id=chain_id,
        symbol_in=symbol_in,
        symbol_out=symbol_out,
        denom_in=denom_in,
        denom_out=denom_out,
        decimal_in=decimal_in,
        decimal_out=decimal_out,
        amount_in_token=float(amount_in),
        amount_in_raw=amount_raw,
        estimated_out_raw=est_out_raw,
        estimated_out_token=_raw_to_token(int(est_out_raw), decimal_out),
        min_amount_out_raw=min_out_raw,
        min_amount_out_token=_raw_to_token(int(min_out_raw), decimal_out),
        slippage_percent=float(slippage_percent),
        sender_name=sender_name,
        sender_address=sender_address,
        wallet_attr=wallet_attr,
        gas=int(gas),
        pool_ids=_extract_pool_ids(route),
        price_impact_percent=_price_impact(route),
        txs_required=txs_required,
        transaction=transaction,
        route=route,
        msgs=msgs,
    )


def broadcast_skip_swap(
    preview: SwapPreview,
    client,
    wallet,
    gas_limit: Optional[int] = None,
) -> str:
    logger = setup_logging()
    limit = int(gas_limit) if gas_limit is not None else preview.gas
    tx = prepare_and_broadcast_basic_transaction(
        client,
        preview.transaction,
        wallet,
        fee=TxFee(gas_limit=limit),
    )
    tx_hash = tx.tx_hash
    logger.info(
        'Skip swap: sender=%s %s→%s amount_in=%s est_out=%s tx_hash=%s',
        preview.sender_address,
        preview.symbol_in,
        preview.symbol_out,
        preview.amount_in_raw,
        preview.estimated_out_raw,
        tx_hash,
    )
    return tx_hash
