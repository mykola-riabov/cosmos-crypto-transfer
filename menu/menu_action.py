from colorama import init, Fore, Style
from action_crypto.bank.check_all_balances import check_balances_addresses_book
from action_crypto.info.tokens_info import filter_data_by_display
from action_crypto.bank.check_custom_balance import check_custom_balances_addresses_book
from action_crypto.info.pools_info import check_custom_balances_pool_book
from action_crypto.tx.transfer.transfer_ibc import transfer_ibc
import chain.clients.ledger_clients as ledger_clients
import chain.wallets.wallets_list as wallets_list
from menu.menu_setting import clear_menu
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


def menu_action_crypto_management():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Welcome to the Action Crypto Transfer System!" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Check all balances of all addresses in address book")
    print("2. Check custom balances of custom wallet name")
    print("3. Info tokens osmosis DEX")
    print(Fore.CYAN + "================Transfer IBC================" + Style.RESET_ALL)
    print("4. Transfer IBC cosmos chain")
    print(Fore.YELLOW + "5. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "6. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        check_balances_addresses_book(path_filename.ledger_client_mapping, path_filename.address_book,
                                      path_filename.ledger_clients)
    elif choice == "2":
        clear_menu(True)
        check_custom_balances_addresses_book(path_filename.ledger_client_mapping, path_filename.address_book,
                                             path_filename.denoms_book_path,
                                             path_filename.ledger_clients, data_list.wallet_name_list, 20)
    elif choice == "3":
        clear_menu(True)
        filter_data_by_display(links_api_chain.link_osmosis_token, data_list.display_values, data_list.group1_color,
                               data_list.group2_color, 60)
    elif choice == "4":
        clear_menu(True)
        menu_transfer_ibc()
    elif choice == "5":
        from menu.main_menu import main_menu
        clear_menu(True)
        return main_menu()
    elif choice == "6":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_action_crypto_management()


def menu_transfer_ibc():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Welcome to the Transfer IBC System!" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC Osmosis")
    print("2. Transfer IBC IRISnet")
    print("3. Transfer IBC Gravity Bridge")
    print("4. Transfer IBC Crescent")
    print("5. Transfer IBC Axelar")
    print("6. Transfer IBC Fetchhub")
    print("7. Transfer IBC Cosmoshub")
    print("8. Transfer IBC Juno")
    print("9. Transfer IBC Comdex")
    print("10. Transfer IBC Bostrom")
    print("11. Transfer IBC Kujira")
    print(Fore.YELLOW + "12. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "13. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        menu_transfer_ibc_osmosis()
    elif choice == "2":
        clear_menu(True)
        menu_transfer_ibc_irisnet()
    elif choice == "3":
        clear_menu(True)
        menu_transfer_ibc_gravitybridge()
    elif choice == "4":
        clear_menu(True)
        menu_transfer_ibc_crescent()
    elif choice == "5":
        clear_menu(True)
        menu_transfer_ibc_axelar()
    elif choice == "6":
        clear_menu(True)
        menu_transfer_ibc_fetchhub()
    elif choice == "7":
        clear_menu(True)
        menu_transfer_ibc_cosmoshub()
    elif choice == "8":
        clear_menu(True)
        menu_transfer_ibc_juno()
    elif choice == "9":
        clear_menu(True)
        menu_transfer_ibc_comdex()
    elif choice == "10":
        clear_menu(True)
        menu_transfer_ibc_bostrom()
    elif choice == "11":
        clear_menu(True)
        menu_transfer_ibc_kujira()
    elif choice == "12":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_action_crypto_management()
    elif choice == "13":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc()


def menu_transfer_ibc_osmosis():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Transfer IBC Osmosis" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC Osmosis to IRISnet")
    print("2. Transfer IBC Osmosis to Gravity Bridge")
    print("3. Transfer IBC Osmosis to Crescent")
    print("4. Transfer IBC Osmosis to Axelar")
    print("5. Transfer IBC Osmosis to Fetchhub")
    print("6. Transfer IBC Osmosis to Cosmoshub")
    print("7. Transfer IBC Osmosis to Juno")
    print("8. Transfer IBC Osmosis to Comdex")
    print("9. Transfer IBC Osmosis to Bostrom")
    print("10. Transfer IBC Osmosis to Kujira")
    print(Fore.YELLOW + "11. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "12. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'osmosis', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_osmosis', 'digriz_keplr_8_irisnet', 'channel-6', 200000,
                     ledger_clients.osmosis_client, wallets_list.wallet_digriz_keplr_8_osmosis_chain)
    elif choice == "2":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'osmosis', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_osmosis', 'digriz_keplr_8_gravitybridge', 'channel-144', 200000,
                     ledger_clients.osmosis_client, wallets_list.wallet_digriz_keplr_8_osmosis_chain)
    elif choice == "3":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'osmosis', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_osmosis', 'digriz_keplr_8_crescent', 'channel-297', 200000,
                     ledger_clients.osmosis_client, wallets_list.wallet_digriz_keplr_8_osmosis_chain)
    elif choice == "4":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'osmosis', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_osmosis', 'digriz_keplr_8_axelar', 'channel-208', 240000,
                     ledger_clients.osmosis_client, wallets_list.wallet_digriz_keplr_8_osmosis_chain)
    elif choice == "5":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'osmosis', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_osmosis', 'digriz_keplr_8_fetchhub', 'channel-229', 200000,
                     ledger_clients.osmosis_client, wallets_list.wallet_digriz_keplr_8_osmosis_chain)
    elif choice == "6":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'osmosis', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_osmosis', 'digriz_keplr_8_cosmoshub', 'channel-0', 200000,
                     ledger_clients.osmosis_client, wallets_list.wallet_digriz_keplr_8_osmosis_chain)
    elif choice == "7":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'osmosis', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_osmosis', 'digriz_keplr_8_juno', 'channel-42', 200000,
                     ledger_clients.osmosis_client, wallets_list.wallet_digriz_keplr_8_osmosis_chain)
    elif choice == "8":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'osmosis', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_osmosis', 'digriz_keplr_8_comdex', 'channel-87', 200000,
                     ledger_clients.osmosis_client, wallets_list.wallet_digriz_keplr_8_osmosis_chain)
    elif choice == "9":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'osmosis', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_osmosis', 'digriz_keplr_8_bostrom', 'channel-95', 200000,
                     ledger_clients.osmosis_client, wallets_list.wallet_digriz_keplr_8_osmosis_chain)
    elif choice == "10":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'osmosis', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_osmosis', 'digriz_keplr_8_kujira', 'channel-259', 200000,
                     ledger_clients.osmosis_client, wallets_list.wallet_digriz_keplr_8_osmosis_chain)
    elif choice == "11":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_transfer_ibc()
    elif choice == "12":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc_osmosis()


