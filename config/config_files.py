from datetime import datetime

now = datetime.now()
timestamp = now.strftime("%Y-%m-%d_%H-%M-%S")


class PrefixFileName:
    wallet = 'wallet_'


class SuffixFileName:
    suffix_wallet_1 = '_wallet_1'


class FileName:
    backup_file = f'project_backup_{timestamp}.tar.gz'
    result_collection_chain = 'result_data_chain_' + timestamp + '.json'
    result_collection_keplr_chain = 'result_keplr_data_chain_' + timestamp + '.json'
    result_collection_assets = 'result_data_assets_' + timestamp + '.json'
    result_collection_rpc = 'result_data_rpc_' + timestamp + '.json'
    result_collection_rest = 'result_data_rest_' + timestamp + '.json'
    result_collection_grpc = 'result_data_grpc_' + timestamp + '.json'
# ======================================================================================================================
    report_rpc_link = 'rpc_links_report.json'
    report_rest_link = 'rest_links_report.json'
    report_grpc_link = 'grpc_links_report.json'
# ======================================================================================================================
    filename_cosmos_data = 'cosmos_data_list.json'
    filename_chain_data_to_create = 'chain_data_list.json'
    filename_chain_keplr_data_to_create = 'chain_keplr_data_list.json'
    filename_assets_data_to_create = 'assets_data_list.json'
    filename_rpc_link_to_create = 'rpc_links_report.json'
    filename_rest_link_to_create = 'rest_links_report.json'
    filename_grpc_link_to_create = 'grpc_links_report.json'
    project_file_ledger_client = 'ledger_clients.py'
# ======================================================================================================================
    filename_db_crypto_managements = 'cosmos_crypto.kdbx'
    filename_key_crypto_managements = 'crypto_key'
    filename_google_api = 'gacc.json'
    group_keepass = 'crypto_management'
    title_keepass = 'creds'
    mnemonic_name = 'mnemonic'
    mnemonic_1_keepass = mnemonic_name + SuffixFileName.suffix_wallet_1
# ======================================================================================================================
    filename_dict_chain_id = 'list_chain_id.json'
    filename_wallets_list = 'wallets_list.py'
    filename_temp_address_book = 'temp_address_book.json'
    filename_address_book = 'address_book.json'
    filename_ledger_client_mapping = 'ledger_client_mapping.json'
    filename_ledger_clients = 'create_ledger_clients.py'
    filename_chain_list = 'config_list.py'
# ======================================================================================================================
    filename_denoms_book = 'denoms_book.json'
    filename_pools_book = 'pools_book.json'
    filename_transaction_log = 'transactions.log'
    file_name_status_signal = 'signal_status.json'
    file_name_last_period = 'last_period.json'
    file_name_log_signal = 'log_signal.log'
# ======================================================================================================================
    file_name_binance_ohlc_db = 'binance_ohlc.db'
    file_name_log_dwl_binance = 'log_dwl_data_binance.log'
