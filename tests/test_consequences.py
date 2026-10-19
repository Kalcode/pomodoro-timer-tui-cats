"""Breaking the rules has consequences (home stretch §5): poop, the knocked bowl, and a furious cat on the clock."""

import random

import pytest
from textual.widgets import Static

from canvas_reading import screen_text
from pomo.clock import FakeClock
from pomo.config import Config
from pomo.game import balance
from pomo.game.behavior import Doing, Mode, Step, walkable
from pomo.game.cat import Cat, Stage, Trait
from pomo.game.events import ClockLeft, ClockTaken, Fed, KnockedBowl, Pooped, RuleBreak, RuleKind
from pomo.game.playscape import CLOCK_PERCH
from pomo.game.tools import Tool
from pomo.game.world import CLOCK_SPOT, Poop, World
from pomo.notify import NullNotifier
from pomo.render import scene, sprites
from pomo.render.canvas import Canvas
from pomo.timer import PomodoroTimer, TimerSettings
from pomo.ui import view
from pomo.ui.app import PomoApp

TICK = 0.125


def a_cat(name: str = "Mango", mood: float = 80.0, trait: Trait = Trait.CLINGY, coat: str = "tabby") -> Cat:
    return Cat(name, coat, trait, mood=mood)


def room(*cats: Cat, seed: int = 1) -> World:
    """Cats on the floor of a 70×58 room (a 100×30 terminal): the first at x=38, the next 22 columns on."""
    return World(list(cats), random.Random(seed), 70, 58)


def run(world: World, seconds: float, each=None) -> None:
    for _ in range(int(seconds / TICK)):
        world.tick(TICK)
        if each:
            each(world)


def run_until(world: World, done, limit_s: float = 300.0) -> None:
    for _ in range(int(limit_s / TICK)):
        world.tick(TICK)
        if done(world):
            return
    raise AssertionError("it never happened")


def view_of(world: World, name: str):
    return next(c for c in world.view().cats if c.name == name)


def on_the_clock(world: World) -> World:
    """The room, once Tux is sitting on the clock."""
    run_until(world, lambda w: w.bodies["Tux"].surface == CLOCK_PERCH.name)
    return world


def leaping(body, surface: str) -> bool:
    return body.step is not None and body.step.doing is Doing.JUMP and body.step.surface == surface


# --- poop (§5.1) -----------------------------------------------------------------------

@pytest.mark.parametrize("mood, pooped", [(80, False), (50, False), (30, True), (10, True)])
def test_a_pissy_or_furious_cat_poops_on_the_floor_instead_of_using_the_door(mood, pooped):
    world = room(a_cat(mood=mood))
    world.litter_in["Mango"] = 0
    doings = set()
    run(world, 60, lambda w: doings.add(w.bodies["Mango"].step.doing))
    assert (Doing.POOP in doings, Doing.AWAY in doings) == (pooped, not pooped)
    if pooped:
        assert [(p.x, p.y) for p in world.poops] == [(38, world.scape.floor.y)]  # right where it was standing
        assert Pooped("Mango") in world.take_news()
    else:
        assert world.poops == []


def test_a_poop_is_scooped_up_like_any_other():
    world = room(a_cat(mood=30))
    world.litter_in["Mango"] = 0
    run(world, 30)
    world.hold(Tool.SCOOP)
    world.click(38, world.scape.floor.y - 1)
    assert world.poops == []


def test_every_poop_sours_every_cat_by_2_every_10_minutes():
    world = room(a_cat("Mango", mood=90), a_cat("Pebble", mood=85))
    floor = world.scape.floor.y
    world.poops = [Poop(10, floor)]
    run(world, 10 * 60)
    assert [c.mood for c in world.cats] == pytest.approx([88, 83])
    world.poops.append(Poop(20, floor))
    run(world, 10 * 60)
    assert [c.mood for c in world.cats] == pytest.approx([84, 79])


def test_poop_alone_never_makes_a_cat_furious_and_pins_a_pissy_one_at_15():
    world = room(a_cat(mood=16))
    floor = world.scape.floor.y
    world.poops = [Poop(10, floor), Poop(20, floor), Poop(30, floor)]
    run(world, 30 * 60)
    assert world.cats[0].mood == 15  # cooling can't lift it while the poop is down
    assert world.cats[0].stage is Stage.PISSY


def test_poop_leaves_a_furious_cat_to_cool_off_as_usual():
    world = room(a_cat(mood=10))
    world.poops = [Poop(10, world.scape.floor.y)]
    run(world, 10 * 60)
    assert world.cats[0].mood == pytest.approx(11)


# --- the knocked bowl (§5.2) --------------------------------------------------------------

