"""Treeview row tags for signed percent changes (Market tab)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import List, Tuple


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = (hex_color or '#888888').lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    if len(h) != 6:
        return (136, 136, 136)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return '#{:02x}{:02x}{:02x}'.format(
        max(0, min(255, rgb[0])),
        max(0, min(255, rgb[1])),
        max(0, min(255, rgb[2])),
    )


def blend_hex(base: str, target: str, amount: float) -> str:
    """Blend base→target; amount 0 = base, 1 = full target."""
    t = max(0.0, min(1.0, float(amount)))
    b = _hex_to_rgb(base)
    e = _hex_to_rgb(target)
    return _rgb_to_hex(
        (
            int(b[0] + (e[0] - b[0]) * t),
            int(b[1] + (e[1] - b[1]) * t),
            int(b[2] + (e[2] - b[2]) * t),
        )
    )


def change_row_tag(value: float, max_abs: float, *, levels: int = 5) -> str:
    """Tag name from signed change magnitude (for Treeview row foreground)."""
    if max_abs <= 0:
        max_abs = 1.0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 'chg_zero'
    if abs(v) < 1e-12:
        return 'chg_zero'
    ratio = min(1.0, abs(v) / max_abs)
    idx = min(levels - 1, int(ratio * levels))
    if v > 0:
        return f'chg_pos_{idx}'
    return f'chg_neg_{idx}'


def configure_market_change_tags(
    tree: ttk.Treeview,
    *,
    bg: str,
    fg: str,
    success: str,
    error: str,
    muted: str,
    levels: int = 5,
) -> None:
    """Register chg_pos_* / chg_neg_* tags; stronger tint for larger |change|."""
    for i in range(levels):
        t = (i + 1) / levels
        tree.tag_configure(f'chg_pos_{i}', foreground=blend_hex(bg, success, 0.35 + 0.65 * t))
        tree.tag_configure(f'chg_neg_{i}', foreground=blend_hex(bg, error, 0.35 + 0.65 * t))
    tree.tag_configure('chg_zero', foreground=muted or fg)


def format_signed_change(value) -> str:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return ''
    if v > 0:
        return f'+{v:.4g}'
    return f'{v:.4g}'
