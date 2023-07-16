import os
import requests
import json


def download_api_data(url, file_path):
    folder_path, file_name = os.path.split(file_path)

    # Check if the folder exists, if not, create the folder
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f'Folder created: {folder_path}')

    # Check if the file exists, if so, notify and overwrite, if not, notify and create a new file
    if os.path.exists(file_path):
        print(f'File already exists: {file_path}. Overwriting...')
    else:
        print(f'File does not exist: {file_path}. Creating...')

    response = requests.get(url)

    # Check the response status code
    if response.status_code == 200:
        # Parse JSON data from the response
        data = response.json()

        # Save data to a JSON file
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f'Data successfully saved to file: {file_path}')
    else:
        print('Error while executing API request')