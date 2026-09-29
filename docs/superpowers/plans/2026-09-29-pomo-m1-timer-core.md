# pomo Milestone 1: Timer Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A working terminal pomodoro timer with IDEA.md parity: the focus and break cycle, desktop and ntfy pings, config file and flags, and confirm dialogs before rule-breaking actions. No cats yet.

**Architecture:** A pure core, with no Textual imports, sits under one thin Textual shell.
- The core is `clock`, `timer`, `session` and `game/*`. `timer` is a state machine that stores when a phase ends instead of counting down.
- `session` wraps the timer and turns user actions and phase transitions into game events. Those events are rule breaks, completed focus sessions and so on, and milestone 3 feeds them to the cats.
- `notify` sends desktop and ntfy pings on a worker thread and never raises.
- The Textual app only wires keys to the session and draws text produced by `ui/view.py`.

**Tech Stack:** Python ≥ 3.12, Textual 8.2 (the only runtime dependency), pytest and pytest-asyncio, uv, hatchling.

**Spec:** `docs/superpowers/specs/2026-09-29-pomo-cats-design.md` (with `IDEA.md`). This plan is **milestone 1 of 6** (spec §13). Each later milestone gets its own plan, written against the code this one produces.

## Global Constraints

- Python `>=3.12`. The dev machine runs 3.14.
- Runtime dependencies: `textual>=8.2,<9` only. Dev dependencies: `pytest>=8`, `pytest-asyncio>=0.24`.
- Source lives in `src/pomo/`. The command is `pomo`, the entry point is `pomo.cli:main`, and `python -m pomo` also works.
- `timer.py`, `session.py`, `clock.py` and everything under `game/` must not import Textual.
- Time comes only from an injected `Clock`. Nothing in the core calls `time.time()` or `time.monotonic()` directly.
- The ntfy topic is a secret. It is never logged, never accepted as a CLI flag, and never included in a user-facing message.
- Notifications never raise into the timer. A failed ntfy request is retried once after 2 s, then dropped.
- ntfy request: `POST {ntfy_server}/{topic}` with the headers `Title`, `Priority: default` and `Tags: tomato,clock`. Titles that aren't ASCII are RFC 2047 encoded.
- Pings go out only when a phase runs to its end, never for skipped phases, and at most one per tick.
- Rule penalties (spec §3.2): abandon focus −25, skip break −20, pause over 3 min in total per focus −10. They are shown to the user as "(−N)".
- Tests never touch the real `~/.config` or `~/.local/state`. `tests/conftest.py` redirects the `XDG_*` variables.
- Target terminals are iTerm2 and Ghostty on macOS. tmux is not a target.
- Run every test with `uv run pytest` from the repo root.
- Every commit message ends with the trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