def test_an_angry_cat_knocks_the_bowl_over_from_beside_it_when_mischief_is_due():
    world = room(a_cat(mood=30))
    world.mischief_in["Mango"] = 0
    knocked_from = set()

    def watch(w: World):
        body = w.bodies["Mango"]
        if body.step.doing is Doing.KNOCK:
            knocked_from.add((body.surface, body.x))

    run(world, 30, watch)
    assert knocked_from == {("floor", world.scape.bowl.x - 6)}
    assert world.bowl_knocked and not world.bowl_full
    assert world.view().bowl_knocked
    assert world.take_news() == [KnockedBowl("Mango")]
    assert world.mischief_in["Mango"] > balance.MISCHIEF_EVERY_S[0] - 30  # and again in 10–20 minutes


def test_a_cat_that_is_not_angry_lets_the_bowl_be_and_waits_for_next_time():
    world = room(a_cat(mood=50))
    world.mischief_in["Mango"] = 0
    run(world, 30)
    assert world.bowl_full and not world.bowl_knocked
    assert world.mischief_in["Mango"] > balance.MISCHIEF_EVERY_S[0] - 30


def test_a_bowl_already_on_its_side_is_left_where_it_lies():
    world = room(a_cat(mood=30))
    world.bowl_knocked, world.bowl_full = True, False
    world.mischief_in["Mango"] = 0
    run(world, 30)
    assert world.take_news() == []
    assert world.mischief_in["Mango"] > balance.MISCHIEF_EVERY_S[0] - 30


@pytest.mark.parametrize("trait, every", [(Trait.CLINGY, (600, 1200)), (Trait.GREMLIN, (300, 600))])
def test_mischief_comes_every_10_to_20_minutes_and_twice_as_often_for_a_gremlin(trait, every):
    rolls = [room(a_cat(trait=trait), seed=seed).mischief_in["Mango"] for seed in range(40)]
    assert every[0] <= min(rolls) and max(rolls) <= every[1]
    assert max(rolls) - min(rolls) > (every[1] - every[0]) / 2  # spread over the range


def test_feeding_stands_a_knocked_bowl_back_up_and_fills_it():
    world = room(a_cat())
    world.bowl_knocked, world.bowl_full = True, False
    world.hold(Tool.FEED)
    world.click(world.scape.bowl.x + 3, world.scape.bowl.y + 1)  # the bowl's box, as when it stands
    assert world.bowl_full and not world.bowl_knocked
    assert not world.view().bowl_knocked
    assert world.take_news() == [Fed(was_knocked=True)]


def test_hungry_cats_beg_at_a_knocked_bowl():
    world = room(a_cat())
    world.bowl_knocked, world.bowl_full = True, False
    world.cats[0].needs["hunger"] = 90
    bubbles = set()
    run(world, 30, lambda w: bubbles.add(w.view().cats[0].bubble))
    assert "meow" in bubbles and "nom" not in bubbles
    assert world.cats[0].needs["hunger"] > 80


# --- the clock (§5.3) -----------------------------------------------------------------------

def test_a_skipped_break_puts_tux_on_the_clock_until_tux_cheers_up_to_25():
    """The scenario from the main spec §11."""
    tux = a_cat("Tux", mood=30, coat="tuxedo")
    world = room(a_cat("Mango"), tux)
    world.apply([RuleBreak(RuleKind.SKIP_BREAK)])
    assert (tux.mood, tux.stage) == (10, Stage.FURIOUS)
    world.set_mode(Mode.NAP)  # the focus after the skipped break
    run(world, 3 * 60)

    assert world.on_clock == "Tux"
    view = view_of(world, "Tux")
    assert view.free and (view.pose, view.face, view.x, view.feet) == ("loaf", "mad", CLOCK_SPOT, CLOCK_PERCH.y)
    assert world.view().clock_cat == "Tux"
    assert world.take_news() == [ClockTaken("Tux")]
    clock = FakeClock()
    canvas = Canvas(scene.PANEL_WIDTH + 70, 29, (0, 0, 0))
    scene.draw(canvas, PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), clock), world.view(), 1)
    coat = set(sprites.COATS["tuxedo"].values())
    over_digits = [canvas.pixel_at(x, py) for x in range(scene.CLOCK_X, scene.CLOCK_X + 25)
                   for py in range(scene.CLOCK_PY, scene.CLOCK_PY + 7)]
    assert sum(p in coat for p in over_digits) > len(over_digits) / 2  # in the panel, over the digits

    tux.mood = 25
    run(world, 10)
    body = world.bodies["Tux"]
    assert world.on_clock is None and world.view().clock_cat is None
    assert body.surface in {s.name for s in world.scape.surfaces} and body.x >= 0
    assert not view_of(world, "Tux").free
    assert world.take_news() == [ClockLeft("Tux")]


