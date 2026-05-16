from colorama import init

from config.config_path_files import PathFileName
from menu.menu_runner import run_menu
from menu.menu_setting import clear_menu
from project_utils.template.book import search_by_name, view_all_addresses, view_by_network

init(autoreset=True)
path_filename = PathFileName()


def menu_addresses_book_crypto_management():
    def view_all():
        clear_menu(True)
        view_all_addresses(path_filename.address_book)

    def search():
        clear_menu(True)
        search_by_name(path_filename.address_book)

    def by_network():
        clear_menu(True)
        view_by_network(path_filename.address_book)

    while True:
        items = [
            ('1', 'View all addresses', view_all),
            ('2', 'Search address by name', search),
            ('3', 'View addresses for specified network', by_network),
        ]

        result = run_menu('Addresses book', items)
        if result == 'back':
            return
        if result == 'exit':
            raise SystemExit(0)
