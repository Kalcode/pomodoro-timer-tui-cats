"""The shop's toys and furniture in the room (home stretch §4)."""

import json
import random

import pytest

from pomo import persist
from pomo.clock import FakeClock
from pomo.game import balance
from pomo.game.behavior import Doing, Mode, box_spot, nap_spots
from pomo.game.cat import Cat, Trait
from pomo.game.events import Played
from pomo.game.tools import Tool
from pomo.game.world import World
from pomo.session import Session
from pomo.timer import TimerSettings

TICK = 0.125


def room(*names: str, seed: int = 2, owned=(), width: int = 70, height: int = 58) -> World:
    world = World([Cat(n, "tabby", Trait.CLINGY) for n in names], random.Random(seed), width, height)
    world.wallet.owned |= set(owned)
    world.furnish()
    return world


def run(world: World, seconds: float, each=None) -> None:
    for _ in range(int(seconds / TICK)):
        world.tick(TICK)
        if each:
            each(world)


# --- furniture -----------------------------------------------------------------


def test_buying_furniture_puts_it_in_the_room_straight_away():
    world = room("Mango")
    world.wallet.treats = 100
    assert world.scape.perch is None
    world.buy("perch")
    assert world.scape.perch is not None
    assert world.view().furniture == {"perch"}
    world.buy("laser")
    assert world.view().furniture == {"perch"}  # a toy isn't furniture


def test_a_resize_keeps_the_furniture():
    world = room("Mango", owned={"box", "hammock"})
    world.fit(120, 80)
    assert world.scape.box is not None and world.scape.hammock is not None


def test_cats_love_the_box_and_the_hammock_once_they_are_there():
    assert set(nap_spots(room("Mango").scape)) == {"tree_top", "tree_mid", "shelf", "floor"}
    weights = nap_spots(room("Mango", owned={"box", "hammock", "perch"}).scape)
    assert weights["box"] > weights["tree_top"] and weights["hammock"] > weights["tree_top"]


@pytest.mark.parametrize("seed", range(3))
def test_napping_cats_use_the_furniture(seed):
    world = room("Mango", "Pebble", seed=seed, owned={"box", "hammock", "perch"})
    world.set_mode(Mode.NAP)
    spots, boxed = set(), []

    def look(w: World):
        for name, body in w.bodies.items():
            if body.step is not None and body.step.doing is Doing.NAP:
                spots.add("box" if abs(body.x - box_spot(w.scape)) < 1 and body.surface == "floor" else body.surface)
        boxed.extend(c.in_box for c in w.view().cats)

    run(world, 90 * 60, look)
    assert {"box", "hammock"} <= spots
    assert any(boxed)


def test_only_a_napping_cat_is_in_the_box():
    world = room("Mango", owned={"box"})
    body = world.bodies["Mango"]
    body.x = box_spot(world.scape)
    assert not world.view().cats[0].in_box  # sitting beside it, not in it


def test_a_save_on_the_perch_comes_back_on_the_perch():
    world = room("Mango", owned={"perch"})
    world.place("Mango", "perch", 30)
    session = Session(TimerSettings.from_minutes(25, 5, 15, 4), FakeClock())
    data = json.loads(json.dumps(persist.snapshot(session, world, 1.0)))
    back = persist.build_world(persist.read(data), random.Random(1))
    assert back.bodies["Mango"].surface == "perch"


def test_a_cat_saved_on_furniture_that_is_not_there_lands_on_the_floor():
    world = room("Mango")
    world.place("Mango", "hammock", 50)
    assert world.bodies["Mango"].surface == "floor"


# --- catnip --------------------------------------------------------------------


def keen(world: World) -> None:
    for cat in world.cats:
        cat.needs["play"] = 100.0


def test_catnip_needs_buying_and_waits_for_the_break():
    world = room("Mango")
    assert not world.hold(Tool.CATNIP)
    world.wallet.owned.add("catnip")
    world.set_mode(Mode.NAP)
    assert not world.hold(Tool.CATNIP)
    world.set_mode(Mode.PLAY)
    assert world.hold(Tool.CATNIP)


def test_a_keen_cat_rolls_on_the_dropped_catnip_and_has_a_big_play():
    world = room("Mango", owned={"catnip"})
    world.set_mode(Mode.PLAY)
    keen(world)
    world.cats[0].mood = 70.0
    world.hold(Tool.CATNIP)
    world.click(20, 40)
    assert world.view().catnip == 20
    poses, news = set(), []

    def look(w: World):
        poses.update(c.pose for c in w.view().cats)
        news.extend(w.take_news())

    run(world, 30, look)
    assert {"roll0", "roll1"} <= poses
    assert Played("Mango", "catnip") in news
    assert world.cats[0].needs["play"] < 5  # catnip meets all of it...
    assert world.cats[0].mood > 70 + balance.CATNIP_MOOD - 1  # ...and pays for it


# --- the laser -----------------------------------------------------------------


def test_the_dot_lands_on_the_first_surface_under_the_pointer():
    world = room("Mango", owned={"laser"})
    world.set_mode(Mode.PLAY)
    world.hold(Tool.LASER)
    shelf = world.scape.shelf
    world.point(shelf.x0 + 5, shelf.y - 10)
    assert (world.laser.surface, world.view().laser) == ("shelf", (shelf.x0 + 5, shelf.y))
    world.point(shelf.x0 + 5, shelf.y + 1)  # just under the shelf: the floor
    assert world.laser.surface == "floor"


