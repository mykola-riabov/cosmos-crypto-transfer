import pykeepass
import os
from config.config_path import ConfigPath
from config.config_files import FileName
from config.config_path_files import PathFileName

path = ConfigPath()
filename = FileName()
path_filename = PathFileName()


def get_creds_info():

    if not os.path.exists(path.creds_path):
        print('Error: directory not found:', path.creds_path)
        return
    if not os.path.exists(path_filename.db_keepass_filepath):
        print('Error: DB file not found')
        return
    if not os.path.exists(path_filename.key_keepass_filepath):
        print('Error: key file not found')
        return

    # open database with key
    with pykeepass.PyKeePass(path_filename.db_keepass_filepath, keyfile=path_filename.key_keepass_filepath) as kp:
        # find the desired record in the database
        group = kp.find_groups(name=filename.group_keepass, first=True)
        entry = kp.find_entries(title=filename.title_keepass, group=group, first=True)

        # get the value of the mnemonic field
        mnemonic_1 = entry.get_custom_property(filename.mnemonic_1_keepass)
        api = entry.get_custom_property('api')
        return {f'{filename.mnemonic_1_keepass}': mnemonic_1,
                'api': api
                }
