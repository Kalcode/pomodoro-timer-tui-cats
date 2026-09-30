import pytest

from pomo.game.cat import Cat, Petting, Stage, Trait
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


class FixedRandom:
    """Stands in for random.Random: every roll comes out the same."""

    def __init__(self, value: float):
        self.value = value

    def random(self) -> float:
        return self.value


NO_SWAT, SWAT = FixedRandom(0.99), FixedRandom(0.1)


def test_a_stroke_meets_affection_and_a_content_cat_purrs():
    c = cat()
    c.needs["affection"] = 60.0
    assert c.pet(NO_SWAT) is Petting.PURR
    assert (c.needs["affection"], c.mood) == (35, 82)


def test_a_stroke_pays_only_for_the_affection_it_meets():
    c = cat()
    c.needs["affection"] = 10.0
    c.pet(NO_SWAT)
    assert c.needs["affection"] == 0
    assert c.mood == pytest.approx(80.8)


def test_a_petting_session_tops_out_at_8_mood():
    c = cat()
    c.needs["affection"] = 100.0
    for _ in range(10):
        c.pet(NO_SWAT)
    assert c.mood == 88


def test_petting_a_satisfied_cat_can_earn_a_swat():
    c = cat()
    c.needs["affection"] = 5.0
    assert c.pet(SWAT) is Petting.SWAT
    assert (c.needs["affection"], c.mood) == (5, 78)


def test_a_satisfied_cat_that_doesnt_swat_still_purrs():
    c = cat()
    c.needs["affection"] = 5.0
    assert c.pet(NO_SWAT) is Petting.PURR
    assert c.needs["affection"] == 0


def test_only_a_satisfied_cat_swats():
    c = cat()
    c.needs["affection"] = 10.0
    assert c.pet(SWAT) is Petting.PURR


def test_a_grumpy_cat_tolerates_petting():
    c = cat(mood=50.0)
    c.needs["affection"] = 50.0
    assert c.pet(NO_SWAT) is Petting.TOLERATE
    assert (c.needs["affection"], c.mood) == (25, 52)


@pytest.mark.parametrize("mood", [30.0, 10.0])
def test_pissy_and_furious_cats_hiss_and_nothing_changes(mood):
    c = cat(mood=mood)
    c.needs["affection"] = 90.0
    assert c.pet(NO_SWAT) is Petting.HISS
    assert (c.needs["affection"], c.mood) == (90, mood)


def test_playing_meets_play_and_cheers_the_cat_up():
    c = cat()
    c.needs["play"] = 80.0
    c.play()
    assert (c.needs["play"], c.mood) == (30, 85)


def test_playing_pays_only_for_the_play_it_meets():
    c = cat()
    c.needs["play"] = 10.0
    c.play()
    assert (c.needs["play"], c.mood) == (0, 81)


def test_an_angry_cat_made_to_play_gets_no_cheer():
    c = cat(mood=30.0)
    c.needs["play"] = 80.0
    c.play()
    assert (c.needs["play"], c.mood) == (30, 30)


@pytest.mark.parametrize("mood, play, interest", [
    (80.0, 0.0, 0.3), (80.0, 50.0, 0.8), (80.0, 90.0, 1.0),
    (50.0, 50.0, 0.4), (30.0, 90.0, 0.0), (10.0, 90.0, 0.0),
])
def test_how_likely_a_cat_is_to_go_for_a_toy(mood, play, interest):
    c = cat(mood=mood)
    c.needs["play"] = play
    assert c.toy_interest() == pytest.approx(interest)
