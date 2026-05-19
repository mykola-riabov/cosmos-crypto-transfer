"""Dialog to edit custom theme colors."""
import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

from gui.theme import CUSTOM_COLOR_FIELDS, default_custom_colors


class CustomThemeDialog(tk.Toplevel):
    def __init__(self, parent, colors: dict, on_save):
        super().__init__(parent)
        self.title('Custom theme colors')
        self.transient(parent)
        self.grab_set()
        self._on_save = on_save
        self._vars = {}

        defaults = default_custom_colors()
        merged = dict(defaults)
        merged.update({k: colors.get(k, defaults[k]) for k in CUSTOM_COLOR_FIELDS})

        canvas = tk.Canvas(self, highlightthickness=0)
        scroll = ttk.Scrollbar(self, orient=tk.VERTICAL, command=canvas.yview)
        inner = ttk.Frame(canvas, padding=12)
        inner.bind('<Configure>', lambda _e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=inner, anchor=tk.NW)
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Label(
            inner,
            text='Pick colors for the Custom theme. Values are saved in gui_settings.json.',
            wraplength=420,
        ).grid(row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 12))

        for row, field in enumerate(CUSTOM_COLOR_FIELDS, start=1):
            ttk.Label(inner, text=field).grid(row=row, column=0, sticky=tk.W, padx=(0, 8), pady=3)
            var = tk.StringVar(value=merged[field])
            self._vars[field] = var
            entry = ttk.Entry(inner, textvariable=var, width=12)
            entry.grid(row=row, column=1, sticky=tk.W, pady=3)
            ttk.Button(
                inner,
                text='Pick…',
                command=lambda f=field: self._pick_color(f),
                width=8,
            ).grid(row=row, column=2, sticky=tk.W, padx=(8, 0), pady=3)

        btns = ttk.Frame(inner)
        btns.grid(row=len(CUSTOM_COLOR_FIELDS) + 1, column=0, columnspan=3, sticky=tk.W, pady=(16, 0))
        ttk.Button(btns, text='Save', command=self._save).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btns, text='Reset to Dark defaults', command=self._reset).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btns, text='Cancel', command=self.destroy).pack(side=tk.LEFT)

        self.geometry('480x520')
        self.minsize(400, 400)

    def _pick_color(self, field: str):
        current = self._vars[field].get()
        result = colorchooser.askcolor(color=current, title=f'Color: {field}', parent=self)
        if result and result[1]:
            self._vars[field].set(result[1])

    def _reset(self):
        defaults = default_custom_colors()
        for field, var in self._vars.items():
            var.set(defaults[field])

    def _save(self):
        colors = {}
        for field, var in self._vars.items():
            value = var.get().strip()
            if not value.startswith('#') or len(value) not in (4, 7):
                messagebox.showerror('Invalid color', f'{field}: use #RGB or #RRGGBB', parent=self)
                return
            colors[field] = value
        self._on_save(colors)
        self.destroy()


def open_custom_theme_dialog(parent, colors: dict, on_save) -> None:
    CustomThemeDialog(parent, colors, on_save)
