import logging
import os

from config.config_path_files import PathFileName

_configured = False


def setup_logging():
    global _configured
    if _configured:
        return logging.getLogger('cosmos_crypto_transfer')

    path_filename = PathFileName()
    os.makedirs(os.path.dirname(path_filename.transaction_log), exist_ok=True)

    logging.basicConfig(
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO,
        filename=path_filename.transaction_log,
    )
    _configured = True
    return logging.getLogger('cosmos_crypto_transfer')
