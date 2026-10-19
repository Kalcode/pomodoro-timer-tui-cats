import random

from textual.widgets import Static

from canvas_reading import screen_text
from pomo.clock import FakeClock
from pomo.config import Config
from pomo.game import balance
from pomo.game.cat import COATS, Cat, Trait
from pomo.game.events import Adopted, FocusCompleted, StrayArrived
from pomo.game.playscape import layout
from pomo.game.world import RoomView, RosterLine, Stray, StrayView, World
from pomo.notify import NullNotifier
from pomo.render import sprites
from pomo.render.canvas import Canvas
from pomo.render.scene import PANEL_WIDTH, ROSTER_ROW, draw
from pomo.timer import PomodoroTimer, TimerSettings
from pomo.ui import view
from pomo.ui.app import PomoApp
from pomo.ui.dialogs import ConfirmScreen
from pomo.ui.stage import Stage

SIZE = (100, 30)


def room(*names: str, seed: int = 5) -> World:
    return World([Cat(n, "tabby", Trait.CLINGY) for n in names], random.Random(seed))


def finish_focus(world: World, times: int = 1) -> None:
    for _ in range(times):
        world.apply([FocusCompleted(25)])


# --- when strays come ----------------------------------------------------------


def test_the_first_stray_turns_up_after_four_focus_sessions():
    world = room("Mango")
    finish_focus(world, 3)
    assert world.stray is None
    finish_focus(world)
    assert world.stray is not None
    assert world.take_news()[-1] == StrayArrived(world.stray.name)


def test_the_next_stray_needs_twelve_more_once_the_first_is_adopted():
    world = room("Mango")
    world.wallet.treats = 100
    finish_focus(world, 4)
    assert world.adopt()
    finish_focus(world, 11)  # 15 in all
    assert world.stray is None
    finish_focus(world)  # 16
    assert world.stray is not None


def test_one_stray_waits_at_a_time():
    world = room("Mango")
    finish_focus(world, 4)
    first = world.stray
    finish_focus(world, 30)
    assert world.stray == first


def test_a_save_with_plenty_of_focus_behind_it_brings_strays_one_focus_at_a_time():
    world = room("Mango")
    world.focus_total, world.wallet.treats = 40, 100
    assert world.stray is None  # nothing until a focus completes
    finish_focus(world)
    assert world.adopt()
    assert world.stray is None
    finish_focus(world)
    assert world.stray is not None


def test_the_room_holds_five_cats_at_most():
    world = room("Mango", "Pebble", "Miso", "Tux", "Noodle")
    finish_focus(world, 100)
    assert world.stray is None


def test_a_stray_has_a_new_name_and_if_it_can_a_new_coat():
    world = room(*balance.STRAY_NAMES[:3], "Mango")
    finish_focus(world, 40)
    assert world.stray.name not in {c.name for c in world.cats}
    assert world.stray.coat != "tabby" and world.stray.coat in COATS
    assert COATS == tuple(sprites.COATS)


# --- adopting ------------------------------------------------------------------


def test_adopting_costs_ten_treats_and_the_cat_comes_in_through_the_door():
    world = room("Mango")
    world.stray, world.wallet.treats = Stray("Pebble", "grey", Trait.CHILL), 12
    assert world.adopt()
    assert world.stray is None and world.wallet.treats == 2
    pebble = world.cats[-1]
    assert (pebble.name, pebble.coat, pebble.trait, pebble.mood) == ("Pebble", "grey", Trait.CHILL, 80)
    assert pebble.needs["hunger"] == balance.STRAY_HUNGER
    door = world.scape.door
    assert world.bodies["Pebble"].x == door.x + door.w / 2
    assert world.take_news() == [Adopted("Pebble")]
    for _ in range(40):
        world.tick(0.125)
    assert world.bodies["Pebble"].x < door.x  # walked in
    assert [r.name for r in world.view().roster] == ["Mango", "Pebble"]


def test_no_treats_no_adoption():
    world = room("Mango")
    world.stray, world.wallet.treats = Stray("Pebble", "grey", Trait.CHILL), 9
    assert not world.adopt()
    assert world.stray is not None and len(world.cats) == 1 and world.wallet.treats == 9


