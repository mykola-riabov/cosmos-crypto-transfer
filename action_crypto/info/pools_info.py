import json
import curses
import requests
import time
from tabulate import tabulate
import signal


def check_custom_balances_pool_book(filepath_json1, filepath_json2, filepath_json3, filepath_py, pool_names,
                                    update_interval):
    def signal_handler(signal, frame):
        print('Execution terminated.')
        curses.echo()
        curses.nocbreak()
        stdscr.keypad(False)
        curses.endwin()
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)

    try:

        while True:
            stdscr.clear()
            with open(filepath_json1, 'r') as f1, open(filepath_json2, 'r') as f2, open(filepath_json3, 'r') as f3:
                json_data_1 = json.load(f1)
                json_data_2 = json.load(f2)
                json_data_3 = json.load(f3)
                # create denom name dictionary
                denom_names = {d["denom_contract"]: d["symbol"] for d in json_data_3}
                denom_decimal = {d["denom_contract"]: 10 ** int(d["decimal"]) for d in json_data_3}

            with open(filepath_py, 'r') as f4:
                code = f4.read()
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
            data = []
            headers = ['Pools Name', 'Network', 'Balance', 'Denom']
            for addr in json_data_2:
                network = addr["network"]
                pool_name = addr["name"]
                if pool_name not in pool_names:
                    continue
                if network not in variable_values:
                    missed_clients.append(network)
                    continue
                client = variable_values[network]
                if "address" in addr:
                    if pool_name not in pool_names:
                        continue
                    address = addr["address"]
                    balance_amount = "error network"
                    denom_name = "error network"
                    try:
                        balance = client.query_bank_all_balances(address)
                        # append balance data to the data list
                        for balance_item in balance:
                            denom_name = denom_names.get(balance_item.denom)
                            denom_decimal_value = denom_decimal.get(balance_item.denom)
                            if denom_decimal_value is None:
                                denom_decimal_value = 1
                            balance_amount = int(balance_item.amount) / denom_decimal_value
                            if denom_name is None:
                                denom_name = balance_item.denom
                            data.append([pool_name, network, balance_amount, denom_name])
                    except (requests.exceptions.HTTPError, requests.exceptions.RequestException) as e:
                        if isinstance(e, requests.exceptions.HTTPError) and e.response.status_code == 504:
                            balance_amount = "timeout"
                            denom_name = denom_names.get(balance_item.denom, balance_item.denom)
                            data.append([pool_name, network, balance_amount, denom_name])
                        else:
                            print(f"Error occurred during processing balance: {e}")
                            data.append([pool_name, network, "error network", "error network"])
                    except requests.exceptions.HTTPError as e:
                        print(f'Error: Failed to make request for network {network} and address {address}: {e}')
                        data.append([pool_name, network, "error network", "error network"])

            if missed_clients:
                print(f'Missed clients: {", ".join(missed_clients)}')

            stdscr.addstr(0, 0, tabulate(data, headers=headers, tablefmt='grid', numalign='right', floatfmt='.2f'))
            stdscr.refresh()

            time.sleep(update_interval)


    except KeyboardInterrupt:
        print("Execution terminated.")
        curses.echo()
        curses.nocbreak()
        stdscr.keypad(False)
        curses.endwin()
        exit(0)
