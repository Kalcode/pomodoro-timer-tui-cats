import random

import pytest

from pomo.game.behavior import Doing, Mode, Step
from pomo.game.cat import Cat, Trait
from pomo.game.events import Fed, Petted
from pomo.game.tools import Tool, locked
from pomo.game.world import Poop, World, mode_for
from pomo.timer import Phase

TICK = 0.125


def room(*names: str, seed: int = 1) -> World:
    """Cats on the floor of a 70×58 room: the first at x=38, the next 22 columns on."""
    return World([Cat(name, "tabby", Trait.CLINGY) for name in names], random.Random(seed), 70, 58)


def run(world: World, seconds: float) -> None:
    for _ in range(int(seconds / TICK)):
        world.tick(TICK)


def stroke(world: World, x0: float, cells: int, y: float = 50) -> None:
    """Move the hand one column at a time, from x0 across `cells` columns."""
    for i in range(cells + 1):
        world.point(x0 + i, y)


class AlwaysLow(random.Random):
    """Every roll comes out 0.1: a 30% swat always happens."""

    def random(self) -> float:
        return 0.1


# --- tools -------------------------------------------------------------------

@pytest.mark.parametrize("mode, open_tools", [
    (Mode.NAP, {Tool.SCOOP}),
    (Mode.PLAY, set(Tool)),
    (Mode.RELAX, set(Tool)),
])
def test_a_focus_locks_every_tool_but_the_scoop(mode, open_tools):
    assert {t for t in Tool if not locked(t, mode)} == open_tools


def test_idle_is_relaxed():
    assert mode_for(Phase.FOCUS, True, idle=True) is Mode.RELAX
    assert mode_for(Phase.SHORT_BREAK, False, idle=True) is Mode.RELAX


def test_a_locked_tool_cannot_be_picked_up():
    world = room("Mango")
    world.set_mode(Mode.NAP)
    assert not world.hold(Tool.BALL)
    assert world.tool is None
    assert world.hold(Tool.SCOOP)
    assert world.tool is Tool.SCOOP


def test_a_focus_starting_puts_the_toys_away_but_not_the_scoop():
    world = room("Mango")
    world.hold(Tool.PET)
    world.set_mode(Mode.NAP)
    assert world.tool is None
    world.hold(Tool.SCOOP)
    world.set_mode(Mode.PLAY)
    world.set_mode(Mode.NAP)
    assert world.tool is Tool.SCOOP


def test_the_tool_in_hand_follows_the_pointer_over_the_room():
    world = room("Mango")
    world.hold(Tool.BALL)
    assert world.view().cursor is None  # the pointer hasn't come over the room yet
    world.point(10, 20)
    cursor = world.view().cursor
    assert (cursor.tool, cursor.x, cursor.y, cursor.busy) == ("ball", 10, 20, False)
    world.leave()
    assert world.view().cursor is None
    world.point(10, 20)
    world.hold(None)
    assert world.view().cursor is None


# --- feed ----------------------------------------------------------------------

def test_clicking_the_bowl_with_kibble_fills_it():
    world = room("Mango")
    world.bowl_full = False
    world.hold(Tool.FEED)
    bowl = world.scape.bowl
    world.click(bowl.x - 3, bowl.y + 1)  # beside it
    assert not world.bowl_full
    world.click(bowl.x + 3, bowl.y + 1)
    assert world.bowl_full
    assert world.take_news() == [Fed()]
    assert world.take_news() == []


def test_the_bowl_can_be_clicked_from_the_row_above():
    world = room("Mango")
    world.bowl_full = False
    world.hold(Tool.FEED)
    world.click(world.scape.bowl.x + 3, world.scape.bowl.y - 2)
    assert world.bowl_full


def test_picking_feed_twice_fills_the_bowl():
    world = room("Mango")
    world.bowl_full = False
    world.hold(Tool.FEED)
    assert not world.bowl_full
    world.hold(Tool.FEED)
    assert world.bowl_full


def test_feeding_a_full_bowl_says_so():
    world = room("Mango")
    world.feed()
    assert world.take_news() == [Fed(already_full=True)]


def test_only_the_feed_tool_fills_the_bowl():
    world = room("Mango")
    world.bowl_full = False
    world.hold(Tool.SCOOP)
    world.click(world.scape.bowl.x + 3, world.scape.bowl.y + 1)
    assert not world.bowl_full


def test_a_hungry_cat_comes_to_eat_once_the_bowl_is_filled():
    world = room("Mango")
    world.bowl_full = False
    world.cats[0].needs["hunger"] = 90
    run(world, 30)
    assert world.cats[0].needs["hunger"] > 80  # begging at an empty bowl
    world.hold(Tool.FEED)
    world.hold(Tool.FEED)
    run(world, 60)
    assert world.cats[0].needs["hunger"] < 5


# --- scoop ---------------------------------------------------------------------

def test_clicking_a_poop_scoops_it_up():
    world = room("Mango")
    floor = world.scape.floor.y
    world.poops = [Poop(20, floor), Poop(50, floor)]
    world.hold(Tool.SCOOP)
    world.click(30, floor - 2)  # nowhere near either
    assert len(world.poops) == 2
    world.click(21, floor - 2)
    assert [p.x for p in world.poops] == [50]
    assert world.view().poops == ((50, floor),)


