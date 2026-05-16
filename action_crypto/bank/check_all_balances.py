import json
import time

import requests

from project_utils.chain_resources import build_client_map


def check_balances_addresses_book(filepath_mapping, filepath_address_book, _filepath_py_unused=None):
    with open(filepath_mapping, 'r', encoding='utf-8') as f1, open(filepath_address_book, 'r', encoding='utf-8') as f2:
        mapping_data = json.load(f1)
        address_data = json.load(f2)

    try:
        variable_values, missed_from_map = build_client_map(mapping_data)
    except (ModuleNotFoundError, AttributeError) as exc:
        print(f'Error loading ledger clients: {exc}')
        return

    missed_clients = list(missed_from_map)
    for addr in address_data:
        network = addr['network']
        wallet_name = addr['name']
        if network not in variable_values:
            if network not in missed_clients:
                missed_clients.append(network)
            continue
        client = variable_values[network]
        if 'address' not in addr:
            print(f'Error: "address" key missing for network {network}')
            continue
        address = addr['address']
        try:
            balance = client.query_bank_all_balances(address)
            print(f'Network: {network} | Wallet name: {wallet_name} | Address: {address}: {balance}')
        except requests.exceptions.HTTPError as e:
            print(f'Error: Failed to make request for network {network} and address {address}: {e}')
        except RuntimeError as e:
            print(f'Error: Failed to make request for network {network} and address {address}: {e}')
        time.sleep(3)

    if missed_clients:
        print(f'Missed clients: {", ".join(sorted(set(missed_clients)))}')
