class ListData:
    keys_to_extract_chain_data = ['chain_name', 'status', 'chain_id', 'network_type', 'bech32_prefix',
                                  'denom', 'average_gas_price', 'low_gas_price', 'high_gas_price',
                                  'fixed_min_gas_price', 'apis']
    keys_to_extract_chain_keplr_data = ['chainId', 'rest']
    keys_to_extract_link_data = ['chain_name', 'apis']
    keys_to_extract_assets_data = ['chain_name', 'denom_units']
    modules_list = [
        'cosmpy', 'grpcio==1.51.1', 'protobuf', 'pykeepass',
        'colorama', 'tabulate', 'schedule', 'termcolor',
        'urwid', 'google', 'oauth2client', 'cosmospy-protobuf'
    ]
    chain_list_work = [
        'kava', 'axelar', 'osmosis', 'cosmoshub', 'kujira', 'crescent',
        'fetchhub', 'secretnetwork', 'juno', 'comdex', 'injective',
        'mars', 'irisnet', 'gravitybridge'
    ]
    chain_id_list = ['axelar-dojo-1', 'comdex-1', 'cosmoshub-4', 'crescent-1',
                     'evmos_9001-2', 'gravity-bridge-3', 'injective-1', 'irishub-1',
                     'juno-1', 'kava_2222-10', 'kaiyo-1', 'mars-1', 'osmosis-1', 'secret-4','fetchhub-4']
    exclude_dir = ['chain-registry',
                   'keplr-chain-registry']
    key1_chain = 'chain_name'
    key2_chain = 'chain_id'
    display_values = ['osmo', 'iris', 'graviton', 'fet', 'scrt', 'luna', 'akt', 'cmst',
                      'atom', 'bld', 'wynd', 'juno', 'iov', 'mars', 'kava', 'arusd', 'axlbusd',
                      'inj', 'gweth', 'umee', 'evmos', 'gusdt', 'axlusdt', 'axl', 'ist', 'dvpn',
                      'stars', 'somm', 'gusdc', 'xprt', 'xki', 'huahua', 'grdn', 'kuji', 'acre',
                      'ust', 'hope', 'axlusdc', 'hopers', 'axlweth', 'cmdx', 'dsm', 'whale',
                      'boot', 'ion', 'flix', 'strd', 'lum', 'axlwbtc']

    token_list = ['GRAV', 'IRIS', 'OSMO', 'FET', 'LUNC',
                  'ATOM', 'JUNO', 'USTC', 'SCRT', 'LUNA',
                  'AKT', 'IOV', 'MARS', 'KAVA', 'BLD',
                  'WYND', 'INJ', 'UMEE', 'EVMOS', 'DVPN',
                  'NETA', 'PLQ', 'STARS', 'SOMM', 'XPRT',
                  'XKI', 'HUAHUA', 'KUJI', 'HOPE', 'HOPERS',
                  'CMDX', 'DSM', 'WHALE', 'CRO', 'BTSG',
                  'BAND', 'MNTL', 'BCNA']
                  
    group1_color = ['osmo', 'iris', 'graviton', 'fet']
    group2_color = ['cmst', 'arusd', 'axlbusd', 'gusdt', 'axlusdt', 'ist', 'gusdc', 'axlusdc']
    wallet_name_list = ['wallet_1_osmosis', 'wallet_1_irisnet',
                        'wallet_1_gravitybridge', 'wallet_1_crescent',
                        'wallet_1_axelar', 'wallet_1_fetchhub',
                        'wallet_1_cosmoshub', 'wallet_1_juno'
                        ]