def test_scooping_works_during_a_focus():
    world = room("Mango")
    floor = world.scape.floor.y
    world.poops = [Poop(20, floor)]
    world.set_mode(Mode.NAP)
    world.hold(Tool.SCOOP)
    world.click(20, floor - 1)
    assert world.poops == []


def test_poops_stay_on_the_floor_when_the_room_is_resized():
    world = room("Mango")
    world.poops = [Poop(65, world.scape.floor.y)]
    world.fit(100, 80)
    assert (world.poops[0].x, world.poops[0].y) == (65, 79)
    world.fit(70, 54)
    assert (world.poops[0].x, world.poops[0].y) == (65, 53)


# --- pet -----------------------------------------------------------------------

def test_six_cells_of_hand_movement_on_a_cat_is_one_stroke():
    world = room("Mango")
    mango = world.cats[0]
    mango.needs["affection"] = 60
    world.hold(Tool.PET)
    stroke(world, 33, 5)
    assert mango.needs["affection"] == 60
    world.point(39, 50)
    assert (mango.needs["affection"], mango.mood) == (35, 82)
    assert world.take_news() == [Petted("Mango", "purr")]


def test_a_purring_cat_sits_still_shuts_its_eyes_and_floats_a_heart():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    body = world.bodies["Mango"]
    assert body.step.doing is Doing.PURR
    (mango,) = world.view().cats
    assert (mango.pose, mango.face, mango.bubble) == ("sit", "blink", "prr")
    (heart,) = world.view().effects
    assert (heart.kind, heart.x) == ("heart", 44)  # beside the head, clear of the "prr" over it
    x = body.x
    run(world, 2)
    assert body.x == x and body.step.doing is Doing.PURR


def test_effects_float_up_and_fade():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    start = world.view().effects[0].y
    run(world, 1)
    assert world.view().effects[0].y == pytest.approx(start - 6)
    run(world, 0.5)
    assert world.view().effects == ()


def test_the_hand_is_busy_while_it_is_on_a_cat():
    world = room("Mango")
    world.hold(Tool.PET)
    world.point(10, 50)
    assert not world.view().cursor.busy
    world.point(38, 50)
    assert world.view().cursor.busy


def test_moving_onto_a_cat_is_not_a_stroke_yet():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.PET)
    world.point(10, 50)
    world.point(38, 50)  # a 28-column jump onto the cat
    assert world.cats[0].needs["affection"] == 60


def test_up_and_down_counts_half_as_much_as_across():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.PET)
    for y in (42, 44, 46, 48, 50, 52):  # five moves of one row each: 5 cells
        world.point(38, y)
    assert world.cats[0].needs["affection"] == 60
    world.point(38, 54)
    assert world.cats[0].needs["affection"] == 35


def test_leaving_the_room_lifts_the_hand():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.PET)
    stroke(world, 33, 3)
    world.leave()
    stroke(world, 36, 3)
    assert world.cats[0].needs["affection"] == 60


def test_only_the_hand_pets():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.BALL)
    stroke(world, 33, 10)
    assert world.cats[0].needs["affection"] == 60


def test_an_angry_cat_hisses_at_the_hand():
    world = room("Mango")
    mango = world.cats[0]
    mango.mood, mango.needs["affection"] = 30, 60
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    assert (mango.mood, mango.needs["affection"]) == (30, 60)
    assert [e.kind for e in world.view().effects] == ["hiss"]
    assert world.bodies["Mango"].step is None or world.bodies["Mango"].step.doing is not Doing.PURR
    assert world.take_news() == [Petted("Mango", "hiss")]


def test_too_much_petting_earns_a_swat():
    world = room("Mango")
    mango = world.cats[0]
    mango.needs["affection"] = 5
    world.rng = AlwaysLow()
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    assert mango.mood == 78
    assert [e.kind for e in world.view().effects] == ["swat"]
    assert world.take_news() == [Petted("Mango", "swat")]


def test_a_grumpy_cat_sits_for_petting_without_hearts():
    world = room("Mango")
    mango = world.cats[0]
    mango.mood, mango.needs["affection"] = 50, 60
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    assert mango.mood == 52
    assert world.bodies["Mango"].step.doing is Doing.PURR
    (view,) = world.view().cats
    assert (view.face, view.bubble) == ("meh", None)
    assert world.view().effects == ()


def test_the_hand_pets_the_cat_in_front():
    world = room("Mango", "Pebble")
    for cat in world.cats:
        cat.needs["affection"] = 60
    world.bodies["Pebble"].x = 42  # overlapping Mango at 38, and drawn over him
    world.hold(Tool.PET)
    stroke(world, 34, 6)
    assert [c.needs["affection"] for c in world.cats] == [60, 35]


def test_a_cat_out_through_the_door_cannot_be_petted():
    world = room("Mango")
    mango = world.cats[0]
    mango.needs["affection"] = 60
    world.bodies["Mango"].step = Step(Doing.AWAY, seconds=30)
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    assert mango.needs["affection"] == 60
