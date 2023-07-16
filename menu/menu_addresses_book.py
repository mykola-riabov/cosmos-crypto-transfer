from colorama import init, Fore, Style
from project_utils.template.book import view_all_addresses, search_by_name, view_by_network
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


def menu_addresses_book_crypto_management():
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Welcome to the Addresses book!" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. View all addresses")
    print("2. Search address by name")
    print("3. View addresses for specified network")
    print(Fore.YELLOW + "4. Back to main menu" + Style.RESET_ALL)
    print(Fore.RED + "5. Exit" + Style.RESET_ALL)

    choice = input("Enter your choice: ")
    if choice == "1":
        clear_menu(True)
        view_all_addresses(path_filename.address_book)
    elif choice == "2":
        clear_menu(True)
        search_by_name(path_filename.address_book)
    elif choice == "3":
        clear_menu(True)
        view_by_network(path_filename.address_book)
    elif choice == "4":
        from menu.main_menu import main_menu
        clear_menu(True)
        return main_menu()
    elif choice == "5":
        print("Exiting program...")
        clear_menu(True)
        exit()
    menu_addresses_book_crypto_management()

