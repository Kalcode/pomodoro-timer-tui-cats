import pytest

from canvas_reading import read_big, screen_text
from pomo.clock import FakeClock
from pomo.game.playscape import MIN_HEIGHT, layout
from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.render.scene import (
    BLINK_EVERY, CLOCK_PY, CLOCK_X, PANEL_WIDTH, TWINKLE_FRAMES, CatSprite, blinking, draw,
)
from pomo.timer import PomodoroTimer, TimerSettings

W, H = 100, 29  # 100×30 terminal minus the message line
MANGO = CatSprite("Mango", "tabby", "sit", "ok", "floor", 30)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def timer(clock):
    return PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), clock)


def render(timer, cats=(), frame=1, width=W, height=H) -> Canvas:
    canvas = Canvas(width, height, (0, 0, 0))
    draw(canvas, timer, cats, frame)
    return canvas


def clock_ink(canvas: Canvas) -> set:
    return {canvas.pixel_at(x, py) for x in range(CLOCK_X, CLOCK_X + 25)
            for py in range(CLOCK_PY, CLOCK_PY + 7)} - {theme.PANEL_BG}


def test_the_panel_shows_the_phase_counts_and_keys(timer):
    text = screen_text(render(timer))
    for expected in ["● FOCUS", "space to start", "pomodoro 1 of 4", "next: 5 min break",
                     "space start/pause", "q quit"]:
        assert expected in text


def test_the_clock_shows_the_time_left(timer, clock):
    assert read_big(render(timer), CLOCK_X, CLOCK_PY, theme.PANEL_BG) == "25:00"
    timer.start()
    clock.advance(61)
    assert read_big(render(timer), CLOCK_X, CLOCK_PY, theme.PANEL_BG) == "23:59"


def test_the_clock_colour_follows_the_phase(timer, clock):
    assert clock_ink(render(timer)) == {theme.IDLE_CLOCK}
    timer.start()
    assert clock_ink(render(timer)) == {theme.FOCUS}
    clock.advance(25 * 60)
    timer.tick()
    assert clock_ink(render(timer)) == {theme.BREAK}


def test_panel_text_never_spills_into_the_room(clock):
    timer = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 1), clock)
    timer.start()
    clock.advance(25 * 60)
    timer.tick()
    timer.pause()  # "● LONG BREAK" / "paused"
    canvas = render(timer)
    assert "LONG BREAK" in screen_text(canvas)
    assert all(canvas.row_text(y)[PANEL_WIDTH:].strip() == "" for y in range(H))


def test_a_clock_too_wide_for_the_panel_is_cut_at_the_edge(timer):
    timer.adjust(+100)  # 125:00 would be 31 columns
    canvas = render(timer)
    assert all(canvas.pixel_at(PANEL_WIDTH, py) == theme.ROOM_BG for py in range(CLOCK_PY, CLOCK_PY + 7))


def test_the_room_has_its_furniture(timer):
    canvas = render(timer)
    room = layout(W - PANEL_WIDTH, H * 2)
    assert canvas.pixel_at(PANEL_WIDTH + room.tree_top.x0, room.tree_top.y) == theme.PLATFORM
    assert canvas.pixel_at(PANEL_WIDTH + room.shelf.x0, room.shelf.y) == theme.SHELF
    assert canvas.pixel_at(PANEL_WIDTH + room.door.x, room.door.y) == sprites.DOOR_PALETTE["o"]
    assert canvas.pixel_at(PANEL_WIDTH, room.floor.y) == theme.FLOOR


def test_a_cat_stands_on_its_surface(timer):
    canvas = render(timer, [MANGO])
    floor = layout(W - PANEL_WIDTH, H * 2).floor
    tabby = sprites.COATS["tabby"]
    x = PANEL_WIDTH + MANGO.x
    assert canvas.pixel_at(x + 1, floor.y - 1) == tabby["o"]  # bottom outline, just above the floor
    assert canvas.pixel_at(x + 2, floor.y - 16) == tabby["o"]  # ear tip
    assert canvas.pixel_at(x, floor.y - 16) == theme.ROOM_BG  # transparent corner


def test_a_cat_on_the_tree_top_fits_in_the_smallest_room(timer):
    height = MIN_HEIGHT // 2
    top_cat = CatSprite("Pebble", "grey", "sit", "ok", "tree_top", 3)
    canvas = render(timer, [top_cat], width=PANEL_WIDTH + 70, height=height)
    assert canvas.pixel_at(PANEL_WIDTH + 3 + 2, 0) == sprites.COATS["grey"]["o"]  # the ear tip is on screen


def test_higher_cats_are_drawn_behind_lower_ones(timer):
    room = layout(W - PANEL_WIDTH, H * 2)
    back = CatSprite("Pebble", "grey", "sit", "ok", "tree_mid", 8)
    front = CatSprite("Mango", "tabby", "sit", "ok", "floor", 8)
    canvas = render(timer, [front, back])  # given in the wrong order on purpose
    # the floor cat's ear tip overlaps the tree-mid cat's body
    assert canvas.pixel_at(PANEL_WIDTH + 8 + 2, room.floor.y - 16) == sprites.COATS["tabby"]["o"]


def test_ok_cats_blink_now_and_then():
    blinks = [frame for frame in range(BLINK_EVERY) if blinking("Mango", frame)]
    assert len(blinks) == 2
    assert blinking("Mango", blinks[0] + BLINK_EVERY)


def test_a_blinking_cat_closes_its_eyes(timer):
    frame = next(f for f in range(BLINK_EVERY) if blinking("Mango", f))
    floor = layout(W - PANEL_WIDTH, H * 2).floor
    eye = (PANEL_WIDTH + MANGO.x + 2, floor.y - 16 + 5)  # head row 5: "ofekeff", column 2 is eye
    assert render(timer, [MANGO], frame=frame + 10).pixel_at(*eye) == sprites.COATS["tabby"]["e"]
    assert render(timer, [MANGO], frame=frame).pixel_at(*eye) != sprites.COATS["tabby"]["e"]


def test_sleeping_cats_float_a_z(timer):
    sleeper = CatSprite("Pebble", "grey", "loaf", "sleep", "tree_top", 3)
    assert "z" in screen_text(render(timer, [sleeper]))
    assert "z" not in screen_text(render(timer, [MANGO]))


def test_the_stars_twinkle(timer):
    frames = [render(timer, frame=f * TWINKLE_FRAMES) for f in range(3)]
    keys = [tuple(c.row_key(y) for y in range(H)) for c in frames]
    assert len(set(keys)) == 3


@pytest.mark.parametrize("size", [(0, 0), (10, 3), (40, 10), (PANEL_WIDTH, H)])
def test_small_or_empty_screens_do_not_crash(timer, size):
    render(timer, [MANGO], width=size[0], height=size[1])
