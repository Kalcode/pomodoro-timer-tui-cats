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
MAX_DOTS = 8  # keeps the count line inside the 30-column panel


def clock_text(seconds: float) -> str:
    """MM:SS, rounded up so it reads 25:00 until a whole second has passed and 00:00 only at the end."""
    total = math.ceil(max(0.0, seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def phase_label(timer: PomodoroTimer) -> str:
    return f"● {PHASE_NAMES[timer.phase]}"


def phase_state(timer: PomodoroTimer) -> str:
    """Shown under the phase name while the timer isn't running."""
    if timer.running:
        return ""
    return "paused" if timer.started else "space to start"


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
        Action.IDLE: "Switch to Idle in the middle of a focus?",
    }[action]
    return f"{question} The cats will be upset (−{PENALTIES[cost]})."
