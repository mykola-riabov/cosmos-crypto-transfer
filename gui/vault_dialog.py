import tkinter as tk
from tkinter import messagebox, ttk

from chain.wallets.secret_vault import VaultError, create_vault, get_mnemonic, get_status, set_mnemonic, unlock
from config.config_path import ConfigPath


class _MnemonicForm(ttk.Frame):
    def __init__(self, parent, *, show_master=False, title=''):
        super().__init__(parent, padding=8)
        self.show_master = show_master

        row = 0
        if title:
            ttk.Label(self, text=title, font=('', 10, 'bold')).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))
            row += 1

        ttk.Label(self, text='Mnemonic (12/24 words):').grid(row=row, column=0, sticky=tk.W, pady=2)
        self.txt_mnemonic = tk.Text(self, height=3, width=52, wrap=tk.WORD)
        self.txt_mnemonic.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        ttk.Label(self, text='Confirm mnemonic:').grid(row=row, column=0, sticky=tk.W, pady=2)
        self.txt_mnemonic2 = tk.Text(self, height=3, width=52, wrap=tk.WORD)
        self.txt_mnemonic2.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        if show_master:
            ttk.Label(self, text='Master password:').grid(row=row, column=0, sticky=tk.W, pady=2)
            self.var_master = tk.StringVar()
            ttk.Entry(self, textvariable=self.var_master, show='•', width=40).grid(row=row, column=1, sticky=tk.W, pady=2)
            row += 1

            ttk.Label(self, text='Confirm master password:').grid(row=row, column=0, sticky=tk.W, pady=2)
            self.var_master2 = tk.StringVar()
            ttk.Entry(self, textvariable=self.var_master2, show='•', width=40).grid(row=row, column=1, sticky=tk.W, pady=2)
            row += 1

            self.var_write_password = tk.BooleanVar(value=True)
            ttk.Checkbutton(
                self,
                text='Save master.password in vault folder (copy to USB; delete locally when idle)',
                variable=self.var_write_password,
            ).grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=6)

    def read_mnemonic(self) -> str:
        return self.txt_mnemonic.get('1.0', tk.END).strip()

    def read_mnemonic_confirm(self) -> str:
        return self.txt_mnemonic2.get('1.0', tk.END).strip()

    def read_master_password(self) -> tuple:
        if not self.show_master:
            return '', False
        return self.var_master.get(), self.var_write_password.get()

    def validate(self) -> tuple:
        m1 = self.read_mnemonic()
        m2 = self.read_mnemonic_confirm()
        if not m1:
            raise VaultError('Mnemonic is empty.')
        if m1 != m2:
            raise VaultError('Mnemonic fields do not match.')
        if self.show_master:
            p1 = self.var_master.get()
            p2 = self.var_master2.get()
            if not p1:
                raise VaultError('Master password is empty.')
            if p1 != p2:
                raise VaultError('Master password fields do not match.')
            return m1, p1, self.var_write_password.get()
        return m1, None, False


def show_create_vault_dialog(parent) -> bool:
    status = get_status()
    if status.vault_initialized and not messagebox.askyesno(
        'Vault exists',
        'A vault already exists. Overwrite it? This cannot be undone.',
        parent=parent,
    ):
        return False

    dialog = tk.Toplevel(parent)
    dialog.title('Create secret vault')
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(False, False)

    ttk.Label(
        dialog,
        text=(
            f'Files will be created in:\n{ConfigPath.secrets_path}\n\n'
            'wallet.kdbx — encrypted database\n'
            'wallet.key — key file (keep on USB when not in use)\n'
            'master.password — optional local copy of master password'
        ),
        justify=tk.LEFT,
        padding=8,
    ).pack(anchor=tk.W)

    form = _MnemonicForm(dialog, show_master=True, title='New vault')
    form.pack(fill=tk.BOTH, expand=True)

    result = {'ok': False}

    def submit():
        try:
            mnemonic, master, write_pw = form.validate()
            from project_utils.wallet_ids import DEFAULT_WALLET_ID

            create_vault(
                mnemonic,
                master,
                wallet_id=DEFAULT_WALLET_ID,
                write_password_file=write_pw,
                overwrite=True,
            )
            from project_utils.wallet_profiles import create_wallet, ensure_default_profile, load_profiles

            ensure_default_profile()
            if DEFAULT_WALLET_ID not in load_profiles()['profiles']:
                create_wallet('Wallet 1', wallet_id=DEFAULT_WALLET_ID, key_type='mnemonic')
            result['ok'] = True
            messagebox.showinfo(
                'Vault created',
                'Vault created successfully.\n\n'
                'Copy wallet.key and master.password to your USB stick.\n'
                'You may delete those two files from disk when not trading.',
                parent=dialog,
            )
            dialog.destroy()
        except VaultError as exc:
            messagebox.showerror('Vault', str(exc), parent=dialog)

    btns = ttk.Frame(dialog, padding=8)
    btns.pack(fill=tk.X)
    ttk.Button(btns, text='Create vault', command=submit).pack(side=tk.LEFT, padx=4)
    ttk.Button(btns, text='Cancel', command=dialog.destroy).pack(side=tk.LEFT, padx=4)

    parent.wait_window(dialog)
    return result['ok']


def show_edit_mnemonic_dialog(parent) -> bool:
    dialog = tk.Toplevel(parent)
    dialog.title('View / edit mnemonic')
    dialog.transient(parent)
    dialog.grab_set()

    unlock_row = ttk.Frame(dialog, padding=8)
    unlock_row.pack(fill=tk.X)
    ttk.Label(
        unlock_row,
        text='Unlock vault (needs master.password + wallet.key in secrets folder, or enter password):',
        wraplength=480,
    ).pack(anchor=tk.W)
    var_pw = tk.StringVar()
    ttk.Entry(unlock_row, textvariable=var_pw, show='•', width=40).pack(anchor=tk.W, pady=4)

    form = _MnemonicForm(dialog, show_master=False)
    form.pack(fill=tk.BOTH, expand=True)

    def do_unlock():
        try:
            password = var_pw.get().strip() or None
            unlock(master_password=password)
            mnemonic = get_mnemonic()
            form.txt_mnemonic.delete('1.0', tk.END)
            form.txt_mnemonic.insert('1.0', mnemonic)
            form.txt_mnemonic2.delete('1.0', tk.END)
            form.txt_mnemonic2.insert('1.0', mnemonic)
        except VaultError as exc:
            messagebox.showerror('Unlock', str(exc), parent=dialog)

    ttk.Button(unlock_row, text='Unlock', command=do_unlock).pack(anchor=tk.W)

    result = {'ok': False}

    def save():
        try:
            if not get_status().is_unlocked:
                unlock(master_password=var_pw.get().strip() or None)
            mnemonic, _, _ = form.validate()
            set_mnemonic(mnemonic)
            result['ok'] = True
            messagebox.showinfo('Saved', 'Mnemonic updated in vault.', parent=dialog)
            dialog.destroy()
        except VaultError as exc:
            messagebox.showerror('Vault', str(exc), parent=dialog)

    btns = ttk.Frame(dialog, padding=8)
    btns.pack(fill=tk.X)
    ttk.Button(btns, text='Save', command=save).pack(side=tk.LEFT, padx=4)
    ttk.Button(btns, text='Cancel', command=dialog.destroy).pack(side=tk.LEFT, padx=4)

    if get_status().unlock_files_ready:
        do_unlock()

    parent.wait_window(dialog)
    return result['ok']
