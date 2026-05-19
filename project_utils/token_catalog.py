"""Map denoms ↔ symbols and format human-readable amounts."""

from __future__ import annotations

import json
import os
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

from config.config_path_files import PathFileName
from project_utils.denoms_lookup import load_denoms_index
from project_utils.keplr_registry_loader import iter_keplr_currency_rows
from project_utils.registry_tokens import load_registry_tokens


def _norm_network(network: str) -> str:
    return (network or '').strip().lower()


def _norm_denom(denom: str) -> str:
    from project_utils.ibc_denom_resolver import normalize_ibc_denom

    d = (denom or '').strip()
    if d.lower().startswith('ibc/'):
        return normalize_ibc_denom(d)
    return d


class TokenCatalog:
    """Unified symbol/denom/decimals lookup for GUI and transfers."""

    def __init__(self) -> None:
        self._by_network_denom: Dict[Tuple[str, str], dict] = {}
        self._by_network_symbol: Dict[Tuple[str, str], dict] = {}
        self._loaded = False

    def reload(self) -> None:
        self._by_network_denom.clear()
        self._by_network_symbol.clear()
        paths = PathFileName()

        from project_utils.denoms_book import load_entries

        for item in load_entries(paths.denoms_book_path):
            self._register(
                item.get('network', ''),
                item.get('denom_contract', ''),
                symbol=item.get('symbol'),
                decimals=item.get('decimal'),
                source='denoms_book',
            )

        for token in load_registry_tokens():
            self._register(
                token.get('chain_name', ''),
                token.get('denom', ''),
                symbol=token.get('symbol') or token.get('display'),
                decimals=token.get('decimals'),
                display=token.get('display'),
                source='registry',
            )

        for row in iter_keplr_currency_rows():
            self._register(
                row.get('chain_name', ''),
                row.get('denom', ''),
                symbol=row.get('symbol'),
                decimals=row.get('decimals'),
                display=row.get('display'),
                coingecko_id=row.get('coingecko_id'),
                source='keplr_registry',
            )

        cosmos_path = paths.data_cosmos_file_name
        if os.path.isfile(cosmos_path):
            with open(cosmos_path, 'r', encoding='utf-8') as f:
                chains = json.load(f)
            for chain in chains:
                network = chain.get('chain_name', '')
                denom = chain.get('denom', '')
                if network and denom:
                    self._register(
                        network,
                        denom,
                        symbol=denom.lstrip('u').upper()[:6] if denom.startswith('u') else denom,
                        decimals=6,
                        source='chain_fee',
                    )

        self._loaded = True

    def _register(
        self,
        network: str,
        denom: str,
        *,
        symbol: Optional[str] = None,
        decimals=None,
        display: Optional[str] = None,
        coingecko_id: Optional[str] = None,
        source: str = '',
    ) -> None:
        network_n = _norm_network(network)
        denom_n = _norm_denom(denom)
        if not network_n or not denom_n:
            return
        try:
            dec = int(decimals) if decimals is not None else None
        except (TypeError, ValueError):
            dec = None
        key = (network_n, denom_n)
        row = self._by_network_denom.get(key, {})
        row.update(
            {
                'network': network,
                'denom': denom_n,
                'symbol': (symbol or row.get('symbol') or denom_n).strip(),
                'display': (display or row.get('display') or symbol or denom_n).strip(),
                'decimals': dec if dec is not None else row.get('decimals'),
                'source': source or row.get('source'),
            }
        )
        if coingecko_id:
            row['coingecko_id'] = coingecko_id
        self._by_network_denom[key] = row
        sym = (row.get('symbol') or '').lower()
        if sym:
            self._by_network_symbol[(network_n, sym)] = row
        self._loaded = True

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self.reload()

    def resolve_denom(self, network: str, symbol: str) -> Tuple[str, int]:
        self.ensure_loaded()
        network_n = _norm_network(network)
        sym_n = (symbol or '').strip().lower()
        row = self._by_network_symbol.get((network_n, sym_n))
        if row is None:
            paths = PathFileName()
            if os.path.isfile(paths.denoms_book_path):
                from project_utils.denoms_lookup import resolve_denom

                index = load_denoms_index(paths.denoms_book_path)
                denom, dec = resolve_denom(index, symbol, network)
                return denom, dec
            raise ValueError(f'Unknown token symbol {symbol!r} on {network!r}')
        dec = row.get('decimals')
        if dec is None:
            raise ValueError(f'No decimals for {symbol!r} on {network!r}')
        return row['denom'], int(dec)

    def get_row(self, network: str, denom: str) -> Optional[dict]:
        self.ensure_loaded()
        return self._by_network_denom.get((_norm_network(network), _norm_denom(denom)))

    def get_coingecko_id(self, network: str, denom: str) -> Optional[str]:
        row = self.get_row(network, denom)
        if not row:
            return None
        return row.get('coingecko_id')

    def register_ibc_resolution(
        self,
        network: str,
        ibc_denom: str,
        origin_denom: str,
        origin_network: Optional[str] = None,
        *,
        persist: bool = True,
    ) -> bool:
        """Map IBC hash denom to symbol/decimals from origin asset (any known network)."""
        origin_denom_n = _norm_denom(origin_denom)
        origin_row = None
        if origin_network:
            origin_row = self.get_row(origin_network, origin_denom)
        if origin_row is None:
            for (net, denom), row in self._by_network_denom.items():
                if denom == origin_denom_n:
                    origin_row = row
                    origin_network = origin_network or row.get('network') or net
                    break
        symbol = None
        decimals = None
        display = None
        coingecko_id = None
        if origin_row:
            symbol = origin_row.get('symbol')
            decimals = origin_row.get('decimals')
            display = origin_row.get('display')
            coingecko_id = origin_row.get('coingecko_id')
            origin_network = origin_network or origin_row.get('network')
        else:
            from project_utils.ibc_denom_resolver import infer_symbol_decimals_from_base_denom

            symbol, decimals = infer_symbol_decimals_from_base_denom(origin_denom)
        self._register(
            network,
            ibc_denom,
            symbol=symbol,
            decimals=decimals,
            display=display,
            coingecko_id=coingecko_id,
            source='ibc_trace',
        )
        if persist and symbol:
            from project_utils.denoms_book import upsert_entry

            upsert_entry(
                network,
                str(symbol),
                ibc_denom,
                int(decimals or 6),
            )
            self._register(
                network,
                ibc_denom,
                symbol=symbol,
                decimals=decimals,
                display=display,
                coingecko_id=coingecko_id,
                source='denoms_book',
            )
        return True

    def resolve_ibc_via_rest(self, network: str, ibc_denom: str, rest_base: str) -> bool:
        """Query denom_traces on chain REST and register symbol for this IBC denom."""
        if not ibc_denom.lower().startswith('ibc/'):
            return False
        ibc_denom = _norm_denom(ibc_denom)
        if self.get_row(network, ibc_denom):
            return True
        from project_utils.ibc_denom_resolver import fetch_denom_trace, origin_denom_from_trace

        trace = fetch_denom_trace(rest_base, ibc_denom)
        origin = origin_denom_from_trace(trace) if trace else None
        if not origin:
            return False
        return self.register_ibc_resolution(network, ibc_denom, origin, persist=True)

    def ensure_ibc_denom_resolved(self, network: str, denom: str, rest_base: Optional[str] = None) -> None:
        if not denom.lower().startswith('ibc/'):
            return
        if self.get_row(network, denom):
            return
        if rest_base:
            self.resolve_ibc_via_rest(network, denom, rest_base)

    def label_for_denom(self, network: str, denom: str) -> str:
        self.ensure_loaded()
        row = self.get_row(network, denom)
        if not row:
            if denom.startswith('ibc/'):
                return f'IBC…{denom[-8:]}'
            return denom
        sym = row.get('symbol') or row.get('display') or denom
        return str(sym).upper() if len(str(sym)) <= 8 else str(sym)

    def format_amount(
        self,
        raw_amount: str,
        network: str,
        denom: str,
        *,
        max_places: int = 6,
    ) -> str:
        self.ensure_loaded()
        row = self._by_network_denom.get((_norm_network(network), _norm_denom(denom)))
        decimals = row.get('decimals') if row else None
        label = self.label_for_denom(network, denom) if row else denom
        if decimals is None:
            if denom.startswith('ibc/'):
                decimals = 6
            else:
                try:
                    decimals = 6 if str(denom).startswith('u') else 0
                except Exception:
                    decimals = 6
        try:
            raw = Decimal(str(raw_amount))
            scale = Decimal(10) ** int(decimals)
            human = raw / scale
        except (InvalidOperation, ValueError, TypeError):
            return f'{raw_amount} {label}'
        text = format(human, f',.{max_places}f').rstrip('0').rstrip('.')
        return f'{text} {label}'

    def symbols_for_network(self, network: str) -> List[str]:
        self.ensure_loaded()
        network_n = _norm_network(network)
        seen = set()
        symbols: List[str] = []
        for (net, sym), row in sorted(self._by_network_symbol.items()):
            if net != network_n:
                continue
            display = (row.get('symbol') or sym).strip()
            key = display.lower()
            if key in seen:
                continue
            seen.add(key)
            symbols.append(display)
        return symbols


_catalog: Optional[TokenCatalog] = None


def get_token_catalog() -> TokenCatalog:
    global _catalog
    if _catalog is None:
        _catalog = TokenCatalog()
    return _catalog


def invalidate_token_catalog() -> None:
    global _catalog
    if _catalog is not None:
        _catalog.reload()
    else:
        _catalog = TokenCatalog()
