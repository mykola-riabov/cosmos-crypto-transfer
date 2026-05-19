"""Setup step metadata, first-run pipeline, and existing-config warnings."""
import os
from dataclasses import dataclass
from typing import List, Optional

from chain.wallets.get_creds import mnemonic_is_configured
from chain.wallets.secret_vault import get_status as vault_get_status
from config.config_path import ConfigPath
from config.config_path_files import PathFileName

FIRST_RUN_PIPELINE = (
    'source',
    'modules',
    'collect_json',
    'ledger_clients',
    'wallets',
    'address_book',
)


@dataclass(frozen=True)
class SetupActionDef:
    id: str
    title: str
    description: str
    in_first_run: bool = False


SETUP_ACTIONS: tuple[SetupActionDef, ...] = (
    SetupActionDef(
        'source',
        '1. Create source and chain registries',
        'Creates ./source inside the project (data, temp, chain-registry clones). '
        'Required before any other setup step.',
        in_first_run=True,
    ),
    SetupActionDef(
        'modules',
        '2. Install Python dependencies',
        'Installs packages from requirements.txt (cosmpy, pykeepass, requests, etc.).',
        in_first_run=True,
    ),
    SetupActionDef(
        'collect_json',
        '3. Collect chain-registry JSON (networks + tokens)',
        'Scans all chains from chain-registry (list_chain_id.json). Creates cosmos_data_list.json '
        '(networks) and assets_registry.json (tokens from assetlist.json). REST URLs come from '
        'registry without live probe — use Networks → Test all to verify endpoints.',
        in_first_run=True,
    ),
    SetupActionDef(
        'ledger_clients',
        '4. Generate ledger_clients.py',
        'Creates chain/clients/ledger_clients.py and client mapping for cosmpy.',
        in_first_run=True,
    ),
    SetupActionDef(
        'wallets',
        '5. Generate wallets_list.py',
        'Creates chain/wallets/wallets_list.py (lazy load; mnemonic read from vault when used).',
        in_first_run=True,
    ),
    SetupActionDef(
        'address_book',
        '6. Generate address_book.json',
        'Derives addresses from the vault mnemonic into source/data/address_book.json. '
        'Requires vault unlock files (master.password + wallet.key) on disk.',
        in_first_run=True,
    ),
    SetupActionDef(
        'pythonpath',
        'PYTHONPATH hint',
        'Shows how to run the project from the repo root.',
        in_first_run=False,
    ),
    SetupActionDef(
        'apps',
        'Check system applications',
        'Verifies git, pip3, tree, and curl.',
        in_first_run=False,
    ),
    SetupActionDef(
        'all_checks',
        'Run all environment checks',
        'Platform, source, PYTHONPATH, applications, and Python modules.',
        in_first_run=False,
    ),
)


def get_setup_action(action_id: str) -> Optional[SetupActionDef]:
    for action in SETUP_ACTIONS:
        if action.id == action_id:
            return action
    return None


def _wallet_has_real_mnemonic() -> bool:
    return mnemonic_is_configured()


def _vault_ready_for_address_book() -> bool:
    status = vault_get_status()
    if not status.vault_initialized:
        return False
    return status.unlock_files_ready or status.is_unlocked


def get_action_warnings(action_id: str) -> List[str]:
    paths = PathFileName()
    path = ConfigPath()
    warnings: List[str] = []
    vault = vault_get_status()

    if action_id == 'source':
        if os.path.isdir(path.source_path):
            warnings.append(f'Source directory already exists: {path.source_path}')
        if os.path.isdir(path.chain_registry_path):
            warnings.append('chain-registry is already cloned (git pull will run).')

    elif action_id == 'collect_json':
        if os.path.isfile(paths.data_cosmos_file_name):
            warnings.append(f'File already exists: {paths.data_cosmos_file_name} (will be rebuilt).')

    elif action_id == 'ledger_clients':
        if os.path.isfile(paths.ledger_clients):
            warnings.append('ledger_clients.py already exists (will be overwritten).')
        if os.path.isfile(paths.ledger_client_mapping):
            warnings.append('Client mapping file already exists (will be overwritten).')

    elif action_id == 'wallets':
        if os.path.isfile(paths.wallets_list_path):
            warnings.append('wallets_list.py already exists (will be overwritten).')
        if not vault.vault_initialized:
            warnings.append(
                f'KeePass vault not found under {vault.secrets_dir} — create it first (Secret vault button).'
            )

    elif action_id == 'address_book':
        if os.path.isfile(paths.address_book):
            warnings.append('address_book.json already exists (will be rebuilt).')
        if not vault.vault_initialized:
            warnings.append('Secret vault not initialized.')
        elif not _vault_ready_for_address_book():
            warnings.append(
                'Vault unlock files missing. Copy master.password and wallet.key from USB to the secrets folder.'
            )
        if not os.path.isfile(paths.wallets_list_path):
            warnings.append('wallets_list.py not found — generate wallets first.')

    return warnings


def _environment_ready() -> bool:
    paths = PathFileName()
    vault = vault_get_status()
    return all(
        (
            vault.vault_initialized,
            os.path.isfile(paths.ledger_clients),
            os.path.isfile(paths.wallets_list_path),
            os.path.isfile(paths.address_book),
            os.path.isfile(paths.ledger_client_mapping),
        )
    )


def get_first_run_warnings() -> List[str]:
    seen = set()
    combined: List[str] = []
    vault = vault_get_status()

    if not vault.vault_initialized:
        combined.append(
            f'KeePass vault not found in {vault.secrets_dir}. '
            'It will be created when you run first-time setup (or Secret vault button).'
        )
    elif not vault.unlock_files_ready:
        combined.append(
            'Vault exists but master.password and/or wallet.key are missing. '
            'Copy them from USB before generating the address book.'
        )

    if _environment_ready():
        combined.append(
            'Environment is already fully configured. Running again may overwrite generated files.'
        )

    for action_id in FIRST_RUN_PIPELINE:
        for msg in get_action_warnings(action_id):
            if msg not in seen:
                seen.add(msg)
                combined.append(msg)

    return combined
