from colorama import init, Fore, Style
from menu.menu_setting import clear_menu
from project_utils.create_check_data.setup.setup import (
    source_create_or_check, check_pythonpath,
    check_apps, check_python_modules, check_platform
)
from project_utils.create_check_data.collect_data.json.json_scanner import (
    traverse_directory_chain_data,
    check_info,
    init_data_list
)
from project_utils.create_check_data.generate.create_ledger_clients import (create_ledger_clients_file,
                                                                            create_ledger_client_mapping)
from project_utils.create_check_data.generate.create_wallets import create_wallets_list_code
from project_utils.template.template_denoms_book import create_json_template
from config.config_list import ListData
from config.config_path import ConfigPath
from config.config_files import FileName
from config.config_path_files import PathFileName
from config.config_links import LinksAPIChain

init(autoreset=True)
path = ConfigPath()
filename = FileName()
path_filename = PathFileName()
links_api_chain = LinksAPIChain()
data_list = ListData()


def check_and_create_data():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Welcome to the Cosmos Crypto Transfer System" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Check or create source")
    print("2. Check pythonpath")
    print("3. Check apps")
    print("4. Check python modules")
    print(Fore.BLUE + "5. All check and create data" + Style.RESET_ALL)
    print(Fore.CYAN + "=================================================" + Style.RESET_ALL)
    print("6. Collect data json files")
    print(Fore.CYAN + "=================================================" + Style.RESET_ALL)
    print("7. Generate ledger clients")
    print("8. Generate Wallets list")
    print("9. Generate Addresses book")
    print(Fore.CYAN + "=================================================" + Style.RESET_ALL)
    print("10. Create template json file")
    print(Fore.YELLOW + "11. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "12. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        source_create_or_check()
        check_info(path.chain_registry_path, path.data_path, filename.filename_dict_chain_id, data_list.key1_chain,
                   data_list.key2_chain)
    if choice == "2":
        clear_menu(True)
        check_pythonpath(path.project_path)
    elif choice == "3":
        clear_menu(True)
        check_apps()
    elif choice == "4":
        clear_menu(True)
        check_python_modules(data_list.modules_list)
    elif choice == "5":
        clear_menu(True)
        check_platform()
        source_create_or_check()
        check_pythonpath(path.project_path)
        check_apps()
        check_python_modules(data_list.modules_list)
    elif choice == "6":
        clear_menu(True)
        traverse_directory_chain_data(path.chain_registry_path, path.keplr_chain_registry_path,
                                      path_filename.result_collection_chain_file_name,
                                      data_list.keys_to_extract_chain_data, data_list.keys_to_extract_chain_keplr_data,
                                      data_list.chain_id_list)
        init_data_list(path.chain_path, path.data_path, filename.filename_cosmos_data)
    elif choice == "7":
        clear_menu(True)
        create_ledger_clients_file(path_filename.data_cosmos_file_name, path.data_path, filename.filename_cosmos_data,
                                   path.root_client_path, filename.project_file_ledger_client)
        create_ledger_client_mapping(path_filename.data_cosmos_file_name, path_filename.ledger_client_mapping)
    elif choice == "8":
        clear_menu(True)
        create_wallets_list_code(path_filename.data_cosmos_file_name, path_filename.wallets_list_path)
    elif choice == "9":
        clear_menu(True)
        from chain.wallets.wallets_list import write_address_variables_to_json
        write_address_variables_to_json(path_filename.address_book_temp)
        from project_utils.create_check_data.generate.create_address_book import create_addresses_book
        create_addresses_book(path.create_path, filename.filename_temp_address_book, path.data_path,
                              filename.filename_address_book)
    elif choice == "10":
        clear_menu(True)
        create_json_template(path_filename.denoms_book_path, 5)
    elif choice == "11":
        from menu.main_menu import main_menu
        clear_menu(True)
        return main_menu()
    elif choice == "12":
        print("Exiting program...")
        clear_menu(True)
        exit()
    check_and_create_data()
