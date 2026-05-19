#!/usr/bin/env python3
"""Headless / SSH CLI entry point (no GUI required)."""
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from cli.main import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
