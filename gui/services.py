import io
import json
import os
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass
from typing import Callable, Iterable, List, Optional

from action_crypto.bank.balance_query import query_all_balances, query_symbol_balance_on_network
from action_crypto.info.tokens_info import fetch_osmosis_token_rows
from action_crypto.tx.transfer.transfer_ibc import (
    broadcast_ibc_transfer,
    prepare_ibc_transfer,
)
from config.config_links import LinksAPIChain
from config.config_list import ListData
from config.config_path import ConfigPath
from config.config_path_files import PathFileName
from project_utils.chain_resources import (
    get_network_client,
    get_wallet,
    load_ledger_clients_module,
    load_wallets_module,
)
from gui.setup_catalog import FIRST_RUN_PIPELINE, SETUP_ACTIONS
from project_utils.ibc_routes import (
    filter_routes_by_enabled,
    find_route,
    load_ibc_routes,
    routes_by_source,
)
from project_utils.networks_manager import (
    get_enabled_networks,
    get_rest_url,
    load_all_chains,
    network_rows,
    probe_all_chains,
    reset_enabled_to_defaults,
    set_enabled_networks,
    update_health_cache,
)
from action_crypto.tx.transfer.transfer_ibc import TIMEOUT_MODE_HEIGHT, TIMEOUT_MODE_TIME


@dataclass
class SetupStatus:
    source_dir: bool
    secret_vault: bool
    secret_unlock_files: bool
    secret_unlocked: bool
    ledger_clients: bool
    wallets_list: bool
    address_book: bool
    client_mapping: bool
    cosmos_data: bool
    secrets_path: str

    @property
    def ready_for_transfer(self) -> bool:
        return all(
            (
                self.secret_vault,
                self.secret_unlock_files or self.secret_unlocked,
                self.ledger_clients,
                self.wallets_list,
                self.address_book,
                self.client_mapping,
            )
        )


def get_paths() -> PathFileName:
    return PathFileName()


def active_wallet_display() -> tuple[str, str]:
    """(wallet_id, display label) for Portfolio header."""
    from project_utils.wallet_profiles import get_active_wallet_id, get_active_wallet_label

    wid = get_active_wallet_id()
    return wid, get_active_wallet_label()


def apply_wallet_switch_refresh() -> None:
    """Reload derived addresses and UI-facing data after wallet create/switch."""
    import importlib

    from project_utils.token_catalog import invalidate_token_catalog
    from project_utils.wallet_derivation import clear_wallet_cache

    clear_wallet_cache()
    invalidate_balance_cache()
    paths = get_paths()
    if os.path.isfile(paths.data_cosmos_file_name):
        from project_utils.create_check_data.generate.create_wallets import create_wallets_list_code

        create_wallets_list_code(
            paths.data_cosmos_file_name,
            paths.wallets_list_path,
            enabled_networks=get_wallet_networks(),
        )
        import chain.wallets.wallets_list as wallets_list_module

        importlib.reload(wallets_list_module)
    sync_wallet_artifacts_for_enabled_networks(update_address_book=True)
    invalidate_token_catalog()


def activate_wallet(wallet_id: str) -> str:
    from project_utils.wallet_ids import normalize_wallet_id
    from project_utils.wallet_profiles import set_active_wallet

    wid = normalize_wallet_id(wallet_id)
    set_active_wallet(wid)
    apply_wallet_switch_refresh()
    return wid


def create_new_wallet(
    label: str | None,
    secret: str,
    *,
    key_type: str | None = None,
    master_password: str | None = None,
    write_password_file: bool = True,
    create_vault: bool = False,
) -> str:
    """Store mnemonic or private key in vault, create profile, refresh addresses. Returns wN."""
    from chain.wallets.secret_vault import (
        get_status,
        store_mnemonic,
        store_private_key,
        store_wallet_secret,
    )
    from project_utils.wallet_mnemonic import normalize_secret_input
    from project_utils.wallet_profiles import create_wallet, next_wallet_id

    if key_type:
        secret_value = secret.strip()
        if key_type == 'mnemonic':
            from project_utils.wallet_mnemonic import validate_mnemonic

            validate_mnemonic(secret_value)
        else:
            from project_utils.wallet_mnemonic import parse_private_key_hex

            parse_private_key_hex(secret_value)
    else:
        key_type, secret_value = normalize_secret_input(secret)

    status = get_status()
    wallet_id = next_wallet_id()

    if create_vault or not status.vault_initialized:
        if not master_password:
            raise ValueError('Master password is required to create the vault.')
        if key_type != 'mnemonic':
            raise ValueError('The first wallet in a new vault must use a mnemonic.')
        store_wallet_secret(
            wallet_id,
            'mnemonic',
            secret_value,
            master_password=master_password,
            write_password_file=write_password_file,
            create_vault=True,
            overwrite=not status.vault_initialized,
        )
    elif key_type == 'mnemonic':
        store_mnemonic(wallet_id, secret_value)
    else:
        store_private_key(wallet_id, secret_value)

    create_wallet(label, wallet_id=wallet_id, key_type=key_type)
    activate_wallet(wallet_id)
    return wallet_id


