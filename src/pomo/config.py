"""The config file (spec §9): ~/.config/pomo/config.toml, every key optional."""

from __future__ import annotations

import dataclasses
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


def permission_warning(path: Path, cfg: Config) -> str | None:
    """Warn (never chmod) when the file holding the topic is readable by others."""
    if not cfg.topic or not path.exists():
        return None
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        return f"{path} holds your ntfy topic but others can read it. Run: chmod 600 {path}"
    return None
