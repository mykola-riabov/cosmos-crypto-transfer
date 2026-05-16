import json
import time
from datetime import datetime, timezone

from cosmpy.aerial.client.utils import prepare_and_broadcast_basic_transaction
from cosmpy.aerial.tx import Transaction, TxFee
from cosmpy.protos.cosmos.base.v1beta1.coin_pb2 import Coin
from cosmpy.protos.ibc.applications.transfer.v1.tx_pb2 import MsgTransfer

from project_utils.address_book import resolve_wallets
from project_utils.denoms_lookup import convert_amount, load_denoms_index, resolve_denom
from project_utils.logging_setup import setup_logging


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
):
    logger = setup_logging()
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

    print(f'Sender wallet: {sender_name}: sender address: {sender_address}')
    print(f'Receiver wallet: {receiver_name}: receiver address: {receiver_address}')
    print(
        f'denom contract: {denom_contract}\n'
        f'symbol sender: {symbol}\n'
        f'network sender: {network}\n'
        f'decimal: {decimal_token}'
    )
    print(
        f'Time out {time_out} (nanoseconds)\n'
        f'Time out in seconds {timeout_second}\n'
        f'Time out in date {formatted_dt}'
    )
    print(f'Amount transfer {amount_token}')
    print(f'Amount original {amount_convert}')
    print(f'Gas limit {gas}')
    print('=====================')

    confirm_amount = input(f'Re-enter amount to confirm ({amount_token}): ').strip()
    try:
        if float(confirm_amount) != amount_token:
            print('Amount mismatch. Operation cancelled.')
            return
    except ValueError:
        print('Invalid amount. Operation cancelled.')
        return

    user_input = input('Type "yes" to execute the transaction: ').strip().lower()
    if user_input != 'yes':
        print('Operation cancelled by the user.')
        return

    tx = prepare_and_broadcast_basic_transaction(client, tx, wallet, fee=TxFee(gas_limit=gas))
    tx_hash = tx.tx_hash
    logger.info(
        'IBC transfer: sender_wallet=%s sender_address=%s receiver_wallet=%s receiver_address=%s '
        'denom=%s symbol=%s network=%s decimal=%s timeout=%s timeout_seconds=%s timeout_date=%s '
        'amount=%s amount_raw=%s tx_hash=%s',
        sender_name,
        sender_address,
        receiver_name,
        receiver_address,
        denom_contract,
        symbol,
        network,
        decimal_token,
        time_out,
        timeout_second,
        formatted_dt,
        amount_token,
        amount_convert,
        tx_hash,
    )
    print('Transaction successfully executed!')
    print(f'Transaction hash: {tx_hash}')