def menu_transfer_ibc_irisnet():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Transfer IBC IRISnet" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC IRISnet to Osmosis")
    print("2. Transfer IBC IRISnet to Gravity Bridge")
    print("3. Transfer IBC IRISnet to Crescent")
    print("4. Transfer IBC IRISnet to Cosmoshub")
    print(Fore.YELLOW + "5. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "6. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'irisnet', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_irisnet', 'digriz_keplr_8_osmosis', 'channel-3', 150000,
                     ledger_clients.irisnet_client, wallets_list.wallet_digriz_keplr_8_irisnet_chain)
    elif choice == "2":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'irisnet', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_irisnet', 'digriz_keplr_8_gravitybridge', 'channel-29', 150000,
                     ledger_clients.irisnet_client, wallets_list.wallet_digriz_keplr_8_irisnet_chain)
    elif choice == "3":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'irisnet', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_irisnet', 'digriz_keplr_8_crescent', 'channel-37', 150000,
                     ledger_clients.irisnet_client, wallets_list.wallet_digriz_keplr_8_irisnet_chain)
    elif choice == "4":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'irisnet', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_irisnet', 'digriz_keplr_8_cosmoshub', 'channel-0', 150000,
                     ledger_clients.irisnet_client, wallets_list.wallet_digriz_keplr_8_irisnet_chain)
    elif choice == "5":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_transfer_ibc()
    elif choice == "6":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc_irisnet()


