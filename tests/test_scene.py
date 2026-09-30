import pytest
from rich.color import Color

from canvas_reading import read_big, screen_text
from pomo.clock import FakeClock
from pomo.game.playscape import MIN_HEIGHT, layout
from pomo.game.world import CatView, RoomView, RosterLine
from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.render.scene import (
    BLINK_EVERY, CLOCK_PY, CLOCK_X, PANEL_WIDTH, ROSTER_ROW, TWINKLE_FRAMES, blinking, draw,
)
from pomo.timer import PomodoroTimer, TimerSettings

W, H = 100, 29  # 100×30 terminal minus the message line
ROOM = layout(W - PANEL_WIDTH, H * 2)
FLOOR = ROOM.floor.y
MANGO = CatView("Mango", "tabby", "sit", "ok", x=38.5, feet=FLOOR)  # centre 38.5 → left edge at room column 30


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def timer(clock):
    return PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), clock)


def render(timer, cats=(), frame=1, width=W, height=H, roster=(), bowl_full=True) -> Canvas:
    canvas = Canvas(width, height, (0, 0, 0))
    draw(canvas, timer, RoomView(tuple(cats), tuple(roster), bowl_full), frame)
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
    canvas = render(timer, roster=[RosterLine("Butterscotch", 5, "furious")])
    assert "LONG BREAK" in screen_text(canvas)
    assert all(canvas.row_text(y)[PANEL_WIDTH:].strip() == "" for y in range(H))


def test_a_clock_too_wide_for_the_panel_is_cut_at_the_edge(timer):
    timer.adjust(+100)  # 125:00 would be 31 columns
    canvas = render(timer)
    assert all(canvas.pixel_at(PANEL_WIDTH, py) == theme.ROOM_BG for py in range(CLOCK_PY, CLOCK_PY + 7))


def test_a_clock_of_100_minutes_or_more_closes_up_to_fit_the_panel(clock):
    timer = PomodoroTimer(TimerSettings.from_minutes(120, 5, 15, 4), clock)
    canvas = render(timer)
    assert read_big(canvas, CLOCK_X, CLOCK_PY, theme.PANEL_BG, gap=0) == "120:00"
    assert read_big(render(PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), clock)),
                    CLOCK_X, CLOCK_PY, theme.PANEL_BG) == "25:00"  # normal clocks keep their spacing


def test_the_room_has_its_furniture(timer):
    canvas = render(timer)
    assert canvas.pixel_at(PANEL_WIDTH + ROOM.tree_top.x0, ROOM.tree_top.y) == theme.PLATFORM
    assert canvas.pixel_at(PANEL_WIDTH + ROOM.shelf.x0, ROOM.shelf.y) == theme.SHELF
    assert canvas.pixel_at(PANEL_WIDTH + ROOM.door.x, ROOM.door.y) == sprites.DOOR_PALETTE["o"]
    assert canvas.pixel_at(PANEL_WIDTH, FLOOR) == theme.FLOOR


def test_the_bowl_shows_whether_it_has_kibble(timer):
    kibble = (PANEL_WIDTH + ROOM.bowl.x + 1, ROOM.bowl.y)  # BOWL_FULL row 0: ".kkkkkk."
    assert render(timer).pixel_at(*kibble) == sprites.BOWL_PALETTE["k"]
    assert render(timer, bowl_full=False).pixel_at(*kibble) == sprites.BOWL_PALETTE["o"]


def test_a_cat_stands_where_the_world_says(timer):
    canvas = render(timer, [MANGO])
    tabby = sprites.COATS["tabby"]
    x = PANEL_WIDTH + 30
    assert canvas.pixel_at(x + 1, FLOOR - 1) == tabby["o"]  # bottom outline, just above the floor
    assert canvas.pixel_at(x + 2, FLOOR - 16) == tabby["o"]  # ear tip
    assert canvas.pixel_at(x, FLOOR - 16) == theme.ROOM_BG  # transparent corner


