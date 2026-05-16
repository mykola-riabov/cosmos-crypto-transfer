import json
from decimal import Decimal
from typing import Dict, Optional, Tuple


def load_denoms_index(path: str) -> Dict[Tuple[str, str], dict]:
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    index = {}
    for item in data:
        key = (item['symbol'].lower(), item['network'].lower())
        index[key] = item
    return index


def resolve_denom(
    index: Dict[Tuple[str, str], dict],
    symbol: str,
    network: str,
) -> Tuple[str, int]:
    item = index.get((symbol.lower(), network.lower()))
    if item is None:
        raise ValueError(f'Symbol and network pair not found in denoms book: {symbol!r} on {network!r}')
    denom = item.get('denom_contract')
    decimal = item.get('decimal')
    if denom is None or decimal is None:
        raise ValueError(f'Incomplete denom entry for {symbol!r} on {network!r}')
    return denom, int(decimal)


def convert_amount(amount: float, decimals: int) -> int:
    scaled = Decimal(str(amount)) * (Decimal(10) ** decimals)
    return int(scaled)
