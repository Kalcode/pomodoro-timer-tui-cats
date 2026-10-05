import pytest

from pomo.clock import FakeClock
from pomo.game.cat import Cat, Trait
from pomo.game.events import Fed, FocusCompleted, Petted, Played, RuleBreak, RuleKind, SetCompleted
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


@pytest.mark.parametrize("event, text", [
    (Fed(), "Kibble's in the bowl."),
    (Fed(already_full=True), "The bowl is already full."),
    (Petted("Mango", "hiss"), "Mango hisses at your hand. Not now."),
    (Petted("Mango", "swat"), "Mango swats your hand. That's enough petting."),
    (Played("Mango", "ball"), "Mango had a good play with the yarn ball."),
    (Played("Mango", "string"), "Mango had a good play with the string."),
])
def test_describe_what_happens_in_the_room(event, text):
    assert view.describe(event) == text


@pytest.mark.parametrize("how", ["purr", "tolerate"])
def test_a_happy_stroke_needs_no_words(how):
    assert view.describe(Petted("Mango", how)) is None


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


def test_a_waiting_phase_says_so(timer, clock):
    timer.start()
    clock.advance(25 * 60)
    timer.tick()  # an auto-continuing timer: pause it to stand in for a waiting break
    timer.pause()
    assert view.phase_state(timer, waiting=True) == "break time: space to start"
    timer.skip()
    assert view.phase_state(timer, waiting=True) == "focus time: space to start"
    assert view.phase_state(timer) == "space to start"


def test_messages_for_a_phase_that_waits_for_you():
    focus_done = Transition(Phase.FOCUS, Phase.SHORT_BREAK, True, 1500, 1)
    break_done = Transition(Phase.SHORT_BREAK, Phase.FOCUS, True, 300, 1)
    assert view.describe(focus_done, waits=True) == "Focus complete. Break time! Press space to start your break."
    assert view.describe(break_done, waits=True) == "Break's over. Press space when you're ready to focus."
    assert view.describe(focus_done) == "Focus complete. Time for a break!"
