import queue
import threading
import time
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
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
from gui.network_picker import NetworkListPicker
from gui.vault_dialog import show_create_vault_dialog, show_edit_mnemonic_dialog

NAV_LABELS = (
    'Portfolio',
    'Send',
    'Receive',
    'History',
    'Assets',
    '—',
    'Networks',
    'Tokens',
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
        self._build_receive_tab()
        self._build_history_tab()
        self._build_balances_tab()
        self._build_networks_tab()
        self._build_tokens_tab()
        self._build_addresses_tab()
        self._build_osmosis_tab()
        self._build_setup_tab()
        self._build_settings_tab()
        self._build_status_tab()
        self.after(100, self._poll_log_queue)
        self.after(50, self._poll_main_callbacks)
        self.refresh_status()
        self.after(800, self._schedule_balance_refresh)

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
        self.tab_receive = ttk.Frame(self._page_stack, padding=12)
        self.tab_history = ttk.Frame(self._page_stack, padding=12)
        self.tab_balances = ttk.Frame(self._page_stack, padding=12)
        self.tab_networks = ttk.Frame(self._page_stack, padding=12)
        self.tab_tokens = ttk.Frame(self._page_stack, padding=12)
        self.tab_addresses = ttk.Frame(self._page_stack, padding=12)
        self.tab_osmosis = ttk.Frame(self._page_stack, padding=12)
        self.tab_setup = ttk.Frame(self._page_stack, padding=12)
        self.tab_settings = ttk.Frame(self._page_stack, padding=12)
        self.tab_status = ttk.Frame(self._page_stack, padding=12)

        self._page_by_label = {
            'Portfolio': self.tab_portfolio,
            'Send': self.tab_transfer,
            'Receive': self.tab_receive,
            'History': self.tab_history,
            'Assets': self.tab_balances,
            'Networks': self.tab_networks,
            'Tokens': self.tab_tokens,
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
        if label in ('Portfolio', 'Send', 'Assets'):
            self._refresh_wallet_balances(quiet=True)
        elif label == 'Receive':
            self._load_receive_addresses()
        elif label == 'Networks':
            self._refresh_networks_table()
        elif label == 'Tokens':
            self._refresh_tokens_chain_filter()
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

    def _treeview_focus_item(self, tree) -> Optional[str]:
        """Selected row, or focused row (focus survives toolbar button clicks on Linux)."""
        sel = tree.selection()
        if sel:
            return sel[0]
        focus = tree.focus()
        return focus if focus else None

    def _copy_text_to_clipboard(self, text: str) -> None:
        """Copy to CLIPBOARD; re-assert after idle so X11 keeps text after focus changes."""
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update_idletasks()

        def _reassert():
            try:
                self.clipboard_clear()
                self.clipboard_append(text)
            except tk.TclError:
                pass

        self.after(100, _reassert)

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
        summaries = services.summarize_wallet_balances(rows)
        if hasattr(self, 'lbl_portfolio_status'):
            try:
                from gui.wallet_views import balance_rows_to_assets
                from project_utils.token_catalog import get_token_catalog

                catalog = get_token_catalog()
                usd_prices = {}
                if self.settings.get('show_fiat_prices', True):
                    from project_utils.coingecko_prices import fetch_usd_prices

                    ids = set()
                    for row in rows:
                        if row.denom and not row.error:
                            cg = catalog.get_coingecko_id(row.network, row.denom)
                            if cg:
                                ids.add(cg)
                    usd_prices = fetch_usd_prices(ids)
                assets = balance_rows_to_assets(
                    rows,
                    catalog=catalog,
                    usd_prices=usd_prices,
                    chain_rest_by_network=services.chain_rest_urls(),
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
            nets = ', '.join(sorted(services.get_wallet_networks()))
            self.lbl_portfolio_status.configure(
                text=f'{len(assets)} asset(s) · networks: {nets or "none"}',
            )
        if hasattr(self, 'balances_tree'):
            for item in self.balances_tree.get_children():
                self.balances_tree.delete(item)
            for row in rows:
                if row.error:
                    sym = ''
                    amount_h = ''
                elif row.denom == '(empty)':
                    sym = '—'
                    amount_h = '0'
                else:
                    from project_utils.token_catalog import get_token_catalog

                    sym = get_token_catalog().label_for_denom(row.network, row.denom)
                    amount_h = services.format_balance_display(
                        row.network, row.denom, row.amount
                    )
                self.balances_tree.insert(
                    '',
                    tk.END,
                    values=(
                        row.wallet_name,
                        row.network,
                        sym,
                        amount_h,
                        row.error or '',
                    ),
                )
        if missed:
            self.log('Networks without client: ' + ', '.join(missed))

    def _refresh_wallet_balances(self, quiet: bool = False):
        if self._balance_fetch_in_progress or not self._can_fetch_balances():
            return

        def worker():
            return services.fetch_balances()

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
        header.pack(fill=tk.X, pady=(0, 12))
        self.lbl_portfolio_total = ttk.Label(header, text='Portfolio', font=('', 16, 'bold'))
        self.lbl_portfolio_total.pack(side=tk.LEFT)
        ttk.Button(header, text='Refresh', command=lambda: self._refresh_wallet_balances()).pack(
            side=tk.RIGHT, padx=4,
        )
        ttk.Button(header, text='Send', command=lambda: self._go_nav('Send')).pack(side=tk.RIGHT, padx=4)
        ttk.Button(header, text='Receive', command=lambda: self._go_nav('Receive')).pack(side=tk.RIGHT)

        self.lbl_portfolio_status = self._muted_label(self.tab_portfolio, text='Loading…')
        self.lbl_portfolio_status.pack(anchor=tk.W, pady=(0, 8))

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

        also_book = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            dialog,
            text='Also append to denoms_book.json (same format as Osmosis mappings)',
            variable=also_book,
        ).pack(anchor=tk.W, padx=12, pady=(0, 8))

        self._muted_label(
            dialog,
            text='Saved to source/data/user_token_mappings.json and used for Send / Portfolio.',
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
                    also_denoms_book=bool(also_book.get()),
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
        self.receive_tree.bind('<Double-1>', lambda _e: self._copy_receive_address())

    def _load_receive_addresses(self):
        if not hasattr(self, 'receive_tree'):
            return
        entries = services.load_address_book_entries()
        for item in self.receive_tree.get_children():
            self.receive_tree.delete(item)
        for entry in entries:
            self.receive_tree.insert(
                '',
                tk.END,
                iid=entry.get('address', ''),
                values=(entry.get('network', ''), entry.get('name', ''), entry.get('address', '')),
            )

    def _copy_receive_address(self):
        if not hasattr(self, 'receive_tree'):
            return
        item = self._treeview_focus_item(self.receive_tree)
        if not item:
            messagebox.showinfo('Receive', 'Select an address row first.')
            return
        address = self.receive_tree.item(item, 'values')[2]
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
        self.log(f'Transaction hash: {tx_hash}')
        messagebox.showinfo(
            'Success',
            f'Transaction broadcast.\n\nHash (copied to clipboard):\n{tx_hash}',
        )
        self.clipboard_clear()
        self.clipboard_append(tx_hash)
        self._preview = None
        self.btn_send.configure(state=tk.DISABLED)

    def _build_history_tab(self):
        ttk.Label(self.tab_history, text='Transaction history', font=('', 11, 'bold')).pack(
            anchor=tk.W, pady=(0, 8),
        )
        self._muted_label(
            self.tab_history,
            text='IBC sends from this app. Select a row and copy the hash, or double-click a row.',
            wraplength=900,
        ).pack(anchor=tk.W, pady=(0, 8))

        toolbar = ttk.Frame(self.tab_history)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text='Refresh', command=self._refresh_history_table).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(toolbar, text='Copy hash', command=self._copy_history_hash).pack(side=tk.LEFT)

        cols = ('time', 'status', 'route', 'symbol', 'amount', 'timeout', 'gas', 'tx_hash')
        self.history_tree = ttk.Treeview(self.tab_history, columns=cols, show='headings', height=18)
        for col, title, width in [
            ('time', 'Time (UTC)', 150),
            ('status', 'Status', 72),
            ('route', 'Route', 130),
            ('symbol', 'Token', 56),
            ('amount', 'Amount', 72),
            ('timeout', 'Timeout', 100),
            ('gas', 'Gas', 64),
            ('tx_hash', 'Tx hash', 280),
        ]:
            self.history_tree.heading(col, text=title)
            self.history_tree.column(col, width=width, stretch=col == 'tx_hash')
        scroll = ttk.Scrollbar(self.tab_history, orient=tk.VERTICAL, command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scroll.set)
        self.history_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)
        self.history_tree.bind('<Double-1>', lambda _e: self._copy_history_hash())
        self.history_tree.tag_configure('success', foreground=self.colors.success)
        self.history_tree.tag_configure('failed', foreground=self.colors.error)
        self.history_tree.tag_configure('pending', foreground=self.colors.muted)
        self._refresh_history_table()

    def _refresh_history_table(self):
        if not hasattr(self, 'history_tree'):
            return
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for row in services.list_tx_history():
            route = f'{row.get("source", "")} → {row.get("destination", "")}'
            status = row.get('status', '')
            if status == 'success':
                tags = ('success',)
            elif status == 'failed':
                tags = ('failed',)
            else:
                tags = ('pending',)
            mode = row.get('timeout_mode', 'time')
            tval = row.get('timeout_value', '')
            timeout_col = row.get('timeout_display') or (
                f'{tval}s' if mode == 'time' else f'+{tval} blk'
            )
            tx = row.get('tx_hash', '') or row.get('error', '')[:48]
            self.history_tree.insert(
                '',
                tk.END,
                values=(
                    row.get('time', ''),
                    status,
                    route,
                    row.get('symbol', ''),
                    row.get('amount', ''),
                    timeout_col,
                    row.get('gas', ''),
                    tx,
                ),
                tags=tags,
            )

    def _copy_history_hash(self):
        if not hasattr(self, 'history_tree'):
            return
        item = self._treeview_focus_item(self.history_tree)
        if not item:
            messagebox.showinfo('History', 'Select a row first.')
            return
        values = self.history_tree.item(item, 'values')
        tx_hash = values[7] if len(values) > 7 else ''
        if not tx_hash or tx_hash.startswith('out of gas') or len(tx_hash) < 16:
            messagebox.showinfo('History', 'No transaction hash for this row (failed or pending).')
            return
        self._copy_text_to_clipboard(tx_hash)
        self.log(f'Copied tx hash: {tx_hash}')

    def _build_balances_tab(self):
        ttk.Label(self.tab_balances, text='Assets — all token balances', font=('', 11, 'bold')).pack(
            anchor=tk.W, pady=(0, 8),
        )
        toolbar = ttk.Frame(self.tab_balances)
        toolbar.pack(fill=tk.X)
        ttk.Button(
            toolbar,
            text='Refresh now',
            command=lambda: self._refresh_wallet_balances(),
        ).pack(side=tk.LEFT)
        self._muted_label(
            toolbar,
            text='  Detailed list · auto-refresh in Settings',
        ).pack(side=tk.LEFT, padx=8)

        cols = ('wallet', 'network', 'symbol', 'amount', 'error')
        self.balances_tree = ttk.Treeview(self.tab_balances, columns=cols, show='headings', height=18)
        for col, title, width in [
            ('wallet', 'Wallet', 120),
            ('network', 'Network', 100),
            ('symbol', 'Token', 80),
            ('amount', 'Amount', 180),
            ('error', 'Error', 200),
        ]:
            self.balances_tree.heading(col, text=title)
            self.balances_tree.column(col, width=width, stretch=col == 'amount')
        scroll = ttk.Scrollbar(self.tab_balances, orient=tk.VERTICAL, command=self.balances_tree.yview)
        self.balances_tree.configure(yscrollcommand=scroll.set)
        self.balances_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

    def _send_token_list_mode(self) -> str:
        if hasattr(self, 'var_send_token_list'):
            return self.var_send_token_list.get().strip().lower() or 'nonzero'
        return self.settings.get('send_token_list_mode', 'nonzero')

    def _on_send_token_list_mode_changed(self):
        self.settings['send_token_list_mode'] = self._send_token_list_mode()
        from gui.settings import save_settings

        save_settings(self.settings)
        self._update_transfer_symbols()

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
                'Tokens from chain-registry assetlist.json (denom / contract). '
                'Osmosis DEX prices merged from Numia API when a denom matches. '
                'Rebuild catalog via Setup → step 3 (Collect chain-registry JSON).'
            ),
            wraplength=920,
        )
        intro.pack(anchor=tk.W, pady=(0, 8))

        toolbar = ttk.Frame(self.tab_tokens)
        toolbar.pack(fill=tk.X)
        ttk.Label(toolbar, text='Network').pack(side=tk.LEFT, padx=(0, 6))
        self.var_token_chain = tk.StringVar(value='All')
        self.cmb_token_chain = ttk.Combobox(
            toolbar,
            textvariable=self.var_token_chain,
            state='readonly',
            width=22,
        )
        self.cmb_token_chain.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(toolbar, text='Search').pack(side=tk.LEFT, padx=(0, 6))
        self.var_token_search = tk.StringVar()
        search_entry = ttk.Entry(toolbar, textvariable=self.var_token_search, width=28)
        search_entry.pack(side=tk.LEFT, padx=(0, 10))
        search_entry.bind('<Return>', lambda _e: self._load_registry_tokens())
        ttk.Button(toolbar, text='Load tokens', command=self._load_registry_tokens).pack(side=tk.LEFT)

        cols = ('network', 'symbol', 'display', 'denom', 'decimals', 'contract', 'price', 'liq', 'chg24')
        self.tokens_tree = ttk.Treeview(self.tab_tokens, columns=cols, show='headings', height=20)
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
            self.tokens_tree.heading(col, text=title)
            self.tokens_tree.column(col, width=width, stretch=col in ('denom', 'contract'))
        scroll = ttk.Scrollbar(self.tab_tokens, orient=tk.VERTICAL, command=self.tokens_tree.yview)
        self.tokens_tree.configure(yscrollcommand=scroll.set)
        self.tokens_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

        self.lbl_tokens_status = ttk.Label(self.tab_tokens, text='')
        self.lbl_tokens_status.pack(anchor=tk.W)
        self._refresh_tokens_chain_filter()

    def _refresh_tokens_chain_filter(self):
        if not hasattr(self, 'cmb_token_chain'):
            return
        chains = ['All'] + services.registry_chains_with_tokens()
        self.cmb_token_chain['values'] = chains
        if self.var_token_chain.get() not in chains:
            self.var_token_chain.set(chains[0] if chains else 'All')

    def _load_registry_tokens(self):
        chain = self.var_token_chain.get()
        search = self.var_token_search.get()

        def worker():
            return services.fetch_registry_token_rows(
                chain_name=None if chain == 'All' else chain,
                search=search,
                with_prices=True,
            )

        def on_success(result):
            rows, meta = result
            for item in self.tokens_tree.get_children():
                self.tokens_tree.delete(item)
            for row in rows:
                price = row.get('price')
                liq = row.get('liquidity')
                self.tokens_tree.insert(
                    '',
                    tk.END,
                    values=(
                        row.get('chain_name', ''),
                        row.get('symbol', ''),
                        row.get('display', ''),
                        row.get('denom', ''),
                        row.get('decimals', ''),
                        row.get('contract', '') or '',
                        f'{float(price):.6g}' if price not in (None, '') else '',
                        f'{float(liq):,.0f}' if liq not in (None, '') else '',
                        row.get('price_24h_change', '') if row.get('price_24h_change') is not None else '',
                    ),
                )
            parts = [f'Showing {meta.get("shown", 0)} token(s)']
            if meta.get('registry_loaded') is False:
                parts = ['No assets_registry.json — run Setup → step 3 (Collect chain-registry JSON)']
            elif meta.get('truncated'):
                parts.append('(list truncated — narrow network or search)')
            if meta.get('osmosis_prices') is False:
                parts.append(f'Osmosis prices unavailable: {meta.get("osmosis_error", "")}')
            self.lbl_tokens_status.configure(text=' · '.join(parts))
            self.log('Tokens loaded: ' + ' · '.join(parts))

        self._run_async('Registry tokens', worker, on_success=on_success)

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
        ttk.Label(toolbar, text='Filter:').pack(side=tk.LEFT)
        ttk.Entry(toolbar, textvariable=self.var_addr_filter, width=24).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(
            toolbar,
            text='Show all networks in file',
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
        self.addr_tree.bind('<Double-1>', lambda _e: self._copy_address_book_address())

        self._address_entries = []
        self._load_addresses()

    def _load_addresses(self):
        show_all = bool(self.var_addr_show_all.get()) if hasattr(self, 'var_addr_show_all') else False
        self._address_entries = services.load_address_book_entries(all_networks=show_all)
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
        needle = self.var_addr_filter.get().strip().lower()
        for item in self.addr_tree.get_children():
            self.addr_tree.delete(item)
        for entry in self._address_entries:
            hay = f'{entry.get("name", "")} {entry.get("network", "")} {entry.get("address", "")}'.lower()
            if needle and needle not in hay:
                continue
            addr = entry.get('address', '')
            network = entry.get('network', '')
            self.addr_tree.insert(
                '',
                tk.END,
                iid=f'{network}:{addr}' if network and addr else None,
                values=(entry.get('name', ''), network, addr),
            )

    def _copy_address_book_address(self):
        if not hasattr(self, 'addr_tree'):
            return
        item = self._treeview_focus_item(self.addr_tree)
        if not item:
            messagebox.showinfo('Address book', 'Select a row first.')
            return
        values = self.addr_tree.item(item, 'values')
        address = values[2] if len(values) > 2 else ''
        if not address:
            messagebox.showinfo('Address book', 'No address in this row.')
            return
        self._copy_text_to_clipboard(address)
        self.log(f'Copied address: {address}')

    def _build_osmosis_tab(self):
        ttk.Label(
            self.tab_osmosis,
            text='Market — Osmosis DEX prices (Numia API). Top tokens by 24h volume.',
            wraplength=700,
        ).pack(anchor=tk.W, pady=(0, 8))
        toolbar = ttk.Frame(self.tab_osmosis)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text='Load DEX prices', command=self._load_osmosis).pack(side=tk.LEFT)
        self._muted_label(
            toolbar,
            text='  Click column headers to sort',
        ).pack(side=tk.LEFT, padx=8)

        self._osmo_rows: list = []
        self._osmo_sort_col = 'volume'
        self._osmo_sort_reverse = True
        self._osmo_heading_titles = {
            'symbol': 'Symbol',
            'denom': 'Denom',
            'price': 'Price',
            'liquidity': 'Liquidity',
            'volume': 'Vol 24h',
            'chg24': '24h %',
            'chg7': '7d %',
        }

        cols = ('symbol', 'denom', 'price', 'liquidity', 'volume', 'chg24', 'chg7')
        self.osmo_tree = ttk.Treeview(self.tab_osmosis, columns=cols, show='headings', height=20)
        headers = [
            ('symbol', 'Symbol', 72),
            ('denom', 'Denom', 120),
            ('price', 'Price', 88),
            ('liquidity', 'Liquidity', 100),
            ('volume', 'Vol 24h', 100),
            ('chg24', '24h %', 72),
            ('chg7', '7d %', 72),
        ]
        for col, title, width in headers:
            self.osmo_tree.heading(
                col,
                text=title,
                command=lambda c=col: self._sort_osmo_column(c),
            )
            self.osmo_tree.column(col, width=width)
        scroll = ttk.Scrollbar(self.tab_osmosis, orient=tk.VERTICAL, command=self.osmo_tree.yview)
        self.osmo_tree.configure(yscrollcommand=scroll.set)
        self.osmo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

    def _osmo_sort_key(self, row: dict, column: str):
        if column in ('symbol', 'denom'):
            return (row.get(column) or '').lower()
        try:
            return float(row.get(column) or 0)
        except (TypeError, ValueError):
            return 0.0

    def _sort_osmo_column(self, column: str):
        if self._osmo_sort_col == column:
            self._osmo_sort_reverse = not self._osmo_sort_reverse
        else:
            self._osmo_sort_col = column
            self._osmo_sort_reverse = column not in ('symbol', 'denom')
        self._render_osmo_table()

    def _update_osmo_headings(self):
        for col, base in self._osmo_heading_titles.items():
            arrow = ''
            if col == self._osmo_sort_col:
                arrow = ' ▼' if self._osmo_sort_reverse else ' ▲'
            self.osmo_tree.heading(col, text=base + arrow)

    def _render_osmo_table(self):
        rows = list(self._osmo_rows)
        rows.sort(key=lambda r: self._osmo_sort_key(r, self._osmo_sort_col), reverse=self._osmo_sort_reverse)
        for item in self.osmo_tree.get_children():
            self.osmo_tree.delete(item)
        for row in rows:
            self.osmo_tree.insert(
                '',
                tk.END,
                values=(
                    row.get('symbol', ''),
                    row.get('denom', ''),
                    row.get('price', ''),
                    row.get('_liquidity_fmt', ''),
                    row.get('_volume_fmt', ''),
                    row.get('price_24h_change', ''),
                    row.get('price_7d_change', ''),
                ),
            )
        self._update_osmo_headings()

    def _load_osmosis(self):
        def on_success(rows):
            prepared = []
            for row in rows:
                item = dict(row)
                liq = item.get('liquidity')
                vol = item.get('volume_24h')
                item['_liquidity_fmt'] = (
                    f'{float(liq):,.0f}' if liq not in ('', None) else ''
                )
                item['_volume_fmt'] = (
                    f'{float(vol):,.0f}' if vol not in ('', None) else ''
                )
                prepared.append(item)
            self._osmo_rows = prepared
            self._render_osmo_table()

        self._run_async('Osmosis DEX', services.fetch_osmosis_tokens, on_success=on_success)

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
            text='Auto-refresh balances (Portfolio, Send, Assets)',
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
