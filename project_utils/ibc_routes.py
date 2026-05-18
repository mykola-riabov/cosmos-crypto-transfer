import json
import os
from collections import defaultdict

from config.config_path import ConfigPath


def load_ibc_routes():
    path = os.path.join(ConfigPath.root_config_path, 'ibc_routes.json')
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)['routes']


def routes_by_source(routes=None):
    routes = routes or load_ibc_routes()
    grouped = defaultdict(list)
    for route in routes:
        grouped[route['source_network']].append(route)
    return dict(sorted(grouped.items()))


def find_route(source_network, destination_network, routes=None):
    routes = routes or load_ibc_routes()
    for route in routes:
        if route['source_network'] == source_network and route['destination_network'] == destination_network:
            return route
    return None
