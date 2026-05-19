"""Search-as-you-type for ttk.Combobox (type to filter options)."""

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
        'Shift_L',
        'Shift_R',
        'Control_L',
        'Control_R',
        'Alt_L',
        'Alt_R',
    }
)


def resolve_combobox_value(typed: str, candidates: List[str]) -> str | None:
    """Pick a single candidate from partial input, or None if ambiguous."""
    needle = typed.strip()
    if not needle or not candidates:
        return None
    if needle in candidates:
        return needle
    lower = needle.lower()
    exact = [c for c in candidates if c.lower() == lower]
    if len(exact) == 1:
        return exact[0]
    starts = [c for c in candidates if c.lower().startswith(lower)]
    if len(starts) == 1:
        return starts[0]
    contains = [c for c in candidates if lower in c.lower()]
    if len(contains) == 1:
        return contains[0]
    return None


def bind_searchable_combobox(
    combobox: ttk.Combobox,
    get_values: Callable[[], List[str]],
    on_change: Callable[[], None] | None = None,
    textvariable: tk.StringVar | None = None,
) -> Callable[[], None]:
    """
    Allow typing in a Combobox to filter `values`. Returns a refresh function
    to reload the full list from get_values().

    Pass `textvariable` so dropdown picks update the bound StringVar reliably
    (required on Linux when state='normal').
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
        needle = combobox.get().strip().lower()
        if not needle:
            combobox['values'] = state['all']
            return
        combobox['values'] = [v for v in state['all'] if needle in v.lower()]

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

    combobox.configure(state='normal')
    combobox.bind('<KeyRelease>', apply_filter)
    combobox.bind('<<ComboboxSelected>>', on_selected)
    combobox.bind('<Return>', on_return)
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
