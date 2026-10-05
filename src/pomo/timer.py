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
    auto_continue: bool = True  # False: each new phase waits for you to start it

    @classmethod
    def from_minutes(cls, focus: int, short_break: int, long_break: int, long_every: int,
                     auto_continue: bool = True) -> TimerSettings:
        return cls(focus * 60.0, short_break * 60.0, long_break * 60.0, long_every, auto_continue)


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
            # The next phase starts exactly when the last ended, or waits for you to start it.
            self._ends_at = ended_at + self._length if self._settings.auto_continue else None
        return transitions

    def skip(self) -> Transition:
        was_running = self.running
        transition = self._advance(completed=False)
        carry_on = was_running and self._settings.auto_continue
        self._ends_at = self._clock.now() + self._length if carry_on else None
        return transition

    def reset(self) -> None:
        """Back to the full, unadjusted length of the current phase, stopped."""
        self._length = self.base_length(self._phase)
        self._remaining = self._length
        self._ends_at = None

    def restore(self, phase: Phase, focus_in_set: int) -> None:
        """Pick up a saved session: this phase, ready to start, at today's lengths."""
        top = self._settings.long_every if phase is Phase.LONG_BREAK else self._settings.long_every - 1
        self._phase = phase
        self._focus_in_set = min(max(0, focus_in_set), top)
        self.reset()

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
