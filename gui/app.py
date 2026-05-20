import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk
from typing import Optional

from config.config_path import ConfigPath
from chain.wallets.secret_vault import get_status as vault_get_status
from gui import services
from gui.settings import load_settings, save_settings
from gui.custom_theme_dialog import open_custom_theme_dialog
from gui.theme import (
    CUSTOM_THEME_ID,
    DEFAULT_THEME,
    apply_theme,
    get_palette,
    style_canvas,
    style_listbox,
    style_text_widget,
    theme_labels_map,
)
from gui.autocomplete import bind_searchable_combobox
from gui.clipboard_util import copy_to_clipboard
from gui.network_picker import NetworkListPicker
from gui.vault_dialog import show_create_vault_dialog, show_edit_mnemonic_dialog

NAV_LABELS = (
    'Portfolio',
    'Send',
    'Swap',
    'Receive',
    'History',
    '—',
    'Networks',
    'Tokens',
    'Denoms',
    'Market',
    '—',
    'Address book',
    'Setup',
    'Settings',
    'Status',
)

NAV_SEPARATORS = {'—'}


class CosmosGuiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Cosmos Wallet')
        self.geometry('1280x720')
        self.minsize(960, 600)
        self._log_panel_attached = False
        self._log_queue: queue.Queue = queue.Queue()
        self._main_callbacks: queue.Queue = queue.Queue()
        self._preview = None
        self._swap_preview = None
        self._tree_bulk_update = False
        self._current_route = None
        self._by_source = services.ibc_routes_grouped()
        self._muted_labels: list = []
        self._setup_canvas = None
        self._balance_fetch_in_progress = False
        self._last_balance_fetch = 0.0
        self._portfolio_assets: dict = {}
        self._last_nav = 'Portfolio'
        self.settings = load_settings()
        self.style = ttk.Style(self)
        theme_id = self.settings.get('theme', DEFAULT_THEME)
        self.colors = apply_theme(self, self.style, theme_id, self.settings)

        self._build_layout()
        style_text_widget(self.log_text, self.colors)
        self._build_portfolio_tab()
        self._build_transfer_tab()
        self._build_swap_tab()
        self._build_receive_tab()
        self._build_history_tab()
        self._build_networks_tab()
        self._build_tokens_tab()
        self._build_denoms_tab()
        self._build_addresses_tab()
        self._build_osmosis_tab()
        self._build_setup_tab()
        self._build_settings_tab()
        self._build_status_tab()
        self.after(100, self._poll_log_queue)
        self.after(50, self._poll_main_callbacks)
        self.refresh_status()
        self.after(800, self._schedule_balance_refresh)
        self.protocol('WM_DELETE_WINDOW', self._on_app_close)

    def _on_app_close(self):
        if hasattr(self, 'osmo_tree'):
            self._save_market_tree_layout()
        self.destroy()

    def _build_layout(self):
        outer = ttk.Frame(self, padding=(10, 8))
        outer.pack(fill=tk.BOTH, expand=True)

        self._main_paned = ttk.Panedwindow(outer, orient=tk.HORIZONTAL)
        self._main_paned.pack(fill=tk.BOTH, expand=True)

        content_shell = ttk.Frame(self._main_paned)
        self._main_paned.add(content_shell, weight=4)

        content = ttk.Frame(content_shell, padding=(4, 0))
        content.pack(fill=tk.BOTH, expand=True)

        body = ttk.Frame(content)
        body.pack(fill=tk.BOTH, expand=True)

        nav_side = ttk.Frame(body, width=168)
        nav_side.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 12))
        nav_side.pack_propagate(False)
        ttk.Label(nav_side, text='Cosmos Wallet', font=('', 11, 'bold')).pack(anchor=tk.W, pady=(0, 8))

        nav_list_frame = ttk.Frame(nav_side)
        nav_list_frame.pack(fill=tk.BOTH, expand=True)
        nav_scroll = ttk.Scrollbar(nav_list_frame, orient=tk.VERTICAL)
        self.nav_list = tk.Listbox(
            nav_list_frame,
            exportselection=False,
            yscrollcommand=nav_scroll.set,
            width=20,
            height=len(NAV_LABELS),
        )
        nav_scroll.config(command=self.nav_list.yview)
        self.nav_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        nav_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        style_listbox(self.nav_list, self.colors)
        for label in NAV_LABELS:
            self.nav_list.insert(tk.END, label)
        self.nav_list.selection_set(0)
        self.nav_list.bind('<<ListboxSelect>>', self._on_nav_selected)

        self._page_stack = ttk.Frame(body)
        self._page_stack.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tab_portfolio = ttk.Frame(self._page_stack, padding=12)
        self.tab_transfer = ttk.Frame(self._page_stack, padding=12)
        self.tab_swap = ttk.Frame(self._page_stack, padding=12)
        self.tab_receive = ttk.Frame(self._page_stack, padding=12)
        self.tab_history = ttk.Frame(self._page_stack, padding=12)
        self.tab_networks = ttk.Frame(self._page_stack, padding=12)
        self.tab_tokens = ttk.Frame(self._page_stack, padding=12)
        self.tab_denoms = ttk.Frame(self._page_stack, padding=12)
        self.tab_addresses = ttk.Frame(self._page_stack, padding=12)
        self.tab_osmosis = ttk.Frame(self._page_stack, padding=12)
        self.tab_setup = ttk.Frame(self._page_stack, padding=12)
        self.tab_settings = ttk.Frame(self._page_stack, padding=12)
        self.tab_status = ttk.Frame(self._page_stack, padding=12)

        self._page_by_label = {
            'Portfolio': self.tab_portfolio,
            'Send': self.tab_transfer,
            'Swap': self.tab_swap,
            'Receive': self.tab_receive,
            'History': self.tab_history,
            'Networks': self.tab_networks,
            'Tokens': self.tab_tokens,
            'Denoms': self.tab_denoms,
            'Market': self.tab_osmosis,
            'Address book': self.tab_addresses,
            'Setup': self.tab_setup,
            'Settings': self.tab_settings,
            'Status': self.tab_status,
        }
        self._show_nav_page(NAV_LABELS[0])

        self._log_panel = ttk.Frame(self._main_paned, padding=(8, 0))
        log_toolbar = ttk.Frame(self._log_panel)
        log_toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(log_toolbar, text='Log', font=('', 10, 'bold')).pack(side=tk.LEFT)
        ttk.Button(log_toolbar, text='Clear', command=self._clear_log, width=8).pack(side=tk.RIGHT)

        self.log_text = scrolledtext.ScrolledText(
            self._log_panel,
            width=48,
            state=tk.DISABLED,
            wrap=tk.WORD,
            borderwidth=0,
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self._apply_log_panel_visibility()

    def _clear_log(self):
        self.log_text.configure(state=tk.NORMAL)
        self.log_text.delete('1.0', tk.END)
        self.log_text.configure(state=tk.DISABLED)

    def _go_nav(self, label: str):
        if label in NAV_SEPARATORS or label not in self._page_by_label:
            return
        self._show_nav_page(label)

    def _on_nav_selected(self, _event=None):
        selection = self.nav_list.curselection()
        if not selection:
            return
        label = self.nav_list.get(selection[0])
        if label in NAV_SEPARATORS:
            prev = self._last_nav if self._last_nav in self._page_by_label else 'Portfolio'
            idx = NAV_LABELS.index(prev)
            self.nav_list.selection_clear(0, tk.END)
            self.nav_list.selection_set(idx)
            return
        self._last_nav = label
        self._show_nav_page(label)
        if label in ('Portfolio', 'Send'):
            self._refresh_wallet_balances(quiet=True)
        elif label == 'Receive':
            self._load_receive_addresses()
        elif label == 'Networks':
            self._refresh_networks_table()
        elif label == 'Tokens':
            self._refresh_tokens_chain_filter()
            if not self._token_rows:
                self._try_restore_tokens_cache()
            self._maybe_auto_refresh_tokens()
        elif label == 'Market':
            if not self._osmo_rows:
                self._try_restore_market_cache()
            self._maybe_auto_refresh_market()
        elif label == 'Denoms':
            self._refresh_denoms_table()
        elif label == 'Address book':
            self._load_addresses()

    def _show_nav_page(self, label: str):
        frame = self._page_by_label.get(label)
        if frame is None:
            return
        if hasattr(self, 'nav_list'):
            try:
                index = NAV_LABELS.index(label)
            except ValueError:
                pass
            else:
                self.nav_list.selection_clear(0, tk.END)
                self.nav_list.selection_set(index)
                self.nav_list.see(index)
        for child in self._page_stack.winfo_children():
            child.pack_forget()
        frame.pack(fill=tk.BOTH, expand=True)
        if label == 'History':
            self._refresh_history_table()

    def _apply_log_panel_visibility(self):
        show = bool(self.settings.get('show_log_panel', True))
        if show and not self._log_panel_attached:
            self._main_paned.add(self._log_panel, weight=1)
            self._log_panel_attached = True
            self.update_idletasks()
            try:
                width = max(self.winfo_width(), 960)
                self._main_paned.sashpos(0, int(width * 0.68))
            except tk.TclError:
                pass
        elif not show and self._log_panel_attached:
            self._main_paned.forget(self._log_panel)
            self._log_panel_attached = False

    def _on_log_panel_toggle(self):
        self.settings['show_log_panel'] = self.var_show_log.get()
        save_settings(self.settings)
        self._apply_log_panel_visibility()

    def log(self, message: str):
        self._log_queue.put(message)

    def _poll_log_queue(self):
        while True:
            try:
                chunk = self._log_queue.get_nowait()
            except queue.Empty:
                break
            self.log_text.configure(state=tk.NORMAL)
            self.log_text.insert(tk.END, chunk)
            if not chunk.endswith('\n'):
                self.log_text.insert(tk.END, '\n')
            self.log_text.see(tk.END)
            self.log_text.configure(state=tk.DISABLED)
        self.after(100, self._poll_log_queue)

    def _run_on_main(self, callback) -> None:
        """Schedule UI work on the Tk main thread (safe from background threads)."""
        self._main_callbacks.put(callback)

    def _poll_main_callbacks(self):
        while True:
            try:
                callback = self._main_callbacks.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except tk.TclError:
                pass
        try:
            self.after(50, self._poll_main_callbacks)
        except RuntimeError:
            pass

    def _run_async(self, label: str, worker, on_success=None, on_error=None):
        self.log(f'[{label}] started…')

        def task():
            try:
                result = worker()
            except Exception as exc:
                def fail(err=exc):
                    if on_error:
                        on_error(err)
                    else:
                        self._async_error(label, err)

                self._run_on_main(fail)
                return

            def done():
                self.log(f'[{label}] finished.')
                if on_success:
                    on_success(result)

            self._run_on_main(done)

        threading.Thread(target=task, daemon=True).start()

    def _async_error(self, label: str, exc: Exception):
        self.log(f'[{label}] error: {exc}')
        messagebox.showerror(label, str(exc))

    def _muted_label(self, parent, *, track: bool = True, **kwargs):
        """Muted helper text. Use track=False for short-lived dialogs (Toplevel)."""
        label = ttk.Label(parent, foreground=self.colors.muted, **kwargs)
        if track:
            self._muted_labels.append(label)
        return label

    def _treeview_focus_item(self, tree, *, last_item_attr: str = '') -> Optional[str]:
        """Selected row, last remembered row, or focused row (for toolbar Copy on Linux)."""
        sel = tree.selection()
        if sel:
            return sel[0]
        if last_item_attr:
            remembered = getattr(self, last_item_attr, None)
            if remembered and tree.exists(remembered):
                return remembered
        focus = tree.focus()
        return focus if focus else None

    def _remember_tree_row(self, tree, last_item_attr: str, event=None) -> None:
        if getattr(self, '_tree_bulk_update', False):
            return
        item = None
        if event is not None:
            try:
                item = tree.identify_row(event.y)
            except tk.TclError:
                item = None
        if not item:
            sel = tree.selection()
            if sel:
                item = sel[0]
        if not item:
            return
        setattr(self, last_item_attr, item)
        # Do not re-select on <<TreeviewSelect>> — selection_set() can recurse and freeze the UI.
        if event is not None:
            cur = tree.selection()
            if not cur or cur[0] != item:
                tree.selection_set(item)
            if tree.focus() != item:
                tree.focus(item)

    def _treeview_column_value(self, tree, item: str, column_index: int) -> str:
        values = tree.item(item, 'values')
        if len(values) > column_index:
            return str(values[column_index] or '').strip()
        return ''

    def _copy_text_to_clipboard(self, text: str) -> None:
        if not copy_to_clipboard(self, text):
            messagebox.showwarning('Clipboard', 'Could not copy to clipboard.')

    def _apply_theme(self, theme_name: Optional[str] = None) -> None:
        theme_name = theme_name or self.settings.get('theme', DEFAULT_THEME)
        self.colors = apply_theme(self, self.style, theme_name, self.settings)
        if hasattr(self, 'log_text'):
            style_text_widget(self.log_text, self.colors)
        if hasattr(self, 'nav_list'):
            style_listbox(self.nav_list, self.colors)
        if hasattr(self, '_picker_source'):
            style_listbox(self._picker_source.listbox, self.colors)
        if hasattr(self, '_picker_dest'):
            style_listbox(self._picker_dest.listbox, self.colors)
        if self._setup_canvas is not None:
            style_canvas(self._setup_canvas, self.colors)
        alive: list = []
        for label in self._muted_labels:
            try:
                if label.winfo_exists():
                    label.configure(foreground=self.colors.muted)
                    alive.append(label)
            except tk.TclError:
                pass
        self._muted_labels = alive
        self.refresh_status()

    def refresh_status(self):
        status = services.get_setup_status()
        lines = [
            ('Source directory', status.source_dir),
            ('Secret vault (KDBX)', status.secret_vault),
            ('Unlock files on disk', status.secret_unlock_files),
            ('cosmos_data_list.json', status.cosmos_data),
            ('ledger_clients.py', status.ledger_clients),
            ('wallets_list.py', status.wallets_list),
            ('address_book.json', status.address_book),
            ('client mapping', status.client_mapping),
        ]
        for label, ok in lines:
            widget = self._status_labels.get(label)
            if widget:
                widget.configure(
                    text='OK' if ok else 'missing',
                    foreground=self.colors.success if ok else self.colors.error,
                )

        if status.ready_for_transfer:
            self.transfer_hint.configure(
                text='Ready for IBC transfers.',
                foreground=self.colors.success,
            )
        else:
            self.transfer_hint.configure(
                text='Complete Setup (secret vault, unlock files, clients, address book) before transferring.',
                foreground=self.colors.warning,
            )

    def _build_status_tab(self):
        ttk.Label(
            self.tab_status,
            text='Environment status',
            font=('', 12, 'bold'),
        ).pack(anchor=tk.W)

        ttk.Label(
            self.tab_status,
            text='CLI: python menu_crypto.py  |  GUI: python gui_crypto.py',
        ).pack(anchor=tk.W, pady=(4, 12))

        frame = ttk.LabelFrame(self.tab_status, text='Environment', padding=8)
        frame.pack(fill=tk.X, anchor=tk.W)

        self._status_labels = {}
        status = services.get_setup_status()
        ttk.Label(
            self.tab_status,
            text=f'Secrets folder: {status.secrets_path}',
            wraplength=700,
        ).pack(anchor=tk.W, pady=(0, 8))
        items = [
            ('Source directory', status.source_dir),
            ('Secret vault (KDBX)', status.secret_vault),
            ('Unlock files on disk', status.secret_unlock_files),
            ('cosmos_data_list.json', status.cosmos_data),
            ('ledger_clients.py', status.ledger_clients),
            ('wallets_list.py', status.wallets_list),
            ('address_book.json', status.address_book),
            ('client mapping', status.client_mapping),
        ]
        for row, (label, ok) in enumerate(items):
            ttk.Label(frame, text=label + ':').grid(row=row, column=0, sticky=tk.W, padx=(0, 8), pady=2)
            value = ttk.Label(frame, text='OK' if ok else 'missing')
            value.grid(row=row, column=1, sticky=tk.W, pady=2)
            value.configure(foreground=self.colors.success if ok else self.colors.error)
            self._status_labels[label] = value

        self.transfer_hint = ttk.Label(self.tab_status, text='')
        self.transfer_hint.pack(anchor=tk.W, pady=12)

        ttk.Button(self.tab_status, text='Refresh status', command=self.refresh_status).pack(anchor=tk.W)

    def _can_fetch_balances(self) -> bool:
        status = services.get_setup_status()
        return bool(
            status.ledger_clients
            and status.address_book
            and status.client_mapping
        )

    def _schedule_balance_refresh(self):
        if self.settings.get('auto_refresh_balances', True) and self._can_fetch_balances():
            self._refresh_wallet_balances(quiet=True)
        interval_ms = max(15, int(self.settings.get('balance_refresh_seconds', 60))) * 1000
        self.after(interval_ms, self._schedule_balance_refresh)

    def _apply_balance_rows(self, rows, missed):
        enabled = services.get_wallet_networks()
        if enabled:
            rows = [r for r in rows if getattr(r, 'network', None) in enabled]
        from project_utils.wallet_profiles import row_belongs_to_active_wallet

        rows = [r for r in rows if row_belongs_to_active_wallet(r.wallet_name)]
        if hasattr(self, 'lbl_portfolio_status'):
            try:
                from gui.wallet_views import balance_rows_to_assets
                from project_utils.token_catalog import get_token_catalog

                catalog = get_token_catalog()
                chain_rest = services.chain_rest_urls()
                usd_prices = {}
                if self.settings.get('show_fiat_prices', True):
                    from project_utils.coingecko_prices import fetch_usd_prices

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
            except Exception:
                assets, total_usd = [], 0.0
            if hasattr(self, 'portfolio_tree'):
                for item in self.portfolio_tree.get_children():
                    self.portfolio_tree.delete(item)
                self._portfolio_assets = {}
                for asset in assets:
                    iid = self.portfolio_tree.insert(
                        '',
                        tk.END,
                        values=(
                            asset.get('symbol', ''),
                            asset.get('network', ''),
                            asset.get('amount', ''),
                            asset.get('usd', ''),
                        ),
                    )
                    self._portfolio_assets[iid] = asset
            if total_usd > 0:
                self.lbl_portfolio_total.configure(text=f'≈ ${total_usd:,.2f} USD')
            else:
                self.lbl_portfolio_total.configure(text='Portfolio (enable fiat in Settings for USD)')
            self._refresh_portfolio_wallet_header()
            self.lbl_portfolio_status.configure(text='')
        if missed:
            self.log('Networks without client: ' + ', '.join(missed))

    def _refresh_wallet_balances(self, quiet: bool = False, force: bool = False):
        if self._balance_fetch_in_progress or not self._can_fetch_balances():
            return

        def worker():
            return services.fetch_balances(force=force)

        def on_success(result):
            rows, missed = result
            self._apply_balance_rows(rows, missed)
            self._last_balance_fetch = time.time()
            self._balance_fetch_in_progress = False

        def on_error(label, exc):
            self._balance_fetch_in_progress = False
            if not quiet:
                self._async_error(label, exc)

        self._balance_fetch_in_progress = True
        if not quiet:
            self.log('[Balances] started…')

        def task():
            try:
                result = worker()
            except Exception as exc:
                self._run_on_main(lambda err=exc: on_error('Balances', err))
                return

            def done():
                if not quiet:
                    self.log('[Balances] finished.')
                on_success(result)

            self._run_on_main(done)

        threading.Thread(target=task, daemon=True).start()

    def _build_portfolio_tab(self):
        header = ttk.Frame(self.tab_portfolio)
        header.pack(fill=tk.X, pady=(0, 8))
        self.lbl_portfolio_total = ttk.Label(header, text='Portfolio', font=('', 16, 'bold'))
        self.lbl_portfolio_total.pack(side=tk.LEFT)
        ttk.Button(header, text='Refresh', command=lambda: self._refresh_wallet_balances(force=True)).pack(
            side=tk.RIGHT, padx=4,
        )
        ttk.Button(header, text='Send', command=lambda: self._go_nav('Send')).pack(side=tk.RIGHT, padx=4)
        ttk.Button(header, text='Receive', command=lambda: self._go_nav('Receive')).pack(side=tk.RIGHT)

        wallet_row = ttk.Frame(self.tab_portfolio)
        wallet_row.pack(fill=tk.X, pady=(0, 6))
        self.lbl_portfolio_wallet = ttk.Label(wallet_row, text='Wallet: —', font=('', 10, 'bold'))
        self.lbl_portfolio_wallet.pack(side=tk.LEFT)
        ttk.Button(wallet_row, text='Rename', command=self._portfolio_rename_wallet).pack(
            side=tk.LEFT, padx=(10, 4),
        )
        ttk.Button(wallet_row, text='New wallet…', command=self._portfolio_create_wallet).pack(
            side=tk.LEFT, padx=(0, 4),
        )
        ttk.Button(wallet_row, text='Manage wallets…', command=self._portfolio_manage_wallets).pack(
            side=tk.LEFT,
        )

        self.lbl_portfolio_status = self._muted_label(self.tab_portfolio, text='')
        self.lbl_portfolio_status.pack(anchor=tk.W, pady=(0, 4))
        self._refresh_portfolio_wallet_header()

        portfolio_toolbar = ttk.Frame(self.tab_portfolio)
        portfolio_toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(
            portfolio_toolbar,
            text='Name token…',
            command=self._map_portfolio_token,
        ).pack(side=tk.LEFT)
        self._muted_label(
            portfolio_toolbar,
            text='Select a row with an unknown IBC token, then assign a symbol (e.g. OSMO).',
            wraplength=700,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self._portfolio_assets: dict = {}

        cols = ('symbol', 'network', 'amount', 'usd')
        self.portfolio_tree = ttk.Treeview(self.tab_portfolio, columns=cols, show='headings', height=16)
        for col, title, width in [
            ('symbol', 'Asset', 100),
            ('network', 'Network', 120),
            ('amount', 'Balance', 220),
            ('usd', '≈ USD', 100),
        ]:
            self.portfolio_tree.heading(col, text=title)
            self.portfolio_tree.column(col, width=width, stretch=col == 'amount')
        scroll = ttk.Scrollbar(self.tab_portfolio, orient=tk.VERTICAL, command=self.portfolio_tree.yview)
        self.portfolio_tree.configure(yscrollcommand=scroll.set)
        self.portfolio_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _refresh_portfolio_wallet_header(self):
        if not hasattr(self, 'lbl_portfolio_wallet'):
            return
        wid, label = services.active_wallet_display()
        self.lbl_portfolio_wallet.configure(text=f'Wallet: {label}  ({wid})')

    def _portfolio_create_wallet(self):
        from gui.wallet_dialog import show_create_wallet_dialog

        new_id = show_create_wallet_dialog(self)
        if new_id:
            self.log(f'Created / activated wallet {new_id}')
            self._on_wallet_context_changed()

    def _on_wallet_context_changed(self):
        """Refresh all wallet-dependent UI after create or switch."""
        self._refresh_portfolio_wallet_header()
        self.refresh_status()
        self._refresh_wallet_balances(quiet=False)
        if hasattr(self, 'addr_tree'):
            self._load_addresses()
        if hasattr(self, 'receive_tree'):
            self._load_receive_addresses()
        if self._last_nav == 'Send' and hasattr(self, 'var_source'):
            self._on_source_changed()
            self._refresh_send_balances()

    def _portfolio_rename_wallet(self):
        from project_utils.wallet_profiles import get_active_wallet_id, rename_wallet

        wid = get_active_wallet_id()
        _, current = services.active_wallet_display()
        dialog = tk.Toplevel(self)
        dialog.title('Rename wallet')
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text=f'Display name for {wid}:').pack(anchor=tk.W, padx=12, pady=(12, 4))
        name_var = tk.StringVar(value=current)
        ttk.Entry(dialog, textvariable=name_var, width=32).pack(padx=12, pady=(0, 8))

        def save():
            try:
                rename_wallet(wid, name_var.get())
            except Exception as exc:
                messagebox.showerror('Rename wallet', str(exc), parent=dialog)
                return
            dialog.destroy()
            self._refresh_portfolio_wallet_header()
            self.log(f'Wallet renamed: {name_var.get().strip()}')

        btn_row = ttk.Frame(dialog)
        btn_row.pack(pady=12)
        ttk.Button(btn_row, text='Save', command=save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text='Cancel', command=dialog.destroy).pack(side=tk.LEFT, padx=6)

    def _portfolio_manage_wallets(self):
        from project_utils.wallet_profiles import (
            list_wallet_profiles,
            rename_wallet,
            set_active_wallet,
        )

        dialog = tk.Toplevel(self)
        dialog.title('Wallets')
        dialog.transient(self)
        dialog.geometry('420x320')
        dialog.grab_set()

        ttk.Label(
            dialog,
            text='Each wallet has its own mnemonic in the KeePass vault. The active wallet is used for Send and Portfolio.',
            wraplength=380,
        ).pack(anchor=tk.W, padx=12, pady=(12, 8))

        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        lb = tk.Listbox(list_frame, height=8, yscrollcommand=scroll.set, exportselection=False)
        scroll.config(command=lb.yview)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def refresh_list(select_id=None):
            lb.delete(0, tk.END)
            profiles = list_wallet_profiles()
            select_idx = 0
            for i, p in enumerate(profiles):
                mark = '● ' if p['active'] else '  '
                lb.insert(tk.END, f"{mark}{p['label']}  ({p['id']})")
                if select_id and p['id'] == select_id:
                    select_idx = i
                elif p['active'] and select_id is None:
                    select_idx = i
            lb.selection_set(select_idx)
            lb.see(select_idx)

        refresh_list()

        def selected_profile():
            sel = lb.curselection()
            if not sel:
                return None
            profiles = list_wallet_profiles()
            if sel[0] >= len(profiles):
                return None
            return profiles[sel[0]]

        def on_use():
            p = selected_profile()
            if not p:
                return
            try:
                services.activate_wallet(p['id'])
            except Exception as exc:
                messagebox.showerror('Wallets', str(exc), parent=dialog)
                return
            self._on_wallet_context_changed()
            refresh_list(p['id'])

        def on_rename():
            p = selected_profile()
            if not p:
                return
            name = simpledialog.askstring(
                'Rename wallet',
                f"Name for {p['id']}:",
                initialvalue=p['label'],
                parent=dialog,
            )
            if not name:
                return
            try:
                rename_wallet(p['id'], name)
            except Exception as exc:
                messagebox.showerror('Wallets', str(exc), parent=dialog)
                return
            refresh_list(p['id'])
            self._refresh_portfolio_wallet_header()

        def on_create():
            from gui.wallet_dialog import show_create_wallet_dialog

            dialog.withdraw()
            try:
                new_id = show_create_wallet_dialog(self)
            finally:
                dialog.deiconify()
            if not new_id:
                return
            self.log(f'Created wallet {new_id}')
            self._on_wallet_context_changed()
            refresh_list(new_id)

        def on_delete():
            p = selected_profile()
            if not p:
                return
            if not messagebox.askyesno(
                'Delete wallet',
                f"Remove profile “{p['label']}” ({p['id']})?",
                parent=dialog,
            ):
                return
            try:
                services.delete_wallet_full(p['id'])
            except Exception as exc:
                messagebox.showerror('Wallets', str(exc), parent=dialog)
                return
            self.log(f'Deleted wallet {p["id"]}')
            self._on_wallet_context_changed()
            refresh_list()

        btn_row = ttk.Frame(dialog)
        btn_row.pack(fill=tk.X, padx=12, pady=12)
        ttk.Button(btn_row, text='Use', command=on_use).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text='Rename', command=on_rename).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text='New', command=on_create).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text='Delete', command=on_delete).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_row, text='Close', command=dialog.destroy).pack(side=tk.RIGHT, padx=2)

    def _map_portfolio_token(self):
        if not hasattr(self, 'portfolio_tree'):
            return
        sel = self.portfolio_tree.selection()
        if not sel:
            messagebox.showinfo(
                'Name token',
                'Select an asset row in the table first.',
                parent=self,
            )
            return
        asset = getattr(self, '_portfolio_assets', {}).get(sel[0])
        if not asset:
            messagebox.showinfo('Name token', 'No asset data for this row.', parent=self)
            return
        network = asset.get('network', '')
        denom = asset.get('denom', '')
        if not network or not denom:
            messagebox.showinfo('Name token', 'This row has no on-chain denom.', parent=self)
            return

        dialog = tk.Toplevel(self)
        dialog.title('Name token')
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text=f'Network: {network}', font=('', 10, 'bold')).pack(
            anchor=tk.W, padx=12, pady=(12, 4),
        )
        ttk.Label(dialog, text='On-chain denom (token address):').pack(anchor=tk.W, padx=12)
        denom_var = tk.StringVar(value=denom)
        ttk.Label(dialog, textvariable=denom_var, wraplength=520).pack(
            padx=12, pady=(0, 8), anchor=tk.W,
        )

        ttk.Label(dialog, text='Your name for this token (e.g. OSMO):').pack(anchor=tk.W, padx=12)
        symbol_var = tk.StringVar(value='')
        current_sym = asset.get('symbol', '')
        if current_sym and not str(current_sym).upper().startswith('IBC'):
            symbol_var.set(str(current_sym))
        ttk.Entry(dialog, textvariable=symbol_var, width=24).pack(padx=12, pady=(0, 8), anchor=tk.W)

        ttk.Label(dialog, text='Decimals:').pack(anchor=tk.W, padx=12)
        decimals_var = tk.StringVar(value='6')
        ttk.Entry(dialog, textvariable=decimals_var, width=8).pack(padx=12, pady=(0, 8), anchor=tk.W)

        self._muted_label(
            dialog,
            text='Saved to addresses/denoms/denoms_book.json (edit all mappings on Denoms tab).',
            wraplength=480,
            track=False,
        ).pack(anchor=tk.W, padx=12, pady=(0, 8))

        def save():
            sym = symbol_var.get().strip()
            if not sym:
                messagebox.showerror('Name token', 'Enter a symbol.', parent=dialog)
                return
            try:
                dec = int(decimals_var.get().strip())
            except ValueError:
                messagebox.showerror('Name token', 'Decimals must be a whole number.', parent=dialog)
                return
            if dec < 0 or dec > 18:
                messagebox.showerror('Name token', 'Decimals must be between 0 and 18.', parent=dialog)
                return
            try:
                services.add_user_token_mapping(
                    network,
                    denom_var.get().strip(),
                    sym,
                    decimals=dec,
                )
            except Exception as exc:
                messagebox.showerror('Name token', str(exc), parent=dialog)
                return
            dialog.destroy()
            self.log(f'Named token on {network}: {sym} → {denom_var.get().strip()[:48]}…')
            self._refresh_wallet_balances(quiet=True)
            messagebox.showinfo(
                'Name token',
                f'Mapping saved: {sym} on {network}.\n\n'
                'Portfolio refreshed; you can use this symbol on Send.',
                parent=self,
            )

        btn_row = ttk.Frame(dialog)
        btn_row.pack(pady=12)
        ttk.Button(btn_row, text='Save', command=save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text='Cancel', command=dialog.destroy).pack(side=tk.LEFT, padx=6)

    def _build_receive_tab(self):
        ttk.Label(
            self.tab_receive,
            text='Receive — your deposit addresses (derived from vault mnemonic)',
            font=('', 11, 'bold'),
        ).pack(anchor=tk.W, pady=(0, 8))
        self._muted_label(
            self.tab_receive,
            text='Enabled networks only. Enable on Networks (✓), then Update address book if the chain is new.',
            wraplength=900,
        ).pack(anchor=tk.W, pady=(0, 8))

        toolbar = ttk.Frame(self.tab_receive)
        toolbar.pack(fill=tk.X)
        self.var_receive_filter = tk.StringVar()
        self.var_receive_filter.trace_add('write', lambda *_a: self._filter_receive_addresses())
        self.var_receive_all_wallets = tk.BooleanVar(
            value=bool(self.settings.get('receive_all_wallets', False)),
        )
        ttk.Label(toolbar, text='Filter:').pack(side=tk.LEFT)
        ttk.Entry(toolbar, textvariable=self.var_receive_filter, width=24).pack(side=tk.LEFT, padx=6)
        recv_wallet_scope = ttk.Frame(toolbar)
        recv_wallet_scope.pack(side=tk.LEFT, padx=(8, 6))
        ttk.Label(recv_wallet_scope, text='Wallets:').pack(side=tk.LEFT)
        ttk.Radiobutton(
            recv_wallet_scope,
            text='Active only',
            variable=self.var_receive_all_wallets,
            value=False,
            command=self._on_receive_wallet_scope_changed,
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Radiobutton(
            recv_wallet_scope,
            text='All wallets',
            variable=self.var_receive_all_wallets,
            value=True,
            command=self._on_receive_wallet_scope_changed,
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(toolbar, text='Reload', command=self._load_receive_addresses).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text='Copy address', command=self._copy_receive_address).pack(side=tk.LEFT)

        cols = ('network', 'name', 'address')
        self.receive_tree = ttk.Treeview(self.tab_receive, columns=cols, show='headings', height=18)
        for col, title, width in [
            ('network', 'Network', 120),
            ('name', 'Wallet', 180),
            ('address', 'Address', 420),
        ]:
            self.receive_tree.heading(col, text=title)
            self.receive_tree.column(col, width=width, stretch=col == 'address')
        scroll = ttk.Scrollbar(self.tab_receive, orient=tk.VERTICAL, command=self.receive_tree.yview)
        self.receive_tree.configure(yscrollcommand=scroll.set)
        self.receive_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)
        self._receive_tree_last_item = None
        self.receive_tree.bind('<<TreeviewSelect>>', lambda _e: self._remember_tree_row(
            self.receive_tree, '_receive_tree_last_item',
        ))
        self.receive_tree.bind(
            '<ButtonRelease-1>',
            lambda e: self._remember_tree_row(self.receive_tree, '_receive_tree_last_item', e),
        )
        self.receive_tree.bind('<Double-1>', self._on_receive_double_click)
        self.receive_tree.bind('<Control-c>', lambda _e: self._copy_receive_address())

        self._receive_entries = []
        self.lbl_receive_scope = self._muted_label(self.tab_receive, text='')
        self.lbl_receive_scope.pack(anchor=tk.W, pady=(0, 4))
        self._load_receive_addresses()

    def _on_receive_wallet_scope_changed(self):
        if hasattr(self, 'var_receive_all_wallets'):
            self.settings['receive_all_wallets'] = bool(self.var_receive_all_wallets.get())
            save_settings(self.settings)
        self._load_receive_addresses()

    def _load_receive_addresses(self):
        if not hasattr(self, 'receive_tree'):
            return
        all_wallets = bool(self.var_receive_all_wallets.get()) if hasattr(self, 'var_receive_all_wallets') else False
        self._receive_entries = services.load_address_book_entries(all_wallets=all_wallets)
        if hasattr(self, 'lbl_receive_scope'):
            wid, label = services.active_wallet_display()
            if all_wallets:
                self.lbl_receive_scope.configure(
                    text=f'Showing all wallets ({len(self._receive_entries)} address(es), enabled networks).',
                )
            else:
                self.lbl_receive_scope.configure(
                    text=f'Active wallet: {label} ({wid}) — {len(self._receive_entries)} address(es).',
                )
        self._filter_receive_addresses()

    def _filter_receive_addresses(self):
        if not hasattr(self, 'receive_tree'):
            return
        needle = ''
        if hasattr(self, 'var_receive_filter'):
            needle = self.var_receive_filter.get().strip().lower()
        rows = []
        for idx, entry in enumerate(getattr(self, '_receive_entries', [])):
            hay = f'{entry.get("name", "")} {entry.get("network", "")} {entry.get("address", "")}'.lower()
            if needle and needle not in hay:
                continue
            addr = entry.get('address', '')
            network = entry.get('network', '')
            rows.append((f'rcv-{idx}', (network, entry.get('name', ''), addr)))
        self._tree_bulk_update = True
        try:
            children = self.receive_tree.get_children()
            if children:
                self.receive_tree.delete(*children)
            for iid, values in rows:
                self.receive_tree.insert('', tk.END, iid=iid, values=values)
        finally:
            self._tree_bulk_update = False

    def _on_receive_double_click(self, event):
        self._remember_tree_row(self.receive_tree, '_receive_tree_last_item', event)
        self._copy_receive_address()

    def _copy_receive_address(self):
        if not hasattr(self, 'receive_tree'):
            return
        item = self._treeview_focus_item(
            self.receive_tree, last_item_attr='_receive_tree_last_item',
        )
        if not item:
            messagebox.showinfo('Receive', 'Select an address row first.')
            return
        address = self._treeview_column_value(self.receive_tree, item, 2)
        if not address:
            messagebox.showinfo('Receive', 'No address in this row.')
            return
        self._copy_text_to_clipboard(address)
        self.log(f'Copied address: {address}')

    def _build_transfer_tab(self):
        ttk.Label(self.tab_transfer, text='Send — IBC transfer', font=('', 11, 'bold')).pack(
            anchor=tk.W, pady=(0, 8),
        )
        self._muted_label(
            self.tab_transfer,
            text=(
                'Click a network in the From / To lists. Routes are built from chain-registry '
                '_IBC when you enable networks (see source/data/generated_ibc_routes.json). '
                'Manual overrides stay in config/ibc_routes.json.'
            ),
            wraplength=900,
        ).pack(anchor=tk.W, pady=(0, 8))

        form = ttk.Frame(self.tab_transfer)
        form.pack(fill=tk.X, anchor=tk.W)

        sources = sorted(self._by_source.keys())
        default_from = 'osmosis' if 'osmosis' in sources else (sources[0] if sources else '')
        self.var_source = tk.StringVar(value=default_from)
        self.var_dest = tk.StringVar()
        self.var_symbol = tk.StringVar(value='')
        self.var_amount = tk.StringVar(value='0.01')
        self._send_max_amount = 0.0
        self._send_balance_fetch_in_progress = False

        ttk.Label(form, text='From').grid(row=0, column=0, sticky=tk.NW, padx=4, pady=4)
        src_row = ttk.Frame(form)
        src_row.grid(row=0, column=1, sticky=tk.W, padx=4, pady=4)
        self._picker_source = NetworkListPicker(
            src_row,
            self.var_source,
            lambda: sorted(self._by_source.keys()),
            on_change=self._on_source_changed,
            height=5,
            width=24,
        )
        ttk.Button(src_row, text='⇄ Reverse', command=self._swap_send_direction, width=10).pack(
            side=tk.LEFT, padx=(8, 0),
        )

        ttk.Label(form, text='To').grid(row=1, column=0, sticky=tk.NW, padx=4, pady=4)
        dest_cell = ttk.Frame(form)
        dest_cell.grid(row=1, column=1, sticky=tk.W, padx=4, pady=4)
        self._picker_dest = NetworkListPicker(
            dest_cell,
            self.var_dest,
            lambda: self._destinations_for_source(self.var_source.get().strip()),
            on_change=self._on_dest_changed,
            height=5,
            width=24,
        )

        ttk.Label(form, text='Token').grid(row=2, column=0, sticky=tk.NW, padx=4, pady=4)
        token_cell = ttk.Frame(form)
        token_cell.grid(row=2, column=1, sticky=tk.W, padx=4, pady=4)
        self.cmb_symbol = ttk.Combobox(token_cell, textvariable=self.var_symbol, width=56)
        self.cmb_symbol.pack(anchor=tk.W)
        self.lbl_send_token_denom = self._muted_label(token_cell, text='')
        self.lbl_send_token_denom.pack(anchor=tk.W, pady=(2, 0))
        token_mode_row = ttk.Frame(token_cell)
        token_mode_row.pack(anchor=tk.W, pady=(4, 0))
        self.var_send_token_list = tk.StringVar(
            value=self.settings.get('send_token_list_mode', 'nonzero'),
        )
        ttk.Radiobutton(
            token_mode_row,
            text='With balance on From',
            variable=self.var_send_token_list,
            value='nonzero',
            command=self._on_send_token_list_mode_changed,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            token_mode_row,
            text='All in catalog',
            variable=self.var_send_token_list,
            value='all',
            command=self._on_send_token_list_mode_changed,
        ).pack(side=tk.LEFT, padx=(10, 0))

        self.lbl_send_sender_balance = self._muted_label(form, text='From: —')
        self.lbl_send_sender_balance.grid(row=3, column=1, sticky=tk.W, padx=4, pady=(0, 2))
        self.lbl_send_receiver_balance = self._muted_label(form, text='To: —')
        self.lbl_send_receiver_balance.grid(row=4, column=1, sticky=tk.W, padx=4, pady=(0, 6))

        ttk.Label(form, text='Amount').grid(row=5, column=0, sticky=tk.W, padx=4, pady=4)
        amount_row = ttk.Frame(form)
        amount_row.grid(row=5, column=1, sticky=tk.W, padx=4, pady=4)
        ttk.Entry(amount_row, textvariable=self.var_amount, width=22).pack(side=tk.LEFT)
        ttk.Button(amount_row, text='Max', width=6, command=self._send_fill_max_amount).pack(
            side=tk.LEFT, padx=(6, 0),
        )

        def _on_token_field_change():
            self._refresh_send_balances()
            self._update_send_token_denom_hint()

        self._refresh_symbol_combobox = bind_searchable_combobox(
            self.cmb_symbol,
            lambda: services.symbols_for_transfer_network(
                self.var_source.get().strip(),
                list_mode=self.var_send_token_list.get(),
            ),
            on_change=_on_token_field_change,
            textvariable=self.var_symbol,
        )

        self.lbl_send_direction = ttk.Label(self.tab_transfer, text='', font=('', 10, 'bold'))
        self.lbl_send_direction.pack(anchor=tk.W, pady=(4, 0))

        self.route_info = ttk.Label(self.tab_transfer, text='', wraplength=700)
        self.route_info.pack(anchor=tk.W, pady=8)

        gas_row = ttk.Frame(form)
        gas_row.grid(row=6, column=0, columnspan=2, sticky=tk.W, padx=4, pady=4)
        ttk.Label(gas_row, text='Gas limit').pack(side=tk.LEFT, padx=(0, 8))
        self.var_gas = tk.StringVar(value='250000')
        ttk.Entry(gas_row, textvariable=self.var_gas, width=12).pack(side=tk.LEFT)
        self.var_auto_gas = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            gas_row,
            text='Auto (+35% buffer)',
            variable=self.var_auto_gas,
            command=self._apply_route_gas_defaults,
        ).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Button(gas_row, text='Reset', width=7, command=self._apply_route_gas_defaults).pack(
            side=tk.LEFT, padx=(8, 0),
        )
        self.lbl_route_gas_hint = self._muted_label(form, text='')
        self.lbl_route_gas_hint.grid(row=7, column=1, sticky=tk.W, padx=4, pady=(0, 4))

        timeout_row = ttk.Frame(form)
        timeout_row.grid(row=8, column=0, columnspan=2, sticky=tk.W, padx=4, pady=4)
        ttk.Label(timeout_row, text='IBC timeout').pack(side=tk.LEFT, padx=(0, 8))
        self.var_timeout_mode = tk.StringVar(value='time')
        ttk.Radiobutton(
            timeout_row,
            text='By time (sec)',
            variable=self.var_timeout_mode,
            value='time',
            command=self._on_timeout_mode_changed,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            timeout_row,
            text='By block height',
            variable=self.var_timeout_mode,
            value='height',
            command=self._on_timeout_mode_changed,
        ).pack(side=tk.LEFT, padx=(8, 0))
        self.var_timeout_value = tk.StringVar(value='120')
        ttk.Entry(timeout_row, textvariable=self.var_timeout_value, width=8).pack(side=tk.LEFT, padx=(8, 0))
        self.lbl_timeout_hint = self._muted_label(form, text='Default: 120 seconds from broadcast time')
        self.lbl_timeout_hint.grid(row=9, column=1, sticky=tk.W, padx=4, pady=(0, 4))

        btn_row = ttk.Frame(self.tab_transfer)
        btn_row.pack(anchor=tk.W, pady=4)
        ttk.Button(
            btn_row,
            text='Preview transfer',
            command=lambda: self._preview_transfer(),
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.btn_send = ttk.Button(btn_row, text='Send (after preview)', command=self._send_transfer, state=tk.DISABLED)
        self.btn_send.pack(side=tk.LEFT)

        self._on_source_changed()
        self._update_transfer_symbols()

    def _send_fill_max_amount(self):
        if self._send_max_amount <= 0:
            messagebox.showinfo('Send', 'No spendable balance loaded for this token on the source network.')
            return
        text = f'{self._send_max_amount:.8f}'.rstrip('0').rstrip('.')
        self.var_amount.set(text or '0')

    def _refresh_send_balances(self):
        if not hasattr(self, 'lbl_send_sender_balance'):
            return
        if self._send_balance_fetch_in_progress:
            return
        src = self.var_source.get().strip()
        dst = self.var_dest.get().strip()
        raw_sym = self.var_symbol.get().strip()
        if not src or not raw_sym:
            self.lbl_send_sender_balance.configure(text='From: —')
            self.lbl_send_receiver_balance.configure(text='To: —')
            self._send_max_amount = 0.0
            return
        try:
            sym = services.resolve_transfer_symbol(src, raw_sym, self._send_token_list_mode())
        except ValueError:
            sym = raw_sym

        self.lbl_send_sender_balance.configure(text=f'From ({src}): loading…')
        self.lbl_send_receiver_balance.configure(
            text=f'To ({dst}): loading…' if dst else 'To: —',
        )

        def worker():
            return services.get_transfer_side_balances(src, dst, sym)

        def on_success(data: dict):
            self._send_balance_fetch_in_progress = False
            self.lbl_send_sender_balance.configure(text=data.get('sender_text', 'From: —'))
            self.lbl_send_receiver_balance.configure(text=data.get('receiver_text', 'To: —'))
            self._send_max_amount = float(data.get('sender_max', 0.0))

        def on_fail():
            self._send_balance_fetch_in_progress = False
            self.lbl_send_sender_balance.configure(text=f'From ({src}): balance unavailable')
            self.lbl_send_receiver_balance.configure(
                text=f'To ({dst}): balance unavailable' if dst else 'To: —',
            )
            self._send_max_amount = 0.0

        self._send_balance_fetch_in_progress = True

        def task():
            try:
                result = worker()
            except Exception:
                self._run_on_main(on_fail)
                return
            self._run_on_main(lambda r=result: on_success(r))

        threading.Thread(target=task, daemon=True).start()

    def _destinations_for_source(self, source: str):
        routes = self._by_source.get(source, [])
        return sorted({r['destination_network'] for r in routes})

    def _route_for_selection(self):
        return services.ibc_route_for(self.var_source.get(), self.var_dest.get())

    def _on_source_changed(self):
        if hasattr(self, '_picker_source'):
            self._picker_source.refresh()
        source = self.var_source.get().strip()
        sources = sorted(self._by_source.keys())
        if source not in sources and sources:
            fallback = 'osmosis' if 'osmosis' in sources else sources[0]
            self.var_source.set(fallback)
            source = fallback

        dests = self._destinations_for_source(source)
        if hasattr(self, '_picker_dest'):
            self._picker_dest.refresh()
        if dests:
            current_dest = self.var_dest.get().strip()
            if current_dest not in dests:
                prefer = 'cosmoshub' if 'cosmoshub' in dests else dests[0]
                self.var_dest.set(prefer)
        else:
            self.var_dest.set('')
        self._preview = None
        self.btn_send.configure(state=tk.DISABLED)
        self._update_transfer_symbols()
        self._update_route_info()
        self._refresh_send_balances()

    def _on_dest_changed(self):
        dests = self._destinations_for_source(self.var_source.get().strip())
        dest = self.var_dest.get().strip()
        if dests and dest not in dests:
            self.var_dest.set(dests[0])
        self._preview = None
        self.btn_send.configure(state=tk.DISABLED)
        self._update_route_info()
        self._refresh_send_balances()

    def _swap_send_direction(self):
        src = self.var_source.get().strip()
        dst = self.var_dest.get().strip()
        if not src or not dst:
            messagebox.showinfo('Send', 'Select both From and To networks first.')
            return
        sources = sorted(self._by_source.keys())
        if dst not in sources:
            messagebox.showwarning(
                'Send',
                f'Cannot reverse: “{dst}” is not an IBC source in your enabled networks.\n'
                f'Configured sources: {", ".join(sources)}.',
            )
            return
        new_dests = self._destinations_for_source(dst)
        if src not in new_dests:
            reverse = services.ibc_route_for(dst, src)
            hint = ''
            if reverse is None and services.ibc_route_for(src, dst):
                hint = f'\n\nOnly {src} → {dst} exists in ibc_routes.json (one-way).'
            messagebox.showwarning(
                'Send',
                f'No route {dst} → {src} for enabled networks.{hint}\n'
                'Pick From/To from the lists or add a route in config/ibc_routes.json.',
            )
            return
        self.var_source.set(dst)
        self.var_dest.set(src)
        if hasattr(self, '_picker_source'):
            self._picker_source.refresh()
        if hasattr(self, '_picker_dest'):
            self._picker_dest.refresh()
        self._update_transfer_symbols()
        self._update_route_info()
        self._refresh_send_balances()
        self.log(f'Send direction reversed: {dst} → {src}')

    def _update_send_direction_label(self):
        if not hasattr(self, 'lbl_send_direction'):
            return
        src = self.var_source.get().strip()
        dst = self.var_dest.get().strip()
        if src and dst:
            self.lbl_send_direction.configure(text=f'{src}  →  {dst}')
        else:
            self.lbl_send_direction.configure(text='')

    def _update_route_info(self):
        route = self._route_for_selection()
        self._current_route = route
        if not route:
            self._update_send_direction_label()
            self.route_info.configure(text='No route for this pair. Check config/ibc_routes.json.')
            return
        self._update_send_direction_label()
        self.route_info.configure(
            text=(
                f'channel {route["channel"]} | route gas {route["gas"]:,} | '
                f'wallets {route["sender_wallet"]} → {route["receiver_wallet"]}'
            )
        )
        self._apply_route_gas_defaults()
        self._apply_route_timeout_defaults()

    def _on_timeout_mode_changed(self):
        if not hasattr(self, 'lbl_timeout_hint'):
            return
        if self.var_timeout_mode.get() == 'height':
            self.lbl_timeout_hint.configure(
                text='Adds N blocks to latest height on destination (REST query at preview/send)',
            )
        else:
            self.lbl_timeout_hint.configure(text='Default: 120 seconds from broadcast time')

    def _apply_route_timeout_defaults(self):
        if not hasattr(self, 'var_timeout_value'):
            return
        route = self._route_for_selection()
        if not route:
            return
        if self.var_timeout_mode.get() == 'time':
            self.var_timeout_value.set(str(route.get('timeout_seconds', 120)))

    def _parse_timeout_settings(self):
        mode = self.var_timeout_mode.get().strip().lower()
        if mode not in ('time', 'height'):
            raise ValueError('Invalid timeout mode.')
        try:
            value = int(self.var_timeout_value.get().strip())
        except ValueError as exc:
            raise ValueError('Invalid timeout value — enter a whole number.') from exc
        if value < 1:
            raise ValueError('Timeout must be at least 1.')
        return mode, value

    def _apply_route_gas_defaults(self):
        if not hasattr(self, 'var_gas'):
            return
        route = self._route_for_selection()
        if not route:
            if hasattr(self, 'lbl_route_gas_hint'):
                self.lbl_route_gas_hint.configure(text='')
            return
        auto = bool(self.var_auto_gas.get()) if hasattr(self, 'var_auto_gas') else True
        suggested = services.recommended_gas_limit(route['gas'], auto_buffer=auto)
        if auto or not self.var_gas.get().strip():
            self.var_gas.set(str(suggested))
        if hasattr(self, 'lbl_route_gas_hint'):
            self.lbl_route_gas_hint.configure(
                text=f'Route default {route["gas"]:,} · using {self.var_gas.get()}'
                + (' (auto buffer)' if auto else ' (manual)'),
            )

    def _parse_gas_limit(self) -> int:
        route = self._current_route or {}
        fallback = services.recommended_gas_limit(route.get('gas', 200_000))
        try:
            value = int(self.var_gas.get().strip().replace(',', ''))
        except (ValueError, AttributeError):
            raise ValueError('Invalid gas limit — enter a whole number.') from None
        if value < 100_000:
            raise ValueError('Gas limit is too low (minimum 100000).')
        return value

    def _format_amount_for_display(self, amount: float) -> str:
        text = f'{amount:.8f}'.rstrip('0').rstrip('.')
        return text or '0'

    def _resolve_transfer_symbol(self) -> str:
        raw = self.var_symbol.get().strip()
        network = self.var_source.get().strip()
        return services.resolve_transfer_symbol(network, raw, list_mode=self._send_token_list_mode())

    def _update_send_token_denom_hint(self):
        if not hasattr(self, 'lbl_send_token_denom'):
            return
        network = self.var_source.get().strip()
        picked = self.var_symbol.get().strip()
        if not network or not picked:
            self.lbl_send_token_denom.configure(text='')
            return
        try:
            symbol = services.resolve_transfer_symbol(
                network, picked, list_mode=self._send_token_list_mode(),
            )
        except ValueError:
            self.lbl_send_token_denom.configure(text='')
            return
        for choice in services.transfer_token_choices(network, self._send_token_list_mode()):
            if choice['symbol'] == symbol:
                self.lbl_send_token_denom.configure(text=f'On-chain denom: {choice["denom"]}')
                return
        self.lbl_send_token_denom.configure(text='')

    def _parse_amount(self) -> float:
        try:
            return float(self.var_amount.get().strip())
        except ValueError as exc:
            raise ValueError('Invalid amount') from exc

    def _preview_transfer(self):
        route = self._route_for_selection()
        if not route:
            src = self.var_source.get().strip()
            dst = self.var_dest.get().strip()
            hint = ''
            if src and dst and services.ibc_route_for(dst, src) and not services.ibc_route_for(src, dst):
                hint = f'\n\nOnly {dst} → {src} is configured. Swap From and To in the lists.'
            messagebox.showwarning(
                'Transfer',
                f'No IBC route {src} → {dst} for your enabled networks.{hint}',
            )
            return
        try:
            amount = self._parse_amount()
            symbol = self._resolve_transfer_symbol()
        except ValueError as exc:
            messagebox.showerror('Transfer', str(exc))
            return

        source = self.var_source.get().strip()
        check = services.validate_transfer_sender(source, symbol, amount)
        if check:
            messagebox.showwarning('Transfer', check)
            return

        try:
            timeout_mode, timeout_value = self._parse_timeout_settings()
        except ValueError as exc:
            messagebox.showerror('Transfer', str(exc))
            return

        try:
            preview = services.gui_prepare_transfer(
                route,
                symbol,
                amount,
                timeout_mode=timeout_mode,
                timeout_value=timeout_value,
            )
        except Exception as exc:
            services.record_transfer_tx(
                status='failed',
                route=route,
                symbol=symbol,
                amount=str(amount),
                gas=route.get('gas', 0),
                error=str(exc),
                timeout_mode=timeout_mode,
                timeout_value=str(timeout_value),
            )
            self._refresh_history_table()
            messagebox.showerror('Preview failed', str(exc))
            return

        try:
            gas_limit = self._parse_gas_limit()
        except ValueError as exc:
            messagebox.showerror('Transfer', str(exc))
            return

        self._preview = preview
        self._preview_gas_limit = gas_limit
        self.btn_send.configure(state=tk.NORMAL)
        services.record_transfer_tx(status='preview', route=route, preview=preview, gas=gas_limit)
        self._refresh_history_table()
        body = '\n'.join(preview.summary_lines()) + f'\nGas limit: {gas_limit:,}'
        self.log('--- Transfer preview ---\n' + body)
        messagebox.showinfo('Transfer preview', body)

    def _send_transfer(self):
        if self._preview is None or self._current_route is None:
            messagebox.showwarning('Transfer', 'Run preview first.')
            return

        route = self._current_route
        preview = self._preview
        check = services.validate_transfer_sender(
            route['source_network'],
            preview.symbol,
            preview.amount_token,
        )
        if check:
            messagebox.showwarning('Transfer', check)
            return

        dialog = tk.Toplevel(self)
        dialog.title('Confirm IBC transfer')
        dialog.transient(self)
        dialog.grab_set()

        try:
            gas_limit = self._parse_gas_limit()
        except ValueError as exc:
            messagebox.showerror('Transfer', str(exc), parent=self)
            return

        summary = '\n'.join(preview.summary_lines()) + f'\nGas limit: {gas_limit:,}'
        ttk.Label(dialog, text=summary, justify=tk.LEFT).pack(padx=12, pady=12)

        amount_display = self._format_amount_for_display(preview.amount_token)
        confirm_var = tk.StringVar(value=amount_display)
        ttk.Label(
            dialog,
            text=f'Confirm amount ({preview.symbol}, editable if needed):',
        ).pack(anchor=tk.W, padx=12)
        ttk.Entry(dialog, textvariable=confirm_var, width=24).pack(padx=12, pady=4, anchor=tk.W)

        agree_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(dialog, text='I confirm this transfer', variable=agree_var).pack(anchor=tk.W, padx=12, pady=8)

        def submit():
            try:
                if float(confirm_var.get().strip()) != float(preview.amount_token):
                    messagebox.showerror('Confirm', 'Amount mismatch.', parent=dialog)
                    return
            except ValueError:
                messagebox.showerror('Confirm', 'Invalid amount.', parent=dialog)
                return
            if not agree_var.get():
                messagebox.showerror('Confirm', 'Check the confirmation box.', parent=dialog)
                return
            dialog.destroy()
            services.record_transfer_tx(status='submitted', route=route, preview=preview, gas=gas_limit)
            self._refresh_history_table()

            def on_fail(exc: Exception):
                self._refresh_history_table()
                self._async_error('IBC transfer', exc)

            self._run_async(
                'IBC transfer',
                lambda: services.gui_broadcast_transfer(route, preview, gas_limit=gas_limit),
                on_success=lambda tx_hash: self._transfer_done(tx_hash, route, preview, gas_limit),
                on_error=on_fail,
            )

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text='Send', command=submit).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text='Cancel', command=dialog.destroy).pack(side=tk.LEFT, padx=4)

    def _transfer_done(self, tx_hash: str, route, preview, gas_limit: int):
        self._refresh_history_table()
        self._refresh_wallet_balances(quiet=True, force=True)
        self.log(f'Transaction hash: {tx_hash}')
        messagebox.showinfo(
            'Success',
            f'Transaction broadcast.\n\nHash (copied to clipboard):\n{tx_hash}',
        )
        self.clipboard_clear()
        self.clipboard_append(tx_hash)
        self._preview = None
        self.btn_send.configure(state=tk.DISABLED)

    def _build_swap_tab(self):
        ttk.Label(self.tab_swap, text='Swap — Osmosis (Skip route)', font=('', 11, 'bold')).pack(
            anchor=tk.W, pady=(0, 8),
        )
        self._muted_label(
            self.tab_swap,
            text=(
                'Quotes and routing use the Skip API; your wallet signs and broadcasts via Cosmpy. '
                'Osmosis must be enabled under Networks. Same-chain swaps only in this version.'
            ),
            wraplength=900,
        ).pack(anchor=tk.W, pady=(0, 8))

        form = ttk.Frame(self.tab_swap)
        form.pack(fill=tk.X, anchor=tk.W)

        self.var_swap_in = tk.StringVar(value='OSMO')
        self.var_swap_out = tk.StringVar(value='USDC')
        self.var_swap_amount = tk.StringVar(value='0.01')
        self.var_swap_slippage = tk.StringVar(value='1.5')
        self.var_swap_gas = tk.StringVar(value='1000000')
        self.var_swap_auto_gas = tk.BooleanVar(value=True)
        self.var_swap_split = tk.BooleanVar(value=False)
        self._swap_max_amount = 0.0
        self._swap_balance_fetch_in_progress = False

        ttk.Label(form, text='Sell').grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        swap_in_row = ttk.Frame(form)
        swap_in_row.grid(row=0, column=1, sticky=tk.W, padx=4, pady=4)
        self.cmb_swap_in = ttk.Combobox(swap_in_row, textvariable=self.var_swap_in, width=40)
        self.cmb_swap_in.pack(side=tk.LEFT)
        ttk.Button(swap_in_row, text='⇄', width=3, command=self._swap_flip_tokens).pack(
            side=tk.LEFT, padx=(8, 0),
        )

        ttk.Label(form, text='Buy').grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self.cmb_swap_out = ttk.Combobox(form, textvariable=self.var_swap_out, width=40)
        self.cmb_swap_out.grid(row=1, column=1, sticky=tk.W, padx=4, pady=4)

        self.lbl_swap_balance = self._muted_label(form, text='Balance (sell token): —')
        self.lbl_swap_balance.grid(row=2, column=1, sticky=tk.W, padx=4, pady=(0, 4))

        ttk.Label(form, text='Amount').grid(row=3, column=0, sticky=tk.W, padx=4, pady=4)
        amount_row = ttk.Frame(form)
        amount_row.grid(row=3, column=1, sticky=tk.W, padx=4, pady=4)
        ttk.Entry(amount_row, textvariable=self.var_swap_amount, width=22).pack(side=tk.LEFT)
        ttk.Button(amount_row, text='Max', width=6, command=self._swap_fill_max_amount).pack(
            side=tk.LEFT, padx=(6, 0),
        )

        ttk.Label(form, text='Slippage %').grid(row=4, column=0, sticky=tk.W, padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_swap_slippage, width=8).grid(
            row=4, column=1, sticky=tk.W, padx=4, pady=4,
        )

        gas_row = ttk.Frame(form)
        gas_row.grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=4, pady=4)
        ttk.Label(gas_row, text='Gas limit').pack(side=tk.LEFT, padx=(0, 8))
        ttk.Entry(gas_row, textvariable=self.var_swap_gas, width=12).pack(side=tk.LEFT)
        ttk.Checkbutton(
            gas_row,
            text='Auto (+35% buffer)',
            variable=self.var_swap_auto_gas,
            command=self._apply_swap_gas_defaults,
        ).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Checkbutton(
            gas_row,
            text='Split routes (Skip)',
            variable=self.var_swap_split,
        ).pack(side=tk.LEFT, padx=(16, 0))

        self.swap_route_info = ttk.Label(self.tab_swap, text='', wraplength=700)
        self.swap_route_info.pack(anchor=tk.W, pady=8)

        btn_row = ttk.Frame(self.tab_swap)
        btn_row.pack(anchor=tk.W, pady=4)
        ttk.Button(btn_row, text='Preview swap', command=self._preview_swap).pack(side=tk.LEFT, padx=(0, 8))
        self.btn_swap_send = ttk.Button(
            btn_row, text='Swap (after preview)', command=self._send_swap, state=tk.DISABLED,
        )
        self.btn_swap_send.pack(side=tk.LEFT)

        def _swap_token_change():
            self._refresh_swap_balance()
            self._update_swap_route_hint()

        self._refresh_swap_in_combobox = bind_searchable_combobox(
            self.cmb_swap_in,
            lambda: services.symbols_for_transfer_network('osmosis', 'nonzero'),
            on_change=_swap_token_change,
            textvariable=self.var_swap_in,
        )
        self._refresh_swap_out_combobox = bind_searchable_combobox(
            self.cmb_swap_out,
            lambda: services.symbols_for_transfer_network('osmosis', 'all'),
            on_change=_swap_token_change,
            textvariable=self.var_swap_out,
        )
        self._apply_swap_gas_defaults()
        self._update_swap_route_hint()
        self._refresh_swap_balance()

    def _apply_swap_gas_defaults(self):
        base = 1_000_000
        if getattr(self, 'var_swap_auto_gas', None) and self.var_swap_auto_gas.get():
            limit = services.recommended_gas_limit(base)
            self.var_swap_gas.set(str(limit))
        else:
            self.var_swap_gas.set(str(base))

    def _update_swap_route_hint(self):
        if not hasattr(self, 'swap_route_info'):
            return
        sell = self.var_swap_in.get().strip() or '—'
        buy = self.var_swap_out.get().strip() or '—'
        self.swap_route_info.configure(
            text=f'Osmosis swap: {sell} → {buy} · routing: Skip API · signer: active wallet',
        )

    def _swap_flip_tokens(self):
        a, b = self.var_swap_in.get(), self.var_swap_out.get()
        self.var_swap_in.set(b)
        self.var_swap_out.set(a)
        if hasattr(self, '_refresh_swap_in_combobox'):
            self._refresh_swap_in_combobox()
        self._swap_preview = None
        self.btn_swap_send.configure(state=tk.DISABLED)
        self._refresh_swap_balance()
        self._update_swap_route_hint()

    def _swap_fill_max_amount(self):
        if self._swap_max_amount <= 0:
            messagebox.showinfo('Swap', 'No spendable balance for the sell token on Osmosis.')
            return
        text = f'{self._swap_max_amount:.8f}'.rstrip('0').rstrip('.')
        self.var_swap_amount.set(text or '0')

    def _refresh_swap_balance(self):
        if not hasattr(self, 'lbl_swap_balance'):
            return
        if self._swap_balance_fetch_in_progress:
            return
        raw = self.var_swap_in.get().strip()
        if not raw:
            self.lbl_swap_balance.configure(text='Balance (sell token): —')
            self._swap_max_amount = 0.0
            return
        try:
            sym = services.resolve_transfer_symbol('osmosis', raw, 'nonzero')
        except ValueError:
            sym = raw
        self.lbl_swap_balance.configure(text=f'Balance ({sym} on Osmosis): loading…')
        self._swap_balance_fetch_in_progress = True

        def worker():
            return services.get_transfer_side_balances('osmosis', 'osmosis', sym)

        def on_success(data):
            self._swap_balance_fetch_in_progress = False
            self._swap_max_amount = float(data.get('sender_max') or 0)
            self.lbl_swap_balance.configure(
                text=data.get('sender_text', f'Balance ({sym}): —').replace('From (osmosis)', 'Balance'),
            )

        def on_error(exc):
            self._swap_balance_fetch_in_progress = False
            self._swap_max_amount = 0.0
            self.lbl_swap_balance.configure(text=f'Balance: error ({exc})')

        self._run_async('Swap balance', worker, on_success=on_success, on_error=on_error)

    def _parse_swap_gas_limit(self) -> int:
        try:
            raw = int(self.var_swap_gas.get().strip())
        except ValueError as exc:
            raise ValueError('Gas limit must be an integer.') from exc
        if raw <= 0:
            raise ValueError('Gas limit must be positive.')
        return raw

    def _preview_swap(self):
        try:
            sym_in = services.resolve_transfer_symbol(
                'osmosis', self.var_swap_in.get().strip(), 'nonzero',
            )
            sym_out = services.resolve_transfer_symbol(
                'osmosis', self.var_swap_out.get().strip(), 'all',
            )
            amount = float(self.var_swap_amount.get().strip())
            slippage = float(self.var_swap_slippage.get().strip())
            gas_limit = self._parse_swap_gas_limit()
        except ValueError as exc:
            messagebox.showerror('Swap', str(exc))
            return
        if amount <= 0:
            messagebox.showerror('Swap', 'Amount must be greater than zero.')
            return
        if slippage < 0 or slippage > 50:
            messagebox.showerror('Swap', 'Slippage must be between 0 and 50%.')
            return

        def worker():
            return services.gui_prepare_swap(
                sym_in,
                sym_out,
                amount,
                slippage_percent=slippage,
                gas=gas_limit,
                split_routes=self.var_swap_split.get(),
            )

        def on_success(preview):
            self._swap_preview = preview
            self._swap_gas_limit = gas_limit
            self.btn_swap_send.configure(state=tk.NORMAL)
            services.record_swap_tx(status='preview', preview=preview, gas=gas_limit)
            self._refresh_history_table()
            body = '\n'.join(preview.summary_lines()) + f'\nGas limit: {gas_limit:,}'
            self.log('--- Swap preview ---\n' + body)
            messagebox.showinfo('Swap preview', body)

        def on_error(exc):
            self._swap_preview = None
            self.btn_swap_send.configure(state=tk.DISABLED)
            services.record_swap_tx(
                status='failed',
                gas=gas_limit,
                error=f'preview: {exc}',
                symbol_in=sym_in,
                symbol_out=sym_out,
                amount=str(amount),
            )
            self._refresh_history_table()
            messagebox.showerror('Preview failed', str(exc))

        self._run_async('Swap preview', worker, on_success=on_success, on_error=on_error)

    def _send_swap(self):
        if self._swap_preview is None:
            messagebox.showwarning('Swap', 'Run preview first.')
            return
        preview = self._swap_preview
        try:
            gas_limit = self._parse_swap_gas_limit()
        except ValueError as exc:
            messagebox.showerror('Swap', str(exc))
            return

        summary = '\n'.join(preview.summary_lines()) + f'\nGas limit: {gas_limit:,}'
        dialog = tk.Toplevel(self)
        dialog.title('Confirm swap')
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text=summary, justify=tk.LEFT).pack(padx=12, pady=12)
        amount_display = self._format_amount_for_display(preview.amount_in_token)
        confirm_var = tk.StringVar(value=amount_display)
        ttk.Label(
            dialog,
            text=f'Confirm sell amount ({preview.symbol_in}, editable if needed):',
        ).pack(anchor=tk.W, padx=12)
        ttk.Entry(dialog, textvariable=confirm_var, width=24).pack(padx=12, pady=4)

        def submit():
            try:
                if float(confirm_var.get().strip()) != float(preview.amount_in_token):
                    messagebox.showerror('Swap', 'Amount mismatch. Cancelled.', parent=dialog)
                    return
            except ValueError:
                messagebox.showerror('Swap', 'Invalid amount.', parent=dialog)
                return
            dialog.destroy()
            services.record_swap_tx(status='submitted', preview=preview, gas=gas_limit)
            self._refresh_history_table()

            def on_fail(exc):
                self._refresh_history_table()
                messagebox.showerror('Swap failed', str(exc))

            self._run_async(
                'Swap',
                lambda: services.gui_broadcast_swap(preview, gas_limit=gas_limit),
                on_success=lambda tx_hash: self._swap_done(tx_hash, preview, gas_limit),
                on_error=on_fail,
            )

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text='Swap', command=submit).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text='Cancel', command=dialog.destroy).pack(side=tk.LEFT, padx=4)

    def _swap_done(self, tx_hash: str, preview, gas_limit: int):
        self._refresh_history_table()
        self._refresh_wallet_balances(quiet=True, force=True)
        self.log(f'Swap tx hash: {tx_hash}')
        messagebox.showinfo(
            'Swap success',
            f'Swap confirmed on chain.\n\nHash (copied to clipboard):\n{tx_hash}',
        )
        self.clipboard_clear()
        self.clipboard_append(tx_hash)
        self._swap_preview = None
        self.btn_swap_send.configure(state=tk.DISABLED)

    def _history_visible_columns(self) -> list:
        from gui.history_view import HISTORY_COLUMN_IDS, default_visible_columns

        saved = self.settings.get('history_visible_columns')
        if isinstance(saved, list) and saved:
            return [c for c in saved if c in HISTORY_COLUMN_IDS]
        return default_visible_columns()

    def _history_status_filter_set(self) -> set:
        from gui.history_view import KNOWN_STATUSES, default_status_filter

        saved = self.settings.get('history_status_filter')
        if isinstance(saved, list) and saved:
            return {s.lower() for s in saved if s.lower() in KNOWN_STATUSES}
        return {s.lower() for s in default_status_filter()}

    def _build_history_tab(self):
        from gui.history_view import HISTORY_COLUMN_IDS, KNOWN_STATUSES, column_specs

        ttk.Label(self.tab_history, text='Transaction history', font=('', 11, 'bold')).pack(
            anchor=tk.W, pady=(0, 8),
        )
        self._muted_label(
            self.tab_history,
            text='IBC transfers from this app. Filter by date and status; choose columns. Double-click a row to copy tx hash.',
            wraplength=900,
        ).pack(anchor=tk.W, pady=(0, 8))

        toolbar = ttk.Frame(self.tab_history)
        toolbar.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(toolbar, text='Refresh', command=self._refresh_history_table).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text='Copy hash', command=self._copy_history_hash).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text='Columns…', command=self._history_choose_columns).pack(side=tk.LEFT)

        filter_row = ttk.Frame(self.tab_history)
        filter_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(filter_row, text='Date from').pack(side=tk.LEFT)
        self.var_history_date_from = tk.StringVar(value='')
        ttk.Entry(filter_row, textvariable=self.var_history_date_from, width=12).pack(side=tk.LEFT, padx=(4, 12))
        ttk.Label(filter_row, text='to').pack(side=tk.LEFT)
        self.var_history_date_to = tk.StringVar(value='')
        ttk.Entry(filter_row, textvariable=self.var_history_date_to, width=12).pack(side=tk.LEFT, padx=(4, 12))
        self._muted_label(filter_row, text='(YYYY-MM-DD, empty = any)', track=False).pack(side=tk.LEFT)

        status_row = ttk.Frame(self.tab_history)
        status_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(status_row, text='Events:').pack(side=tk.LEFT)
        self._history_status_vars: dict = {}
        active_statuses = self._history_status_filter_set()
        for st in KNOWN_STATUSES:
            var = tk.BooleanVar(value=st in active_statuses)
            self._history_status_vars[st] = var
            ttk.Checkbutton(
                status_row,
                text=st,
                variable=var,
                command=self._refresh_history_table,
            ).pack(side=tk.LEFT, padx=(6, 0))

        self.lbl_history_count = self._muted_label(self.tab_history, text='')
        self.lbl_history_count.pack(anchor=tk.W, pady=(0, 4))

        self._history_column_ids = list(HISTORY_COLUMN_IDS)
        tree_frame = ttk.Frame(self.tab_history)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.history_tree = ttk.Treeview(
            tree_frame,
            columns=self._history_column_ids,
            show='headings',
            height=18,
        )
        spec_by_id = {spec[0]: spec for spec in column_specs()}
        for col_id in self._history_column_ids:
            title, width, stretch = spec_by_id[col_id][1], spec_by_id[col_id][2], spec_by_id[col_id][3]
            self.history_tree.heading(col_id, text=title)
            self.history_tree.column(col_id, width=width, stretch=stretch, minwidth=40)
        vscroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.history_tree.yview)
        hscroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        self.history_tree.grid(row=0, column=0, sticky='nsew')
        vscroll.grid(row=0, column=1, sticky='ns')
        hscroll.grid(row=1, column=0, sticky='ew')
        self.history_tree.bind('<Double-1>', lambda _e: self._copy_history_hash())
        self.history_tree.tag_configure('success', foreground=self.colors.success)
        self.history_tree.tag_configure('failed', foreground=self.colors.error)
        self.history_tree.tag_configure('pending', foreground=self.colors.muted)
        self._history_rows_by_iid: dict = {}
        self._apply_history_column_visibility()
        self.var_history_date_from.trace_add('write', lambda *_a: self._refresh_history_table())
        self.var_history_date_to.trace_add('write', lambda *_a: self._refresh_history_table())
        self._refresh_history_table()

    def _apply_history_column_visibility(self):
        if not hasattr(self, 'history_tree'):
            return
        visible = self._history_visible_columns()
        self.history_tree['displaycolumns'] = visible

    def _history_choose_columns(self):
        from gui.history_view import HISTORY_COLUMN_IDS, column_specs

        dialog = tk.Toplevel(self)
        dialog.title('History columns')
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text='Show columns (at least one):').pack(anchor=tk.W, padx=12, pady=(12, 6))
        vars_map: dict = {}
        visible = set(self._history_visible_columns())
        spec_titles = {spec[0]: spec[1] for spec in column_specs()}
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=12)
        for col_id in HISTORY_COLUMN_IDS:
            var = tk.BooleanVar(value=col_id in visible)
            vars_map[col_id] = var
            ttk.Checkbutton(frame, text=spec_titles.get(col_id, col_id), variable=var).pack(anchor=tk.W)

        def save():
            chosen = [c for c in HISTORY_COLUMN_IDS if vars_map[c].get()]
            if not chosen:
                messagebox.showerror('Columns', 'Select at least one column.', parent=dialog)
                return
            self.settings['history_visible_columns'] = chosen
            save_settings(self.settings)
            dialog.destroy()
            self._apply_history_column_visibility()
            self._refresh_history_table()

        btn_row = ttk.Frame(dialog)
        btn_row.pack(pady=12)
        ttk.Button(btn_row, text='Apply', command=save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text='Cancel', command=dialog.destroy).pack(side=tk.LEFT, padx=6)

    def _refresh_history_table(self):
        if not hasattr(self, 'history_tree'):
            return
        from gui.history_view import row_values, status_tag

        visible = self._history_visible_columns()
        statuses = {st for st, var in self._history_status_vars.items() if var.get()}
        self.settings['history_status_filter'] = sorted(statuses)
        try:
            rows = services.filtered_tx_history(
                date_from=self.var_history_date_from.get(),
                date_to=self.var_history_date_to.get(),
                statuses=statuses,
            )
        except ValueError as exc:
            self.lbl_history_count.configure(text=str(exc))
            return
        total = len(services.list_tx_history())
        self.lbl_history_count.configure(
            text=f'Showing {len(rows)} of {total} event(s) · columns: {len(visible)} · statuses: {", ".join(sorted(statuses)) or "none"}',
        )
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        self._history_rows_by_iid.clear()
        for row in rows:
            iid = self.history_tree.insert(
                '',
                tk.END,
                values=row_values(row, self._history_column_ids),
                tags=status_tag(row.get('status', '')),
            )
            self._history_rows_by_iid[iid] = row

    def _copy_history_hash(self):
        if not hasattr(self, 'history_tree'):
            return
        item = self._treeview_focus_item(self.history_tree)
        if not item:
            messagebox.showinfo('History', 'Select a row first.')
            return
        row = self._history_rows_by_iid.get(item, {})
        tx_hash = (row.get('tx_hash') or '').strip()
        if not tx_hash or len(tx_hash) < 16:
            messagebox.showinfo('History', 'No transaction hash for this row (failed, preview, or pending).')
            return
        self._copy_text_to_clipboard(tx_hash)
        self.log(f'Copied tx hash: {tx_hash}')

    def _send_token_list_mode(self) -> str:
        if hasattr(self, 'var_send_token_list'):
            return self.var_send_token_list.get().strip().lower() or 'nonzero'
        return self.settings.get('send_token_list_mode', 'nonzero')

    def _on_send_token_list_mode_changed(self):
        self.settings['send_token_list_mode'] = self._send_token_list_mode()
        from gui.settings import save_settings

        save_settings(self.settings)
        self._update_transfer_symbols()

    def _refresh_token_comboboxes_after_denoms(self):
        """Apply denoms_book renames to Send/Swap lists and portfolio labels."""
        if hasattr(self, '_refresh_symbol_combobox'):
            self._refresh_symbol_combobox()
        if hasattr(self, '_refresh_swap_in_combobox'):
            self._refresh_swap_in_combobox()
        if hasattr(self, '_refresh_swap_out_combobox'):
            self._refresh_swap_out_combobox()
        if hasattr(self, '_refresh_send_balances'):
            self._refresh_send_balances()
        if hasattr(self, '_refresh_swap_balance'):
            self._refresh_swap_balance()
        if self._can_fetch_balances():
            self._refresh_wallet_balances(quiet=True)

    def _update_transfer_symbols(self):
        if not hasattr(self, 'cmb_symbol'):
            return
        network = self.var_source.get().strip()
        mode = self._send_token_list_mode()
        if hasattr(self, '_refresh_symbol_combobox'):
            self._refresh_symbol_combobox()
        else:
            symbols = services.symbols_for_transfer_network(network, list_mode=mode) if network else []
            self.cmb_symbol['values'] = symbols
        symbols = services.symbols_for_transfer_network(network, list_mode=mode) if network else []
        if symbols:
            current = self.var_symbol.get().strip().lower()
            if not current or current not in [s.lower() for s in symbols]:
                self.var_symbol.set(symbols[0])
        self._update_send_token_denom_hint()
        self._refresh_send_balances()

    def _build_networks_tab(self):
        from project_utils.networks_manager import DEFAULT_ENABLED_NETWORKS

        self._network_use_state: dict = {}

        cfg_path = services.enabled_networks_config_path()
        intro = ttk.Label(
            self.tab_networks,
            text=(
                'Click Use (✓) to enable a chain — wallets, address book, IBC routes, and Send '
                'update automatically (vault must be unlocked for new addresses). '
                f'Defaults: {", ".join(DEFAULT_ENABLED_NETWORKS)}. '
                f'Settings: {cfg_path}.'
            ),
            wraplength=920,
        )
        intro.pack(anchor=tk.W, pady=(0, 8))

        toolbar = ttk.Frame(self.tab_networks)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text='Test all', command=self._test_all_networks).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text='Apply selection', command=self._save_networks_selection).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(toolbar, text='Defaults (Osmosis, Cosmos)', command=self._networks_use_defaults).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(
            toolbar,
            text='Regenerate clients & wallets',
            command=self._regenerate_network_clients,
        ).pack(side=tk.LEFT)

        cols = ('use', 'network', 'chain_id', 'status', 'rest')
        self.networks_tree = ttk.Treeview(self.tab_networks, columns=cols, show='headings', height=20)
        for col, title, width in [
            ('use', 'Use', 44),
            ('network', 'Network', 140),
            ('chain_id', 'Chain ID', 160),
            ('status', 'Status', 100),
            ('rest', 'REST', 360),
        ]:
            self.networks_tree.heading(col, text=title)
            self.networks_tree.column(col, width=width, stretch=col == 'rest')
        scroll = ttk.Scrollbar(self.tab_networks, orient=tk.VERTICAL, command=self.networks_tree.yview)
        self.networks_tree.configure(yscrollcommand=scroll.set)
        self.networks_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)
        self.networks_tree.bind('<Button-1>', self._on_networks_tree_click)
        self.networks_tree.tag_configure('ok', foreground=self.colors.success)
        self.networks_tree.tag_configure('fail', foreground=self.colors.error)

        self.lbl_networks_hint = ttk.Label(self.tab_networks, text='')
        self.lbl_networks_hint.pack(anchor=tk.W)
        self._refresh_networks_table()

    def _refresh_networks_table(self):
        if not hasattr(self, 'networks_tree'):
            return
        rows = services.list_network_rows()
        self._network_use_state = {r['chain_name']: r['enabled'] for r in rows}
        for item in self.networks_tree.get_children():
            self.networks_tree.delete(item)
        if not rows:
            self.lbl_networks_hint.configure(
                text='No chain data yet. Run Setup → step 3 (Collect chain-registry JSON).',
            )
            return
        self.lbl_networks_hint.configure(
            text=f'{sum(1 for r in rows if r["enabled"])} enabled of {len(rows)} networks in registry.',
        )
        for row in rows:
            mark = '✓' if row['enabled'] else '·'
            tags = ()
            if row['status'] == 'OK':
                tags = ('ok',)
            elif row['status'] == 'Offline':
                tags = ('fail',)
            rest = row['rest']
            if len(rest) > 72:
                rest = rest[:69] + '…'
            self.networks_tree.insert(
                '',
                tk.END,
                iid=row['chain_name'],
                values=(mark, row['chain_name'], row['chain_id'], row['status'], rest),
                tags=tags,
            )

    def _on_networks_tree_click(self, event):
        if self.networks_tree.identify_region(event.x, event.y) != 'cell':
            return
        if self.networks_tree.identify_column(event.x) != '#1':
            return
        row_id = self.networks_tree.identify_row(event.y)
        if not row_id:
            return
        was_on = self._network_use_state.get(row_id, False)
        self._network_use_state[row_id] = not was_on
        enabled = self._enabled_networks_from_tree()
        if not enabled:
            self._network_use_state[row_id] = was_on
            messagebox.showwarning('Networks', 'At least one network must stay enabled.')
            return
        mark = '✓' if self._network_use_state[row_id] else '·'
        values = list(self.networks_tree.item(row_id, 'values'))
        values[0] = mark
        self.networks_tree.item(row_id, values=values)
        self._apply_enabled_networks_live()

    def _enabled_networks_from_tree(self) -> list:
        return sorted(name for name, on in self._network_use_state.items() if on)

    def _apply_enabled_networks_live(self) -> None:
        """Persist enabled networks; sync wallets, address book, IBC, and UI."""
        enabled = self._enabled_networks_from_tree()
        if not enabled:
            return
        services.save_enabled_network_selection(enabled)
        self._refresh_network_filters()
        if hasattr(self, 'lbl_networks_hint'):
            self.lbl_networks_hint.configure(
                text=f'{len(enabled)} enabled · syncing wallets…',
            )

        def worker():
            return services.sync_wallet_artifacts_for_enabled_networks(set(enabled))

        def on_success(text: str):
            if text.strip():
                self.log(text)
            from project_utils.ibc_routes import load_generated_ibc_routes

            self.log(
                f'IBC routes for enabled pairs: {len(load_generated_ibc_routes())}',
            )
            if hasattr(self, 'addr_tree'):
                self._load_addresses()
            if hasattr(self, 'receive_tree'):
                self._load_receive_addresses()
            self._refresh_wallet_balances(quiet=True)
            if hasattr(self, 'lbl_networks_hint'):
                self.lbl_networks_hint.configure(
                    text=f'{len(enabled)} enabled · saved to enabled_networks.json',
                )

        self._run_async('Wallet sync', worker, on_success=on_success)

    def _save_networks_selection(self):
        enabled = self._enabled_networks_from_tree()
        if not enabled:
            messagebox.showwarning('Networks', 'Select at least one network.')
            return
        self._apply_enabled_networks_live()
        self._refresh_networks_table()
        messagebox.showinfo(
            'Networks',
            f'Using {len(enabled)} network(s).\n'
            'Wallets and address book are syncing in the background.',
        )

    def _networks_use_defaults(self):
        defaults = services.restore_default_enabled_networks()
        self._refresh_networks_table()
        self._apply_enabled_networks_live()
        self.log('Enabled networks reset to defaults: ' + ', '.join(defaults))

    def _test_all_networks(self):
        self._run_async(
            'Network health',
            services.test_all_network_health,
            on_success=lambda text: (self.log(text), self._refresh_networks_table()),
        )

    def _regenerate_network_clients(self):
        enabled = self._enabled_networks_from_tree()
        if not enabled:
            messagebox.showwarning('Networks', 'Select at least one network before regenerating.')
            return
        services.save_enabled_network_selection(enabled)

        def worker():
            return services.regenerate_for_enabled_networks(
                link_type=self.settings.get('ledger_link_type', 'keplr_rest_link'),
            )

        def on_success(text):
            self.log(text)
            self._refresh_network_filters()
            self._refresh_networks_table()
            messagebox.showinfo('Networks', 'Ledger clients and wallets regenerated for enabled networks.')

        self._run_async('Regenerate clients', worker, on_success=on_success)

    def _refresh_network_filters(self):
        self._by_source = services.ibc_routes_grouped()
        if not hasattr(self, 'var_source'):
            return
        sources = sorted(self._by_source.keys())
        current = self.var_source.get().strip()
        if current not in sources:
            fallback = 'osmosis' if 'osmosis' in sources else (sources[0] if sources else '')
            if fallback:
                self.var_source.set(fallback)
        if hasattr(self, '_picker_source'):
            self._picker_source.refresh()
        self._on_source_changed()

    def _build_tokens_tab(self):
        intro = ttk.Label(
            self.tab_tokens,
            text=(
                'Chain-registry tokens. Filter by network, then by symbol or display name. '
                'Osmosis DEX prices from Numia when denom matches. Setup → step 3 to rebuild catalog.'
            ),
            wraplength=920,
        )
        intro.pack(anchor=tk.W, pady=(0, 8))

        toolbar = ttk.Frame(self.tab_tokens)
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text='Network:').pack(side=tk.LEFT, padx=(0, 6))
        self.var_token_chain = tk.StringVar(value='All')
        self.cmb_token_chain = ttk.Combobox(
            toolbar,
            textvariable=self.var_token_chain,
            state='readonly',
            width=22,
        )
        self.cmb_token_chain.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(toolbar, text='Symbol:').pack(side=tk.LEFT, padx=(0, 6))
        self.var_token_symbol = tk.StringVar()
        symbol_entry = ttk.Entry(toolbar, textvariable=self.var_token_symbol, width=16)
        symbol_entry.pack(side=tk.LEFT, padx=(0, 10))
        symbol_entry.bind('<Return>', lambda _e: self._on_token_symbol_filter())
        self.var_token_symbol.trace_add('write', lambda *_a: self._on_token_symbol_filter())
        self.cmb_token_chain.bind('<<ComboboxSelected>>', lambda _e: self._on_token_chain_changed())
        ttk.Button(
            toolbar,
            text='Refresh',
            command=lambda: self._load_registry_tokens(force=True),
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.var_tokens_auto = tk.BooleanVar(value=bool(self.settings.get('tokens_auto_refresh', False)))
        ttk.Checkbutton(
            toolbar,
            text='Auto-refresh',
            variable=self.var_tokens_auto,
            command=self._on_tokens_auto_changed,
        ).pack(side=tk.LEFT)
        tsec = max(30, min(86400, int(self.settings.get('tokens_auto_refresh_seconds', 3600))))
        self.var_tokens_auto_sec = tk.StringVar(value=str(tsec))
        ttk.Label(toolbar, text='every').pack(side=tk.LEFT, padx=(8, 2))
        self.spin_tokens_auto_sec = ttk.Spinbox(
            toolbar,
            from_=30,
            to=86400,
            width=7,
            textvariable=self.var_tokens_auto_sec,
        )
        self.spin_tokens_auto_sec.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(toolbar, text='s').pack(side=tk.LEFT)
        self.spin_tokens_auto_sec.bind('<FocusOut>', lambda _e: self._save_tokens_auto_interval())
        self.spin_tokens_auto_sec.bind('<Return>', lambda _e: self._save_tokens_auto_interval())
        self._muted_label(
            toolbar,
            text='  Symbol matches ticker / display / name only (not IBC hash). Click headers to sort.',
            track=False,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self._token_rows: list = []
        self._token_meta: dict = {}
        self._token_sort_col = 'symbol'
        self._token_sort_reverse = False
        self._token_heading_titles = {
            'network': 'Network',
            'symbol': 'Symbol',
            'display': 'Display',
            'denom': 'Denom / base',
            'decimals': 'Dec',
            'contract': 'Contract / IBC',
            'price': 'Price',
            'liq': 'Liquidity',
            'chg24': '24h %',
        }

        cols = ('network', 'symbol', 'display', 'denom', 'decimals', 'contract', 'price', 'liq', 'chg24')
        tree_frame = ttk.Frame(self.tab_tokens)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.tokens_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=20)
        for col, title, width in [
            ('network', 'Network', 110),
            ('symbol', 'Symbol', 72),
            ('display', 'Display', 72),
            ('denom', 'Denom / base', 200),
            ('decimals', 'Dec', 40),
            ('contract', 'Contract / IBC', 160),
            ('price', 'Price', 88),
            ('liq', 'Liquidity', 96),
            ('chg24', '24h %', 64),
        ]:
            self.tokens_tree.heading(
                col,
                text=title,
                command=lambda c=col: self._sort_token_column(c),
            )
            self.tokens_tree.column(col, width=width, stretch=col in ('denom', 'contract'), minwidth=40)
        vscroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tokens_tree.yview)
        hscroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.tokens_tree.xview)
        self.tokens_tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        self.tokens_tree.grid(row=0, column=0, sticky='nsew')
        vscroll.grid(row=0, column=1, sticky='ns')
        hscroll.grid(row=1, column=0, sticky='ew')

        self.lbl_tokens_status = ttk.Label(self.tab_tokens, text='')
        self.lbl_tokens_status.pack(anchor=tk.W)
        self._tokens_cached_at_iso: Optional[str] = None
        self._refresh_tokens_chain_filter()
        self._try_restore_tokens_cache()

    def _refresh_tokens_chain_filter(self):
        if not hasattr(self, 'cmb_token_chain'):
            return
        chains = ['All'] + services.registry_chains_with_tokens()
        self.cmb_token_chain['values'] = chains
        if self.var_token_chain.get() not in chains:
            self.var_token_chain.set(chains[0] if chains else 'All')

    def _token_matches_symbol(self, row: dict, needle: str) -> bool:
        needle = (needle or '').strip().lower()
        if not needle:
            return True
        for key in ('symbol', 'display', 'name'):
            if needle in (row.get(key) or '').lower():
                return True
        return False

    def _token_sort_key(self, row: dict, column: str):
        text_cols = {'network', 'symbol', 'display', 'denom', 'contract'}
        if column in text_cols:
            if column == 'network':
                return (row.get('chain_name') or '').lower()
            return (row.get(column) or '').lower()
        if column == 'decimals':
            try:
                return int(row.get('decimals') or 0)
            except (TypeError, ValueError):
                return 0
        if column == 'liq':
            try:
                return float(row.get('liquidity') or 0)
            except (TypeError, ValueError):
                return 0.0
        if column == 'chg24':
            try:
                return float(row.get('price_24h_change') or 0)
            except (TypeError, ValueError):
                return 0.0
        if column == 'price':
            try:
                return float(row.get('price') or 0)
            except (TypeError, ValueError):
                return 0.0
        return (row.get(column) or '').lower()

    def _sort_token_column(self, column: str):
        if self._token_sort_col == column:
            self._token_sort_reverse = not self._token_sort_reverse
        else:
            self._token_sort_col = column
            self._token_sort_reverse = column not in (
                'network',
                'symbol',
                'display',
                'denom',
                'contract',
            )
        self._render_tokens_table()

    def _update_token_headings(self):
        for col, base in self._token_heading_titles.items():
            arrow = ''
            if col == self._token_sort_col:
                arrow = ' ▼' if self._token_sort_reverse else ' ▲'
            self.tokens_tree.heading(col, text=base + arrow)

    def _token_display_values(self, row: dict) -> tuple:
        price = row.get('price')
        liq = row.get('liquidity')
        chg = row.get('price_24h_change')
        return (
            row.get('chain_name', ''),
            row.get('symbol', ''),
            row.get('display', ''),
            row.get('denom', ''),
            row.get('decimals', ''),
            row.get('contract', '') or '',
            f'{float(price):.6g}' if price not in (None, '') else '',
            f'{float(liq):,.0f}' if liq not in (None, '') else '',
            f'{float(chg):.4g}' if chg not in (None, '') else '',
        )

    def _filtered_token_rows(self) -> list:
        needle = self.var_token_symbol.get() if hasattr(self, 'var_token_symbol') else ''
        return [r for r in self._token_rows if self._token_matches_symbol(r, needle)]

    def _render_tokens_table(self):
        if not hasattr(self, 'tokens_tree'):
            return
        rows = self._filtered_token_rows()
        rows.sort(
            key=lambda r: self._token_sort_key(r, self._token_sort_col),
            reverse=self._token_sort_reverse,
        )
        for item in self.tokens_tree.get_children():
            self.tokens_tree.delete(item)
        for row in rows:
            self.tokens_tree.insert('', tk.END, values=self._token_display_values(row))
        self._update_token_headings()
        self._update_tokens_status(len(rows))

    def _on_token_chain_changed(self):
        self._try_restore_tokens_cache()

    def _clamp_tab_refresh_seconds(self, raw) -> int:
        try:
            v = int(str(raw).strip())
        except (TypeError, ValueError):
            v = 3600
        return max(30, min(86400, v))

    def _tokens_auto_refresh_seconds(self) -> int:
        if hasattr(self, 'var_tokens_auto_sec'):
            return self._clamp_tab_refresh_seconds(self.var_tokens_auto_sec.get())
        return self._clamp_tab_refresh_seconds(self.settings.get('tokens_auto_refresh_seconds', 3600))

    def _save_tokens_auto_interval(self):
        if not hasattr(self, 'var_tokens_auto_sec'):
            return
        sec = self._tokens_auto_refresh_seconds()
        self.settings['tokens_auto_refresh_seconds'] = sec
        self.var_tokens_auto_sec.set(str(sec))
        save_settings(self.settings)

    def _on_tokens_auto_changed(self):
        self.settings['tokens_auto_refresh'] = bool(self.var_tokens_auto.get())
        if hasattr(self, 'var_tokens_auto_sec'):
            self.settings['tokens_auto_refresh_seconds'] = self._tokens_auto_refresh_seconds()
        save_settings(self.settings)

    def _tokens_cache_envelope(self):
        chain = self.var_token_chain.get() if hasattr(self, 'var_token_chain') else 'All'
        return services.load_tokens_tab_cache(chain)

    def _tokens_cache_stale(self) -> bool:
        env = self._tokens_cache_envelope()
        if not env:
            return True
        sec = self._tokens_auto_refresh_seconds()
        age = time.time() - float(env.get('cached_at', 0))
        return age > sec

    def _maybe_auto_refresh_tokens(self):
        if not self.settings.get('tokens_auto_refresh'):
            return
        if self._tokens_cache_stale():
            self._load_registry_tokens(force=True)

    def _apply_tokens_payload(self, rows: list, meta: dict, cached_at_iso: Optional[str] = None):
        self._token_rows = rows
        self._token_meta = meta
        self._tokens_cached_at_iso = cached_at_iso
        self._render_tokens_table()

    def _try_restore_tokens_cache(self) -> bool:
        env = self._tokens_cache_envelope()
        if not env:
            if hasattr(self, 'lbl_tokens_status'):
                self.lbl_tokens_status.configure(
                    text='No cached data — click Refresh to load from registry + Osmosis prices.',
                )
            return False
        payload = env.get('payload') or {}
        self._apply_tokens_payload(
            payload.get('rows', []),
            payload.get('meta', {}),
            env.get('cached_at_iso'),
        )
        return True

    def _update_tokens_status(self, shown: int):
        meta = getattr(self, '_token_meta', {})
        parts = [f'Showing {shown} token(s)']
        if getattr(self, '_tokens_cached_at_iso', None):
            parts.append(f'cache {self._tokens_cached_at_iso}')
        if meta.get('registry_loaded') is False:
            parts = ['No assets_registry.json — run Setup → step 3 (Collect chain-registry JSON)']
        elif meta.get('truncated'):
            parts.append(f'(loaded {meta.get("shown", 0)} max — pick one network)')
        sym = self.var_token_symbol.get().strip() if hasattr(self, 'var_token_symbol') else ''
        if sym and self._token_rows:
            parts.append(f'symbol filter “{sym}”')
        if meta.get('osmosis_prices') is False:
            parts.append(f'Osmosis prices unavailable: {meta.get("osmosis_error", "")}')
        self.lbl_tokens_status.configure(text=' · '.join(parts))

    def _on_token_symbol_filter(self):
        if self._token_rows:
            self._render_tokens_table()

    def _load_registry_tokens(self, force: bool = False):
        if not force and self._try_restore_tokens_cache():
            return
        chain = self.var_token_chain.get()

        def worker():
            return services.fetch_registry_token_rows(
                chain_name=None if chain == 'All' else chain,
                symbol_filter=None,
                with_prices=True,
            )

        def on_success(result):
            rows, meta = result
            services.save_tokens_tab_cache(chain, rows, meta)
            env = services.load_tokens_tab_cache(chain)
            cached_iso = env.get('cached_at_iso') if env else None
            self._apply_tokens_payload(rows, meta, cached_iso)
            self.log('Tokens refreshed: ' + self.lbl_tokens_status.cget('text'))

        self._run_async('Registry tokens', worker, on_success=on_success)

    def _build_denoms_tab(self):
        from config.config_path_files import PathFileName

        book_path = PathFileName().denoms_book_path
        ttk.Label(
            self.tab_denoms,
            text='Token map (denoms_book.json)',
            font=('', 11, 'bold'),
        ).pack(anchor=tk.W, pady=(0, 4))
        self._muted_label(
            self.tab_denoms,
            text=(
                f'All symbol ↔ on-chain denom mappings live in one file:\n{book_path}\n'
                'Manual names from Portfolio and auto IBC resolves are saved here too.'
            ),
            wraplength=920,
        ).pack(anchor=tk.W, pady=(0, 8))

        toolbar = ttk.Frame(self.tab_denoms)
        toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(toolbar, text='Network').pack(side=tk.LEFT, padx=(0, 6))
        self.var_denoms_network = tk.StringVar(value='All')
        self.cmb_denoms_network = ttk.Combobox(
            toolbar,
            textvariable=self.var_denoms_network,
            state='readonly',
            width=22,
        )
        self.cmb_denoms_network.pack(side=tk.LEFT, padx=(0, 10))
        self.cmb_denoms_network.bind('<<ComboboxSelected>>', lambda _e: self._refresh_denoms_table())
        ttk.Button(toolbar, text='Add…', command=self._denoms_add_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text='Edit…', command=self._denoms_edit_dialog).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text='Delete', command=self._denoms_delete_selected).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text='Reload', command=self._refresh_denoms_table).pack(side=tk.LEFT, padx=4)
        ttk.Button(toolbar, text='Copy denom', command=self._copy_denoms_denom).pack(side=tk.LEFT, padx=4)

        filter_row = ttk.Frame(self.tab_denoms)
        filter_row.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(filter_row, text='Search:').pack(side=tk.LEFT)
        self.var_denoms_filter = tk.StringVar()
        self.var_denoms_filter.trace_add('write', lambda *_a: self._filter_denoms_table())
        ttk.Entry(filter_row, textvariable=self.var_denoms_filter, width=36).pack(
            side=tk.LEFT, padx=(6, 0),
        )
        self._muted_label(
            filter_row,
            text='symbol, network, or on-chain denom · double-click row to copy denom',
        ).pack(side=tk.LEFT, padx=(12, 0))

        cols = ('network', 'symbol', 'denom', 'decimal')
        self.denoms_tree = ttk.Treeview(self.tab_denoms, columns=cols, show='headings', height=20)
        for col, title, width in [
            ('network', 'Network', 120),
            ('symbol', 'Symbol', 80),
            ('denom', 'Denom / contract', 360),
            ('decimal', 'Decimals', 72),
        ]:
            self.denoms_tree.heading(col, text=title)
            self.denoms_tree.column(col, width=width, stretch=col == 'denom')
        scroll = ttk.Scrollbar(self.tab_denoms, orient=tk.VERTICAL, command=self.denoms_tree.yview)
        self.denoms_tree.configure(yscrollcommand=scroll.set)
        self.denoms_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

        self.lbl_denoms_status = self._muted_label(self.tab_denoms, text='')
        self.lbl_denoms_status.pack(anchor=tk.W)
        self._denoms_row_by_iid: dict = {}
        self._denoms_all_entries: list = []
        self._denoms_tree_last_item = None
        self.denoms_tree.bind('<<TreeviewSelect>>', lambda _e: self._remember_tree_row(
            self.denoms_tree, '_denoms_tree_last_item',
        ))
        self.denoms_tree.bind(
            '<ButtonRelease-1>',
            lambda e: self._remember_tree_row(self.denoms_tree, '_denoms_tree_last_item', e),
        )
        self.denoms_tree.bind('<Double-1>', self._on_denoms_double_click)
        self.denoms_tree.bind('<Control-c>', lambda _e: self._copy_denoms_denom())
        self._refresh_denoms_network_filter()
        self.after(0, self._refresh_denoms_table)

    def _refresh_denoms_network_filter(self):
        nets = sorted({n for n in services.get_wallet_networks() if n}, key=str.lower)
        values = ['All'] + nets
        self.cmb_denoms_network['values'] = values
        if self.var_denoms_network.get() not in values:
            self.var_denoms_network.set('All')

    def _refresh_denoms_table(self):
        if not hasattr(self, 'denoms_tree'):
            return
        self._refresh_denoms_network_filter()
        network = self.var_denoms_network.get()
        self._denoms_all_entries = services.list_denoms_book_entries(
            None if network == 'All' else network,
        )
        self._filter_denoms_table()

    def _filter_denoms_table(self):
        if not hasattr(self, 'denoms_tree'):
            return
        needle = ''
        if hasattr(self, 'var_denoms_filter'):
            needle = self.var_denoms_filter.get().strip().lower()
        rows: list = []
        self._denoms_row_by_iid.clear()
        for idx, entry in enumerate(self._denoms_all_entries):
            net = entry.get('network', '')
            sym = entry.get('symbol', '')
            denom = entry.get('denom_contract', '')
            dec = str(entry.get('decimal', '6'))
            hay = f'{net} {sym} {denom} {dec}'.lower()
            if needle and needle not in hay:
                continue
            rows.append((f'denom-{idx}', (net, sym, denom, dec), entry))
        self._tree_bulk_update = True
        try:
            children = self.denoms_tree.get_children()
            if children:
                self.denoms_tree.delete(*children)
            for iid, values, entry in rows:
                self.denoms_tree.insert('', tk.END, iid=iid, values=values)
                self._denoms_row_by_iid[iid] = entry
        finally:
            self._tree_bulk_update = False
        total = len(self._denoms_all_entries)
        shown = len(rows)
        if needle:
            self.lbl_denoms_status.configure(text=f'{shown} of {total} mapping(s) (filtered)')
        else:
            self.lbl_denoms_status.configure(text=f'{shown} mapping(s)')

    def _denoms_selected_entry(self):
        if not hasattr(self, 'denoms_tree'):
            return None
        item = self._treeview_focus_item(
            self.denoms_tree, last_item_attr='_denoms_tree_last_item',
        )
        if not item:
            return None
        return self._denoms_row_by_iid.get(item)

    def _on_denoms_double_click(self, event):
        self._remember_tree_row(self.denoms_tree, '_denoms_tree_last_item', event)
        self._copy_denoms_denom()

    def _copy_denoms_denom(self):
        if not hasattr(self, 'denoms_tree'):
            return
        item = self._treeview_focus_item(
            self.denoms_tree, last_item_attr='_denoms_tree_last_item',
        )
        if not item:
            messagebox.showinfo('Denoms', 'Select a row first.', parent=self)
            return
        denom = self._treeview_column_value(self.denoms_tree, item, 2)
        if not denom:
            entry = self._denoms_row_by_iid.get(item)
            denom = (entry or {}).get('denom_contract', '').strip()
        if not denom:
            messagebox.showinfo('Denoms', 'No on-chain denom in this row.', parent=self)
            return
        self._copy_text_to_clipboard(denom)
        self.log(f'Copied denom: {denom}')

    def _denoms_entry_dialog(self, title: str, entry: Optional[dict] = None):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()

        net_var = tk.StringVar(value=(entry or {}).get('network', ''))
        sym_var = tk.StringVar(value=(entry or {}).get('symbol', ''))
        denom_var = tk.StringVar(value=(entry or {}).get('denom_contract', ''))
        dec_var = tk.StringVar(value=str((entry or {}).get('decimal', '6')))

        ttk.Label(dialog, text='Network').grid(row=0, column=0, sticky=tk.W, padx=12, pady=6)
        ttk.Entry(dialog, textvariable=net_var, width=28).grid(row=0, column=1, padx=12, pady=6)
        ttk.Label(dialog, text='Symbol').grid(row=1, column=0, sticky=tk.W, padx=12, pady=6)
        ttk.Entry(dialog, textvariable=sym_var, width=28).grid(row=1, column=1, padx=12, pady=6)
        ttk.Label(dialog, text='Denom / contract').grid(row=2, column=0, sticky=tk.W, padx=12, pady=6)
        ttk.Entry(dialog, textvariable=denom_var, width=48).grid(row=2, column=1, padx=12, pady=6)
        ttk.Label(dialog, text='Decimals').grid(row=3, column=0, sticky=tk.W, padx=12, pady=6)
        ttk.Entry(dialog, textvariable=dec_var, width=8).grid(row=3, column=1, sticky=tk.W, padx=12, pady=6)

        def save():
            try:
                dec = int(dec_var.get().strip())
            except ValueError:
                messagebox.showerror(title, 'Decimals must be a whole number.', parent=dialog)
                return
            if dec < 0 or dec > 18:
                messagebox.showerror(title, 'Decimals must be between 0 and 18.', parent=dialog)
                return
            try:
                services.upsert_denoms_book_entry(
                    net_var.get().strip(),
                    sym_var.get().strip(),
                    denom_var.get().strip(),
                    dec,
                )
            except Exception as exc:
                messagebox.showerror(title, str(exc), parent=dialog)
                return
            dialog.destroy()
            self._refresh_denoms_table()
            self._refresh_token_comboboxes_after_denoms()
            self.log(f'Denoms book: {sym_var.get().strip()} on {net_var.get().strip()}')

        btn_row = ttk.Frame(dialog)
        btn_row.grid(row=4, column=0, columnspan=2, pady=12)
        ttk.Button(btn_row, text='Save', command=save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text='Cancel', command=dialog.destroy).pack(side=tk.LEFT, padx=6)

    def _denoms_add_dialog(self):
        self._denoms_entry_dialog('Add token mapping')

    def _denoms_edit_dialog(self):
        entry = self._denoms_selected_entry()
        if not entry:
            messagebox.showinfo('Denoms', 'Select a row to edit.', parent=self)
            return
        self._denoms_entry_dialog('Edit token mapping', entry)

    def _denoms_delete_selected(self):
        entry = self._denoms_selected_entry()
        if not entry:
            messagebox.showinfo('Denoms', 'Select a row to delete.', parent=self)
            return
        sym = entry.get('symbol', '')
        net = entry.get('network', '')
        if not messagebox.askyesno(
            'Denoms',
            f'Delete mapping {sym} on {net}?',
            parent=self,
        ):
            return
        if services.delete_denoms_book_entry(net, entry.get('denom_contract', '')):
            self._refresh_denoms_table()
            self._refresh_token_comboboxes_after_denoms()
            self.log(f'Deleted denoms mapping: {sym} on {net}')
        else:
            messagebox.showerror('Denoms', 'Could not delete entry.', parent=self)

    def _build_addresses_tab(self):
        ttk.Label(
            self.tab_addresses,
            text=(
                'Addresses are derived from the vault mnemonic when you enable a chain on Networks (✓). '
                'Vault unlock files must be present (Setup → Secret vault). '
                'Disabled chains are hidden here.'
            ),
            wraplength=920,
        ).pack(anchor=tk.W, pady=(0, 8))
        toolbar = ttk.Frame(self.tab_addresses)
        toolbar.pack(fill=tk.X)
        self.var_addr_filter = tk.StringVar()
        self.var_addr_filter.trace_add('write', lambda *_a: self._filter_addresses())
        self.var_addr_show_all = tk.BooleanVar(value=False)
        self.var_addr_all_wallets = tk.BooleanVar(
            value=bool(self.settings.get('address_book_all_wallets', False)),
        )
        ttk.Label(toolbar, text='Filter:').pack(side=tk.LEFT)
        ttk.Entry(toolbar, textvariable=self.var_addr_filter, width=24).pack(side=tk.LEFT, padx=6)
        wallet_scope = ttk.Frame(toolbar)
        wallet_scope.pack(side=tk.LEFT, padx=(8, 6))
        ttk.Label(wallet_scope, text='Wallets:').pack(side=tk.LEFT)
        ttk.Radiobutton(
            wallet_scope,
            text='Active only',
            variable=self.var_addr_all_wallets,
            value=False,
            command=self._on_address_book_wallet_scope_changed,
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Radiobutton(
            wallet_scope,
            text='All wallets',
            variable=self.var_addr_all_wallets,
            value=True,
            command=self._on_address_book_wallet_scope_changed,
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Checkbutton(
            toolbar,
            text='All networks in file',
            variable=self.var_addr_show_all,
            command=self._load_addresses,
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text='Reload', command=self._load_addresses).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text='Copy address', command=self._copy_address_book_address).pack(
            side=tk.LEFT, padx=(0, 6),
        )
        ttk.Button(toolbar, text='Update address book', command=self._sync_address_book).pack(side=tk.LEFT)
        self._muted_label(
            self.tab_addresses,
            text='Select a row and click Copy address, or double-click a row.',
            wraplength=920,
        ).pack(anchor=tk.W, pady=(0, 4))

        cols = ('name', 'network', 'address')
        self.addr_tree = ttk.Treeview(self.tab_addresses, columns=cols, show='headings', height=20)
        for col, title, width in [('name', 'Name', 160), ('network', 'Network', 120), ('address', 'Address', 420)]:
            self.addr_tree.heading(col, text=title)
            self.addr_tree.column(col, width=width, stretch=col == 'address')
        scroll = ttk.Scrollbar(self.tab_addresses, orient=tk.VERTICAL, command=self.addr_tree.yview)
        self.addr_tree.configure(yscrollcommand=scroll.set)
        self.addr_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)
        self._addr_tree_last_item = None
        self.addr_tree.bind('<<TreeviewSelect>>', lambda _e: self._remember_tree_row(
            self.addr_tree, '_addr_tree_last_item',
        ))
        self.addr_tree.bind(
            '<ButtonRelease-1>',
            lambda e: self._remember_tree_row(self.addr_tree, '_addr_tree_last_item', e),
        )
        self.addr_tree.bind('<Double-1>', self._on_address_book_double_click)
        self.addr_tree.bind('<Control-c>', lambda _e: self._copy_address_book_address())

        self._address_entries = []
        self._tree_bulk_update = False
        self.lbl_addr_scope = self._muted_label(self.tab_addresses, text='')
        self.lbl_addr_scope.pack(anchor=tk.W, pady=(0, 4))
        self.after(0, self._load_addresses)

    def _on_address_book_wallet_scope_changed(self):
        if hasattr(self, 'var_addr_all_wallets'):
            self.settings['address_book_all_wallets'] = bool(self.var_addr_all_wallets.get())
            save_settings(self.settings)
        self._load_addresses()

    def _load_addresses(self):
        show_all_nets = bool(self.var_addr_show_all.get()) if hasattr(self, 'var_addr_show_all') else False
        all_wallets = bool(self.var_addr_all_wallets.get()) if hasattr(self, 'var_addr_all_wallets') else False
        self._address_entries = services.load_address_book_entries(
            all_networks=show_all_nets,
            all_wallets=all_wallets,
        )
        if hasattr(self, 'lbl_addr_scope'):
            wid, label = services.active_wallet_display()
            if all_wallets:
                self.lbl_addr_scope.configure(
                    text=f'Showing all wallets in address book ({len(self._address_entries)} row(s)).',
                )
            else:
                self.lbl_addr_scope.configure(
                    text=f'Showing active wallet only: {label} ({wid}) — {len(self._address_entries)} row(s).',
                )
        self._filter_addresses()

    def _sync_address_book(self):
        from gui.setup_catalog import get_action_warnings

        warnings = get_action_warnings('address_book')
        if not self._confirm_setup_warnings('Update address book', warnings):
            return

        def worker():
            return services.run_setup_action('address_book')

        def on_success(text):
            self.log(text)
            self._load_addresses()
            messagebox.showinfo(
                'Address book',
                'Address book rebuilt for all chains in wallets_list.\n'
                'Use Networks to choose which ones appear in the wallet view.',
            )

        self._run_async('Address book', worker, on_success=on_success)

    def _filter_addresses(self):
        if not hasattr(self, 'addr_tree'):
            return
        needle = self.var_addr_filter.get().strip().lower()
        rows = []
        for idx, entry in enumerate(self._address_entries):
            hay = f'{entry.get("name", "")} {entry.get("network", "")} {entry.get("address", "")}'.lower()
            if needle and needle not in hay:
                continue
            rows.append(
                (
                    f'addr-{idx}',
                    (entry.get('name', ''), entry.get('network', ''), entry.get('address', '')),
                )
            )
        self._tree_bulk_update = True
        try:
            children = self.addr_tree.get_children()
            if children:
                self.addr_tree.delete(*children)
            for iid, values in rows:
                self.addr_tree.insert('', tk.END, iid=iid, values=values)
        finally:
            self._tree_bulk_update = False

    def _on_address_book_double_click(self, event):
        self._remember_tree_row(self.addr_tree, '_addr_tree_last_item', event)
        self._copy_address_book_address()

    def _copy_address_book_address(self):
        if not hasattr(self, 'addr_tree'):
            return
        item = self._treeview_focus_item(
            self.addr_tree, last_item_attr='_addr_tree_last_item',
        )
        if not item:
            messagebox.showinfo('Address book', 'Select a row first.')
            return
        address = self._treeview_column_value(self.addr_tree, item, 2)
        if not address:
            messagebox.showinfo('Address book', 'No address in this row.')
            return
        self._copy_text_to_clipboard(address)
        self.log(f'Copied address: {address}')

    def _build_osmosis_tab(self):
        ttk.Label(
            self.tab_osmosis,
            text=(
                'Market — Osmosis DEX prices (Numia API). Top tokens by 24h volume. '
                'Row tint reflects 24h % change. Click column headers to sort.'
            ),
            wraplength=700,
        ).pack(anchor=tk.W, pady=(0, 8))
        toolbar = ttk.Frame(self.tab_osmosis)
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text='Search:').pack(side=tk.LEFT, padx=(0, 6))
        self.var_osmo_search = tk.StringVar()
        osmo_search = ttk.Entry(toolbar, textvariable=self.var_osmo_search, width=18)
        osmo_search.pack(side=tk.LEFT, padx=(0, 10))
        osmo_search.bind('<Return>', lambda _e: self._on_osmo_filter_changed())
        self.var_osmo_search.trace_add('write', lambda *_a: self._on_osmo_filter_changed())
        liq_scope = ttk.Frame(toolbar)
        liq_scope.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(liq_scope, text='Show:').pack(side=tk.LEFT)
        self.var_market_liquidity_only = tk.BooleanVar(
            value=bool(self.settings.get('market_liquidity_only', False)),
        )
        ttk.Radiobutton(
            liq_scope,
            text='All',
            variable=self.var_market_liquidity_only,
            value=False,
            command=self._on_market_scope_changed,
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Radiobutton(
            liq_scope,
            text='Liquidity > 0',
            variable=self.var_market_liquidity_only,
            value=True,
            command=self._on_market_scope_changed,
        ).pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(
            toolbar,
            text='Refresh',
            command=lambda: self._load_osmosis(force=True),
        ).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(toolbar, text='Columns…', command=self._market_choose_columns).pack(side=tk.LEFT, padx=(0, 8))
        self.var_market_auto = tk.BooleanVar(value=bool(self.settings.get('market_auto_refresh', False)))
        ttk.Checkbutton(
            toolbar,
            text='Auto-refresh',
            variable=self.var_market_auto,
            command=self._on_market_auto_changed,
        ).pack(side=tk.LEFT)
        msec = max(30, min(86400, int(self.settings.get('market_auto_refresh_seconds', 3600))))
        self.var_market_auto_sec = tk.StringVar(value=str(msec))
        ttk.Label(toolbar, text='every').pack(side=tk.LEFT, padx=(8, 2))
        self.spin_market_auto_sec = ttk.Spinbox(
            toolbar,
            from_=30,
            to=86400,
            width=7,
            textvariable=self.var_market_auto_sec,
        )
        self.spin_market_auto_sec.pack(side=tk.LEFT, padx=(0, 2))
        ttk.Label(toolbar, text='s').pack(side=tk.LEFT)
        self.spin_market_auto_sec.bind('<FocusOut>', lambda _e: self._save_market_auto_interval())
        self.spin_market_auto_sec.bind('<Return>', lambda _e: self._save_market_auto_interval())
        self._muted_label(
            toolbar,
            text='  Search: symbol / denom / name. Columns… to show/hide. Click headers to sort.',
            track=False,
        ).pack(side=tk.LEFT, padx=(8, 0))

        limit_row = ttk.Frame(self.tab_osmosis)
        limit_row.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(limit_row, text='Numia list:').pack(side=tk.LEFT, padx=(0, 8))
        _m = self.settings.get('market_tokens_limit_mode', 'limit')
        if _m not in ('all', 'limit'):
            _m = 'limit'
        self.var_market_tokens_mode = tk.StringVar(value=_m)
        ttk.Radiobutton(
            limit_row,
            text='All rows (full API response)',
            variable=self.var_market_tokens_mode,
            value='all',
            command=self._on_market_tokens_limit_changed,
        ).pack(side=tk.LEFT)
        ttk.Radiobutton(
            limit_row,
            text='Top N by 24h volume',
            variable=self.var_market_tokens_mode,
            value='limit',
            command=self._on_market_tokens_limit_changed,
        ).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(limit_row, text='N =').pack(side=tk.LEFT, padx=(12, 4))
        _n = max(1, min(100_000, int(self.settings.get('market_tokens_limit_count', 500))))
        self.var_market_tokens_limit_count = tk.StringVar(value=str(_n))
        self.spin_market_tokens_limit = ttk.Spinbox(
            limit_row,
            from_=1,
            to=100000,
            width=8,
            textvariable=self.var_market_tokens_limit_count,
        )
        self.spin_market_tokens_limit.pack(side=tk.LEFT)
        self.spin_market_tokens_limit.bind('<FocusOut>', lambda _e: self._save_market_tokens_limit_count())
        self.spin_market_tokens_limit.bind('<Return>', lambda _e: self._save_market_tokens_limit_count())
        self._muted_label(
            limit_row,
            text='  Apply on Refresh. Full list may take longer.',
            track=False,
        ).pack(side=tk.LEFT, padx=(10, 0))
        self._update_market_limit_spin_state()

        self._osmo_rows: list = []
        from gui.market_view import (
            MARKET_COLUMN_IDS,
            MARKET_COLUMN_LAYOUT,
            MARKET_COLUMN_TITLES,
            normalize_sort_column,
        )

        self._osmo_heading_titles = dict(MARKET_COLUMN_TITLES)
        self._osmo_sort_col = normalize_sort_column(self.settings.get('market_sort_column', 'volume'))
        self._osmo_sort_reverse = bool(self.settings.get('market_sort_reverse', True))

        cols = tuple(MARKET_COLUMN_IDS)
        tree_frame = ttk.Frame(self.tab_osmosis)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=8)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.osmo_tree = ttk.Treeview(tree_frame, columns=cols, show='headings', height=20)
        for col_id, _width, stretch in MARKET_COLUMN_LAYOUT:
            self.osmo_tree.heading(
                col_id,
                text=MARKET_COLUMN_TITLES[col_id],
                command=lambda c=col_id: self._sort_osmo_column(c),
            )
            self.osmo_tree.column(col_id, width=_width, stretch=stretch, minwidth=40)
        vscroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.osmo_tree.yview)
        hscroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.osmo_tree.xview)
        self.osmo_tree.configure(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)
        self.osmo_tree.grid(row=0, column=0, sticky='nsew')
        vscroll.grid(row=0, column=1, sticky='ns')
        hscroll.grid(row=1, column=0, sticky='ew')
        self.osmo_tree.bind('<ButtonRelease-1>', self._on_osmo_tree_release)
        from gui.market_colors import configure_market_change_tags

        configure_market_change_tags(
            self.osmo_tree,
            bg=self.colors.bg,
            fg=self.colors.fg,
            success=self.colors.success,
            error=self.colors.error,
            muted=self.colors.muted,
        )
        self.lbl_osmo_status = self._muted_label(
            self.tab_osmosis,
            text='No cached data — click Refresh to load from Numia API.',
        )
        self.lbl_osmo_status.pack(anchor=tk.W, pady=(0, 4))
        self._market_cached_at_iso: Optional[str] = None
        self._apply_market_column_layout()
        self._try_restore_market_cache()

    def _market_visible_columns(self) -> list:
        from gui.market_view import normalize_visible_columns

        return normalize_visible_columns(self.settings.get('market_visible_columns'))

    def _apply_market_column_layout(self):
        if not hasattr(self, 'osmo_tree'):
            return
        from gui.market_view import MARKET_COLUMN_IDS, normalize_column_widths

        self.osmo_tree['displaycolumns'] = self._market_visible_columns()
        widths = normalize_column_widths(self.settings.get('market_column_widths'))
        for col_id in MARKET_COLUMN_IDS:
            self.osmo_tree.column(col_id, width=widths[col_id])

    def _save_market_tree_layout(self):
        if not hasattr(self, 'osmo_tree'):
            return
        from gui.market_view import MARKET_COLUMN_IDS

        dc = self.osmo_tree['displaycolumns']
        if dc and dc != '#all':
            order = [c for c in dc if c in MARKET_COLUMN_IDS]
            if order:
                self.settings['market_visible_columns'] = order
        widths = {}
        for col_id in MARKET_COLUMN_IDS:
            try:
                widths[col_id] = int(self.osmo_tree.column(col_id, 'width'))
            except (tk.TclError, TypeError, ValueError):
                pass
        if widths:
            self.settings['market_column_widths'] = widths
        self.settings['market_sort_column'] = self._osmo_sort_col
        self.settings['market_sort_reverse'] = bool(self._osmo_sort_reverse)
        save_settings(self.settings)

    def _on_osmo_tree_release(self, event):
        if not hasattr(self, 'osmo_tree'):
            return
        region = self.osmo_tree.identify_region(event.x, event.y)
        if region in ('separator', 'heading'):
            self._save_market_tree_layout()

    def _market_choose_columns(self):
        from gui.market_view import MARKET_COLUMN_IDS, MARKET_COLUMN_TITLES

        dialog = tk.Toplevel(self)
        dialog.title('Market columns')
        dialog.transient(self)
        dialog.grab_set()
        ttk.Label(dialog, text='Show columns (at least one):').pack(anchor=tk.W, padx=12, pady=(12, 6))
        vars_map: dict = {}
        visible = set(self._market_visible_columns())
        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=12)
        for col_id in MARKET_COLUMN_IDS:
            var = tk.BooleanVar(value=col_id in visible)
            vars_map[col_id] = var
            ttk.Checkbutton(
                frame,
                text=MARKET_COLUMN_TITLES.get(col_id, col_id),
                variable=var,
            ).pack(anchor=tk.W)

        def save():
            prev_order = self._market_visible_columns()
            chosen = [c for c in prev_order if vars_map[c].get()]
            for col_id in MARKET_COLUMN_IDS:
                if col_id not in chosen and vars_map[col_id].get():
                    chosen.append(col_id)
            if not chosen:
                messagebox.showerror('Columns', 'Select at least one column.', parent=dialog)
                return
            self.settings['market_visible_columns'] = chosen
            dialog.destroy()
            self._apply_market_column_layout()
            self._save_market_tree_layout()
            self._render_osmo_table()

        btn_row = ttk.Frame(dialog)
        btn_row.pack(pady=12)
        ttk.Button(btn_row, text='Apply', command=save).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text='Cancel', command=dialog.destroy).pack(side=tk.LEFT, padx=6)

    def _market_disk_cache_key(self) -> str:
        if self.settings.get('market_tokens_limit_mode', 'limit') == 'all':
            return 'all'
        try:
            n = int(self.settings.get('market_tokens_limit_count', 500))
        except (TypeError, ValueError):
            n = 500
        n = max(1, min(100_000, n))
        return f'top_{n}'

    def _market_fetch_limit_optional(self) -> Optional[int]:
        if self.settings.get('market_tokens_limit_mode', 'limit') == 'all':
            return None
        try:
            n = int(self.settings.get('market_tokens_limit_count', 500))
        except (TypeError, ValueError):
            n = 500
        return max(1, min(100_000, n))

    def _update_market_limit_spin_state(self):
        if not hasattr(self, 'spin_market_tokens_limit'):
            return
        lim = self.var_market_tokens_mode.get() == 'limit'
        self.spin_market_tokens_limit.configure(state='normal' if lim else 'disabled')

    def _on_market_tokens_limit_changed(self):
        mode = self.var_market_tokens_mode.get()
        if mode not in ('all', 'limit'):
            mode = 'limit'
        self.settings['market_tokens_limit_mode'] = mode
        self.var_market_tokens_mode.set(mode)
        if mode == 'limit':
            self._save_market_tokens_limit_count()
        else:
            save_settings(self.settings)
        self._update_market_limit_spin_state()
        if self._try_restore_market_cache():
            return
        self._osmo_rows = []
        if hasattr(self, 'osmo_tree'):
            self._render_osmo_table()
        if hasattr(self, 'lbl_osmo_status'):
            self.lbl_osmo_status.configure(
                text='No cache for this list mode — click Refresh to load from Numia.',
            )

    def _save_market_tokens_limit_count(self):
        if not hasattr(self, 'var_market_tokens_limit_count'):
            return
        try:
            n = int(self.var_market_tokens_limit_count.get().strip())
        except ValueError:
            n = 500
        n = max(1, min(100_000, n))
        self.var_market_tokens_limit_count.set(str(n))
        self.settings['market_tokens_limit_count'] = n
        save_settings(self.settings)
        if self.settings.get('market_tokens_limit_mode') == 'limit':
            if self._try_restore_market_cache():
                return
            self._osmo_rows = []
            if hasattr(self, 'osmo_tree'):
                self._render_osmo_table()
            if hasattr(self, 'lbl_osmo_status'):
                self.lbl_osmo_status.configure(
                    text='No cache for this N — click Refresh to load from Numia.',
                )

    def _osmo_liquidity_value(self, row: dict) -> float:
        try:
            return float(row.get('liquidity') or 0)
        except (TypeError, ValueError):
            return 0.0

    def _osmo_matches_search(self, row: dict, needle: str) -> bool:
        needle = (needle or '').strip().lower()
        if not needle:
            return True
        for key in ('symbol', 'denom', 'display', 'name'):
            if needle in (row.get(key) or '').lower():
                return True
        return False

    def _osmo_filtered_rows(self) -> list:
        rows = list(self._osmo_rows)
        liq_only = bool(self.var_market_liquidity_only.get()) if hasattr(self, 'var_market_liquidity_only') else False
        if liq_only:
            rows = [r for r in rows if self._osmo_liquidity_value(r) > 0]
        needle = self.var_osmo_search.get() if hasattr(self, 'var_osmo_search') else ''
        rows = [r for r in rows if self._osmo_matches_search(r, needle)]
        return rows

    def _on_osmo_filter_changed(self):
        if self._osmo_rows:
            self._render_osmo_table()

    def _on_market_scope_changed(self):
        if hasattr(self, 'var_market_liquidity_only'):
            self.settings['market_liquidity_only'] = bool(self.var_market_liquidity_only.get())
            save_settings(self.settings)
        self._on_osmo_filter_changed()

    def _osmo_sort_key(self, row: dict, column: str):
        if column in ('symbol', 'denom'):
            return (row.get(column) or '').lower()
        field = {
            'price': 'price',
            'liquidity': 'liquidity',
            'volume': 'volume_24h',
            'chg24': 'price_24h_change',
            'chg7': 'price_7d_change',
        }.get(column, column)
        try:
            return float(row.get(field) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _sort_osmo_column(self, column: str):
        if self._osmo_sort_col == column:
            self._osmo_sort_reverse = not self._osmo_sort_reverse
        else:
            self._osmo_sort_col = column
            self._osmo_sort_reverse = column not in ('symbol', 'denom')
        self._save_market_tree_layout()
        self._render_osmo_table()

    def _update_osmo_headings(self):
        for col, base in self._osmo_heading_titles.items():
            arrow = ''
            if col == self._osmo_sort_col:
                arrow = ' ▼' if self._osmo_sort_reverse else ' ▲'
            self.osmo_tree.heading(col, text=base + arrow)

    def _render_osmo_table(self):
        from gui.market_colors import change_row_tag
        from gui.market_view import market_row_display_values

        rows = self._osmo_filtered_rows()
        rows.sort(key=lambda r: self._osmo_sort_key(r, self._osmo_sort_col), reverse=self._osmo_sort_reverse)
        max_abs_24 = 1.0
        for row in rows:
            try:
                max_abs_24 = max(max_abs_24, abs(float(row.get('price_24h_change') or 0)))
            except (TypeError, ValueError):
                pass
        for item in self.osmo_tree.get_children():
            self.osmo_tree.delete(item)
        for row in rows:
            tag = change_row_tag(row.get('price_24h_change'), max_abs_24)
            self.osmo_tree.insert(
                '',
                tk.END,
                values=market_row_display_values(row),
                tags=(tag,),
            )
        self._update_osmo_headings()
        if hasattr(self, 'lbl_osmo_status'):
            total = len(self._osmo_rows)
            shown = len(rows)
            parts = [f'Showing {shown} of {total} loaded row(s)']
            lim = self._market_fetch_limit_optional()
            if lim is None:
                parts.append('Numia: all rows')
            else:
                parts.append(f'Numia: top {lim} by volume')
            if getattr(self, '_market_cached_at_iso', None):
                parts.append(f'cache {self._market_cached_at_iso}')
            if self.var_market_liquidity_only.get():
                parts.append('liquidity > 0')
            sym = self.var_osmo_search.get().strip() if hasattr(self, 'var_osmo_search') else ''
            if sym:
                parts.append(f'search “{sym}”')
            self.lbl_osmo_status.configure(text=' · '.join(parts))

    def _market_auto_refresh_seconds(self) -> int:
        if hasattr(self, 'var_market_auto_sec'):
            return self._clamp_tab_refresh_seconds(self.var_market_auto_sec.get())
        return self._clamp_tab_refresh_seconds(self.settings.get('market_auto_refresh_seconds', 3600))

    def _save_market_auto_interval(self):
        if not hasattr(self, 'var_market_auto_sec'):
            return
        sec = self._market_auto_refresh_seconds()
        self.settings['market_auto_refresh_seconds'] = sec
        self.var_market_auto_sec.set(str(sec))
        save_settings(self.settings)

    def _on_market_auto_changed(self):
        self.settings['market_auto_refresh'] = bool(self.var_market_auto.get())
        if hasattr(self, 'var_market_auto_sec'):
            self.settings['market_auto_refresh_seconds'] = self._market_auto_refresh_seconds()
        save_settings(self.settings)

    def _market_cache_stale(self) -> bool:
        env = services.load_market_tab_cache(self._market_disk_cache_key())
        if not env:
            return True
        sec = self._market_auto_refresh_seconds()
        age = time.time() - float(env.get('cached_at', 0))
        return age > sec

    def _maybe_auto_refresh_market(self):
        if not self.settings.get('market_auto_refresh'):
            return
        if self._market_cache_stale():
            self._load_osmosis(force=True)

    def _apply_market_rows(self, rows: list, cached_at_iso: Optional[str] = None):
        self._osmo_rows = services.prepare_market_rows(rows)
        self._market_cached_at_iso = cached_at_iso
        self._render_osmo_table()

    def _try_restore_market_cache(self) -> bool:
        env = services.load_market_tab_cache(self._market_disk_cache_key())
        if not env:
            return False
        payload = env.get('payload') or {}
        self._apply_market_rows(payload.get('rows', []), env.get('cached_at_iso'))
        return True

    def _load_osmosis(self, force: bool = False):
        if not force and self._try_restore_market_cache():
            return

        def worker():
            lim = self._market_fetch_limit_optional()
            return services.fetch_osmosis_tokens(limit=lim)

        def on_success(rows):
            prepared = services.prepare_market_rows(rows)
            services.save_market_tab_cache(prepared, self._market_disk_cache_key())
            env = services.load_market_tab_cache(self._market_disk_cache_key())
            cached_iso = env.get('cached_at_iso') if env else None
            self._apply_market_rows(prepared, cached_iso)
            if hasattr(self, 'lbl_osmo_status'):
                self.log('Market refreshed: ' + self.lbl_osmo_status.cget('text'))

        self._run_async('Osmosis DEX', worker, on_success=on_success)

    def _build_setup_tab(self):
        outer = ttk.Frame(self.tab_setup)
        outer.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(outer, highlightthickness=0)
        self._setup_canvas = canvas
        style_canvas(canvas, self.colors)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        scroll = ttk.Frame(canvas)
        scroll.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        canvas.bind_all('<MouseWheel>', _on_mousewheel)

        vault_box = ttk.LabelFrame(scroll, text='Secret vault (KeePass)', padding=10)
        vault_box.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(
            vault_box,
            text=(
                f'Storage: {ConfigPath.secrets_path}\n'
                'Files: wallet.kdbx, wallet.key, master.password\n'
                'Copy key + password from USB when trading; delete them locally when idle.'
            ),
            wraplength=680,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 8))
        vault_btns = ttk.Frame(vault_box)
        vault_btns.pack(anchor=tk.W)
        ttk.Button(vault_btns, text='Create / reset vault', command=self._create_vault).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(vault_btns, text='View / edit mnemonic', command=self._edit_mnemonic).pack(side=tk.LEFT)

        first_run = ttk.LabelFrame(
            scroll,
            text='First launch — full pipeline',
            padding=10,
        )
        first_run.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(
            first_run,
            text=(
                'Runs all required steps in order: source → dependencies → cosmos_data_list → '
                'clients → wallets → address book. May take several minutes (registry clone, pip). '
                'Create the secret vault first (button above) if it does not exist yet.'
            ),
            wraplength=680,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 8))

        ttk.Button(
            first_run,
            text='Run first-time setup',
            command=self._run_first_run_pipeline,
        ).pack(anchor=tk.W)

        opts = ttk.LabelFrame(scroll, text='Ledger client options', padding=8)
        opts.pack(fill=tk.X, pady=(0, 10))

        self.var_link_type = tk.StringVar(value=self.settings.get('ledger_link_type', 'keplr_rest_link'))
        link_row = ttk.Frame(opts)
        link_row.pack(anchor=tk.W)
        ttk.Label(link_row, text='REST field in cosmos_data_list:').pack(side=tk.LEFT)
        ttk.Combobox(
            link_row,
            textvariable=self.var_link_type,
            values=['rest_link', 'keplr_rest_link'],
            state='readonly',
            width=20,
        ).pack(side=tk.LEFT, padx=8)
        self._muted_label(
            opts,
            text='Used for “Generate ledger clients” and the full first-time pipeline.',
            wraplength=680,
        ).pack(anchor=tk.W, pady=(6, 0))

        steps = ttk.LabelFrame(scroll, text='Individual steps', padding=8)
        steps.pack(fill=tk.BOTH, expand=True)

        for action in services.list_setup_actions():
            block = ttk.Frame(steps)
            block.pack(fill=tk.X, pady=6)

            header = ttk.Frame(block)
            header.pack(fill=tk.X)
            title = action.title
            if action.in_first_run:
                title = f'[{action.id}] {title}'
            ttk.Label(header, text=title, font=('', 10, 'bold')).pack(side=tk.LEFT, anchor=tk.W)

            self._muted_label(
                block,
                text=action.description,
                wraplength=620,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=(2, 4))

            ttk.Button(
                block,
                text='Run',
                command=lambda aid=action.id: self._run_setup(aid),
            ).pack(anchor=tk.W)

            ttk.Separator(steps, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=4)

    def _confirm_setup_warnings(self, title: str, warnings: list) -> bool:
        if not warnings:
            return True
        body = '\n'.join(f'• {w}' for w in warnings)
        body += '\n\nContinue? Existing files may be overwritten.'
        return messagebox.askyesno(title, body, icon=messagebox.WARNING)

    def _build_settings_tab(self):
        appearance = ttk.LabelFrame(self.tab_settings, text='Appearance', padding=12)
        appearance.pack(fill=tk.X, anchor=tk.W)

        row = ttk.Frame(appearance)
        row.pack(fill=tk.X, anchor=tk.W, pady=4)
        ttk.Label(row, text='Color theme:').pack(side=tk.LEFT)

        self.var_theme = tk.StringVar(value=self.settings.get('theme', DEFAULT_THEME))
        self._theme_label_by_id = theme_labels_map()
        self._theme_id_by_label = {label: theme_id for theme_id, label in self._theme_label_by_id.items()}

        display_values = list(self._theme_label_by_id.values())
        current_label = self._theme_label_by_id.get(self.var_theme.get(), self._theme_label_by_id[DEFAULT_THEME])
        self.var_theme_display = tk.StringVar(value=current_label)

        theme_combo = ttk.Combobox(
            row,
            textvariable=self.var_theme_display,
            values=display_values,
            state='readonly',
            width=36,
        )
        theme_combo.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)
        theme_combo.bind('<<ComboboxSelected>>', self._on_theme_selected)

        theme_btns = ttk.Frame(appearance)
        theme_btns.pack(fill=tk.X, anchor=tk.W, pady=(8, 0))
        ttk.Button(theme_btns, text='Edit custom colors…', command=self._edit_custom_theme).pack(side=tk.LEFT)
        ttk.Button(theme_btns, text='Apply theme', command=lambda: self._apply_theme(self.var_theme.get())).pack(
            side=tk.LEFT, padx=(8, 0)
        )

        self._muted_label(
            appearance,
            text='Themes: Dark, Light, Dracula, Nord, Gruvbox, One Dark, Rosé Pine, Solarized, Midnight, Forest, Custom.',
            wraplength=640,
        ).pack(anchor=tk.W, pady=(8, 0))

        interface = ttk.LabelFrame(self.tab_settings, text='Interface', padding=12)
        interface.pack(fill=tk.X, anchor=tk.W, pady=(16, 0))

        self.var_show_log = tk.BooleanVar(value=bool(self.settings.get('show_log_panel', True)))
        ttk.Checkbutton(
            interface,
            text='Show log panel on the right',
            variable=self.var_show_log,
            command=self._on_log_panel_toggle,
        ).pack(anchor=tk.W)
        self._muted_label(
            interface,
            text='Hide for a wider workspace; log output is still buffered and shown when re-enabled.',
            wraplength=640,
        ).pack(anchor=tk.W, pady=(6, 0))

        wallet = ttk.LabelFrame(self.tab_settings, text='Wallet', padding=12)
        wallet.pack(fill=tk.X, anchor=tk.W, pady=(16, 0))

        link_row = ttk.Frame(wallet)
        link_row.pack(anchor=tk.W, pady=4)
        ttk.Label(link_row, text='Ledger REST source:').pack(side=tk.LEFT)
        self.var_settings_link = tk.StringVar(value=self.settings.get('ledger_link_type', 'keplr_rest_link'))
        link_combo = ttk.Combobox(
            link_row,
            textvariable=self.var_settings_link,
            values=['keplr_rest_link', 'rest_link'],
            state='readonly',
            width=22,
        )
        link_combo.pack(side=tk.LEFT, padx=8)
        link_combo.bind('<<ComboboxSelected>>', self._on_wallet_settings_changed)

        self.var_auto_balance = tk.BooleanVar(value=bool(self.settings.get('auto_refresh_balances', True)))
        ttk.Checkbutton(
            wallet,
            text='Auto-refresh balances (Portfolio, Send)',
            variable=self.var_auto_balance,
            command=self._on_wallet_settings_changed,
        ).pack(anchor=tk.W, pady=(8, 0))

        self.var_show_fiat = tk.BooleanVar(value=bool(self.settings.get('show_fiat_prices', True)))
        ttk.Checkbutton(
            wallet,
            text='Show approximate USD on Portfolio (CoinGecko, Keplr-style)',
            variable=self.var_show_fiat,
            command=self._on_wallet_settings_changed,
        ).pack(anchor=tk.W, pady=(4, 0))

        interval_row = ttk.Frame(wallet)
        interval_row.pack(anchor=tk.W, pady=6)
        ttk.Label(interval_row, text='Refresh every (seconds):').pack(side=tk.LEFT)
        self.var_balance_interval = tk.StringVar(
            value=str(int(self.settings.get('balance_refresh_seconds', 60))),
        )
        spin = ttk.Spinbox(interval_row, from_=15, to=600, width=8, textvariable=self.var_balance_interval)
        spin.pack(side=tk.LEFT, padx=8)
        spin.bind('<FocusOut>', lambda _e: self._on_wallet_settings_changed())
        spin.bind('<Return>', lambda _e: self._on_wallet_settings_changed())

        cache_row = ttk.Frame(wallet)
        cache_row.pack(anchor=tk.W, pady=6)
        ttk.Label(cache_row, text='Balance cache (seconds):').pack(side=tk.LEFT)
        self.var_balance_cache = tk.StringVar(
            value=str(int(self.settings.get('balance_cache_seconds', 30))),
        )
        cache_spin = ttk.Spinbox(cache_row, from_=0, to=600, width=8, textvariable=self.var_balance_cache)
        cache_spin.pack(side=tk.LEFT, padx=8)
        cache_spin.bind('<FocusOut>', lambda _e: self._on_wallet_settings_changed())
        cache_spin.bind('<Return>', lambda _e: self._on_wallet_settings_changed())
        self._muted_label(
            cache_row,
            text='0 = always query chain; reuse snapshot for Send token list and balance labels.',
            track=False,
        ).pack(side=tk.LEFT, padx=(8, 0))

        self._muted_label(
            wallet,
            text='Address book and balances use networks enabled under Networks (default Osmosis, Cosmos).',
            wraplength=640,
        ).pack(anchor=tk.W, pady=(6, 0))

        send_opts = ttk.LabelFrame(self.tab_settings, text='Send', padding=12)
        send_opts.pack(fill=tk.X, anchor=tk.W, pady=(16, 0))
        ttk.Label(send_opts, text='Token list on Send tab:').pack(anchor=tk.W)
        self.var_settings_send_token_list = tk.StringVar(
            value=self.settings.get('send_token_list_mode', 'nonzero'),
        )
        send_mode_row = ttk.Frame(send_opts)
        send_mode_row.pack(anchor=tk.W, pady=4)
        ttk.Radiobutton(
            send_mode_row,
            text='Only tokens with balance on source network (includes IBC via REST)',
            variable=self.var_settings_send_token_list,
            value='nonzero',
            command=self._on_wallet_settings_changed,
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            send_mode_row,
            text='All symbols from catalog / denoms book',
            variable=self.var_settings_send_token_list,
            value='all',
            command=self._on_wallet_settings_changed,
        ).pack(anchor=tk.W, pady=(2, 0))

        about = ttk.LabelFrame(self.tab_settings, text='About', padding=12)
        about.pack(fill=tk.X, anchor=tk.W, pady=(16, 0))
        ttk.Label(
            about,
            text='Cosmos Crypto Transfer — IBC transfers, balances, and address book for Cosmos chains.',
            wraplength=640,
        ).pack(anchor=tk.W)

    def _on_wallet_settings_changed(self, _event=None):
        self.settings['ledger_link_type'] = self.var_settings_link.get()
        self.settings['auto_refresh_balances'] = bool(self.var_auto_balance.get())
        self.settings['show_fiat_prices'] = bool(self.var_show_fiat.get())
        try:
            seconds = int(self.var_balance_interval.get().strip())
        except ValueError:
            seconds = 60
        self.settings['balance_refresh_seconds'] = max(15, min(600, seconds))
        try:
            cache_sec = int(self.var_balance_cache.get().strip())
        except ValueError:
            cache_sec = 30
        self.settings['balance_cache_seconds'] = max(0, min(600, cache_sec))
        if hasattr(self, 'var_balance_cache'):
            self.var_balance_cache.set(str(int(self.settings['balance_cache_seconds'])))
        if hasattr(self, 'var_settings_send_token_list'):
            self.settings['send_token_list_mode'] = self.var_settings_send_token_list.get()
            if hasattr(self, 'var_send_token_list'):
                self.var_send_token_list.set(self.settings['send_token_list_mode'])
        self.var_balance_interval.set(str(self.settings['balance_refresh_seconds']))
        if hasattr(self, 'var_link_type'):
            self.var_link_type.set(self.settings['ledger_link_type'])
        save_settings(self.settings)
        self.log('Wallet settings saved.')

    def _on_theme_selected(self, _event=None):
        label = self.var_theme_display.get()
        theme_id = self._theme_id_by_label.get(label, DEFAULT_THEME)
        self.var_theme.set(theme_id)
        self.settings['theme'] = theme_id
        save_settings(self.settings)
        self._apply_theme(theme_id)
        self._apply_log_panel_visibility()
        self.log(f'Theme changed to {label}.')

    def _edit_custom_theme(self):
        def on_save(colors):
            self.settings['custom_colors'] = colors
            self.settings['theme'] = CUSTOM_THEME_ID
            self.var_theme.set(CUSTOM_THEME_ID)
            self.var_theme_display.set(self._theme_label_by_id[CUSTOM_THEME_ID])
            save_settings(self.settings)
            self._apply_theme(CUSTOM_THEME_ID)
            self.log('Custom theme colors saved.')

        open_custom_theme_dialog(
            self,
            self.settings.get('custom_colors', {}),
            on_save,
        )

    def _create_vault(self):
        if show_create_vault_dialog(self):
            self.log(f'Vault created under {ConfigPath.secrets_path}')
            self.refresh_status()

    def _edit_mnemonic(self):
        if show_edit_mnemonic_dialog(self):
            self.log('Mnemonic updated in vault.')
            self.refresh_status()

    def _run_first_run_pipeline(self):
        from gui.setup_catalog import get_first_run_warnings

        if not vault_get_status().vault_initialized:
            if not messagebox.askyesno(
                'Secret vault',
                'KeePass vault does not exist yet. Create it now?',
            ):
                return
            if not show_create_vault_dialog(self):
                return
            self.refresh_status()

        warnings = get_first_run_warnings()
        if not self._confirm_setup_warnings('First-time setup', warnings):
            return

        link_type = self.var_link_type.get()

        def worker():
            return services.run_first_run_pipeline(link_type=link_type)

        def on_success(output: str):
            if output.strip():
                self.log(output)
            self.refresh_status()
            status = services.get_setup_status()
            if status.ready_for_transfer:
                messagebox.showinfo(
                    'Setup complete',
                    'Initial setup finished. You can use the IBC Transfer tab.',
                )
            elif not status.secret_unlock_files:
                messagebox.showinfo(
                    'Setup almost done',
                    'Steps 1–5 completed.\n\n'
                    f'Copy master.password and wallet.key to:\n{status.secrets_path}\n\n'
                    'Then run “Generate address book” or first-time setup again.',
                )
            else:
                messagebox.showwarning(
                    'Setup incomplete',
                    'Pipeline finished but some files are missing. Check the log and Status tab.',
                )

        self._run_async('First-time setup (full pipeline)', worker, on_success=on_success)

    def _run_setup(self, action_id: str):
        from gui.setup_catalog import get_action_warnings, get_setup_action

        action = get_setup_action(action_id)
        title = action.title if action else action_id
        warnings = get_action_warnings(action_id)
        if not self._confirm_setup_warnings(title, warnings):
            return

        link_type = self.var_link_type.get() if action_id == 'ledger_clients' else None

        def worker():
            return services.run_setup_action(action_id, link_type=link_type)

        def on_success(output: str):
            if output.strip():
                self.log(output)
            self.refresh_status()

        self._run_async(f'Setup: {title}', worker, on_success=on_success)


def run_gui():
    app = CosmosGuiApp()
    app.mainloop()
