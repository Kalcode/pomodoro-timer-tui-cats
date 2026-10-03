"""The config file (spec §9): ~/.config/pomo/config.toml, every key optional."""

from __future__ import annotations

import dataclasses
import os
import secrets
import stat
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class ConfigError(Exception):
    """The config can't be used. The message is shown to the user as-is."""


@dataclass(frozen=True)
class Config:
    ntfy_server: str = "https://ntfy.sh"
    # A secret: never logged, never a flag, and kept out of repr() because crash tracebacks print locals.
    topic: str = field(default="", repr=False)
    focus: int = 25
    short_break: int = 5
    long_break: int = 15
    long_every: int = 4


STARTER = """\
# pomo settings. Every key is optional: delete a line to get the default back.

# Phone pings go through ntfy (https://ntfy.sh). Anyone who knows your topic can
# read your pings, so this one was made up at random, just for you. To get them,
# install the ntfy app, tap +, and subscribe to this topic. Then check it works
# with: pomo --test-ping
ntfy_server = "https://ntfy.sh"
topic = "{topic}"

# Lengths, in minutes
focus = 25
short_break = 5
long_break = 15
long_every = 4  # a long break after this many focus sessions
"""

_MINUTE_KEYS = ("focus", "short_break", "long_break")
_MAX_MINUTES = 24 * 60
_MAX_LONG_EVERY = 100


def load_config(path: Path) -> Config:
    """Read the config file. A missing file means all defaults."""
    if not path.exists():
        return Config()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: not valid TOML ({e})") from None
    except (OSError, UnicodeDecodeError) as e:
        raise ConfigError(f"{path}: can't read it ({e})") from None
    known = {f.name for f in dataclasses.fields(Config)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ConfigError(f"{path}: unknown key(s): {', '.join(unknown)}")
    return validate(Config(**data), source=str(path))


def validate(cfg: Config, source: str) -> Config:
    for name in ("ntfy_server", "topic"):
        if not isinstance(getattr(cfg, name), str):
            raise ConfigError(f"{source}: {name} must be a string")
    for name in (*_MINUTE_KEYS, "long_every"):
        value = getattr(cfg, name)
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{source}: {name} must be a whole number")
        limit = _MAX_LONG_EVERY if name == "long_every" else _MAX_MINUTES
        if not 1 <= value <= limit:
            raise ConfigError(f"{source}: {name} must be between 1 and {limit}")
    if not cfg.ntfy_server.startswith(("http://", "https://")):
        raise ConfigError(f"{source}: ntfy_server must start with http:// or https://")
    return cfg


def with_overrides(cfg: Config, **overrides: int | None) -> Config:
    """Apply command-line flags on top of the file. None means 'flag not given'."""
    changes = {key: value for key, value in overrides.items() if value is not None}
    return validate(dataclasses.replace(cfg, **changes), source="command line")


def new_topic() -> str:
    """An unguessable ntfy topic: ntfy allows letters, digits, - and _ (token_urlsafe uses only those)."""
    return "pomo-" + secrets.token_urlsafe(16)


def write_starter(path: Path, topic: str) -> bool:
    """Create a commented config file, private from its first byte. False, untouched, if one is already there."""
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(STARTER.format(topic=topic))
    return True


def permission_warning(path: Path, cfg: Config) -> str | None:
    """Warn (never chmod) when the file holding the topic is readable by others."""
    if not cfg.topic or not path.exists():
        return None
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        shown = display_path(path)
        return f"{shown} holds your ntfy topic but others can read it. Run: chmod 600 {shown}"
    return None


def display_path(path: Path) -> str:
    """~/... for anything under the home directory, so messages stay short."""
    try:
        return "~/" + str(path.resolve().relative_to(Path.home().resolve()))
    except ValueError:
        return str(path)