@pytest.mark.parametrize("trait, wait", [(Trait.CLINGY, 60), (Trait.GREMLIN, 15)])
def test_a_cat_heads_for_the_clock_once_furious_for_a_minute_or_15_s_for_a_gremlin(trait, wait):
    world = room(a_cat("Tux", mood=10, trait=trait))
    run(world, wait - 1)
    assert world.on_clock is None
    run(world, 2)
    assert world.on_clock == "Tux"  # spoken for, though not there yet
    body = world.bodies["Tux"]
    assert [body.step, *body.plan][-1] == Step(Doing.JUMP, x=CLOCK_SPOT, surface=CLOCK_PERCH.name)


def test_the_wait_starts_over_if_the_cat_calms_down_in_between():
    tux = a_cat("Tux", mood=10, trait=Trait.GREMLIN)
    world = room(tux)
    run(world, 10)
    tux.mood = 20
    world.tick(TICK)
    tux.mood = 10
    run(world, 10)
    assert world.on_clock is None
    run(world, 6)
    assert world.on_clock == "Tux"


def test_the_leap_onto_the_clock_starts_from_the_left_end_of_the_tree_top():
    world = room(a_cat("Tux", mood=5, trait=Trait.GREMLIN))
    run_until(world, lambda w: leaping(w.bodies["Tux"], CLOCK_PERCH.name))
    body = world.bodies["Tux"]
    assert body.surface == "tree_top" and body.x == pytest.approx(walkable(world.scape.tree_top)[0])
    assert view_of(world, "Tux").free  # drawn uncut as it crosses the divider


def test_only_one_cat_sits_on_the_clock_at_a_time():
    world = room(a_cat("Tux", mood=5), a_cat("Mango", mood=5))
    seen = set()

    def one_at_a_time(w: World):
        free = [c.name for c in w.view().cats if c.free]
        assert len(free) <= 1
        seen.update(free)

    run(world, 5 * 60, one_at_a_time)
    assert world.on_clock is not None and seen == {world.on_clock}
    other = next(name for name in ("Tux", "Mango") if name != world.on_clock)
    assert world.bodies[other].x >= 0  # still in the room, zooming and sulking


def test_a_cat_through_the_door_takes_the_clock_once_it_is_back():
    world = room(a_cat("Tux", trait=Trait.GREMLIN))
    world.litter_in["Tux"] = 0  # content, so out through the door it goes...
    run_until(world, lambda w: w.bodies["Tux"].step.doing is Doing.AWAY)
    world.cats[0].mood = 5  # ...and is furious by the time it's back
    run(world, 16)
    assert world.bodies["Tux"].step.doing is Doing.AWAY and world.on_clock is None
    run_until(world, lambda w: w.on_clock == "Tux")


def test_a_phase_change_leaves_the_cat_on_the_clock():
    world = on_the_clock(room(a_cat("Tux", mood=5, trait=Trait.GREMLIN)))
    body = world.bodies["Tux"]
    glare = body.step
    assert glare.doing is Doing.GLARE
    for mode in (Mode.PLAY, Mode.NAP, Mode.RELAX):
        world.set_mode(mode)
        assert body.step is glare
    run(world, 2 * 60)
    assert body.surface == CLOCK_PERCH.name and body.step.doing is Doing.GLARE


def test_a_phase_change_does_not_call_off_the_trip_to_the_clock():
    world = room(a_cat("Tux", mood=5, trait=Trait.GREMLIN))
    run_until(world, lambda w: w.on_clock == "Tux")
    body = world.bodies["Tux"]
    trip = [body.step, *body.plan]
    world.set_mode(Mode.NAP)
    assert [body.step, *body.plan] == trip
    run_until(world, lambda w: w.bodies["Tux"].surface == CLOCK_PERCH.name, limit_s=60)


def test_the_cat_on_the_clock_ignores_food_toys_and_the_litter_box():
    world = on_the_clock(room(a_cat("Tux", mood=5, trait=Trait.GREMLIN)))
    world.cats[0].needs["hunger"] = 90
    world.litter_in["Tux"] = world.mischief_in["Tux"] = 0
    world.hold(Tool.BALL)
    world.click(40, 50)
    run(world, 3 * 60)
    body = world.bodies["Tux"]
    assert body.surface == CLOCK_PERCH.name and body.step.doing is Doing.GLARE
    assert world.poops == [] and not world.bowl_knocked
    assert view_of(world, "Tux").bubble is None  # nothing floats up over the panel's text


