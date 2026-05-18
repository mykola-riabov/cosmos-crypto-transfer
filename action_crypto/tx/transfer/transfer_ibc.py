import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from cosmpy.aerial.client.utils import prepare_and_broadcast_basic_transaction
from cosmpy.aerial.tx import Transaction, TxFee
from cosmpy.protos.cosmos.base.v1beta1.coin_pb2 import Coin
from cosmpy.protos.ibc.applications.transfer.v1.tx_pb2 import MsgTransfer

from project_utils.address_book import resolve_wallets
from project_utils.denoms_lookup import convert_amount, load_denoms_index, resolve_denom
from project_utils.logging_setup import setup_logging


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
            f'Timeout: {self.timeout_second}s ({self.formatted_dt})',
        ]


def prepare_ibc_transfer(
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
):
    nanos_per_second = int(10 ** 9)
    time_out = (int(time.time()) * nanos_per_second) + (nanos_per_second * timeout_second)
    formatted_dt = datetime.fromtimestamp(time_out // nanos_per_second, tz=timezone.utc).strftime(
        '%Y-%m-%d %H:%M:%S UTC'
    )
    amount_token = float(amount)

    with open(path_address_book, 'r', encoding='utf-8') as f1, open(path_denoms_book, 'r', encoding='utf-8') as f2:
        data_address = json.load(f1)
        sender_name, sender_address, receiver_name, receiver_address = resolve_wallets(
            data_address, sender_wallet, receiver_wallet
        )
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
        timeout_second=timeout_second,
        formatted_dt=formatted_dt,
        channel_ibc=channel_ibc,
        gas=gas,
        transaction=tx,
    )


def broadcast_ibc_transfer(preview: IbcTransferPreview, client, wallet) -> str:
    logger = setup_logging()
    tx = prepare_and_broadcast_basic_transaction(
        client,
        preview.transaction,
        wallet,
        fee=TxFee(gas_limit=preview.gas),
    )
    tx_hash = tx.tx_hash
    logger.info(
        'IBC transfer: sender_wallet=%s sender_address=%s receiver_wallet=%s receiver_address=%s '
        'denom=%s symbol=%s network=%s decimal=%s timeout=%s timeout_seconds=%s timeout_date=%s '
        'amount=%s amount_raw=%s tx_hash=%s',
        preview.sender_name,
        preview.sender_address,
        preview.receiver_name,
        preview.receiver_address,
        preview.denom_contract,
        preview.symbol,
        preview.network,
        preview.decimal_token,
        preview.time_out,
        preview.timeout_second,
        preview.formatted_dt,
        preview.amount_token,
        preview.amount_raw,
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
):
    preview = prepare_ibc_transfer(
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
    )

    for line in preview.summary_lines():
        print(line)
    print('=====================')

    if interactive:
        entered = input(f'Re-enter amount to confirm ({preview.amount_token}): ').strip()
        try:
            if float(entered) != preview.amount_token:
                print('Amount mismatch. Operation cancelled.')
                return None
        except ValueError:
            print('Invalid amount. Operation cancelled.')
            return None
        if input('Type "yes" to execute the transaction: ').strip().lower() != 'yes':
            print('Operation cancelled by the user.')
            return None
    else:
        if confirm_amount is None or float(confirm_amount) != preview.amount_token:
            raise ValueError('Amount confirmation failed')
        if not confirm_execute:
            raise ValueError('Execution not confirmed')

    tx_hash = broadcast_ibc_transfer(preview, client, wallet)
    print('Transaction successfully executed!')
    print(f'Transaction hash: {tx_hash}')
    return tx_hash
