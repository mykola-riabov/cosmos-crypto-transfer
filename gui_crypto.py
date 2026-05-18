#!/usr/bin/env python3
"""Desktop GUI entry point for Cosmos Crypto Transfer."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from gui.app import run_gui  # noqa: E402

if __name__ == '__main__':
    run_gui()
