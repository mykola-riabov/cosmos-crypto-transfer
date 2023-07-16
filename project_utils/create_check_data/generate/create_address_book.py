import os
import json


def create_addresses_book(input_dir, input_filename, output_dir, output_filename):
    # Check if input directory and file exist
    if not os.path.exists(os.path.join(input_dir, input_filename)):
        print(f"Directory {input_dir} or file {input_filename} does not exist.")
        return

    # Load the content of input file
    with open(os.path.join(input_dir, input_filename), "r") as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError as e:
            print(f"Failed to load {input_filename}: {e}")
            return

    # Check if output directory exists
    if not os.path.exists(output_dir):
        print(f"Directory {output_dir} does not exist.")
        return

    # Generate data for output file
    output = []
    for key in data.keys():
        # Extract name from key
        name = key.replace("address_", "").replace("_chain", "")
        # Extract address value from key
        address_value = data[key]
        # Extract network value from name
        network = name.split("_")[-1]

        # Create a dictionary with the required values
        output.append({
            "name": name,
            "address": address_value,
            "network": network
        })

    # Write data to output file
    with open(os.path.join(output_dir, output_filename), "w") as file:
        json.dump(output, file, indent=4)

    print(f"File {output_filename} has been generated in directory {output_dir}.")
