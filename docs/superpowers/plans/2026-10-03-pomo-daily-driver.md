# pomo Daily-Driver Round Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `pomo` something you can run all day as your real pomodoro timer:
- **Saving:** it remembers Mango and your place in the set across quits and restarts, and charges a focus left without the quit dialog on the next launch.
- **Setup helpers:** `pomo --init` writes a private config with an ntfy topic, and `pomo --test-ping` checks desktop and phone notifications right now.
- **The too-small screen:** it degrades gracefully below 100×30.
- **The cat line:** pings end with a line about Mango.
- **The six fixes** milestone 4 deferred.

**Architecture:**
- **Saving:**
  - The pure core gains a `SessionState` snapshot with `Session.state()` and `Session.restore(state, closed_for)` (the restore rules live here and are tested with `FakeClock`), plus `PomodoroTimer.restore` and `World.focus_total`/`World.place`.
  - A new `persist.py` turns the session and the world into versioned JSON and back. It validates and clamps what it reads, writes atomically, and backs bad saves up.
  - A new `lock.py` keeps it to one `pomo` at a time.
- **The app** gains an optional save path and a wall clock. It saves on every phase change, every 30 s and on the way out, and restores at startup. `cli.py` takes the lock, loads the save and wires it in.
- **The setup helpers** live in `config.py` (the starter file) and `notify.py` (the test ping).
- **The too-small screen and the idle key hints** live in `scene.py`.
- **The cat line** is a pure function in `ui/view.py`.

**Tech Stack:** Python ≥ 3.12, Textual 8.2, pytest and pytest-asyncio. Standard library only for saving (`json`, `tempfile`, `os.replace`, `fcntl.flock`, `secrets`). No new dependencies.

**Spec:**
- The main spec: `docs/superpowers/specs/2026-09-29-pomo-cats-design.md`.
- This round's addendum, which wins where they differ: `docs/superpowers/specs/2026-10-03-pomo-daily-driver-design.md`. The addendum covers:
  - §2 saving.
  - §3 setup helpers.
  - §4 the too-small screen.
  - §5 the cat line.
  - §6 the six fixes.
  - §7 testing.

This round builds on milestone 4, which is on `main` (506 tests).

## Global Constraints

- **Everything from the milestone 1–4 plans still holds:**
  - A pure core with an injected `Clock` and `random.Random`.
  - `game/*` imports neither Textual nor `pomo.render`.
  - Colours live only in `theme.py`.
  - The panel is exactly 30 columns.
  - 8 fps with row-diff repaints.
  - `dt` is capped at 1 s.
- **The ntfy topic is a secret:**
  - It is never logged and never a flag.
  - It never appears in anything printed or shown: `--init` and `--test-ping` included.
  - It is kept out of `repr`.
- **The save:**
  - It lives at `$XDG_STATE_HOME/pomo/save.json` (default `~/.local/state/pomo/save.json`) and is version 1 JSON.
  - It's written to a temporary file in the same directory, flushed, then `os.replace`d over the old one.
  - It saves on every phase change, every 30 s and on the way out.
- **Restores:**
  - The timer always comes back ready, never running.
  - Phase lengths come from the current config.
  - A focus left mid-way without the quit dialog costs the abandon penalty (−25, scaled by trait) on the next launch, with *"Mango remembers you left."*
  - A break whose time ran out while closed (wall clock) comes back as a ready focus, with no reward and no penalty.
  - `--idle` wins over the save.
- **Bad saves** (not JSON, an unknown version, a missing or wrong-typed field, an unknown coat, trait or surface, a non-finite number) are renamed to `save.json.bak-YYYYmmdd-HHMMSS`. `pomo` starts fresh and says so. Out-of-range moods and needs are clamped to 0–100.
- **The lock:** an exclusive `flock` on `$XDG_STATE_HOME/pomo/pomo.lock`. A second `pomo` prints *"pomo is already running in another window."* and exits 1. `--help`, `--version`, `--gallery`, `--init` and `--test-ping` don't take it.
- **The too-small screen:** a terminal narrower than 100 or shorter than 30 shows *"The cats need more room."*, *"Make the window at least 100×30 (it's W×H now)."*, the timer as text, and a sad loaf in the first cat's coat when it fits. The toolbar is hidden and the mouse tools are off.
- Tests never touch the real `~/.config` or `~/.local/state`. `tests/conftest.py` already redirects both `XDG_*` variables.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

**Design decisions this plan makes where the addendum is silent:**
- **What's not saved:** cats' litter timers and the yarn ball. Timers re-roll on launch, and the ball goes away.
- **A cat mid-jump or out through the door** is saved on the surface it's on (the takeoff surface, or the floor by the door), at its current column.
- **`focus_in_set` clamping:** it's clamped to `long_every − 1`, except on a long break, where `long_every` itself is right ("4 of 4 done").
- **A save that can't be written** (e.g. a full disk) is logged with only the error's type. The message line shows the OS's reason (`strerror`), which never contains a path.
- **`--test-ping`'s exit code:** a channel that wasn't tried (no topic) doesn't make it fail. One that was tried and failed does.
- **The "pomo remembers" message** names the cat when there's one (*"Mango remembers you left."*), and says *"The cats remember you left."* when there are several.
- **The too-small screen** is chosen from the terminal size (`App.size`), not the canvas, because the toolbar hides then. `scene.draw` takes it as `terminal=`, defaulting to the canvas plus 2 rows.
- **The smallest real stage is 28 rows** (100×30, less the message line and the toolbar). The scene test that used a 27-row stage moves to 28.
- **Leaving the window:** the stage's top row and last column count as outside the room (`room_point(col, row, columns)`), and so does `AppBlur`.
- **Redraws on mouse moves** are skipped when the room point hasn't changed, or when no tool is held.

## Review Focus

1. **A crash or a closed window at the worst moment.** For example, mid-write of a save, or mid-focus without the dialog. The old save is never truncated, the next launch charges the focus once (not twice after a confirmed quit), and nothing is half-restored. Tests:
   - Task 2 `test_a_write_that_fails_leaves_the_old_save_alone`.
   - Task 3 `test_closing_mid_focus_without_the_dialog_saves_the_focus_as_still_owed`.
   - Task 3 `test_a_confirmed_quit_mid_focus_is_saved_as_paid_for`.
2. **A hand-edited, truncated or future-version save.** It's set aside with a message, and `pomo` starts fresh rather than crashing. Tests:
   - Task 2 `test_a_save_that_cannot_be_used_says_why` (17 cases).
   - Task 2 `test_files_that_are_not_saves`.
   - Task 4 `test_an_unreadable_save_is_kept_aside_and_pomo_starts_fresh`.
3. **Changing the config between runs** (a shorter `long_every`, a different `--focus`). The restored count stays inside the set, and the phase uses today's lengths. Tests: Task 1 `test_restore_keeps_the_count_inside_todays_set` and `test_restore_picks_up_a_phase_ready_at_todays_length`.
4. **Two `pomo` windows.** The second is turned away and the first keeps its lock. The lock goes when the process ends. Tests: Task 4 `test_a_second_pomo_is_turned_away` and `test_the_lock_is_let_go_when_pomo_ends`.
5. **The topic leaking through the new commands.** `--init` and `--test-ping` output never contains it, success or failure. Tests:
   - Task 5 `test_init_writes_a_private_starter_and_says_what_next_without_the_topic`.
   - Task 5 `test_a_failed_phone_ping_says_why_without_the_topic`.
   - Task 5 `test_test_ping_reports_each_channel_and_its_result`.

## File Map

| File | Responsibility | Task |
|---|---|---|
| `src/pomo/clock.py` (edit) | `WallClock` | 1 |
| `src/pomo/timer.py` (edit) | `PomodoroTimer.restore` | 1 |
| `src/pomo/session.py` (replace) | `SessionState`; `Session.state`, `Session.restore`; `quit` resets a paid-for focus | 1 |
| `src/pomo/game/world.py` (edits) | `focus_total` (T1), `place` (T2), the roster's coat (T6), the hand re-checks what it's on (T8) | 1, 2, 6, 8 |
| `src/pomo/persist.py` | `snapshot`, `write`, `load`, `read`, `BadSave`, `Saved`, `SavedCat`, `build_world`, `back_up` | 2 |
| `src/pomo/ui/app.py` (edits) | Save/restore (T3), the too-small screen (T6), the cat line (T7), pointer and mode fixes (T8) | 3, 6, 7, 8 |
| `src/pomo/ui/view.py` (edits) | `remembers` (T3), `cat_line` (T7) | 3, 7 |
| `src/pomo/lock.py` | `acquire`, `Lock` | 4 |
| `src/pomo/paths.py` (edit) | `save_path`, `lock_path` | 4 |
| `src/pomo/cli.py` (replace twice) | The lock and the save (T4); `--init`, `--test-ping` (T5) | 4, 5 |
| `src/pomo/config.py` (replace) | `STARTER`, `new_topic`, `write_starter`, `display_path` | 5 |
| `src/pomo/notify.py` (edits) | `send_test_ping` (T5); `ping_for(…, cat_line)` (T7) | 5, 7 |
| `README.md` (replace) | Install editable, saving, phone pings in 3 steps | 5 |
| `src/pomo/render/scene.py` (edits) | The too-small screen (T6); idle hints, `room_point` edges (T8) | 6, 8 |
| `src/pomo/ui/toolbar.py` (replace) | Two mode buttons; the bar colour from the theme | 8 |
| `src/pomo/render/theme.py` (edits) | `BAR_BG`, `css()` | 8 |

---

### Task 1: Restoring a session

**Files:**
- Modify: `src/pomo/clock.py`, `src/pomo/timer.py`, `src/pomo/game/world.py`
- Replace: `src/pomo/session.py`
- Test: `tests/test_clock.py`, `tests/test_timer.py`, `tests/test_session.py`, `tests/test_world.py`

**Interfaces:**
- Consumes: milestone 4's `Session` (with `idle`, `_break_left`, `_idle_since`), `PomodoroTimer`, `World`.
- Produces:
  - `WallClock().now() -> float`: `time.time()`.
  - `PomodoroTimer.restore(phase: Phase, focus_in_set: int) -> None`: the timer is left ready.
  - `SessionState(phase, focus_in_set, set_clean, focus_in_progress, break_left: float | None, idle)`, frozen.
  - `Session.state() -> SessionState`.
  - `Session.restore(state, closed_for: float) -> list[Event]`.
  - `Session.quit()` resets a started focus after charging it.
  - `World.focus_total: int`, incremented on `FocusCompleted`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_clock.py`:

Replace:

```python
from pomo.clock import FakeClock, RealClock
```

with:

```python
from pomo.clock import FakeClock, RealClock, WallClock
```

and append to the end of `tests/test_clock.py`:

```python
def test_the_wall_clock_is_seconds_since_the_epoch():
    import time
    before = time.time()
    assert before <= WallClock().now() <= time.time()
```

Append to the end of `tests/test_timer.py`:

```python
def test_restore_picks_up_a_phase_ready_at_todays_length(timer):
    timer.restore(Phase.SHORT_BREAK, 2)
    assert (timer.phase, timer.focus_in_set, timer.started, timer.remaining()) == (Phase.SHORT_BREAK, 2, False, 5 * MIN)


@pytest.mark.parametrize("phase, saved, kept", [
    (Phase.FOCUS, 9, 3), (Phase.SHORT_BREAK, 9, 3), (Phase.LONG_BREAK, 9, 4), (Phase.FOCUS, -2, 0),
])
def test_restore_keeps_the_count_inside_todays_set(timer, phase, saved, kept):
    timer.restore(phase, saved)  # long_every is 4: a long break shows 4 of 4, anything else at most 3
    assert timer.focus_in_set == kept
```

In `tests/test_session.py`:

Replace:

```python
from pomo.session import Action, Session
```

with:

```python
from pomo.session import Action, Session, SessionState
```

Replace:

```python
MIN = 60.0
```

with:

```python
MIN = 60.0
HOUR = 3600.0
```

and append to the end of `tests/test_session.py`:

```python
# --- saving and restoring (daily-driver addendum §2) -----------------------------

def restored(state: SessionState, closed_for: float = 60.0, clock=None) -> tuple[Session, list]:
    fresh = Session(TimerSettings.from_minutes(25, 5, 15, 4), clock or FakeClock())
    return fresh, fresh.restore(state, closed_for)


def test_the_state_of_a_ready_focus(session):
    assert session.state() == SessionState(Phase.FOCUS, 0, True, False, None, False)


def test_a_started_or_paused_focus_is_in_progress(session, clock):
    session.toggle()
    clock.advance(MIN)
    assert session.state().focus_in_progress
    session.toggle()  # paused
    assert session.state().focus_in_progress


def test_a_break_saves_what_is_left_of_it(session, clock):
    finish(session, clock)
    clock.advance(2 * MIN)
    state = session.state()
    assert (state.phase, state.focus_in_set, state.break_left) == (Phase.SHORT_BREAK, 1, 3 * MIN)


def test_idle_on_a_break_keeps_counting_the_break_down(session, clock):
    finish(session, clock)
    clock.advance(1 * MIN)
    session.enter_idle()
    clock.advance(3 * MIN)
    assert session.state().break_left == 1 * MIN
    clock.advance(5 * MIN)
    assert session.state().break_left == 0


def test_a_quit_mid_focus_is_paid_for_once_and_resets_the_focus(session, clock):
    session.toggle()
    clock.advance(5 * MIN)
    assert rule_breaks(session.quit()) == [RuleKind.ABANDON_FOCUS]
    assert not session.state().focus_in_progress


def test_a_quit_on_a_break_leaves_the_break_alone(session, clock):
    finish(session, clock)
    clock.advance(1 * MIN)
    assert session.quit() == []
    assert session.timer.running


def test_restoring_a_ready_focus_changes_nothing(session):
    fresh, events = restored(SessionState(Phase.FOCUS, 2, True, False, None, False))
    assert events == []
    assert (fresh.timer.phase, fresh.timer.focus_in_set, fresh.timer.started) == (Phase.FOCUS, 2, False)


