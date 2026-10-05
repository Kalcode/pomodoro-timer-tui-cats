"""A widget that shows a Canvas and repaints only the rows that changed (spec §7).

It also reports the mouse, in its own cells, for the app to turn into tool commands.
"""

from __future__ import annotations

from collections.abc import Callable

from textual import events
from textual.geometry import Region
from textual.message import Message
from textual.strip import Strip
from textual.widget import Widget

from pomo.render.canvas import Canvas
from pomo.render.theme import ROOM_BG


class Stage(Widget):
    DEFAULT_CSS = "Stage { width: 1fr; height: 1fr; }"

    class Pointer(Message):
        """The mouse moved to (col, row). Terminals that report pixels give fractions of a cell."""

        def __init__(self, col: float, row: float) -> None:
            super().__init__()
            self.col, self.row = col, row

    class Pressed(Message):
        """A click at (col, row)."""

        def __init__(self, col: float, row: float) -> None:
            super().__init__()
            self.col, self.row = col, row

    class Left(Message):
        """The mouse left the stage."""

    def __init__(self, draw: Callable[[Canvas], None], *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._draw = draw
        self._canvas = Canvas(0, 0, ROOM_BG)
        self._keys: list[tuple] = []

    @property
    def canvas(self) -> Canvas:
        """The last frame drawn."""
        return self._canvas

    def redraw(self) -> None:
        width, height = self.size.width, self.size.height
        canvas = Canvas(width, height, ROOM_BG)
        self._draw(canvas)
        keys = [canvas.row_key(y) for y in range(height)]
        resized = (width, height) != (self._canvas.width, self._canvas.height)
        changed = [y for y in range(height) if resized or keys[y] != self._keys[y]]
        old = self._keys
        self._canvas, self._keys = canvas, keys
        if resized:
            self.refresh()
        else:
            for y in changed:
                start, end = _changed_span(keys[y], old[y], width)
                self.refresh(Region(start, y, end - start, 1))

    def on_resize(self) -> None:
        self.redraw()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        self.post_message(self.Pointer(event.pointer_x, event.pointer_y))

    def on_click(self, event: events.Click) -> None:
        self.post_message(self.Pressed(event.pointer_x, event.pointer_y))

    def on_leave(self, event: events.Leave) -> None:
        self.post_message(self.Left())

    def render_line(self, y: int) -> Strip:
        if y >= self._canvas.height:
            return Strip.blank(self.size.width)
        return Strip(self._canvas.row_segments(y), self._canvas.width)


def _changed_span(new: tuple, old: tuple, width: int) -> tuple[int, int]:
    """The columns [start, end) where two row keys differ, plus one either side, so a wide glyph
    (which takes two cells) is never split at the edge of a repaint."""
    columns = [x for x in range(width) if any(a[x] != b[x] for a, b in zip(new, old))]
    return max(0, columns[0] - 1), min(width, columns[-1] + 2)
