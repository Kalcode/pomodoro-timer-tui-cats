"""The whole screen: the timer panel on the left, the cat room on the right (spec §6–§7).

Pure: timer, cats and an animation frame number in, pixels out. It never reads the
clock and never changes the game.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pomo.game.playscape import Box, Playscape, layout
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
KEY_HINTS = ("space start/pause   s skip", "r reset  +/- 5 min  q quit")

BLINK_EVERY = 48  # frames: about every 6 s at 8 fps
BLINK_FRAMES = 2
STARS = ((2, 3), (9, 2), (8, 8))  # inside the window
TWINKLE_FRAMES = 12


@dataclass(frozen=True)
class CatSprite:
    name: str
    coat: str
    pose: str  # a key of sprites.POSES
    face: str  # a key of sprites.FACES; "ok" blinks on its own now and then
    surface: str  # a playscape surface name
    x: int  # room column of the sprite's left edge


def draw(canvas: Canvas, timer: PomodoroTimer, cats: Sequence[CatSprite], frame: int) -> None:
    canvas.fill(0, 0, canvas.width, canvas.height, theme.ROOM_BG)
    _panel(canvas, timer)
    room = layout(max(0, canvas.width - PANEL_WIDTH), canvas.height * 2)
    _room(canvas, PANEL_WIDTH, room, cats, frame)


def phase_color(timer: PomodoroTimer) -> RGB:
    if not timer.running:
        return theme.IDLE_CLOCK
    return theme.BREAK if timer.phase.is_break else theme.FOCUS


# --- timer panel ------------------------------------------------------------


def _panel(canvas: Canvas, timer: PomodoroTimer) -> None:
    canvas.fill(0, 0, PANEL_WIDTH, canvas.height, theme.PANEL_BG)
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
    first_hint_row = canvas.height - len(KEY_HINTS) - 1
    for i, hint in enumerate(KEY_HINTS):
        _panel_text(canvas, first_hint_row + i, hint, theme.DIM)


def _panel_text(canvas: Canvas, row: int, s: str, color: RGB, bold: bool = False) -> None:
    canvas.text(TEXT_X, row, s[: PANEL_WIDTH - TEXT_X - 1], color, bold=bold)


# --- cat room ---------------------------------------------------------------


def _room(canvas: Canvas, ox: int, room: Playscape, cats: Sequence[CatSprite], frame: int) -> None:
    canvas.fill(ox, 0, room.width, canvas.height, theme.ROOM_BG)  # also trims a clock too wide for the panel
    _window(canvas, ox, room.window, frame)
    _cat_tree(canvas, ox, room)
    _shelf(canvas, ox, room)
    canvas.rect(ox, room.floor.y, room.width, 1, theme.FLOOR)
    canvas.sprite(ox + room.door.x, room.door.y, sprites.DOOR, sprites.DOOR_PALETTE)
    canvas.sprite(ox + room.bowl.x, room.bowl.y, sprites.BOWL_FULL, sprites.BOWL_PALETTE)
    for cat in sorted(cats, key=lambda c: (room.surface(c.surface).y, c.x)):  # back (high) to front (low)
        _cat(canvas, ox, room, cat, frame)


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


def _cat(canvas: Canvas, ox: int, room: Playscape, cat: CatSprite, frame: int) -> None:
    face = "blink" if cat.face == "ok" and blinking(cat.name, frame) else cat.face
    grid = sprites.cat(cat.pose, face)
    top = room.surface(cat.surface).y - len(grid)
    canvas.sprite(ox + cat.x, top, grid, sprites.COATS[cat.coat])
    if face == "sleep":
        step = (frame // 6) % 3
        canvas.text(ox + cat.x + 15 + step % 2, top // 2 - step, "z", theme.SLEEP_Z, bold=True)


def blinking(name: str, frame: int) -> bool:
    offset = sum(map(ord, name))  # stable per cat (hash() changes every run)
    return (frame + offset) % BLINK_EVERY < BLINK_FRAMES
