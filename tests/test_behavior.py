import dataclasses
import random
from collections import Counter

import pytest

from pomo.game import balance
from pomo.game.behavior import Body, Doing, Mode, Step, advance, choose, path, pick, route, walkable
from pomo.game.cat import Cat, Stage, Trait
from pomo.game.playscape import Surface, can_jump, layout

SCAPE = layout(70, 58)


def body_on(surface: str, x: float | None = None) -> Body:
    s = SCAPE.surface(surface)
    return Body(surface, walkable(s)[0] if x is None else x, float(s.y))


def carry_out(body: Body, steps, dt=0.1, limit_s=900.0, watch=None) -> list[Step]:
    """Run a plan to the end; returns the steps in the order they finished."""
    body.plan = list(steps)
    finished, t = [], 0.0
    while (body.step or body.plan) and t < limit_s:
        if body.step is None:
            body.step = body.plan.pop(0)
        if watch:
            watch(body)
        done = advance(body, SCAPE, dt)
        if done:
            finished.append(done)
        t += dt
    assert not body.step and not body.plan, "the plan never finished"
    return finished


def a_cat(mood=80.0, **needs) -> Cat:
    cat = Cat("Mango", "tabby", Trait.CLINGY, mood=mood)
    cat.needs.update(needs)
    return cat


def test_walkable_keeps_the_centre_inside_and_narrow_surfaces_are_one_spot():
    assert walkable(SCAPE.floor) == (9, 61)
    assert walkable(SCAPE.tree_top) == (12, 12)


def test_paths_only_hop_between_surfaces_a_cat_can_jump():
    hops = path(SCAPE, "floor", "shelf")
    assert hops[-1] == "shelf"
    for a, b in zip(["floor", *hops], hops):
        assert can_jump(SCAPE.surface(a), SCAPE.surface(b))
    assert path(SCAPE, "floor", "floor") == []


def test_an_unreachable_surface_is_an_error():
    stranded = dataclasses.replace(SCAPE, shelf=Surface("shelf", 50, 70, -40))  # far out of reach
    with pytest.raises(ValueError):
        path(stranded, "floor", "shelf")


@pytest.mark.parametrize("start, goal", [("floor", "tree_top"), ("tree_top", "floor"), ("floor", "shelf"),
                                         ("shelf", "tree_top"), ("tree_mid", "floor")])
def test_a_route_ends_standing_on_the_goal(start, goal):
    body = body_on(start)
    target = walkable(SCAPE.surface(goal))[1]
    carry_out(body, route(SCAPE, body, goal, target))
    assert (body.surface, body.x, body.y) == (goal, target, SCAPE.surface(goal).y)


def test_route_targets_are_clamped_onto_the_surface():
    body = body_on("floor", 30)
    carry_out(body, route(SCAPE, body, "floor", 500))
    assert body.x == walkable(SCAPE.floor)[1]


def test_walking_moves_at_walking_speed_and_faces_the_way_it_goes():
    body = body_on("floor", 20)
    body.step = Step(Doing.WALK, x=40)
    advance(body, SCAPE, 1.0)
    assert (body.x, body.facing, body.walked) == (20 + balance.WALK_SPEED, 1, balance.WALK_SPEED)
    body.step = Step(Doing.WALK, x=20)
    advance(body, SCAPE, 0.5)
    assert body.facing == -1


def test_zooming_is_faster_than_walking():
    body = body_on("floor", 10)
    body.step = Step(Doing.ZOOM, x=60)
    advance(body, SCAPE, 1.0)
    assert body.x == 10 + balance.ZOOM_SPEED


def test_a_walk_stops_exactly_on_its_target():
    body = body_on("floor", 20)
    body.step = Step(Doing.WALK, x=21.5)
    done = advance(body, SCAPE, 1.0)
    assert done is not None and body.x == 21.5 and body.step is None


def test_jumps_arc_above_the_straight_line_and_land_exactly():
    body = body_on("floor", 18)
    heights = []
    carry_out(body, [Step(Doing.JUMP, x=18, surface="tree_mid")], dt=0.05, watch=lambda b: heights.append(b.y))
    assert body.surface == "tree_mid" and body.y == SCAPE.tree_mid.y
    floor_y, mid_y = SCAPE.floor.y, SCAPE.tree_mid.y
    assert min(heights) < mid_y  # the arc peaks above the landing spot
    assert all(y <= floor_y for y in heights)


