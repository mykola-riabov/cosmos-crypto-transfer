"""Tk/ttk color themes for the desktop GUI."""
from dataclasses import dataclass
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import ttk

from gui.appearance import MONO_FONT_CANDIDATES, _first_available, apply_sv_theme, polish_ttk, setup_ui_fonts

CUSTOM_COLOR_FIELDS = (
    'bg',
    'fg',
    'muted',
    'accent',
    'border',
    'input_bg',
    'input_fg',
    'select_bg',
    'log_bg',
    'log_fg',
    'success',
    'warning',
    'error',
    'button_bg',
    'button_fg',
)


@dataclass(frozen=True)
class ThemePalette:
    name: str
    label: str
    bg: str
    fg: str
    muted: str
    accent: str
    border: str
    input_bg: str
    input_fg: str
    select_bg: str
    log_bg: str
    log_fg: str
    success: str
    warning: str
    error: str
    button_bg: str
    button_fg: str


def _p(
    name,
    label,
    bg,
    fg,
    muted,
    accent,
    border,
    input_bg,
    input_fg=None,
    select_bg=None,
    log_bg=None,
    log_fg=None,
    success='#a6e3a1',
    warning='#f9e2af',
    error='#f38ba8',
    button_bg=None,
    button_fg=None,
):
    input_fg = input_fg or fg
    select_bg = select_bg or border
    log_bg = log_bg or bg
    log_fg = log_fg or fg
    button_bg = button_bg or border
    button_fg = button_fg or fg
    return ThemePalette(
        name=name,
        label=label,
        bg=bg,
        fg=fg,
        muted=muted,
        accent=accent,
        border=border,
        input_bg=input_bg,
        input_fg=input_fg,
        select_bg=select_bg,
        log_bg=log_bg,
        log_fg=log_fg,
        success=success,
        warning=warning,
        error=error,
        button_bg=button_bg,
        button_fg=button_fg,
    )


THEMES: Dict[str, ThemePalette] = {
    'dark': _p('dark', 'Dark (Catppuccin)', '#1e1e2e', '#cdd6f4', '#a6adc8', '#89b4fa', '#45475a', '#313244', log_bg='#11111b'),
    'light': _p('light', 'Light', '#eff1f5', '#4c4f69', '#6c6f85', '#1e66f5', '#ccd0da', '#ffffff', log_bg='#ffffff'),
    'dracula': _p('dracula', 'Dracula', '#282a36', '#f8f8f2', '#6272a4', '#bd93f9', '#44475a', '#383a59', log_bg='#21222c'),
    'nord': _p('nord', 'Nord', '#2e3440', '#eceff4', '#d8dee9', '#88c0d0', '#4c566a', '#3b4252', log_bg='#242933'),
    'gruvbox_dark': _p('gruvbox_dark', 'Gruvbox Dark', '#282828', '#ebdbb2', '#a89984', '#b8bb26', '#3c3836', '#32302f', log_bg='#1d2021'),
    'one_dark': _p('one_dark', 'One Dark', '#282c34', '#abb2bf', '#5c6370', '#61afef', '#3e4451', '#21252b', log_bg='#1e2127'),
    'rose_pine': _p('rose_pine', 'Rosé Pine', '#191724', '#e0def4', '#908caa', '#c4a7e7', '#403d52', '#1f1d2e', log_bg='#12101a'),
    'solarized_dark': _p(
        'solarized_dark',
        'Solarized Dark',
        '#002b36',
        '#93a1a1',
        '#657b83',
        '#2aa198',
        '#073642',
        '#073642',
        log_bg='#001e26',
    ),
    'solarized_light': _p(
        'solarized_light',
        'Solarized Light',
        '#fdf6e3',
        '#657b83',
        '#839496',
        '#268bd2',
        '#eee8d5',
        '#fdf6e3',
        log_bg='#fdf6e3',
        success='#859900',
        warning='#b58900',
        error='#dc322f',
    ),
    'midnight': _p('midnight', 'Midnight', '#0d1117', '#c9d1d9', '#8b949e', '#58a6ff', '#30363d', '#161b22', log_bg='#010409'),
    'forest': _p('forest', 'Forest', '#1a2421', '#d4e7d4', '#8faa8f', '#95d5b2', '#2d3f3a', '#243530', log_bg='#121a18'),
}

