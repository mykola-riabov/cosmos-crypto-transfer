import json
import os
from collections import defaultdict

from config.config_path import ConfigPath
from config.config_path_files import PathFileName
from project_utils.ibc_route_builder import build_routes_for_enabled, merge_route_lists


def _manual_routes_path() -> str:
    return os.path.join(ConfigPath.root_config_path, 'ibc_routes.json')


def _generated_routes_path() -> str:
    return PathFileName().generated_ibc_routes


def load_manual_ibc_routes() -> list:
    path = _manual_routes_path()
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)['routes']


def load_generated_ibc_routes() -> list:
    path = _generated_routes_path()
    if not os.path.isfile(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    routes = data.get('routes')
    return routes if isinstance(routes, list) else []


def save_generated_ibc_routes(routes: list) -> str:
    path = _generated_routes_path()
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    payload = {'routes': routes}
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2)
    return path


def sync_generated_routes_for_enabled(enabled) -> list:
    """Rebuild generated_ibc_routes.json for enabled network pairs from chain-registry _IBC."""
    routes = build_routes_for_enabled(enabled)
    save_generated_ibc_routes(routes)
    return routes


def load_ibc_routes():
    manual = load_manual_ibc_routes()
    generated = load_generated_ibc_routes()
    return merge_route_lists(manual, generated)


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


def filter_routes_by_enabled(grouped, enabled):
    """Keep routes whose source and destination are both in *enabled*."""
    enabled_set = set(enabled)
    filtered = {}
    for source, routes in grouped.items():
        if source not in enabled_set:
            continue
        kept = [r for r in routes if r['destination_network'] in enabled_set]
        if kept:
            filtered[source] = kept
    return filtered