def delete_wallet_full(wallet_id: str) -> None:
    """Remove profile, vault secrets, and rebuild address book."""
    from chain.wallets.secret_vault import delete_wallet_secrets, has_wallet_secret
    from project_utils.wallet_ids import normalize_wallet_id
    from project_utils.wallet_profiles import delete_wallet, get_active_wallet_id

    wid = normalize_wallet_id(wallet_id)
    if has_wallet_secret(wid):
        delete_wallet_secrets(wid)
    delete_wallet(wid)
    if get_active_wallet_id() == wid:
        apply_wallet_switch_refresh()
    else:
        sync_wallet_artifacts_for_enabled_networks(update_address_book=True)


def mnemonic_configured() -> bool:
    from chain.wallets.get_creds import mnemonic_is_configured

    return mnemonic_is_configured()


def get_setup_status() -> SetupStatus:
    from chain.wallets.secret_vault import get_status as vault_status

    paths = get_paths()
    vault = vault_status()
    return SetupStatus(
        source_dir=os.path.isdir(ConfigPath.source_path),
        secret_vault=vault.vault_initialized,
        secret_unlock_files=vault.unlock_files_ready,
        secret_unlocked=vault.is_unlocked,
        ledger_clients=os.path.isfile(paths.ledger_clients),
        wallets_list=os.path.isfile(paths.wallets_list_path),
        address_book=os.path.isfile(paths.address_book),
        client_mapping=os.path.isfile(paths.ledger_client_mapping),
        cosmos_data=os.path.isfile(paths.data_cosmos_file_name),
        secrets_path=vault.secrets_dir,
    )


def get_wallet_networks() -> set:
    from project_utils.networks_manager import get_enabled_networks

    return get_enabled_networks()


def enabled_networks_config_path() -> str:
    from project_utils.networks_manager import enabled_networks_path

    return enabled_networks_path()


