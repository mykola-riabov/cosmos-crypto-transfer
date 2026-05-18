#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
export PYTHONPATH="${PWD}${PYTHONPATH:+:$PYTHONPATH}"

if ! python3 -c "import tkinter" 2>/dev/null; then
  echo "Install tkinter: sudo apt install python3-tk"
  exit 1
fi

python3 -m pip install -q -r requirements.txt
exec python3 gui_crypto.py
