import os
from config.config_path import ConfigPath
from config.config_files import FileName

path = ConfigPath()
filename = FileName()


class PathFileName:
    backup_path_file_name = os.path.join(path.backup_path, filename.backup_file)
    result_collection_chain_file_name = os.path.join(path.chain_path, filename.result_collection_chain)
    result_collection_assets_file_name = os.path.join(path.assets_path, filename.result_collection_assets)
    report_filepath_rpc_link = os.path.join(path.create_path, filename.report_rpc_link)
    report_filepath_rest_link = os.path.join(path.create_path, filename.report_rest_link)
    report_filepath_grpc_link = os.path.join(path.create_path, filename.report_grpc_link)
    report_filepath_chain = os.path.join(path.create_path, filename.filename_chain_data_to_create)
    report_filepath_keplr_chain = os.path.join(path.create_path, filename.filename_chain_keplr_data_to_create)
    report_filepath_assets = os.path.join(path.create_path, filename.filename_assets_data_to_create)
    data_cosmos_file_name = os.path.join(path.data_path, filename.filename_cosmos_data)
    db_keepass_filepath = os.path.join(path.creds_path, filename.filename_db_crypto_managements)
    key_keepass_filepath = os.path.join(path.creds_path, filename.filename_key_crypto_managements)
    google_api_key = os.path.join(path.creds_path, filename.filename_google_api)
    wallets_list_path = os.path.join(path.root_wallet_path, filename.filename_wallets_list)
    address_book_temp = os.path.join(path.create_path, filename.filename_temp_address_book)
    address_book = os.path.join(path.data_path, filename.filename_address_book)
    ledger_client_mapping = os.path.join(path.data_path, filename.filename_ledger_client_mapping)
    ledger_clients = os.path.join(path.root_client_path, filename.project_file_ledger_client)
    chain_list = os.path.join(path.root_config_path, filename.filename_chain_list)
    denoms_book_path = os.path.join(path.root_denoms_path, filename.filename_denoms_book)
    pools_book_path = os.path.join(path.root_pools_path, filename.filename_pools_book)
    transaction_log = os.path.join(path.logs_path, filename.filename_transaction_log)
    status_signal_path = os.path.join(path.data_path, filename.file_name_status_signal)
    last_period_path = os.path.join(path.data_path, filename.file_name_last_period)
    status_signal_log_path = os.path.join(path.data_path, filename.file_name_log_signal)
    binance_ohlc_db_path = os.path.join(path.data_path, filename.file_name_binance_ohlc_db)
    dwl_data_binance_log_path = os.path.join(path.data_path, filename.file_name_log_dwl_binance)
