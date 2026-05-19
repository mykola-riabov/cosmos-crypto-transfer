#!/usr/bin/env python3
"""
Unified CLI — use on servers without a display (SSH, cron, automation).

Examples:
  python cosmos_cli.py status
  python cosmos_cli.py setup pipeline
  python cosmos_cli.py networks list
  python cosmos_cli.py balances
  python cosmos_cli.py transfer preview -s osmosis -d cosmoshub --symbol osmo --amount 0.01
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from project_utils.logging_setup import setup_logging


def _cmd_status(_args) -> int:
    from gui import services

    s = services.get_setup_status()
    lines = [
        ('source_dir', s.source_dir),
        ('secret_vault', s.secret_vault),
        ('unlock_files', s.secret_unlock_files),
        ('cosmos_data', s.cosmos_data),
        ('ledger_clients', s.ledger_clients),
        ('wallets_list', s.wallets_list),
        ('address_book', s.address_book),
        ('client_mapping', s.client_mapping),
        ('ready_for_transfer', s.ready_for_transfer),
        ('secrets_path', s.secrets_path),
    ]
    if _args.json:
        print(json.dumps(dict(lines), indent=2))
    else:
        for key, val in lines:
            print(f'{key}: {val}')
    return 0


def _cmd_setup(args) -> int:
    from gui import services
    from gui.setup_catalog import FIRST_RUN_PIPELINE, SETUP_ACTIONS

    if args.action == 'pipeline':
        lt = args.link_type or services.get_ledger_link_type()
        log = services.run_first_run_pipeline(link_type=lt)
        print(log)
        return 0

    if args.action == 'list':
        for a in SETUP_ACTIONS:
            mark = '*' if a.in_first_run else ' '
            print(f'{mark} {a.id:16} {a.title}')
        print('\n* = included in: setup pipeline')
        return 0

    if args.action not in {a.id for a in SETUP_ACTIONS}:
        print(f'Unknown setup action: {args.action}', file=sys.stderr)
        print('Use: cosmos_cli.py setup list', file=sys.stderr)
        return 2

    lt = args.link_type if args.action == 'ledger_clients' else None
    print(services.run_setup_action(args.action, link_type=lt))
    return 0


def _cmd_networks(args) -> int:
    from project_utils.networks_manager import (
        DEFAULT_ENABLED_NETWORKS,
        get_enabled_networks,
        network_rows,
        reset_enabled_to_defaults,
        set_enabled_networks,
        test_all_network_health,
        update_health_cache,
        probe_all_chains,
        load_all_chains,
    )

    if args.networks_cmd == 'list':
        rows = network_rows()
        if args.json:
            print(json.dumps(rows, indent=2))
            return 0
        for r in rows:
            use = 'Y' if r['enabled'] else ' '
            print(f"[{use}] {r['chain_name']:20} {r['chain_id']:22} {r['status']:12} {r['rest'][:50]}")
        return 0

    if args.networks_cmd == 'enabled':
        enabled = sorted(get_enabled_networks())
        if args.json:
            print(json.dumps(enabled, indent=2))
        else:
            print(', '.join(enabled) if enabled else '(none)')
        return 0

    if args.networks_cmd == 'defaults':
        reset_enabled_to_defaults()
        print('Enabled networks reset to:', ', '.join(DEFAULT_ENABLED_NETWORKS))
        return 0

    if args.networks_cmd == 'enable':
        names = args.names or list(DEFAULT_ENABLED_NETWORKS)
        set_enabled_networks(names)
        print('Saved enabled networks:', ', '.join(sorted(names)))
        return 0

    if args.networks_cmd == 'test':
        if args.json:
            chains = load_all_chains()
            results = probe_all_chains(chains)
            update_health_cache(results)
            print(json.dumps(results, indent=2))
        else:
            print(test_all_network_health())
        return 0

    return 2


def _cmd_balances(args) -> int:
    from gui import services
    from project_utils.token_catalog import get_token_catalog

    rows, missed = services.fetch_balances()
    catalog = get_token_catalog()

    if args.json:
        out = []
        for r in rows:
            out.append(
                {
                    'wallet': r.wallet_name,
                    'network': r.network,
                    'symbol': catalog.label_for_denom(r.network, r.denom) if r.denom else '',
                    'denom': r.denom,
                    'amount_raw': r.amount,
                    'amount': services.format_balance_display(r.network, r.denom, r.amount)
                    if r.denom and not r.error
                    else r.amount,
                    'error': r.error,
                }
            )
        print(json.dumps({'balances': out, 'missed_clients': missed}, indent=2))
        return 0

    from tabulate import tabulate

    table = []
    for r in rows:
        if r.error:
            table.append([r.network, r.wallet_name, '', '', r.error])
        elif r.denom == '(empty)':
            table.append([r.network, r.wallet_name, '—', '0', ''])
        else:
            sym = catalog.label_for_denom(r.network, r.denom)
            amt = services.format_balance_display(r.network, r.denom, r.amount)
            table.append([r.network, r.wallet_name, sym, amt, ''])
    print(tabulate(table, headers=['Network', 'Wallet', 'Token', 'Amount', 'Error'], tablefmt='simple'))
    if missed:
        print('\nNo client for:', ', '.join(missed))
    return 0


def _cmd_transfer(args) -> int:
    from gui import services

    route = services.ibc_route_for(args.source, args.dest)
    if route is None:
        print(f'No IBC route: {args.source} → {args.dest}', file=sys.stderr)
        return 2

    if args.transfer_cmd == 'routes':
        grouped = services.ibc_routes_grouped()
        if args.json:
            print(json.dumps(grouped, indent=2, default=str))
            return 0
        for src, routes in sorted(grouped.items()):
            for r in routes:
                print(f"{src} → {r['destination_network']}  channel={r['channel']}")
        return 0

    preview = services.gui_prepare_transfer(route, args.symbol, args.amount)
    if args.transfer_cmd == 'preview':
        if args.json:
            print(
                json.dumps(
                    {
                        'summary': preview.summary_lines(),
                        'amount_token': preview.amount_token,
                        'amount_raw': preview.amount_raw,
                    },
                    indent=2,
                )
            )
        else:
            print('\n'.join(preview.summary_lines()))
        return 0

    if args.transfer_cmd == 'send':
        if not args.yes:
            print('Refusing to broadcast without --yes', file=sys.stderr)
            print('Run preview first, then send with --yes', file=sys.stderr)
            return 2
        tx_hash = services.gui_broadcast_transfer(route, preview)
        print(tx_hash)
        return 0

    return 2


def _cmd_tokens(args) -> int:
    from gui import services

    if args.tokens_cmd == 'symbols':
        symbols = services.symbols_for_transfer_network(args.network or '')
        if args.json:
            print(json.dumps(symbols, indent=2))
        else:
            for s in symbols:
                print(s)
        return 0

    rows, meta = services.fetch_registry_token_rows(
        chain_name=None if args.network == 'all' else args.network,
        search=args.search,
        with_prices=not args.no_prices,
    )
    if args.json:
        print(json.dumps({'meta': meta, 'tokens': rows[: args.limit]}, indent=2, default=str))
        return 0
    from tabulate import tabulate

    table = []
    for r in rows[: args.limit]:
        table.append(
            [
                r.get('chain_name', ''),
                r.get('symbol', ''),
                r.get('denom', ''),
                r.get('decimals', ''),
                r.get('price', ''),
            ]
        )
    print(tabulate(table, headers=['Network', 'Symbol', 'Denom', 'Dec', 'Price'], tablefmt='simple'))
    print(f"\nShown {min(len(rows), args.limit)} of {meta.get('total', len(rows))} tokens")
    return 0


def _cmd_menu(_args) -> int:
    from menu.main_menu import main_menu

    main_menu()
    return 0


def _cmd_secrets(argv: Optional[List[str]]) -> int:
    from secrets_cli import main as secrets_main

    old = sys.argv
    sys.argv = ['secrets_cli'] + (argv or ['status'])
    try:
        secrets_main()
    finally:
        sys.argv = old
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='cosmos_cli',
        description='Cosmos Crypto Transfer — desktop GUI + headless terminal CLI',
    )
    parser.add_argument('--json', action='store_true', help='Machine-readable JSON output')
    sub = parser.add_subparsers(dest='command', required=True)

    p_status = sub.add_parser('status', help='Environment and file readiness')
    p_status.set_defaults(func=_cmd_status)

    p_setup = sub.add_parser('setup', help='Setup steps (same as GUI Setup tab)')
    p_setup.add_argument(
        'action',
        nargs='?',
        default='list',
        help='Step id, pipeline, or list (default: list)',
    )
    p_setup.add_argument(
        '--link-type',
        default=None,
        choices=['keplr_rest_link', 'rest_link'],
        help='REST field for ledger client generation',
    )
    p_setup.set_defaults(func=_cmd_setup)

    p_net = sub.add_parser('networks', help='Manage enabled networks')
    p_net.add_argument(
        'networks_cmd',
        choices=['list', 'enabled', 'enable', 'defaults', 'test'],
        help='Subcommand',
    )
    p_net.add_argument('names', nargs='*', help='Chain names for enable')
    p_net.set_defaults(func=_cmd_networks)

    p_bal = sub.add_parser('balances', help='Balances for enabled networks')
    p_bal.set_defaults(func=_cmd_balances)

    p_tr = sub.add_parser('transfer', help='IBC transfer')
    p_tr.add_argument(
        'transfer_cmd',
        choices=['routes', 'preview', 'send'],
        help='List routes, preview, or broadcast',
    )
    p_tr.add_argument('-s', '--source', help='Source network')
    p_tr.add_argument('-d', '--dest', help='Destination network')
    p_tr.add_argument('--symbol', help='Token symbol (denoms book / catalog)')
    p_tr.add_argument('--amount', type=float, help='Human amount')
    p_tr.add_argument('--yes', action='store_true', help='Required for send')
    p_tr.set_defaults(func=_cmd_transfer)

    p_tok = sub.add_parser('tokens', help='Token catalog')
    p_tok.add_argument('tokens_cmd', choices=['list', 'symbols'], default='list', nargs='?')
    p_tok.add_argument('-n', '--network', default='all', help='Chain name or all')
    p_tok.add_argument('--search', default='', help='Filter substring')
    p_tok.add_argument('--limit', type=int, default=50)
    p_tok.add_argument('--no-prices', action='store_true')
    p_tok.set_defaults(func=_cmd_tokens)

    p_menu = sub.add_parser('menu', help='Interactive text menu (legacy)')
    p_menu.set_defaults(func=_cmd_menu)

    p_sec = sub.add_parser('secrets', help='KeePass vault (init, unlock, status, …)')
    p_sec.add_argument('secrets_args', nargs=argparse.REMAINDER)
    p_sec.set_defaults(func=lambda a: _cmd_secrets(a.secrets_args))

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == 'transfer' and args.transfer_cmd in ('preview', 'send'):
        if not args.source or not args.dest or not args.symbol or args.amount is None:
            parser.error('transfer preview/send requires --source, --dest, --symbol, --amount')

    try:
        return args.func(args) or 0
    except KeyboardInterrupt:
        print('\nInterrupted.', file=sys.stderr)
        return 130
    except Exception as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
