import importlib
from typing import Any, Dict, Optional


def load_ledger_clients_module():
    try:
        return importlib.import_module('chain.clients.ledger_clients')
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            'chain.clients.ledger_clients not found. '
            'Run menu "Check and create data" → "Generate ledger clients".'
        ) from exc


def load_wallets_module():
    try:
        return importlib.import_module('chain.wallets.wallets_list')
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            'chain.wallets.wallets_list not found. '
            'Run menu "Check and create data" → "Generate Wallets list".'
        ) from exc


def get_network_client(ledger_module: Any, network: str) -> Any:
    attr = f'{network}_client'
    client = getattr(ledger_module, attr, None)
    if client is None:
        raise AttributeError(f'{attr} not found in ledger_clients')
    return client


def get_wallet(wallets_module: Any, wallet_attr: str) -> Any:
    from project_utils.wallet_derivation import resolve_wallet_attr

    resolved = resolve_wallet_attr(wallet_attr)
    wallet = getattr(wallets_module, resolved, None)
    if wallet is None:
        raise AttributeError(f'{resolved} not found in wallets_list (from route {wallet_attr})')
    return wallet


def build_client_map(mapping_entries: list) -> Dict[str, Any]:
    ledger_module = load_ledger_clients_module()
    clients: Dict[str, Any] = {}
    missed = []
    for entry in mapping_entries:
        network = entry['network']
        client_attr = entry.get('client', f'{network}_client')
        client = getattr(ledger_module, client_attr, None)
        if client is None:
            missed.append(network)
            continue
        clients[network] = client
    return clients, missed
