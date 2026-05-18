import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from gui import services


class CosmosGuiApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Cosmos Crypto Transfer')
        self.minsize(900, 620)
        self._log_queue: queue.Queue = queue.Queue()
        self._preview = None
        self._current_route = None
        self._by_source = services.ibc_routes_grouped()

        self._build_layout()
        self._build_home_tab()
        self._build_transfer_tab()
        self._build_balances_tab()
        self._build_addresses_tab()
        self._build_osmosis_tab()
        self._build_setup_tab()
        self.after(100, self._poll_log_queue)
        self.refresh_status()

    def _build_layout(self):
        main = ttk.Frame(self, padding=8)
        main.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.tab_home = ttk.Frame(self.notebook, padding=10)
        self.tab_transfer = ttk.Frame(self.notebook, padding=10)
        self.tab_balances = ttk.Frame(self.notebook, padding=10)
        self.tab_addresses = ttk.Frame(self.notebook, padding=10)
        self.tab_osmosis = ttk.Frame(self.notebook, padding=10)
        self.tab_setup = ttk.Frame(self.notebook, padding=10)

        self.notebook.add(self.tab_home, text='Home')
        self.notebook.add(self.tab_transfer, text='IBC Transfer')
        self.notebook.add(self.tab_balances, text='Balances')
        self.notebook.add(self.tab_addresses, text='Address book')
        self.notebook.add(self.tab_osmosis, text='Osmosis tokens')
        self.notebook.add(self.tab_setup, text='Setup')

        log_frame = ttk.LabelFrame(main, text='Log', padding=4)
        log_frame.pack(fill=tk.BOTH, expand=False, pady=(8, 0))
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, state=tk.DISABLED, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)

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

    def _run_async(self, label: str, worker, on_success=None):
        self.log(f'[{label}] started…')

        def task():
            try:
                result = worker()
            except Exception as exc:
                self.after(0, lambda: self._async_error(label, exc))
                return

            def done():
                self.log(f'[{label}] finished.')
                if on_success:
                    on_success(result)

            self.after(0, done)

        threading.Thread(target=task, daemon=True).start()

    def _async_error(self, label: str, exc: Exception):
        self.log(f'[{label}] error: {exc}')
        messagebox.showerror(label, str(exc))

    def refresh_status(self):
        status = services.get_setup_status()
        lines = [
            ('Source directory', status.source_dir),
            ('wallet.json', status.wallet_json),
            ('cosmos_data_list.json', status.cosmos_data),
            ('ledger_clients.py', status.ledger_clients),
            ('wallets_list.py', status.wallets_list),
            ('address_book.json', status.address_book),
            ('client mapping', status.client_mapping),
        ]
        for label, ok in lines:
            widget = self._status_labels.get(label)
            if widget:
                widget.configure(text='OK' if ok else 'missing', foreground='#1a7f37' if ok else '#cf222e')

        if status.ready_for_transfer:
            self.transfer_hint.configure(
                text='Ready for IBC transfers.',
                foreground='#1a7f37',
            )
        else:
            self.transfer_hint.configure(
                text='Complete Setup (wallet, clients, wallets list, address book) before transferring.',
                foreground='#9a6700',
            )

    def _build_home_tab(self):
        ttk.Label(
            self.tab_home,
            text='Cosmos IBC transfer — desktop GUI',
            font=('', 12, 'bold'),
        ).pack(anchor=tk.W)

        ttk.Label(
            self.tab_home,
            text='CLI: python menu_crypto.py  |  GUI: python gui_crypto.py',
        ).pack(anchor=tk.W, pady=(4, 12))

        frame = ttk.LabelFrame(self.tab_home, text='Environment', padding=8)
        frame.pack(fill=tk.X, anchor=tk.W)

        self._status_labels = {}
        status = services.get_setup_status()
        items = [
            ('Source directory', status.source_dir),
            ('wallet.json', status.wallet_json),
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
            value.configure(foreground='#1a7f37' if ok else '#cf222e')
            self._status_labels[label] = value

        self.transfer_hint = ttk.Label(self.tab_home, text='')
        self.transfer_hint.pack(anchor=tk.W, pady=12)

        ttk.Button(self.tab_home, text='Refresh status', command=self.refresh_status).pack(anchor=tk.W)

    def _build_transfer_tab(self):
        form = ttk.Frame(self.tab_transfer)
        form.pack(fill=tk.X, anchor=tk.W)

        sources = sorted(self._by_source.keys())
        self.var_source = tk.StringVar(value=sources[0] if sources else '')
        self.var_dest = tk.StringVar()
        self.var_symbol = tk.StringVar(value='bld')
        self.var_amount = tk.StringVar(value='0.01')

        ttk.Label(form, text='Source chain').grid(row=0, column=0, sticky=tk.W, padx=4, pady=4)
        self.cmb_source = ttk.Combobox(form, textvariable=self.var_source, values=sources, state='readonly', width=28)
        self.cmb_source.grid(row=0, column=1, sticky=tk.W, padx=4, pady=4)
        self.cmb_source.bind('<<ComboboxSelected>>', lambda _e: self._on_source_changed())

        ttk.Label(form, text='Destination').grid(row=1, column=0, sticky=tk.W, padx=4, pady=4)
        self.cmb_dest = ttk.Combobox(form, textvariable=self.var_dest, state='readonly', width=28)
        self.cmb_dest.grid(row=1, column=1, sticky=tk.W, padx=4, pady=4)
        self.cmb_dest.bind('<<ComboboxSelected>>', lambda _e: self._update_route_info())

        ttk.Label(form, text='Symbol').grid(row=2, column=0, sticky=tk.W, padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_symbol, width=30).grid(row=2, column=1, sticky=tk.W, padx=4, pady=4)

        ttk.Label(form, text='Amount').grid(row=3, column=0, sticky=tk.W, padx=4, pady=4)
        ttk.Entry(form, textvariable=self.var_amount, width=30).grid(row=3, column=1, sticky=tk.W, padx=4, pady=4)

        self.route_info = ttk.Label(self.tab_transfer, text='', wraplength=700)
        self.route_info.pack(anchor=tk.W, pady=8)

        btn_row = ttk.Frame(self.tab_transfer)
        btn_row.pack(anchor=tk.W, pady=4)
        ttk.Button(btn_row, text='Preview transfer', command=self._preview_transfer).pack(side=tk.LEFT, padx=(0, 8))
        self.btn_send = ttk.Button(btn_row, text='Send (after preview)', command=self._send_transfer, state=tk.DISABLED)
        self.btn_send.pack(side=tk.LEFT)

        self._on_source_changed()

    def _destinations_for_source(self, source: str):
        routes = self._by_source.get(source, [])
        return sorted({r['destination_network'] for r in routes})

    def _route_for_selection(self):
        return services.ibc_route_for(self.var_source.get(), self.var_dest.get())

    def _on_source_changed(self):
        dests = self._destinations_for_source(self.var_source.get())
        self.cmb_dest['values'] = dests
        if dests:
            if self.var_dest.get() not in dests:
                self.var_dest.set(dests[0])
        else:
            self.var_dest.set('')
        self._preview = None
        self.btn_send.configure(state=tk.DISABLED)
        self._update_route_info()

    def _update_route_info(self):
        route = self._route_for_selection()
        self._current_route = route
        if not route:
            self.route_info.configure(text='No route for this pair. Check config/ibc_routes.json.')
            return
        self.route_info.configure(
            text=(
                f'{route["source_network"]} → {route["destination_network"]} | '
                f'channel {route["channel"]} | gas {route["gas"]} | '
                f'wallets {route["sender_wallet"]} → {route["receiver_wallet"]}'
            )
        )

    def _parse_amount(self) -> float:
        try:
            return float(self.var_amount.get().strip())
        except ValueError as exc:
            raise ValueError('Invalid amount') from exc

    def _preview_transfer(self):
        route = self._route_for_selection()
        if not route:
            messagebox.showwarning('Transfer', 'Select a valid source and destination.')
            return
        try:
            amount = self._parse_amount()
            symbol = self.var_symbol.get().strip()
        except ValueError as exc:
            messagebox.showerror('Transfer', str(exc))
            return

        try:
            preview = services.gui_prepare_transfer(route, symbol, amount)
        except Exception as exc:
            messagebox.showerror('Preview failed', str(exc))
            return

        self._preview = preview
        self.btn_send.configure(state=tk.NORMAL)
        body = '\n'.join(preview.summary_lines())
        self.log('--- Transfer preview ---\n' + body)
        messagebox.showinfo('Transfer preview', body)

    def _send_transfer(self):
        if self._preview is None or self._current_route is None:
            messagebox.showwarning('Transfer', 'Run preview first.')
            return

        route = self._current_route
        preview = self._preview

        dialog = tk.Toplevel(self)
        dialog.title('Confirm IBC transfer')
        dialog.transient(self)
        dialog.grab_set()

        ttk.Label(dialog, text='\n'.join(preview.summary_lines()), justify=tk.LEFT).pack(padx=12, pady=12)

        confirm_var = tk.StringVar()
        ttk.Label(dialog, text=f'Re-enter amount ({preview.amount_token}):').pack(anchor=tk.W, padx=12)
        ttk.Entry(dialog, textvariable=confirm_var, width=20).pack(padx=12, pady=4, anchor=tk.W)

        agree_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(dialog, text='I confirm this transfer', variable=agree_var).pack(anchor=tk.W, padx=12, pady=8)

        def submit():
            try:
                if float(confirm_var.get().strip()) != preview.amount_token:
                    messagebox.showerror('Confirm', 'Amount mismatch.', parent=dialog)
                    return
            except ValueError:
                messagebox.showerror('Confirm', 'Invalid amount.', parent=dialog)
                return
            if not agree_var.get():
                messagebox.showerror('Confirm', 'Check the confirmation box.', parent=dialog)
                return
            dialog.destroy()
            self._run_async(
                'IBC transfer',
                lambda: services.gui_broadcast_transfer(route, preview),
                on_success=lambda tx_hash: self._transfer_done(tx_hash),
            )

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text='Send', command=submit).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text='Cancel', command=dialog.destroy).pack(side=tk.LEFT, padx=4)

    def _transfer_done(self, tx_hash: str):
        self.log(f'Transaction hash: {tx_hash}')
        messagebox.showinfo('Success', f'Transaction hash:\n{tx_hash}')
        self._preview = None
        self.btn_send.configure(state=tk.DISABLED)

    def _build_balances_tab(self):
        toolbar = ttk.Frame(self.tab_balances)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text='Fetch all balances', command=self._fetch_balances).pack(side=tk.LEFT)

        cols = ('wallet', 'network', 'address', 'denom', 'amount', 'error')
        self.balances_tree = ttk.Treeview(self.tab_balances, columns=cols, show='headings', height=18)
        for col, title, width in [
            ('wallet', 'Wallet', 120),
            ('network', 'Network', 100),
            ('address', 'Address', 220),
            ('denom', 'Denom', 140),
            ('amount', 'Amount', 100),
            ('error', 'Error', 180),
        ]:
            self.balances_tree.heading(col, text=title)
            self.balances_tree.column(col, width=width, stretch=col == 'address')
        scroll = ttk.Scrollbar(self.tab_balances, orient=tk.VERTICAL, command=self.balances_tree.yview)
        self.balances_tree.configure(yscrollcommand=scroll.set)
        self.balances_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

    def _fetch_balances(self):
        def worker():
            rows, missed = services.fetch_balances()
            return rows, missed

        def on_success(result):
            rows, missed = result
            for item in self.balances_tree.get_children():
                self.balances_tree.delete(item)
            for row in rows:
                self.balances_tree.insert(
                    '',
                    tk.END,
                    values=(
                        row.wallet_name,
                        row.network,
                        row.address[:24] + '…' if len(row.address) > 24 else row.address,
                        row.denom,
                        row.amount,
                        row.error or '',
                    ),
                )
            if missed:
                self.log('Networks without client: ' + ', '.join(missed))

        self._run_async('Balances', worker, on_success=on_success)

    def _build_addresses_tab(self):
        toolbar = ttk.Frame(self.tab_addresses)
        toolbar.pack(fill=tk.X)
        self.var_addr_filter = tk.StringVar()
        self.var_addr_filter.trace_add('write', lambda *_a: self._filter_addresses())
        ttk.Label(toolbar, text='Filter:').pack(side=tk.LEFT)
        ttk.Entry(toolbar, textvariable=self.var_addr_filter, width=30).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text='Reload', command=self._load_addresses).pack(side=tk.LEFT)

        cols = ('name', 'network', 'address')
        self.addr_tree = ttk.Treeview(self.tab_addresses, columns=cols, show='headings', height=20)
        for col, title, width in [('name', 'Name', 160), ('network', 'Network', 120), ('address', 'Address', 420)]:
            self.addr_tree.heading(col, text=title)
            self.addr_tree.column(col, width=width)
        scroll = ttk.Scrollbar(self.tab_addresses, orient=tk.VERTICAL, command=self.addr_tree.yview)
        self.addr_tree.configure(yscrollcommand=scroll.set)
        self.addr_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

        self._address_entries = []
        self._load_addresses()

    def _load_addresses(self):
        self._address_entries = services.load_address_book_entries()
        self._filter_addresses()

    def _filter_addresses(self):
        needle = self.var_addr_filter.get().strip().lower()
        for item in self.addr_tree.get_children():
            self.addr_tree.delete(item)
        for entry in self._address_entries:
            hay = f'{entry.get("name", "")} {entry.get("network", "")} {entry.get("address", "")}'.lower()
            if needle and needle not in hay:
                continue
            self.addr_tree.insert(
                '',
                tk.END,
                values=(entry.get('name', ''), entry.get('network', ''), entry.get('address', '')),
            )

    def _build_osmosis_tab(self):
        toolbar = ttk.Frame(self.tab_osmosis)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text='Load token prices', command=self._load_osmosis).pack(side=tk.LEFT)

        cols = ('symbol', 'price', 'liquidity', 'volume', 'chg24', 'chg7')
        self.osmo_tree = ttk.Treeview(self.tab_osmosis, columns=cols, show='headings', height=20)
        headers = [
            ('symbol', 'Symbol', 80),
            ('price', 'Price', 90),
            ('liquidity', 'Liquidity', 110),
            ('volume', 'Vol 24h', 110),
            ('chg24', '24h %', 80),
            ('chg7', '7d %', 80),
        ]
        for col, title, width in headers:
            self.osmo_tree.heading(col, text=title)
            self.osmo_tree.column(col, width=width)
        scroll = ttk.Scrollbar(self.tab_osmosis, orient=tk.VERTICAL, command=self.osmo_tree.yview)
        self.osmo_tree.configure(yscrollcommand=scroll.set)
        self.osmo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=8)
        scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=8)

    def _load_osmosis(self):
        def on_success(rows):
            for item in self.osmo_tree.get_children():
                self.osmo_tree.delete(item)
            for row in rows:
                self.osmo_tree.insert(
                    '',
                    tk.END,
                    values=(
                        row['symbol'],
                        row['price'],
                        f'{float(row["liquidity"]):,.0f}' if row.get('liquidity') not in ('', None) else '',
                        f'{float(row["volume_24h"]):,.0f}' if row.get('volume_24h') not in ('', None) else '',
                        row.get('price_24h_change', ''),
                        row.get('price_7d_change', ''),
                    ),
                )

        self._run_async('Osmosis tokens', services.fetch_osmosis_tokens, on_success=on_success)

    def _build_setup_tab(self):
        ttk.Label(
            self.tab_setup,
            text='Run setup steps (same as CLI menu “Check and create data”). Long steps run in background.',
            wraplength=700,
        ).pack(anchor=tk.W, pady=(0, 8))

        self.var_link_type = tk.StringVar(value='rest_link')
        link_row = ttk.Frame(self.tab_setup)
        link_row.pack(anchor=tk.W, pady=4)
        ttk.Label(link_row, text='Ledger client REST field:').pack(side=tk.LEFT)
        ttk.Combobox(
            link_row,
            textvariable=self.var_link_type,
            values=['rest_link', 'keplr_rest_link'],
            state='readonly',
            width=18,
        ).pack(side=tk.LEFT, padx=6)

        grid = ttk.Frame(self.tab_setup)
        grid.pack(anchor=tk.W, pady=8)

        buttons = [
            ('source', '1. Create source / registries'),
            ('pythonpath', '2. Check PYTHONPATH tip'),
            ('apps', '3. Check apps (may prompt in terminal)'),
            ('modules', '4. Install Python modules'),
            ('all_checks', '5. All checks'),
            ('collect_json', '6. Collect chain JSON'),
            ('ledger_clients', '7. Generate ledger clients'),
            ('wallets', '8. Generate wallets list'),
            ('address_book', '9. Generate address book'),
        ]
        for idx, (action_id, label) in enumerate(buttons):
            ttk.Button(
                grid,
                text=label,
                command=lambda aid=action_id: self._run_setup(aid),
            ).grid(row=idx // 2, column=idx % 2, sticky=tk.W, padx=4, pady=4)

    def _run_setup(self, action_id: str):
        link_type = self.var_link_type.get() if action_id == 'ledger_clients' else None

        def worker():
            return services.run_setup_action(action_id, link_type=link_type)

        def on_success(output: str):
            if output.strip():
                self.log(output)
            self.refresh_status()

        self._run_async(f'Setup: {action_id}', worker, on_success=on_success)


def run_gui():
    app = CosmosGuiApp()
    app.mainloop()
