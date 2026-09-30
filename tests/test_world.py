import random

import pytest

from pomo.game.behavior import Doing, Mode, walkable
from pomo.game.cat import Cat, Trait
from pomo.game.events import RuleBreak, RuleKind
from pomo.game.world import World, mode_for
from pomo.timer import Phase

TICK = 0.125


def world_with(*names: str, seed: int = 1, width: int = 70, height: int = 58) -> World:
    cats = [Cat(name, "tabby", Trait.CLINGY) for name in names]
    return World(cats, random.Random(seed), width, height)


def run(world: World, seconds: float, each=None) -> None:
    for _ in range(int(seconds / TICK)):
        world.tick(TICK)
        if each:
            each(world)


def test_a_new_room_has_its_cats_sitting_on_the_floor():
    world = world_with("Mango")
    view = world.view()
    (mango,) = view.cats
    assert (mango.name, mango.pose, mango.face, mango.feet) == ("Mango", "sit", "ok", world.scape.floor.y)
    assert [(r.name, r.hearts, r.stage) for r in view.roster] == [("Mango", 4, "content")]
    assert view.bowl_full


def test_cats_start_spaced_apart():
    world = world_with("Mango", "Pebble")
    xs = [c.x for c in world.view().cats]
    assert xs[1] - xs[0] >= 17


def test_rule_breaks_and_rewards_reach_every_cat():
    world = world_with("Mango", "Pebble")
    world.apply([RuleBreak(RuleKind.SKIP_BREAK)])
    assert [c.mood for c in world.cats] == [60, 60]
    assert [r.stage for r in world.view().roster] == ["grumpy", "grumpy"]


@pytest.mark.parametrize("phase, started, mode", [
    (Phase.FOCUS, False, Mode.RELAX), (Phase.FOCUS, True, Mode.NAP),
    (Phase.SHORT_BREAK, False, Mode.PLAY), (Phase.LONG_BREAK, True, Mode.PLAY),
])
def test_the_phase_sets_the_mode(phase, started, mode):
    assert mode_for(phase, started) is mode


@pytest.mark.parametrize("seed", range(3))
def test_cats_keep_moving_around_and_stay_in_the_room(seed):
    world = world_with("Mango", "Pebble", seed=seed)
    world.set_mode(Mode.PLAY)
    visited = set()

    def check(w: World):
        for view in w.view().cats:
            assert -10 <= view.x <= w.scape.width + 10
            assert 0 <= view.feet <= w.scape.floor.y
        visited.update(body.surface for body in w.bodies.values())

    run(world, 20 * 60, check)
    assert visited == {"floor", "tree_mid", "tree_top", "shelf"}


def test_focus_is_mostly_nap_time():
    world = world_with("Mango", seed=4)
    world.set_mode(Mode.NAP)
    faces = []
    run(world, 30 * 60, lambda w: faces.append(w.view().cats[0].face if w.view().cats else "away"))
    assert faces.count("sleep") / len(faces) > 0.5


def test_a_break_wakes_the_nappers():
    world = world_with("Mango", seed=5)
    world.set_mode(Mode.NAP)
    for _ in range(20000):
        world.tick(TICK)
        if world.view().cats and world.view().cats[0].face == "sleep":
            break
    assert world.view().cats[0].face == "sleep"
    world.set_mode(Mode.PLAY)
    world.tick(TICK)
    assert world.view().cats[0].face != "sleep"


def test_a_hungry_cat_eats_and_the_next_one_begs():
    world = world_with("Mango", "Pebble", seed=6)
    for cat in world.cats:
        cat.needs["hunger"] = 90
    bubbles = set()
    run(world, 60, lambda w: bubbles.update(c.bubble for c in w.view().cats))
    assert not world.bowl_full
    assert sorted(c.needs["hunger"] < 5 for c in world.cats) == [False, True]  # exactly one ate
    assert {"nom", "meow"} <= bubbles
    world.refill()
    run(world, 60)
    assert all(c.needs["hunger"] < 5 for c in world.cats)


def test_a_litter_trip_hides_the_cat_then_brings_it_back():
    world = world_with("Mango", seed=7)
    world.litter_in["Mango"] = 0
    seen = []
    run(world, 120, lambda w: seen.append(bool(w.view().cats)))
    assert False in seen and seen[-1] is True
    assert world.litter_in["Mango"] > 15 * 60


def test_needs_show_as_bubbles():
    world = world_with("Mango", seed=8)
    world.cats[0].needs["play"] = 90
    world.tick(TICK)
    body = world.bodies["Mango"]
    if body.step.doing is not Doing.NAP:
        assert world.view().cats[0].bubble == "🧶"


