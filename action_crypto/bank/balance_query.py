import json
import time
from dataclasses import dataclass
from typing import List, Optional

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
        except (requests.exceptions.HTTPError, RuntimeError) as exc:
            rows.append(BalanceRow(wallet_name, network, address, '', '', error=str(exc)))
        time.sleep(sleep_seconds)

    return rows, sorted(set(missed_clients))
