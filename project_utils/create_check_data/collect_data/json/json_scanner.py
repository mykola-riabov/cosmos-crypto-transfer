from colorama import init, Fore, Style
import json
import os
import shutil
import subprocess

init(autoreset=True)


def check_info(input_directory, output_directory, output_file_name, key1, key2):
    result = {}  # Create an empty dictionary for the result
    for filename in os.listdir(input_directory):
        file_path = os.path.join(input_directory, filename)
        if os.path.isfile(file_path) and filename.endswith(".json"):
            # If it's a .json file, process it
            try:
                with open(file_path, 'r', encoding='utf-8') as f_in:
                    data = json.load(f_in)
            except json.JSONDecodeError:
                continue
            chain_name = data.get(key1)
            chain_id = data.get(key2)
            if chain_name and chain_id:
                result[chain_name] = chain_id
        elif os.path.isdir(file_path):
            # If it's a subdirectory, call the function recursively
            result.update(
                check_info(file_path, output_directory, output_file_name, key1, key2))  # Update the result dictionary

    output_file_path = os.path.join(output_directory, output_file_name)
    # Sort the dictionary by the value corresponding to key2
    sorted_result = sorted(result.items(), key=lambda x: x[0])
    result = dict(sorted_result)
    with open(output_file_path, 'w') as f_out:
        json.dump(result, f_out, indent=4)
    return result


def chain_should_skip(content, chain_list=None):
    skip_conditions = [
        not content.get('fees'),
        not content.get('$schema', '').endswith('chain.schema.json'),
        'testnet' in content.get('network_type', '').lower(),
        'testnet' in content.get('chain_id', '').lower(),
        'devnet' in content.get('network_type', '').lower(),
        'devnet' in content.get('chain_id', '').lower(),
        'killed' in content.get('status', '').lower(),
        content.get('chain_id', '').lower().startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9')),
    ]
    if chain_list:
        allowed = {x.replace(' ', '').lower() for x in chain_list}
        skip_conditions.append(
            content.get('chain_id', '').replace(' ', '').lower() not in allowed
        )
    return any(skip_conditions)


# ======================================================================================================================
def keplr_should_skip(content, chain_list=None):
    if not chain_list:
        return 'chainId' not in content
    allowed = {x.replace(' ', '').lower() for x in chain_list}
    skip_conditions = [
        'chainId' not in content
        or content['chainId'].replace(' ', '').lower() not in allowed,
    ]
    return any(skip_conditions)


# ======================================================================================================================

def check_address(address):
    if '/' not in address[-1]:
        cmd = f'curl --max-time 5 -s {address}/cosmos/base/tendermint/v1beta1/node_info'
    else:
        cmd = f'curl --max-time 5 -s {address}cosmos/base/tendermint/v1beta1/node_info'
    result = subprocess.run(cmd, shell=True, capture_output=True)
    if result.returncode == 0:
        return True
    else:
        return False


# ======================================================================================================================
def traverse_directory_chain_data(input_path_dir, input_path_dir2, output_path_filename,
                                  extract_chain_keys, extract_keplr_chain_keys, chain_list,
                                  verify_rest=True):
    results_chain_data = []
    with open(output_path_filename, 'w') as f_out:
        for root, dirs, files in os.walk(input_path_dir):
            for cosmos_data in files:
                if cosmos_data != 'chain.json':
                    continue
                file_path = os.path.join(root, cosmos_data)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f_in:
                        content = json.load(f_in)
                except json.JSONDecodeError:
                    continue
                if chain_should_skip(content, chain_list):
                    continue
                result = {}
                for key in extract_chain_keys:
                    if key == 'denom':
                        result[key] = content['fees']['fee_tokens'][0].get('denom')
                    elif key in content['fees']['fee_tokens'][0]:
                        result[key] = content['fees']['fee_tokens'][0].get(key)
                    elif key in content:
                        result[key] = content.get(key)
                    else:
                        result[key] = None
                apis = content.get('apis', {}).get('rest', [])
                result['rest_link'] = None
                if verify_rest:
                    for api in apis:
                        address = api.get('address', '')
                        if check_address(address):
                            print(f'[{result.get("chain_id")}] {address} is working')
                            result['rest_link'] = address
                            break
                else:
                    for api in apis:
                        address = (api.get('address') or '').strip()
                        if address:
                            result['rest_link'] = address
                            break
                result.pop('apis', None)
                results_chain_data.append(result)

        keplr_rows = []
        for root, dirs, files in os.walk(input_path_dir2):
            for cosmos_data in files:
                if not cosmos_data.endswith('.json'):
                    continue
                file_path = os.path.join(root, cosmos_data)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                except (json.JSONDecodeError, OSError):
                    continue
                if keplr_should_skip(content, chain_list):
                    continue
                chain_id = content.get('chainId')
                if not chain_id:
                    continue
                result = {'chain_id': chain_id}
                if 'rest' in content:
                    result['keplr_rest_link'] = content['rest']
                keplr_rows.append(result)

        chain_rows = list(results_chain_data)

        merged_results = {}
        for result in chain_rows:
            chain_id = result.get('chain_id')
            if not chain_id:
                continue
            merged_results[chain_id] = result

        for result in keplr_rows:
            chain_id = result.get('chain_id')
            if not chain_id:
                continue
            if chain_id in merged_results:
                merged_results[chain_id].update(result)

        merged_list = [
            row for row in merged_results.values()
            if row.get('chain_name')
        ]
        merged_list.sort(key=lambda x: (x.get('chain_name') or '').lower())

        json.dump(merged_list, f_out, indent=4)
    print(Fore.GREEN + 'Successful completion of scanning and creation Data Chain' + Style.RESET_ALL)


def init_data_list(input_path, output_path, filename_file):
    files = os.listdir(input_path)
    if len(files) == 0:
        print(f"Error: no files found in directory '{input_path}'")
        exit()
    latest_file = max(files, key=lambda f: os.path.getmtime(os.path.join(input_path, f)))
    new_file_path = os.path.join(output_path, filename_file)
    if os.path.isfile(new_file_path):
        os.remove(new_file_path)
        print(f"Warning: file '{new_file_path}' already exists and will be overwritten")
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    try:
        shutil.copy2(os.path.join(input_path, latest_file), new_file_path)
        os.rename(new_file_path, os.path.join(output_path, filename_file))
    except (shutil.Error, OSError) as e:
        print(f"Error occurred during file copy/renaming: {e}")
    else:
        print(
            f"File '{latest_file}' has been copied to '{output_path}' and renamed to '{filename_file}'")
