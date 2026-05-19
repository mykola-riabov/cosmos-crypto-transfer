"""Fonts and modern ttk styling (sv-ttk when available)."""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from typing import Tuple

UI_FONT_CANDIDATES = ('Cantarell', 'Ubuntu', 'Segoe UI', 'Noto Sans', 'TkDefaultFont')
MONO_FONT_CANDIDATES = ('JetBrains Mono', 'DejaVu Sans Mono', 'Consolas', 'Monospace')


def _first_available(families: Tuple[str, ...], size: int, weight: str = 'normal') -> Tuple[str, int, str]:
    available = set(tkfont.families())
    for name in families:
        if name in available or name == 'TkDefaultFont':
            return (name, size, weight)
    return ('TkDefaultFont', size, weight)


def setup_ui_fonts(root: tk.Tk) -> Tuple[Tuple[str, int, str], Tuple[str, int, str]]:
    normal = _first_available(UI_FONT_CANDIDATES, 10)
    bold = _first_available(UI_FONT_CANDIDATES, 10, 'bold')
    mono = _first_available(MONO_FONT_CANDIDATES, 9)
    root.option_add('*Font', normal)
    return normal, mono


def apply_sv_theme(mode: str) -> bool:
    try:
        import sv_ttk

        sv_ttk.set_theme('dark' if mode == 'dark' else 'light')
        return True
    except (ImportError, tk.TclError):
        return False


def polish_ttk(style: ttk.Style, palette, *, sv_active: bool) -> None:
    """Extra tweaks on top of clam or sv-ttk."""
    if not sv_active:
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass

    style.configure('.', background=palette.bg, foreground=palette.fg)
    style.configure('TFrame', background=palette.bg)
    style.configure('TLabel', background=palette.bg, foreground=palette.fg)
    style.configure(
        'TLabelframe',
        background=palette.bg,
        foreground=palette.fg,
        bordercolor=palette.border,
    )
    style.configure('TLabelframe.Label', background=palette.bg, foreground=palette.fg)
    style.configure(
        'TButton',
        padding=(12, 6),
        background=palette.button_bg,
        foreground=palette.button_fg,
        bordercolor=palette.border,
    )
    style.configure('TNotebook', background=palette.bg, tabmargins=(4, 6, 4, 0))
    style.configure(
        'TNotebook.Tab',
        padding=(14, 8),
        background=palette.button_bg,
        foreground=palette.muted,
    )
    style.configure(
        'Treeview',
        rowheight=26,
        background=palette.input_bg,
        foreground=palette.fg,
        fieldbackground=palette.input_bg,
        bordercolor=palette.border,
    )
    style.configure(
        'Treeview.Heading',
        background=palette.button_bg,
        foreground=palette.fg,
        relief='flat',
        padding=(8, 6),
    )
    style.configure(
        'Vertical.TScrollbar',
        background=palette.button_bg,
        troughcolor=palette.bg,
        bordercolor=palette.border,
    )
    style.configure(
        'Horizontal.TScrollbar',
        background=palette.button_bg,
        troughcolor=palette.bg,
        bordercolor=palette.border,
    )
    style.configure('TPanedwindow', background=palette.bg)
    style.configure(
        'TCombobox',
        fieldbackground=palette.input_bg,
        background=palette.button_bg,
        foreground=palette.input_fg,
        arrowcolor=palette.fg,
    )
    style.configure(
        'TEntry',
        fieldbackground=palette.input_bg,
        foreground=palette.input_fg,
        insertcolor=palette.fg,
    )
    style.configure('TCheckbutton', background=palette.bg, foreground=palette.fg)

    style.map(
        'TButton',
        background=[('active', palette.select_bg), ('pressed', palette.border)],
        foreground=[('disabled', palette.muted)],
    )
    style.map(
        'TNotebook.Tab',
        background=[('selected', palette.input_bg)],
        foreground=[('selected', palette.fg)],
    )
    style.map(
        'Treeview',
        background=[('selected', palette.accent)],
        foreground=[('selected', '#1e1e2e' if palette.name == 'dark' else '#ffffff')],
    )
    style.map('TCombobox', fieldbackground=[('readonly', palette.input_bg)])