def menu_transfer_ibc_gravitybridge():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Transfer IBC Gravity Bridge" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC Gravity Bridge to Osmosis")
    print("2. Transfer IBC Gravity Bridge to IRISnet")
    print("3. Transfer IBC Gravity Bridge to Crescent")
    print("4. Transfer IBC Gravity Bridge to Bostrom")
    print(Fore.YELLOW + "5. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "6. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'gravitybridge', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_gravitybridge', 'digriz_keplr_8_osmosis', 'channel-10', 150000,
                     ledger_clients.gravitybridge_client, wallets_list.wallet_digriz_keplr_8_gravitybridge_chain)
    elif choice == "2":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'gravitybridge', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_gravitybridge', 'digriz_keplr_8_irisnet', 'channel-47', 150000,
                     ledger_clients.gravitybridge_client, wallets_list.wallet_digriz_keplr_8_gravitybridge_chain)
    elif choice == "3":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'gravitybridge', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_gravitybridge', 'digriz_keplr_8_crescent', 'channel-62', 150000,
                     ledger_clients.gravitybridge_client, wallets_list.wallet_digriz_keplr_8_gravitybridge_chain)
    elif choice == "4":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'gravitybridge', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_gravitybridge', 'digriz_keplr_8_bostrom', 'channel-103', 150000,
                     ledger_clients.gravitybridge_client, wallets_list.wallet_digriz_keplr_8_gravitybridge_chain)
    elif choice == "5":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_transfer_ibc()
    elif choice == "6":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc_gravitybridge()


def menu_transfer_ibc_crescent():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Transfer IBC Crescent" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC Crescent to IRISnet")
    print("2. Transfer IBC Crescent to Gravity Bridge")
    print("3. Transfer IBC Crescent to Osmosis")
    print("4. Transfer IBC Crescent to Axelar")
    print("5. Transfer IBC Crescent to Cosmoshub")
    print("6. Transfer IBC Crescent to Juno")
    print("7. Transfer IBC Crescent to Comdex")
    print(Fore.YELLOW + "8. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "9. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'crescent', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_crescent', 'digriz_keplr_8_irisnet', 'channel-37', 160000,
                     ledger_clients.crescent_client, wallets_list.wallet_digriz_keplr_8_crescent_chain)
    elif choice == "2":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'crescent', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_crescent', 'digriz_keplr_8_gravitybridge', 'channel-2', 160000,
                     ledger_clients.crescent_client, wallets_list.wallet_digriz_keplr_8_crescent_chain)
    elif choice == "3":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'crescent', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_crescent', 'digriz_keplr_8_osmosis', 'channel-9', 160000,
                     ledger_clients.crescent_client, wallets_list.wallet_digriz_keplr_8_crescent_chain)
    elif choice == "4":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'crescent', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_crescent', 'digriz_keplr_8_axelar', 'channel-4', 160000,
                     ledger_clients.crescent_client, wallets_list.wallet_digriz_keplr_8_crescent_chain)
    elif choice == "5":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'crescent', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_crescent', 'digriz_keplr_8_cosmoshub', 'channel-1', 160000,
                     ledger_clients.crescent_client, wallets_list.wallet_digriz_keplr_8_crescent_chain)
    elif choice == "6":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'crescent', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_crescent', 'digriz_keplr_8_juno', 'channel-3', 160000,
                     ledger_clients.crescent_client, wallets_list.wallet_digriz_keplr_8_crescent_chain)
    elif choice == "7":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'crescent', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_crescent', 'digriz_keplr_8_comdex', 'channel-26', 160000,
                     ledger_clients.crescent_client, wallets_list.wallet_digriz_keplr_8_crescent_chain)
    elif choice == "8":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_transfer_ibc()
    elif choice == "9":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc_crescent()


