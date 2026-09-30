import pytest

from pomo.game.cat import Cat, Stage, Trait
from pomo.game.events import BreakCompleted, FocusCompleted, RuleBreak, RuleKind, SetCompleted
from pomo.timer import Phase

HOUR = 3600.0


def cat(trait=Trait.CLINGY, mood=80.0) -> Cat:
    c = Cat("Mango", "tabby", trait)
    c.mood = mood
    return c


def run(c: Cat, seconds: float, step: float = 1.0) -> None:
    for _ in range(int(seconds / step)):
        c.tick(step)


def test_a_new_cat_is_content_and_wants_nothing():
    c = Cat("Mango", "tabby", Trait.CLINGY)
    assert (c.mood, c.stage, c.hearts, c.wants()) == (80, Stage.CONTENT, 4, None)


@pytest.mark.parametrize("mood, stage", [
    (100, Stage.CONTENT), (70, Stage.CONTENT), (69.9, Stage.GRUMPY), (40, Stage.GRUMPY),
    (39.9, Stage.PISSY), (15, Stage.PISSY), (14.9, Stage.FURIOUS), (0, Stage.FURIOUS),
])
def test_stages(mood, stage):
    assert cat(mood=mood).stage is stage


@pytest.mark.parametrize("mood, hearts", [(100, 5), (99, 4), (80, 4), (40, 2), (19, 0), (0, 0)])
def test_hearts(mood, hearts):
    assert cat(mood=mood).hearts == hearts


@pytest.mark.parametrize("kind, lost", [
    (RuleKind.ABANDON_FOCUS, 25), (RuleKind.SKIP_BREAK, 20), (RuleKind.LONG_PAUSE, 10),
])
def test_rule_breaks_cost_mood(kind, lost):
    c = cat()
    c.apply(RuleBreak(kind))
    assert c.mood == 80 - lost


def test_traits_scale_the_penalties():
    chill, diva, gremlin = cat(Trait.CHILL), cat(Trait.DIVA), cat(Trait.GREMLIN)
    for c in (chill, diva, gremlin):
        c.apply(RuleBreak(RuleKind.SKIP_BREAK))
    assert (chill.mood, diva.mood, gremlin.mood) == (70, 50, 60)


def test_mood_never_leaves_0_to_100():
    c = cat(mood=10)
    c.apply(RuleBreak(RuleKind.ABANDON_FOCUS))
    assert c.mood == 0
    c = cat(mood=95)
    c.apply(FocusCompleted(25))
    assert c.mood == 100


def test_finished_focus_and_breaks_cheer_cats_up():
    c = cat(mood=50)
    c.apply(FocusCompleted(25))
    c.apply(BreakCompleted(Phase.SHORT_BREAK))
    assert c.mood == 65


def test_a_focus_shorter_than_15_minutes_earns_no_mood():
    c = cat(mood=50)
    c.apply(FocusCompleted(10))
    assert c.mood == 50


def test_other_events_leave_the_mood_alone():
    c = cat(mood=50)
    c.apply(SetCompleted())
    assert c.mood == 50


@pytest.mark.parametrize("need, hours", [("hunger", 3), ("play", 2), ("affection", 2.5)])
def test_needs_fill_up_over_runtime(need, hours):
    c = cat(Trait.CHILL)
    run(c, hours * HOUR / 2, step=60)
    assert c.needs[need] == pytest.approx(50)
    run(c, hours * HOUR, step=60)
    assert c.needs[need] == 100


def test_clingy_cats_want_affection_sooner():
    clingy, chill = cat(Trait.CLINGY), cat(Trait.CHILL)
    for c in (clingy, chill):
        run(c, HOUR, step=60)
    assert clingy.needs["affection"] == pytest.approx(chill.needs["affection"] * 1.5)


def test_wants_names_the_most_urgent_need_over_70():
    c = cat()
    c.needs.update(hunger=65, play=90, affection=75)
    assert c.wants() == "play"
    c.needs.update(play=60, affection=60)
    assert c.wants() is None


def test_unmet_needs_sour_the_mood_but_never_past_grumpy():
    c = cat(mood=80)
    c.needs.update(hunger=100)
    run(c, 10 * 60)
    assert c.mood == pytest.approx(70, abs=0.2)  # about 1 per minute
    run(c, 2 * HOUR, step=5)
    assert c.mood == pytest.approx(40, abs=0.05)
    assert c.stage is Stage.GRUMPY


def test_unmet_needs_cannot_make_an_angry_cat_angrier():
    c = cat(mood=30)
    c.needs.update(hunger=100)
    run(c, 10 * 60)
    assert c.mood == pytest.approx(31)  # only the slow cooling


def test_anger_cools_slowly_and_only_up_to_content():
    c = cat(mood=50)
    run(c, 10 * 60)
    assert c.mood == pytest.approx(51)
    c = cat(mood=69.5)
    run(c, HOUR, step=10)
    assert c.mood == 70


def test_eating_fixes_hunger_and_cheers_up_calm_cats_only():
    content, pissy = cat(mood=60), cat(mood=30)
    for c in (content, pissy):
        c.needs["hunger"] = 90
        c.eat()
        assert c.needs["hunger"] == 0
    assert (content.mood, pissy.mood) == (63, 30)
