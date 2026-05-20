"""Persistent JSON cache for GUI tabs (Tokens, Market) across app restarts."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from config.config_path import ConfigPath


def cache_dir() -> str:
    path = os.path.join(ConfigPath.data_path, 'gui_cache')
    os.makedirs(path, exist_ok=True)
    return path


def _safe_key(key: str) -> str:
    text = (key or 'default').strip().lower()
    text = re.sub(r'[^a-z0-9._-]+', '_', text)
    return text or 'default'


def _cache_path(namespace: str, key: str) -> str:
    return os.path.join(cache_dir(), f'{_safe_key(namespace)}__{_safe_key(key)}.json')


def save_tab_cache(namespace: str, key: str, payload: Any) -> str:
    """Write payload under namespace/key. Returns file path."""
    path = _cache_path(namespace, key)
    envelope = {
        'cached_at': time.time(),
        'cached_at_iso': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'),
        'payload': payload,
    }
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(envelope, f, indent=2, default=str)
        f.write('\n')
    os.replace(tmp, path)
    return path


def load_tab_cache(namespace: str, key: str) -> Optional[dict]:
    """Return envelope dict (cached_at, cached_at_iso, payload) or None."""
    path = _cache_path(namespace, key)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict) and 'payload' in data:
            return data
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return None


def clear_tab_cache(namespace: str, key: Optional[str] = None) -> None:
    if key is not None:
        path = _cache_path(namespace, key)
        if os.path.isfile(path):
            os.remove(path)
        return
    prefix = _safe_key(namespace) + '__'
    for name in os.listdir(cache_dir()):
        if name.startswith(prefix) and name.endswith('.json'):
            try:
                os.remove(os.path.join(cache_dir(), name))
            except OSError:
                pass
