import os
from pathlib import Path


def _project_root() -> Path:
    return Path(
        os.environ.get(
            'COSMOS_PROJECT_ROOT',
            Path(__file__).resolve().parents[1],
        )
    ).resolve()


def _source_root(project_root: Path) -> Path:
    return Path(
        os.environ.get(
            'COSMOS_SOURCE_PATH',
            project_root.parent / 'source',
        )
    ).resolve()


_project = _project_root()
_source = _source_root(_project)


class ConfigPath:
    project_path = str(_project)
    source_path = str(_source)
    backup_path = str(_source.parent / 'backup')
    creds_path = str(_source / 'creds')
    data_path = str(_source / 'data')
    temp_path = str(_source / 'temp')
    assets_path = str(_source / 'temp' / 'assets')
    chain_path = str(_source / 'temp' / 'chain')
    create_path = str(_source / 'temp' / 'create')
    chain_registry_path = str(_source / 'chain-registry')
    keplr_chain_registry_path = str(_source / 'keplr-chain-registry')
    root_chain_path = str(_project / 'chain')
    root_client_path = str(_project / 'chain' / 'clients')
    root_wallet_path = str(_project / 'chain' / 'wallets')
    root_config_path = str(_project / 'config')
    root_action_crypto = str(_project / 'action_crypto')
    root_bank = str(_project / 'action_crypto' / 'bank')
    root_addresses_path = str(_project / 'addresses')
    root_denoms_path = str(_project / 'addresses' / 'denoms')
    root_pools_path = str(_project / 'addresses' / 'pools')
    data_api_path = str(_source / 'temp' / 'data_api')
    logs_path = str(_source / 'temp' / 'logs')
