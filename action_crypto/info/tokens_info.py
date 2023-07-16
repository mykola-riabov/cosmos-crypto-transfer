import os
import json
import requests
import signal
import time
from tabulate import tabulate


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
