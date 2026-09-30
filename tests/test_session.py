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
