#!/usr/bin/env python3
"""CLI for KeePass secret vault (~/.market_ai_secrets/<project>/)."""
import argparse
import getpass
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from chain.wallets.secret_vault import (  # noqa: E402
    VaultError,
    create_vault,
    get_mnemonic,
    get_status,
    lock,
    set_mnemonic,
    unlock,
)
from config.config_path import ConfigPath  # noqa: E402


def _cmd_status(_args):
    status = get_status()
    print(f'Secrets directory: {status.secrets_dir}')
    print(f'  wallet.kdbx:       {"yes" if status.database_exists else "no"}')
    print(f'  master.password:   {"yes" if status.password_file_exists else "no"}')
    print(f'  wallet.key:        {"yes" if status.keyfile_exists else "no"}')
    print(f'  vault.meta.json:   {"yes" if status.meta_exists else "no"}')
    print(f'  Unlock files ready: {"yes" if status.unlock_files_ready else "no"}')
    print(f'  Session unlocked:  {"yes" if status.is_unlocked else "no"}')
    print(f'Source data:         {ConfigPath.source_path}')


def _cmd_init(args):
    mnemonic = args.mnemonic or getpass.getpass('Mnemonic (hidden): ')
    confirm = getpass.getpass('Confirm mnemonic (hidden): ')
    if mnemonic.strip() != confirm.strip():
        raise VaultError('Mnemonic confirmation does not match.')

    master = args.master_password or getpass.getpass('Master password (hidden): ')
    confirm_master = getpass.getpass('Confirm master password (hidden): ')
    if master != confirm_master:
        raise VaultError('Master password confirmation does not match.')

    status = create_vault(
        mnemonic,
        master,
        write_password_file=not args.no_password_file,
        overwrite=args.force,
    )
    print(f'Vault created under {status.secrets_dir}')
    print('Files: wallet.kdbx, wallet.key', end='')
    print(', master.password' if not args.no_password_file else '')
    print('Copy master.password and wallet.key to USB; you may delete them locally when idle.')


def _cmd_unlock(_args):
    unlock()
    print('Vault unlocked for this process.')


def _cmd_lock(_args):
    lock()
    print('Vault locked.')


def _cmd_show(args):
    unlock()
    value = get_mnemonic()
    if args.full:
        print(value)
    else:
        words = value.split()
        print(f'Mnemonic: {len(words)} words, starts with "{words[0]} … {words[1]}"')


def _cmd_set(args):
    unlock()
    mnemonic = args.mnemonic or getpass.getpass('New mnemonic (hidden): ')
    confirm = getpass.getpass('Confirm mnemonic (hidden): ')
    if mnemonic.strip() != confirm.strip():
        raise VaultError('Mnemonic confirmation does not match.')
    set_mnemonic(mnemonic)
    print('Mnemonic updated in vault.')


def main():
    parser = argparse.ArgumentParser(description='Manage Cosmos project KeePass vault')
    sub = parser.add_subparsers(dest='command', required=True)

    sub.add_parser('status', help='Show vault file status').set_defaults(func=_cmd_status)

    init_p = sub.add_parser('init', help='Create vault, key file, and database')
    init_p.add_argument('--mnemonic', help='BIP39 mnemonic (otherwise prompted)')
    init_p.add_argument('--master-password', help='KeePass master password (otherwise prompted)')
    init_p.add_argument(
        '--no-password-file',
        action='store_true',
        help='Do not write master.password (enter manually each unlock)',
    )
    init_p.add_argument('--force', action='store_true', help='Overwrite existing vault')
    init_p.set_defaults(func=_cmd_init)

    sub.add_parser('unlock', help='Unlock vault in this process').set_defaults(func=_cmd_unlock)
    sub.add_parser('lock', help='Clear unlocked session').set_defaults(func=_cmd_lock)

    show_p = sub.add_parser('show', help='Show mnemonic summary or full with --full')
    show_p.add_argument('--full', action='store_true', help='Print full mnemonic (dangerous)')
    show_p.set_defaults(func=_cmd_show)

    set_p = sub.add_parser('set', help='Update mnemonic in vault')
    set_p.add_argument('--mnemonic', help='New mnemonic (otherwise prompted)')
    set_p.set_defaults(func=_cmd_set)

    args = parser.parse_args()
    try:
        args.func(args)
    except VaultError as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