def test_a_focus_left_without_the_dialog_is_abandoned_on_the_next_launch():
    fresh, events = restored(SessionState(Phase.FOCUS, 1, True, True, None, False))
    assert rule_breaks(events) == [RuleKind.ABANDON_FOCUS]
    assert (fresh.timer.phase, fresh.timer.started, fresh.timer.remaining()) == (Phase.FOCUS, False, 25 * MIN)


def test_an_abandoned_focus_on_relaunch_spoils_the_set():
    clock = FakeClock()
    fresh, _ = restored(SessionState(Phase.FOCUS, 3, True, True, None, False), clock=clock)
    fresh.toggle()
    clock.advance(25 * MIN)
    assert SetCompleted() not in fresh.tick()


def test_a_break_that_ran_out_while_closed_comes_back_as_a_ready_focus():
    fresh, events = restored(SessionState(Phase.SHORT_BREAK, 1, True, False, 3 * MIN, False), closed_for=3 * MIN)
    assert [e for e in events if isinstance(e, (BreakCompleted, RuleBreak))] == []
    assert (fresh.timer.phase, fresh.timer.started, fresh.timer.focus_in_set) == (Phase.FOCUS, False, 1)


def test_a_long_break_that_ran_out_starts_a_new_set():
    fresh, _ = restored(SessionState(Phase.LONG_BREAK, 4, False, False, 10 * MIN, False), closed_for=HOUR)
    assert (fresh.timer.phase, fresh.timer.focus_in_set) == (Phase.FOCUS, 0)


def test_a_break_with_time_left_comes_back_ready():
    fresh, events = restored(SessionState(Phase.SHORT_BREAK, 1, True, False, 3 * MIN, False), closed_for=MIN)
    assert events == []
    assert (fresh.timer.phase, fresh.timer.started, fresh.timer.remaining()) == (Phase.SHORT_BREAK, False, 5 * MIN)


def test_idle_comes_back_idle_with_the_break_clock_still_running():
    clock = FakeClock()
    fresh, events = restored(SessionState(Phase.SHORT_BREAK, 1, True, False, 3 * MIN, True), closed_for=MIN,
                             clock=clock)
    assert events == [] and fresh.idle
    clock.advance(2 * MIN)  # the last two minutes of the break go by in Idle
    fresh.leave_idle()
    assert fresh.timer.phase is Phase.FOCUS


def test_restoring_never_starts_the_timer():
    for state in [SessionState(Phase.FOCUS, 0, True, True, None, False),
                  SessionState(Phase.SHORT_BREAK, 1, True, False, HOUR, False)]:
        fresh, _ = restored(state)
        assert not fresh.timer.running
```

Append to the end of `tests/test_world.py`:

```python
def test_the_world_counts_every_focus_ever_completed():
    from pomo.game.events import BreakCompleted, FocusCompleted
    world = world_with("Mango")
    world.apply([FocusCompleted(25), BreakCompleted(Phase.SHORT_BREAK), FocusCompleted(10)])
    assert world.focus_total == 2
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_clock.py tests/test_timer.py tests/test_session.py tests/test_world.py -q`
Expected: FAIL during collection with `ImportError: cannot import name 'WallClock' from 'pomo.clock'` (and `'SessionState'` from `pomo.session`)

- [ ] **Step 3: The wall clock and the timer**

In `src/pomo/clock.py`:

Replace:

```python
class FakeClock:
```

with:

```python
class WallClock:
    """Seconds since the epoch: comparable across runs, unlike the monotonic clock (for saves)."""

    def now(self) -> float:
        return time.time()


class FakeClock:
```

In `src/pomo/timer.py`, in `PomodoroTimer`:

Replace:

```python
    def adjust(self, minutes: int) -> None:
```

with:

```python
    def restore(self, phase: Phase, focus_in_set: int) -> None:
        """Pick up a saved session: this phase, ready to start, at today's lengths."""
        top = self._settings.long_every if phase is Phase.LONG_BREAK else self._settings.long_every - 1
        self._phase = phase
        self._focus_in_set = min(max(0, focus_in_set), top)
        self.reset()

    def adjust(self, minutes: int) -> None:
```

- [ ] **Step 4: The session's state and restore**

Replace all of `src/pomo/session.py` with:

```python
"""The timer plus the rules: user actions in, events out (spec §3.1–§3.2).

Idle mode (spec §2, §3.1) lives here too: going idle resets the phase, which costs
what a reset costs, and puts the timer away until you come back to it. A break keeps
its clock while you're idle: idle past its end and you come back to a ready focus.
"""

from __future__ import annotations

from dataclasses import dataclass
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
    IDLE = "idle"


@dataclass(frozen=True)
class SessionState:
    """What a save needs to bring the session back (addendum §2)."""

    phase: Phase
    focus_in_set: int
    set_clean: bool
    focus_in_progress: bool  # a focus had started and hadn't been paid for
    break_left: float | None  # seconds left on the break you were on, if any
    idle: bool


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
        self.idle = False
        self._idle_since = 0.0
        self._break_left: float | None = None  # what was left of the break you went idle on

    def rule_cost(self, action: Action) -> RuleKind | None:
        """Which rule this action would break right now, if any."""
        if self.timer.phase is Phase.FOCUS:
            if action is Action.SKIP or self.timer.started:
                return RuleKind.ABANDON_FOCUS
            return None
        return RuleKind.SKIP_BREAK if action is Action.SKIP else None

    def toggle(self) -> None:
        if self.idle:
            return
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
        if not self.idle:
            self.timer.adjust(minutes)

    def tick(self) -> list[Event]:
        events: list[Event] = []
        for transition in self.timer.tick():
            events += self._on_transition(transition)
        return events + self._check_pause()

    def skip(self) -> list[Event]:
        if self.idle:
            return []
        events = self._break_rule(self.rule_cost(Action.SKIP))
        return events + self._on_transition(self.timer.skip())

    def reset(self) -> list[Event]:
        if self.idle:
            return []
        events = self._break_rule(self.rule_cost(Action.RESET))
        self.timer.reset()
        self._reset_pause_tracking()
        return events

    def quit(self) -> list[Event]:
        """Leaving. A focus abandoned here is paid for now and reset, so the last save won't charge it again."""
        events = self._break_rule(self.rule_cost(Action.QUIT))
        if events:
            self.timer.reset()
        return events

    def enter_idle(self) -> list[Event]:
        """Reset the phase and put the timer away. Mid-focus, that's abandoning it."""
        if self.idle:
            return []
        break_left = self.timer.remaining() if self.timer.phase.is_break else None
        events = self.reset()
        self.idle = True
        self._idle_since, self._break_left = self._clock.now(), break_left
        return events

    def leave_idle(self) -> list[Event]:
        """Back to pomodoro, to the phase you left, ready to start. A break that would have
        run out while you were idle is over instead, with no reward (spec §3.2)."""
        self.idle = False
        if self._break_left is not None and self._clock.now() - self._idle_since >= self._break_left:
            return self._on_transition(self.timer.skip())
        return []

    def state(self) -> SessionState:
        timer = self.timer
        break_left = None
        if self.idle:
            if self._break_left is not None:
                break_left = max(0.0, self._break_left - (self._clock.now() - self._idle_since))
        elif timer.phase.is_break:
            break_left = timer.remaining()
        in_progress = not self.idle and timer.phase is Phase.FOCUS and timer.started
        return SessionState(timer.phase, timer.focus_in_set, self._set_clean, in_progress, break_left, self.idle)

    def restore(self, state: SessionState, closed_for: float) -> list[Event]:
        """Bring a saved session back, ready, never running (addendum §2.3). closed_for: seconds pomo was closed.
        A focus left without the quit dialog is abandoned now; a break that would have run out is over."""
        self.timer.restore(state.phase, state.focus_in_set)
        self._set_clean = state.set_clean
        self._reset_pause_tracking()
        events: list[Event] = []
        if state.focus_in_progress:
            events += self._break_rule(RuleKind.ABANDON_FOCUS)
        if state.idle:
            self.idle = True
            self._idle_since = self._clock.now()
            self._break_left = None if state.break_left is None else max(0.0, state.break_left - closed_for)
        elif state.break_left is not None and closed_for >= state.break_left:
            events += self._on_transition(self.timer.skip())
        return events

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

- [ ] **Step 5: Count focus sessions in the world**

In `src/pomo/game/world.py`:

Replace:

```python
from pomo.game.events import Event, Fed, Petted, Played
```

with:

```python
from pomo.game.events import Event, Fed, FocusCompleted, Petted, Played
```

Replace:

```python
        self.bowl_full = True
        self.bodies: dict[str, Body] = {}
```

with:

```python
        self.bowl_full = True
        self.focus_total = 0  # every focus ever completed: strays come by this (spec §4)
        self.bodies: dict[str, Body] = {}
```

Replace:

```python
    def apply(self, events: Iterable[Event]) -> None:
        for event in events:
            for cat in self.cats:
                cat.apply(event)
```

with:

```python
    def apply(self, events: Iterable[Event]) -> None:
        for event in events:
            for cat in self.cats:
                cat.apply(event)
            if isinstance(event, FocusCompleted):
                self.focus_total += 1
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest -q`
Expected: `527 passed`

- [ ] **Step 7: Commit**

```bash
git add src/pomo/clock.py src/pomo/timer.py src/pomo/session.py src/pomo/game/world.py tests/test_clock.py tests/test_timer.py tests/test_session.py tests/test_world.py
git commit -m "feat: a session can be snapshotted and restored: ready, never running, abandon charged once" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: The save file

**Files:**
- Create: `src/pomo/persist.py`, `tests/test_persist.py`
- Modify: `src/pomo/game/world.py` (`place`)

**Interfaces:**
- Consumes:
  - From Task 1: `SessionState`, `Session.state()`, `World.focus_total`.
  - From milestone 4: `World`, `Poop`, `Body`, `Cat`, `Trait`, `NEEDS`, `COATS`, `layout`.
- Produces:
  - `persist.VERSION = 1`.
  - `persist.snapshot(session, world, saved_at: float) -> dict`.
  - `persist.write(path, data: dict) -> None`: atomic.
  - `persist.load(path) -> Saved | None`: `None` when there's no file, and `BadSave` when the save can't be used.
  - `persist.read(data: object) -> Saved`, which raises `BadSave`.
  - `Saved(saved_at, session: SessionState, cats: tuple[SavedCat, ...], bowl_full, focus_total, poops: tuple[float, ...])`.
  - `SavedCat(cat: Cat, surface: str, x: float)`.
  - `persist.build_world(saved, rng) -> World`.
  - `persist.back_up(path, when: datetime) -> Path`.
  - `World.place(name, surface, x)`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_persist.py`:

```python
import json
import random
from datetime import datetime

import pytest

from pomo import persist
from pomo.clock import FakeClock
from pomo.game.cat import Cat, Trait
from pomo.game.world import Poop, World
from pomo.persist import BadSave, Saved
from pomo.session import Session, SessionState
from pomo.timer import Phase, TimerSettings

MIN = 60.0


def a_day_in_progress() -> tuple[Session, World]:
    """Mango on the shelf, a little grumpy and hungry, two focus sessions into a set, on a break."""
    clock = FakeClock()
    session = Session(TimerSettings.from_minutes(25, 5, 15, 4), clock)
    for _ in range(3):  # focus, break, focus: now on the second break
        if not session.timer.running:
            session.toggle()
        clock.advance(session.timer.remaining())
        session.tick()
    clock.advance(2 * MIN)
    mango = Cat("Mango", "tabby", Trait.CLINGY, mood=62.5, needs={"hunger": 75.0, "play": 10.0, "affection": 33.0})
    world = World([mango], random.Random(1))
    world.place("Mango", "shelf", 55.0)
    world.bowl_full, world.focus_total = False, 17
    world.poops = [Poop(20.0, world.scape.floor.y)]
    return session, world


def saved_dict() -> dict:
    session, world = a_day_in_progress()
    return json.loads(json.dumps(persist.snapshot(session, world, saved_at=1_759_500_000.0)))


def test_a_save_comes_back_exactly():
    saved = persist.read(saved_dict())
    assert saved.saved_at == 1_759_500_000.0
    assert saved.session == SessionState(Phase.SHORT_BREAK, 2, True, False, 3 * MIN, False)
    (mango,) = saved.cats
    assert (mango.cat.name, mango.cat.coat, mango.cat.trait, mango.cat.mood) == ("Mango", "tabby", Trait.CLINGY, 62.5)
    assert mango.cat.needs == {"hunger": 75.0, "play": 10.0, "affection": 33.0}
    assert (mango.surface, mango.x) == ("shelf", 55.0)
    assert (saved.bowl_full, saved.focus_total, saved.poops) == (False, 17, (20.0,))


def test_the_saved_world_is_rebuilt_as_it_was():
    world = persist.build_world(persist.read(saved_dict()), random.Random(2))
    (mango,) = world.cats
    body = world.bodies["Mango"]
    assert (mango.mood, mango.needs["hunger"]) == (62.5, 75.0)
    assert (body.surface, body.x, body.y) == ("shelf", 55.0, world.scape.shelf.y)
    assert (world.bowl_full, world.focus_total) == (False, 17)
    assert [(p.x, p.y) for p in world.poops] == [(20.0, world.scape.floor.y)]


def test_the_file_holds_what_the_spec_says(tmp_path):
    path = tmp_path / "save.json"
    persist.write(path, saved_dict())
    data = json.loads(path.read_text())
    assert data["version"] == 1
    assert data["timer"] == {"phase": "short_break", "focus_in_set": 2, "set_clean": True,
                             "focus_in_progress": False, "break_left": 180.0, "idle": False}
    assert data["world"]["cats"][0]["surface"] == "shelf"


def test_writing_replaces_the_save_and_leaves_nothing_else_behind(tmp_path):
    path = tmp_path / "state" / "save.json"
    persist.write(path, {"n": 1})
    persist.write(path, {"n": 2})
    assert json.loads(path.read_text()) == {"n": 2}
    assert [p.name for p in path.parent.iterdir()] == ["save.json"]


def test_a_write_that_fails_leaves_the_old_save_alone(tmp_path):
    path = tmp_path / "save.json"
    persist.write(path, {"n": 1})
    with pytest.raises(TypeError):
        persist.write(path, {"n": object()})  # can't be written as JSON
    assert json.loads(path.read_text()) == {"n": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["save.json"]


def test_no_save_yet_is_none(tmp_path):
    assert persist.load(tmp_path / "save.json") is None


def test_load_reads_a_written_save(tmp_path):
    path = tmp_path / "save.json"
    persist.write(path, saved_dict())
    assert isinstance(persist.load(path), Saved)


def broken(change) -> dict:
    data = saved_dict()
    change(data)
    return data


@pytest.mark.parametrize("data", [
    [],
    broken(lambda d: d.update(version=2)),
    broken(lambda d: d.pop("timer")),
    broken(lambda d: d["timer"].update(phase="lunch")),
    broken(lambda d: d["timer"].update(idle="no")),
    broken(lambda d: d["timer"].update(focus_in_set=-1)),
    broken(lambda d: d["timer"].update(break_left="soon")),
    broken(lambda d: d["world"].update(cats=[])),
    broken(lambda d: d["world"]["cats"].append(dict(d["world"]["cats"][0]))),
    broken(lambda d: d["world"]["cats"][0].update(coat="plaid")),
    broken(lambda d: d["world"]["cats"][0].update(trait="sleepy")),
    broken(lambda d: d["world"]["cats"][0].update(surface="fridge")),
    broken(lambda d: d["world"]["cats"][0].update(name="")),
    broken(lambda d: d["world"]["cats"][0].update(mood=True)),
    broken(lambda d: d["world"]["cats"][0]["needs"].pop("play")),
    broken(lambda d: d["world"].update(focus_total=2.5)),
    broken(lambda d: d["world"].update(poops=[{"y": 3}])),
], ids=["not-a-table", "version", "no-timer", "phase", "idle", "count", "break-left", "no-cats", "twins", "coat",
        "trait", "surface", "nameless", "mood-bool", "needs", "total", "poop"])
def test_a_save_that_cannot_be_used_says_why(data):
    with pytest.raises(BadSave):
        persist.read(data)


@pytest.mark.parametrize("text", ["{not json", '{"version": 1, "saved_at": NaN}', "\udcff"])
def test_files_that_are_not_saves(tmp_path, text):
    path = tmp_path / "save.json"
    path.write_text(text, encoding="utf-8", errors="surrogateescape")
    with pytest.raises(BadSave):
        persist.load(path)


def test_numbers_out_of_range_are_clamped_not_rejected():
    def stretch(d):
        cat = d["world"]["cats"][0]
        cat["mood"], cat["needs"]["hunger"] = 150, -5
        d["timer"]["break_left"] = -3
    saved = persist.read(broken(stretch))
    assert (saved.cats[0].cat.mood, saved.cats[0].cat.needs["hunger"], saved.session.break_left) == (100, 0, 0)


def test_a_bad_save_is_put_aside_never_over_an_earlier_one(tmp_path):
    path = tmp_path / "save.json"
    when = datetime(2026, 10, 3, 9, 30, 5)
    path.write_text("first")
    first = persist.back_up(path, when)
    path.write_text("second")
    second = persist.back_up(path, when)
    assert (first.name, second.name) == ("save.json.bak-20261003-093005", "save.json.bak-20261003-093005-2")
    assert (first.read_text(), second.read_text()) == ("first", "second")
    assert not path.exists()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_persist.py -q`
Expected: FAIL during collection with `ImportError: cannot import name 'persist' from 'pomo'`

- [ ] **Step 3: Put a cat back where it was**

In `src/pomo/game/world.py`, in `World`:

Replace:

```python
    def feed(self) -> None:
```

with:

```python
    def place(self, name: str, surface: str, x: float) -> None:
        """Put a cat back where a save left it, standing still."""
        where = self.scape.surface(surface)
        body = self.bodies[name]
        body.surface, body.x, body.y = surface, clamp(x, *walkable(where)), float(where.y)
        self._stop(body)

    def feed(self) -> None:
```

- [ ] **Step 4: The save file**

Create `src/pomo/persist.py`:

```python
"""Saving and loading (daily-driver addendum §2): versioned JSON, written atomically.

`snapshot` turns the session and the world into plain data. `read` checks a save over
and turns it back into a `Saved`, or raises `BadSave` saying why. `write` swaps a new
save in with a rename, so a crash can never leave half of one, and `back_up` puts a
bad save aside so pomo can start fresh without losing it.
"""

from __future__ import annotations

import json
import math
import os
import random
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pomo.game.behavior import Body
from pomo.game.cat import NEEDS, Cat, Trait
from pomo.game.playscape import MIN_HEIGHT, MIN_WIDTH, layout
from pomo.game.world import Poop, World
from pomo.render.sprites import COATS
from pomo.session import Session, SessionState
from pomo.timer import Phase

VERSION = 1
SURFACES = frozenset(s.name for s in layout(MIN_WIDTH, MIN_HEIGHT).surfaces)


class BadSave(Exception):
    """The save can't be used. The message says why."""


@dataclass(frozen=True)
class SavedCat:
    cat: Cat
    surface: str
    x: float


@dataclass(frozen=True)
class Saved:
    saved_at: float  # wall-clock seconds since the epoch
    session: SessionState
    cats: tuple[SavedCat, ...]
    bowl_full: bool
    focus_total: int
    poops: tuple[float, ...]  # columns: poops are always on the floor


# --- out ---------------------------------------------------------------------------


def snapshot(session: Session, world: World, saved_at: float) -> dict:
    s = session.state()
    return {
        "version": VERSION,
        "saved_at": saved_at,
        "timer": {"phase": s.phase.value, "focus_in_set": s.focus_in_set, "set_clean": s.set_clean,
                  "focus_in_progress": s.focus_in_progress, "break_left": s.break_left, "idle": s.idle},
        "world": {
            "bowl_full": world.bowl_full,
            "focus_total": world.focus_total,
            "cats": [_cat_out(cat, world.bodies[cat.name]) for cat in world.cats],
            "poops": [{"x": poop.x} for poop in world.poops],
        },
    }


def _cat_out(cat: Cat, body: Body) -> dict:
    # A cat mid-jump is saved on the surface it jumped from: the column puts it back on its way.
    return {"name": cat.name, "coat": cat.coat, "trait": cat.trait.value, "mood": cat.mood,
            "needs": dict(cat.needs), "surface": body.surface, "x": body.x}


def write(path: Path, data: dict) -> None:
    """Swap a new save in: a temporary file beside it, flushed to disk, then renamed over it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# --- in ----------------------------------------------------------------------------


def load(path: Path) -> Saved | None:
    """The save at path, or None if there isn't one yet. Raises BadSave if it can't be used."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as e:
        raise BadSave(f"can't read it ({type(e).__name__})") from None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise BadSave(f"not valid JSON ({e.msg})") from None
    return read(data)


def read(data: object) -> Saved:
    root = _table(data, "the save")
    if root.get("version") != VERSION:
        raise BadSave(f"unknown version {root.get('version')!r}")
    timer, world = _table(root.get("timer"), "timer"), _table(root.get("world"), "world")
    break_left = timer.get("break_left")
    session = SessionState(
        phase=_choice(timer.get("phase"), {p.value: p for p in Phase}, "timer.phase"),
        focus_in_set=_count(timer.get("focus_in_set"), "timer.focus_in_set"),
        set_clean=_flag(timer.get("set_clean"), "timer.set_clean"),
        focus_in_progress=_flag(timer.get("focus_in_progress"), "timer.focus_in_progress"),
        break_left=None if break_left is None else max(0.0, _number(break_left, "timer.break_left")),
        idle=_flag(timer.get("idle"), "timer.idle"),
    )
    cats = tuple(_cat_in(c, i) for i, c in enumerate(_list(world.get("cats"), "world.cats")))
    if not cats:
        raise BadSave("no cats")
    names = [c.cat.name for c in cats]
    if len(set(names)) != len(names):
        raise BadSave("two cats share a name")
    poops = tuple(_number(_table(p, "a poop").get("x"), "poop x") for p in _list(world.get("poops"), "world.poops"))
    return Saved(_number(root.get("saved_at"), "saved_at"), session, cats,
                 _flag(world.get("bowl_full"), "world.bowl_full"),
                 _count(world.get("focus_total"), "world.focus_total"), poops)


def _cat_in(data: object, i: int) -> SavedCat:
    d = _table(data, f"cat {i + 1}")
    name = d.get("name")
    if not isinstance(name, str) or not name:
        raise BadSave(f"cat {i + 1} has no name")
    needs = _table(d.get("needs"), f"{name}'s needs")
    cat = Cat(
        name,
        _choice(d.get("coat"), {c: c for c in COATS}, f"{name}'s coat"),
        _choice(d.get("trait"), {t.value: t for t in Trait}, f"{name}'s trait"),
        mood=_percent(d.get("mood"), f"{name}'s mood"),
        needs={n: _percent(needs.get(n), f"{name}'s {n}") for n in NEEDS},
    )
    surface = _choice(d.get("surface"), {s: s for s in SURFACES}, f"{name}'s surface")
    return SavedCat(cat, surface, _number(d.get("x"), f"{name}'s column"))


def _table(value: object, what: str) -> dict:
    if not isinstance(value, dict):
        raise BadSave(f"{what} is missing or not a table")
    return value


def _list(value: object, what: str) -> list:
    if not isinstance(value, list):
        raise BadSave(f"{what} is missing or not a list")
    return value


def _flag(value: object, what: str) -> bool:
    if not isinstance(value, bool):
        raise BadSave(f"{what} is missing or not true/false")
    return value


def _number(value: object, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BadSave(f"{what} is missing or not a number")
    return float(value)


def _percent(value: object, what: str) -> float:
    return min(100.0, max(0.0, _number(value, what)))


def _count(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BadSave(f"{what} is missing or not a whole number")
    return value


def _choice[T](value: object, options: dict[str, T], what: str) -> T:
    if not isinstance(value, str) or value not in options:
        raise BadSave(f"{what} is unknown: {value!r}")
    return options[value]


def build_world(saved: Saved, rng: random.Random) -> World:
    """The room as the save left it. Its size is fitted to the screen at the first draw."""
    world = World([c.cat for c in saved.cats], rng)
    for c in saved.cats:
        world.place(c.cat.name, c.surface, c.x)
    world.bowl_full, world.focus_total = saved.bowl_full, saved.focus_total
    world.poops = [Poop(min(max(x, 0.0), world.scape.width - 1), world.scape.floor.y) for x in saved.poops]
    return world


def back_up(path: Path, when: datetime) -> Path:
    """Put a bad save aside as save.json.bak-<when>, never over an earlier one. Returns where it went."""
    stamp = when.strftime("%Y%m%d-%H%M%S")
    target, n = path.with_name(f"{path.name}.bak-{stamp}"), 2
    while target.exists():
        target, n = path.with_name(f"{path.name}.bak-{stamp}-{n}"), n + 1
    path.rename(target)
    return target
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -q`
Expected: `556 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/persist.py src/pomo/game/world.py tests/test_persist.py
git commit -m "feat: the save file: versioned JSON, atomic writes, validation, bad saves backed up" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: The app saves and comes back

**Files:**
- Modify: `src/pomo/ui/app.py`, `src/pomo/ui/view.py`
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes:
  - From Task 1: `WallClock`, `Session.restore`.
  - From Task 2: `persist.snapshot`, `write`, `build_world`, `Saved`.
- Produces:
  - `PomoApp(..., saved: persist.Saved | None = None, save_path: Path | None = None, wall: Clock | None = None)`. With no `save_path`, nothing is saved.
  - `PomoApp.save()`.
  - `SAVE_EVERY_S = 30.0`.
  - `view.remembers(cats) -> str`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_app.py`:

Replace:

```python
import random
```

with:

```python
import json
import random
```

Replace:

```python
from pomo.clock import FakeClock
```

with:

```python
from pomo import persist
from pomo.clock import FakeClock
```

and append to the end of `tests/test_app.py`:

```python
# --- saving (daily-driver addendum §2) -------------------------------------------

def a_save(saved_at: float, **timer) -> persist.Saved:
    """Mango on the shelf at mood 62.5, two focus sessions into the set, on a ready focus unless told otherwise."""
    state = {"phase": "focus", "focus_in_set": 2, "set_clean": True, "focus_in_progress": False,
             "break_left": None, "idle": False, **timer}
    return persist.read({
        "version": 1, "saved_at": saved_at, "timer": state,
        "world": {"bowl_full": False, "focus_total": 17, "poops": [],
                  "cats": [{"name": "Mango", "coat": "tabby", "trait": "clingy", "mood": 62.5,
                            "needs": {"hunger": 20.0, "play": 10.0, "affection": 30.0},
                            "surface": "shelf", "x": 55.0}]},
    })


def make_saving_app(tmp_path, saved=None, idle=False):
    clock = FakeClock()  # stands in for the wall clock too
    app = PomoApp(Config(), clock, FakeNotifier(), rng=random.Random(0), idle=idle, saved=saved,
                  save_path=tmp_path / "save.json", wall=clock)
    return app, clock, tmp_path / "save.json"


def on_disk(path):
    return json.loads(path.read_text())


async def test_a_phase_change_is_saved(tmp_path):
    app, clock, path = make_saving_app(tmp_path)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(25 * MIN)
        app.tick()
        assert on_disk(path)["timer"]["phase"] == "short_break"
        assert on_disk(path)["world"]["focus_total"] == 1


async def test_the_room_is_saved_every_30_seconds(tmp_path):
    app, clock, path = make_saving_app(tmp_path)
    async with app.run_test(size=SIZE):
        clock.advance(29)
        app.tick()
        assert not path.exists()
        clock.advance(2)
        app.tick()
        assert on_disk(path)["world"]["cats"][0]["name"] == "Mango"


async def test_quitting_saves(tmp_path):
    app, _, path = make_saving_app(tmp_path)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("q")
    assert on_disk(path)["timer"]["focus_in_progress"] is False


async def test_a_confirmed_quit_mid_focus_is_saved_as_paid_for(tmp_path):
    app, clock, path = make_saving_app(tmp_path)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(5 * MIN)
        await pilot.press("q", "y")
    assert on_disk(path)["timer"]["focus_in_progress"] is False
    assert on_disk(path)["world"]["cats"][0]["mood"] == 55


async def test_closing_mid_focus_without_the_dialog_saves_the_focus_as_still_owed(tmp_path):
    app, clock, path = make_saving_app(tmp_path)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(5 * MIN)
        app.exit()  # the window closing, say
    assert on_disk(path)["timer"]["focus_in_progress"] is True


async def test_pomo_comes_back_where_it_left_off(tmp_path):
    saved = a_save(saved_at=FakeClock().now() - 60, phase="short_break", break_left=180.0)
    app, _, _ = make_saving_app(tmp_path, saved=saved)
    async with app.run_test(size=SIZE):
        timer = app.session.timer
        assert (timer.phase, timer.started, timer.focus_in_set) == (Phase.SHORT_BREAK, False, 2)
        assert (app.world.cats[0].mood, app.world.bodies["Mango"].surface) == (62.5, "shelf")
        assert (app.world.focus_total, app.world.bowl_full) == (17, False)
        assert "Mango  ♥♥♥♡♡ grumpy" in on_screen(app)


async def test_a_focus_left_without_the_dialog_costs_25_on_the_next_launch(tmp_path):
    saved = a_save(saved_at=FakeClock().now() - 3600, focus_in_progress=True)
    app, _, _ = make_saving_app(tmp_path, saved=saved)
    async with app.run_test(size=SIZE):
        assert app.world.cats[0].mood == 37.5
        assert text(app, "message") == "Mango remembers you left."
        assert not app.session.timer.started


async def test_a_break_that_ran_out_while_closed_comes_back_as_a_focus(tmp_path):
    saved = a_save(saved_at=FakeClock().now() - 3600, phase="short_break", break_left=180.0)
    app, _, _ = make_saving_app(tmp_path, saved=saved)
    async with app.run_test(size=SIZE):
        assert (app.session.timer.phase, app.session.timer.started) == (Phase.FOCUS, False)
        assert app.world.cats[0].mood == 62.5  # no reward, no penalty


async def test_the_idle_flag_wins_over_the_save(tmp_path):
    app, _, _ = make_saving_app(tmp_path, saved=a_save(saved_at=FakeClock().now()), idle=True)
    async with app.run_test(size=SIZE):
        assert app.session.idle


async def test_a_save_that_fails_says_so_once(tmp_path):
    (tmp_path / "save.json").mkdir()  # a directory where the save should go: every write fails
    app, clock, _ = make_saving_app(tmp_path)
    async with app.run_test(size=SIZE):
        clock.advance(31)
        app.tick()
        assert text(app, "message").startswith("Couldn't save your cats:")
        app.show_message("")
        clock.advance(31)
        app.tick()
        assert text(app, "message") == ""
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_app.py -q`
Expected: `10 failed, 48 passed`. Every failure is `TypeError: PomoApp.__init__() got an unexpected keyword argument 'saved'`.

- [ ] **Step 3: The "remembers" message**

In `src/pomo/ui/view.py`:

Replace:

```python
import math
```

with:

```python
import math
from collections.abc import Sequence
```

Replace:

```python
from pomo.game.balance import PENALTIES
```

with:

```python
from pomo.game.balance import PENALTIES
from pomo.game.cat import Cat
```

Replace:

```python
def confirm_question(
```

with:

```python
def remembers(cats: Sequence[Cat]) -> str:
    """The message for a focus left without the quit dialog, charged on the next launch (spec §3.2)."""
    return f"{cats[0].name} remembers you left." if len(cats) == 1 else "The cats remember you left."


def confirm_question(
```

- [ ] **Step 4: Save and restore in the app**

In `src/pomo/ui/app.py`, the imports:

Replace:

```python
import random
from collections.abc import Callable, Iterable
```

with:

```python
import logging
import random
from collections.abc import Callable, Iterable
from pathlib import Path
```

Replace:

```python
from pomo.awake import KeepsAwake, NoKeepAwake
from pomo.clock import Clock
from pomo.config import Config
from pomo.game.cat import Cat, Trait
from pomo.game.events import Event
```

with:

```python
from pomo import persist
from pomo.awake import KeepsAwake, NoKeepAwake
from pomo.clock import Clock, WallClock
from pomo.config import Config
from pomo.game.cat import Cat, Trait
from pomo.game.events import Event, RuleBreak
```

The constants:

Replace:

```python
TICK_S = 1 / 8  # 8 fps: the session ticks and the scene redraws together
```

with:

```python
log = logging.getLogger(__name__)

TICK_S = 1 / 8  # 8 fps: the session ticks and the scene redraws together
SAVE_EVERY_S = 30.0  # and on every phase change, and on the way out (addendum §2.2)
```

`PomoApp.__init__`'s parameters:

Replace:

```python
        rng: random.Random | None = None,
        idle: bool = False,
    ) -> None:
```

with:

```python
        rng: random.Random | None = None,
        idle: bool = False,
        saved: persist.Saved | None = None,
        save_path: Path | None = None,
        wall: Clock | None = None,
    ) -> None:
```

Its body. The world is now made after the rest of the state, because restoring it can produce events to handle:

Replace:

```python
        if idle:
            self.session.enter_idle()  # free: nothing has started
        self.world = World([Cat("Mango", "tabby", Trait.CLINGY)], rng or random.Random())  # spec §4: a new save
        self.frame = 0
        self._last_tick = clock.now()
```

with:

```python
        rng = rng or random.Random()
        self.save_path = save_path  # None: nothing is saved (tests, mostly)
        self.wall = wall or WallClock()
        self.frame = 0
        self._last_tick = self._last_save = clock.now()
        self._save_failing = False
```

Replace:

```python
        self._message = ""
        self._message_at = 0.0

    def get_default_screen
```

with:

```python
        self._message = ""
        self._message_at = 0.0
        if saved is None:
            self.world = World([Cat("Mango", "tabby", Trait.CLINGY)], rng)  # spec §4: a new save
        else:
            self.world = persist.build_world(saved, rng)
            events = self.session.restore(saved.session, max(0.0, self.wall.now() - saved.saved_at))
            self.handle(events)
            if any(isinstance(e, RuleBreak) for e in events):
                self.show_message(view.remembers(self.world.cats))
        if idle and not self.session.idle:
            self.session.enter_idle()  # --idle wins over the save; free, since nothing restored is running

    def get_default_screen
```

Save every 30 s, in `tick`:

Replace:

```python
        self.world.tick(dt)
        self._report(self.world.take_news())
        self.refresh_view()
```

with:

```python
        self.world.tick(dt)
        self._report(self.world.take_news())
        if now - self._last_save >= SAVE_EVERY_S:
            self.save()
        self.refresh_view()
```

…on every phase change, in `handle`:

Replace:

```python
    def handle(self, events: list[Event]) -> None:
        self.world.apply(events)
        self._transitions += sum(isinstance(e, Transition) for e in events)
```

with:

```python
    def handle(self, events: list[Event]) -> None:
        self.world.apply(events)
        changes = sum(isinstance(e, Transition) for e in events)
        self._transitions += changes
        if changes:
            self.save()
```

…and on the way out:

Replace:

```python
    def on_unmount(self) -> None:
        self.keep_awake.hold(False)
```

with:

```python
    def save(self) -> None:
        """Write the save (addendum §2.2). A failure is shown once, and tried again at the next save point."""
        self._last_save = self.clock.now()
        if self.save_path is None:
            return
        try:
            persist.write(self.save_path, persist.snapshot(self.session, self.world, self.wall.now()))
        except OSError as e:
            log.warning("saving failed: %s", type(e).__name__)
            if not self._save_failing:
                self.show_message(f"Couldn't save your cats: {e.strerror or type(e).__name__}.")
            self._save_failing = True
        else:
            self._save_failing = False

    def on_unmount(self) -> None:
        self.keep_awake.hold(False)
        self.save()  # however the app is closing; a focus still under way is charged on the next launch
```

Replace:

```python
    def _quit(self) -> None:
        self.handle(self.session.quit())
        self.exit()
```

with:

```python
    def _quit(self) -> None:
        self.handle(self.session.quit())
        self.save()
        self.exit()
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -q`
Expected: `566 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/ui/app.py src/pomo/ui/view.py tests/test_app.py
git commit -m "feat: the app saves on phase changes, every 30 s and on the way out, and comes back where it left off" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: One pomo at a time, with its save

**Files:**
- Create: `src/pomo/lock.py`, `tests/test_lock.py`
- Modify: `src/pomo/paths.py`
- Replace: `src/pomo/cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes:
  - From Task 2: `persist.load`, `BadSave`, `back_up`.
  - From Task 3: `PomoApp(saved=, save_path=)`.
- Produces:
  - `lock.acquire(path) -> Lock | None`, and `Lock.release()`.
  - `paths.save_path()` and `paths.lock_path()`.
  - `cli.run(args, cfg, path) -> int`, run with the lock held.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_lock.py`:

```python
from pomo.lock import acquire


def test_only_one_holder_at_a_time(tmp_path):
    path = tmp_path / "state" / "pomo.lock"
    first = acquire(path)
    assert first is not None
    assert acquire(path) is None
    first.release()
    second = acquire(path)
    assert second is not None
    second.release()


def test_releasing_twice_is_harmless(tmp_path):
    lock = acquire(tmp_path / "pomo.lock")
    lock.release()
    lock.release()
```

In `tests/test_cli.py`:

Replace:

```python
import pytest

from pomo import cli
```

with:

```python
import random

import pytest

from pomo import cli, persist
from pomo.clock import FakeClock
from pomo.game.cat import Cat, Trait
from pomo.game.world import World
from pomo.lock import acquire
from pomo.paths import lock_path, save_path
from pomo.session import Session
from pomo.timer import TimerSettings
```

and append to the end of `tests/test_cli.py`:

```python
def a_written_save(focus_total: int) -> None:
    clock = FakeClock()
    session = Session(TimerSettings.from_minutes(25, 5, 15, 4), clock)
    world = World([Cat("Mango", "tabby", Trait.CLINGY)], random.Random(0))
    world.focus_total = focus_total
    persist.write(save_path(), persist.snapshot(session, world, saved_at=0.0))


def test_the_save_is_loaded_and_saving_goes_back_to_it(launched):
    a_written_save(focus_total=12)
    assert cli.main([]) == 0
    (app,) = launched
    assert app.world.focus_total == 12
    assert app.save_path == save_path()


def test_with_no_save_mango_starts_fresh(launched):
    cli.main([])
    assert [c.name for c in launched[0].world.cats] == ["Mango"]


def test_an_unreadable_save_is_kept_aside_and_pomo_starts_fresh(launched):
    save_path().parent.mkdir(parents=True, exist_ok=True)
    save_path().write_text("not a save")
    assert cli.main([]) == 0
    (app,) = launched
    assert app.world.focus_total == 0
    (kept,) = save_path().parent.glob("save.json.bak-*")
    assert kept.read_text() == "not a save"
    assert not save_path().exists()
    assert any("couldn't be read" in w and kept.name in w for w in app._warnings)


def test_a_second_pomo_is_turned_away(launched, capsys):
    held = acquire(lock_path())
    try:
        assert cli.main([]) == 1
    finally:
        held.release()
    assert launched == []
    assert "already running" in capsys.readouterr().err


def test_the_lock_is_let_go_when_pomo_ends(launched):
    cli.main([])
    lock = acquire(lock_path())
    assert lock is not None
    lock.release()
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_lock.py tests/test_cli.py -q`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.lock'`

- [ ] **Step 3: The lock and the paths**

Create `src/pomo/lock.py`:

```python
"""One pomo at a time (daily-driver addendum §2.5).

An exclusive flock on a lock file, held for the whole run. The operating system drops it
when the process ends, however it ends, so there's never a stale lock to clean up.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path


class Lock:
    def __init__(self, fd: int) -> None:
        self._fd = fd

    def release(self) -> None:
        if self._fd >= 0:
            os.close(self._fd)  # closing the file lets the lock go
            self._fd = -1


def acquire(path: Path) -> Lock | None:
    """The lock, or None while another pomo holds it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return Lock(fd)
```

In `src/pomo/paths.py`:

Replace:

```python
def log_path() -> Path:
    return state_dir() / "pomo.log"
```

with:

```python
def log_path() -> Path:
    return state_dir() / "pomo.log"


def save_path() -> Path:
    return state_dir() / "save.json"


def lock_path() -> Path:
    return state_dir() / "pomo.lock"
```

- [ ] **Step 4: Wire it into the command line**

Replace all of `src/pomo/cli.py` with:

```python
"""`pomo` command line: flags → config → app."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from pomo import __version__, persist
from pomo.awake import keep_awake
from pomo.clock import RealClock
from pomo.config import Config, ConfigError, load_config, permission_warning, with_overrides
from pomo.gallery import GalleryApp
from pomo.lock import acquire
from pomo.notify import Notifier, NullNotifier
from pomo.paths import config_path, lock_path, log_path, save_path
from pomo.ui.app import PomoApp

log = logging.getLogger(__name__)

DESCRIPTION = (
    "A pomodoro timer for your terminal, with cats. "
    "Pings your desktop, and your phone via ntfy, when each phase ends."
)
EPILOG = """\
keys:
  space  start / pause        s  skip phase        r  reset phase
  + / -  add / remove 5 min   i  idle mode         q  quit
  1-5    pick a care tool: feed, ball, string, pet, scoop     esc  put it down

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
    parser.add_argument("--idle", action="store_true", help="start in Idle mode: no timer, every care tool unlocked")
    parser.add_argument("--no-notify", action="store_true", help="no desktop or phone notifications")
    parser.add_argument("--config", type=Path, metavar="PATH", help="config file to use instead of the default")
    parser.add_argument("--gallery", action="store_true", help="show every cat sprite and prop (for tuning the art)")
    parser.add_argument("--version", action="version", version=f"pomo {__version__}")
    return parser


def setup_logging(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def truecolor_warning(environ: Mapping[str, str]) -> str | None:
    """iTerm2 and Ghostty set COLORTERM=truecolor. Without it the pixel art gets approximated."""
    if environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return None
    return "This terminal doesn't report 24-bit colour (COLORTERM), so the cats may look a bit off."


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.gallery:
        GalleryApp().run()
        return 0
    if args.config is not None:
        path = args.config.expanduser()  # shells don't expand ~ in --config=~/...
        if not path.is_file():
            print(f"pomo: config file not found: {path}", file=sys.stderr)
            return 2
    else:
        path = config_path()  # the default may be missing: that just means defaults
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
    lock = acquire(lock_path())
    if lock is None:
        print("pomo is already running in another window.", file=sys.stderr)
        return 1
    try:
        return run(args, cfg, path)
    finally:
        lock.release()


def run(args: argparse.Namespace, cfg: Config, path: Path) -> int:
    """The timer itself, with the lock held."""
    warnings = [w for w in [permission_warning(path, cfg), truecolor_warning(os.environ)] if w]
    try:
        saved = persist.load(save_path())
    except persist.BadSave as e:
        log.warning("unreadable save: %s", e)
        try:
            kept = persist.back_up(save_path(), datetime.now())
        except OSError as move_error:
            print(f"pomo: can't read the save or move it aside ({move_error.strerror})", file=sys.stderr)
            return 2
        saved = None
        warnings.append(f"Your save couldn't be read, so pomo started fresh. The old one is kept as {kept.name}.")
    app = PomoApp(cfg, RealClock(), NullNotifier(), warnings=warnings, keep_awake=keep_awake(), idle=args.idle,
                  saved=saved, save_path=save_path())
    if not args.no_notify:
        # The bell must ring on Textual's thread; notifications arrive from a worker thread.
        app.notifier = Notifier(cfg.ntfy_server, cfg.topic, bell=lambda: app.call_from_thread(app.bell))
    app.run()
    return 0
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -q`
Expected: `573 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/lock.py src/pomo/paths.py src/pomo/cli.py tests/test_lock.py tests/test_cli.py
git commit -m "feat: one pomo at a time; the save is loaded at launch and a bad one is kept aside" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Setup helpers: `--init` and `--test-ping`

**Files:**
- Replace: `src/pomo/config.py`, `src/pomo/cli.py`, `README.md`
- Modify: `src/pomo/notify.py`
- Test: `tests/test_config.py`, `tests/test_notify.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: from Task 4, `cli.py`'s structure (`main` → `run`).
- Produces:
  - `config.STARTER`, `config.new_topic() -> str`, `config.write_starter(path, topic) -> bool`.
  - `config.display_path(path) -> str`, renamed from `_display_path`.
  - `notify.TEST_PING`, `notify.BANNER_HINT`.
  - `notify.send_test_ping(cfg, config_shown, *, desktop=None, post=None, platform=sys.platform) -> tuple[list[str], bool]`.
  - `cli.init(path) -> int`.
  - `--init` and `--test-ping`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_config.py`:

Replace:

```python
from pathlib import Path

import pytest

from pomo.config import Config, ConfigError, load_config, permission_warning, with_overrides
```

with:

```python
import re
import stat
from pathlib import Path

import pytest

from pomo.config import (
    Config, ConfigError, load_config, new_topic, permission_warning, with_overrides, write_starter,
)
```

and append to the end of `tests/test_config.py`:

```python
def test_a_new_topic_is_long_random_and_safe_for_ntfy():
    topics = {new_topic() for _ in range(50)}
    assert len(topics) == 50
    assert all(re.fullmatch(r"pomo-[A-Za-z0-9_-]{22}", t) for t in topics)


def test_the_starter_file_is_private_and_loads(tmp_path):
    path = tmp_path / "pomo" / "config.toml"
    assert write_starter(path, "pomo-abc_DEF-123")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    cfg = load_config(path)
    assert cfg == Config(topic="pomo-abc_DEF-123")
    assert cfg.topic == "pomo-abc_DEF-123"
    assert permission_warning(path, cfg) is None


def test_the_starter_never_overwrites_a_config(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("focus = 50\n")
    assert not write_starter(path, "pomo-new")
    assert path.read_text() == "focus = 50\n"
```

In `tests/test_notify.py`:

Replace:

```python
from pomo.notify import NullNotifier, Notifier, Ping, build_ntfy_request, encode_header, ping_for
```

with:

```python
from pomo.notify import (
    NullNotifier, Notifier, Ping, build_ntfy_request, encode_header, ping_for, send_test_ping,
)
```

and append to the end of `tests/test_notify.py`:

```python
# --- pomo --test-ping ---------------------------------------------------------------

SECRET = "pomo-s3cret-topic"


def tried(**cfg):
    sent = {"desktop": [], "phone": []}

    def desktop(ping):
        sent["desktop"].append(ping)
        return True

    def post(request):
        sent["phone"].append(request)

    return sent, desktop, post


def test_a_test_ping_goes_to_both_and_says_so():
    sent, desktop, post = tried()
    lines, ok = send_test_ping(Config(topic=SECRET), "~/.config/pomo/config.toml", desktop=desktop, post=post,
                               platform="darwin")
    assert ok
    assert lines == ["desktop: sent. No banner? Allow notifications for Script Editor in System Settings → "
                     "Notifications.", "phone: sent to your ntfy topic."]
    assert [p.title for p in sent["desktop"]] == ["🍅 pomo test"]
    assert sent["phone"][0].full_url == f"https://ntfy.sh/{SECRET}"


def test_the_banner_hint_is_only_for_macos():
    _, desktop, post = tried()
    lines, _ = send_test_ping(Config(topic=SECRET), "x", desktop=desktop, post=post, platform="linux")
    assert lines[0] == "desktop: sent."


def test_without_a_topic_the_phone_is_skipped_and_explained():
    _, desktop, post = tried()
    lines, ok = send_test_ping(Config(), "~/.config/pomo/config.toml", desktop=desktop, post=post)
    assert ok
    assert lines[1] == "phone: no topic set in ~/.config/pomo/config.toml (run pomo --init)."


def test_a_failed_phone_ping_says_why_without_the_topic():
    def refuse(request):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)

    lines, ok = send_test_ping(Config(topic=SECRET), "x", desktop=lambda p: True, post=refuse)
    assert not ok
    assert lines[1] == "phone: failed (HTTP 403)."
    assert not any(SECRET in line for line in lines)


def test_no_desktop_notifications_is_a_failure():
    lines, ok = send_test_ping(Config(), "x", desktop=lambda p: False, post=lambda r: None)
    assert not ok
    assert lines[0] == "desktop: couldn't show a notification here."
```

In `tests/test_cli.py`:

Replace:

```python
import random

import pytest

from pomo import cli, persist
```

with:

```python
import random
import stat

import pytest

from pomo import cli, notify, persist
```

Replace:

```python
from pomo.paths import lock_path, save_path
```

with:

```python
from pomo.config import load_config
from pomo.paths import config_path, lock_path, save_path
```

Replace:

```python
    for flag in ["--focus", "--short-break", "--long-break", "--long-every", "--no-notify", "--config", "--gallery",
                 "--version"]:
```

with:

```python
    for flag in ["--focus", "--short-break", "--long-break", "--long-every", "--no-notify", "--config", "--gallery",
                 "--version", "--idle", "--init", "--test-ping"]:
```

and append to the end of `tests/test_cli.py`:

```python
# --- setup helpers ------------------------------------------------------------------

def test_init_writes_a_private_starter_and_says_what_next_without_the_topic(capsys):
    assert cli.main(["--init"]) == 0
    out = capsys.readouterr().out
    path = config_path()
    topic = load_config(path).topic
    assert topic.startswith("pomo-")
    assert "Install the ntfy app" in out and "pomo --test-ping" in out
    assert topic not in out
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_init_leaves_an_existing_config_alone(capsys):
    config_path().parent.mkdir(parents=True)
    config_path().write_text("focus = 50\n")
    assert cli.main(["--init"]) == 0
    assert "already exists" in capsys.readouterr().out
    assert config_path().read_text() == "focus = 50\n"


def test_init_writes_where_config_points(tmp_path):
    path = tmp_path / "elsewhere.toml"
    assert cli.main(["--init", "--config", str(path)]) == 0
    assert load_config(path).topic.startswith("pomo-")


def test_test_ping_reports_each_channel_and_its_result(monkeypatch, capsys, launched):
    path = config_path()
    cli.main(["--init"])
    capsys.readouterr()
    topic = load_config(path).topic
    monkeypatch.setattr(notify, "desktop_notify", lambda ping: True)
    monkeypatch.setattr(notify, "urlopen_post", lambda request: None)
    assert cli.main(["--test-ping"]) == 0
    out = capsys.readouterr().out
    assert "desktop: sent." in out and "phone: sent to your ntfy topic." in out
    assert topic not in out
    assert launched == []  # it doesn't start the timer


def test_a_failing_test_ping_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(notify, "desktop_notify", lambda ping: False)
    assert cli.main(["--test-ping"]) == 1
    assert "desktop: couldn't" in capsys.readouterr().out
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_config.py tests/test_notify.py tests/test_cli.py -q`
Expected: FAIL during collection with `ImportError: cannot import name 'new_topic' from 'pomo.config'` (and `'send_test_ping'` from `pomo.notify`)

- [ ] **Step 3: The starter config**

Replace all of `src/pomo/config.py` with:

```python
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
```

- [ ] **Step 4: The test ping**

In `src/pomo/notify.py`:

Replace:

```python
@dataclass(frozen=True)
class Ping:
    title: str
    body: str
```

with:

```python
@dataclass(frozen=True)
class Ping:
    title: str
    body: str


TEST_PING = Ping("🍅 pomo test", "If you can read this, pings work. Mango says hi.")
BANNER_HINT = " No banner? Allow notifications for Script Editor in System Settings → Notifications."
```

Replace:

```python
class Notifier:
```

with:

```python
def send_test_ping(
    cfg: Config,
    config_shown: str,
    *,
    desktop: Callable[[Ping], bool] | None = None,
    post: Callable[[urllib.request.Request], None] | None = None,
    platform: str = sys.platform,
) -> tuple[list[str], bool]:
    """`pomo --test-ping`: one notification, sent now on this thread. Returns a line per channel, and
    whether every channel it tried worked. The lines never show the topic or the URL."""
    desktop, post = desktop or desktop_notify, post or urlopen_post
    lines, ok = [], True
    if desktop(TEST_PING):
        lines.append("desktop: sent." + (BANNER_HINT if platform == "darwin" else ""))
    else:
        lines.append("desktop: couldn't show a notification here.")
        ok = False
    if not cfg.topic:
        lines.append(f"phone: no topic set in {config_shown} (run pomo --init).")
    else:
        try:
            post(build_ntfy_request(TEST_PING, cfg.ntfy_server, cfg.topic))
        except Exception as e:  # whatever went wrong is the answer the user asked for
            lines.append(f"phone: failed ({_describe(e)}).")
            ok = False
        else:
            lines.append("phone: sent to your ntfy topic.")
    return lines, ok


class Notifier:
```

- [ ] **Step 5: The flags**

Replace all of `src/pomo/cli.py` with:

```python
"""`pomo` command line: flags → config → app."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from pomo import __version__, persist
from pomo.awake import keep_awake
from pomo.clock import RealClock
from pomo.config import (
    Config, ConfigError, display_path, load_config, new_topic, permission_warning, with_overrides, write_starter,
)
from pomo.gallery import GalleryApp
from pomo.lock import acquire
from pomo.notify import Notifier, NullNotifier, send_test_ping
from pomo.paths import config_path, lock_path, log_path, save_path
from pomo.ui.app import PomoApp

log = logging.getLogger(__name__)

INIT_DONE = """\
Wrote {path} (only you can read it).
It holds a private ntfy topic made just for you. For pings on your phone:
  1. Install the ntfy app and subscribe to the topic in that file.
  2. Run: pomo --test-ping"""

DESCRIPTION = (
    "A pomodoro timer for your terminal, with cats. "
    "Pings your desktop, and your phone via ntfy, when each phase ends."
)
EPILOG = """\
keys:
  space  start / pause        s  skip phase        r  reset phase
  + / -  add / remove 5 min   i  idle mode         q  quit
  1-5    pick a care tool: feed, ball, string, pet, scoop     esc  put it down

config file (all keys optional), default ~/.config/pomo/config.toml.
pomo --init writes one for you, with a private ntfy topic; pomo --test-ping checks it:
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
    parser.add_argument("--idle", action="store_true", help="start in Idle mode: no timer, every care tool unlocked")
    parser.add_argument("--no-notify", action="store_true", help="no desktop or phone notifications")
    parser.add_argument("--config", type=Path, metavar="PATH", help="config file to use instead of the default")
    parser.add_argument("--init", action="store_true", help="write a starter config file with a private ntfy topic")
    parser.add_argument("--test-ping", action="store_true", help="send a test notification to your desktop and phone")
    parser.add_argument("--gallery", action="store_true", help="show every cat sprite and prop (for tuning the art)")
    parser.add_argument("--version", action="version", version=f"pomo {__version__}")
    return parser


