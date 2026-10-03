"""The whole screen: the timer panel on the left, the cat room on the right (spec §6–§7).

Pure: the timer, a RoomView from the world and an animation frame number in, pixels
out. It never reads the clock and never changes the game. `room_point` goes the other
way, from where the mouse is on screen to where that is in the room.
"""

from __future__ import annotations

from collections.abc import Mapping

from pomo.game.playscape import Box, Playscape, layout
from pomo.game.world import BallView, CatView, CursorView, EffectView, RoomView, RosterLine, StringView
from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.render.font import draw_big, text_width
from pomo.render.theme import RGB
from pomo.timer import PomodoroTimer
from pomo.ui import view

PANEL_WIDTH = 30
TEXT_X = 2
PHASE_ROW, STATE_ROW = 1, 2
CLOCK_X, CLOCK_PY = 2, 8  # the 7-pixel clock covers text rows 4-7
BAR_ROW = 9
CLOCK_ROOM = PANEL_WIDTH - CLOCK_X - 1  # columns the clock may use
BAR_WIDTH = 25  # the same width as "18:42"
COUNT_ROW, NEXT_ROW = 11, 12
ROSTER_ROW = 14  # "cats", then one line per cat
ROSTER_HEARTS_X = TEXT_X + 7
ROSTER_STAGE_X = ROSTER_HEARTS_X + 6
KEY_HINTS = ("space start/pause   s skip", "r reset  +/- 5 min  q quit", "1-5 tools  esc drop  i idle")
IDLE_LABEL, IDLE_HINT, IDLE_TEXT = "● IDLE", "i to go back to pomodoro", "just hanging out"
IDLE_TEXT_ROW = 6  # where the clock would be
EFFECT_TEXT = {"heart": "♥", "hiss": "#@!", "swat": "swat!"}
MIN_COLUMNS, MIN_ROWS = 100, 30  # the smallest terminal the room fits in (spec §6)
TOO_SMALL = ("The cats need more room.", "Make the window at least 100×30 (it's {w}×{h} now).")

BLINK_EVERY = 48  # frames: about every 6 s at 8 fps
BLINK_FRAMES = 2
STARS = ((2, 3), (9, 2), (8, 8))  # inside the window
TWINKLE_FRAMES = 12


def draw(canvas: Canvas, timer: PomodoroTimer, room_view: RoomView, frame: int, idle: bool = False,
         terminal: tuple[int, int] | None = None) -> None:
    """terminal: the whole screen's size, which defaults to the canvas plus the message line and toolbar."""
    columns, rows = terminal or (canvas.width, canvas.height + 2)
    if too_small(columns, rows):
        _too_small(canvas, timer, room_view, idle, columns, rows)
        return
    canvas.fill(0, 0, canvas.width, canvas.height, theme.ROOM_BG)
    _panel(canvas, timer, room_view.roster, idle)
    room = layout(max(0, canvas.width - PANEL_WIDTH), canvas.height * 2)
    _room(canvas, PANEL_WIDTH, room, room_view, frame)


def too_small(columns: int, rows: int) -> bool:
    return columns < MIN_COLUMNS or rows < MIN_ROWS


def room_point(col: float, row: float) -> tuple[float, float] | None:
    """Where a pointer at (col, row) on screen is in the room: a column and a pixel row. None over the panel.
    Terminals that report the pointer finer than a cell give the half-cell too."""
    if col < PANEL_WIDTH:
        return None
    return float(int(col) - PANEL_WIDTH), float(int(row * 2))


def phase_color(timer: PomodoroTimer) -> RGB:
    if not timer.running:
        return theme.IDLE_CLOCK
    return theme.BREAK if timer.phase.is_break else theme.FOCUS


# --- too small ----------------------------------------------------------------