DEFAULT_THEME = 'dark'
CUSTOM_THEME_ID = 'custom'


def default_custom_colors() -> Dict[str, str]:
    base = THEMES['dark']
    return {field: getattr(base, field) for field in CUSTOM_COLOR_FIELDS}


def palette_from_custom(colors: Dict[str, str]) -> ThemePalette:
    base = default_custom_colors()
    base.update({k: v for k, v in colors.items() if k in CUSTOM_COLOR_FIELDS})
    return _p(
        CUSTOM_THEME_ID,
        'Custom',
        base['bg'],
        base['fg'],
        base['muted'],
        base['accent'],
        base['border'],
        base['input_bg'],
        input_fg=base['input_fg'],
        select_bg=base['select_bg'],
        log_bg=base['log_bg'],
        log_fg=base['log_fg'],
        success=base['success'],
        warning=base['warning'],
        error=base['error'],
        button_bg=base['button_bg'],
        button_fg=base['button_fg'],
    )


def is_dark_palette(palette: ThemePalette) -> bool:
    if palette.name in {
        'light',
        'solarized_light',
    }:
        return False
    if palette.name == CUSTOM_THEME_ID:
        hexv = palette.bg.lstrip('#')
        if len(hexv) == 6:
            r, g, b = int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16)
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            return luminance < 140
        return True
    return True


def theme_ids() -> List[str]:
    return list(THEMES.keys()) + [CUSTOM_THEME_ID]


def theme_labels_map() -> Dict[str, str]:
    labels = {theme_id: palette.label for theme_id, palette in THEMES.items()}
    labels[CUSTOM_THEME_ID] = 'Custom (editable)'
    return labels


def theme_names() -> List[str]:
    return theme_ids()


def resolve_palette(theme_name: str, settings: Optional[dict] = None) -> ThemePalette:
    if theme_name == CUSTOM_THEME_ID:
        colors = {}
        if settings:
            colors = settings.get('custom_colors') or {}
        return palette_from_custom(colors)
    return THEMES.get(theme_name, THEMES[DEFAULT_THEME])


def get_palette(theme_name: str, settings: Optional[dict] = None) -> ThemePalette:
    return resolve_palette(theme_name, settings)


def apply_theme(
    root: tk.Tk,
    style: ttk.Style,
    theme_name: str,
    settings: Optional[dict] = None,
) -> ThemePalette:
    palette = resolve_palette(theme_name, settings)
    setup_ui_fonts(root)
    sv_mode = 'dark' if is_dark_palette(palette) else 'light'
    sv_active = apply_sv_theme(sv_mode)
    root.configure(bg=palette.bg)
    polish_ttk(style, palette, sv_active=sv_active)
    return palette


def style_listbox(widget: tk.Listbox, palette: ThemePalette) -> None:
    widget.configure(
        bg=palette.input_bg,
        fg=palette.fg,
        selectbackground=palette.accent,
        selectforeground='#1e1e2e' if palette.name in {'dark', 'dracula', 'nord', 'onedark', 'midnight', 'forest'} else '#ffffff',
        highlightthickness=1,
        highlightbackground=palette.border,
        highlightcolor=palette.accent,
        relief=tk.FLAT,
        activestyle='none',
    )


def style_text_widget(widget: tk.Text, palette: ThemePalette, *, mono: bool = True) -> None:
    font = _first_available(MONO_FONT_CANDIDATES, 9) if mono else _first_available(
        ('Cantarell', 'Ubuntu', 'Segoe UI', 'TkDefaultFont'), 10
    )

    widget.configure(
        bg=palette.log_bg,
        fg=palette.log_fg,
        insertbackground=palette.fg,
        selectbackground=palette.select_bg,
        font=font,
        relief=tk.FLAT,
        highlightthickness=1,
        highlightbackground=palette.border,
        highlightcolor=palette.accent,
        padx=8,
        pady=6,
    )


def style_canvas(widget: tk.Canvas, palette: ThemePalette) -> None:
    widget.configure(bg=palette.bg, highlightthickness=0)
