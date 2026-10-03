"""Where pomo keeps its files (XDG base directories, with the usual fallbacks)."""

from __future__ import annotations

import os
from pathlib import Path


def _xdg(var: str, fallback: str) -> Path:
    value = os.environ.get(var, "")
    # The XDG spec says relative paths must be ignored.
    if value and os.path.isabs(value):
        return Path(value)
    return Path.home() / fallback


def config_path() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / "pomo" / "config.toml"


def state_dir() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state") / "pomo"


def log_path() -> Path:
    return state_dir() / "pomo.log"


def save_path() -> Path:
    return state_dir() / "save.json"


def lock_path() -> Path:
    return state_dir() / "pomo.lock"