def test_a_cat_that_cheers_up_on_its_way_to_the_clock_stays_in_the_room():
    world = room(a_cat("Tux", mood=5))
    world.place("Tux", "floor", 50)
    world.furious_for["Tux"] = balance.CLOCK_AFTER_S
    world.tick(TICK)
    assert world.on_clock == "Tux"
    world.cats[0].mood = 30
    run(world, 30)
    assert world.on_clock is None
    assert world.bodies["Tux"].surface != CLOCK_PERCH.name
    assert world.take_news() == []


def test_a_resize_leaves_the_cat_on_the_clock():
    world = on_the_clock(room(a_cat("Tux", mood=5, trait=Trait.GREMLIN)))
    body = world.bodies["Tux"]
    glare = body.step
    for size in ((120, 80), (70, 54)):
        world.fit(*size)
        assert (body.surface, body.x, body.y) == (CLOCK_PERCH.name, CLOCK_SPOT, CLOCK_PERCH.y)
        assert body.step is glare


def test_a_resize_mid_leap_lands_the_cat_on_the_clock():
    world = room(a_cat("Tux", mood=5, trait=Trait.GREMLIN))
    run_until(world, lambda w: leaping(w.bodies["Tux"], CLOCK_PERCH.name) and w.bodies["Tux"].x < 0)
    world.fit(120, 80)
    body = world.bodies["Tux"]
    assert (body.surface, body.x, body.y) == (CLOCK_PERCH.name, CLOCK_SPOT, CLOCK_PERCH.y)
    assert world.take_news() == [ClockTaken("Tux")]
    run(world, 2)
    assert body.surface == CLOCK_PERCH.name and body.step.doing is Doing.GLARE


def test_a_resize_mid_leap_off_the_clock_puts_the_cat_back_to_try_again():
    world = on_the_clock(room(a_cat("Tux", mood=5, trait=Trait.GREMLIN)))
    world.take_news()
    world.cats[0].mood = 30
    world.tick(TICK)
    body = world.bodies["Tux"]
    assert leaping(body, "tree_top")
    world.fit(120, 80)
    assert (body.surface, body.x, body.y) == (CLOCK_PERCH.name, CLOCK_SPOT, CLOCK_PERCH.y)
    run(world, 5)
    assert world.on_clock is None and body.surface != CLOCK_PERCH.name and body.x >= 0
    assert world.take_news() == [ClockLeft("Tux")]


def test_a_cat_is_never_put_back_onto_the_clock():
    world = on_the_clock(room(a_cat("Tux", mood=5, trait=Trait.GREMLIN)))
    world.place("Tux", CLOCK_PERCH.name, CLOCK_SPOT)
    body = world.bodies["Tux"]
    assert (body.surface, body.x, body.y) == ("tree_top", walkable(world.scape.tree_top)[0], world.scape.tree_top.y)
    assert world.on_clock is None


def test_the_room_view_draws_a_cat_on_the_clock_free_of_the_room():
    world = on_the_clock(room(a_cat("Mango"), a_cat("Tux", mood=5, trait=Trait.GREMLIN)))
    view = world.view()
    assert [(c.name, c.free) for c in view.cats] == [("Mango", False), ("Tux", True)]
    assert view.clock_cat == "Tux"
    canvas = Canvas(scene.PANEL_WIDTH + 70, 29, (0, 0, 0))
    scene.draw(canvas, PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), FakeClock()), view, 1)
    assert canvas.row_text(scene.STATE_ROW).strip() == "25:00 space to start"
    assert canvas.pixel_at(scene.PANEL_WIDTH // 2, scene.CLOCK_PY + 3) in sprites.COATS["tabby"].values()


async def test_in_the_app_the_message_line_says_who_took_the_clock_and_the_time_stays_readable():
    clock = FakeClock()
    app = PomoApp(Config(), clock, NullNotifier(), rng=random.Random(0))
    async with app.run_test(size=(100, 30)) as pilot:
        await pilot.press("space")
        mango = app.world.cats[0]
        mango.trait, mango.mood = Trait.GREMLIN, 5
        for _ in range(int(60 / TICK)):
            clock.advance(TICK)
            app.tick()
            if app.world.bodies["Mango"].surface == CLOCK_PERCH.name:
                break
        assert app.world.on_clock == "Mango"
        message = str(app.main.query_one("#message", Static).render())
        assert message == "Mango is sitting on your clock. Tuna, or a better mood, will move them."
        canvas = app.main.stage.canvas
        time = view.clock_text(app.session.timer.remaining())
        assert canvas.row_text(scene.STATE_ROW).strip() == f"{time} · Mango is on it"
        assert "● FOCUS" in screen_text(canvas)