def test_the_stray_is_on_the_window():
    world = room("Mango")
    w = world.scape.window
    assert not world.stray_at(w.x + 3, w.y + 3)
    world.stray = Stray("Pebble", "grey", Trait.CHILL)
    assert world.stray_at(w.x + 3, w.y + 3)
    assert not world.stray_at(w.x - 3, w.y + 3)
    assert world.view().stray == StrayView("Pebble", "grey")


# --- drawing -------------------------------------------------------------------

W, H = 100, 28


def render(stray: StrayView | None, roster=(RosterLine("Mango", 4, "content"),)) -> Canvas:
    canvas = Canvas(W, H, (0, 0, 0))
    timer = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), FakeClock())
    draw(canvas, timer, RoomView(roster=roster, stray=stray), 1)
    return canvas


def test_a_stray_peers_in_through_the_window_with_a_question_mark():
    window = layout(W - PANEL_WIDTH, H * 2).window
    inside = {(PANEL_WIDTH + window.x + dx, window.y + dy) for dx in range(1, window.w - 1)
              for dy in range(1, window.h - 1)}
    without, with_stray = render(None), render(StrayView("Pebble", "siamese"))
    fur = sprites.COATS["siamese"]["f"]
    assert all(without.pixel_at(x, py) != fur for x, py in inside)
    assert sum(with_stray.pixel_at(x, py) == fur for x, py in inside) > 10
    assert "?" in with_stray.row_text(max(0, window.y // 2 - 1))[PANEL_WIDTH:]
    outside = [(PANEL_WIDTH + window.x + dx, window.y + window.h + 1) for dx in range(window.w)]
    assert all(with_stray.pixel_at(x, py) != fur for x, py in outside)  # cut to the glass


def test_the_panel_says_who_is_at_the_window_and_how_to_adopt():
    canvas = render(StrayView("Pebble", "grey"))
    text = screen_text(canvas)
    assert "? Pebble is at the window" in text
    assert f"a to adopt ({balance.ADOPT_PRICE} 🐟)" in text
    assert canvas.row_text(ROSTER_ROW + 3).strip() == "? Pebble is at the window"
    assert "at the window" not in screen_text(render(None))


# --- the app -------------------------------------------------------------------


def make_app(treats: int):
    app = PomoApp(Config(), FakeClock(), NullNotifier(), rng=random.Random(0))
    app.world.stray = Stray("Pebble", "grey", Trait.DIVA)
    app.world.wallet.treats = treats
    return app


def message(app):
    return str(app.main.query_one("#message", Static).render())


async def test_a_asks_first_and_yes_brings_the_stray_in():
    app = make_app(treats=15)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("a")
        assert isinstance(app.screen, ConfirmScreen)
        assert app.screen.question == "Adopt Pebble for 10 🐟? A grey cat, and a bit of a diva."
        await pilot.press("y")
        assert [c.name for c in app.world.cats] == ["Mango", "Pebble"]
        assert app.world.wallet.treats == 5
        assert message(app) == "Pebble comes in through the door. Welcome home, Pebble!"


async def test_no_leaves_the_stray_at_the_window():
    app = make_app(treats=15)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("a", "n")
        assert app.world.stray is not None and len(app.world.cats) == 1


async def test_too_few_treats_says_how_many_more():
    app = make_app(treats=4)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("a")
        assert app.screen is app.main
        assert message(app) == "Pebble would love to come in. Adopting is 10 🐟: you need 6 more."


async def test_clicking_the_stray_asks_to_adopt_it():
    app = make_app(treats=15)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.pause()
        window = app.world.scape.window
        await pilot.click(Stage, offset=(PANEL_WIDTH + window.x + 4, (window.y + 4) // 2))
        assert isinstance(app.screen, ConfirmScreen)


async def test_a_with_nobody_at_the_window():
    app = make_app(treats=15)
    app.world.stray = None
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("a")
        assert message(app) == view.NO_STRAY