def test_a_cat_on_the_tree_top_fits_in_the_smallest_room(timer):
    small = layout(70, MIN_HEIGHT)
    top_cat = CatView("Pebble", "grey", "sit", "ok", x=small.tree_top.x0 + 8.5, feet=small.tree_top.y)
    canvas = render(timer, [top_cat], width=PANEL_WIDTH + 70, height=MIN_HEIGHT // 2)
    assert canvas.pixel_at(PANEL_WIDTH + small.tree_top.x0 + 2, 0) == sprites.COATS["grey"]["o"]  # ear tip


def test_higher_cats_are_drawn_behind_lower_ones(timer):
    back = CatView("Pebble", "grey", "sit", "ok", x=16.5, feet=ROOM.tree_mid.y)
    front = CatView("Mango", "tabby", "sit", "ok", x=16.5, feet=FLOOR)
    canvas = render(timer, [front, back])  # given in the wrong order on purpose
    # the floor cat's ear tip overlaps the tree-mid cat's body
    assert canvas.pixel_at(PANEL_WIDTH + 8 + 2, FLOOR - 16) == sprites.COATS["tabby"]["o"]


def test_side_view_cats_face_the_way_they_walk(timer):
    def eye_column(facing: int) -> int:
        walker = CatView("Mango", "tabby", "walk0", "ok", x=40, feet=FLOOR, facing=facing)
        canvas = render(timer, [walker], frame=10)
        eye_py = FLOOR - 13 + 4  # side sprites are 13 tall; row 4 holds the eye
        return next(x for x in range(PANEL_WIDTH, W) if canvas.pixel_at(x, eye_py) == sprites.COATS["tabby"]["e"])

    centre = PANEL_WIDTH + 40
    assert eye_column(1) > centre > eye_column(-1)


def test_a_cat_mid_jump_is_drawn_in_the_air(timer):
    leaper = CatView("Mango", "tabby", "leap", "ok", x=40, feet=FLOOR - 10)
    canvas = render(timer, [leaper])
    assert all(canvas.pixel_at(x, FLOOR - 1) != sprites.COATS["tabby"]["o"]
               for x in range(PANEL_WIDTH + 25, PANEL_WIDTH + 55))  # nothing touching the floor


def test_ok_cats_blink_now_and_then():
    blinks = [frame for frame in range(BLINK_EVERY) if blinking("Mango", frame)]
    assert len(blinks) == 2
    assert blinking("Mango", blinks[0] + BLINK_EVERY)


def test_a_blinking_cat_closes_its_eyes(timer):
    frame = next(f for f in range(BLINK_EVERY) if blinking("Mango", f))
    eye = (PANEL_WIDTH + 30 + 2, FLOOR - 16 + 5)  # head row 5: "ofekeff", column 2 is eye
    assert render(timer, [MANGO], frame=frame + 10).pixel_at(*eye) == sprites.COATS["tabby"]["e"]
    assert render(timer, [MANGO], frame=frame).pixel_at(*eye) != sprites.COATS["tabby"]["e"]


def test_sleeping_cats_float_a_z(timer):
    sleeper = CatView("Pebble", "grey", "loaf", "sleep", x=ROOM.tree_top.x0 + 8.5, feet=ROOM.tree_top.y)
    assert "z" in screen_text(render(timer, [sleeper]))
    assert "z" not in screen_text(render(timer, [MANGO]))


def test_bubbles_float_over_the_cat(timer):
    beggar = CatView("Mango", "tabby", "sit", "ok", x=38.5, feet=FLOOR, bubble="meow")
    text = screen_text(render(timer, [beggar]))
    assert "meow" in text
    row = next(y for y in range(H) if "meow" in render(timer, [beggar]).row_text(y))
    assert row < (FLOOR - 16) // 2  # above the head


def test_the_roster_lists_each_cat_with_hearts_and_mood(timer):
    roster = [RosterLine("Mango", 4, "content"), RosterLine("Pebble", 2, "grumpy")]
    canvas = render(timer, roster=roster)
    assert canvas.row_text(ROSTER_ROW).strip() == "cats"
    assert canvas.row_text(ROSTER_ROW + 1).strip() == "Mango  ♥♥♥♥♡ content"
    assert canvas.row_text(ROSTER_ROW + 2).strip() == "Pebble ♥♥♡♡♡ grumpy"
    (grumpy,) = [s for s in canvas.row_segments(ROSTER_ROW + 2) if "grumpy" in s.text]
    assert grumpy.style.color == Color.from_rgb(*theme.STAGE_COLORS["grumpy"])


def test_no_cats_means_no_roster_header(timer):
    assert "cats" not in screen_text(render(timer))


def test_the_stars_twinkle(timer):
    frames = [render(timer, frame=f * TWINKLE_FRAMES) for f in range(3)]
    keys = [tuple(c.row_key(y) for y in range(H)) for c in frames]
    assert len(set(keys)) == 3


@pytest.mark.parametrize("size", [(0, 0), (10, 3), (40, 10), (PANEL_WIDTH, H)])
def test_small_or_empty_screens_do_not_crash(timer, size):
    render(timer, [MANGO], width=size[0], height=size[1], roster=[RosterLine("Mango", 4, "content")])
