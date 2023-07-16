import os
import subprocess
import sys
import platform
from colorama import init, Fore, Style
init(autoreset=True)


def source_create_or_check():
    root_path = os.path.abspath(os.getcwd())
    root_chain_path = os.path.join(root_path, "chain")
    root_clients_path = os.path.join(root_chain_path, "clients")
    root_wallets_path = os.path.join(root_chain_path, "wallets")
    if not os.path.exists(root_chain_path):
        os.makedirs(root_chain_path)
    if not os.path.exists(root_clients_path):
        os.makedirs(root_clients_path)
    if not os.path.exists(root_wallets_path):
        os.makedirs(root_wallets_path)
    root_action_crypto_path = os.path.join(root_path, "action_crypto")
    root_bank_path = os.path.join(root_action_crypto_path, "bank")
    if not os.path.exists(root_action_crypto_path):
        os.makedirs(root_action_crypto_path)
    if not os.path.exists(root_bank_path):
        os.makedirs(root_bank_path)
    root_addresses_path = os.path.join(root_path, "addresses")
    if not os.path.exists(root_addresses_path):
        os.makedirs(root_addresses_path)
    root_denoms_path = os.path.join(root_addresses_path, "denoms")
    if not os.path.exists(root_denoms_path):
        os.makedirs(root_denoms_path)
    root_pools_path = os.path.join(root_addresses_path, "pools")
    if not os.path.exists(root_pools_path):
        os.makedirs(root_pools_path)

    source_path = os.path.join(root_path, "..", "source")
    backup_path = os.path.join(root_path, "..", "backup")
    if not os.path.exists(source_path):
        os.makedirs(source_path)
    if not os.path.exists(backup_path):
        os.makedirs(backup_path)

    creds_path = os.path.join(source_path, "creds")
    data_path = os.path.join(source_path, "data")
    temp_path = os.path.join(source_path, "temp")
    if not os.path.exists(creds_path):
        os.makedirs(creds_path)
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    if not os.path.exists(temp_path):
        os.makedirs(temp_path)

    assets_path = os.path.join(temp_path, "assets")
    chain_path = os.path.join(temp_path, "chain")
    create_path = os.path.join(temp_path, "create")
    data_api_path = os.path.join(temp_path, "data_api")
    logs_path = os.path.join(temp_path, "logs")
    if not os.path.exists(assets_path):
        os.makedirs(assets_path)
    if not os.path.exists(chain_path):
        os.makedirs(chain_path)
    if not os.path.exists(create_path):
        os.makedirs(create_path)
    if not os.path.exists(data_api_path):
        os.makedirs(data_api_path)
    if not os.path.exists(logs_path):
        os.makedirs(logs_path)

    chain_registry_path = os.path.join(source_path, "chain-registry")
    if not os.path.exists(chain_registry_path):
        subprocess.run(["git", "clone", "https://github.com/cosmos/chain-registry", chain_registry_path], check=True)
        print(Fore.GREEN + "The chain-registry repository has been cloned." + Style.RESET_ALL)
    else:
        subprocess.run(["git", "-C", chain_registry_path, "pull"], check=True)
        print(Fore.GREEN + "The chain-registry repository has been updated." + Style.RESET_ALL)
    keplr_chain_registry_path = os.path.join(source_path, "keplr-chain-registry")
    if not os.path.exists(keplr_chain_registry_path):
        subprocess.run(
            ["git", "clone", "https://github.com/chainapsis/keplr-chain-registry", keplr_chain_registry_path],
            check=True)
        print(Fore.GREEN + "The keplr-chain-registry repository has been cloned." + Style.RESET_ALL)
    else:
        subprocess.run(["git", "-C", keplr_chain_registry_path, "pull"], check=True)
        print(Fore.GREEN + "The keplr-chain-registry repository has been updated." + Style.RESET_ALL)

    config_path = os.path.join(root_path, "config")
    if not os.path.exists(config_path):
        os.makedirs(config_path)

    config_path_file = os.path.join(config_path, "config_path.py")
    with open(config_path_file, 'w') as f:
        f.write("class ConfigPath:\n")
        f.write(f"    project_path = '{os.path.abspath(root_path)}'\n")
        f.write(f"    source_path = '{os.path.abspath(source_path)}'\n")
        f.write(f"    backup_path = '{os.path.abspath(backup_path)}'\n")
        f.write(f"    creds_path = '{os.path.abspath(creds_path)}'\n")
        f.write(f"    data_path = '{os.path.abspath(data_path)}'\n")
        f.write(f"    temp_path = '{os.path.abspath(temp_path)}'\n")
        f.write(f"    assets_path = '{os.path.abspath(assets_path)}'\n")
        f.write(f"    chain_path = '{os.path.abspath(chain_path)}'\n")
        f.write(f"    create_path = '{os.path.abspath(create_path)}'\n")
        f.write(f"    chain_registry_path = '{os.path.abspath(chain_registry_path)}'\n")
        f.write(f"    keplr_chain_registry_path = '{os.path.abspath(keplr_chain_registry_path)}'\n")
        f.write(f"    root_chain_path = '{os.path.abspath(root_chain_path)}'\n")
        f.write(f"    root_client_path = '{os.path.abspath(root_clients_path)}'\n")
        f.write(f"    root_wallet_path = '{os.path.abspath(root_wallets_path)}'\n")
        f.write(f"    root_config_path = '{os.path.abspath(config_path)}'\n")
        f.write(f"    root_action_crypto = '{os.path.abspath(root_action_crypto_path)}'\n")
        f.write(f"    root_bank = '{os.path.abspath(root_bank_path)}'\n")
        f.write(f"    root_addresses_path = '{os.path.abspath(root_addresses_path)}'\n")
        f.write(f"    root_denoms_path = '{os.path.abspath(root_denoms_path)}'\n")
        f.write(f"    root_pools_path = '{os.path.abspath(root_pools_path)}'\n")
        f.write(f"    data_api_path = '{os.path.abspath(data_api_path)}'\n")
        f.write(f"    logs_path = '{os.path.abspath(logs_path)}'\n")

    print(Fore.GREEN + "Check data has been successfully created." + Style.RESET_ALL)


