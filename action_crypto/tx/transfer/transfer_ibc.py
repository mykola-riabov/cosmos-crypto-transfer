import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from cosmpy.aerial.client.utils import prepare_and_broadcast_basic_transaction
from cosmpy.aerial.tx import Transaction, TxFee
from cosmpy.protos.cosmos.base.v1beta1.coin_pb2 import Coin
from cosmpy.protos.ibc.applications.transfer.v1.tx_pb2 import MsgTransfer
from cosmpy.protos.ibc.core.client.v1.client_pb2 import Height

from project_utils.address_book import resolve_wallets
from project_utils.denoms_lookup import convert_amount
from project_utils.token_catalog import get_token_catalog
from project_utils.logging_setup import setup_logging

TIMEOUT_MODE_TIME = 'time'
TIMEOUT_MODE_HEIGHT = 'height'


@dataclass
class IbcTransferPreview:
    sender_name: str
    sender_address: str
    receiver_name: str
    receiver_address: str
    denom_contract: str
    symbol: str
    network: str
    decimal_token: int
    amount_token: float
    amount_raw: int
    time_out: int
    timeout_second: int
    timeout_mode: str
    timeout_value: int
    timeout_display: str
    formatted_dt: str
    channel_ibc: str
    gas: int
    transaction: Transaction

    def summary_lines(self):
        return [
            f'Sender: {self.sender_name} ({self.sender_address})',
            f'Receiver: {self.receiver_name} ({self.receiver_address})',
            f'Token: {self.symbol} on {self.network} → {self.denom_contract}',
            f'Amount: {self.amount_token} (raw {self.amount_raw})',
            f'Channel: {self.channel_ibc} | Gas: {self.gas}',
            f'Timeout: {self.timeout_display}',
        ]


def _resolve_timeout(
    timeout_mode: str,
    timeout_value: int,
    destination_rest: Optional[str],
) -> tuple[int, str, Height]:
    """Return (timeout_timestamp_nanos, display_text, timeout_height proto)."""
    mode = (timeout_mode or TIMEOUT_MODE_TIME).strip().lower()
    value = int(timeout_value)

    if mode == TIMEOUT_MODE_HEIGHT:
        from project_utils.chain_query import fetch_latest_block_height

        latest = fetch_latest_block_height(destination_rest)
        target = latest + max(value, 1)
        height = Height(revision_number=0, revision_height=target)
        display = f'height +{value} blocks → {target} (latest {latest})'
        return 0, display, height

    seconds = max(value, 1)
    nanos_per_second = int(10**9)
    time_out = (int(time.time()) * nanos_per_second) + (nanos_per_second * seconds)
    formatted_dt = datetime.fromtimestamp(time_out // nanos_per_second, tz=timezone.utc).strftime(
        '%Y-%m-%d %H:%M:%S UTC'
    )
    display = f'{seconds}s (until {formatted_dt})'
    return time_out, display, Height(revision_number=0, revision_height=0)


def prepare_ibc_transfer(
    symbol,
    network,
    path_address_book,
    path_denoms_book,
    amount,
    sender_wallet,
    receiver_wallet,
    channel_ibc,
    gas,
    timeout_mode: str = TIMEOUT_MODE_TIME,
    timeout_value: int = 120,
    destination_rest: Optional[str] = None,
    timeout_second: Optional[int] = None,
):
    """Build IBC MsgTransfer. *timeout_value* is seconds (time mode) or block count (height mode)."""
    if timeout_second is not None:
        timeout_value = int(timeout_second)
        timeout_mode = TIMEOUT_MODE_TIME

    time_out, timeout_display, timeout_height = _resolve_timeout(
        timeout_mode,
        timeout_value,
        destination_rest,
    )
    timeout_second_out = int(timeout_value) if timeout_mode == TIMEOUT_MODE_TIME else 0
    amount_token = float(amount)

    with open(path_address_book, 'r', encoding='utf-8') as f1, open(path_denoms_book, 'r', encoding='utf-8') as f2:
        data_address = json.load(f1)
        sender_name, sender_address, receiver_name, receiver_address = resolve_wallets(
            data_address, sender_wallet, receiver_wallet
        )
        catalog = get_token_catalog()
        try:
            denom_contract, decimal_token = catalog.resolve_denom(network, symbol)
        except ValueError:
            from project_utils.denoms_lookup import load_denoms_index, resolve_denom

            denom_index = load_denoms_index(path_denoms_book)
            denom_contract, decimal_token = resolve_denom(denom_index, symbol, network)
        amount_convert = convert_amount(amount_token, decimal_token)

    tx = Transaction()
    tx.add_message(
        MsgTransfer(
            source_port='transfer',
            source_channel=channel_ibc,
            token=Coin(denom=denom_contract, amount=str(amount_convert)),
            sender=sender_address,
            receiver=receiver_address,
            timeout_timestamp=time_out,
            timeout_height=timeout_height,
        )
    )

    return IbcTransferPreview(
        sender_name=sender_name,
        sender_address=sender_address,
        receiver_name=receiver_name,
        receiver_address=receiver_address,
        denom_contract=denom_contract,
        symbol=symbol,
        network=network,
        decimal_token=decimal_token,
        amount_token=amount_token,
        amount_raw=amount_convert,
        time_out=time_out,
        timeout_second=timeout_second_out,
        timeout_mode=timeout_mode,
        timeout_value=int(timeout_value),
        timeout_display=timeout_display,
        formatted_dt=timeout_display.split('until ')[-1] if 'until ' in timeout_display else timeout_display,
        channel_ibc=channel_ibc,
        gas=gas,
        transaction=tx,
    )


