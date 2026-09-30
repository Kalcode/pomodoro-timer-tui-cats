"""The timer plus the rules: user actions in, events out (spec §3.1–§3.2).

Idle mode (spec §2, §3.1) lives here too: going idle resets the phase, which costs
what a reset costs, and puts the timer away until you come back to it.
"""

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
    IDLE = "idle"


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
        return self._break_rule(self.rule_cost(Action.QUIT))

    def enter_idle(self) -> list[Event]:
        """Reset the phase and put the timer away. Mid-focus, that's abandoning it."""
        events = self.reset()
        self.idle = True
        return events

    def leave_idle(self) -> None:
        """Back to pomodoro: the phase that was reset waits, ready to start."""
        self.idle = False

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
