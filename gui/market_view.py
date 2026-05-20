"""Market tab: column ids, titles, row values (full tuple for Treeview)."""

from __future__ import annotations

from typing import Dict, List, Tuple

from gui.market_colors import format_signed_change

# Treeview column order must match `values` tuple order.
MARKET_COLUMN_IDS: Tuple[str, ...] = (
    'symbol',
    'denom',
    'price',
    'liquidity',
    'volume',
    'chg24',
    'chg7',
)

MARKET_COLUMN_TITLES: Dict[str, str] = {
    'symbol': 'Symbol',
    'denom': 'Denom',
    'price': 'Price',
    'liquidity': 'Liquidity',
    'volume': 'Vol 24h',
    'chg24': '24h %',
    'chg7': '7d %',
}

# id, width, stretch
MARKET_COLUMN_LAYOUT: Tuple[Tuple[str, int, bool], ...] = (
    ('symbol', 72, False),
    ('denom', 120, False),
    ('price', 88, False),
    ('liquidity', 100, False),
    ('volume', 100, False),
    ('chg24', 72, False),
    ('chg7', 72, False),
)


def default_market_visible_columns() -> List[str]:
    return list(MARKET_COLUMN_IDS)


def default_market_column_widths() -> Dict[str, int]:
    return {col_id: width for col_id, width, _stretch in MARKET_COLUMN_LAYOUT}


def normalize_visible_columns(saved) -> List[str]:
    if not isinstance(saved, list) or not saved:
        return default_market_visible_columns()
    out = [c for c in saved if c in MARKET_COLUMN_IDS]
    return out if out else default_market_visible_columns()


def normalize_column_widths(saved) -> Dict[str, int]:
    defaults = default_market_column_widths()
    if not isinstance(saved, dict):
        return defaults
    out = dict(defaults)
    for col_id in MARKET_COLUMN_IDS:
        if col_id not in saved:
            continue
        try:
            out[col_id] = max(40, min(800, int(saved[col_id])))
        except (TypeError, ValueError):
            pass
    return out


def normalize_sort_column(column: str) -> str:
    return column if column in MARKET_COLUMN_IDS else 'volume'


def market_row_display_values(row: dict) -> Tuple:
    """One value per MARKET_COLUMN_IDS entry (for Treeview `values`)."""
    return (
        row.get('symbol', ''),
        row.get('denom', ''),
        row.get('price', ''),
        row.get('_liquidity_fmt', ''),
        row.get('_volume_fmt', ''),
        format_signed_change(row.get('price_24h_change')),
        format_signed_change(row.get('price_7d_change')),
    )