def _record_route_history(
    status: str,
    route_meta: dict,
    preview: IbcTransferPreview,
    *,
    gas: Optional[int] = None,
    tx_hash: str = '',
    error: str = '',
) -> None:
    if not route_meta:
        return
    try:
        from project_utils.tx_history import append_tx_record

        append_tx_record(
            status=status,
            source=route_meta.get('source_network', ''),
            destination=route_meta.get('destination_network', ''),
            symbol=preview.symbol,
            amount=str(preview.amount_token),
            gas=int(gas if gas is not None else preview.gas),
            channel=route_meta.get('channel', preview.channel_ibc),
            tx_hash=tx_hash,
            error=error,
            sender_address=preview.sender_address,
            receiver_address=preview.receiver_address,
            timeout_mode=preview.timeout_mode,
            timeout_value=str(preview.timeout_value),
            timeout_display=preview.timeout_display,
        )
    except Exception:
        pass


def broadcast_ibc_transfer(preview: IbcTransferPreview, client, wallet, gas_limit: Optional[int] = None) -> str:
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
        'IBC transfer: sender_wallet=%s sender_address=%s receiver_wallet=%s receiver_address=%s '
        'denom=%s symbol=%s network=%s decimal=%s timeout=%s timeout_mode=%s tx_hash=%s',
        preview.sender_name,
        preview.sender_address,
        preview.receiver_name,
        preview.receiver_address,
        preview.denom_contract,
        preview.symbol,
        preview.network,
        preview.decimal_token,
        preview.timeout_display,
        preview.timeout_mode,
        tx_hash,
    )
    return tx_hash


def transfer_ibc(
    symbol,
    network,
    path_address_book,
    path_denoms_book,
    timeout_second,
    amount,
    sender_wallet,
    receiver_wallet,
    channel_ibc,
    gas,
    client,
    wallet,
    interactive: bool = True,
    confirm_amount: Optional[float] = None,
    confirm_execute: bool = False,
    timeout_mode: str = TIMEOUT_MODE_TIME,
    destination_rest: Optional[str] = None,
    route_meta: Optional[dict] = None,
):
    preview = prepare_ibc_transfer(
        symbol,
        network,
        path_address_book,
        path_denoms_book,
        amount,
        sender_wallet,
        receiver_wallet,
        channel_ibc,
        gas,
        timeout_mode=timeout_mode,
        timeout_value=int(timeout_second),
        destination_rest=destination_rest,
    )

    _record_route_history('preview', route_meta, preview, gas=gas)

    for line in preview.summary_lines():
        print(line)
    print('=====================')

    if interactive:
        entered = input(f'Re-enter amount to confirm ({preview.amount_token}): ').strip()
        try:
            if float(entered) != preview.amount_token:
                print('Amount mismatch. Operation cancelled.')
                _record_route_history('cancelled', route_meta, preview, gas=gas, error='amount mismatch')
                return None
        except ValueError:
            print('Invalid amount. Operation cancelled.')
            _record_route_history('cancelled', route_meta, preview, gas=gas, error='invalid amount')
            return None
        if input('Type "yes" to execute the transaction: ').strip().lower() != 'yes':
            print('Operation cancelled by the user.')
            _record_route_history('cancelled', route_meta, preview, gas=gas, error='user declined')
            return None
    else:
        if confirm_amount is None or float(confirm_amount) != preview.amount_token:
            raise ValueError('Amount confirmation failed')
        if not confirm_execute:
            raise ValueError('Execution not confirmed')

    _record_route_history('submitted', route_meta, preview, gas=gas)
    try:
        tx_hash = broadcast_ibc_transfer(preview, client, wallet)
    except Exception as exc:
        _record_route_history('failed', route_meta, preview, gas=gas, error=str(exc))
        raise
    _record_route_history('success', route_meta, preview, gas=gas, tx_hash=tx_hash)
    print('Transaction successfully executed!')
    print(f'Transaction hash: {tx_hash}')
    return tx_hash
