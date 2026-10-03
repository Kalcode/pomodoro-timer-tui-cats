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


def test_restore_picks_up_a_phase_ready_at_todays_length(timer):
    timer.restore(Phase.SHORT_BREAK, 2)
    assert (timer.phase, timer.focus_in_set, timer.started, timer.remaining()) == (Phase.SHORT_BREAK, 2, False, 5 * MIN)


@pytest.mark.parametrize("phase, saved, kept", [
    (Phase.FOCUS, 9, 3), (Phase.SHORT_BREAK, 9, 3), (Phase.LONG_BREAK, 9, 4), (Phase.FOCUS, -2, 0),
])
def test_restore_keeps_the_count_inside_todays_set(timer, phase, saved, kept):
    timer.restore(phase, saved)  # long_every is 4: a long break shows 4 of 4, anything else at most 3
    assert timer.focus_in_set == kept
