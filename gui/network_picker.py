"""Listbox-based network picker (reliable on Linux; ttk.Combobox often ignores clicks)."""

from __future__ import annotations

from typing import Callable, List

import tkinter as tk
from tkinter import ttk


class NetworkListPicker:
    """Single-choice list bound to a StringVar."""

    def __init__(
        self,
        parent,
        textvariable: tk.StringVar,
        get_options: Callable[[], List[str]],
        on_change: Callable[[], None] | None = None,
        *,
        height: int = 5,
        width: int = 26,
    ) -> None:
        self.var = textvariable
        self.get_options = get_options
        self.on_change = on_change
        self._suppress_select = False

        frame = ttk.Frame(parent)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox = tk.Listbox(
            frame,
            height=height,
            width=width,
            exportselection=False,
            activestyle='dotbox',
        )
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.bind('<<ListboxSelect>>', self._on_list_select)
        self.listbox.bind('<ButtonRelease-1>', self._on_list_select)
        self.refresh()

    def refresh(self) -> None:
        options = list(self.get_options())
        current = self.var.get().strip()
        self._suppress_select = True
        self.listbox.delete(0, tk.END)
        select_idx = None
        for idx, name in enumerate(options):
            self.listbox.insert(tk.END, name)
            if name == current:
                select_idx = idx
        if options:
            pick = select_idx if select_idx is not None else 0
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(pick)
            self.listbox.see(pick)
            if select_idx is None:
                self.var.set(options[pick])
        self._suppress_select = False

    def set_value(self, value: str, *, fire_change: bool = False) -> None:
        self.var.set(value)
        self.refresh()
        if fire_change and self.on_change:
            self.on_change()

    def _on_list_select(self, _event=None) -> None:
        if self._suppress_select:
            return
        sel = self.listbox.curselection()
        if not sel:
            return
        value = self.listbox.get(sel[0])
        if value == self.var.get():
            return
        self.var.set(value)
        if self.on_change:
            self.on_change()
