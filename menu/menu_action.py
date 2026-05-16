import json
import os
from collections import defaultdict

from colorama import init

from action_crypto.bank.check_all_balances import check_balances_addresses_book
from action_crypto.bank.check_custom_balance import check_custom_balances_addresses_book
from action_crypto.info.tokens_info import filter_data_by_display
from action_crypto.tx.transfer.transfer_ibc import transfer_ibc
from config.config_links import LinksAPIChain
from config.config_list import ListData
from config.config_path import ConfigPath
from config.config_path_files import PathFileName
from menu.menu_runner import run_menu
from menu.menu_setting import clear_menu
from project_utils.chain_resources import get_network_client, get_wallet, load_ledger_clients_module, load_wallets_module

init(autoreset=True)
path_filename = PathFileName()
links_api_chain = LinksAPIChain()
data_list = ListData()

_IBC_ROUTES_PATH = os.path.join(ConfigPath.root_config_path, 'ibc_routes.json')


def _load_ibc_routes():
    with open(_IBC_ROUTES_PATH, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    return payload['routes']


def _routes_by_source(routes):
    grouped = defaultdict(list)
    for route in routes:
        grouped[route['source_network']].append(route)
    return dict(sorted(grouped.items()))


def _execute_ibc_route(route):
    clear_menu(True)
    symbol_transfer = input('Enter the transfer symbol: ').strip()
    amount_transfer = float(input('Enter the transfer amount: '))

    ledger_module = load_ledger_clients_module()
    wallets_module = load_wallets_module()
    network = route['source_network']
    client = get_network_client(ledger_module, network)
    wallet = get_wallet(wallets_module, route['wallet_attr'])

    transfer_ibc(
        symbol_transfer,
        network,
        path_filename.address_book,
        path_filename.denoms_book_path,
        route.get('timeout_seconds', 120),
        amount_transfer,
        route['sender_wallet'],
        route['receiver_wallet'],
        route['channel'],
        route['gas'],
        client,
        wallet,
    )


def _menu_transfer_destinations(source_network, routes):
    dest_routes = sorted(routes, key=lambda r: r['destination_network'])
    items = []
    for route in dest_routes:
        dst = route['destination_network']
        label = f'{source_network} → {dst} ({route["channel"]})'
        items.append((dst, label, lambda r=route: _execute_ibc_route(r)))

    return run_menu(
        f'Transfer IBC {source_network}',
        items,
        back_label='Back to source chains',
    )


def menu_transfer_ibc():
    routes = _load_ibc_routes()
    by_source = _routes_by_source(routes)

    while True:
        items = []
        for source in sorted(by_source):

            def make_handler(src=source):
                def handler():
                    while True:
                        result = _menu_transfer_destinations(src, by_source[src])
                        if result == 'exit':
                            raise SystemExit(0)
                        if result == 'back':
                            return
                return handler

            count = len(by_source[source])
            items.append((source, f'{source} ({count} routes)', make_handler()))

        result = run_menu('Transfer IBC — select source chain', items)
        if result == 'back':
            return
        if result == 'exit':
            raise SystemExit(0)


def menu_action_crypto_management():
    def do_balances_all():
        clear_menu(True)
        check_balances_addresses_book(
            path_filename.ledger_client_mapping,
            path_filename.address_book,
        )

    def do_balances_custom():
        clear_menu(True)
        check_custom_balances_addresses_book(
            path_filename.ledger_client_mapping,
            path_filename.address_book,
            path_filename.denoms_book_path,
            wallet_names=data_list.wallet_name_list,
            update_interval=20,
        )

    def do_tokens_info():
        clear_menu(True)
        filter_data_by_display(
            links_api_chain.link_osmosis_token,
            data_list.display_values,
            data_list.group1_color,
            data_list.group2_color,
            60,
        )

    def do_transfer():
        clear_menu(True)
        menu_transfer_ibc()

    while True:
        items = [
            ('1', 'Check all balances of all addresses in address book', do_balances_all),
            ('2', 'Check custom balances of custom wallet name', do_balances_custom),
            ('3', 'Info tokens osmosis DEX', do_tokens_info),
            ('4', 'Transfer IBC cosmos chain', do_transfer),
        ]

        result = run_menu('Action Crypto Transfer System', items)
        if result == 'back':
            return
        if result == 'exit':
            raise SystemExit(0)