def menu_transfer_ibc_axelar():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Transfer IBC Axelar" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC Axelar to Osmosis")
    print("2. Transfer IBC Axelar to Fetchhub")
    print("3. Transfer IBC Axelar to Crescent")
    print("4. Transfer IBC Axelar to Juno")
    print("5. Transfer IBC Axelar to Comdex")
    print("6. Transfer IBC Axelar to Kujira")
    print(Fore.YELLOW + "7. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "8. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'axelar', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_axelar', 'digriz_keplr_8_osmosis', 'channel-3', 160000,
                     ledger_clients.axelar_client, wallets_list.wallet_digriz_keplr_8_axelar_chain)
    elif choice == "2":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'axelar', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_axelar', 'digriz_keplr_8_fetchhub', 'channel-21', 160000,
                     ledger_clients.axelar_client, wallets_list.wallet_digriz_keplr_8_axelar_chain)
    elif choice == "3":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'axelar', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_axelar', 'digriz_keplr_8_crescent', 'channel-7', 160000,
                     ledger_clients.axelar_client, wallets_list.wallet_digriz_keplr_8_axelar_chain)
    elif choice == "4":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'axelar', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_axelar', 'digriz_keplr_8_juno', 'channel-4', 160000,
                     ledger_clients.axelar_client, wallets_list.wallet_digriz_keplr_8_axelar_chain)
    elif choice == "5":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'axelar', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_axelar', 'digriz_keplr_8_comdex', 'channel-31', 160000,
                     ledger_clients.axelar_client, wallets_list.wallet_digriz_keplr_8_axelar_chain)
    elif choice == "6":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'axelar', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_axelar', 'digriz_keplr_8_kujira', 'channel-14', 160000,
                     ledger_clients.axelar_client, wallets_list.wallet_digriz_keplr_8_axelar_chain)
    elif choice == "7":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_transfer_ibc()
    elif choice == "8":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc_axelar()


def menu_transfer_ibc_fetchhub():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Transfer IBC Fetchhub" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC Fetchhub to Osmosis")
    print("2. Transfer IBC Fetchhub to Axelar")
    print("3. Transfer IBC Fetchhub to Cosmoshub")
    print(Fore.YELLOW + "4. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "5. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'fetchhub', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_fetchhub', 'digriz_keplr_8_osmosis', 'channel-10', 160000,
                     ledger_clients.fetchhub_client, wallets_list.wallet_digriz_keplr_8_fetchhub_chain)
    elif choice == "2":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'fetchhub', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_fetchhub', 'digriz_keplr_8_axelar', 'channel-14', 160000,
                     ledger_clients.fetchhub_client, wallets_list.wallet_digriz_keplr_8_fetchhub_chain)
    elif choice == "3":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'fetchhub', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_fetchhub', 'digriz_keplr_8_cosmoshub', 'channel-16', 160000,
                     ledger_clients.fetchhub_client, wallets_list.wallet_digriz_keplr_8_fetchhub_chain)
    elif choice == "4":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_transfer_ibc()
    elif choice == "5":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc_fetchhub()


