import json
import os


def create_json_template(file_path, num_blocks):
    if not os.path.exists(file_path):
        # If the file does not exist, create a new file
        with open(file_path, 'w') as f:
            json.dump([], f, indent=4)
        print(f'JSON file created: {file_path}')

    with open(file_path, 'r+') as f:
        try:
            # Try to load data from the file
            data = json.load(f)
        except json.decoder.JSONDecodeError:
            # If the file is empty or has invalid JSON, create a new list
            data = []

        for i in range(num_blocks):
            # Generate data for a block
            block = {
                "symbol": f"symbol denom {i + 1}",
                "denom_contract": f"xxx {i + 1}",
                "network": f"network name {i + 1}",
                "decimal": f"xxx {i + 1}"
            }
            # Add the block to the data list
            data.append(block)

        # Move the file pointer to the end of the file and write the updated data
        f.seek(0, os.SEEK_END)
        json.dump(data, f, indent=4)
        f.truncate()

    print(f'Template JSON file updated: {file_path}')
