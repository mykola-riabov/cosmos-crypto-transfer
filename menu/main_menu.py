from colorama import Fore, Style, init

from menu.menu_setting import clear_menu
from project_utils.logging_setup import setup_logging


def main_menu():
    init(autoreset=True)
    setup_logging()

    while True:
        clear_menu(True)
        print(Fore.RED + '################################################' + Style.RESET_ALL)
        print(Fore.GREEN + 'Welcome to the Cosmos Crypto Transfer System!' + Style.RESET_ALL)
        print(Fore.RED + '################################################' + Style.RESET_ALL)
        print('1. Action crypto management')
        print('2. Addresses book')
        print('3. Check and create data')
        print(Fore.RED + '4. Exit' + Style.RESET_ALL)

        choice = input('Enter your choice: ').strip()
        if choice == '1':
            clear_menu(True)
            from menu.menu_action import menu_action_crypto_management

            menu_action_crypto_management()
        elif choice == '2':
            clear_menu(True)
            from menu.menu_addresses_book import menu_addresses_book_crypto_management

            menu_addresses_book_crypto_management()
        elif choice == '3':
            clear_menu(True)
            from menu.menu_check_apps_create_data import check_and_create_data

            check_and_create_data()
        elif choice == '4':
            print('Exiting program...')
            clear_menu(True)
            break
        else:
            print('Invalid choice. Please try again.')
