import json
import os
import signal
import time

import requests
from tabulate import tabulate


def fetch_osmosis_token_rows(
    api_url,
    display_values=None,
    sort_by='volume_24h',
    limit=None,
    timeout=45.0,
):
    response = requests.get(api_url, timeout=timeout)
    response.raise_for_status()
    data = json.loads(response.text)
    if not isinstance(data, list):
        raise ValueError('Unexpected Osmosis tokens API response')

    sort_key = {
        'volume_24h': lambda x: float(x.get('volume_24h') or 0),
        'liquidity': lambda x: float(x.get('liquidity') or 0),
        'price_7d_change': lambda x: float(x.get('price_7d_change') or 0),
    }.get(sort_by, lambda x: float(x.get('volume_24h') or 0))
    data = sorted(data, key=sort_key, reverse=True)

    rows = []
    for item in data:
        if display_values is not None and item.get('display') not in display_values:
            continue
        rows.append({
            'symbol': item.get('symbol', ''),
            'denom': item.get('denom', ''),
            'display': item.get('display', ''),
            'name': item.get('name', ''),
            'price': item.get('price', ''),
            'liquidity': item.get('liquidity', ''),
            'volume_24h': item.get('volume_24h', ''),
            'price_24h_change': item.get('price_24h_change', ''),
            'price_7d_change': item.get('price_7d_change', ''),
        })
        if limit is not None and len(rows) >= limit:
            break
    return rows


def filter_data_by_display(api_url, display_values, group1_color, group2_color, update_interval):

    def signal_handler(signal, frame):
        print('Execution terminated.')
        exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        os.system('clear')  # Use 'clear' for Linux/Unix, 'cls' for Windows
        response = requests.get(api_url)
        data = json.loads(response.text)

        # Sort data by the price_24h_change key from highest to lowest value
        data = sorted(data, key=lambda x: float(x.get('price_7d_change', 0)), reverse=True)

        table_data = []
        for item in data:
            if item.get('display') in display_values:
                row = [
                    item.get('symbol', ''),
                    item.get('price', ''),
                    '{:,.0f}'.format(item.get('liquidity', '')),
                    '{:,.0f}'.format(item.get('volume_24h', '')),
                    format(item.get('price_24h_change', '')),
                    item.get('price_7d_change', ''),
                ]

                # Determine color for price_24h_change
                price_24h_change = float(item.get('price_24h_change', 0))
                price = float(item.get('price', 0))
                if price_24h_change < 0:
                    row[4] = f'\033[91m{price_24h_change}\033[0m'  # Red color
                    row[1] = f'\033[91m{price}\033[0m'
                elif price_24h_change > 0:
                    row[4] = f'\033[92m{price_24h_change}\033[0m'  # Green color
                    row[1] = f'\033[92m{price}\033[0m'

                # Determine color for price_7d_change
                price_7d_change = float(item.get('price_7d_change', 0))
                if price_7d_change < 0:
                    row[5] = f'\033[91m{price_7d_change}\033[0m'  # Red color
                elif price_7d_change > 0:
                    row[5] = f'\033[92m{price_7d_change}\033[0m'  # Green color

                if item.get('display') in group1_color:
                    row[0] = f'\033[94m{item.get("symbol")}\033[0m'

                elif item.get('display') in group2_color:
                    row[0] = f'\033[35m{item.get("symbol")}\033[0m'

                table_data.append(row)

        headers = ['Symbol', 'Price', 'Liquidity', 'Volume 24h', 'Price 24h Change', 'Price 7d Change']
        print(tabulate(table_data, headers=headers, tablefmt='pipe', numalign='center'))
        for i in range(update_interval, 0, -1):
            print(f'Updating data... {i} seconds', end='\r')
            time.sleep(1)
        print('\033[K', end='')
