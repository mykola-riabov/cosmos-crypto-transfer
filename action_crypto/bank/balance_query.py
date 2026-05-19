import json
import time
from dataclasses import dataclass
from typing import List, Optional, Set

import requests

from project_utils.chain_resources import build_client_map


@dataclass
class BalanceRow:
    wallet_name: str
    network: str
    address: str
    denom: str
    amount: str
    error: Optional[str] = None


def query_all_balances(
    filepath_mapping: str,
    filepath_address_book: str,
    sleep_seconds: float = 0.5,
    networks: Optional[Set[str]] = None,
) -> tuple[List[BalanceRow], List[str]]:
    rows: List[BalanceRow] = []
    missed_clients: List[str] = []

    with open(filepath_mapping, 'r', encoding='utf-8') as f1, open(filepath_address_book, 'r', encoding='utf-8') as f2:
        mapping_data = json.load(f1)
        address_data = json.load(f2)

    try:
        clients, missed_from_map = build_client_map(mapping_data)
    except (ModuleNotFoundError, AttributeError) as exc:
        raise RuntimeError(f'Error loading ledger clients: {exc}') from exc

    missed_clients.extend(missed_from_map)

    for addr in address_data:
        network = addr['network']
        if networks is not None and network not in networks:
            continue
        wallet_name = addr['name']
        address = addr.get('address')
        if network not in clients:
            if network not in missed_clients:
                missed_clients.append(network)
            continue
        if not address:
            rows.append(BalanceRow(wallet_name, network, '', '', error='missing address'))
            continue
        client = clients[network]
        try:
            balance = client.query_bank_all_balances(address)
            if not balance:
                rows.append(BalanceRow(wallet_name, network, address, '(empty)', '0'))
            for coin in balance:
                rows.append(BalanceRow(wallet_name, network, address, coin.denom, coin.amount))
        except (requests.exceptions.RequestException, OSError, RuntimeError) as exc:
            rows.append(BalanceRow(wallet_name, network, address, '', '', error=str(exc)))
        time.sleep(sleep_seconds)

    return rows, sorted(set(missed_clients))


def query_symbol_balance_on_network(
    network: str,
    symbol: str,
    filepath_mapping: str,
    filepath_address_book: str,
) -> BalanceRow:
    """Query on-chain balance for *symbol* on one network (resolved via token catalog)."""
    from project_utils.token_catalog import get_token_catalog

    network = (network or '').strip()
    symbol = (symbol or '').strip()
    if not network or not symbol:
        return BalanceRow('', network, '', '', '', error='network and symbol required')

    with open(filepath_mapping, 'r', encoding='utf-8') as f1, open(
        filepath_address_book, 'r', encoding='utf-8'
    ) as f2:
        mapping_data = json.load(f1)
        address_data = json.load(f2)

    wallet_name = ''
    address = ''
    for entry in address_data:
        if entry.get('network') == network:
            wallet_name = entry.get('name', '')
            address = entry.get('address', '')
            break

    if not address:
        return BalanceRow(wallet_name, network, '', '', '', error=f'no address for {network} in address book')

    try:
        clients, _missed = build_client_map(mapping_data)
    except (ModuleNotFoundError, AttributeError) as exc:
        return BalanceRow(wallet_name, network, address, '', '', error=str(exc))

    if network not in clients:
        return BalanceRow(wallet_name, network, address, '', '', error=f'no ledger client for {network}')

    catalog = get_token_catalog()
    try:
        target_denom, _decimals = catalog.resolve_denom(network, symbol)
    except ValueError as exc:
        return BalanceRow(wallet_name, network, address, '', '', error=str(exc))

    client = clients[network]
    try:
        coins = client.query_bank_all_balances(address)
    except (requests.exceptions.RequestException, OSError, RuntimeError) as exc:
        return BalanceRow(wallet_name, network, address, '', '', error=str(exc))

    if not coins:
        return BalanceRow(wallet_name, network, address, target_denom, '0')

    sym_lower = symbol.lower()
    for coin in coins:
        if coin.denom == target_denom:
            return BalanceRow(wallet_name, network, address, coin.denom, coin.amount)
        if catalog.label_for_denom(network, coin.denom).lower() == sym_lower:
            return BalanceRow(wallet_name, network, address, coin.denom, coin.amount)

    return BalanceRow(wallet_name, network, address, target_denom, '0')
