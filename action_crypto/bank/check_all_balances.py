import json
import requests
import time


def check_balances_addresses_book(filepath_json1, filepath_json2, filepath_py):
    with open(filepath_json1, 'r') as f1, open(filepath_json2, 'r') as f2:
        json_data_1 = json.load(f1)
        json_data_2 = json.load(f2)

    with open(filepath_py, 'r') as f3:
        code = f3.read()
        exec(code)

    variable_values = {}
    for entry in json_data_1:
        variable_name = entry['network']
        if variable_name + '_client' not in locals():
            print(f'Error: variable {variable_name}_client not found')
            continue
        variable_value = eval(variable_name + '_client')
        variable_values[variable_name] = variable_value

    missed_clients = []
    for addr in json_data_2:
        network = addr["network"]
        wallet_name = addr["name"]
        if network not in variable_values:
            missed_clients.append(network)
            continue
        client = variable_values[network]
        if "address" in addr:
            address = addr["address"]
            try:
                balance = client.query_bank_all_balances(address)
                print(f'Network: {network} | Wallet name: {wallet_name} | Address: {address}: {balance}')
            except requests.exceptions.HTTPError as e:
                print(f'Error: Failed to make request for network {network} and address {address}: {e}')
            except RuntimeError as e:
                print(f'Error: Failed to make request for network {network} and address {address}: {e}')
            time.sleep(3)
        else:
            print(f'Error: "address" key missing for network {network}')

    if missed_clients:
        print(f'Missed clients: {", ".join(missed_clients)}')
