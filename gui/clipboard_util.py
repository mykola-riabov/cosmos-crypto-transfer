"""Reliable clipboard copy on Linux (Tk + xclip/wl-copy fallback)."""

from __future__ import annotations

import shutil
import subprocess
import sys
from typing import Optional

import tkinter as tk


def _copy_via_external_tools(text: str) -> bool:
    payload = text.encode('utf-8')
    if shutil.which('wl-copy'):
        try:
            subprocess.run(
                ['wl-copy'],
                input=payload,
                check=True,
                timeout=5,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            pass
    if shutil.which('xclip'):
        try:
            subprocess.run(
                ['xclip', '-selection', 'clipboard'],
                input=payload,
                check=True,
                timeout=5,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            pass
    if shutil.which('xsel'):
        try:
            subprocess.run(
                ['xsel', '--clipboard', '--input'],
                input=payload,
                check=True,
                timeout=5,
            )
            return True
        except (OSError, subprocess.SubprocessError):
            pass
    return False


def copy_to_clipboard(widget: tk.Misc, text: str) -> bool:
    """Copy text; returns True if at least one method succeeded."""
    value = str(text or '')
    if not value:
        return False
    ok = False
    try:
        widget.clipboard_clear()
        widget.clipboard_append(value)
        widget.update_idletasks()
        ok = True
    except tk.TclError:
        pass

    if sys.platform.startswith('linux'):
        ok = _copy_via_external_tools(value) or ok

    if ok:

        def _reassert() -> None:
            try:
                widget.clipboard_clear()
                widget.clipboard_append(value)
            except tk.TclError:
                pass

        try:
            widget.after(100, _reassert)
        except tk.TclError:
            pass
    return ok
