"""Portfolio / asset view helpers (Exodus-style aggregation)."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import List, Optional

from action_crypto.bank.balance_query import BalanceRow


def balance_rows_to_assets(
    rows: List[BalanceRow],
    *,
    catalog,
    usd_prices: Optional[dict] = None,
    resolve_ibc: bool = True,
    chain_rest_by_network: Optional[dict] = None,
) -> List[dict]:
    """Flatten balance rows into portfolio asset lines with symbol and optional USD."""
    assets: List[dict] = []
    usd_prices = usd_prices or {}
    chain_rest = chain_rest_by_network or {}

    for row in rows:
        if row.error or not row.denom or row.denom == '(empty)':
            continue
        network = row.network
        denom = row.denom
        if resolve_ibc and denom.lower().startswith('ibc/'):
            rest = chain_rest.get(network)
            if rest:
                catalog.ensure_ibc_denom_resolved(network, denom, rest)
        symbol = catalog.label_for_denom(network, denom)
        amount_h = catalog.format_amount(row.amount, network, denom)
        cg_id = catalog.get_coingecko_id(network, denom)

        usd_val = ''
        usd_note = usd_prices.get(cg_id) if cg_id else None
        if usd_note is not None:
            try:
                human = Decimal(amount_h.split()[0].replace(',', ''))
                usd_val = f'${float(human * Decimal(str(usd_note))):,.2f}'
            except (InvalidOperation, ValueError, IndexError):
                usd_val = ''

        assets.append(
            {
                'network': network,
                'symbol': symbol,
                'amount': amount_h,
                'denom': denom,
                'usd': usd_val,
                'wallet': row.wallet_name,
            }
        )
    assets.sort(key=lambda a: (a['network'].lower(), a['symbol'].lower()))
    return assets
