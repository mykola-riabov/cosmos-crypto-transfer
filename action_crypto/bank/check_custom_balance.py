import json
import signal
import time

import curses
import requests
from tabulate import tabulate

from project_utils.chain_resources import build_client_map
from project_utils.denoms_lookup import load_denoms_index


def check_custom_balances_addresses_book(
    filepath_mapping,
    filepath_address_book,
    filepath_denoms_book,
    _filepath_py_unused=None,
    wallet_names=None,
    update_interval=20,
):
    wallet_names = wallet_names or []

    with open(filepath_mapping, 'r', encoding='utf-8') as f1, open(filepath_address_book, 'r', encoding='utf-8') as f2:
        mapping_data = json.load(f1)
        address_data = json.load(f2)

    try:
        variable_values, missed_from_map = build_client_map(mapping_data)
    except (ModuleNotFoundError, AttributeError) as exc:
        print(f'Error loading ledger clients: {exc}')
        return

    denom_index = load_denoms_index(filepath_denoms_book)
    denom_names = {item['denom_contract']: item['symbol'] for item in denom_index.values()}
    denom_decimal = {
        item['denom_contract']: 10 ** int(item['decimal']) for item in denom_index.values()
    }

    stdscr = curses.initscr()
    curses.noecho()
    curses.cbreak()
    stdscr.keypad(True)

    def _cleanup():
        curses.echo()
        curses.nocbreak()
        stdscr.keypad(False)
        curses.endwin()

    def signal_handler(sig, frame):
        _cleanup()
        print('Execution terminated.')
        raise SystemExit(0)

    signal.signal(signal.SIGINT, signal_handler)

    try:
        while True:
            stdscr.clear()
            missed_clients = list(missed_from_map)
            data = []
            headers = ['Wallet Name', 'Network', 'Balance', 'Denom']

            for addr in address_data:
                network = addr['network']
                wallet_name = addr['name']
                if wallet_name not in wallet_names:
                    continue
                if network not in variable_values:
                    if network not in missed_clients:
                        missed_clients.append(network)
                    continue
                if 'address' not in addr:
                    continue

                client = variable_values[network]
                address = addr['address']
                try:
                    balance = client.query_bank_all_balances(address)
                    for balance_item in balance:
                        denom_name = denom_names.get(balance_item.denom)
                        denom_decimal_value = denom_decimal.get(balance_item.denom, 1)
                        balance_amount = int(balance_item.amount) / denom_decimal_value
                        if denom_name is None:
                            denom_name = balance_item.denom
                        data.append([wallet_name, network, balance_amount, denom_name])
                except requests.exceptions.HTTPError as e:
                    if e.response is not None and e.response.status_code == 504:
                        data.append([wallet_name, network, 'timeout', '—'])
                    else:
                        data.append([wallet_name, network, 'error network', 'error network'])
                except (requests.exceptions.RequestException, ConnectionError, RuntimeError, AttributeError):
                    data.append([wallet_name, network, 'error network', 'error network'])

            if missed_clients:
                stdscr.addstr(0, 0, f'Missed clients: {", ".join(sorted(set(missed_clients)))}\n')

            table = tabulate(data, headers=headers, tablefmt='grid', numalign='right', floatfmt='.6f')
            row_offset = 2 if missed_clients else 0
            for line_idx, line in enumerate(table.splitlines()):
                try:
                    stdscr.addstr(row_offset + line_idx, 0, line[: curses.COLS - 1])
                except curses.error:
                    break
            stdscr.refresh()
            time.sleep(update_interval)

    except (KeyboardInterrupt, SystemExit):
        _cleanup()
        print('Execution terminated.')
