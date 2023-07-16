def main_menu():
    from colorama import init, Fore, Style
    init(autoreset=True)
    from menu.menu_setting import clear_menu
    clear_menu(True)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print(Fore.GREEN + "Welcome to the Cosmos Crypto Transfer System!" + Style.RESET_ALL)
    print(Fore.RED + "################################################" + Style.RESET_ALL)
    print("1. Action crypto management")
    print("2. Addresses book")
    print("3. Check and create data")
    print(Fore.RED + "5. Exit" + Style.RESET_ALL)
    choice = input("Enter your choice: ")
    if choice == "1":
        from menu.menu_setting import clear_menu
        clear_menu(True)
        from menu.menu_action import menu_action_crypto_management
        menu_action_crypto_management()
    elif choice == "2":
        from menu.menu_setting import clear_menu
        clear_menu(True)
        from menu.menu_addresses_book import menu_addresses_book_crypto_management
        menu_addresses_book_crypto_management()
    elif choice == "3":
        from menu.menu_setting import clear_menu
        from menu.menu_check_apps_create_data import check_and_create_data
        clear_menu(True)
        check_and_create_data()
    elif choice == "4":
        from menu.menu_setting import clear_menu
        print("Exiting program...")
        clear_menu(True)
        exit()
    else:
        print("Invalid choice. Please try again.")
    main_menu()