def test_the_dot_goes_when_the_pointer_or_the_tool_does():
    world = room("Mango", owned={"laser"})
    world.hold(Tool.LASER)
    world.point(30, 30)
    world.leave()
    assert world.laser is None
    world.point(30, 30)
    world.hold(Tool.BALL)
    assert world.laser is None


def test_cats_chase_the_dot_flat_out():
    world = room("Mango", owned={"laser"}, seed=4)
    world.set_mode(Mode.PLAY)
    keen(world)
    world.hold(Tool.LASER)
    world.point(10, world.scape.floor.y - 2)
    zooms, news = [], []
    xs = [10, 60]

    def look(w: World):
        body = w.bodies["Mango"]
        zooms.append(body.step is not None and body.step.doing is Doing.ZOOM)
        news.extend(w.take_news())

    for i in range(8):  # the dot flicks from side to side
        world.point(xs[i % 2], world.scape.floor.y - 2)
        run(world, 3, look)
    assert any(zooms)
    assert Played("Mango", "laser") in news


# --- drawing -------------------------------------------------------------------

from pomo.game.playscape import FURNITURE, layout  # noqa: E402
from pomo.game.world import CatView, RoomView  # noqa: E402
from pomo.render import sprites  # noqa: E402
from pomo.render.canvas import Canvas  # noqa: E402
from pomo.render.scene import PANEL_WIDTH, draw  # noqa: E402
from pomo.timer import PomodoroTimer  # noqa: E402

W, H = 100, 28
ROOM = layout(W - PANEL_WIDTH, H * 2, frozenset(FURNITURE))


def render(*cats: CatView, furniture=frozenset(FURNITURE), **view) -> Canvas:
    canvas = Canvas(W, H, (0, 0, 0))
    timer = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), FakeClock())
    draw(canvas, timer, RoomView(cats=cats, furniture=frozenset(furniture), **view), 1)
    return canvas


def colours(canvas: Canvas, x0: int, x1: int, y0: int, y1: int) -> set:
    return {canvas.pixel_at(PANEL_WIDTH + x, py) for x in range(x0, x1) for py in range(y0, y1)}


def test_bought_furniture_is_drawn_and_nothing_else_is():
    bare, furnished = render(furniture=()), render()
    perch, hammock, box = ROOM.perch, ROOM.hammock, ROOM.box
    for x0, x1, y0, y1, palette in ((perch.x0, perch.x1, perch.y, perch.y + 3, sprites.PERCH_PALETTE),
                                    (hammock.x0, hammock.x1, hammock.y - 3, hammock.y + 2, sprites.HAMMOCK_PALETTE),
                                    (box.x, box.x + box.w, box.y, box.y + box.h, sprites.BOX_PALETTE)):
        assert colours(furnished, x0, x1, y0, y1) & set(palette.values())
        assert not colours(bare, x0, x1, y0, y1) & set(palette.values())


def test_a_cat_in_the_box_peeks_out_over_the_front():
    centre = ROOM.box.x + ROOM.box.w / 2
    cat = CatView("Mango", "tabby", "loaf", "sleep", centre, ROOM.floor.y, in_box=True)
    canvas = render(cat)
    fur = sprites.COATS["tabby"]["f"]
    front_top = ROOM.floor.y - len(sprites.BOX_FRONT)
    left, right = round(centre - 6), round(centre + 6)
    assert fur in colours(canvas, left, right, ROOM.floor.y - 15, front_top)  # the head shows
    assert fur not in colours(canvas, left, right, front_top + 1, ROOM.floor.y)  # the body doesn't


def test_a_cat_walking_past_the_box_is_in_front_of_it():
    centre = ROOM.box.x + ROOM.box.w / 2
    cat = CatView("Mango", "tabby", "sit", "ok", centre, ROOM.floor.y)
    fur = sprites.COATS["tabby"]["f"]
    assert fur in colours(render(cat), round(centre - 4), round(centre + 4), ROOM.floor.y - 4, ROOM.floor.y)


def test_catnip_and_the_laser_dot_are_drawn_where_they_are():
    canvas = render(catnip=20.0, laser=(50.0, ROOM.shelf.y))
    assert set(sprites.CATNIP_PALETTE.values()) & colours(canvas, 14, 27, ROOM.floor.y - 6, ROOM.floor.y)
    assert set(sprites.LASER_PALETTE.values()) & colours(canvas, 48, 53, ROOM.shelf.y - 4, ROOM.shelf.y)


@pytest.mark.parametrize("pose", ["roll0", "roll1"])
def test_a_rolling_cat_can_be_drawn(pose):
    cat = CatView("Mango", "calico", pose, "blink", 40.0, ROOM.floor.y)
    assert sprites.COATS["calico"]["f"] in colours(render(cat), 30, 51, ROOM.floor.y - 14, ROOM.floor.y)


def test_buying_furniture_lets_every_cat_carry_on():
    world = room("Mango", owned=())
    world.wallet.treats = 100
    world.set_mode(Mode.PLAY)
    run(world, 5)
    body = world.bodies["Mango"]
    before = (body.step, list(body.plan), body.x)
    world.buy("hammock")
    assert (body.step, body.plan, body.x) == before