def test_faces_follow_the_mood():
    world = world_with("Mango", seed=9)
    world.cats[0].mood = 50
    world.bodies["Mango"].step = None
    world.bodies["Mango"].plan = []
    assert world.view().cats[0].face == "meh"
    world.cats[0].mood = 10
    assert world.view().cats[0].face == "mad"


def test_resizing_puts_every_cat_back_on_its_surface():
    world = world_with("Mango", seed=10)
    body = world.bodies["Mango"]
    body.surface, body.x, body.y = "shelf", 55.0, float(world.scape.shelf.y)
    world.fit(120, 80)
    assert body.y == world.scape.shelf.y
    lo, hi = walkable(world.scape.shelf)
    assert lo <= body.x <= hi
    assert body.step is None and body.plan == []


def test_resizing_mid_jump_lands_the_cat():
    world = world_with("Mango", seed=11)
    world.set_mode(Mode.PLAY)
    for _ in range(20000):
        world.tick(TICK)
        if world.bodies["Mango"].step and world.bodies["Mango"].step.doing is Doing.JUMP:
            break
    target = world.bodies["Mango"].step.surface
    world.fit(100, 70)
    assert world.bodies["Mango"].surface == target
    assert world.bodies["Mango"].y == world.scape.surface(target).y


def test_a_stalled_tick_is_capped_at_one_second():
    world = world_with("Mango")
    world.tick(3600)
    assert world.cats[0].needs["hunger"] == pytest.approx(100 / (3 * 3600))


def test_two_cats_never_eat_from_the_bowl_at_once():
    world = world_with("Mango", "Pebble", seed=6)
    for cat in world.cats:
        cat.needs["hunger"] = 90

    def one_at_a_time(w: World):
        eaters = [b for b in w.bodies.values() if b.step and b.step.doing is Doing.EAT]
        assert len(eaters) <= 1
        beggars = [b for b in w.bodies.values() if b.step and b.step.doing is Doing.BEG]
        for beggar in beggars:
            for eater in eaters:
                assert abs(beggar.x - eater.x) >= 17  # sitting beside, not on top

    run(world, 60, one_at_a_time)


def test_a_long_day_in_the_room_never_gets_stuck():
    world = world_with("Mango", "Pebble", "Tux", seed=12)
    world.cats[2].mood = 20  # one angry cat in the mix
    last_change = {name: 0.0 for name in world.bodies}
    previous = {}
    trips = set()
    t = 0.0
    for minute in range(4 * 60):  # four hours of 25/5 pomodoros
        world.set_mode(Mode.NAP if minute % 30 < 25 else Mode.PLAY)
        if minute % 90 == 0:
            world.refill()
        for _ in range(60):
            world.tick(1.0)
            t += 1.0
            for name, body in world.bodies.items():
                state = (body.surface, round(body.x), body.step.doing if body.step else None)
                if state != previous.get(name):
                    previous[name], last_change[name] = state, t
                if body.step and body.step.doing is Doing.AWAY:
                    trips.add(name)
                if body.step is None or body.step.doing is not Doing.JUMP:
                    assert body.y == world.scape.surface(body.surface).y
            for name in world.bodies:
                assert t - last_change[name] <= 400  # longest nap is 300 s
    assert trips == {"Mango", "Pebble", "Tux"}  # everyone used the litter door


def test_a_cat_away_during_a_resize_comes_back_on_the_new_floor():
    world = world_with("Mango", seed=7)
    world.litter_in["Mango"] = 0
    body = world.bodies["Mango"]
    for _ in range(2000):
        world.tick(TICK)
        if body.step and body.step.doing is Doing.AWAY:
            break
    assert body.step.doing is Doing.AWAY
    world.fit(120, 80)

    def grounded(w: World):
        b = w.bodies["Mango"]
        if b.step is None or b.step.doing is not Doing.JUMP:
            assert b.y == w.scape.surface(b.surface).y

    run(world, 60, grounded)


def test_until_there_is_a_feed_button_a_finished_break_refills_the_bowl():
    from pomo.game.events import BreakCompleted, FocusCompleted
    world = world_with("Mango")
    world.bowl_full = False
    world.apply([FocusCompleted(25)])
    assert not world.bowl_full
    world.apply([BreakCompleted(Phase.SHORT_BREAK)])
    assert world.bowl_full


def test_there_is_never_an_idle_frame_between_steps():
    # an idle body is drawn as a front-facing sit, which flashes between two walks or jumps
    world = world_with("Mango", "Pebble", seed=13)
    world.set_mode(Mode.PLAY)

    def busy(w: World):
        for body in w.bodies.values():
            assert body.step is not None

    run(world, 5 * 60, busy)