def test_timed_steps_last_their_seconds():
    body = body_on("floor")
    body.step = Step(Doing.LOAF, seconds=2.0)
    assert advance(body, SCAPE, 1.9) is None
    assert advance(body, SCAPE, 0.2) is not None


def test_a_hungry_cat_heads_to_the_bowl_and_eats_or_begs():
    body = body_on("tree_top")
    plan = choose(a_cat(hunger=90), body, SCAPE, Mode.NAP, random.Random(1), bowl_full=True, litter_due=False)
    assert plan[-1].doing is Doing.EAT
    carry_out(body, plan)
    assert body.surface == "floor" and body.x == SCAPE.bowl.x - 6
    plan = choose(a_cat(hunger=90), body, SCAPE, Mode.NAP, random.Random(1), bowl_full=False, litter_due=False)
    assert plan[-1].doing is Doing.BEG


def test_a_litter_trip_goes_out_the_door_and_comes_back():
    body = body_on("shelf")
    plan = choose(a_cat(), body, SCAPE, Mode.PLAY, random.Random(2), bowl_full=True, litter_due=True)
    door_x = SCAPE.door.x + SCAPE.door.w / 2
    doings = [s.doing for s in plan]
    assert Doing.AWAY in doings
    away = doings.index(Doing.AWAY)
    assert plan[away - 1] == Step(Doing.WALK, x=door_x)
    carry_out(body, plan)
    lo, hi = walkable(SCAPE.floor)
    assert body.surface == "floor" and lo <= body.x <= hi


def test_the_litter_box_comes_before_hunger():
    plan = choose(a_cat(hunger=100), body_on("floor"), SCAPE, Mode.NAP, random.Random(3),
                  bowl_full=True, litter_due=True)
    assert Doing.AWAY in [s.doing for s in plan]


def picks(stage: Stage, mode: Mode, n=3000) -> Counter:
    rng = random.Random(7)
    return Counter(pick(stage, mode, rng) for _ in range(n))


def test_focus_is_nap_time_and_breaks_are_play_time():
    nap, play = picks(Stage.CONTENT, Mode.NAP), picks(Stage.CONTENT, Mode.PLAY)
    assert nap["nap"] / 3000 > 0.5 and nap["zoom"] == 0
    assert play["zoom"] / 3000 > 0.15 and play["nap"] / 3000 < 0.1


def test_grumpy_cats_sulk_instead_of_zooming():
    play = picks(Stage.GRUMPY, Mode.PLAY)
    assert play["zoom"] == 0 and play["sulk"] > 0


def test_angry_cats_only_sulk_wander_climb_or_nap():
    for stage in (Stage.PISSY, Stage.FURIOUS):
        chosen = set(picks(stage, Mode.PLAY))
        assert chosen <= {"sulk", "wander", "climb", "nap"}


def test_naps_mostly_happen_up_high():
    rng = random.Random(11)
    napped_on = Counter()
    for _ in range(200):
        body = body_on("floor", 40)
        plan = choose(a_cat(), body, SCAPE, Mode.NAP, rng, bowl_full=True, litter_due=False)
        if plan[-1].doing is Doing.NAP:
            carry_out(body, plan[:-1])
            napped_on[body.surface] += 1
    assert sum(napped_on.values()) > 50
    assert napped_on["floor"] < sum(napped_on.values()) / 3


@pytest.mark.parametrize("seed", range(5))
def test_every_plan_can_be_carried_out_and_keeps_the_cat_in_the_room(seed):
    rng = random.Random(seed)
    body = body_on("floor", 40)
    for _ in range(60):
        mode = rng.choice(list(Mode))
        cat = a_cat(mood=rng.uniform(0, 100), hunger=rng.choice([0, 90]))

        def inside(b: Body):
            assert -5 <= b.x <= SCAPE.width + 5 and 0 <= b.y <= SCAPE.floor.y

        plan = choose(cat, body, SCAPE, mode, rng, bowl_full=rng.random() < 0.5, litter_due=rng.random() < 0.1)
        carry_out(body, plan, dt=0.25, watch=inside)
        assert body.y == SCAPE.surface(body.surface).y
