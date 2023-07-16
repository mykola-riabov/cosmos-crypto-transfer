import json


def get_denom_contract(symbol, network, json_file):
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
            for item in data:
                if item.get('symbol') == symbol and item.get('network') == network:
                    return item.get('denom_contract')
            print(f"Error: No matching symbol '{symbol}' and network '{network}' found in JSON file.")
            return None
    except FileNotFoundError:
        print(f"Error: JSON file '{json_file}' not found.")
        return None
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON file '{json_file}': {e}")
        return None
