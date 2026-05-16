from colorama import init

from config.config_list import ListData
from config.config_files import FileName
from config.config_links import LinksAPIChain
from config.config_path import ConfigPath
from config.config_path_files import PathFileName
from menu.menu_runner import run_menu
from menu.menu_setting import clear_menu
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

init(autoreset=True)
path = ConfigPath()
filename = FileName()
path_filename = PathFileName()
links_api_chain = LinksAPIChain()
data_list = ListData()


def check_and_create_data():
    def do_source():
        clear_menu(True)
        source_create_or_check()
        check_info(
            path.chain_registry_path,
            path.data_path,
            filename.filename_dict_chain_id,
            data_list.key1_chain,
            data_list.key2_chain,
        )

    def do_pythonpath():
        clear_menu(True)
        check_pythonpath(path.project_path)

    def do_apps():
        clear_menu(True)
        check_apps()

    def do_modules():
        clear_menu(True)
        check_python_modules(data_list.modules_list)

    def do_all_checks():
        clear_menu(True)
        check_platform()
        source_create_or_check()
        check_pythonpath(path.project_path)
        check_apps()
        check_python_modules(data_list.modules_list)

    def do_collect_json():
        clear_menu(True)
        traverse_directory_chain_data(
            path.chain_registry_path,
            path.keplr_chain_registry_path,
            path_filename.result_collection_chain_file_name,
            data_list.keys_to_extract_chain_data,
            data_list.keys_to_extract_chain_keplr_data,
            data_list.chain_id_list,
        )
        init_data_list(path.chain_path, path.data_path, filename.filename_cosmos_data)

    def do_ledger_clients():
        clear_menu(True)
        create_ledger_clients_file(
            path_filename.data_cosmos_file_name,
            path.data_path,
            filename.filename_cosmos_data,
            path.root_client_path,
            filename.project_file_ledger_client,
        )
        create_ledger_client_mapping(
            path_filename.data_cosmos_file_name,
            path_filename.ledger_client_mapping,
        )

    def do_wallets():
        clear_menu(True)
        create_wallets_list_code(path_filename.data_cosmos_file_name, path_filename.wallets_list_path)

    def do_address_book():
        clear_menu(True)
        from chain.wallets.wallets_list import write_address_variables_to_json

        write_address_variables_to_json(path_filename.address_book_temp)
        create_addresses_book(
            path.create_path,
            filename.filename_temp_address_book,
            path.data_path,
            filename.filename_address_book,
        )

    while True:
        items = [
            ('1', 'Check or create source', do_source),
            ('2', 'Check pythonpath', do_pythonpath),
            ('3', 'Check apps', do_apps),
            ('4', 'Check python modules', do_modules),
            ('5', 'All check and create data', do_all_checks),
            ('6', 'Collect data json files', do_collect_json),
            ('7', 'Generate ledger clients', do_ledger_clients),
            ('8', 'Generate Wallets list', do_wallets),
            ('9', 'Generate Addresses book', do_address_book),
        ]

        result = run_menu('Check and create data', items)
        if result == 'back':
            return
        if result == 'exit':
            raise SystemExit(0)
