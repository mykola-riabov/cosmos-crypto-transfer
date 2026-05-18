import io
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import Callable, List, Optional

from action_crypto.bank.balance_query import query_all_balances
from action_crypto.info.tokens_info import fetch_osmosis_token_rows
from action_crypto.tx.transfer.transfer_ibc import (
    broadcast_ibc_transfer,
    prepare_ibc_transfer,
)
from config.config_links import LinksAPIChain
from config.config_list import ListData
from config.config_path import ConfigPath
from config.config_path_files import PathFileName
from project_utils.chain_resources import (
    get_network_client,
    get_wallet,
    load_ledger_clients_module,
    load_wallets_module,
)
from project_utils.ibc_routes import find_route, load_ibc_routes, routes_by_source


@dataclass
class SetupStatus:
    wallet_json: bool
    ledger_clients: bool
    wallets_list: bool
    address_book: bool
    client_mapping: bool
    cosmos_data: bool
    source_dir: bool

    @property
    def ready_for_transfer(self) -> bool:
        return all(
            (
                self.wallet_json,
                self.ledger_clients,
                self.wallets_list,
                self.address_book,
                self.client_mapping,
            )
        )


def get_paths() -> PathFileName:
    return PathFileName()


def get_setup_status() -> SetupStatus:
    paths = get_paths()
    return SetupStatus(
        wallet_json=os.path.isfile(paths.wallet_json_filepath),
        ledger_clients=os.path.isfile(paths.ledger_clients),
        wallets_list=os.path.isfile(paths.wallets_list_path),
        address_book=os.path.isfile(paths.address_book),
        client_mapping=os.path.isfile(paths.ledger_client_mapping),
        cosmos_data=os.path.isfile(paths.data_cosmos_file_name),
        source_dir=os.path.isdir(ConfigPath.source_path),
    )


def load_address_book_entries() -> List[dict]:
    paths = get_paths()
    if not os.path.isfile(paths.address_book):
        return []
    with open(paths.address_book, 'r', encoding='utf-8') as f:
        return json.load(f)


def run_captured(callable_fn: Callable[[], None]) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        try:
            callable_fn()
        except SystemExit:
            pass
    return buffer.getvalue()


def gui_prepare_transfer(route, symbol: str, amount: float):
    paths = get_paths()
    return prepare_ibc_transfer(
        symbol,
        route['source_network'],
        paths.address_book,
        paths.denoms_book_path,
        route.get('timeout_seconds', 120),
        amount,
        route['sender_wallet'],
        route['receiver_wallet'],
        route['channel'],
        route['gas'],
    )


def gui_broadcast_transfer(route, preview) -> str:
    ledger_module = load_ledger_clients_module()
    wallets_module = load_wallets_module()
    network = route['source_network']
    client = get_network_client(ledger_module, network)
    wallet = get_wallet(wallets_module, route['wallet_attr'])
    return broadcast_ibc_transfer(preview, client, wallet)


def fetch_balances():
    paths = get_paths()
    return query_all_balances(paths.ledger_client_mapping, paths.address_book)


def fetch_osmosis_tokens():
    links = LinksAPIChain()
    data_list = ListData()
    return fetch_osmosis_token_rows(links.link_osmosis_token, data_list.display_values)


def run_setup_action(action_id: str, link_type: Optional[str] = None) -> str:
    from config.config_files import FileName
    from config.config_list import ListData
    from project_utils.create_check_data.collect_data.json.json_scanner import (
        check_info,
        init_data_list,
        traverse_directory_chain_data,
    )
    from project_utils.create_check_data.generate.create_address_book import create_addresses_book
    from project_utils.create_check_data.generate.create_ledger_clients import (
        create_ledger_client_mapping,
        create_ledger_clients_file,
    )
    from project_utils.create_check_data.generate.create_wallets import create_wallets_list_code
    from project_utils.create_check_data.setup.setup import (
        check_apps,
        check_platform,
        check_python_modules,
        check_pythonpath,
        source_create_or_check,
    )

    path = ConfigPath()
    filename = FileName()
    paths = get_paths()
    data_list = ListData()

    def do_source():
        source_create_or_check()
        check_info(
            path.chain_registry_path,
            path.data_path,
            filename.filename_dict_chain_id,
            data_list.key1_chain,
            data_list.key2_chain,
        )

    def do_pythonpath():
        check_pythonpath(path.project_path)

    def do_apps():
        check_apps()

    def do_modules():
        check_python_modules(data_list.modules_list)

    def do_all_checks():
        check_platform()
        source_create_or_check()
        check_pythonpath(path.project_path)
        check_apps()
        check_python_modules(data_list.modules_list)

    def do_collect_json():
        traverse_directory_chain_data(
            path.chain_registry_path,
            path.keplr_chain_registry_path,
            paths.result_collection_chain_file_name,
            data_list.keys_to_extract_chain_data,
            data_list.keys_to_extract_chain_keplr_data,
            data_list.chain_id_list,
        )
        init_data_list(path.chain_path, path.data_path, filename.filename_cosmos_data)

    def do_ledger_clients():
        create_ledger_clients_file(
            paths.data_cosmos_file_name,
            path.data_path,
            filename.filename_cosmos_data,
            path.root_client_path,
            filename.project_file_ledger_client,
            link_type=link_type,
        )
        create_ledger_client_mapping(
            paths.data_cosmos_file_name,
            paths.ledger_client_mapping,
        )

    def do_wallets():
        create_wallets_list_code(paths.data_cosmos_file_name, paths.wallets_list_path)

    def do_address_book():
        from chain.wallets.wallets_list import write_address_variables_to_json

        write_address_variables_to_json(paths.address_book_temp)
        create_addresses_book(
            path.create_path,
            filename.filename_temp_address_book,
            path.data_path,
            filename.filename_address_book,
        )

    actions = {
        'source': do_source,
        'pythonpath': do_pythonpath,
        'apps': do_apps,
        'modules': do_modules,
        'all_checks': do_all_checks,
        'collect_json': do_collect_json,
        'ledger_clients': do_ledger_clients,
        'wallets': do_wallets,
        'address_book': do_address_book,
    }
    fn = actions.get(action_id)
    if fn is None:
        raise ValueError(f'Unknown setup action: {action_id}')
    return run_captured(fn)


def ibc_routes_grouped():
    return routes_by_source(load_ibc_routes())


def ibc_route_for(source: str, destination: str):
    return find_route(source, destination)