def load_address_book_entries(
    networks: Optional[set] = None,
    all_networks: bool = False,
    all_wallets: bool = True,
) -> List[dict]:
    paths = get_paths()
    if not os.path.isfile(paths.address_book):
        return []
    with open(paths.address_book, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    if not all_networks:
        if networks is None:
            networks = get_wallet_networks()
        entries = [e for e in entries if e.get('network') in networks]
    if not all_wallets:
        from project_utils.wallet_ids import wallet_id_from_book_name
        from project_utils.wallet_profiles import get_active_wallet_id

        active = get_active_wallet_id()
        entries = [
            e
            for e in entries
            if wallet_id_from_book_name(e.get('name', '')) == active
        ]
    return entries


def _format_token_choice_display(symbol: str, denom: str) -> str:
    sym = (symbol or '').strip() or '?'
    d = (denom or '').strip()
    if not d:
        return sym
    if len(d) <= 52:
        return f'{sym} — {d}'
    return f'{sym} — {d[:22]}…{d[-10:]}'


def transfer_token_choices(network: str, list_mode: Optional[str] = None) -> List[dict]:
    """Token options for Send combobox: display label, symbol, on-chain denom."""
    from gui.settings import load_settings
    from project_utils.token_catalog import get_token_catalog

    network = (network or '').strip()
    if not network:
        return []
    mode = (list_mode or load_settings().get('send_token_list_mode', 'nonzero')).strip().lower()
    catalog = get_token_catalog()
    rest_map = chain_rest_urls()
    rest = rest_map.get(network)
    choices: List[dict] = []
    seen: set = set()

    def _add(symbol: str, denom: str) -> None:
        if not denom:
            return
        if rest and denom.lower().startswith('ibc/'):
            catalog.ensure_ibc_denom_resolved(network, denom, rest)
        row = catalog.get_row(network, denom)
        sym = (row.get('symbol') if row else symbol) or symbol
        sym = str(sym).strip()
        if sym.upper().startswith('IBC'):
            return
        key = (sym.lower(), _norm_denom_key(denom))
        if key in seen:
            return
        seen.add(key)
        choices.append(
            {
                'display': _format_token_choice_display(sym, denom),
                'symbol': sym,
                'denom': denom,
            }
        )

    if mode == 'all':
        network_n = network.lower()
        for (net, denom), row in catalog._by_network_denom.items():
            if net != network_n:
                continue
            _add(row.get('symbol', ''), row.get('denom', denom))
        choices.sort(key=lambda c: c['display'].lower())
        return choices
    return _balance_token_choices(network, catalog, rest)


def _norm_denom_key(denom: str) -> str:
    from project_utils.ibc_denom_resolver import normalize_ibc_denom

    d = (denom or '').strip()
    if d.lower().startswith('ibc/'):
        return normalize_ibc_denom(d)
    return d


def symbols_for_transfer_network(network: str, list_mode: Optional[str] = None) -> List[str]:
    return [c['display'] for c in transfer_token_choices(network, list_mode)]


def resolve_transfer_symbol(network: str, picked: str, list_mode: Optional[str] = None) -> str:
    """Map combobox display (or symbol) to catalog symbol for transfers."""
    from project_utils.token_catalog import get_token_catalog

    picked = (picked or '').strip()
    if not picked:
        raise ValueError('Enter a token symbol.')
    for choice in transfer_token_choices(network, list_mode):
        if picked == choice['display'] or picked.lower() == choice['symbol'].lower():
            return choice['symbol']
    network = (network or '').strip()
    catalog_symbols = get_token_catalog().symbols_for_network(network) if network else []
    for sym in catalog_symbols:
        if sym.lower() == picked.lower():
            return sym
    raise ValueError(f'Unknown token “{picked}” on {network}. Pick from the list.')


def _balance_token_choices(network: str, catalog, rest: Optional[str]) -> List[dict]:
    from decimal import Decimal, InvalidOperation

    choices: List[dict] = []
    seen: set = set()

    def _add(symbol: str, denom: str) -> None:
        if not denom:
            return
        if rest and denom.lower().startswith('ibc/'):
            catalog.ensure_ibc_denom_resolved(network, denom, rest)
        row = catalog.get_row(network, denom)
        sym = (row.get('symbol') if row else symbol) or symbol
        sym = str(sym).strip()
        if sym.upper().startswith('IBC'):
            return
        key = (sym.lower(), _norm_denom_key(denom))
        if key in seen:
            return
        seen.add(key)
        choices.append(
            {
                'display': _format_token_choice_display(sym, denom),
                'symbol': sym,
                'denom': denom,
            }
        )

    rows, _missed = fetch_balances(networks={network})
    if not rows:
        from project_utils.denoms_book import entries_for_network

        for item in entries_for_network(network):
            _add(item.get('symbol', ''), item.get('denom_contract', ''))
    for row in rows:
        if row.error or not row.denom or row.denom == '(empty)':
            continue
        try:
            if Decimal(str(row.amount)) <= 0:
                continue
        except (InvalidOperation, ValueError, TypeError):
            continue
        _add('', row.denom)
    choices.sort(key=lambda c: c['display'].lower())
    return choices


def add_user_token_mapping(
    network: str,
    denom: str,
    symbol: str,
    decimals: int = 6,
) -> dict:
    """Save user label for on-chain denom into denoms_book.json."""
    return upsert_denoms_book_entry(network, symbol, denom, decimals)


def list_denoms_book_entries(network: Optional[str] = None) -> List[dict]:
    from project_utils.denoms_book import load_entries

    entries = load_entries()
    if network and network.strip().lower() not in ('', 'all'):
        net = network.strip().lower()
        entries = [e for e in entries if e.get('network', '').lower() == net]
    return entries


def upsert_denoms_book_entry(
    network: str,
    symbol: str,
    denom_contract: str,
    decimal: int = 6,
) -> dict:
    from project_utils.denoms_book import upsert_entry
    from project_utils.token_catalog import invalidate_token_catalog

    entry = upsert_entry(network, symbol, denom_contract, decimal)
    invalidate_token_catalog()
    return entry


def delete_denoms_book_entry(network: str, denom_contract: str) -> bool:
    from project_utils.denoms_book import delete_entry
    from project_utils.token_catalog import invalidate_token_catalog

    ok = delete_entry(network, denom_contract)
    if ok:
        invalidate_token_catalog()
    return ok


def chain_rest_urls() -> dict:
    """network -> rest URL for IBC trace lookups."""
    import json
    import os

    from project_utils.networks_manager import get_rest_url

    paths = get_paths()
    if not os.path.isfile(paths.data_cosmos_file_name):
        return {}
    with open(paths.data_cosmos_file_name, 'r', encoding='utf-8') as f:
        chains = json.load(f)
    out = {}
    for chain in chains:
        name = chain.get('chain_name')
        rest = get_rest_url(chain)
        if name and rest:
            out[name] = rest
    return out


def fetch_portfolio_assets(with_fiat: bool = True):
    from gui.wallet_views import balance_rows_to_assets
    from project_utils.token_catalog import get_token_catalog
    from project_utils.wallet_profiles import row_belongs_to_active_wallet

    rows, missed = fetch_balances()
    rows = [r for r in rows if row_belongs_to_active_wallet(r.wallet_name)]
    catalog = get_token_catalog()
    chain_rest = chain_rest_urls()
    usd_prices = {}
    if with_fiat:
        from gui.settings import load_settings
        from project_utils.coingecko_prices import fetch_usd_prices

        if load_settings().get('show_fiat_prices', True):
            ids = set()
            for row in rows:
                if not row.denom or row.error:
                    continue
                if row.denom.lower().startswith('ibc/'):
                    rest = chain_rest.get(row.network)
                    if rest:
                        catalog.ensure_ibc_denom_resolved(row.network, row.denom, rest)
                cg = catalog.resolve_coingecko_id(row.network, row.denom)
                if cg:
                    ids.add(cg)
            usd_prices = fetch_usd_prices(ids)

    assets = balance_rows_to_assets(
        rows,
        catalog=catalog,
        usd_prices=usd_prices,
        chain_rest_by_network=chain_rest,
    )
    total_usd = 0.0
    for asset in assets:
        usd = asset.get('usd', '')
        if usd.startswith('$'):
            try:
                total_usd += float(usd.replace('$', '').replace(',', ''))
            except ValueError:
                pass
    return assets, missed, total_usd, rows


def balance_cache_ttl_seconds() -> float:
    from gui.settings import load_settings

    raw = load_settings().get('balance_cache_seconds', 30)
    try:
        ttl = float(raw)
    except (TypeError, ValueError):
        ttl = 30.0
    return max(0.0, min(600.0, ttl))


def invalidate_balance_cache() -> None:
    from project_utils.data_cache import get_cache

    get_cache('balances').clear()


def _balance_cache_key() -> tuple:
    from project_utils.wallet_profiles import get_active_wallet_id

    enabled = frozenset(get_wallet_networks())
    return (get_active_wallet_id(), enabled)


def _symbol_balance_from_rows(
    rows: List,
    network: str,
    symbol: str,
    catalog,
) -> Optional['BalanceRow']:
    from action_crypto.bank.balance_query import BalanceRow

    network = (network or '').strip()
    symbol = (symbol or '').strip()
    if not network or not symbol:
        return None

    wallet_name = ''
    address = ''
    for row in rows:
        if getattr(row, 'network', None) == network:
            wallet_name = getattr(row, 'wallet_name', '')
            address = getattr(row, 'address', '')
            if getattr(row, 'error', None):
                return row
            break
    if not address:
        return None

    try:
        target_denom, _decimals = catalog.resolve_denom(network, symbol)
    except ValueError as exc:
        return BalanceRow(wallet_name, network, address, '', '', error=str(exc))

    sym_lower = symbol.lower()
    match: Optional[BalanceRow] = None
    for row in rows:
        if getattr(row, 'network', None) != network:
            continue
        if getattr(row, 'error', None):
            return row
        denom = getattr(row, 'denom', '')
        if denom == target_denom:
            return row
        if catalog.label_for_denom(network, denom).lower() == sym_lower:
            match = row
    if match is not None:
        return match
    return BalanceRow(wallet_name, network, address, target_denom, '0')


def get_transfer_side_balances(source: str, dest: str, symbol: str) -> dict:
    """
    On-chain balances for Send UI: sender on source network, receiver on destination.
    Returns dict with sender_text, receiver_text, sender_max (float human amount for Max).
    """
    from decimal import Decimal, InvalidOperation

    from project_utils.token_catalog import get_token_catalog

    source = (source or '').strip()
    dest = (dest or '').strip()
    symbol = (symbol or '').strip()
    empty = {
        'sender_text': '—',
        'receiver_text': '—',
        'sender_max': 0.0,
    }
    if not symbol:
        return empty

    paths = get_paths()
    catalog = get_token_catalog()

    def _format_row(row, label: str) -> tuple[str, float]:
        if row.error:
            return f'{label}: error — {row.error}', 0.0
        display = format_balance_display(row.network, row.denom, row.amount)
        max_human = 0.0
        if row.denom and row.denom != '(empty)':
            try:
                row_meta = catalog.get_row(row.network, row.denom)
                decimals = int(row_meta.get('decimals', 6)) if row_meta else 6
                max_human = float(Decimal(str(row.amount)) / (Decimal(10) ** decimals))
            except (InvalidOperation, ValueError, TypeError):
                max_human = 0.0
        return f'{label}: {display}', max_human

    cached_rows, _missed = fetch_balances()
    sender_row = _symbol_balance_from_rows(cached_rows, source, symbol, catalog)
    if sender_row is None:
        sender_row = query_symbol_balance_on_network(
            source,
            symbol,
            paths.ledger_client_mapping,
            paths.address_book,
        )
    sender_text, sender_max = _format_row(sender_row, f'From ({source})')

    receiver_text = f'To ({dest}): —'
    if dest:
        receiver_row = _symbol_balance_from_rows(cached_rows, dest, symbol, catalog)
        if receiver_row is None:
            receiver_row = query_symbol_balance_on_network(
                dest,
                symbol,
                paths.ledger_client_mapping,
                paths.address_book,
            )
        receiver_text, _ = _format_row(receiver_row, f'To ({dest})')

    return {
        'sender_text': sender_text,
        'receiver_text': receiver_text,
        'sender_max': max(0.0, sender_max),
    }


def format_balance_display(network: str, denom: str, amount: str) -> str:
    from project_utils.token_catalog import get_token_catalog

    if not denom or denom == '(empty)':
        return '0'
    catalog = get_token_catalog()
    if denom.lower().startswith('ibc/'):
        rest = chain_rest_urls().get((network or '').strip())
        if rest:
            catalog.ensure_ibc_denom_resolved(network, denom, rest)
    return catalog.format_amount(amount, network, denom)


def get_ledger_link_type() -> str:
    from gui.settings import load_settings

    return load_settings().get('ledger_link_type', 'keplr_rest_link')


def run_captured(callable_fn: Callable[[], None]) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        try:
            callable_fn()
        except SystemExit:
            pass
    return buffer.getvalue()


def validate_transfer_sender(source: str, symbol: str, amount: float) -> Optional[str]:
    """
    Pre-flight check: sender has enough balance. Returns user-facing error or None.
    """
    source = (source or '').strip()
    symbol = (symbol or '').strip()
    if not source or not symbol:
        return 'Select source network and token.'
    try:
        amount_f = float(amount)
    except (TypeError, ValueError):
        return 'Invalid amount.'
    if amount_f <= 0:
        return 'Amount must be greater than zero.'

    info = get_transfer_side_balances(source, '', symbol)
    available = float(info.get('sender_max', 0.0))
    if available <= 0:
        return (
            f'On {source} you have 0 {symbol} ({info.get("sender_text", "")}).\n\n'
            f'The address exists in your address book but is not activated on-chain yet '
            f'(Cosmos accounts appear after the first incoming transfer).\n\n'
            f'Fund this wallet on {source} first, or set From to a network where you already '
            f'have balance (e.g. osmosis if BLD is there).'
        )
    if amount_f > available + 1e-12:
        return (
            f'Amount {amount_f} {symbol} exceeds available balance on {source} '
            f'({available:g} {symbol}). Use Max or lower the amount.'
        )
    return None


def destination_rest_url(network: str) -> Optional[str]:
    for chain in load_all_chains():
        if chain.get('chain_name') == network:
            return get_rest_url(chain)
    return None


def gui_prepare_transfer(
    route,
    symbol: str,
    amount: float,
    *,
    timeout_mode: str = TIMEOUT_MODE_TIME,
    timeout_value: Optional[int] = None,
):
    paths = get_paths()
    mode = (timeout_mode or TIMEOUT_MODE_TIME).strip().lower()
    value = int(timeout_value if timeout_value is not None else route.get('timeout_seconds', 120))
    dest = route.get('destination_network', '')
    destination_rest = destination_rest_url(dest) if mode == TIMEOUT_MODE_HEIGHT else None
    return prepare_ibc_transfer(
        symbol,
        route['source_network'],
        paths.address_book,
        paths.denoms_book_path,
        amount,
        route['sender_wallet'],
        route['receiver_wallet'],
        route['channel'],
        route['gas'],
        timeout_mode=mode,
        timeout_value=value,
        destination_rest=destination_rest,
    )


def recommended_gas_limit(route_gas: int, *, auto_buffer: bool = True) -> int:
    """Suggest gas with headroom (failed txs often exceed route file defaults)."""
    base = max(int(route_gas), 80_000)
    if not auto_buffer:
        return base
    return max(base + 80_000, int(base * 1.35))


def parse_out_of_gas_hint(error_text: str, used_gas: Optional[int] = None) -> str:
    import re

    text = error_text or ''
    m = re.search(r'gasWanted:\s*(\d+).*?gasUsed:\s*(\d+)', text, re.I | re.S)
    if m:
        wanted, used = int(m.group(1)), int(m.group(2))
        suggest = max(used + 50_000, int(used * 1.2))
        return (
            f'Out of gas: used {used:,} but limit was {wanted:,}.\n'
            f'Try Gas limit ≥ {suggest:,} (enable Auto gas or raise manually).'
        )
    if used_gas:
        suggest = max(used_gas + 50_000, int(used_gas * 1.2))
        return f'Out of gas. Try Gas limit ≥ {suggest:,}.'
    if 'out of gas' in text.lower():
        return 'Out of gas — increase Gas limit on the Send tab (Auto gas or manual).'
    return text


def record_transfer_tx(
    *,
    status: str,
    route: dict,
    preview=None,
    gas: int = 0,
    tx_hash: str = '',
    error: str = '',
    symbol: str = '',
    amount: str = '',
    timeout_mode: str = TIMEOUT_MODE_TIME,
    timeout_value: str = '120',
    timeout_display: str = '',
) -> None:
    from project_utils.tx_history import append_tx_record

    sym = symbol or getattr(preview, 'symbol', '') or ''
    amt = amount if amount != '' else getattr(preview, 'amount_token', '')
    mode = timeout_mode or getattr(preview, 'timeout_mode', TIMEOUT_MODE_TIME)
    tval = timeout_value or str(getattr(preview, 'timeout_value', route.get('timeout_seconds', 120)))
    tdisplay = timeout_display or getattr(preview, 'timeout_display', '')
    append_tx_record(
        status=status,
        source=route.get('source_network', ''),
        destination=route.get('destination_network', ''),
        symbol=sym,
        amount=str(amt),
        gas=int(gas or getattr(preview, 'gas', route.get('gas', 0))),
        channel=route.get('channel', ''),
        tx_hash=tx_hash,
        error=error,
        sender_address=getattr(preview, 'sender_address', ''),
        receiver_address=getattr(preview, 'receiver_address', ''),
        timeout_mode=mode,
        timeout_value=tval,
        timeout_display=tdisplay,
    )


def list_tx_history() -> List[dict]:
    from project_utils.tx_history import load_tx_history

    return load_tx_history()


def filtered_tx_history(
    *,
    date_from: str = '',
    date_to: str = '',
    statuses: Optional[set] = None,
) -> List[dict]:
    from gui.history_view import filter_tx_history, parse_filter_date

    rows = list_tx_history()
    try:
        d_from = parse_filter_date(date_from) if date_from.strip() else None
        d_to = parse_filter_date(date_to) if date_to.strip() else None
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    return filter_tx_history(rows, date_from=d_from, date_to=d_to, statuses=statuses)


def gui_broadcast_transfer(route, preview, gas_limit: Optional[int] = None) -> str:
    ledger_module = load_ledger_clients_module()
    wallets_module = load_wallets_module()
    network = route['source_network']
    client = get_network_client(ledger_module, network)
    wallet = get_wallet(wallets_module, route['wallet_attr'])
    limit = int(gas_limit) if gas_limit is not None else preview.gas
    try:
        tx_hash = broadcast_ibc_transfer(preview, client, wallet, gas_limit=limit)
    except Exception as exc:
        record_transfer_tx(
            status='failed',
            route=route,
            preview=preview,
            gas=limit,
            error=str(exc),
        )
        msg = str(exc)
        lower = msg.lower()
        if 'not found' in lower and 'account' in lower:
            raise RuntimeError(
                f'Account not found on {network} ({preview.sender_address}).\n\n'
                f'The wallet was never funded on this chain — send a small deposit to this '
                f'address first, or use From = another network where you already hold tokens.'
            ) from exc
        if 'out of gas' in lower:
            raise RuntimeError(parse_out_of_gas_hint(msg)) from exc
        raise
    record_transfer_tx(
        status='success',
        route=route,
        preview=preview,
        gas=limit,
        tx_hash=tx_hash,
    )
    invalidate_balance_cache()
    return tx_hash


def fetch_balances(networks: Optional[set] = None, *, force: bool = False):
    """On-chain balances for enabled networks; cached snapshot shared across GUI tabs."""
    paths = get_paths()
    if not os.path.isfile(paths.ledger_client_mapping) or not os.path.isfile(paths.address_book):
        return [], []
    enabled = frozenset(get_wallet_networks())
    if not enabled:
        return [], []

    from project_utils.data_cache import get_cache

    cache = get_cache('balances', default_ttl=balance_cache_ttl_seconds())
    ttl = balance_cache_ttl_seconds()
    use_cache = ttl > 0 and not force
    cache_key = _balance_cache_key()

    def _load():
        return query_all_balances(
            paths.ledger_client_mapping,
            paths.address_book,
            networks=set(enabled),
        )

    if use_cache:
        snapshot, _from_cache = cache.get_or_fetch(cache_key, _load, ttl=ttl, force=force)
    else:
        snapshot = _load()
        if ttl > 0:
            cache.set(cache_key, snapshot, ttl=ttl)

    all_rows, missed = snapshot
    if networks is None:
        return all_rows, missed
    want = frozenset(networks)
    filtered = [r for r in all_rows if getattr(r, 'network', None) in want]
    return filtered, missed


def summarize_wallet_balances(rows: List) -> List[dict]:
    """One summary row per network for the wallet overview strip."""
    from action_crypto.bank.balance_query import BalanceRow
    from project_utils.token_catalog import get_token_catalog

    catalog = get_token_catalog()
    by_network: dict = {}
    for row in rows:
        if not isinstance(row, BalanceRow):
            continue
        net = row.network
        if net not in by_network:
            by_network[net] = {'network': net, 'address': row.address, 'summary': '—', 'error': None}
        if row.error:
            by_network[net]['error'] = row.error
            by_network[net]['summary'] = 'error'
        elif row.denom and row.denom != '(empty)':
            part = catalog.format_amount(row.amount, net, row.denom)
            prev = by_network[net]['summary']
            if prev in ('—', '0', 'error'):
                by_network[net]['summary'] = part
            elif prev != part and not prev.endswith('…'):
                by_network[net]['summary'] = prev + ' · ' + part
    order = sorted(by_network.keys(), key=str.lower)
    return [by_network[n] for n in order]


def fetch_osmosis_tokens(limit: Optional[int] = 500):
    links = LinksAPIChain()
    timeout = 180.0 if limit is None else (90.0 if (limit or 0) > 3000 else 60.0 if (limit or 0) > 1000 else 45.0)
    return fetch_osmosis_token_rows(
        links.link_osmosis_token,
        display_values=None,
        limit=limit,
        timeout=timeout,
    )


def fetch_registry_token_rows(
    chain_name: Optional[str] = None,
    symbol_filter: Optional[str] = None,
    search: Optional[str] = None,
    with_prices: bool = True,
):
    from project_utils.registry_tokens import token_display_rows

    sym = symbol_filter if symbol_filter is not None else search
    return token_display_rows(
        chain_name=chain_name,
        symbol_filter=sym,
        with_osmosis_prices=with_prices,
    )


def registry_chains_with_tokens():
    from project_utils.registry_tokens import chains_with_tokens

    return chains_with_tokens()


def tokens_tab_cache_key(chain_label: str) -> str:
    chain = (chain_label or '').strip()
    if not chain or chain.lower() == 'all':
        return 'all'
    return chain.lower().replace(' ', '_')


def save_tokens_tab_cache(chain_label: str, rows: list, meta: dict) -> None:
    from project_utils.tab_data_cache import save_tab_cache

    save_tab_cache(
        'tokens',
        tokens_tab_cache_key(chain_label),
        {'rows': rows, 'meta': meta},
    )


def load_tokens_tab_cache(chain_label: str) -> Optional[dict]:
    from project_utils.tab_data_cache import load_tab_cache

    return load_tab_cache('tokens', tokens_tab_cache_key(chain_label))


def save_market_tab_cache(rows: list, cache_key: str = 'osmosis') -> None:
    from project_utils.tab_data_cache import save_tab_cache

    save_tab_cache('market', cache_key, {'rows': rows})


def load_market_tab_cache(cache_key: str = 'osmosis') -> Optional[dict]:
    from project_utils.tab_data_cache import load_tab_cache

    env = load_tab_cache('market', cache_key)
    if env is None and cache_key == 'top_500':
        return load_tab_cache('market', 'osmosis')
    return env


def prepare_market_rows(rows: list) -> list:
    prepared = []
    for row in rows:
        item = dict(row)
        liq = item.get('liquidity')
        vol = item.get('volume_24h')
        item['_liquidity_fmt'] = f'{float(liq):,.0f}' if liq not in ('', None) else ''
        item['_volume_fmt'] = f'{float(vol):,.0f}' if vol not in ('', None) else ''
        prepared.append(item)
    return prepared


def run_setup_action(action_id: str, link_type: Optional[str] = None) -> str:
    from config.config_files import FileName
    from config.config_list import ListData
    from project_utils.create_check_data.collect_data.json.json_scanner import (
        check_info,
        init_data_list,
        traverse_directory_chain_data,
    )
    from project_utils.create_check_data.generate.create_address_book import create_addresses_book
    from project_utils.create_check_data.generate.create_ledger_clients import (
        create_ledger_client_mapping,
        create_ledger_clients_file,
    )
    from project_utils.create_check_data.generate.create_wallets import create_wallets_list_code
    from project_utils.create_check_data.setup.setup import (
        check_apps,
        check_platform,
        check_python_modules,
        check_pythonpath,
        source_create_or_check,
    )

    path = ConfigPath()
    filename = FileName()
    paths = get_paths()
    data_list = ListData()

    def do_source():
        source_create_or_check()
        check_info(
            path.chain_registry_path,
            path.data_path,
            filename.filename_dict_chain_id,
            data_list.key1_chain,
            data_list.key2_chain,
        )

    def do_pythonpath():
        check_pythonpath(path.project_path)

    def do_apps():
        check_apps()

    def do_modules():
        check_python_modules(data_list.modules_list)

    def do_all_checks():
        check_platform()
        source_create_or_check()
        check_pythonpath(path.project_path)
        check_apps()
        check_python_modules(data_list.modules_list)

    def do_collect_json():
        from project_utils.create_check_data.collect_data.json.collect_assets import (
            collect_assets_registry,
        )

        chain_id_path = paths.list_chain_id
        if not os.path.isfile(chain_id_path):
            raise FileNotFoundError(
                f'{chain_id_path} not found. Run source step first (chain-registry scan).'
            )
        with open(chain_id_path, 'r', encoding='utf-8') as f:
            chain_ids = list(json.load(f).values())
        traverse_directory_chain_data(
            path.chain_registry_path,
            path.keplr_chain_registry_path,
            paths.result_collection_chain_file_name,
            data_list.keys_to_extract_chain_data,
            data_list.keys_to_extract_chain_keplr_data,
            chain_ids,
            verify_rest=False,
        )
        init_data_list(path.chain_path, path.data_path, filename.filename_cosmos_data)
        collect_assets_registry(path.chain_registry_path, paths.assets_registry)
        from project_utils.token_catalog import invalidate_token_catalog

        invalidate_token_catalog()
        try:
            sync_ibc_routes_for_enabled_networks(get_enabled_networks())
        except OSError:
            pass

    def do_ledger_clients():
        enabled = get_enabled_networks()
        lt = link_type or get_ledger_link_type()
        create_ledger_clients_file(
            paths.data_cosmos_file_name,
            path.data_path,
            filename.filename_cosmos_data,
            path.root_client_path,
            filename.project_file_ledger_client,
            link_type=lt,
            enabled_networks=enabled,
        )
        create_ledger_client_mapping(
            paths.data_cosmos_file_name,
            paths.ledger_client_mapping,
            enabled_networks=enabled,
        )

    def do_wallets():
        create_wallets_list_code(
            paths.data_cosmos_file_name,
            paths.wallets_list_path,
            enabled_networks=get_enabled_networks(),
        )

    def do_address_book():
        from chain.wallets.get_creds import require_configured_mnemonic
        from chain.wallets.wallets_list import write_address_variables_to_json

        require_configured_mnemonic()
        write_address_variables_to_json(paths.address_book_temp)
        create_addresses_book(
            path.create_path,
            filename.filename_temp_address_book,
            path.data_path,
            filename.filename_address_book,
        )

    actions = {
        'source': do_source,
        'pythonpath': do_pythonpath,
        'apps': do_apps,
        'modules': do_modules,
        'all_checks': do_all_checks,
        'collect_json': do_collect_json,
        'ledger_clients': do_ledger_clients,
        'wallets': do_wallets,
        'address_book': do_address_book,
    }
    fn = actions.get(action_id)
    if fn is None:
        raise ValueError(f'Unknown setup action: {action_id}')
    return run_captured(fn)


def ibc_routes_grouped():
    """IBC routes limited to networks enabled on the Networks tab (source and destination)."""
    enabled = get_enabled_networks()
    grouped = routes_by_source(load_ibc_routes())
    return filter_routes_by_enabled(grouped, enabled)


def list_network_rows():
    return network_rows()


def sync_ibc_routes_for_enabled_networks(enabled: Optional[set] = None) -> int:
    """Regenerate source/data/generated_ibc_routes.json from registry _IBC for enabled pairs."""
    from project_utils.ibc_routes import sync_generated_routes_for_enabled

    if enabled is None:
        enabled = get_enabled_networks()
    routes = sync_generated_routes_for_enabled(enabled)
    return len(routes)


def save_enabled_network_selection(enabled_names: List[str]) -> None:
    set_enabled_networks(enabled_names)
    try:
        sync_ibc_routes_for_enabled_networks(set(enabled_names))
    except OSError:
        pass


def sync_wallet_artifacts_for_enabled_networks(
    enabled: Optional[Iterable[str]] = None,
    *,
    link_type: Optional[str] = None,
    update_address_book: bool = True,
) -> str:
    """
    Regenerate wallets_list, ledger clients, and address_book.json for enabled networks.
    Called when the user enables a chain on the Networks tab.
    """
    import importlib

    from config.config_files import FileName
    from config.config_path import ConfigPath
    from gui.setup_catalog import _vault_ready_for_address_book
    from project_utils.create_check_data.generate.create_address_book import create_addresses_book
    from project_utils.create_check_data.generate.create_ledger_clients import (
        create_ledger_client_mapping,
        create_ledger_clients_file,
    )
    from project_utils.create_check_data.generate.create_wallets import create_wallets_list_code

    enabled_set = set(enabled) if enabled is not None else get_enabled_networks()
    if not enabled_set:
        return 'No enabled networks to sync.'

    paths = get_paths()
    cfg_path = ConfigPath()
    fn = FileName()
    lt = link_type or get_ledger_link_type()
    lines = [f'Wallet sync for: {", ".join(sorted(enabled_set))}']

    if not os.path.isfile(paths.data_cosmos_file_name):
        lines.append('Skipped: run Setup → Collect chain-registry JSON first.')
        return '\n'.join(lines)

    create_wallets_list_code(
        paths.data_cosmos_file_name,
        paths.wallets_list_path,
        enabled_networks=enabled_set,
    )
    lines.append('· wallets_list.py')

    create_ledger_clients_file(
        paths.data_cosmos_file_name,
        cfg_path.data_path,
        fn.filename_cosmos_data,
        cfg_path.root_client_path,
        fn.project_file_ledger_client,
        link_type=lt,
        enabled_networks=enabled_set,
    )
    create_ledger_client_mapping(
        paths.data_cosmos_file_name,
        paths.ledger_client_mapping,
        enabled_networks=enabled_set,
    )
    lines.append('· ledger clients + mapping')

    if update_address_book:
        if not _vault_ready_for_address_book():
            lines.append(
                '· address book not updated — unlock vault '
                f'({cfg_path.secrets_path}: master.password + wallet.key) or create vault in Setup',
            )
        else:
            import chain.wallets.wallets_list as wallets_list_module

            importlib.reload(wallets_list_module)
            wallets_list_module.write_address_variables_to_json(paths.address_book_temp)
            create_addresses_book(
                cfg_path.create_path,
                fn.filename_temp_address_book,
                cfg_path.data_path,
                fn.filename_address_book,
            )
            import json

            with open(paths.address_book, 'r', encoding='utf-8') as f:
                book = json.load(f)
            nets = sorted({e.get('network') for e in book})
            lines.append(f'· address_book.json ({len(book)} addresses: {", ".join(nets)})')

    return '\n'.join(lines)


def restore_default_enabled_networks() -> List[str]:
    names = reset_enabled_to_defaults()
    try:
        sync_ibc_routes_for_enabled_networks(names)
    except OSError:
        pass
    return sorted(names)


def test_all_network_health(link_type: str = 'rest_link') -> str:
    from project_utils.networks_manager import test_all_network_health as _probe_all

    return _probe_all(link_type=link_type)


def regenerate_for_enabled_networks(link_type: Optional[str] = None) -> str:
    return sync_wallet_artifacts_for_enabled_networks(link_type=link_type)


def ibc_route_for(source: str, destination: str):
    return find_route(source, destination)


def list_setup_actions():
    return SETUP_ACTIONS


def run_first_run_pipeline(link_type: Optional[str] = None) -> str:
    from gui.setup_catalog import _wallet_has_real_mnemonic

    logs = []
    for step, action_id in enumerate(FIRST_RUN_PIPELINE, start=1):
        action = next(a for a in SETUP_ACTIONS if a.id == action_id)
        logs.append(f'\n{"=" * 60}\nStep {step}/{len(FIRST_RUN_PIPELINE)}: {action.title}\n{"=" * 60}\n')

        if action_id == 'address_book':
            from gui.setup_catalog import _vault_ready_for_address_book

            if not _vault_ready_for_address_book():
                logs.append(
                    'SKIPPED: unlock the vault first.\n'
                    f'Copy master.password and wallet.key to {ConfigPath.secrets_path}\n'
                    'or create the vault via “Secret vault” in Setup.\n'
                )
                continue

        lt = (link_type or get_ledger_link_type()) if action_id == 'ledger_clients' else None
        try:
            logs.append(run_setup_action(action_id, link_type=lt))
        except Exception as exc:
            logs.append(f'ERROR: {exc}\n')
    return ''.join(logs)
