import json
from tabulate import tabulate


# Function to read data from JSON file
def read_data_from_json(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f'File "{file_path}" not found.')
        return None
    except json.JSONDecodeError:
        print(f'Error decoding JSON file: "{file_path}".')
        return None


# Function to view all addresses
def view_all_addresses(file_path):
    data = read_data_from_json(file_path)
    if data is not None:
        print("All addresses in the address book:")
        headers = ["Name", "Address", "Network"]
        rows = []
        for entry in data:
            row = [entry["name"], entry["address"], entry["network"]]
            rows.append(row)
        print(tabulate(rows, headers=headers))


# Function to search address by name
def search_by_name(file_path):
    name = input("Enter name for search: ")
    data = read_data_from_json(file_path)
    if data is not None:
        found = False
        for entry in data:
            if entry['name'] == name:
                print(f'Name: {entry["name"]}\nAddress: {entry["address"]}\nNetwork: {entry["network"]}\n')
                found = True
        if not found:
            print(f'Address with name "{name}" not found.')


# Function to view addresses for specified network
def view_by_network(file_path):
    network = input("Enter network name to view addresses: ")
    data = read_data_from_json(file_path)
    if data is not None:
        found = False
        print(f'Addresses for network "{network}":')
        for entry in data:
            if entry['network'] == network:
                print(f'Name: {entry["name"]}\nAddress: {entry["address"]}\nNetwork: {entry["network"]}\n')
                found = True
        if not found:
            print(f'Addresses for network "{network}" not found.')
