#!/usr/bin/env bash
# Terminal CLI — works without X11 / desktop (SSH, servers).
set -e
cd "$(dirname "$0")"
export PYTHONPATH="${PWD}${PYTHONPATH:+:$PYTHONPATH}"
python3 -m pip install -q -r requirements.txt
exec python3 cosmos_cli.py "$@"
