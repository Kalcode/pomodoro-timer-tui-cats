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


def test_phase_label_and_state(timer, clock):
    assert (view.phase_label(timer), view.phase_state(timer)) == ("● FOCUS", "space to start")
    timer.start()
    assert view.phase_state(timer) == ""
    clock.advance(1)
    timer.pause()
    assert view.phase_state(timer) == "paused"
    timer.skip()
    assert view.phase_label(timer) == "● SHORT BREAK"


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


def test_big_sets_skip_the_dots_so_the_line_fits_the_panel(clock):
    timer = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 9), clock)
    assert view.count_line(timer) == "pomodoro 1 of 9"
    timer = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 8), clock)
    assert view.count_line(timer) == "pomodoro 1 of 8  ○○○○○○○○"


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


def test_confirm_question_for_going_idle(timer):
    timer.start()
    assert view.confirm_question(timer, Action.IDLE, RuleKind.ABANDON_FOCUS) == (
        "Switch to Idle in the middle of a focus? The cats will be upset (−25)."
    )