def setup_logging(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def truecolor_warning(environ: Mapping[str, str]) -> str | None:
    """iTerm2 and Ghostty set COLORTERM=truecolor. Without it the pixel art gets approximated."""
    if environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return None
    return "This terminal doesn't report 24-bit colour (COLORTERM), so the cats may look a bit off."


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.gallery:
        GalleryApp().run()
        return 0
    if args.init:
        return init(args.config.expanduser() if args.config is not None else config_path())
    if args.config is not None:
        path = args.config.expanduser()  # shells don't expand ~ in --config=~/...
        if not path.is_file():
            print(f"pomo: config file not found: {path}", file=sys.stderr)
            return 2
    else:
        path = config_path()  # the default may be missing: that just means defaults
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
    if args.test_ping:
        lines, ok = send_test_ping(cfg, display_path(path))
        print("\n".join(lines))
        return 0 if ok else 1
    lock = acquire(lock_path())
    if lock is None:
        print("pomo is already running in another window.", file=sys.stderr)
        return 1
    try:
        return run(args, cfg, path)
    finally:
        lock.release()


def init(path: Path) -> int:
    """`pomo --init`. The topic stays in the file: never printed, so it stays out of scrollback."""
    if not write_starter(path, new_topic()):
        print(f"{display_path(path)} already exists, so pomo left it alone.")
        return 0
    print(INIT_DONE.format(path=display_path(path)))
    return 0


def run(args: argparse.Namespace, cfg: Config, path: Path) -> int:
    """The timer itself, with the lock held."""
    warnings = [w for w in [permission_warning(path, cfg), truecolor_warning(os.environ)] if w]
    try:
        saved = persist.load(save_path())
    except persist.BadSave as e:
        log.warning("unreadable save: %s", e)
        try:
            kept = persist.back_up(save_path(), datetime.now())
        except OSError as move_error:
            print(f"pomo: can't read the save or move it aside ({move_error.strerror})", file=sys.stderr)
            return 2
        saved = None
        warnings.append(f"Your save couldn't be read, so pomo started fresh. The old one is kept as {kept.name}.")
    app = PomoApp(cfg, RealClock(), NullNotifier(), warnings=warnings, keep_awake=keep_awake(), idle=args.idle,
                  saved=saved, save_path=save_path())
    if not args.no_notify:
        # The bell must ring on Textual's thread; notifications arrive from a worker thread.
        app.notifier = Notifier(cfg.ntfy_server, cfg.topic, bell=lambda: app.call_from_thread(app.bell))
    app.run()
    return 0
```

- [ ] **Step 6: The README**

Replace all of `README.md` with:

````markdown
# pomo

A pomodoro timer for your terminal, with a room full of pixel-art cats. Mango lives in the
room: he naps up high while you focus, gets the zoomies on your breaks, eats from the bowl
when he's hungry, pops out through the litter door now and then, and remembers every rule
you break. Look after him with the toolbar: fill his bowl, roll him a yarn ball, dangle a
string, and pet him with the mouse. More cats and real consequences arrive in later milestones.

Needs a terminal with 24-bit colour and at least 100×30 cells. iTerm2 and Ghostty are the targets.

## Install

```bash
uv tool install --editable .    # from this directory: puts `pomo` on your PATH
```

`--editable` makes `pomo` run the code in this folder, so it's always the latest. Only one
`pomo` runs at a time: a second one says so and exits.

## Use

```bash
pomo                               # 25 min focus, 5 min breaks, 15 min long break every 4
pomo --focus 50 --short-break 10
pomo --idle                        # no timer: just hang out with the cats
pomo --init                        # write a starter config file, with a private ntfy topic
pomo --test-ping                   # check desktop and phone notifications right now
pomo --help                        # every flag, key and config option
pomo --gallery                     # every cat pose, face and coat, for tuning the art
```

Keys: `space` start/pause · `s` skip · `r` reset · `+`/`-` 5 min · `i` idle mode · `q` quit

Skipping or abandoning a focus (switching to Idle mid-focus counts), skipping a break, or
pausing a focus for more than 3 minutes breaks a rule. `pomo` asks before letting you,
because the cats will remember.

pomo remembers where you were: quit or close the window and Mango and your place in
the set are still there next time. Nothing happens while it's closed. Leaving in the
middle of a focus without `q` counts as abandoning it, so Mango will remember.

## Looking after the cats

Pick a tool with `1`–`5` or the toolbar, and put it down with `esc`:

- **1 Feed:** click the bowl, or press `1` again, to fill it. Hungry cats come to eat.
- **2 Ball:** click to drop a yarn ball. Cats that want to play chase it and bat it around.
- **3 String:** a string hangs from the mouse. Wiggle it and cats pounce at it.
- **4 Pet:** stroke a cat with the mouse. Content cats purr; angry ones hiss; too much earns a swat.
- **5 Scoop:** click a poop to clean it up. (Angry cats start pooping on the floor in a later milestone.)

A focus is nap time, so only the scoop works until your break. Idle mode (`i`) puts the
timer away and unlocks everything.

## Phone pings in 3 steps

1. `pomo --init` writes `~/.config/pomo/config.toml` (only you can read it) with a
   private, random ntfy topic in it.
2. Install the [ntfy](https://ntfy.sh) app on your phone, tap +, and subscribe to the
   topic from that file.
3. `pomo --test-ping` sends a test notification to your desktop and phone right now.

Anyone who knows the topic can read your pings, so keep it to yourself. pomo never
prints or logs it. On macOS, if no desktop banner shows up, allow notifications for
Script Editor in System Settings → Notifications.

## Develop

```bash
uv sync
uv run pytest
```
````

- [ ] **Step 7: Run the tests**

Run: `uv run pytest -q`
Expected: `586 passed`

- [ ] **Step 8: Commit**

```bash
git add src/pomo/config.py src/pomo/notify.py src/pomo/cli.py README.md tests/test_config.py tests/test_notify.py tests/test_cli.py
git commit -m "feat: pomo --init writes a private starter config; pomo --test-ping checks notifications now" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: The too-small screen

**Files:**
- Modify: `src/pomo/render/scene.py`, `src/pomo/ui/app.py`, `src/pomo/game/world.py`
- Test: `tests/test_scene.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: milestone 4's `scene.draw` and `room_point`, `TimerScreen.toolbar`.
- Produces:
  - `scene.MIN_COLUMNS = 100`, `scene.MIN_ROWS = 30`, `scene.TOO_SMALL`.
  - `scene.too_small(columns, rows) -> bool`.
  - `scene.draw(..., terminal: tuple[int, int] | None = None)`.
  - `RosterLine.coat` (default `"tabby"`).
  - `PomoApp.too_small` (a property) and `PomoApp._room_point(col, row)`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_scene.py`, the imports:

Replace:

```python
from pomo.game.playscape import MIN_HEIGHT, layout
```

with:

```python
from pomo.game.playscape import layout
```

Replace:

```python
    BLINK_EVERY, CLOCK_PY, CLOCK_X, PANEL_WIDTH, ROSTER_ROW, TWINKLE_FRAMES, blinking, draw, room_point,
```

with:

```python
    BLINK_EVERY, CLOCK_PY, CLOCK_X, MIN_ROWS, PANEL_WIDTH, ROSTER_ROW, TWINKLE_FRAMES, blinking, draw, room_point,
    too_small,
```

The smallest real stage is now 28 rows: a 100×30 terminal, less the message line and the toolbar.

Replace:

```python
def test_a_cat_on_the_tree_top_fits_in_the_smallest_room(timer):
    small = layout(70, MIN_HEIGHT)
    top_cat = CatView("Pebble", "grey", "sit", "ok", x=small.tree_top.x0 + 8.5, feet=small.tree_top.y)
    canvas = render(timer, [top_cat], width=PANEL_WIDTH + 70, height=MIN_HEIGHT // 2)
    assert canvas.pixel_at(PANEL_WIDTH + small.tree_top.x0 + 2, 0) == sprites.COATS["grey"]["o"]  # ear tip
```

with:

```python
def test_a_cat_on_the_tree_top_fits_in_the_smallest_room(timer):
    rows = MIN_ROWS - 2  # a 100×30 terminal, less the message line and the toolbar
    small = layout(70, rows * 2)
    top_cat = CatView("Pebble", "grey", "sit", "ok", x=small.tree_top.x0 + 8.5, feet=small.tree_top.y)
    canvas = render(timer, [top_cat], width=PANEL_WIDTH + 70, height=rows)
    ear_tip = small.tree_top.y - 16
    assert ear_tip >= 0
    assert canvas.pixel_at(PANEL_WIDTH + small.tree_top.x0 + 2, ear_tip) == sprites.COATS["grey"]["o"]
```

Append to the end of `tests/test_scene.py`:

```python
# --- the too-small screen (spec §6) -------------------------------------------------

def render_small(timer, columns, rows, idle=False, roster=(RosterLine("Mango", 4, "content", "grey"),)):
    """What the stage shows in a columns×rows terminal (the toolbar is hidden then: one row for the message)."""
    canvas = Canvas(columns, rows - 1, (0, 0, 0))
    draw(canvas, timer, RoomView(cats=(MANGO,), roster=roster), 1, idle=idle, terminal=(columns, rows))
    return canvas


@pytest.mark.parametrize("size, small", [((100, 30), False), ((99, 30), True), ((100, 29), True), ((80, 24), True)])
def test_the_room_needs_a_100_by_30_terminal(size, small):
    assert too_small(*size) is small


def test_a_small_terminal_asks_for_room_and_keeps_the_timer_on_screen(timer):
    text = screen_text(render_small(timer, 80, 24))
    assert "The cats need more room." in text
    assert "Make the window at least 100×30 (it's 80×24 now)." in text
    assert "● FOCUS  25:00  space to start" in text


def test_the_too_small_screen_shows_a_sad_cat_in_the_first_cats_coat(timer):
    canvas = render_small(timer, 80, 24)
    grey = sprites.COATS["grey"]["f"]
    assert any(canvas.pixel_at(x, py) == grey for x in range(80) for py in range(46))
    assert all(canvas.pixel_at(x, py) != sprites.COATS["tabby"]["f"] for x in range(80) for py in range(46))


def test_the_room_is_not_drawn_on_the_too_small_screen(timer):
    canvas = render_small(timer, 80, 24)
    assert all(canvas.pixel_at(x, py) != theme.FLOOR for x in range(80) for py in range(46))


def test_idle_shows_on_the_too_small_screen(timer):
    assert "● IDLE" in screen_text(render_small(timer, 80, 24, idle=True))


def test_a_tiny_terminal_skips_the_cat_and_cuts_the_text(timer):
    canvas = render_small(timer, 20, 6)
    text = screen_text(canvas)
    assert "The cats need more" in text
    assert all(canvas.pixel_at(x, py) == theme.PANEL_BG for x in range(20) for py in range(10)
               if canvas.char_at(x, py // 2) is None)


def test_the_canvas_alone_decides_when_no_terminal_size_is_given(timer):
    assert "The cats need more room." not in screen_text(render(timer, height=MIN_ROWS - 2))
    assert "The cats need more room." in screen_text(render(timer, height=MIN_ROWS - 3))
```

Append to the end of `tests/test_app.py`:

```python
async def test_a_small_window_asks_for_room_and_the_timer_keeps_working():
    app, clock, _ = make_app()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause()
        assert "The cats need more room." in on_screen(app)
        assert not app.main.toolbar.display
        await pilot.press("space")
        clock.advance(61)
        app.tick()
        assert "● FOCUS  23:59" in on_screen(app)


async def test_the_mouse_tools_are_off_while_the_window_is_too_small():
    app, _, _ = make_app()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.press("4")
        await pilot.hover(Stage, offset=(60, 10))
        assert app.world.pointer is None


async def test_growing_the_window_brings_the_room_back():
    app, _, _ = make_app()
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.resize_terminal(100, 30)
        app.tick()
        await pilot.pause()
        assert app.main.toolbar.display
        assert "The cats need more room." not in on_screen(app)
        assert "● FOCUS" in on_screen(app)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_scene.py tests/test_app.py -q`
Expected: FAIL during collection with `ImportError: cannot import name 'MIN_ROWS' from 'pomo.render.scene'`

- [ ] **Step 3: The roster carries each cat's coat**

In `src/pomo/game/world.py`:

Replace:

```python
@dataclass(frozen=True)
class RosterLine:
    name: str
    hearts: int
    stage: str
```

with:

```python
@dataclass(frozen=True)
class RosterLine:
    name: str
    hearts: int
    stage: str
    coat: str = "tabby"
```

Replace:

```python
        roster = tuple(RosterLine(c.name, c.hearts, c.stage.value) for c in self.cats)
```

with:

```python
        roster = tuple(RosterLine(c.name, c.hearts, c.stage.value, c.coat) for c in self.cats)
```

- [ ] **Step 4: Draw the too-small screen**

In `src/pomo/render/scene.py`:

Replace:

```python
EFFECT_TEXT = {"heart": "♥", "hiss": "#@!", "swat": "swat!"}
```

with:

```python
EFFECT_TEXT = {"heart": "♥", "hiss": "#@!", "swat": "swat!"}
MIN_COLUMNS, MIN_ROWS = 100, 30  # the smallest terminal the room fits in (spec §6)
TOO_SMALL = ("The cats need more room.", "Make the window at least 100×30 (it's {w}×{h} now).")
```

Replace:

```python
def draw(canvas: Canvas, timer: PomodoroTimer, room_view: RoomView, frame: int, idle: bool = False) -> None:
    canvas.fill(0, 0, canvas.width, canvas.height, theme.ROOM_BG)
```

with:

```python
def draw(canvas: Canvas, timer: PomodoroTimer, room_view: RoomView, frame: int, idle: bool = False,
         terminal: tuple[int, int] | None = None) -> None:
    """terminal: the whole screen's size, which defaults to the canvas plus the message line and toolbar."""
    columns, rows = terminal or (canvas.width, canvas.height + 2)
    if too_small(columns, rows):
        _too_small(canvas, timer, room_view, idle, columns, rows)
        return
    canvas.fill(0, 0, canvas.width, canvas.height, theme.ROOM_BG)
```

Replace:

```python
def room_point(
```

with:

```python
def too_small(columns: int, rows: int) -> bool:
    return columns < MIN_COLUMNS or rows < MIN_ROWS


def room_point(
```

Replace:

```python
# --- timer panel ------------------------------------------------------------
```

with:

```python
# --- too small ----------------------------------------------------------------


def _too_small(canvas: Canvas, timer: PomodoroTimer, room_view: RoomView, idle: bool, columns: int, rows: int) -> None:
    """A sad cat and a request for more room. The timer keeps going, so it's shown as text (spec §6)."""
    canvas.fill(0, 0, canvas.width, canvas.height, theme.PANEL_BG)
    if idle:
        clock, color = IDLE_LABEL, theme.IDLE
    else:
        clock = f"{view.phase_label(timer)}  {view.clock_text(timer.remaining())}  {view.phase_state(timer)}".rstrip()
        color = phase_color(timer)
    lines = [(TOO_SMALL[0], theme.TEXT, True), (TOO_SMALL[1].format(w=columns, h=rows), theme.DIM, False),
             ("", theme.DIM, False), (clock, color, True)]
    cat = sprites.cat("loaf", "meh")
    cat_rows = (len(cat) + 1) // 2 + 1  # and a blank row under it
    show_cat = canvas.height >= cat_rows + len(lines) and canvas.width >= len(cat[0])
    row = (canvas.height - len(lines) - (cat_rows if show_cat else 0)) // 2
    if show_cat:
        coat = room_view.roster[0].coat if room_view.roster else "tabby"
        canvas.sprite((canvas.width - len(cat[0])) // 2, row * 2, cat, sprites.COATS[coat])
        row += cat_rows
    for text, color, bold in lines:
        text = text[: canvas.width]
        canvas.text(max(0, (canvas.width - len(text)) // 2), row, text, color, bold=bold)
        row += 1


# --- timer panel ------------------------------------------------------------
```

- [ ] **Step 5: The app: hide the toolbar, switch the mouse off**

In `src/pomo/ui/app.py`:

Replace:

```python
    def draw_scene(self, canvas: Canvas) -> None:
        # The room on screen decides the geometry; below the minimum the cats keep the minimum room.
        room_w, room_h = canvas.width - scene.PANEL_WIDTH, canvas.height * 2
        self.world.fit(max(MIN_WIDTH, room_w), max(MIN_HEIGHT, room_h))
        scene.draw(canvas, self.session.timer, self.world.view(), self.frame, idle=self.session.idle)
```

with:

```python
    @property
    def too_small(self) -> bool:
        return scene.too_small(self.size.width, self.size.height)

    def draw_scene(self, canvas: Canvas) -> None:
        if not self.too_small:  # the room on screen decides the geometry; a too-small one leaves it as it was
            room_w, room_h = canvas.width - scene.PANEL_WIDTH, canvas.height * 2
            self.world.fit(max(MIN_WIDTH, room_w), max(MIN_HEIGHT, room_h))
        scene.draw(canvas, self.session.timer, self.world.view(), self.frame, idle=self.session.idle,
                   terminal=(self.size.width, self.size.height))
```

Replace:

```python
        self._sync_mode()
        self.main.toolbar.show(self.world.tool, {t for t in Tool if locked(t, self.world.mode)}, self.session.idle)
        self.main.show(self._message)
```

with:

```python
        self._sync_mode()
        toolbar = self.main.toolbar
        if toolbar.display == self.too_small:  # hidden while the window is too small, back when it grows
            toolbar.display = not self.too_small
            self.world.leave()
        toolbar.show(self.world.tool, {t for t in Tool if locked(t, self.world.mode)}, self.session.idle)
        self.main.show(self._message)
```

Replace:

```python
    def on_stage_pointer(self, message: Stage.Pointer) -> None:
        point = scene.room_point(message.col, message.row)
```

with:

```python
    def _room_point(self, col: float, row: float) -> tuple[float, float] | None:
        return None if self.too_small else scene.room_point(col, row)

    def on_stage_pointer(self, message: Stage.Pointer) -> None:
        point = self._room_point(message.col, message.row)
```

Replace:

```python
    def on_stage_pressed(self, message: Stage.Pressed) -> None:
        point = scene.room_point(message.col, message.row)
```

with:

```python
    def on_stage_pressed(self, message: Stage.Pressed) -> None:
        point = self._room_point(message.col, message.row)
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest -q`
Expected: `599 passed`

- [ ] **Step 7: Commit**

```bash
git add src/pomo/render/scene.py src/pomo/ui/app.py src/pomo/game/world.py tests/test_scene.py tests/test_app.py
git commit -m "feat: below 100x30 a sad cat asks for room; the timer stays on screen and keeps working" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: A line about Mango in every ping

**Files:**
- Modify: `src/pomo/notify.py`, `src/pomo/ui/view.py`, `src/pomo/ui/app.py`
- Test: `tests/test_notify.py`, `tests/test_view.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: `Cat.stage`, `NEEDS`, `NEED_ALERT`, and `Transition.started`.
- Produces:
  - `notify.ping_for(transition, cfg, cat_line: str = "") -> Ping`.
  - `view.WANTS`.
  - `view.cat_line(cats, starting: Phase) -> str`.

- [ ] **Step 1: Write the failing tests**

Append to the end of `tests/test_notify.py`:

```python
def test_the_cat_line_ends_the_ping():
    ping = ping_for(transition(Phase.FOCUS, Phase.SHORT_BREAK, 25), Config(), "Mango is waiting by the bowl.")
    assert ping.body == "25 minutes of focus complete. Time for a 5 min break. Mango is waiting by the bowl."
    ping = ping_for(transition(Phase.SHORT_BREAK, Phase.FOCUS, 5), Config(), "Mango is curling up for a nap.")
    assert ping.body.endswith("Time to focus for 25 minutes. Mango is curling up for a nap.")
```

In `tests/test_view.py`:

Replace:

```python
from pomo.clock import FakeClock
```

with:

```python
from pomo.clock import FakeClock
from pomo.game.cat import Cat, Trait
```

and append to the end of `tests/test_view.py`:

```python
# --- the cat line in pings (daily-driver addendum §5) -------------------------------

def a_cat(name="Mango", mood=80.0, **needs) -> Cat:
    return Cat(name, "tabby", Trait.CLINGY, mood=mood, needs={"hunger": 0.0, "play": 0.0, "affection": 0.0, **needs})


@pytest.mark.parametrize("cat, starting, line", [
    (a_cat(mood=30.0, hunger=90.0), Phase.SHORT_BREAK, "Mango is still sulking."),
    (a_cat(mood=10.0), Phase.FOCUS, "Mango is still sulking."),
    (a_cat(hunger=75.0, play=95.0), Phase.SHORT_BREAK, "Mango is waiting by the bowl."),
    (a_cat(play=75.0, affection=95.0), Phase.FOCUS, "Mango wants to play."),
    (a_cat(affection=75.0), Phase.FOCUS, "Mango could use some fuss."),
    (a_cat(hunger=70.0), Phase.LONG_BREAK, "Mango is stretching for playtime."),
    (a_cat(), Phase.FOCUS, "Mango is curling up for a nap."),
])
def test_the_cat_line_says_what_the_cat_needs_most(cat, starting, line):
    assert view.cat_line([cat], starting) == line


def test_the_cat_line_is_about_the_unhappiest_cat():
    cats = [a_cat("Mango", mood=80.0), a_cat("Pebble", mood=50.0, play=90.0), a_cat("Tux", mood=50.0)]
    assert view.cat_line(cats, Phase.FOCUS) == "Pebble wants to play."


def test_no_cats_no_line():
    assert view.cat_line([], Phase.FOCUS) == ""
```

Append to the end of `tests/test_app.py`:

```python
async def test_pings_end_with_a_line_about_mango():
    app, clock, notifier = make_app()
    async with app.run_test(size=SIZE) as pilot:
        app.world.cats[0].needs["hunger"] = 90
        await pilot.press("space")
        clock.advance(25 * MIN)
        app.tick()
        assert notifier.pings[-1].body.endswith("Time for a 5 min break. Mango is waiting by the bowl.")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_notify.py tests/test_view.py tests/test_app.py -q`
Expected: `11 failed, 107 passed`. `view` has no `cat_line`, `ping_for()` takes 2 positional arguments, and the app's ping has no line about Mango.

- [ ] **Step 3: The cat line**

In `src/pomo/notify.py`:

Replace:

```python
def ping_for(transition: Transition, cfg: Config) -> Ping:
    minutes = round(transition.ended_length_s / 60)
    if transition.ended is Phase.FOCUS:
        break_minutes = cfg.long_break if transition.started is Phase.LONG_BREAK else cfg.short_break
        return Ping(
            "🍅 Pomodoro done!",
            f"{minutes} minutes of focus complete. Time for a {break_minutes} min break.",
        )
    return Ping("☕ Break's over", f"{minutes} min break complete. Time to focus for {cfg.focus} minutes.")
```

with:

```python
def ping_for(transition: Transition, cfg: Config, cat_line: str = "") -> Ping:
    """The ping for a finished phase. cat_line, if any, ends the body (spec §9)."""
    minutes = round(transition.ended_length_s / 60)
    tail = f" {cat_line}" if cat_line else ""
    if transition.ended is Phase.FOCUS:
        break_minutes = cfg.long_break if transition.started is Phase.LONG_BREAK else cfg.short_break
        return Ping(
            "🍅 Pomodoro done!",
            f"{minutes} minutes of focus complete. Time for a {break_minutes} min break.{tail}",
        )
    return Ping("☕ Break's over", f"{minutes} min break complete. Time to focus for {cfg.focus} minutes.{tail}")
```

In `src/pomo/ui/view.py`:

Replace:

```python
from pomo.game.balance import PENALTIES
from pomo.game.cat import Cat
```

with:

```python
from pomo.game.balance import NEED_ALERT, PENALTIES
from pomo.game.cat import NEEDS, Cat
```

Replace:

```python
IDLE_OFF = "Back to pomodoro. Press space to start."
```

with:

```python
IDLE_OFF = "Back to pomodoro. Press space to start."
WANTS = {"hunger": "{} is waiting by the bowl.", "play": "{} wants to play.", "affection": "{} could use some fuss."}
```

Replace:

```python
def remembers(cats: Sequence[Cat]) -> str:
```

with:

```python
def cat_line(cats: Sequence[Cat], starting: Phase) -> str:
    """One line about the unhappiest cat, for the end of a ping (addendum §5)."""
    if not cats:
        return ""
    cat = min(cats, key=lambda c: c.mood)  # the first, on a tie
    if cat.stage.angry:
        return f"{cat.name} is still sulking."
    for need in NEEDS:  # food, then play, then affection
        if cat.needs[need] > NEED_ALERT:
            return WANTS[need].format(cat.name)
    return f"{cat.name} is stretching for playtime." if starting.is_break else f"{cat.name} is curling up for a nap."


def remembers(cats: Sequence[Cat]) -> str:
```

In `src/pomo/ui/app.py`, in `handle`:

Replace:

```python
            self.notifier.send(ping_for(finished[-1], self.config))
```

with:

```python
            last = finished[-1]
            self.notifier.send(ping_for(last, self.config, view.cat_line(self.world.cats, last.started)))
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -q`
Expected: `610 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pomo/notify.py src/pomo/ui/view.py src/pomo/ui/app.py tests/test_notify.py tests/test_view.py tests/test_app.py
git commit -m "feat: pings end with a line about the unhappiest cat" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: The six fixes deferred from milestone 4

**Files:**
- Replace: `src/pomo/ui/toolbar.py`
- Modify: `src/pomo/render/theme.py`, `src/pomo/ui/app.py`, `src/pomo/render/scene.py`, `src/pomo/game/world.py`
- Test: `tests/test_app.py`, `tests/test_scene.py`, `tests/test_care.py`

**Interfaces:**
- Consumes: Task 6's `PomoApp._room_point`, and milestone 4's toolbar and `World._cat_at`.
- Produces:
  - `scene.room_point(col, row, columns)`, which returns `None` on the top row and the last column.
  - `scene.KEY_HINTS_IDLE`.
  - `theme.BAR_BG` and `theme.css(color) -> str`.
  - Toolbar buttons `#mode-pomodoro` and `#mode-idle` (the old `#mode` and `MODE_LABELS` are gone).
  - `PomoApp.on_app_blur`.

- [ ] **Step 1: Update the tests that pin the old behaviour, and write the new ones**

In `tests/test_app.py`, the mode is two buttons now:

Replace:

```python
        assert label(app, "mode") == "🍅 Pomodoro"
```

with:

```python
        assert (label(app, "mode-pomodoro"), label(app, "mode-idle")) == ("🍅 Pomodoro", "💤 Idle")
        assert app.main.toolbar.query_one("#mode-pomodoro").has_class("-held")
```

Replace:

```python
        assert label(app, "mode") == "💤 Idle"
```

with:

```python
        assert app.main.toolbar.query_one("#mode-idle").has_class("-held")
```

Replace:

```python
async def test_the_mode_button_switches_to_idle():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.click("#mode")
        assert app.session.idle
```

with:

```python
async def test_the_mode_buttons_switch_between_pomodoro_and_idle():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.click("#mode-idle")
        assert app.session.idle
        await pilot.click("#mode-idle")  # the mode you're in: nothing happens
        assert app.session.idle
        await pilot.click("#mode-pomodoro")
        assert not app.session.idle
```

In `tests/test_scene.py`, the idle hints change and `room_point` learns the screen's width:

Replace:

```python
    for expected in ["● IDLE", "i to go back to pomodoro", "just hanging out", "Mango  ♥♥♥♥♡ content", "i idle"]:
```

with:

```python
    for expected in ["● IDLE", "i to go back to pomodoro", "just hanging out", "Mango  ♥♥♥♥♡ content",
                     "i back to pomodoro"]:
```

Replace:

```python
@pytest.mark.parametrize("col, row, point", [
    (35, 10, (5.0, 20.0)),
    (35.4, 10.5, (5.0, 21.0)),  # a terminal that reports pixels: the lower half of the cell
    (PANEL_WIDTH, 0, (0.0, 0.0)),
    (PANEL_WIDTH - 1, 10, None),  # over the timer panel
])
def test_room_point_maps_the_pointer_into_the_room(col, row, point):
    assert room_point(col, row) == point
```

with:

```python
@pytest.mark.parametrize("col, row, point", [
    (35, 10, (5.0, 20.0)),
    (35.4, 10.5, (5.0, 21.0)),  # a terminal that reports pixels: the lower half of the cell
    (PANEL_WIDTH, 1, (0.0, 2.0)),
    (98, 27, (68.0, 54.0)),
    (PANEL_WIDTH - 1, 10, None),  # over the timer panel
    (50, 0, None),  # the top row: on the way out of the window
    (99, 10, None),  # the last column: the same
])
def test_room_point_maps_the_pointer_into_the_room(col, row, point):
    assert room_point(col, row, 100) == point
```

In `tests/test_app.py`, the imports:

Replace:

```python
from textual.widgets import Static
```

with:

```python
from textual import events
from textual.widgets import Static
```

Append to the end of `tests/test_app.py`:

```python
# --- milestone 4's leftovers --------------------------------------------------------

async def test_a_mouse_move_to_the_same_spot_or_with_nothing_in_hand_redraws_nothing():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        redraws = []
        app._after_hand = lambda: redraws.append(1)
        await pilot.hover(Stage, offset=on_room(20, 20))
        await pilot.hover(Stage, offset=on_room(25, 20))
        assert redraws == [] and app.world.pointer == (25, 20)  # no tool: noted, not drawn
        await pilot.press("4")
        redraws.clear()
        await pilot.hover(Stage, offset=on_room(30, 20))
        await pilot.hover(Stage, offset=on_room(30, 20))
        assert redraws == [1]


async def test_sliding_out_across_the_top_or_right_edge_puts_the_string_away():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("3")
        await pilot.hover(Stage, offset=on_room(20, 20))
        assert app.world.string is not None
        await pilot.hover(Stage, offset=(50, 0))  # the top row
        assert app.world.string is None
        await pilot.hover(Stage, offset=on_room(20, 20))
        await pilot.hover(Stage, offset=(SIZE[0] - 1, 10))  # the last column
        assert app.world.string is None


async def test_switching_to_another_window_puts_the_hand_away():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("4")
        await pilot.hover(Stage, offset=on_room(20, 20))
        app.post_message(events.AppBlur())
        await pilot.pause()
        assert app.world.pointer is None
        assert app.world.view().cursor is None


async def test_clicking_idle_mid_focus_asks_first_like_i_does():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        await pilot.click("#mode-idle")
        assert isinstance(app.screen, ConfirmScreen)


async def test_the_bars_are_the_theme_colour():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        assert app.main.toolbar.styles.background.rgb == theme.BAR_BG
        assert app.main.query_one("#message").styles.background.rgb == theme.BAR_BG


def test_colours_live_only_in_the_theme():
    import pathlib
    import re
    ui = pathlib.Path(view.__file__).parent
    for source in sorted(ui.glob("*.py")):
        assert re.findall(r"#[0-9a-fA-F]{6}\b", source.read_text()) == [], source.name
```

Append to the end of `tests/test_scene.py`:

```python
def test_idle_hints_drop_the_timer_keys(timer):
    canvas = Canvas(W, H, (0, 0, 0))
    draw(canvas, timer, RoomView(), 1, idle=True)
    text = screen_text(canvas)
    for hint in ["i back to pomodoro", "1-5 tools  esc drop", "q quit"]:
        assert hint in text
    assert "space start/pause" not in text


def test_theme_colours_can_be_written_as_css():
    assert theme.css((26, 28, 40)) == "#1a1c28"
```

Append to the end of `tests/test_care.py`:

```python
def test_the_hand_stops_patting_when_the_cat_walks_out_from_under_it():
    world = room("Mango")
    world.hold(Tool.PET)
    world.point(38, 50)
    assert world.view().cursor.busy
    world.bodies["Mango"].x = 15  # off it goes, while the hand rests
    world.tick(TICK)
    assert not world.view().cursor.busy
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_app.py tests/test_scene.py tests/test_care.py -q`
Expected: `20 failed, 139 passed`. The failures are the missing `#mode-pomodoro`/`#mode-idle` buttons, `room_point` taking only two arguments, the idle hints, the redraw and edge checks, the hex colour still in `app.py`, and the hand still patting.

- [ ] **Step 3: The bar colour in the theme**

In `src/pomo/render/theme.py`:

Replace:

```python
def hex_rgb(value: str) -> RGB:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
```

with:

```python
def hex_rgb(value: str) -> RGB:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def css(color: RGB) -> str:
    """A colour for Textual CSS, which the widgets around the canvas are styled with."""
    return "#{:02x}{:02x}{:02x}".format(*color)
```

Replace:

```python
# screen
ROOM_BG = hex_rgb("#15161e")
```

with:

```python
# screen
ROOM_BG = hex_rgb("#15161e")
BAR_BG = hex_rgb("#1a1c28")  # the message line and the toolbar
```

- [ ] **Step 4: Two mode buttons**

Replace all of `src/pomo/ui/toolbar.py` with:

```python
"""The care toolbar under the message line (spec §5.2, §6): a button per tool, and Pomodoro ↔ Idle."""

from __future__ import annotations

from collections.abc import Set

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button

from pomo.game.tools import Tool
from pomo.render.theme import BAR_BG, css

TOOLS = (  # tool, key, icon, name
    (Tool.FEED, "1", "🍗", "Feed"),
    (Tool.BALL, "2", "🧶", "Ball"),
    (Tool.STRING, "3", "🧵", "String"),
    (Tool.PET, "4", "✋", "Pet"),
    (Tool.SCOOP, "5", "🧹", "Scoop"),
)
LOCK = "🔒"


class ToolButton(Button, can_focus=False):
    """Never takes keyboard focus, so space and the number keys always reach the app."""


class Toolbar(Horizontal):
    DEFAULT_CSS = f"""
    Toolbar {{ height: 1; background: {css(BAR_BG)}; padding: 0 1; }}
    Toolbar ToolButton {{ min-width: 0; margin-right: 1; }}
    Toolbar ToolButton.-held {{ background: $primary; text-style: bold; }}
    Toolbar ToolButton.-locked {{ color: $text-muted; }}
    Toolbar #modes {{ dock: right; width: auto; height: 1; }}
    Toolbar #modes ToolButton {{ margin: 0 0 0 1; }}
    """

    class Picked(Message):
        def __init__(self, tool: Tool) -> None:
            super().__init__()
            self.tool = tool

    class ModeToggled(Message):
        """The mode you're not in was clicked: Pomodoro or Idle."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._shown: tuple | None = None
        self._idle = False

    def compose(self) -> ComposeResult:
        for tool, key, icon, name in TOOLS:
            yield ToolButton(f"{key} {icon} {name}", id=f"tool-{tool.value}", compact=True)
        with Horizontal(id="modes"):  # both modes, the current one highlighted
            yield ToolButton("🍅 Pomodoro", id="mode-pomodoro", compact=True)
            yield ToolButton("💤 Idle", id="mode-idle", compact=True)

    def show(self, held: Tool | None, locked: Set[Tool], idle: bool) -> None:
        """Mark the tool in hand, the locked ones and the mode. Touches nothing if nothing changed."""
        state = (held, frozenset(locked), idle)
        if state == self._shown:
            return
        self._shown, self._idle = state, idle
        for tool, key, icon, name in TOOLS:
            button = self.query_one(f"#tool-{tool.value}", ToolButton)
            button.label = f"{key} {LOCK if tool in locked else icon} {name}"
            button.set_class(tool is held, "-held")
            button.set_class(tool in locked, "-locked")
        self.query_one("#mode-pomodoro", ToolButton).set_class(not idle, "-held")
        self.query_one("#mode-idle", ToolButton).set_class(idle, "-held")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        button = event.button.id or ""
        if button.startswith("mode-"):
            if (button == "mode-idle") != self._idle:  # the current mode's button does nothing
                self.post_message(self.ModeToggled())
        else:
            self.post_message(self.Picked(Tool(button.removeprefix("tool-"))))
```

- [ ] **Step 5: The app: the theme colour, quieter mouse moves, the window's edges and blur**

In `src/pomo/ui/app.py`:

Replace:

```python
    DEFAULT_CSS = """
    TimerScreen { layout: vertical; }
    #message { height: 1; padding: 0 2; color: $warning; background: #1a1c28; }
    """
```

with:

```python
    DEFAULT_CSS = f"""
    TimerScreen {{ layout: vertical; }}
    #message {{ height: 1; padding: 0 2; color: $warning; background: {theme.css(theme.BAR_BG)}; }}
    """
```

Replace:

```python
from pomo.render import scene
```

with:

```python
from pomo.render import scene, theme
```

Replace:

```python
from textual.app import App, ComposeResult
```

with:

```python
from textual import events
from textual.app import App, ComposeResult
```

Replace:

```python
    def _room_point(self, col: float, row: float) -> tuple[float, float] | None:
        return None if self.too_small else scene.room_point(col, row)

    def on_stage_pointer(self, message: Stage.Pointer) -> None:
        point = self._room_point(message.col, message.row)
        if point is None:
            self.world.leave()  # over the timer panel
        else:
            self.world.point(*point)
        self._after_hand()
```

with:

```python
    def _room_point(self, col: float, row: float) -> tuple[float, float] | None:
        return None if self.too_small else scene.room_point(col, row, self.size.width)

    def on_stage_pointer(self, message: Stage.Pointer) -> None:
        point = self._room_point(message.col, message.row)
        if point == self.world.pointer:
            return  # the same spot again: terminals that report pixels send plenty of these
        if point is None:
            self.world.leave()  # over the timer panel, or on the window's edge on the way out
        else:
            self.world.point(*point)
        if self.world.tool is not None:  # with nothing in hand there's nothing to redraw
            self._after_hand()

    def on_app_blur(self, event: events.AppBlur) -> None:
        self.world.leave()  # another window in front: put the hand and the string away
        self._after_hand()
```

- [ ] **Step 6: The scene: idle hints, and the edges count as outside**

In `src/pomo/render/scene.py`:

Replace:

```python
KEY_HINTS = ("space start/pause   s skip", "r reset  +/- 5 min  q quit", "1-5 tools  esc drop  i idle")
```

with:

```python
KEY_HINTS = ("space start/pause   s skip", "r reset  +/- 5 min  q quit", "1-5 tools  esc drop  i idle")
KEY_HINTS_IDLE = ("i back to pomodoro", "1-5 tools  esc drop", "q quit")  # the timer keys do nothing in Idle
```

Replace:

```python
def room_point(col: float, row: float) -> tuple[float, float] | None:
    """Where a pointer at (col, row) on screen is in the room: a column and a pixel row. None over the panel.
    Terminals that report the pointer finer than a cell give the half-cell too."""
    if col < PANEL_WIDTH:
        return None
    return float(int(col) - PANEL_WIDTH), float(int(row * 2))
```

with:

```python
def room_point(col: float, row: float, columns: int) -> tuple[float, float] | None:
    """Where a pointer at (col, row) on a screen this many columns wide is in the room: a column and a pixel
    row. Terminals that report the pointer finer than a cell give the half-cell too. None over the panel,
    and on the screen's top row and last column: Textual never says when the mouse leaves the window, so
    the edge it crosses on the way out counts as outside."""
    if col < PANEL_WIDTH or row < 1 or col >= columns - 1:
        return None
    return float(int(col) - PANEL_WIDTH), float(int(row * 2))
```

Replace:

```python
    _roster(canvas, roster)
    first_hint_row = canvas.height - len(KEY_HINTS) - 1
    for i, hint in enumerate(KEY_HINTS):
        _panel_text(canvas, first_hint_row + i, hint, theme.DIM)
```

with:

```python
    _roster(canvas, roster)
    hints = KEY_HINTS_IDLE if idle else KEY_HINTS
    first_hint_row = canvas.height - len(hints) - 1
    for i, hint in enumerate(hints):
        _panel_text(canvas, first_hint_row + i, hint, theme.DIM)
```

- [ ] **Step 7: The hand re-checks the cat under it**

In `src/pomo/game/world.py`, in `World.tick`:

Replace:

```python
        for effect in self.effects:
            effect.age += dt
```

with:

```python
        if self.tool is Tool.PET and self.pointer is not None:
            under = self._cat_at(*self.pointer)
            if under is not self._petting:  # the cat walked out from under a resting hand: it stops patting
                self._petting, self._stroked = under, 0.0
        for effect in self.effects:
            effect.age += dt
```

- [ ] **Step 8: Run the tests**

Run: `uv run pytest -q`
Expected: `622 passed`

- [ ] **Step 9: Try it in a real terminal**

Run the real app in a pseudo-terminal at 100×30, then:
1. Quit with `q` and relaunch: Mango's mood and your place in the set come back.
2. Start a focus and kill the process, then relaunch: *"Mango remembers you left."* and −25.
3. A second `pomo` while one runs prints *"pomo is already running in another window."* and exits 1.
4. Shrink to 80×24: the too-small screen, with the timer still ticking.
5. `pomo --init` then `pomo --test-ping` with a fake topic, against your own XDG dirs in a temporary directory. Never touch the real `~/.config`.

- [ ] **Step 10: Commit**

```bash
git add src/pomo/ui/toolbar.py src/pomo/render/theme.py src/pomo/ui/app.py src/pomo/render/scene.py src/pomo/game/world.py tests/test_app.py tests/test_scene.py tests/test_care.py
git commit -m "fix: milestone 4's leftovers: quieter mouse moves, window edges, idle hints, mode buttons, bar colour, patting" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