# ======================================================================================================================
def check_platform():
    if platform.system() == 'Windows':
        print(Fore.RED + "The application doesn't work on Windows, only on Linux." + Style.RESET_ALL)
    else:
        print(Fore.GREEN + "Great, Linux system on board!" + Style.RESET_ALL)
#        exit()


# ======================================================================================================================
def check_apps():
    try:
        subprocess.run(['git', '--version'], check=True)
    except FileNotFoundError:
        print(Fore.RED + "Git is not installed on your system." + Style.RESET_ALL)
        choice = input("Do you want to install Git? (Y/N): ")
        if choice.lower() == 'y':
            subprocess.run(['sudo', 'apt-get', 'install', 'git'])
    try:
        subprocess.run(['pip3', '--version'], check=True)
    except FileNotFoundError:
        print(Fore.RED + "Pip3 is not installed on your system." + Style.RESET_ALL)
        choice = input("Do you want to install pip3? (Y/N): ")
        if choice.lower() == 'y':
            subprocess.run(['sudo', 'apt-get', 'install', 'pip3'])
    try:
        subprocess.run(['tree', '--version'], check=True)
    except FileNotFoundError:
        print(Fore.RED + "tree is not installed on your system." + Style.RESET_ALL)
        choice = input("Do you want to install tree? (Y/N): ")
        if choice.lower() == 'y':
            subprocess.run(['sudo', 'apt-get', 'install', 'tree'])
    try:
        subprocess.run(['curl', '--version'], check=True)
    except FileNotFoundError:
        print(Fore.RED + "curl is not installed on your system." + Style.RESET_ALL)
        choice = input("Do you want to install curl? (Y/N): ")
        if choice.lower() == 'y':
            subprocess.run(['sudo', 'apt-get', 'install', 'curl'])


# ======================================================================================================================
def check_python_modules(modules_list_for_project):
    modules = modules_list_for_project
    not_installed_modules = []
    installed_modules = []

    for module in modules:
        try:
            subprocess.run(['pip3', 'show', module], check=True)
            installed_modules.append(module)
        except subprocess.CalledProcessError:
            not_installed_modules.append(module)

    if not_installed_modules:
        print(Fore.RED + "The following modules are not installed on your system:" + Style.RESET_ALL)
        print(", ".join(not_installed_modules))
        while True:
            choice = input("Do you want to install them? (yes/no): ").lower()
            if choice == 'yes':
                subprocess.run(['pip3', 'install'] + not_installed_modules,
                               check=True)
                installed_modules.extend(not_installed_modules)
                print(Fore.GREEN + "Successfully installed the following modules:" + Style.RESET_ALL)
                print(", ".join(not_installed_modules))
                break
            elif choice == 'no':
                exit()
            else:
                print("Invalid choice. Please enter 'yes' or 'no'.")

    print(Fore.GREEN + "All required modules are installed:" + Style.RESET_ALL)
    print(", ".join(installed_modules))


# ======================================================================================================================
def check_pythonpath(project_path):
    # Paths to .bashrc and .zshrc files in the user's home directory
    bashrc_path = os.path.expanduser("~/.bashrc")
    zshrc_path = os.path.expanduser("~/.zshrc")

    # Check if .bashrc and .zshrc files exist
    if not os.path.exists(bashrc_path) or not os.path.exists(zshrc_path):
        print("File .bashrc or .zshrc not found in user's home directory.")
        exit()

    # Function to check if a line exists in a file
    def check_line_in_file(file_path, line):
        with open(file_path, "r") as file:
            for fline in file:
                if line in fline:
                    return True
        return False

    # Function to add a line to a file
    def add_line_to_file(file_path, line):
        with open(file_path, "a") as file:
            file.write(line + "\n")

    # Check for the presence of the entry in .bashrc
    bashrc_line = f'export PYTHONPATH="{project_path}"'
    if not check_line_in_file(bashrc_path, bashrc_line):
        print(f"Entry not found in .bashrc: {bashrc_line}")
        add_line_to_file(bashrc_path, bashrc_line)
        print(f"Entry added to .bashrc")
    else:
        print(f"Entry {bashrc_line} already present in .bashrc")

    # Check for the presence of the entry in .zshrc
    zshrc_line = f'export PYTHONPATH="{project_path}"'
    if not check_line_in_file(zshrc_path, zshrc_line):
        print(f"Entry not found in .zshrc: {zshrc_line}")
        add_line_to_file(zshrc_path, zshrc_line)
        print(f"Entry added to .zshrc")
    else:
        print(f"Entry {zshrc_line} already present in .zshrc")
