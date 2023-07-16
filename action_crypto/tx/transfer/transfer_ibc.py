import time
import json
import logging
import google
import datetime
from cosmpy.aerial.client.utils import prepare_and_broadcast_basic_transaction
from cosmpy.aerial.tx import Transaction
from cosmpy.protos.cosmos.base.v1beta1.coin_pb2 import Coin
from cosmpy.protos.ibc.applications.transfer.v1.tx_pb2 import MsgTransfer
from config.config_path_files import PathFileName

path_filename = PathFileName()


def transfer_ibc(symbol, network, path_address_book, path_denoms_book, timeout_second, amount, sender_wallet,
                 receiver_wallet, channel_ibc, gas, client, wallet):
    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO,
        filename=path_filename.transaction_log
    )
    time_convert = int(10 ** 9)
    # two minutes
    time_out = (int(time.time()) * time_convert) + (time_convert * timeout_second)
    dt = datetime.datetime.utcfromtimestamp(time_out // 1000000000)
    formatted_dt = dt.strftime('%Y-%m-%d %H:%M:%S')
    amount_token = float(amount)
    with open(path_address_book, 'r') as f1, open(path_denoms_book, 'r') as f2:
        data_address = json.load(f1)
        data_denom = json.load(f2)

        sender_name = None
        receiver_name = None
        for item in data_address:
            name_wallet = item["name"]
            address_data = item["address"]
            if name_wallet != sender_wallet and name_wallet != receiver_wallet:
                continue
            if name_wallet == sender_wallet:
                sender_wallet = address_data
                sender_name = name_wallet
            if name_wallet == receiver_wallet:
                receiver_wallet = address_data
                receiver_name = name_wallet
        if sender_name is None and receiver_name is None:
            raise ValueError("Sender and receiver wallet not found in address book")

        denom_contract = None
        decimal_token = None
        for item in data_denom:
            symbol_data = item["symbol"]
            network_data = item["network"]
            denom_contract = item["denom_contract"]
            decimal_token = item["decimal"]
            if symbol_data != symbol or network_data != network:
                continue
            denom_contract = item.get('denom_contract')
            decimal_token = item.get('decimal')
            break
        if denom_contract is None or decimal_token is None:
            raise ValueError("Symbol and network pair not found in denoms book")
        amount_convert = int(float(amount_token) * (10 ** int(decimal_token)))
    tx = Transaction()
    tx.add_message(
        MsgTransfer(
            source_port="transfer",
            source_channel=channel_ibc,
            token=Coin(denom=denom_contract, amount=str(amount_convert)),
            sender=sender_wallet,
            receiver=receiver_wallet,
            timeout_timestamp=time_out
        )
    )
    print(f'Sender wallet: {sender_name}: sender address: {sender_wallet}')
    print(f'Receiver wallet: {receiver_name}: receiver address: {receiver_wallet}')
    print(
        f'denom contract: {denom_contract}\nsymbol sender: {symbol}\nnetwork sender: {network}\ndecimal: {decimal_token}')
    print(f'Time out {time_out} in epoh\nTime out in second {timeout_second}\nTime out in date {formatted_dt}')
    print(f'Amount transfer {amount_token}')
    print(f'Amount original {amount_convert}')
    print('=====================')
    print(tx.msgs)
    # logging.info(f'Sender wallet: {sender_name}: sender address: {sender_wallet}')
    # Obtaining confirmation from the user
    user_input = input("Are you sure you want to execute the transaction? (yes/no): ")
    # Checking the input value
    if user_input.lower() == "yes":
        tx = prepare_and_broadcast_basic_transaction(client, tx, wallet, gas_limit=gas)
        tx_hash = tx.tx_hash
        logging.info(f'sender_wallet: {sender_name},'
                     f'sender_address: {sender_wallet},'
                     f'receiver_wallet: {receiver_name},'
                     f'receiver_address: {receiver_wallet},'
                     f'denom_contract: {denom_contract},'
                     f'symbol_sender: {symbol},'
                     f'network_sender: {network},'
                     f'decimal: {decimal_token},'
                     f'time_out: {time_out},'
                     f'time_out_second: {timeout_second},'
                     f'time_out_date: {formatted_dt},'
                     f'amount_transfer: {amount_token},'
                     f'amount_original: {amount_convert},'
                     f'tx_hash: {tx_hash}')
        print("Transaction successfully executed!")
        print(f'Transaction hash: {tx_hash}')
    else:
        print("Operation cancelled by the user.")
