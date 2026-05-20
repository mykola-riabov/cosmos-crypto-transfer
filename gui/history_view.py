"""History tab: column specs, filters, row formatting."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Callable, Dict, List, Optional, Sequence, Set

# id, title, width, stretch, value builder
ColumnSpec = tuple[str, str, int, bool, Callable[[dict], str]]

HISTORY_COLUMN_IDS: List[str] = [
    'time',
    'status',
    'route',
    'source',
    'destination',
    'symbol',
    'amount',
    'gas',
    'channel',
    'timeout',
    'tx_hash',
    'error',
    'sender',
    'receiver',
]

KNOWN_STATUSES: List[str] = ['success', 'failed', 'submitted', 'preview']


def _timeout_display(row: dict) -> str:
    mode = row.get('timeout_mode', 'time')
    tval = row.get('timeout_value', '')
    return row.get('timeout_display') or (f'{tval}s' if mode == 'time' else f'+{tval} blk')


def _route_display(row: dict) -> str:
    return f'{row.get("source", "")} → {row.get("destination", "")}'


def column_specs() -> List[ColumnSpec]:
    return [
        ('time', 'Time (UTC)', 150, False, lambda r: r.get('time', '')),
        ('status', 'Status', 72, False, lambda r: r.get('status', '')),
        ('route', 'Route', 130, False, _route_display),
        ('source', 'Source', 100, False, lambda r: r.get('source', '')),
        ('destination', 'Destination', 100, False, lambda r: r.get('destination', '')),
        ('symbol', 'Token', 56, False, lambda r: r.get('symbol', '')),
        ('amount', 'Amount', 72, False, lambda r: r.get('amount', '')),
        ('gas', 'Gas', 64, False, lambda r: str(r.get('gas', ''))),
        ('channel', 'Channel', 100, False, lambda r: r.get('channel', '')),
        ('timeout', 'Timeout', 100, False, _timeout_display),
        ('tx_hash', 'Tx hash', 280, False, lambda r: r.get('tx_hash', '')),
        ('error', 'Error', 220, False, lambda r: (r.get('error', '') or '')[:400]),
        ('sender', 'Sender', 120, False, lambda r: r.get('sender_address', '')),
        ('receiver', 'Receiver', 120, False, lambda r: r.get('receiver_address', '')),
    ]


def default_visible_columns() -> List[str]:
    return list(HISTORY_COLUMN_IDS)


def default_status_filter() -> List[str]:
    return list(KNOWN_STATUSES)


def parse_history_timestamp(value: str) -> Optional[datetime]:
    text = (value or '').strip()
    if not text:
        return None
    try:
        if text.endswith('Z'):
            text = text[:-1] + '+00:00'
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def parse_filter_date(text: str) -> Optional[date]:
    text = (text or '').strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError(f'Invalid date “{text}”. Use YYYY-MM-DD.')


def filter_tx_history(
    rows: List[dict],
    *,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    statuses: Optional[Set[str]] = None,
) -> List[dict]:
    out: List[dict] = []
    for row in rows:
        if statuses is not None:
            if not statuses:
                continue
            st = (row.get('status') or '').lower()
            if st not in statuses:
                continue
        ts = parse_history_timestamp(row.get('time', ''))
        if date_from is not None or date_to is not None:
            if ts is None:
                continue
            row_day = ts.astimezone(timezone.utc).date()
            if date_from is not None and row_day < date_from:
                continue
            if date_to is not None and row_day > date_to:
                continue
        out.append(row)
    return out


def row_values(row: dict, column_ids: Sequence[str] | None = None) -> tuple:
    """One value per Treeview column id, in column order.

    Must include hidden columns too: displaycolumns only hides headers;
    values are still indexed by the full ``columns`` list.
    """
    cols = list(column_ids) if column_ids is not None else list(HISTORY_COLUMN_IDS)
    by_id = {spec[0]: spec[4](row) for spec in column_specs()}
    return tuple(by_id.get(col, '') for col in cols)


def status_tag(status: str) -> tuple:
    st = (status or '').lower()
    if st == 'success':
        return ('success',)
    if st == 'failed':
        return ('failed',)
    return ('pending',)
