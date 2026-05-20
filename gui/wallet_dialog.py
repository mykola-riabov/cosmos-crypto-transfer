"""Create / import wallet: generate or paste mnemonic / private key."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from chain.wallets.secret_vault import VaultError, get_status, unlock
from config.config_path import ConfigPath
from project_utils.wallet_mnemonic import generate_mnemonic, normalize_secret_input


def show_create_wallet_dialog(parent) -> str | None:
    from gui import services

    status = get_status()
    need_vault = not status.vault_initialized

    dialog = tk.Toplevel(parent)
    dialog.title('Create / import wallet')
    dialog.transient(parent)
    dialog.grab_set()
    dialog.resizable(True, True)
    dialog.minsize(540, 520)

    ttk.Label(
        dialog,
        text='Each wallet has its own seed or private key in the KeePass vault (w1, w2, …).',
        wraplength=500,
    ).pack(anchor=tk.W, padx=12, pady=(12, 6))

    name_row = ttk.Frame(dialog)
    name_row.pack(fill=tk.X, padx=12, pady=4)
    ttk.Label(name_row, text='Wallet name:').pack(side=tk.LEFT)
    name_var = tk.StringVar(value='')
    ttk.Entry(name_row, textvariable=name_var, width=36).pack(side=tk.LEFT, padx=(8, 0))

    notebook = ttk.Notebook(dialog)
    notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

    tab_new = ttk.Frame(notebook, padding=8)
    tab_import = ttk.Frame(notebook, padding=8)
    notebook.add(tab_new, text='Generate new')
    notebook.add(tab_import, text='Import existing')

    words_var = tk.IntVar(value=24)
    words_row = ttk.Frame(tab_new)
    words_row.pack(fill=tk.X, pady=4)
    ttk.Label(words_row, text='Mnemonic length:').pack(side=tk.LEFT)
    ttk.Radiobutton(words_row, text='12 words', variable=words_var, value=12).pack(side=tk.LEFT, padx=8)
    ttk.Radiobutton(words_row, text='24 words', variable=words_var, value=24).pack(side=tk.LEFT)

    ttk.Label(tab_new, text='Generated mnemonic (shown once — save offline):').pack(anchor=tk.W, pady=(8, 4))
    new_frame = ttk.Frame(tab_new)
    new_frame.pack(fill=tk.BOTH, expand=True)
    new_scroll = ttk.Scrollbar(new_frame, orient=tk.VERTICAL)
    txt_new = tk.Text(new_frame, height=4, wrap=tk.WORD, yscrollcommand=new_scroll.set, font=('', 10))
    new_scroll.config(command=txt_new.yview)
    txt_new.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    new_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def fill_generated():
        phrase = generate_mnemonic(int(words_var.get()))
        txt_new.configure(state=tk.NORMAL)
        txt_new.delete('1.0', tk.END)
        txt_new.insert('1.0', phrase)

    ttk.Button(tab_new, text='Generate mnemonic', command=fill_generated).pack(anchor=tk.W, pady=6)
    fill_generated()

    ttk.Label(
        tab_import,
        text='Paste a BIP39 mnemonic (12/24 words) or a 64-character hex private key:',
        wraplength=480,
    ).pack(anchor=tk.W, pady=(0, 6))
    imp_frame = ttk.Frame(tab_import)
    imp_frame.pack(fill=tk.BOTH, expand=True)
    imp_scroll = ttk.Scrollbar(imp_frame, orient=tk.VERTICAL)
    txt_import = tk.Text(imp_frame, height=6, wrap=tk.WORD, yscrollcommand=imp_scroll.set, font=('', 10))
    imp_scroll.config(command=txt_import.yview)
    txt_import.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    imp_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    if need_vault:
        vault_frame = ttk.LabelFrame(dialog, text='Vault master password (first wallet only)', padding=8)
        vault_frame.pack(fill=tk.X, padx=12, pady=4)
        ttk.Label(vault_frame, text=f'Files in {ConfigPath.secrets_path}', wraplength=460).pack(anchor=tk.W)
        var_master = tk.StringVar()
        ttk.Label(vault_frame, text='Master password:').pack(anchor=tk.W, pady=(6, 2))
        ttk.Entry(vault_frame, textvariable=var_master, show='•', width=40).pack(anchor=tk.W)
        var_master2 = tk.StringVar()
        ttk.Label(vault_frame, text='Confirm:').pack(anchor=tk.W, pady=(6, 2))
        ttk.Entry(vault_frame, textvariable=var_master2, show='•', width=40).pack(anchor=tk.W)
        var_write_pw = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            vault_frame,
            text='Save master.password locally (copy to USB; delete when idle)',
            variable=var_write_pw,
        ).pack(anchor=tk.W, pady=6)
    else:
        var_master = var_master2 = var_write_pw = None

    confirm_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(
        dialog,
        text='I have saved the secret and understand loss of access if it is lost',
        variable=confirm_var,
    ).pack(anchor=tk.W, padx=12, pady=6)

    result: dict = {'wallet_id': None}

    def _read_secret() -> tuple[str, str]:
        if notebook.index(notebook.select()) == 0:
            return 'mnemonic', txt_new.get('1.0', tk.END).strip()
        raw = txt_import.get('1.0', tk.END).strip()
        return normalize_secret_input(raw)

    def submit():
        if not confirm_var.get():
            messagebox.showwarning('Wallet', 'Confirm that you have saved the secret.', parent=dialog)
            return
        label = name_var.get().strip()
        try:
            key_type, secret_value = _read_secret()
            if need_vault:
                p1 = var_master.get().strip()
                p2 = var_master2.get().strip()
                if not p1:
                    raise VaultError('Master password is empty.')
                if p1 != p2:
                    raise VaultError('Master password fields do not match.')
                wallet_id = services.create_new_wallet(
                    label or None,
                    secret_value,
                    key_type=key_type,
                    master_password=p1,
                    write_password_file=bool(var_write_pw.get()),
                    create_vault=True,
                )
            else:
                if not status.is_unlocked and not status.unlock_files_ready:
                    messagebox.showerror(
                        'Vault locked',
                        'Unlock the vault first (Setup → Secret vault).',
                        parent=dialog,
                    )
                    return
                if status.unlock_files_ready and not status.is_unlocked:
                    unlock()
                wallet_id = services.create_new_wallet(
                    label or None,
                    secret_value,
                    key_type=key_type,
                )
            result['wallet_id'] = wallet_id
            messagebox.showinfo(
                'Wallet ready',
                f'Wallet {wallet_id} is active.\n\n'
                'Addresses and balances are updated for enabled networks.',
                parent=dialog,
            )
            dialog.destroy()
        except (VaultError, ValueError, RuntimeError) as exc:
            messagebox.showerror('Wallet', str(exc), parent=dialog)

    btn_row = ttk.Frame(dialog)
    btn_row.pack(fill=tk.X, padx=12, pady=12)
    ttk.Button(btn_row, text='Create wallet', command=submit).pack(side=tk.LEFT, padx=4)
    ttk.Button(btn_row, text='Cancel', command=dialog.destroy).pack(side=tk.LEFT, padx=4)

    parent.wait_window(dialog)
    return result['wallet_id']
