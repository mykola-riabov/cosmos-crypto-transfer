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
            with open(file_path, 'r') as f_in:
                data = json.load(f_in)
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


def chain_should_skip(content, chain_list):
    skip_conditions = [
        not content.get('fees'),
        not content.get('$schema', '').endswith('chain.schema.json'),
        content.get('chain_id', '').lower() not in chain_list,
        'testnet' in content.get('network_type', '').lower(),
        'testnet' in content.get('chain_id', '').lower(),
        'devnet' in content.get('network_type', '').lower(),
        'devnet' in content.get('chain_id', '').lower(),
        'killed' in content.get('status', '').lower(),
        content.get('chain_id', '').lower().startswith(('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'))
    ]
    return any(skip_conditions)


# ======================================================================================================================
def keplr_should_skip(content, chain_list):
    skip_conditions = [
        'chainId' not in content or content['chainId'].replace(" ", "").lower() not in [
            x.replace(" ", "").lower() for x in chain_list]
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
                                  extract_chain_keys, extract_keplr_chain_keys, chain_list):
    results_chain_data = []
    with open(output_path_filename, 'w') as f_out:
        for root, dirs, files in os.walk(input_path_dir):
            for cosmos_data in files:
                if cosmos_data.endswith('.json'):
                    file_path = os.path.join(root, cosmos_data)
                    # Reading the content of the file
                    with open(file_path, 'r') as f_in:
                        content = json.load(f_in)
                    # Extract the necessary data.
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
                    # Adding the 'rest_link' key
                    apis = content.get('apis', {}).get('rest', [])
                    for api in apis:
                        address = api.get('address', '')
                        if check_address(address):
                            print(f'[{result["chain_id"]}] {address} is working')
                            result['rest_link'] = address
                            break
                    else:
                        result['rest_link'] = None
                    # Removing the 'apis' key from the result
                    result.pop('apis', None)
                    # Adding a result
                    results_chain_data.append(result)
        # Additional scanning of second directory and appending matching data to results
        for root, dirs, files in os.walk(input_path_dir2):
            for cosmos_data in files:
                if cosmos_data.endswith('.json'):
                    file_path = os.path.join(root, cosmos_data)
                    try:
                        # Reading the content of the file
                        with open(file_path, 'r') as f:
                            content = json.load(f)
                        # Extract the necessary data.
                        if keplr_should_skip(content, chain_list):
                            continue
                        result = {}
                        # Extract data using 'chainId' key
                        chain_id = content.get('chainId', None)
                        if chain_id is not None:
                            # Change the key from 'chainId' to 'chain_id'
                            result['chain_id'] = chain_id
                            for key in extract_keplr_chain_keys:
                                if key == 'chainId':
                                    continue  # Skip 'chainId' key
                                elif key == 'rest':
                                    if 'rest' in content:  # Check if 'rest' key exists in content
                                        result['keplr_rest_link'] = content['rest']
                                else:
                                    if key in content:  # Check if the key exists in content
                                        result[key] = content.get(key, None)
                                if key != 'rest' and result.get(key) is None:
                                    # If the field is missing, skip the file
                                    continue
                            # Adding a result
                            results_chain_data.append(result)
                    except (json.JSONDecodeError, KeyError) as e:
                        # Skip files with JSON syntax errors or missing keys
                        print(f'Error while reading file {file_path}: {e}')
                        continue
        # Merging results_chain_data by 'chain_id'
        merged_results = {}
        for result in results_chain_data:
            chain_id = result['chain_id']
            if chain_id not in merged_results:
                merged_results[chain_id] = result
            else:
                merged_results[chain_id].update(result)

        # Sorting merged results by 'chain_id'
        merged_results = sorted(merged_results.values(), key=lambda x: x['chain_name'])

        json.dump(merged_results, f_out, indent=4)
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