**Not in this milestone** (don't build these yet): the canvas, sprites, cats, the room, the `--gallery` flag and the truecolor warning (milestone 2). Idle mode and the `--idle` flag (milestone 4). Treats and the shop (milestone 5). The save file and the abandon penalty for an exit during focus on the next launch (milestone 6).

## Review Focus

These are the failure modes a real user is most likely to hit. Each has a test in the task that owns the code.

1. **The laptop sleeps mid-phase:** several phases end in one tick. The timer must advance through them in order and send **one** ping, not a flood. Tests: Task 3 `test_a_long_jump_finishes_several_phases_in_order`, Task 7 `test_a_sleep_wake_jump_sends_one_ping_not_a_flood`.
2. **Keys pressed while a confirm dialog is open** (space, s, r, +, q): all of them are ignored. No stacked dialogs and no double penalties. Test: Task 7 `test_keys_are_ignored_while_the_dialog_is_open`.
3. **A "yes" that arrives after the phase already changed** (focus finished while the dialog was up): nothing gets skipped. Test: Task 7 `test_a_stale_yes_does_not_skip_the_next_phase`.
4. **Pressing `-` near the end of a phase, or on a phase configured shorter than 5 min:** time never goes negative and a phase never gets longer. Tests: Task 3 `test_minus_*`.
5. **A typo in the config file** (`focus_minutes = 30`, `focus = "25"`): the user gets a one-line error and exit code 2. It is never silently ignored and never a traceback. Tests: Task 2 `test_unknown_key_*` and `test_bad_values_*`, Task 8 `test_broken_config_prints_one_line_and_exits_2`.

## File Map

| File | Responsibility | Task |
|---|---|---|
| `pyproject.toml` | Package metadata, the `pomo` script, dev dependencies, pytest config | 1 |
| `src/pomo/__init__.py`, `game/__init__.py`, `ui/__init__.py` | Package markers and `__version__` | 1 |
| `tests/conftest.py` | Redirects XDG directories for every test | 1 |
| `src/pomo/clock.py` | `Clock` protocol, `RealClock`, `FakeClock` | 1 |
| `src/pomo/paths.py` | XDG config and state paths | 2 |
| `src/pomo/config.py` | `Config`, loading and validating the TOML, flag overrides, the permission warning | 2 |
| `src/pomo/timer.py` | `Phase`, `TimerSettings`, `Transition`, `PomodoroTimer` | 3 |
| `src/pomo/game/events.py` | `RuleKind`, `RuleBreak`, `FocusCompleted`, `BreakCompleted`, `SetCompleted`, the `Event` union | 4 |
| `src/pomo/game/balance.py` | Pause allowance and penalties. Later milestones add every other number. | 4 |
| `src/pomo/session.py` | `Action`, `Session` (the timer plus the rules) | 4 |
| `src/pomo/notify.py` | `Ping`, `ping_for`, ntfy request, desktop notifications, `Notifier`, `NullNotifier` | 5 |
| `src/pomo/ui/view.py` | Pure text for the screen: clock, phase, progress, counts, messages, dialog questions | 6 |
| `src/pomo/ui/dialogs.py` | `ConfirmScreen` (y/n modal) | 7 |
| `src/pomo/ui/app.py` | `TimerScreen`, `PomoApp`: key bindings, tick loop, messages, confirmations | 7 |
| `src/pomo/cli.py`, `src/pomo/__main__.py` | Parse flags, load config, set up logging, launch the app | 8 |
| `README.md` | Install and usage | 8 |

---

### Task 1: Project scaffold and clock

**Files:**
- Create: `pyproject.toml`, `README.md` (a stub, replaced in Task 8), `src/pomo/__init__.py`, `src/pomo/game/__init__.py`, `src/pomo/ui/__init__.py`, `tests/conftest.py`, `src/pomo/clock.py`
- Test: `tests/test_clock.py`

**Interfaces:**
- Consumes: nothing. The repo already has `.gitignore`, `IDEA.md` and `docs/`.
- Produces:
  - `pomo.__version__ == "0.1.0"`
  - `Clock` protocol: `now() -> float`, in monotonic seconds
  - `RealClock()`
  - `FakeClock(start: float = 1000.0)` with `.advance(seconds: float) -> None`, which raises `ValueError` if `seconds` is negative
  - An autouse fixture that points `XDG_CONFIG_HOME` at `tmp_path/"config"` and `XDG_STATE_HOME` at `tmp_path/"state"`

- [ ] **Step 1: Create the project files**

`pyproject.toml`:

```toml
[project]
name = "pomo"
version = "0.1.0"
description = "A pomodoro timer for your terminal, with a room full of cats"
readme = "README.md"
requires-python = ">=3.12"
dependencies = ["textual>=8.2,<9"]

[project.scripts]
pomo = "pomo.cli:main"

[dependency-groups]
dev = ["pytest>=8", "pytest-asyncio>=0.24"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/pomo"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
```

`README.md` (a stub, so the package builds. Task 8 writes the real one):

```markdown
# pomo

A pomodoro timer for your terminal, with a room full of cats.
```

`src/pomo/__init__.py`:

```python
"""pomo: a pomodoro timer for your terminal, with cats."""

__version__ = "0.1.0"
```

`src/pomo/game/__init__.py`:

```python
"""Game rules and state that know nothing about the terminal."""
```

`src/pomo/ui/__init__.py`:

```python
"""Textual user interface."""
```

`tests/conftest.py`:

```python
import pytest


@pytest.fixture(autouse=True)
def isolated_xdg(tmp_path, monkeypatch):
    """Keep every test away from the real ~/.config and ~/.local/state."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
```

- [ ] **Step 2: Install the environment**

Run: `uv sync`
Expected: creates `.venv/` and installs textual, pytest and pytest-asyncio, with no errors.

- [ ] **Step 3: Write the failing test**

`tests/test_clock.py`:

```python
import pytest

from pomo.clock import FakeClock, RealClock


def test_fake_clock_only_moves_when_advanced():
    clock = FakeClock(start=50.0)
    assert clock.now() == 50.0
    clock.advance(1.5)
    assert clock.now() == 51.5


def test_fake_clock_refuses_to_go_backwards():
    with pytest.raises(ValueError):
        FakeClock().advance(-1)


def test_real_clock_never_goes_backwards():
    clock = RealClock()
    first = clock.now()
    assert clock.now() >= first
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `uv run pytest tests/test_clock.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.clock'`

- [ ] **Step 5: Implement the clock**

`src/pomo/clock.py`:

```python
"""Time sources. Anything that needs the time takes a Clock, so tests can control it."""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float:
        """Monotonic seconds. Only differences between two readings mean anything."""
        ...


class RealClock:
    def now(self) -> float:
        return time.monotonic()


class FakeClock:
    """A clock that only moves when a test tells it to."""

    def __init__(self, start: float = 1000.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("time only moves forward")
        self._now += seconds
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: `3 passed`

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock README.md src tests
git commit -m "feat: project scaffold and injectable clock" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Config file and paths

**Files:**
- Create: `src/pomo/paths.py`, `src/pomo/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: the XDG fixture from Task 1.
- Produces:
  - `config_path() -> Path`, `state_dir() -> Path`, `log_path() -> Path`. These follow `XDG_CONFIG_HOME` and `XDG_STATE_HOME` and ignore relative values.
  - `Config`, a frozen dataclass: `ntfy_server: str = "https://ntfy.sh"`, `topic: str = ""`, `focus: int = 25`, `short_break: int = 5`, `long_break: int = 15`, `long_every: int = 4`
  - `ConfigError(Exception)`. Its message is shown to the user as-is.
  - `load_config(path: Path) -> Config`. A missing file gives the defaults. Bad TOML, unknown keys and bad values raise `ConfigError`.
  - `validate(cfg: Config, source: str) -> Config`
  - `with_overrides(cfg: Config, **overrides: int | None) -> Config`. `None` means the flag wasn't given.
  - `permission_warning(path: Path, cfg: Config) -> str | None`. The warning never contains the topic.

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:

```python
from pathlib import Path

import pytest

from pomo.config import Config, ConfigError, load_config, permission_warning, with_overrides
from pomo.paths import config_path, log_path, state_dir


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text)
    return path


def test_missing_file_gives_defaults(tmp_path):
    assert load_config(tmp_path / "nope.toml") == Config()


def test_defaults_match_idea_md():
    cfg = Config()
    assert (cfg.ntfy_server, cfg.topic) == ("https://ntfy.sh", "")
    assert (cfg.focus, cfg.short_break, cfg.long_break, cfg.long_every) == (25, 5, 15, 4)


def test_reads_every_key(tmp_path):
    path = write(tmp_path, 'ntfy_server = "https://ntfy.example.com"\ntopic = "s3cret"\n'
                           "focus = 50\nshort_break = 10\nlong_break = 30\nlong_every = 3\n")
    assert load_config(path) == Config("https://ntfy.example.com", "s3cret", 50, 10, 30, 3)


def test_invalid_toml_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError, match="not valid TOML"):
        load_config(write(tmp_path, "focus = = 5"))


def test_unknown_key_is_an_error_so_typos_are_not_silently_ignored(tmp_path):
    with pytest.raises(ConfigError, match="unknown key.*focus_minutes"):
        load_config(write(tmp_path, "focus_minutes = 30"))


@pytest.mark.parametrize("line, message", [
    ('focus = "25"', "focus must be a whole number"),
    ("focus = 2.5", "focus must be a whole number"),
    ("long_every = true", "long_every must be a whole number"),
    ("short_break = 0", "short_break must be between 1 and 1440"),
    ("long_break = -5", "long_break must be between 1 and 1440"),
    ("long_every = 0", "long_every must be between 1 and 100"),
    ("topic = 42", "topic must be a string"),
    ('ntfy_server = "ntfy.sh"', "must start with http"),
])
def test_bad_values_are_config_errors(tmp_path, line, message):
    with pytest.raises(ConfigError, match=message):
        load_config(write(tmp_path, line))


def test_overrides_replace_only_given_values():
    cfg = with_overrides(Config(focus=30), focus=None, short_break=7, long_break=None, long_every=None)
    assert (cfg.focus, cfg.short_break) == (30, 7)


def test_overrides_are_validated_too():
    with pytest.raises(ConfigError, match="command line: focus"):
        with_overrides(Config(), focus=0)


def test_permission_warning_when_topic_is_world_readable(tmp_path):
    path = write(tmp_path, 'topic = "s3cret"')
    path.chmod(0o644)
    warning = permission_warning(path, Config(topic="s3cret"))
    assert warning is not None and "chmod 600" in warning
    assert "s3cret" not in warning


def test_no_permission_warning_when_private_or_no_topic(tmp_path):
    path = write(tmp_path, 'topic = "s3cret"')
    path.chmod(0o600)
    assert permission_warning(path, Config(topic="s3cret")) is None
    path.chmod(0o644)
    assert permission_warning(path, Config(topic="")) is None


def test_paths_follow_xdg(tmp_path):
    # conftest points XDG_CONFIG_HOME / XDG_STATE_HOME into tmp_path
    assert config_path() == tmp_path / "config" / "pomo" / "config.toml"
    assert state_dir() == tmp_path / "state" / "pomo"
    assert log_path() == tmp_path / "state" / "pomo" / "pomo.log"


def test_relative_xdg_paths_are_ignored(monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "relative/dir")
    assert config_path() == Path.home() / ".config" / "pomo" / "config.toml"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_config.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.config'`

- [ ] **Step 3: Implement paths**

`src/pomo/paths.py`:

```python
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
```

- [ ] **Step 4: Implement config**

`src/pomo/config.py`:

```python
"""The config file (spec §9): ~/.config/pomo/config.toml, every key optional."""

from __future__ import annotations

import dataclasses
import stat
import tomllib
from dataclasses import dataclass
from pathlib import Path


class ConfigError(Exception):
    """The config can't be used. The message is shown to the user as-is."""


@dataclass(frozen=True)
class Config:
    ntfy_server: str = "https://ntfy.sh"
    topic: str = ""  # a secret: never log it, never accept it as a flag
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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: `22 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/paths.py src/pomo/config.py tests/test_config.py
git commit -m "feat: TOML config with strict validation and XDG paths" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Pomodoro timer state machine

**Files:**
- Create: `src/pomo/timer.py`
- Test: `tests/test_timer.py`

**Interfaces:**
- Consumes: `Clock` and `FakeClock` from Task 1.
- Produces:
  - `Phase` enum with `FOCUS`, `SHORT_BREAK`, `LONG_BREAK` and the property `.is_break`.
  - `TimerSettings(focus_s, short_break_s, long_break_s, long_every)`, plus `TimerSettings.from_minutes(focus, short_break, long_break, long_every)`.
  - `Transition(ended: Phase, started: Phase, completed: bool, ended_length_s: float, focus_in_set: int)`, a frozen dataclass.
  - `PomodoroTimer(settings, clock)`:
    - Properties: `.settings`, `.phase`, `.running`, `.length`, `.focus_in_set`, `.started`.
    - Methods: `.remaining() -> float`, `.base_length(phase) -> float`, `.next_phase() -> Phase`, `.start()`, `.pause()`, `.tick() -> list[Transition]`, `.skip() -> Transition`, `.reset()`, `.adjust(minutes: int)`.
  - Module constants: `MIN_ADJUSTED_LENGTH_S = 300` and `MAX_LENGTH_S = 86400`.
- Behavior to preserve:
  - The next phase starts exactly when the last one ended, so the timer never drifts.
  - A skip keeps the timer running if it was running.
  - A skipped focus doesn't count toward the set.
  - The long break comes after every `long_every` completed focus sessions.
  - Ending a long break, whether it ran out or was skipped, resets `focus_in_set` to 0.

- [ ] **Step 1: Write the failing tests**

`tests/test_timer.py`:

```python
import pytest

from pomo.clock import FakeClock
from pomo.timer import Phase, PomodoroTimer, TimerSettings, Transition

MIN = 60.0


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def timer(clock):
    return PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), clock)


def finish(timer: PomodoroTimer, clock: FakeClock) -> list[Transition]:
    """Run the current phase to its end and return what happened."""
    timer.start()
    clock.advance(timer.remaining())
    return timer.tick()


def test_starts_ready_in_focus(timer):
    assert timer.phase is Phase.FOCUS
    assert not timer.running
    assert not timer.started
    assert timer.remaining() == 25 * MIN


def test_counts_down_while_running(timer, clock):
    timer.start()
    clock.advance(1 * MIN)
    assert timer.remaining() == 24 * MIN
    assert timer.started


def test_pause_freezes_the_countdown(timer, clock):
    timer.start()
    clock.advance(1 * MIN)
    timer.pause()
    clock.advance(10 * MIN)
    assert timer.remaining() == 24 * MIN
    assert timer.started and not timer.running


def test_finished_focus_starts_the_break_on_its_own(timer, clock):
    transitions = finish(timer, clock)
    assert transitions == [Transition(Phase.FOCUS, Phase.SHORT_BREAK, True, 25 * MIN, 1)]
    assert timer.phase is Phase.SHORT_BREAK
    assert timer.running
    assert timer.remaining() == 5 * MIN


def test_next_phase_starts_exactly_when_the_last_ended(timer, clock):
    timer.start()
    clock.advance(25 * MIN + 30)  # the tick came 30 s late
    timer.tick()
    assert timer.remaining() == 5 * MIN - 30


def test_a_long_jump_finishes_several_phases_in_order(timer, clock):
    timer.start()
    clock.advance(25 * MIN + 5 * MIN + 1 * MIN)  # e.g. the laptop slept
    transitions = timer.tick()
    assert [(t.ended, t.started) for t in transitions] == [
        (Phase.FOCUS, Phase.SHORT_BREAK),
        (Phase.SHORT_BREAK, Phase.FOCUS),
    ]
    assert timer.phase is Phase.FOCUS
    assert timer.remaining() == 24 * MIN


def test_every_fourth_focus_earns_a_long_break_then_the_set_restarts(timer, clock):
    started = []
    for _ in range(8):  # focus, break x4
        started += [t.started for t in finish(timer, clock)]
    assert started == [Phase.SHORT_BREAK, Phase.FOCUS] * 3 + [Phase.LONG_BREAK, Phase.FOCUS]
    assert timer.focus_in_set == 0


def test_next_phase_previews_the_long_break(timer, clock):
    assert timer.next_phase() is Phase.SHORT_BREAK
    for _ in range(6):
        finish(timer, clock)
    assert timer.focus_in_set == 3
    assert timer.next_phase() is Phase.LONG_BREAK


def test_skipping_focus_does_not_count_it(timer, clock):
    timer.start()
    clock.advance(10 * MIN)
    transition = timer.skip()
    assert transition == Transition(Phase.FOCUS, Phase.SHORT_BREAK, False, 25 * MIN, 0)
    assert timer.running  # the cycle keeps going
    assert timer.remaining() == 5 * MIN


def test_skipping_while_paused_leaves_the_next_phase_paused(timer):
    transition = timer.skip()
    assert transition.started is Phase.SHORT_BREAK
    assert not timer.running and not timer.started


def test_skipping_a_break_goes_to_focus(timer, clock):
    finish(timer, clock)
    transition = timer.skip()
    assert (transition.ended, transition.started, transition.completed) == (Phase.SHORT_BREAK, Phase.FOCUS, False)


def test_skipping_the_long_break_still_restarts_the_set(timer, clock):
    for _ in range(7):
        finish(timer, clock)
    assert timer.phase is Phase.LONG_BREAK
    timer.skip()
    assert timer.focus_in_set == 0


def test_reset_restores_the_full_unadjusted_length_and_stops(timer, clock):
    timer.start()
    timer.adjust(+5)
    clock.advance(3 * MIN)
    timer.reset()
    assert timer.remaining() == 25 * MIN
    assert not timer.running and not timer.started


def test_plus_adds_five_minutes_running_or_paused(timer, clock):
    timer.adjust(+5)
    assert timer.remaining() == 30 * MIN and timer.length == 30 * MIN
    assert not timer.started
    timer.start()
    clock.advance(1 * MIN)
    timer.adjust(+5)
    assert timer.remaining() == 34 * MIN


def test_minus_never_goes_below_five_minutes(timer):
    for _ in range(10):
        timer.adjust(-5)
    assert timer.length == 5 * MIN
    assert timer.remaining() == 5 * MIN


def test_minus_never_lengthens_a_phase_shorter_than_five_minutes(clock):
    timer = PomodoroTimer(TimerSettings.from_minutes(1, 1, 1, 4), clock)
    timer.adjust(-5)
    assert timer.length == 1 * MIN
    assert timer.remaining() == 1 * MIN


def test_minus_near_the_end_finishes_the_phase_on_the_next_tick(timer, clock):
    timer.start()
    clock.advance(23 * MIN)  # 2 min left
    timer.adjust(-5)  # length 20 min, which is already over
    assert timer.remaining() == 0
    transitions = timer.tick()
    assert transitions[0].completed and transitions[0].ended_length_s == 20 * MIN


def test_minus_while_paused_near_the_end_never_goes_negative(timer, clock):
    timer.start()
    clock.advance(23 * MIN)
    timer.pause()
    timer.adjust(-5)
    assert timer.remaining() == 0
    timer.start()
    assert timer.tick()[0].completed
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_timer.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.timer'`

- [ ] **Step 3: Implement the timer**

`src/pomo/timer.py`:

```python
"""The pomodoro cycle as a pure state machine (spec §3.1). No UI, no rules, no cats."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pomo.clock import Clock

MIN_ADJUSTED_LENGTH_S = 5 * 60  # "-" never shrinks a phase below this
MAX_LENGTH_S = 24 * 60 * 60


class Phase(Enum):
    FOCUS = "focus"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"

    @property
    def is_break(self) -> bool:
        return self is not Phase.FOCUS


@dataclass(frozen=True)
class TimerSettings:
    focus_s: float
    short_break_s: float
    long_break_s: float
    long_every: int

    @classmethod
    def from_minutes(cls, focus: int, short_break: int, long_break: int, long_every: int) -> TimerSettings:
        return cls(focus * 60.0, short_break * 60.0, long_break * 60.0, long_every)


@dataclass(frozen=True)
class Transition:
    ended: Phase
    started: Phase
    completed: bool  # True: ran down to zero. False: skipped.
    ended_length_s: float  # length of the phase that ended, including +/- adjustments
    focus_in_set: int  # completed focus sessions in the current set, after this transition


class PomodoroTimer:
    """Stores when the running phase ends rather than counting down, so it never drifts."""

    def __init__(self, settings: TimerSettings, clock: Clock) -> None:
        self._settings = settings
        self._clock = clock
        self._phase = Phase.FOCUS
        self._length = settings.focus_s
        self._remaining = self._length  # authoritative while not running
        self._ends_at: float | None = None  # authoritative while running
        self._focus_in_set = 0

    @property
    def settings(self) -> TimerSettings:
        return self._settings

    @property
    def phase(self) -> Phase:
        return self._phase

    @property
    def running(self) -> bool:
        return self._ends_at is not None

    @property
    def length(self) -> float:
        """Length of the current phase, including +/- adjustments."""
        return self._length

    @property
    def focus_in_set(self) -> int:
        return self._focus_in_set

    @property
    def started(self) -> bool:
        """True once the current phase has run at all (running, or paused part-way)."""
        return self.running or self._remaining < self._length

    def remaining(self) -> float:
        if self._ends_at is None:
            return self._remaining
        return max(0.0, self._ends_at - self._clock.now())

    def base_length(self, phase: Phase) -> float:
        s = self._settings
        return {Phase.FOCUS: s.focus_s, Phase.SHORT_BREAK: s.short_break_s, Phase.LONG_BREAK: s.long_break_s}[phase]

    def next_phase(self) -> Phase:
        """The phase that follows if the current one runs to the end."""
        if self._phase is Phase.FOCUS:
            finishing_set = self._focus_in_set + 1 >= self._settings.long_every
            return Phase.LONG_BREAK if finishing_set else Phase.SHORT_BREAK
        return Phase.FOCUS

    def start(self) -> None:
        if self._ends_at is None:
            self._ends_at = self._clock.now() + self._remaining

    def pause(self) -> None:
        if self._ends_at is not None:
            self._remaining = self.remaining()
            self._ends_at = None

    def tick(self) -> list[Transition]:
        """Finish every phase whose end has passed. Usually zero or one; more after a long sleep."""
        transitions = []
        now = self._clock.now()
        while self._ends_at is not None and now >= self._ends_at:
            ended_at = self._ends_at
            transitions.append(self._advance(completed=True))
            self._ends_at = ended_at + self._length  # the next phase starts exactly when the last ended
        return transitions

    def skip(self) -> Transition:
        was_running = self.running
        transition = self._advance(completed=False)
        self._ends_at = self._clock.now() + self._length if was_running else None
        return transition

    def reset(self) -> None:
        """Back to the full, unadjusted length of the current phase, stopped."""
        self._length = self.base_length(self._phase)
        self._remaining = self._length
        self._ends_at = None

    def adjust(self, minutes: int) -> None:
        """+/- keys. Removing time never goes below 5 min and never lengthens a short phase."""
        delta = minutes * 60.0
        if delta < 0:
            new_length = max(min(self._length, MIN_ADJUSTED_LENGTH_S), self._length + delta)
        else:
            new_length = min(MAX_LENGTH_S, self._length + delta)
        applied = new_length - self._length
        self._length = new_length
        if self._ends_at is not None:
            self._ends_at = max(self._clock.now(), self._ends_at + applied)
        else:
            self._remaining = max(0.0, self._remaining + applied)

    def _advance(self, completed: bool) -> Transition:
        ended, ended_length = self._phase, self._length
        if ended is Phase.FOCUS:
            if completed:
                self._focus_in_set += 1
            set_done = completed and self._focus_in_set >= self._settings.long_every
            started = Phase.LONG_BREAK if set_done else Phase.SHORT_BREAK
        else:
            if ended is Phase.LONG_BREAK:
                self._focus_in_set = 0
            started = Phase.FOCUS
        self._phase = started
        self._length = self.base_length(started)
        self._remaining = self._length
        return Transition(ended, started, completed, ended_length, self._focus_in_set)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: `40 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pomo/timer.py tests/test_timer.py
git commit -m "feat: drift-free pomodoro timer state machine" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Session: the timer plus the rules

**Files:**
- Create: `src/pomo/game/events.py`, `src/pomo/game/balance.py`, `src/pomo/session.py`
- Test: `tests/test_session.py`

**Interfaces:**
- Consumes: `Phase`, `PomodoroTimer`, `TimerSettings` and `Transition` from Task 3. `Clock` and `FakeClock` from Task 1.
- Produces:
  - Events:
    - `RuleKind` enum with `ABANDON_FOCUS`, `SKIP_BREAK`, `LONG_PAUSE`
    - `RuleBreak(kind)`, `FocusCompleted(minutes: int)`, `BreakCompleted(phase: Phase)`, `SetCompleted()`, all frozen dataclasses
    - `Event = Transition | RuleBreak | FocusCompleted | BreakCompleted | SetCompleted`
  - Balance: `balance.PAUSE_ALLOWANCE_S = 180` and `balance.PENALTIES: dict[RuleKind, int]`, which is `{ABANDON_FOCUS: 25, SKIP_BREAK: 20, LONG_PAUSE: 10}`.
  - `Action` enum with `SKIP`, `RESET`, `QUIT`.
  - `Session(settings, clock, pause_allowance_s=balance.PAUSE_ALLOWANCE_S)`:
    - `.timer`, the `PomodoroTimer` it wraps.
    - `.rule_cost(action) -> RuleKind | None`
    - `.toggle() -> None` and `.adjust(minutes) -> None`
    - `.tick()`, `.skip()`, `.reset()` and `.quit()`, which each return `list[Event]`.
- Rules (spec §3.2):

  | Action | In focus | During a break |
  |---|---|---|
  | Skip | Always `ABANDON_FOCUS` | `SKIP_BREAK` |
  | Reset | `ABANDON_FOCUS` once the focus has started, otherwise free | Free |
  | Quit | `ABANDON_FOCUS` once the focus has started, otherwise free | Free |

  - More than 3 min of pause in total during one focus is charged once as `LONG_PAUSE`. The allowance starts over with every phase.
  - `SetCompleted` comes after the `long_every`th completed focus, but only if no rule was broken since the last long break ended.
  - A `RuleBreak` is emitted **before** the `Transition` it causes.

- [ ] **Step 1: Write the failing tests**

`tests/test_session.py`:

```python
import pytest

from pomo.clock import FakeClock
from pomo.game.events import BreakCompleted, FocusCompleted, RuleBreak, RuleKind, SetCompleted
from pomo.session import Action, Session
from pomo.timer import Phase, TimerSettings, Transition

MIN = 60.0


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def session(clock):
    return Session(TimerSettings.from_minutes(25, 5, 15, 4), clock)


def finish(session: Session, clock: FakeClock) -> list:
    """Run the current phase to its end, starting it if needed."""
    if not session.timer.running:
        session.toggle()
    clock.advance(session.timer.remaining())
    return session.tick()


def rule_breaks(events) -> list[RuleKind]:
    return [e.kind for e in events if isinstance(e, RuleBreak)]


def test_rule_costs_before_focus_starts(session):
    assert session.rule_cost(Action.SKIP) is RuleKind.ABANDON_FOCUS
    assert session.rule_cost(Action.RESET) is None
    assert session.rule_cost(Action.QUIT) is None


def test_rule_costs_once_focus_has_started(session, clock):
    session.toggle()
    clock.advance(1)
    for action in Action:
        assert session.rule_cost(action) is RuleKind.ABANDON_FOCUS


def test_rule_costs_during_a_break(session, clock):
    finish(session, clock)
    assert session.rule_cost(Action.SKIP) is RuleKind.SKIP_BREAK
    assert session.rule_cost(Action.RESET) is None
    assert session.rule_cost(Action.QUIT) is None


def test_completed_focus_reports_its_minutes(session, clock):
    events = finish(session, clock)
    assert isinstance(events[0], Transition) and events[0].completed
    assert FocusCompleted(minutes=25) in events


def test_completed_focus_counts_plus_minus_adjustments(session, clock):
    session.adjust(+5)
    assert FocusCompleted(minutes=30) in finish(session, clock)


def test_completed_break_is_reported(session, clock):
    finish(session, clock)
    assert BreakCompleted(Phase.SHORT_BREAK) in finish(session, clock)


def test_skipping_focus_breaks_a_rule_and_earns_nothing(session, clock):
    session.toggle()
    clock.advance(5 * MIN)
    events = session.skip()
    assert rule_breaks(events) == [RuleKind.ABANDON_FOCUS]
    assert not any(isinstance(e, FocusCompleted) for e in events)
    assert session.timer.phase is Phase.SHORT_BREAK


def test_skipping_a_break_breaks_a_rule(session, clock):
    finish(session, clock)
    events = session.skip()
    assert rule_breaks(events) == [RuleKind.SKIP_BREAK]
    assert not any(isinstance(e, BreakCompleted) for e in events)


def test_resetting_a_started_focus_is_abandoning_it(session, clock):
    session.toggle()
    clock.advance(5 * MIN)
    assert rule_breaks(session.reset()) == [RuleKind.ABANDON_FOCUS]
    assert session.timer.remaining() == 25 * MIN and not session.timer.running


def test_resetting_an_unstarted_focus_is_free(session):
    assert session.reset() == []


def test_quitting_mid_focus_breaks_a_rule_but_quitting_on_a_break_is_free(session, clock):
    session.toggle()
    clock.advance(1)
    assert rule_breaks(session.quit()) == [RuleKind.ABANDON_FOCUS]
    finish(session, clock)
    assert session.quit() == []


def test_pausing_up_to_three_minutes_is_fine(session, clock):
    session.toggle()
    session.toggle()  # pause
    clock.advance(3 * MIN)
    assert session.tick() == []


def test_pausing_over_three_minutes_breaks_a_rule_once(session, clock):
    session.toggle()
    session.toggle()
    clock.advance(3 * MIN + 1)
    assert rule_breaks(session.tick()) == [RuleKind.LONG_PAUSE]
    clock.advance(10 * MIN)
    assert session.tick() == []


def test_pause_time_adds_up_across_pauses_in_one_focus(session, clock):
    session.toggle()
    for _ in range(2):
        session.toggle()  # pause 90 s: 3 min in total, still allowed
        clock.advance(90)
        assert session.tick() == []
        session.toggle()  # resume
    session.toggle()
    clock.advance(1)  # one more second tips it over
    assert rule_breaks(session.tick()) == [RuleKind.LONG_PAUSE]


def test_pause_allowance_starts_over_with_each_focus(session, clock):
    session.toggle()
    session.toggle()
    clock.advance(2 * MIN)
    session.toggle()
    finish(session, clock)  # focus
    finish(session, clock)  # break
    session.toggle()  # pause the new focus
    clock.advance(2 * MIN)
    assert session.tick() == []


def test_pausing_a_break_never_breaks_a_rule(session, clock):
    finish(session, clock)
    session.toggle()
    clock.advance(30 * MIN)
    assert session.tick() == []


def test_a_clean_set_earns_the_set_bonus(session, clock):
    events = []
    for _ in range(7):
        events += finish(session, clock)
    assert events.count(SetCompleted()) == 1
    assert session.timer.phase is Phase.LONG_BREAK


def test_any_rule_break_in_the_set_loses_the_bonus(session, clock):
    finish(session, clock)
    session.skip()  # skip the first break
    events = []
    for _ in range(5):  # focus 2, break, focus 3, break, focus 4
        events += finish(session, clock)
    assert session.timer.phase is Phase.LONG_BREAK
    assert SetCompleted() not in events


def test_the_next_set_starts_clean_after_the_long_break(session, clock):
    finish(session, clock)
    session.skip()  # dirty the first set
    for _ in range(5):
        finish(session, clock)
    assert session.timer.phase is Phase.LONG_BREAK
    finish(session, clock)  # long break
    events = []
    for _ in range(7):
        events += finish(session, clock)
    assert events.count(SetCompleted()) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_session.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.game.events'`

- [ ] **Step 3: Implement events**

`src/pomo/game/events.py`:

```python
"""What the session tells the rest of the game (spec §3.2, §4)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pomo.timer import Phase, Transition


class RuleKind(Enum):
    ABANDON_FOCUS = "abandon_focus"
    SKIP_BREAK = "skip_break"
    LONG_PAUSE = "long_pause"


@dataclass(frozen=True)
class RuleBreak:
    kind: RuleKind


@dataclass(frozen=True)
class FocusCompleted:
    minutes: int  # length at completion, including +/- adjustments


@dataclass(frozen=True)
class BreakCompleted:
    phase: Phase


@dataclass(frozen=True)
class SetCompleted:
    """A full set of focus sessions finished with no rule broken along the way."""


Event = Transition | RuleBreak | FocusCompleted | BreakCompleted | SetCompleted
```

- [ ] **Step 4: Implement balance**

`src/pomo/game/balance.py`:

```python
"""Every tunable game number lives here (spec §3–§4). Later milestones add to this file."""

from pomo.game.events import RuleKind

PAUSE_ALLOWANCE_S = 3 * 60  # total pause per focus before it counts as a rule break

PENALTIES = {  # mood lost by every cat (spec §3.2)
    RuleKind.ABANDON_FOCUS: 25,
    RuleKind.SKIP_BREAK: 20,
    RuleKind.LONG_PAUSE: 10,
}
```

- [ ] **Step 5: Implement the session**

`src/pomo/session.py`:

```python
"""The timer plus the rules: user actions in, events out (spec §3.1–§3.2)."""

from __future__ import annotations

from enum import Enum

from pomo.clock import Clock
from pomo.game import balance
from pomo.game.events import BreakCompleted, Event, FocusCompleted, RuleBreak, RuleKind, SetCompleted
from pomo.timer import Phase, PomodoroTimer, TimerSettings, Transition


class Action(Enum):
    """User actions that can break a rule, and so may need confirming first."""

    SKIP = "skip"
    RESET = "reset"
    QUIT = "quit"


class Session:
    def __init__(
        self,
        settings: TimerSettings,
        clock: Clock,
        pause_allowance_s: float = balance.PAUSE_ALLOWANCE_S,
    ) -> None:
        self.timer = PomodoroTimer(settings, clock)
        self._clock = clock
        self._allowance = pause_allowance_s
        self._paused_total = 0.0
        self._paused_since: float | None = None
        self._pause_charged = False
        self._set_clean = True

    def rule_cost(self, action: Action) -> RuleKind | None:
        """Which rule this action would break right now, if any."""
        if self.timer.phase is Phase.FOCUS:
            if action is Action.SKIP or self.timer.started:
                return RuleKind.ABANDON_FOCUS
            return None
        return RuleKind.SKIP_BREAK if action is Action.SKIP else None

    def toggle(self) -> None:
        now = self._clock.now()
        if self.timer.running:
            self.timer.pause()
            if self.timer.phase is Phase.FOCUS:
                self._paused_since = now
        else:
            if self._paused_since is not None:
                self._paused_total += now - self._paused_since
                self._paused_since = None
            self.timer.start()

    def adjust(self, minutes: int) -> None:
        self.timer.adjust(minutes)

    def tick(self) -> list[Event]:
        events: list[Event] = []
        for transition in self.timer.tick():
            events += self._on_transition(transition)
        return events + self._check_pause()

    def skip(self) -> list[Event]:
        events = self._break_rule(self.rule_cost(Action.SKIP))
        return events + self._on_transition(self.timer.skip())

    def reset(self) -> list[Event]:
        events = self._break_rule(self.rule_cost(Action.RESET))
        self.timer.reset()
        self._reset_pause_tracking()
        return events

    def quit(self) -> list[Event]:
        return self._break_rule(self.rule_cost(Action.QUIT))

    def _on_transition(self, transition: Transition) -> list[Event]:
        events: list[Event] = [transition]
        if transition.completed:
            if transition.ended is Phase.FOCUS:
                events.append(FocusCompleted(minutes=round(transition.ended_length_s / 60)))
                if transition.started is Phase.LONG_BREAK and self._set_clean:
                    events.append(SetCompleted())
            else:
                events.append(BreakCompleted(transition.ended))
        if transition.ended is Phase.LONG_BREAK:
            self._set_clean = True  # a new set starts
        self._reset_pause_tracking()
        return events

    def _check_pause(self) -> list[Event]:
        if self._pause_charged or self._paused_since is None:
            return []
        paused = self._paused_total + (self._clock.now() - self._paused_since)
        if paused <= self._allowance:
            return []
        self._pause_charged = True
        return self._break_rule(RuleKind.LONG_PAUSE)

    def _break_rule(self, kind: RuleKind | None) -> list[Event]:
        if kind is None:
            return []
        self._set_clean = False
        return [RuleBreak(kind)]

    def _reset_pause_tracking(self) -> None:
        self._paused_total = 0.0
        self._paused_since = None
        self._pause_charged = False
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: `59 passed`

- [ ] **Step 7: Commit**

```bash
git add src/pomo/game/events.py src/pomo/game/balance.py src/pomo/session.py tests/test_session.py
git commit -m "feat: session rules: abandon, skip-break, long-pause, clean-set bonus" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Desktop and ntfy notifications

**Files:**
- Create: `src/pomo/notify.py`
- Test: `tests/test_notify.py`

**Interfaces:**
- Consumes: `Config` from Task 2. `Phase` and `Transition` from Task 3.
- Produces:
  - `Ping(title: str, body: str)`, a frozen dataclass.
  - `Notifies`, a protocol with `send(ping) -> None`.
  - `ping_for(transition, cfg) -> Ping`.
  - `encode_header(value) -> str`.
  - `build_ntfy_request(ping, server, topic) -> urllib.request.Request`.
  - `desktop_notify(ping) -> bool`.
  - `Notifier(server, topic, *, bell, desktop=desktop_notify, post=urlopen_post, sleep=time.sleep, run=run_in_thread)` with `.send(ping)`.
  - `NullNotifier()` with `.send(ping)`.
  - Constant: `RETRY_DELAY_S = 2.0`.
- Copy, taken from IDEA.md:
  - Focus done: title `🍅 Pomodoro done!`, body `"{N} minutes of focus complete. Time for a {B} min break."`
  - Break over: title `☕ Break's over`, body `"{N} min break complete. Time to focus for {F} minutes."`

- [ ] **Step 1: Write the failing tests**

`tests/test_notify.py`:

```python
import email.header
import logging
import subprocess
import urllib.error

import pytest

from pomo import notify
from pomo.config import Config
from pomo.notify import NullNotifier, Notifier, Ping, build_ntfy_request, encode_header, ping_for
from pomo.timer import Phase, Transition

TOPIC = "super-s3cret-topic"


def transition(ended, started, minutes):
    return Transition(ended, started, True, minutes * 60.0, 1)


def test_focus_done_ping_matches_idea_md():
    ping = ping_for(transition(Phase.FOCUS, Phase.SHORT_BREAK, 25), Config())
    assert ping == Ping("🍅 Pomodoro done!", "25 minutes of focus complete. Time for a 5 min break.")


def test_focus_done_before_a_long_break_mentions_the_long_break():
    ping = ping_for(transition(Phase.FOCUS, Phase.LONG_BREAK, 25), Config())
    assert ping.body.endswith("Time for a 15 min break.")


def test_break_over_ping():
    ping = ping_for(transition(Phase.SHORT_BREAK, Phase.FOCUS, 5), Config())
    assert ping == Ping("☕ Break's over", "5 min break complete. Time to focus for 25 minutes.")


def test_ascii_headers_pass_through():
    assert encode_header("Pomodoro done!") == "Pomodoro done!"


def test_emoji_headers_are_rfc2047_encoded_and_latin1_safe():
    encoded = encode_header("🍅 Pomodoro done!")
    encoded.encode("latin-1")  # would raise if urllib couldn't send it
    ((raw, charset),) = email.header.decode_header(encoded)
    assert raw.decode(charset) == "🍅 Pomodoro done!"


def test_ntfy_request_follows_idea_md():
    request = build_ntfy_request(Ping("🍅 Pomodoro done!", "body text"), "https://ntfy.sh/", TOPIC)
    assert request.full_url == f"https://ntfy.sh/{TOPIC}"
    assert request.get_method() == "POST"
    assert request.data == b"body text"
    assert request.get_header("Priority") == "default"
    assert request.get_header("Tags") == "tomato,clock"
    assert request.get_header("Title").startswith("=?UTF-8?B?")


class Recorder:
    """Fakes for every side effect a Notifier has."""

    def __init__(self, desktop_ok=True, failures=0):
        self.desktop_ok = desktop_ok
        self.failures = failures
        self.bells = 0
        self.posts = []
        self.sleeps = []

    def notifier(self, topic=TOPIC):
        return Notifier(
            "https://ntfy.sh", topic,
            bell=self.bell, desktop=self.desktop, post=self.post, sleep=self.sleeps.append,
            run=lambda job: job(),  # run inline instead of on a thread
        )

    def bell(self):
        self.bells += 1

    def desktop(self, ping):
        return self.desktop_ok

    def post(self, request):
        self.posts.append(request)
        if len(self.posts) <= self.failures:
            raise urllib.error.HTTPError(request.full_url, 503, f"down for {TOPIC}", None, None)


PING = Ping("🍅 Pomodoro done!", "25 minutes of focus complete.")


def test_desktop_and_phone_both_get_pinged():
    rec = Recorder()
    rec.notifier().send(PING)
    assert rec.bells == 0
    assert len(rec.posts) == 1
    assert rec.sleeps == []


def test_terminal_bell_when_there_is_no_desktop_notification():
    rec = Recorder(desktop_ok=False)
    rec.notifier().send(PING)
    assert rec.bells == 1


def test_empty_topic_means_no_phone_ping():
    rec = Recorder()
    rec.notifier(topic="").send(PING)
    assert rec.posts == []


def test_ntfy_failure_retries_once_after_two_seconds():
    rec = Recorder(failures=1)
    rec.notifier().send(PING)
    assert len(rec.posts) == 2
    assert rec.sleeps == [2.0]


def test_ntfy_gives_up_quietly_after_the_retry(caplog):
    rec = Recorder(failures=5)
    with caplog.at_level(logging.WARNING):
        rec.notifier().send(PING)  # must not raise
    assert len(rec.posts) == 2
    assert "gave up" in caplog.text


def test_the_topic_never_reaches_the_log(caplog):
    rec = Recorder(failures=5)
    with caplog.at_level(logging.DEBUG):
        rec.notifier().send(PING)
    assert caplog.records
    assert TOPIC not in caplog.text


def test_a_crashing_desktop_notifier_still_lets_the_phone_ping_through():
    rec = Recorder()

    def explode(ping):
        raise RuntimeError("boom")

    notifier = Notifier("https://ntfy.sh", TOPIC, bell=rec.bell, desktop=explode, post=rec.post,
                        sleep=rec.sleeps.append, run=lambda job: job())
    notifier.send(PING)
    assert len(rec.posts) == 1


def test_null_notifier_does_nothing():
    NullNotifier().send(PING)


def test_macos_notification_passes_text_as_arguments_not_script(monkeypatch):
    calls = []
    monkeypatch.setattr(notify.sys, "platform", "darwin")
    monkeypatch.setattr(notify.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(notify.subprocess, "run", lambda cmd, **kw: calls.append(cmd))
    tricky = Ping('Title "with" quotes', 'end run" & do shell script "rm -rf ~')
    assert notify.desktop_notify(tricky) is True
    (command,) = calls
    assert command[0] == "osascript"
    assert command[-2:] == [tricky.title, tricky.body]
    assert all(tricky.body not in part for part in command[:-2])


def test_desktop_notification_reports_failure(monkeypatch):
    monkeypatch.setattr(notify.sys, "platform", "darwin")
    monkeypatch.setattr(notify.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fail(cmd, **kw):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(notify.subprocess, "run", fail)
    assert notify.desktop_notify(PING) is False


def test_no_notifier_available(monkeypatch):
    monkeypatch.setattr(notify.sys, "platform", "linux")
    monkeypatch.setattr(notify.shutil, "which", lambda name: None)
    assert notify.desktop_notify(PING) is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_notify.py -v`
Expected: FAIL during collection with `ImportError: cannot import name 'notify' from 'pomo'`

- [ ] **Step 3: Implement notifications**

`src/pomo/notify.py`:

```python
"""Desktop and ntfy phone pings on phase transitions (spec §9, IDEA.md).

Nothing in here may ever raise into the timer: every failure is logged and dropped.
The ntfy topic is a secret, so it never appears in a log line.
"""

from __future__ import annotations

import base64
import logging
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pomo.config import Config
from pomo.timer import Phase, Transition

log = logging.getLogger(__name__)

RETRY_DELAY_S = 2.0
HTTP_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class Ping:
    title: str
    body: str


class Notifies(Protocol):
    def send(self, ping: Ping) -> None: ...


def ping_for(transition: Transition, cfg: Config) -> Ping:
    minutes = round(transition.ended_length_s / 60)
    if transition.ended is Phase.FOCUS:
        break_minutes = cfg.long_break if transition.started is Phase.LONG_BREAK else cfg.short_break
        return Ping(
            "🍅 Pomodoro done!",
            f"{minutes} minutes of focus complete. Time for a {break_minutes} min break.",
        )
    return Ping("☕ Break's over", f"{minutes} min break complete. Time to focus for {cfg.focus} minutes.")


def encode_header(value: str) -> str:
    """urllib only sends latin-1 headers. ntfy accepts RFC 2047 for everything else."""
    if value.isascii():
        return value
    return "=?UTF-8?B?" + base64.b64encode(value.encode("utf-8")).decode("ascii") + "?="


def build_ntfy_request(ping: Ping, server: str, topic: str) -> urllib.request.Request:
    return urllib.request.Request(
        f"{server.rstrip('/')}/{urllib.parse.quote(topic, safe='')}",
        data=ping.body.encode("utf-8"),
        method="POST",
        headers={"Title": encode_header(ping.title), "Priority": "default", "Tags": "tomato,clock"},
    )


def urlopen_post(request: urllib.request.Request) -> None:
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:
        response.read()


def desktop_notify(ping: Ping) -> bool:
    """Show a native notification. False when this machine has no way to show one."""
    if sys.platform == "darwin" and shutil.which("osascript"):
        # Title and body travel as argv, never spliced into the script, so quotes can't break it.
        command = [
            "osascript",
            "-e", "on run argv",
            "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
            "-e", "end run",
            ping.title, ping.body,
        ]
    elif shutil.which("notify-send"):
        command = ["notify-send", ping.title, ping.body]
    else:
        return False
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("desktop notification failed: %s", type(e).__name__)
        return False
    return True


def run_in_thread(job: Callable[[], None]) -> None:
    threading.Thread(target=job, daemon=True).start()


def _describe(error: Exception) -> str:
    """A log-safe description: never the URL, which contains the topic."""
    if isinstance(error, urllib.error.HTTPError):
        return f"HTTP {error.code}"
    return type(error).__name__


class Notifier:
    def __init__(
        self,
        server: str,
        topic: str,
        *,
        bell: Callable[[], None],
        desktop: Callable[[Ping], bool] = desktop_notify,
        post: Callable[[urllib.request.Request], None] = urlopen_post,
        sleep: Callable[[float], None] = time.sleep,
        run: Callable[[Callable[[], None]], None] = run_in_thread,
    ) -> None:
        self._server = server
        self._topic = topic
        self._bell = bell
        self._desktop = desktop
        self._post = post
        self._sleep = sleep
        self._run = run

    def send(self, ping: Ping) -> None:
        self._run(lambda: self._deliver(ping))

    def _deliver(self, ping: Ping) -> None:
        try:
            if not self._desktop(ping):
                self._bell()
        except Exception as e:  # never let a notification take the timer down
            log.warning("desktop notification crashed: %s", type(e).__name__)
        if self._topic:
            self._publish(ping)

    def _publish(self, ping: Ping) -> None:
        request = build_ntfy_request(ping, self._server, self._topic)
        for attempt in (1, 2):
            try:
                self._post(request)
                return
            except Exception as e:  # offline, DNS, HTTP 5xx...: all non-fatal
                log.warning("ntfy publish failed (attempt %d of 2): %s", attempt, _describe(e))
                if attempt == 1:
                    self._sleep(RETRY_DELAY_S)
        log.warning("ntfy publish gave up")


class NullNotifier:
    """--no-notify."""

    def send(self, ping: Ping) -> None:
        pass
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: `76 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pomo/notify.py tests/test_notify.py
git commit -m "feat: desktop + ntfy pings with retry, RFC 2047 titles, topic never logged" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Screen text (pure view functions)

**Files:**
- Create: `src/pomo/ui/view.py`
- Test: `tests/test_view.py`

**Interfaces:**
- Consumes:
  - From Task 3: `PomodoroTimer`, `Phase`, `Transition`.
  - From Task 4: `Action`, `RuleKind`, `RuleBreak`, `SetCompleted`, `FocusCompleted` and `balance.PENALTIES`.
- Produces pure functions, with no Textual imports:
  - `clock_text(seconds) -> str` gives `MM:SS`, rounded up.
  - `phase_line(timer) -> str`
  - `progress_bar(timer, width) -> str`
  - `count_line(timer) -> str`
  - `next_line(timer) -> str`
  - `describe(event) -> str | None` gives the message-line text for an event.
  - `confirm_question(timer, action, cost) -> str`, for example `"Skip your break? The cats will be upset (−20)."`
- The minus sign in user-facing costs is `−` (U+2212), not `-`.

- [ ] **Step 1: Write the failing tests**

`tests/test_view.py`:

```python
import pytest

from pomo.clock import FakeClock
from pomo.game.events import FocusCompleted, RuleBreak, RuleKind, SetCompleted
from pomo.session import Action
from pomo.timer import Phase, PomodoroTimer, TimerSettings, Transition
from pomo.ui import view


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def timer(clock):
    return PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), clock)


@pytest.mark.parametrize("seconds, text", [(1500, "25:00"), (1499.2, "25:00"), (1499, "24:59"),
                                           (0.4, "00:01"), (0, "00:00"), (-3, "00:00"), (7200, "120:00")])
def test_clock_text(seconds, text):
    assert view.clock_text(seconds) == text


def test_phase_line_states(timer, clock):
    assert view.phase_line(timer) == "● FOCUS  (space to start)"
    timer.start()
    assert view.phase_line(timer) == "● FOCUS"
    clock.advance(1)
    timer.pause()
    assert view.phase_line(timer) == "● FOCUS  (paused)"


def test_progress_bar_fills_up(timer, clock):
    assert view.progress_bar(timer, 10) == "░" * 10
    timer.start()
    clock.advance(12.5 * 60)
    assert view.progress_bar(timer, 10) == "█" * 5 + "░" * 5


def test_count_and_next_lines(timer, clock):
    assert view.count_line(timer) == "pomodoro 1 of 4  ○○○○"
    assert view.next_line(timer) == "next: 5 min break"
    timer.start()
    clock.advance(25 * 60)
    timer.tick()
    assert view.count_line(timer) == "1 of 4 done  ●○○○"
    assert view.next_line(timer) == "next: 25 min focus"


def test_next_line_announces_the_long_break(clock):
    timer = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 1), clock)
    assert view.next_line(timer) == "next: 15 min long break"


def test_huge_sets_skip_the_dots(clock):
    timer = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 50), clock)
    assert view.count_line(timer) == "pomodoro 1 of 50"


def test_describe_rule_breaks_with_their_cost():
    assert view.describe(RuleBreak(RuleKind.SKIP_BREAK)) == "Break skipped. The cats will remember (−20)."


def test_describe_transitions_and_bonus():
    assert view.describe(Transition(Phase.FOCUS, Phase.SHORT_BREAK, True, 1500, 1)) == "Focus complete. Time for a break!"
    assert view.describe(Transition(Phase.SHORT_BREAK, Phase.FOCUS, True, 300, 1)) == "Break's over. Back to focus."
    assert view.describe(Transition(Phase.FOCUS, Phase.SHORT_BREAK, False, 1500, 0)) is None
    assert view.describe(SetCompleted()) == "A full set with no rules broken. Bonus!"
    assert view.describe(FocusCompleted(25)) is None


def test_confirm_question_names_the_cost(timer, clock):
    assert view.confirm_question(timer, Action.SKIP, RuleKind.ABANDON_FOCUS) == (
        "Skip this focus? The cats will be upset (−25)."
    )
    timer.start()
    clock.advance(25 * 60)
    timer.tick()
    assert view.confirm_question(timer, Action.SKIP, RuleKind.SKIP_BREAK) == (
        "Skip your break? The cats will be upset (−20)."
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_view.py -v`
Expected: FAIL during collection with `ImportError: cannot import name 'view' from 'pomo.ui'`

- [ ] **Step 3: Implement the view functions**

`src/pomo/ui/view.py`:

```python
"""Pure text for the timer screen. No Textual here, so it's trivial to test."""

from __future__ import annotations

import math

from pomo.game.balance import PENALTIES
from pomo.game.events import Event, RuleBreak, RuleKind, SetCompleted
from pomo.session import Action
from pomo.timer import Phase, PomodoroTimer, Transition

PHASE_NAMES = {Phase.FOCUS: "FOCUS", Phase.SHORT_BREAK: "SHORT BREAK", Phase.LONG_BREAK: "LONG BREAK"}
NEXT_NAMES = {Phase.FOCUS: "focus", Phase.SHORT_BREAK: "break", Phase.LONG_BREAK: "long break"}
RULE_TEXT = {
    RuleKind.ABANDON_FOCUS: "Focus abandoned.",
    RuleKind.SKIP_BREAK: "Break skipped.",
    RuleKind.LONG_PAUSE: "That pause ran long.",
}
MAX_DOTS = 12


def clock_text(seconds: float) -> str:
    """MM:SS, rounded up so it reads 25:00 until a whole second has passed and 00:00 only at the end."""
    total = math.ceil(max(0.0, seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def phase_line(timer: PomodoroTimer) -> str:
    if timer.running:
        state = ""
    elif timer.started:
        state = "  (paused)"
    else:
        state = "  (space to start)"
    return f"● {PHASE_NAMES[timer.phase]}{state}"


def progress_bar(timer: PomodoroTimer, width: int) -> str:
    done = 1.0 - timer.remaining() / timer.length if timer.length else 1.0
    filled = round(min(1.0, max(0.0, done)) * width)
    return "█" * filled + "░" * (width - filled)


def count_line(timer: PomodoroTimer) -> str:
    total = timer.settings.long_every
    done = timer.focus_in_set
    dots = "●" * done + "○" * (total - done) if total <= MAX_DOTS else ""
    if timer.phase is Phase.FOCUS:
        return f"pomodoro {done + 1} of {total}  {dots}".rstrip()
    return f"{done} of {total} done  {dots}".rstrip()


def next_line(timer: PomodoroTimer) -> str:
    upcoming = timer.next_phase()
    minutes = timer.base_length(upcoming) / 60
    return f"next: {minutes:g} min {NEXT_NAMES[upcoming]}"


def describe(event: Event) -> str | None:
    """The message-line text for an event, if it deserves one."""
    match event:
        case RuleBreak(kind=kind):
            return f"{RULE_TEXT[kind]} The cats will remember (−{PENALTIES[kind]})."
        case Transition(completed=True, ended=Phase.FOCUS):
            return "Focus complete. Time for a break!"
        case Transition(completed=True):
            return "Break's over. Back to focus."
        case SetCompleted():
            return "A full set with no rules broken. Bonus!"
    return None


def confirm_question(timer: PomodoroTimer, action: Action, cost: RuleKind) -> str:
    question = {
        Action.SKIP: "Skip your break?" if timer.phase.is_break else "Skip this focus?",
        Action.RESET: "Restart this focus from the top?",
        Action.QUIT: "Quit in the middle of a focus?",
    }[action]
    return f"{question} The cats will be upset (−{PENALTIES[cost]})."
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: `91 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pomo/ui/view.py tests/test_view.py
git commit -m "feat: pure view text for the timer screen" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Textual app with confirm dialogs

**Files:**
- Create: `src/pomo/ui/dialogs.py`, `src/pomo/ui/app.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes:
  - `Config` (Task 2), `Clock` and `FakeClock` (Task 1), `Session` and `Action` (Task 4).
  - `Notifies` and `ping_for` (Task 5), `view.*` (Task 6), `TimerSettings` and `Transition` (Task 3).
- Produces:
  - `ConfirmScreen(question: str)`, a `ModalScreen[bool]`: `y` answers True, `n` or `esc` answers False.
  - `TimerScreen` with `.show(session, message)`.
  - `PomoApp(config, clock, notifier, *, warnings: list[str] | None = None)`:
    - Attributes: `.config`, `.clock`, `.notifier` (assignable after construction, which Task 8 relies on), `.session`, `.main`, `.confirming`.
    - Methods: `.tick()`, `.handle(events)`, `.show_message(text)`, `.refresh_view()`.
  - Module constants: `TICK_S = 0.25` and `MESSAGE_TTL_S = 10.0`.
- Textual details that matter, all verified against Textual 8.2.8:
  - Override `get_default_screen()` and keep a reference to `TimerScreen` as `self.main`. `App.query_one` searches the **active** screen, which is the modal while a dialog is up, so updates must go through `self.main`.
  - Start the interval in `on_ready`, not `on_mount`. The default screen's widgets don't exist yet during the app's `on_mount`.
  - `check_action` returning `False` blocks bindings while a dialog is open, including the priority `q` / `ctrl+q` binding.
  - Key names: `space`, `plus`, `minus`. Textual's default `ctrl+c` is `help_quit`, which doesn't quit. We rebind `ctrl+q` so it goes through the same confirmation as `q`.

- [ ] **Step 1: Write the failing tests**

`tests/test_app.py`:

```python
from textual.widgets import Digits, Static

from pomo.clock import FakeClock
from pomo.config import Config
from pomo.timer import Phase
from pomo.ui.app import PomoApp
from pomo.ui.dialogs import ConfirmScreen

MIN = 60.0
SIZE = (100, 30)


class FakeNotifier:
    def __init__(self):
        self.pings = []

    def send(self, ping):
        self.pings.append(ping)


def make_app(**config):
    clock, notifier = FakeClock(), FakeNotifier()
    return PomoApp(Config(**config), clock, notifier), clock, notifier


def text(app, widget_id):
    return str(app.main.query_one(f"#{widget_id}", Static).render())


def clock_value(app):
    return app.main.query_one("#clock", Digits).value


async def test_shows_a_ready_focus():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        assert clock_value(app) == "25:00"
        assert "FOCUS" in text(app, "phase")
        assert text(app, "next") == "next: 5 min break"


async def test_space_starts_and_the_clock_counts_down():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(61)
        app.tick()
        assert clock_value(app) == "23:59"


async def test_finishing_focus_pings_once_and_starts_the_break():
    app, clock, notifier = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(25 * MIN)
        app.tick()
        assert app.session.timer.phase is Phase.SHORT_BREAK
        assert [p.title for p in notifier.pings] == ["🍅 Pomodoro done!"]
        assert "Time for a break" in text(app, "message")


async def test_a_sleep_wake_jump_sends_one_ping_not_a_flood():
    app, clock, notifier = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(3 * 60 * MIN)  # several phases went by
        app.tick()
        assert len(notifier.pings) == 1


async def test_plus_and_minus_adjust_the_clock():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("plus")
        assert clock_value(app) == "30:00"
        await pilot.press("minus", "minus")
        assert clock_value(app) == "20:00"


async def test_skipping_focus_asks_first_and_no_leaves_it_alone():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s")
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press("n")
        assert app.session.timer.phase is Phase.FOCUS
        assert not isinstance(app.screen, ConfirmScreen)


async def test_confirmed_skip_breaks_the_rule_without_a_ping():
    app, _, notifier = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s", "y")
        assert app.session.timer.phase is Phase.SHORT_BREAK
        assert "(−25)" in text(app, "message")
        assert notifier.pings == []


async def test_resetting_an_unstarted_focus_does_not_ask():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("r")
        assert not isinstance(app.screen, ConfirmScreen)


async def test_keys_are_ignored_while_the_dialog_is_open():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s")
        await pilot.press("space", "s", "r", "plus", "q")
        assert len(app.screen_stack) == 2  # no stacked dialogs
        assert not app.session.timer.running
        assert app.session.timer.length == 25 * MIN
        assert app.is_running


async def test_a_stale_yes_does_not_skip_the_next_phase():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space", "s")  # asked while in focus...
        clock.advance(25 * MIN)
        app.tick()  # ...focus finished on its own meanwhile
        await pilot.press("y")
        assert app.session.timer.phase is Phase.SHORT_BREAK  # the break was not skipped
        assert "phase changed" in text(app, "message")


async def test_quit_before_starting_just_quits():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running


async def test_quit_mid_focus_asks_first():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(1)
        await pilot.press("q")
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press("y")
        await pilot.pause()
        assert not app.is_running


async def test_messages_fade_after_ten_seconds():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s", "y")
        assert text(app, "message")
        clock.advance(11)
        app.tick()
        assert text(app, "message") == ""


async def test_startup_warnings_are_shown():
    clock = FakeClock()
    app = PomoApp(Config(), clock, FakeNotifier(), warnings=["chmod 600 your config"])
    async with app.run_test(size=SIZE):
        assert text(app, "message") == "chmod 600 your config"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_app.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.ui.app'`

- [ ] **Step 3: Implement the confirm dialog**

`src/pomo/ui/dialogs.py`:

```python
"""Yes/no dialog shown before any rule-breaking action (spec §3.2)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label


class ConfirmScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmScreen { align: center middle; }
    #dialog { width: 54; height: auto; border: thick $warning; padding: 1 2; background: $surface; }
    #hint { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [
        Binding("y", "answer(True)", "Yes"),
        Binding("n,escape", "answer(False)", "No"),
    ]

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.question, id="question")
            yield Label("y  yes     n / esc  no", id="hint")

    def action_answer(self, ok: bool) -> None:
        self.dismiss(ok)
```

- [ ] **Step 4: Implement the app**

`src/pomo/ui/app.py`:

```python
"""The Textual app for milestone 1: a plain timer screen (the cats arrive in milestone 2)."""

from __future__ import annotations

from collections.abc import Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Digits, Footer, Static

from pomo.clock import Clock
from pomo.config import Config
from pomo.game.events import Event
from pomo.notify import Notifies, ping_for
from pomo.session import Action, Session
from pomo.timer import TimerSettings, Transition
from pomo.ui import view
from pomo.ui.dialogs import ConfirmScreen

TICK_S = 0.25
MESSAGE_TTL_S = 10.0
BAR_WIDTH = 38
BLOCKED_WHILE_CONFIRMING = {"toggle", "adjust", "skip", "reset", "request_quit"}


class TimerScreen(Screen):
    DEFAULT_CSS = """
    TimerScreen { align: center middle; }
    #panel { width: 46; height: auto; border: round $primary; padding: 1 2; }
    #phase { text-style: bold; color: $error; }
    #clock { width: auto; margin: 1 0; }
    #next { color: $text-muted; }
    #message { color: $warning; height: 2; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="panel"):
            yield Static(id="phase")
            yield Digits("25:00", id="clock")
            yield Static(id="progress")
            yield Static(id="count")
            yield Static(id="next")
            yield Static(id="message")
        yield Footer()

    def show(self, session: Session, message: str) -> None:
        timer = session.timer
        self.query_one("#phase", Static).update(view.phase_line(timer))
        self.query_one("#clock", Digits).update(view.clock_text(timer.remaining()))
        self.query_one("#progress", Static).update(view.progress_bar(timer, BAR_WIDTH))
        self.query_one("#count", Static).update(view.count_line(timer))
        self.query_one("#next", Static).update(view.next_line(timer))
        self.query_one("#message", Static).update(message)


class PomoApp(App[None]):
    TITLE = "pomo"
    BINDINGS = [
        Binding("space", "toggle", "Start/Pause"),
        Binding("s", "skip", "Skip"),
        Binding("r", "reset", "Reset"),
        Binding("plus", "adjust(5)", "+5 min"),
        Binding("minus", "adjust(-5)", "-5 min"),
        Binding("q,ctrl+q", "request_quit", "Quit", key_display="q", priority=True),
    ]

    def __init__(self, config: Config, clock: Clock, notifier: Notifies, *, warnings: list[str] | None = None) -> None:
        super().__init__()
        self.config = config
        self.clock = clock
        self.notifier = notifier
        self.session = Session(
            TimerSettings.from_minutes(config.focus, config.short_break, config.long_break, config.long_every),
            clock,
        )
        self.main = TimerScreen()
        self.confirming = False
        self._warnings = list(warnings or [])
        self._message = ""
        self._message_at = 0.0

    def get_default_screen(self) -> Screen:
        return self.main

    def on_ready(self) -> None:
        # on_ready, not on_mount: the timer screen's widgets exist by now.
        for warning in self._warnings:
            self.show_message(warning)
        self.refresh_view()
        self.set_interval(TICK_S, self.tick)

    def tick(self) -> None:
        self.handle(self.session.tick())
        self.refresh_view()

    def handle(self, events: list[Event]) -> None:
        finished = [e for e in events if isinstance(e, Transition) and e.completed]
        if finished:
            # A sleep/wake jump can finish several phases in one tick: ping once, for the latest.
            self.notifier.send(ping_for(finished[-1], self.config))
        for event in events:
            text = view.describe(event)
            if text:
                self.show_message(text)

    def show_message(self, text: str) -> None:
        self._message = text
        self._message_at = self.clock.now()

    def refresh_view(self) -> None:
        if self._message and self.clock.now() - self._message_at > MESSAGE_TTL_S:
            self._message = ""
        self.main.show(self.session, self._message)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        return not (self.confirming and action in BLOCKED_WHILE_CONFIRMING)

    def action_toggle(self) -> None:
        self.session.toggle()
        self.refresh_view()

    def action_adjust(self, minutes: int) -> None:
        self.session.adjust(minutes)
        self.refresh_view()

    def action_skip(self) -> None:
        self._guarded(Action.SKIP, lambda: self._apply(self.session.skip()))

    def action_reset(self) -> None:
        self._guarded(Action.RESET, lambda: self._apply(self.session.reset()))

    def action_request_quit(self) -> None:
        self._guarded(Action.QUIT, self._quit)

    def _apply(self, events: list[Event]) -> None:
        self.handle(events)
        self.refresh_view()

    def _quit(self) -> None:
        self.handle(self.session.quit())
        self.exit()

    def _guarded(self, action: Action, perform: Callable[[], None]) -> None:
        """Ask first when the action breaks a rule. Ignore a stale 'yes' if the phase moved on meanwhile."""
        cost = self.session.rule_cost(action)
        if cost is None:
            perform()
            return
        asked_in = self.session.timer.phase
        self.confirming = True

        def answered(ok: bool | None) -> None:
            self.confirming = False
            if ok and self.session.timer.phase is asked_in:
                perform()
            elif ok:
                self.show_message("The phase changed while you were deciding, so nothing was skipped.")
                self.refresh_view()

        self.push_screen(ConfirmScreen(view.confirm_question(self.session.timer, action, cost)), answered)
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run pytest -v`
Expected: `105 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/ui/dialogs.py src/pomo/ui/app.py tests/test_app.py
git commit -m "feat: Textual timer screen with confirm-before-rule-break dialogs" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: CLI, logging, README and a real-terminal smoke test

**Files:**
- Create: `src/pomo/cli.py`, `src/pomo/__main__.py`
- Modify: `README.md` (replace the whole Task 1 stub)
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes:
  - From Task 2: `load_config`, `with_overrides`, `permission_warning`, `ConfigError`, `config_path`, `log_path`.
  - From Task 5: `Notifier` and `NullNotifier`.
  - From Task 7: `PomoApp`.
  - From Task 1: `RealClock`.
- Produces:
  - `main(argv: list[str] | None = None) -> int`: 0 on a normal exit, 2 on a config error.
  - `build_parser()`, `positive_int(text)`, `setup_logging(path)`.
  - Flags: `--focus MIN`, `--short-break MIN`, `--long-break MIN`, `--long-every N`, `--no-notify`, `--config PATH`, `--version`.
  - There is deliberately no `--topic` flag.

- [ ] **Step 1: Write the failing tests**

`tests/test_cli.py`:

```python
import pytest

from pomo import cli
from pomo.notify import NullNotifier, Notifier
from pomo.ui.app import PomoApp


@pytest.fixture
def launched(monkeypatch):
    """Stop main() before it takes over the terminal and hand back the app it built."""
    apps = []
    monkeypatch.setattr(PomoApp, "run", lambda self: apps.append(self))
    return apps


def test_help_documents_every_flag(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--help"])
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    for flag in ["--focus", "--short-break", "--long-break", "--long-every", "--no-notify", "--config", "--version"]:
        assert flag in out
    assert "config.toml" in out and "topic" in out


def test_topic_is_not_a_flag(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--topic", "abc"])
    assert "unrecognized arguments" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["0", "-5", "ten"])
def test_bad_durations_are_rejected_by_argparse(value, capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--focus", value])
    assert exit_info.value.code == 2


def test_broken_config_prints_one_line_and_exits_2(tmp_path, capsys, launched):
    path = tmp_path / "config.toml"
    path.write_text("focus = = 1")
    assert cli.main(["--config", str(path)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("pomo: ") and "Traceback" not in err
    assert launched == []


def test_flags_override_the_config_file(tmp_path, launched):
    path = tmp_path / "config.toml"
    path.write_text("focus = 30\nshort_break = 10\n")
    assert cli.main(["--config", str(path), "--focus", "50"]) == 0
    (app,) = launched
    assert (app.config.focus, app.config.short_break) == (50, 10)


def test_notifications_are_on_by_default_and_off_with_no_notify(launched):
    cli.main([])
    cli.main(["--no-notify"])
    assert isinstance(launched[0].notifier, Notifier)
    assert isinstance(launched[1].notifier, NullNotifier)


def test_permission_warning_reaches_the_app(tmp_path, launched):
    path = tmp_path / "config.toml"
    path.write_text('topic = "s3cret"')
    path.chmod(0o644)
    cli.main(["--config", str(path)])
    assert any("chmod 600" in w for w in launched[0]._warnings)


def test_logs_go_to_the_state_dir(tmp_path, launched):
    cli.main([])
    assert (tmp_path / "state" / "pomo").is_dir()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_cli.py -v`
Expected: FAIL during collection with `ImportError: cannot import name 'cli' from 'pomo'`

- [ ] **Step 3: Implement the CLI**

`src/pomo/cli.py`:

```python
"""`pomo` command line: flags → config → app."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from pomo import __version__
from pomo.clock import RealClock
from pomo.config import ConfigError, load_config, permission_warning, with_overrides
from pomo.notify import Notifier, NullNotifier
from pomo.paths import config_path, log_path
from pomo.ui.app import PomoApp

DESCRIPTION = (
    "A pomodoro timer for your terminal, with cats. "
    "Pings your desktop, and your phone via ntfy, when each phase ends."
)
EPILOG = """\
keys:
  space  start / pause        s  skip phase        r  reset phase
  + / -  add / remove 5 min   q  quit

config file (all keys optional), default ~/.config/pomo/config.toml:
  ntfy_server = "https://ntfy.sh"
  topic = ""          # your ntfy topic; empty disables phone pings
  focus = 25          # minutes
  short_break = 5
  long_break = 15
  long_every = 4      # a long break after this many focus sessions

The ntfy topic is a secret: it is read only from the config file (chmod 600 it),
never from a flag, and never logged.
"""


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pomo",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--focus", type=positive_int, metavar="MIN", help="focus length in minutes (default 25)")
    parser.add_argument("--short-break", type=positive_int, metavar="MIN", help="short break in minutes (default 5)")
    parser.add_argument("--long-break", type=positive_int, metavar="MIN", help="long break in minutes (default 15)")
    parser.add_argument(
        "--long-every", type=positive_int, metavar="N", help="long break after every N focus sessions (default 4)"
    )
    parser.add_argument("--no-notify", action="store_true", help="no desktop or phone notifications")
    parser.add_argument("--config", type=Path, metavar="PATH", help="config file to use instead of the default")
    parser.add_argument("--version", action="version", version=f"pomo {__version__}")
    return parser


def setup_logging(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = args.config or config_path()
    try:
        cfg = with_overrides(
            load_config(path),
            focus=args.focus,
            short_break=args.short_break,
            long_break=args.long_break,
            long_every=args.long_every,
        )
    except ConfigError as e:
        print(f"pomo: {e}", file=sys.stderr)
        return 2

    setup_logging(log_path())
    warnings = [w for w in [permission_warning(path, cfg)] if w]
    app = PomoApp(cfg, RealClock(), NullNotifier(), warnings=warnings)
    if not args.no_notify:
        # The bell must ring on Textual's thread; notifications arrive from a worker thread.
        app.notifier = Notifier(cfg.ntfy_server, cfg.topic, bell=lambda: app.call_from_thread(app.bell))
    app.run()
    return 0
```

`src/pomo/__main__.py`:

```python
import sys

from pomo.cli import main

sys.exit(main())
```

- [ ] **Step 4: Replace the README**

`README.md`:

````markdown
# pomo

A pomodoro timer for your terminal, with a room full of cats. (The cats move in with milestone 2.)

## Install

```bash
uv tool install .    # run from this directory; puts `pomo` on your PATH
```

## Use

```bash
pomo                               # 25 min focus, 5 min breaks, 15 min long break every 4
pomo --focus 50 --short-break 10
pomo --help                        # every flag, key and config option
```

Keys: `space` start/pause · `s` skip · `r` reset · `+`/`-` 5 min · `q` quit

Skipping or abandoning a focus, skipping a break, or pausing a focus for more than
3 minutes breaks a rule. `pomo` asks before letting you, because the cats will remember.

## Phone pings (ntfy)

Put your topic in `~/.config/pomo/config.toml` and keep the file private:

```toml
topic = "your-secret-topic"
```

```bash
chmod 600 ~/.config/pomo/config.toml
```

## Develop

```bash
uv sync
uv run pytest
```
````

- [ ] **Step 5: Run the whole suite**

Run: `uv run pytest -v`
Expected: `115 passed`

- [ ] **Step 6: Check the help text**

Run: `uv run pomo --help`
Expected: usage that lists `--focus`, `--short-break`, `--long-break`, `--long-every`, `--no-notify`, `--config` and `--version`, followed by the key list and the config file example. `uv run pomo --version` prints `pomo 0.1.0`.

- [ ] **Step 7: Smoke test in real terminals**

Do this in **both iTerm2 and Ghostty**. Use a throwaway config so your real one isn't touched:

```bash
printf 'focus = 1\nshort_break = 1\nlong_break = 1\nlong_every = 2\n' > /tmp/pomo-smoke.toml
uv run pomo --config /tmp/pomo-smoke.toml
```

Check each of these:
- `space` starts the countdown and the progress bar fills.
- After 1 min a macOS notification "🍅 Pomodoro done!" appears and the phase changes to SHORT BREAK on its own. If no banner appears, allow notifications for "Script Editor" in System Settings → Notifications, since `osascript` notifications show under that name.
- Pressing `s` during the break asks "Skip your break? The cats will be upset (−20)." `n` keeps the break. `s` then `y` skips it, and the message line shows the cost.
- `+` and `-` change the clock by 5 minutes, and `-` stops at 05:00.
- Resizing the window redraws cleanly.
- After two focus sessions the long break starts.
- `q` mid-focus asks first. `q` during a break quits straight away.

Optional ntfy check: add `topic = "<your topic>"` to `/tmp/pomo-smoke.toml`, `chmod 600` it, run the app again and confirm the phone gets the ping. Then `rm /tmp/pomo-smoke.toml`.

- [ ] **Step 8: Commit**

```bash
git add src/pomo/cli.py src/pomo/__main__.py README.md tests/test_cli.py
git commit -m "feat: pomo CLI, logging and README" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
