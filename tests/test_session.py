import pytest

from pomo.clock import FakeClock
from pomo.game.events import BreakCompleted, FocusCompleted, RuleBreak, RuleKind, SetCompleted
from pomo.session import Action, Session, SessionState
from pomo.timer import Phase, TimerSettings, Transition

MIN = 60.0
HOUR = 3600.0


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


def test_idle_costs_what_a_reset_costs(session, clock):
    assert session.rule_cost(Action.IDLE) is None  # focus not started
    session.toggle()
    assert session.rule_cost(Action.IDLE) is RuleKind.ABANDON_FOCUS
    clock.advance(1)
    session.toggle()  # paused is still mid-focus
    assert session.rule_cost(Action.IDLE) is RuleKind.ABANDON_FOCUS
    session.toggle()
    finish(session, clock)
    assert session.rule_cost(Action.IDLE) is None  # a break


def test_going_idle_mid_focus_abandons_it(session, clock):
    session.toggle()
    clock.advance(5 * MIN)
    assert session.enter_idle() == [RuleBreak(RuleKind.ABANDON_FOCUS)]
    assert session.idle
    assert (session.timer.phase, session.timer.started, session.timer.remaining()) == (Phase.FOCUS, False, 25 * MIN)


def test_going_idle_before_starting_is_free(session):
    assert session.enter_idle() == []
    assert session.idle


def test_going_idle_on_a_break_is_free_and_the_break_waits(session, clock):
    finish(session, clock)
    clock.advance(2 * MIN)
    assert session.enter_idle() == []
    session.leave_idle()
    assert not session.idle
    assert (session.timer.phase, session.timer.started, session.timer.remaining()) == (
        Phase.SHORT_BREAK, False, 5 * MIN)


def test_the_timer_is_put_away_while_idle(session, clock):
    session.enter_idle()
    session.toggle()
    session.adjust(5)
    assert session.skip() == []
    assert session.reset() == []
    clock.advance(30 * MIN)
    assert session.tick() == []
    assert (session.timer.phase, session.timer.started, session.timer.remaining()) == (Phase.FOCUS, False, 25 * MIN)


def test_after_idle_the_timer_works_again(session, clock):
    session.enter_idle()
    session.leave_idle()
    session.toggle()
    clock.advance(MIN)
    session.tick()
    assert session.timer.remaining() == 24 * MIN


def test_going_idle_twice_changes_nothing(session, clock):
    session.toggle()
    session.enter_idle()
    assert session.enter_idle() == []


def test_going_idle_mid_focus_loses_the_set_bonus(session, clock):
    session.toggle()
    session.enter_idle()
    session.leave_idle()
    events = []
    for _ in range(7):
        events += finish(session, clock)
    assert session.timer.phase is Phase.LONG_BREAK
    assert SetCompleted() not in events


def test_idling_through_the_rest_of_a_break_comes_back_to_a_ready_focus(session, clock):
    finish(session, clock)  # the focus: the break starts on its own
    clock.advance(1 * MIN)
    session.enter_idle()
    clock.advance(4 * MIN)  # as long as was left of the break
    events = session.leave_idle()
    assert (session.timer.phase, session.timer.started) == (Phase.FOCUS, False)
    assert [e for e in events if isinstance(e, (BreakCompleted, RuleBreak))] == []  # no reward, no penalty


def test_a_short_idle_on_a_break_comes_back_to_the_break(session, clock):
    finish(session, clock)
    clock.advance(1 * MIN)
    session.enter_idle()
    clock.advance(3 * MIN)
    assert session.leave_idle() == []
    assert (session.timer.phase, session.timer.started) == (Phase.SHORT_BREAK, False)


def test_a_long_idle_during_a_focus_still_comes_back_to_the_focus(session, clock):
    session.enter_idle()
    clock.advance(60 * MIN)
    session.leave_idle()
    assert (session.timer.phase, session.timer.started) == (Phase.FOCUS, False)


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


# --- waiting for you between phases ---------------------------------------------------

@pytest.fixture
def waits(clock):
    return Session(TimerSettings.from_minutes(25, 5, 15, 4, auto_continue=False), clock)


def test_a_finished_phase_leaves_the_next_one_waiting_until_space(waits, clock):
    assert not waits.waiting  # a ready focus at launch isn't a phase change to acknowledge
    finish(waits, clock)
    assert waits.waiting and not waits.timer.running
    waits.toggle()
    assert not waits.waiting and waits.timer.running


def test_skipping_leaves_the_next_phase_waiting(waits, clock):
    waits.toggle()
    clock.advance(MIN)
    waits.skip()
    assert waits.waiting and waits.timer.phase is Phase.SHORT_BREAK


def test_with_auto_continue_nothing_waits(session, clock):
    finish(session, clock)
    assert not session.waiting and session.timer.running


def test_a_break_you_havent_started_doesnt_tick_down_while_closed(waits, clock):
    finish(waits, clock)
    assert waits.state().break_left is None
    fresh, events = restored(waits.state(), closed_for=HOUR)
    assert events == []
    assert fresh.timer.phase is Phase.SHORT_BREAK


def test_a_break_you_havent_started_doesnt_tick_down_in_idle(waits, clock):
    finish(waits, clock)
    waits.enter_idle()
    clock.advance(HOUR)
    assert waits.leave_idle() == []
    assert waits.timer.phase is Phase.SHORT_BREAK


def test_resetting_or_going_idle_ends_the_wait(waits, clock):
    finish(waits, clock)
    waits.reset()
    assert not waits.waiting
    finish(waits, clock)  # the break
    waits.enter_idle()
    assert not waits.waiting