def menu_transfer_ibc_cosmoshub():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Transfer IBC Cosmoshub" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC Cosmoshub to Osmosis")
    print("2. Transfer IBC Cosmoshub to IRISnet")
    print("3. Transfer IBC Cosmoshub to Crescent")
    print("4. Transfer IBC Cosmoshub to Bostrom")
    print("5. Transfer IBC Cosmoshub to Juno")
    print("6. Transfer IBC Cosmoshub to Comdex")
    print("7. Transfer IBC Cosmoshub to Kujira")
    print("8. Transfer IBC Cosmoshub to Fetchhub")
    print(Fore.YELLOW + "9. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "10. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'cosmoshub', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_cosmoshub', 'digriz_keplr_8_osmosis', 'channel-141', 160000,
                     ledger_clients.cosmoshub_client, wallets_list.wallet_digriz_keplr_8_cosmoshub_chain)
    elif choice == "2":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'cosmoshub', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_cosmoshub', 'digriz_keplr_8_irisnet', 'channel-91', 160000,
                     ledger_clients.cosmoshub_client, wallets_list.wallet_digriz_keplr_8_cosmoshub_chain)
    elif choice == "3":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'cosmoshub', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_cosmoshub', 'digriz_keplr_8_crescent', 'channel-326', 160000,
                     ledger_clients.cosmoshub_client, wallets_list.wallet_digriz_keplr_8_cosmoshub_chain)
    elif choice == "4":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'cosmoshub', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_cosmoshub', 'digriz_keplr_8_bostrom', 'channel-341', 160000,
                     ledger_clients.cosmoshub_client, wallets_list.wallet_digriz_keplr_8_cosmoshub_chain)
    elif choice == "5":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'cosmoshub', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_cosmoshub', 'digriz_keplr_8_juno', 'channel-207', 160000,
                     ledger_clients.cosmoshub_client, wallets_list.wallet_digriz_keplr_8_cosmoshub_chain)
    elif choice == "6":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'cosmoshub', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_cosmoshub', 'digriz_keplr_8_comdex', 'channel-400', 160000,
                     ledger_clients.cosmoshub_client, wallets_list.wallet_digriz_keplr_8_cosmoshub_chain)
    elif choice == "7":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'cosmoshub', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_cosmoshub', 'digriz_keplr_8_kujira', 'channel-343', 160000,
                     ledger_clients.cosmoshub_client, wallets_list.wallet_digriz_keplr_8_cosmoshub_chain)
    elif choice == "8":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'cosmoshub', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_cosmoshub', 'digriz_keplr_8_fetchhub', 'channel-526', 160000,
                     ledger_clients.cosmoshub_client, wallets_list.wallet_digriz_keplr_8_cosmoshub_chain)
    elif choice == "9":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_transfer_ibc()
    elif choice == "10":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc_cosmoshub()


def menu_transfer_ibc_juno():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Transfer IBC Juno" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC Juno to Osmosis")
    print("2. Transfer IBC Juno to Crescent")
    print("3. Transfer IBC Juno to Bostrom")
    print("4. Transfer IBC Juno to Comdex")
    print("5. Transfer IBC Juno to Kujira")
    print("6. Transfer IBC Juno to Cosmoshub")
    print(Fore.YELLOW + "7. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "8. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'juno', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_juno', 'digriz_keplr_8_osmosis', 'channel-0', 160000,
                     ledger_clients.juno_client, wallets_list.wallet_digriz_keplr_8_juno_chain)
    elif choice == "2":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'juno', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_juno', 'digriz_keplr_8_crescent', 'channel-81', 160000,
                     ledger_clients.juno_client, wallets_list.wallet_digriz_keplr_8_juno_chain)
    elif choice == "3":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'juno', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_juno', 'digriz_keplr_8_bostrom', 'channel-93', 160000,
                     ledger_clients.juno_client, wallets_list.wallet_digriz_keplr_8_juno_chain)
    elif choice == "4":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'juno', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_juno', 'digriz_keplr_8_comdex', 'channel-36', 160000,
                     ledger_clients.juno_client, wallets_list.wallet_digriz_keplr_8_juno_chain)
    elif choice == "5":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'juno', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_juno', 'digriz_keplr_8_kujira', 'channel-87', 160000,
                     ledger_clients.juno_client, wallets_list.wallet_digriz_keplr_8_juno_chain)
    elif choice == "6":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'juno', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_juno', 'digriz_keplr_8_cosmoshub', 'channel-1', 160000,
                     ledger_clients.juno_client, wallets_list.wallet_digriz_keplr_8_juno_chain)
    elif choice == "7":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_transfer_ibc()
    elif choice == "8":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc_juno()


