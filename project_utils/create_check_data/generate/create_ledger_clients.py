from colorama import init, Fore, Style
import json
import os

init(autoreset=True)


def to_python_identifier(chain_name: str) -> str:
    ident = chain_name.replace('-', '_')
    if ident and ident[0].isdigit():
        ident = f'chain_{ident}'
    return ident


def create_ledger_clients_file(filename_by_path_cosmos, data_path, filename_cosmos, root_client_path,
                                 filename_ledger_client, link_type=None, enabled_networks=None):
    # check if cosmos_data_list.json exists
    print(filename_by_path_cosmos)
    if not os.path.exists(data_path):
        print('Error: directory not found:', data_path)
        return
    if not os.path.exists(os.path.join(data_path, filename_cosmos)):
        print('Error: cosmos_data_list.json file not found')
        return
    if link_type:
        selected_link_type = link_type.strip()
    else:
        selected_link_type = input("Select link type (rest_link or keplr_rest_link): ").strip()

    with open(os.path.join(data_path, filename_cosmos)) as f:
        data = json.load(f)

    # sort data by chain name
    data = sorted(data, key=lambda k: k['chain_name'])
    # write generated code to ledger_clients_generated.py
    with open(os.path.join(root_client_path, filename_ledger_client), 'w') as f:
        f.write('from cosmpy.aerial.client import LedgerClient, NetworkConfig\n')

        num_clients = 0
        chain_names = []
        enabled_set = set(enabled_networks) if enabled_networks is not None else None
        for chain in data:
            network_name = chain['chain_name']
            if enabled_set is not None and network_name not in enabled_set:
                continue
            chain_name = to_python_identifier(network_name)
            url = None
            link = chain.get(selected_link_type)
            if link is None:
                link = chain.get('rest_link') or chain.get('keplr_rest_link')
            if link:
                url = 'rest+' + link

            chain_id = chain['chain_id']
            fee_minimum_gas_price = chain['low_gas_price']
            if fee_minimum_gas_price is None:
                fee_minimum_gas_price = 0.001
            if fee_minimum_gas_price == 0:
                fee_minimum_gas_price = 0.001
            if url is None:
                continue
            chain_names.append(chain_name)
            fee_denomination = chain['denom']
            staking_denomination = chain['denom']

            f.write(f"{chain_name}_network_settings = NetworkConfig(\n")
            f.write(f"    url='{url}',\n")
            f.write(f"    chain_id='{chain_id}',\n")
            f.write(f"    fee_minimum_gas_price={fee_minimum_gas_price},\n")
            f.write(f"    fee_denomination='{fee_denomination}',\n")
            f.write(f"    staking_denomination='{staking_denomination}'\n")
            f.write(f")\n")
            f.write(f"{chain_name}_network_settings.validate()\n")
            f.write(f"{chain_name}_client = LedgerClient({chain_name}_network_settings)\n\n")
            num_clients += 1
            print(f"{network_name} ({chain_name}): {selected_link_type} - {url}")

    print(Fore.YELLOW + 'ledger_clients_generated.py file generated successfully' + Style.RESET_ALL)
    print(Fore.GREEN + f'{num_clients} ledger clients generated for chains:' + Style.RESET_ALL)


def create_ledger_client_mapping(input_file, output_file, enabled_networks=None):
    # Check if input file exists
    if not os.path.isfile(input_file):
        print(f"Error: Input file '{input_file}' does not exist.")
        return

    # Check if output directory exists and create if necessary
    output_dir = os.path.dirname(output_file)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: '{output_dir}'")

    # Check if output file exists
    if os.path.isfile(output_file):
        print(Fore.YELLOW + f"Warning: Output file '{output_file}' already exists and will be overwritten." + Style.RESET_ALL)

    with open(input_file, 'r') as f:
        data = json.load(f)
    network_client_mapping = []
    enabled_set = set(enabled_networks) if enabled_networks is not None else None
    for chain in data:
        network_name = chain['chain_name']
        if enabled_set is not None and network_name not in enabled_set:
            continue
        python_name = to_python_identifier(network_name)
        network_client_mapping.append({
            'network': network_name,
            'client': python_name + '_client',
        })
    # Sort the data alphabetically based on the 'network' key
    network_client_mapping = sorted(network_client_mapping, key=lambda x: x['network'])
    # Write generated data to output json file
    with open(output_file, 'w') as f:
        json.dump(network_client_mapping, f, indent=4)

    print(Fore.GREEN + f"Generated data has been written to file: '{output_file}'" + Style.RESET_ALL)