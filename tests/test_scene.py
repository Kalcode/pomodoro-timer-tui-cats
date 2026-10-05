import pytest
from rich.color import Color

from canvas_reading import read_big, screen_text
from pomo.clock import FakeClock
from pomo.game.playscape import layout
from pomo.game.world import BallView, CatView, CursorView, EffectView, RoomView, RosterLine, StringView
from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.render.scene import (
    BLINK_EVERY, CLOCK_PY, CLOCK_X, MIN_ROWS, PANEL_WIDTH, PULSE_FRAMES, ROSTER_ROW, TWINKLE_FRAMES, blinking, draw,
    room_point, too_small,
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
    rows = MIN_ROWS - 2  # a 100×30 terminal, less the message line and the toolbar
    small = layout(70, rows * 2)
    top_cat = CatView("Pebble", "grey", "sit", "ok", x=small.tree_top.x0 + 8.5, feet=small.tree_top.y)
    canvas = render(timer, [top_cat], width=PANEL_WIDTH + 70, height=rows)
    ear_tip = small.tree_top.y - 16
    assert ear_tip >= 0
    assert canvas.pixel_at(PANEL_WIDTH + small.tree_top.x0 + 2, ear_tip) == sprites.COATS["grey"]["o"]


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


def render_room(timer, **room) -> Canvas:
    canvas = Canvas(W, H, (0, 0, 0))
    draw(canvas, timer, RoomView(**room), 1)
    return canvas


def column_colours(canvas: Canvas, x: int, rows: range) -> set:
    return {canvas.pixel_at(x, py) for py in rows}


def test_the_idle_panel_hides_the_timer(timer):
    canvas = Canvas(W, H, (0, 0, 0))
    draw(canvas, timer, RoomView(roster=(RosterLine("Mango", 4, "content"),)), 1, idle=True)
    text = screen_text(canvas)
    for expected in ["● IDLE", "i to go back to pomodoro", "just hanging out", "Mango  ♥♥♥♥♡ content",
                     "i back to pomodoro"]:
        assert expected in text
    for gone in ["FOCUS", "pomodoro 1 of 4", "next:"]:
        assert gone not in text
    assert clock_ink(canvas) == set()


def test_the_key_hints_name_the_tools_and_idle(timer):
    assert "1-5 tools  esc drop  i idle" in screen_text(render(timer))


def test_poops_sit_on_the_floor(timer):
    canvas = render_room(timer, poops=((20.5, FLOOR),))  # 7 wide, so the left edge is column 17
    assert canvas.pixel_at(PANEL_WIDTH + 17, FLOOR - 1) == sprites.POOP_PALETTE["o"]
    assert canvas.pixel_at(PANEL_WIDTH + 20, FLOOR - 4) == sprites.POOP_PALETTE["o"]  # the tip


def test_the_ball_rolls_between_its_two_frames(timer):
    frames = [render_room(timer, ball=BallView(40.0, FLOOR, f)) for f in (0, 1)]
    spot = (PANEL_WIDTH + 38 + 1, FLOOR - 5 + 1)  # 5×5 yarn: left edge 37.5 → 38, top at FLOOR - 5
    assert frames[0].pixel_at(*spot) == sprites.YARN_PALETTE["r"]
    assert frames[1].pixel_at(*spot) == sprites.YARN_PALETTE["l"]


def test_the_string_hangs_from_the_ceiling_to_a_feather(timer):
    canvas = render_room(timer, string=StringView(anchor=40.0, tip_x=40.0, tip_y=20.0))
    assert column_colours(canvas, PANEL_WIDTH + 40, range(0, 20)) == {theme.STRING}
    assert canvas.pixel_at(PANEL_WIDTH + 40, 21) == sprites.TEASER_PALETTE["F"]


def test_a_swinging_string_leans_towards_its_tip(timer):
    canvas = render_room(timer, string=StringView(anchor=40.0, tip_x=50.0, tip_y=20.0))
    assert canvas.pixel_at(PANEL_WIDTH + 40, 0) == theme.STRING
    assert canvas.pixel_at(PANEL_WIDTH + 45, 10) == theme.STRING
    assert canvas.pixel_at(PANEL_WIDTH + 49, 19) in (theme.STRING, theme.ROOM_BG)
    assert canvas.pixel_at(PANEL_WIDTH + 50, 21) == sprites.TEASER_PALETTE["F"]


@pytest.mark.parametrize("tool", ["feed", "ball", "pet", "scoop"])
def test_the_tool_is_drawn_with_its_hotspot_on_the_pointer(timer, tool):
    grid, palette, (hx, hy) = sprites.CURSORS[tool]
    canvas = render_room(timer, cursor=CursorView(tool, 20.0, 30.0))
    assert canvas.pixel_at(PANEL_WIDTH + 20, 30) == palette[grid[hy][hx]]
    assert canvas.pixel_at(PANEL_WIDTH + 20 - hx, 30 - hy) == palette.get(grid[0][0], theme.ROOM_BG)


def test_the_hand_pats_while_it_is_on_a_cat(timer):
    still = render_room(timer, cursor=CursorView("pet", 20.0, 30.0))
    patting = render_room(timer, cursor=CursorView("pet", 20.0, 30.0, busy=True))
    top_row = [(PANEL_WIDTH + 16 + dx, 26) for dx in range(9)]  # hotspot (4, 4): the sprite's top row
    assert any(still.pixel_at(*p) != theme.ROOM_BG for p in top_row)
    assert all(patting.pixel_at(*p) == theme.ROOM_BG for p in top_row)  # the patting hand's top row is empty


def test_the_string_tool_has_no_sprite_of_its_own(timer):
    plain = render_room(timer)
    holding = render_room(timer, cursor=CursorView("string", 20.0, 30.0))
    assert all(plain.row_key(y) == holding.row_key(y) for y in range(H))


def test_the_tool_is_drawn_over_the_cats(timer):
    grid, palette, (hx, hy) = sprites.CURSORS["pet"]
    canvas = render_room(timer, cats=(MANGO,), cursor=CursorView("pet", 38.0, float(FLOOR - 8)))
    assert canvas.pixel_at(PANEL_WIDTH + 38, FLOOR - 8) == palette[grid[hy][hx]]


@pytest.mark.parametrize("kind, text", [("heart", "♥"), ("hiss", "#@!"), ("swat", "swat!")])
def test_effects_float_over_the_room(timer, kind, text):
    canvas = render_room(timer, cats=(MANGO,), effects=(EffectView(kind, 38.0, 30.0),))
    assert text in canvas.row_text(15)
    (segment,) = [s for s in canvas.row_segments(15) if text in s.text]
    assert segment.style.color == Color.from_rgb(*theme.EFFECT_COLORS[kind])


def test_an_effect_that_floated_off_the_top_is_gone(timer):
    canvas = render_room(timer, effects=(EffectView("heart", 38.0, -3.0),))
    assert "♥" not in screen_text(canvas)


@pytest.mark.parametrize("col, row, point", [
    (35, 10, (5.0, 20.0)),
    (35.4, 10.5, (5.0, 21.0)),  # a terminal that reports pixels: the lower half of the cell
    (PANEL_WIDTH, 1, (0.0, 2.0)),
    (98, 27, (68.0, 54.0)),
    (PANEL_WIDTH - 1, 10, None),  # over the timer panel
    (50, 0, None),  # the top row: on the way out of the window
    (99, 10, None),  # the last column: the same
])
def test_room_point_maps_the_pointer_into_the_room(col, row, point):
    assert room_point(col, row, 100) == point


def test_nothing_in_the_room_draws_over_the_panel(timer):
    def panel(canvas):
        return [(canvas.pixel_at(x, py), canvas.char_at(x, py // 2)) for x in range(PANEL_WIDTH) for py in range(H * 2)]

    crowded = render_room(
        timer,
        cats=(CatView("Mango", "tabby", "walk0", "ok", x=5.0, feet=FLOOR, facing=-1),),
        cursor=CursorView("pet", 1.0, 30.0),
        string=StringView(anchor=2.0, tip_x=-6.0, tip_y=20.0),
        effects=(EffectView("swat", 0.0, 30.0),),
    )
    assert panel(crowded) == panel(render_room(timer))


# --- the too-small screen (spec §6) -------------------------------------------------

def render_small(timer, columns, rows, idle=False, roster=(RosterLine("Mango", 4, "content", "grey"),)):
    """What the stage shows in a columns×rows terminal (the toolbar is hidden then: one row for the message)."""
    canvas = Canvas(columns, rows - 1, (0, 0, 0))
    draw(canvas, timer, RoomView(cats=(MANGO,), roster=roster), 1, idle=idle, terminal=(columns, rows))
    return canvas


@pytest.mark.parametrize("size, small", [((100, 30), False), ((99, 30), True), ((100, 29), True), ((80, 24), True)])
def test_the_room_needs_a_100_by_30_terminal(size, small):
    assert too_small(*size) is small


def test_a_small_terminal_asks_for_room_and_keeps_the_timer_on_screen(timer):
    text = screen_text(render_small(timer, 80, 24))
    assert "The cats need more room." in text
    assert "Make the window at least 100×30 (it's 80×24 now)." in text
    assert "● FOCUS  25:00  space to start" in text


def test_the_too_small_screen_shows_a_sad_cat_in_the_first_cats_coat(timer):
    canvas = render_small(timer, 80, 24)
    grey = sprites.COATS["grey"]["f"]
    assert any(canvas.pixel_at(x, py) == grey for x in range(80) for py in range(46))
    assert all(canvas.pixel_at(x, py) != sprites.COATS["tabby"]["f"] for x in range(80) for py in range(46))


def test_the_room_is_not_drawn_on_the_too_small_screen(timer):
    canvas = render_small(timer, 80, 24)
    assert all(canvas.pixel_at(x, py) != theme.FLOOR for x in range(80) for py in range(46))


def test_idle_shows_on_the_too_small_screen(timer):
    assert "● IDLE" in screen_text(render_small(timer, 80, 24, idle=True))


def test_a_tiny_terminal_skips_the_cat_and_cuts_the_text(timer):
    canvas = render_small(timer, 20, 6)
    text = screen_text(canvas)
    assert "The cats need more" in text
    assert all(canvas.pixel_at(x, py) == theme.PANEL_BG for x in range(20) for py in range(10)
               if canvas.char_at(x, py // 2) is None)


def test_the_canvas_alone_decides_when_no_terminal_size_is_given(timer):
    assert "The cats need more room." not in screen_text(render(timer, height=MIN_ROWS - 2))
    assert "The cats need more room." in screen_text(render(timer, height=MIN_ROWS - 3))


def test_idle_hints_drop_the_timer_keys(timer):
    canvas = Canvas(W, H, (0, 0, 0))
    draw(canvas, timer, RoomView(), 1, idle=True)
    text = screen_text(canvas)
    for hint in ["i back to pomodoro", "1-5 tools  esc drop", "q quit"]:
        assert hint in text
    assert "space start/pause" not in text


def test_theme_colours_can_be_written_as_css():
    assert theme.css((26, 28, 40)) == "#1a1c28"


def test_a_waiting_phase_pulses_the_clock_and_says_space_to_start(clock):
    waiting = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4, auto_continue=False), clock)
    waiting.start()
    clock.advance(25 * 60)
    waiting.tick()

    def frame(n):
        canvas = Canvas(W, H, (0, 0, 0))
        draw(canvas, waiting, RoomView(), n, waiting=True)
        return canvas

    bright, dim = frame(0), frame(PULSE_FRAMES)
    assert theme.BREAK in clock_ink(bright) and theme.BREAK not in clock_ink(dim)
    assert "break time: space to start" in screen_text(bright)
    (label,) = [s for s in bright.row_segments(1) if "SHORT BREAK" in s.text]
    assert label.style.color == Color.from_rgb(*theme.BREAK)  # the phase name stays lit
