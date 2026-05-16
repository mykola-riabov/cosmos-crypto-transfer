import os
import shutil
import subprocess
import sys
import platform
from colorama import init, Fore, Style
init(autoreset=True)


def _ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def source_create_or_check():
    from config.config_path import ConfigPath

    path = ConfigPath()
    dirs = [
        path.root_chain_path,
        path.root_client_path,
        path.root_wallet_path,
        path.root_action_crypto,
        path.root_bank,
        path.root_addresses_path,
        path.root_denoms_path,
        path.root_pools_path,
        path.source_path,
        path.backup_path,
        path.creds_path,
        path.data_path,
        path.temp_path,
        path.assets_path,
        path.chain_path,
        path.create_path,
        path.data_api_path,
        path.logs_path,
    ]
    for directory in dirs:
        _ensure_dir(directory)

    from config.config_path_files import PathFileName
    paths = PathFileName()
    if not os.path.isfile(paths.wallet_json_filepath) and os.path.isfile(
        paths.wallet_json_example_filepath
    ):
        shutil.copy(paths.wallet_json_example_filepath, paths.wallet_json_filepath)
        print(
            Fore.YELLOW
            + f'Created {paths.wallet_json_filepath} from example — edit mnemonic before transfers.'
            + Style.RESET_ALL
        )

    chain_registry_path = path.chain_registry_path
    if not os.path.exists(chain_registry_path):
        subprocess.run(
            ['git', 'clone', 'https://github.com/cosmos/chain-registry', chain_registry_path],
            check=True,
        )
        print(Fore.GREEN + 'The chain-registry repository has been cloned.' + Style.RESET_ALL)
    else:
        subprocess.run(['git', '-C', chain_registry_path, 'pull'], check=True)
        print(Fore.GREEN + 'The chain-registry repository has been updated.' + Style.RESET_ALL)

    keplr_chain_registry_path = path.keplr_chain_registry_path
    if not os.path.exists(keplr_chain_registry_path):
        subprocess.run(
            [
                'git', 'clone',
                'https://github.com/chainapsis/keplr-chain-registry',
                keplr_chain_registry_path,
            ],
            check=True,
        )
        print(Fore.GREEN + 'The keplr-chain-registry repository has been cloned.' + Style.RESET_ALL)
    else:
        subprocess.run(['git', '-C', keplr_chain_registry_path, 'pull'], check=True)
        print(Fore.GREEN + 'The keplr-chain-registry repository has been updated.' + Style.RESET_ALL)

    print(Fore.GREEN + 'Directories and registries are ready.' + Style.RESET_ALL)
    print(Fore.CYAN + f'  Project: {path.project_path}' + Style.RESET_ALL)
    print(Fore.CYAN + f'  Source:  {path.source_path}' + Style.RESET_ALL)
    print(
        Fore.CYAN
        + '  Paths: config/config_path.py (override with COSMOS_PROJECT_ROOT / COSMOS_SOURCE_PATH).'
        + Style.RESET_ALL
    )


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
def _requirements_file_path():
    from config.config_path import ConfigPath
    return os.path.join(ConfigPath.project_path, 'requirements.txt')


def check_python_modules(modules_list_for_project=None):
    requirements_file = _requirements_file_path()
    if os.path.isfile(requirements_file):
        print(Fore.CYAN + f'Installing from {requirements_file} ...' + Style.RESET_ALL)
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', requirements_file], check=False)
        print(Fore.GREEN + 'Dependency install finished (see output above).' + Style.RESET_ALL)
        return

    modules = modules_list_for_project or []
    not_installed_modules = []
    installed_modules = []

    for module in modules:
        try:
            subprocess.run([sys.executable, '-m', 'pip', 'show', module], check=True, capture_output=True)
            installed_modules.append(module)
        except subprocess.CalledProcessError:
            not_installed_modules.append(module)

    if not_installed_modules:
        print(Fore.RED + 'The following modules are not installed:' + Style.RESET_ALL)
        print(', '.join(not_installed_modules))
        while True:
            choice = input('Do you want to install them? (yes/no): ').lower()
            if choice == 'yes':
                subprocess.run([sys.executable, '-m', 'pip', 'install'] + not_installed_modules, check=True)
                break
            if choice == 'no':
                exit()
            print("Invalid choice. Please enter 'yes' or 'no'.")


# ======================================================================================================================
def check_pythonpath(project_path):
    print(
        Fore.GREEN
        + 'Tip: run the app via `python menu_crypto.py` from the project root — PYTHONPATH is set automatically.'
        + Style.RESET_ALL
    )
    bashrc_path = os.path.expanduser('~/.bashrc')
    zshrc_path = os.path.expanduser('~/.zshrc')

    if not os.path.exists(bashrc_path) and not os.path.exists(zshrc_path):
        print('Optional: add PYTHONPATH to ~/.bashrc or ~/.zshrc if you import modules elsewhere.')
        return

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

    export_line = f'export PYTHONPATH="{project_path}"'
    for rc_path, rc_name in ((bashrc_path, '.bashrc'), (zshrc_path, '.zshrc')):
        if not os.path.exists(rc_path):
            continue
        if not check_line_in_file(rc_path, export_line):
            print(f'Entry not found in {rc_name}: {export_line}')
            add_line_to_file(rc_path, export_line)
            print(f'Entry added to {rc_name}')
        else:
            print(f'Entry already present in {rc_name}')
