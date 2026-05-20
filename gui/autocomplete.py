"""Search-as-you-type for ttk.Combobox — ticker prefix or denom substring."""

from __future__ import annotations

from typing import Callable, List

import tkinter as tk
from tkinter import ttk

_IGNORE_KEYS = frozenset(
    {
        'Up',
        'Down',
        'Left',
        'Right',
        'Return',
        'Tab',
        'Escape',
        'Shift_L',
        'Shift_R',
        'Control_L',
        'Control_R',
        'Alt_L',
        'Alt_R',
    }
)


def symbol_from_display(display: str) -> str:
    """'OSMO — uosmo' → 'OSMO'."""
    return (display or '').split(' — ', 1)[0].strip()


def token_matches(display: str, needle: str) -> bool:
    """Match ticker prefix or substring of on-chain denom (e.g. ibc/498A…)."""
    if not needle:
        return True
    n = needle.strip().lower()
    if not n:
        return True
    sym = symbol_from_display(display).lower()
    parts = display.split(' — ', 1)
    denom = parts[1].lower() if len(parts) > 1 else ''
    full = display.lower()
    return sym.startswith(n) or (denom and n in denom) or n in full


def filter_token_values(all_values: List[str], needle: str) -> List[str]:
    n = (needle or '').strip()
    if not n:
        return list(all_values)
    return [v for v in all_values if token_matches(v, n)]


def prefix_matches(typed: str, candidates: List[str]) -> List[str]:
    """Single candidate when filter already narrowed to one match."""
    prefix = (typed or '').strip().lower()
    if not prefix:
        return []
    matches = [c for c in candidates if token_matches(c, prefix)]
    return matches if len(matches) == 1 else []


def resolve_combobox_value(typed: str, candidates: List[str]) -> str | None:
    """Pick a single candidate from partial input, or None if ambiguous."""
    needle = (typed or '').strip()
    if not needle or not candidates:
        return None
    if needle in candidates:
        return needle
    lower = needle.lower()
    exact = [c for c in candidates if c.lower() == lower]
    if len(exact) == 1:
        return exact[0]
    exact_sym = [
        c for c in candidates if symbol_from_display(c).lower() == lower
    ]
    if len(exact_sym) == 1:
        return exact_sym[0]
    by_denom = [
        c
        for c in candidates
        if ' — ' in c and lower in c.split(' — ', 1)[1].lower()
    ]
    if len(by_denom) == 1:
        return by_denom[0]
    starts = prefix_matches(needle, candidates)
    if len(starts) == 1:
        return starts[0]
    return None


def bind_searchable_combobox(
    combobox: ttk.Combobox,
    get_values: Callable[[], List[str]],
    on_change: Callable[[], None] | None = None,
    textvariable: tk.StringVar | None = None,
) -> Callable[[], None]:
    """
    Type to filter: ticker prefix or part of on-chain denom (e.g. ``ibc/498A``).

    Example: ``os`` shows OSMO variants; ``498a`` finds a USDC by IBC hash.
    Tab / Enter picks the value when it is unambiguous.
    """
    state: dict = {'all': [], 'ignore_keys': False}

    def refresh() -> None:
        state['all'] = list(get_values())
        combobox['values'] = state['all']

    def commit_value(value: str) -> None:
        value = value.strip()
        if not value:
            return
        if textvariable is not None:
            textvariable.set(value)
        else:
            combobox.set(value)

    def apply_filter(_event=None) -> None:
        if state['ignore_keys']:
            return
        if _event is not None and _event.keysym in _IGNORE_KEYS:
            return
        needle = combobox.get().strip()
        if not needle:
            combobox['values'] = state['all']
            return
        filtered = filter_token_values(state['all'], needle)
        combobox['values'] = filtered
        if filtered:
            combobox.after(1, lambda: combobox.event_generate('<Down>'))

    def on_selected(_event=None) -> None:
        state['ignore_keys'] = True
        try:
            values = list(combobox['values'])
            idx = combobox.current()
            if idx >= 0 and idx < len(values):
                commit_value(values[idx])
            else:
                picked = resolve_combobox_value(combobox.get(), state['all'])
                if picked:
                    commit_value(picked)
            refresh()
            if on_change:
                on_change()
        finally:
            combobox.after(50, lambda: state.__setitem__('ignore_keys', False))

    def on_return(_event=None) -> None:
        picked = resolve_combobox_value(combobox.get(), state['all'])
        if picked is not None:
            commit_value(picked)
        refresh()
        if on_change:
            on_change()
        return 'break'

    def on_tab(_event=None) -> None:
        picked = resolve_combobox_value(combobox.get(), state['all'])
        if picked is not None:
            commit_value(picked)
            if on_change:
                on_change()
        return 'break'

    def on_focus_out(_event=None) -> None:
        picked = resolve_combobox_value(combobox.get(), state['all'])
        if picked is not None:
            commit_value(picked)

    combobox.configure(state='normal')
    combobox.bind('<KeyRelease>', apply_filter)
    combobox.bind('<<ComboboxSelected>>', on_selected)
    combobox.bind('<Return>', on_return)
    combobox.bind('<Tab>', on_tab)
    combobox.bind('<FocusOut>', on_focus_out)
    refresh()
    return refresh


def bind_readonly_combobox(
    combobox: ttk.Combobox,
    get_values: Callable[[], List[str]],
    on_change: Callable[[], None] | None = None,
    textvariable: tk.StringVar | None = None,
) -> Callable[[], None]:
    """
    Dropdown-only combobox (reliable selection on Linux). Updates textvariable on pick.
    """
    def refresh() -> None:
        combobox['values'] = list(get_values())

    def on_selected(_event=None) -> None:
        values = list(combobox['values'])
        idx = combobox.current()
        if textvariable is not None and idx >= 0 and idx < len(values):
            textvariable.set(values[idx])
        elif textvariable is not None:
            value = combobox.get().strip()
            if value:
                textvariable.set(value)
        if on_change:
            on_change()

    combobox.configure(state='readonly')
    combobox.bind('<<ComboboxSelected>>', on_selected)
    refresh()
    return refresh