def menu_transfer_ibc_comdex():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Transfer IBC Comdex" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC Comdex to Osmosis")
    print("2. Transfer IBC Comdex to Crescent")
    print("3. Transfer IBC Comdex to Juno")
    print("4. Transfer IBC Comdex to Cosmoshub")
    print("5. Transfer IBC comdex to Kujira")
    print(Fore.YELLOW + "6. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "7. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'comdex', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_comdex', 'digriz_keplr_8_osmosis', 'channel-1', 160000,
                     ledger_clients.comdex_client, wallets_list.wallet_digriz_keplr_8_comdex_chain)
    elif choice == "2":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'comdex', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_comdex', 'digriz_keplr_8_crescent', 'channel-49', 160000,
                     ledger_clients.comdex_client, wallets_list.wallet_digriz_keplr_8_comdex_chain)
    elif choice == "3":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'comdex', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_comdex', 'digriz_keplr_8_juno', 'channel-18', 160000,
                     ledger_clients.comdex_client, wallets_list.wallet_digriz_keplr_8_comdex_chain)
    elif choice == "4":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'comdex', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_comdex', 'digriz_keplr_8_cosmoshub', 'channel-37', 160000,
                     ledger_clients.comdex_client, wallets_list.wallet_digriz_keplr_8_comdex_chain)
    elif choice == "5":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'comdex', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_comdex', 'digriz_keplr_8_kujira', 'channel-31', 160000,
                     ledger_clients.comdex_client, wallets_list.wallet_digriz_keplr_8_comdex_chain)
    elif choice == "6":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_transfer_ibc()
    elif choice == "7":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc_comdex()


def menu_transfer_ibc_bostrom():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Transfer IBC Bostrom" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC Bostrom to Osmosis")
    print("2. Transfer IBC Bostrom to Gravity Bridge")
    print("3. Transfer IBC Bostrom to Juno")
    print("4. Transfer IBC Bostrom to Cosmoshub")
    print(Fore.YELLOW + "5. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "6. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'bostrom', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_bostrom', 'digriz_keplr_8_osmosis', 'channel-2', 160000,
                     ledger_clients.bostrom_client, wallets_list.wallet_digriz_keplr_8_bostrom_chain)
    elif choice == "2":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'bostrom', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_bostrom', 'digriz_keplr_8_gravitybridge', 'channel-12', 160000,
                     ledger_clients.bostrom_client, wallets_list.wallet_digriz_keplr_8_bostrom_chain)
    elif choice == "3":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'bostrom', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_bostrom', 'digriz_keplr_8_juno', 'channel-10', 160000,
                     ledger_clients.bostrom_client, wallets_list.wallet_digriz_keplr_8_bostrom_chain)
    elif choice == "4":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'bostrom', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_bostrom', 'digriz_keplr_8_cosmoshub', 'channel-8', 160000,
                     ledger_clients.bostrom_client, wallets_list.wallet_digriz_keplr_8_bostrom_chain)
    elif choice == "5":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_transfer_ibc()
    elif choice == "6":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc_bostrom()


def menu_transfer_ibc_kujira():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Transfer IBC Kujira" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Transfer IBC Kujira to Osmosis")
    print("2. Transfer IBC Kujira to Gravity Bridge")
    print("3. Transfer IBC Kujira to Comdex")
    print("4. Transfer IBC Kujira to Cosmoshub")
    print(Fore.YELLOW + "5. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "6. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'kujira', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_kujira', 'digriz_keplr_8_osmosis', 'channel-3', 160000,
                     ledger_clients.kujira_client, wallets_list.wallet_digriz_keplr_8_kujira_chain)
    elif choice == "2":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'kujira', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_kujira', 'digriz_keplr_8_gravitybridge', 'channel-50', 160000,
                     ledger_clients.kujira_client, wallets_list.wallet_digriz_keplr_8_kujira_chain)
    elif choice == "3":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'kujira', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_kujira', 'digriz_keplr_8_comdex', 'channel-18', 160000,
                     ledger_clients.kujira_client, wallets_list.wallet_digriz_keplr_8_kujira_chain)
    elif choice == "4":
        clear_menu(True)
        symbol_transfer = str(input("Enter the transfer symbol: "))
        amount_transfer = float(input("Enter the transfer amount: "))
        transfer_ibc(symbol_transfer, 'kujira', path_filename.address_book, path_filename.denoms_book_path, 120,
                     amount_transfer,
                     'digriz_keplr_8_kujira', 'digriz_keplr_8_cosmoshub', 'channel-0', 160000,
                     ledger_clients.kujira_client, wallets_list.wallet_digriz_keplr_8_kujira_chain)
    elif choice == "5":
        from menu.main_menu import main_menu
        clear_menu(True)
        return menu_transfer_ibc()
    elif choice == "6":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_transfer_ibc_kujira()