def _too_small(canvas: Canvas, timer: PomodoroTimer, room_view: RoomView, idle: bool, columns: int, rows: int) -> None:
    """A sad cat and a request for more room. The timer keeps going, so it's shown as text (spec §6)."""
    canvas.fill(0, 0, canvas.width, canvas.height, theme.PANEL_BG)
    if idle:
        clock, color = IDLE_LABEL, theme.IDLE
    else:
        clock = f"{view.phase_label(timer)}  {view.clock_text(timer.remaining())}  {view.phase_state(timer)}".rstrip()
        color = phase_color(timer)
    lines = [(TOO_SMALL[0], theme.TEXT, True), (TOO_SMALL[1].format(w=columns, h=rows), theme.DIM, False),
             ("", theme.DIM, False), (clock, color, True)]
    cat = sprites.cat("loaf", "meh")
    cat_rows = (len(cat) + 1) // 2 + 1  # and a blank row under it
    show_cat = canvas.height >= cat_rows + len(lines) and canvas.width >= len(cat[0])
    row = (canvas.height - len(lines) - (cat_rows if show_cat else 0)) // 2
    if show_cat:
        coat = room_view.roster[0].coat if room_view.roster else "tabby"
        canvas.sprite((canvas.width - len(cat[0])) // 2, row * 2, cat, sprites.COATS[coat])
        row += cat_rows
    for text, color, bold in lines:
        text = text[: canvas.width]
        canvas.text(max(0, (canvas.width - len(text)) // 2), row, text, color, bold=bold)
        row += 1


# --- timer panel ------------------------------------------------------------


def _panel(canvas: Canvas, timer: PomodoroTimer, roster: tuple[RosterLine, ...], idle: bool) -> None:
    canvas.fill(0, 0, PANEL_WIDTH, canvas.height, theme.PANEL_BG)
    if idle:
        _panel_text(canvas, PHASE_ROW, IDLE_LABEL, theme.IDLE, bold=True)
        _panel_text(canvas, STATE_ROW, IDLE_HINT, theme.DIM)
        _panel_text(canvas, IDLE_TEXT_ROW, IDLE_TEXT, theme.TEXT)
    else:
        _timer(canvas, timer)
    _roster(canvas, roster)
    first_hint_row = canvas.height - len(KEY_HINTS) - 1
    for i, hint in enumerate(KEY_HINTS):
        _panel_text(canvas, first_hint_row + i, hint, theme.DIM)


def _timer(canvas: Canvas, timer: PomodoroTimer) -> None:
    color = phase_color(timer)
    _panel_text(canvas, PHASE_ROW, view.phase_label(timer), color, bold=True)
    _panel_text(canvas, STATE_ROW, view.phase_state(timer), theme.DIM)
    clock = view.clock_text(timer.remaining())
    gap = 1 if text_width(clock) <= CLOCK_ROOM else 0  # 100+ minutes: close up so "120:00" still fits
    draw_big(canvas, CLOCK_X, CLOCK_PY, clock, color, gap)
    bar = view.progress_bar(timer, BAR_WIDTH)
    filled = bar.count("█")
    canvas.text(TEXT_X, BAR_ROW, bar[:filled], color)
    canvas.text(TEXT_X + filled, BAR_ROW, bar[filled:], theme.BAR_EMPTY)
    _panel_text(canvas, COUNT_ROW, view.count_line(timer), theme.TEXT)
    _panel_text(canvas, NEXT_ROW, view.next_line(timer), theme.DIM)


def _roster(canvas: Canvas, roster: tuple[RosterLine, ...]) -> None:
    if roster:
        _panel_text(canvas, ROSTER_ROW, "cats", theme.DIM)
    for i, line in enumerate(roster):
        row = ROSTER_ROW + 1 + i
        _panel_text(canvas, row, line.name[:6], theme.TEXT)
        hearts_end = canvas.text(ROSTER_HEARTS_X, row, "♥" * line.hearts, theme.HEART)
        canvas.text(hearts_end, row, "♡" * (5 - line.hearts), theme.HEART_EMPTY)
        canvas.text(ROSTER_STAGE_X, row, line.stage, theme.STAGE_COLORS[line.stage])


def _panel_text(canvas: Canvas, row: int, s: str, color: RGB, bold: bool = False) -> None:
    canvas.text(TEXT_X, row, s[: PANEL_WIDTH - TEXT_X - 1], color, bold=bold)


# --- cat room ---------------------------------------------------------------


def _room(canvas: Canvas, ox: int, room: Playscape, room_view: RoomView, frame: int) -> None:
    canvas.fill(ox, 0, room.width, canvas.height, theme.ROOM_BG)  # also trims a clock too wide for the panel
    _window(canvas, ox, room.window, frame)
    _cat_tree(canvas, ox, room)
    _shelf(canvas, ox, room)
    canvas.rect(ox, room.floor.y, room.width, 1, theme.FLOOR)
    canvas.sprite(ox + room.door.x, room.door.y, sprites.DOOR, sprites.DOOR_PALETTE)
    bowl = sprites.BOWL_FULL if room_view.bowl_full else sprites.BOWL_EMPTY
    canvas.sprite(ox + room.bowl.x, room.bowl.y, bowl, sprites.BOWL_PALETTE)
    for x, y in room_view.poops:
        _standing(canvas, ox, x, y, sprites.POOP, sprites.POOP_PALETTE)
    if room_view.ball is not None:
        _ball(canvas, ox, room_view.ball)
    cats = sorted(room_view.cats, key=lambda c: (c.feet, c.x))  # back (high up) to front (floor)
    drawn = [_cat(canvas, ox, cat, frame) for cat in cats]
    if room_view.string is not None:
        _string(canvas, ox, room_view.string)
    if room_view.cursor is not None:
        _cursor(canvas, ox, room_view.cursor)
    for cat, face, left, top, width in drawn:  # effects go over everything
        _cat_marks(canvas, ox, cat, face, left, top, width, frame)
    for effect in room_view.effects:
        _effect(canvas, ox, effect)


def _window(canvas: Canvas, ox: int, w: Box, frame: int) -> None:
    x = ox + w.x
    canvas.rect(x, w.y, w.w, w.h, theme.WINDOW_FRAME)
    canvas.rect(x + 1, w.y + 1, w.w - 2, w.h - 2, theme.WINDOW_GLASS)
    canvas.rect(x + w.w // 2, w.y + 1, 1, w.h - 2, theme.WINDOW_FRAME)
    canvas.rect(x + 1, w.y + w.h // 2, w.w - 2, 1, theme.WINDOW_FRAME)
    canvas.rect(x - 1, w.y + w.h, w.w + 2, 1, theme.WINDOW_SILL)
    for i, (sx, sy) in enumerate(STARS):
        if (frame // TWINKLE_FRAMES + i) % 3:
            canvas.pixel(x + sx, w.y + sy, theme.STAR)


def _cat_tree(canvas: Canvas, ox: int, room: Playscape) -> None:
    post = room.post
    for y in range(post.y, post.y + post.h):
        canvas.rect(ox + post.x, y, post.w, 1, theme.SISAL if y % 2 else theme.SISAL_DARK)
    for platform in (room.tree_top, room.tree_mid):
        width = platform.x1 - platform.x0
        canvas.rect(ox + platform.x0, platform.y, width, 2, theme.PLATFORM)
        canvas.rect(ox + platform.x0, platform.y + 2, width, 1, theme.PLATFORM_EDGE)
    canvas.rect(ox + post.x - 5, room.floor.y - 2, post.w + 10, 2, theme.PLATFORM)  # base


def _shelf(canvas: Canvas, ox: int, room: Playscape) -> None:
    shelf = room.shelf
    canvas.rect(ox + shelf.x0, shelf.y, shelf.x1 - shelf.x0, 2, theme.SHELF)
    canvas.rect(ox + shelf.x0 + 2, shelf.y + 2, 1, 3, theme.SHELF_BRACKET)
    canvas.rect(ox + shelf.x1 - 3, shelf.y + 2, 1, 3, theme.SHELF_BRACKET)


def _sprite(canvas: Canvas, ox: int, x: int, py: int, grid: sprites.Grid, palette: Mapping[str, RGB]) -> None:
    """A sprite at room column x. Whatever hangs off the room's left edge is cut, so the panel stays clear."""
    cut = max(0, -x)
    if cut:
        grid = tuple(row[cut:] for row in grid)
    canvas.sprite(ox + x + cut, py, grid, palette)


def _text(canvas: Canvas, ox: int, x: int, row: int, s: str, color: RGB) -> None:
    """Bold text from room column x, cut at the room's left edge like a sprite."""
    cut = max(0, -x)
    canvas.text(ox + x + cut, row, s[cut:], color, bold=True)


def _standing(canvas: Canvas, ox: int, x: float, y: int, grid: sprites.Grid, palette: Mapping[str, RGB]) -> None:
    """A sprite centred on column x, standing on pixel row y."""
    _sprite(canvas, ox, round(x - len(grid[0]) / 2), y - len(grid), grid, palette)


def _ball(canvas: Canvas, ox: int, ball: BallView) -> None:
    _standing(canvas, ox, ball.x, ball.y, sprites.YARN[ball.frame], sprites.YARN_PALETTE)


def _string(canvas: Canvas, ox: int, string: StringView) -> None:
    """A line from the ceiling above the mouse down to the swinging tip, with a feather on the end."""
    tip_y = round(string.tip_y)
    for py in range(tip_y):
        x = round(string.anchor + (string.tip_x - string.anchor) * py / tip_y)
        if x >= 0:
            canvas.pixel(ox + x, py, theme.STRING)
    _sprite(canvas, ox, round(string.tip_x) - 1, tip_y, sprites.TEASER, sprites.TEASER_PALETTE)


def _cursor(canvas: Canvas, ox: int, cursor: CursorView) -> None:
    if cursor.tool not in sprites.CURSORS:
        return  # the string is drawn as itself
    grid, palette, (hx, hy) = sprites.CURSORS[cursor.tool]
    if cursor.tool == "pet" and cursor.busy:
        grid = sprites.HAND[1]
    _sprite(canvas, ox, round(cursor.x) - hx, round(cursor.y) - hy, grid, palette)


def _effect(canvas: Canvas, ox: int, effect: EffectView) -> None:
    text = EFFECT_TEXT[effect.kind]
    _text(canvas, ox, round(effect.x) - len(text) // 2, int(effect.y) // 2, text, theme.EFFECT_COLORS[effect.kind])


def _cat(canvas: Canvas, ox: int, cat: CatView, frame: int) -> tuple[CatView, str, int, int, int]:
    face = "blink" if cat.face == "ok" and blinking(cat.name, frame) else cat.face
    grid = sprites.cat(cat.pose, face, cat.facing)
    width = len(grid[0])
    left = round(cat.x - width / 2)  # in the room
    top = cat.feet - len(grid)
    _sprite(canvas, ox, left, top, grid, sprites.COATS[cat.coat])
    return cat, face, left, top, width


def _cat_marks(canvas: Canvas, ox: int, cat: CatView, face: str, left: int, top: int, width: int, frame: int) -> None:
    """A sleeping cat's z, or its bubble."""
    if face == "sleep":
        step = (frame // 6) % 3
        _text(canvas, ox, left + width - 2 + step % 2, top // 2 - step, "z", theme.SLEEP_Z)
    elif cat.bubble:
        _text(canvas, ox, left + width // 2 - 1, top // 2 - 1, cat.bubble, theme.TEXT)


def blinking(name: str, frame: int) -> bool:
    offset = sum(map(ord, name))  # stable per cat (hash() changes every run)
    return (frame + offset) % BLINK_EVERY < BLINK_FRAMES
