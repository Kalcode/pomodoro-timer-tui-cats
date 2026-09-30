"""A widget that shows a Canvas and repaints only the rows that changed (spec §7)."""

from __future__ import annotations

from collections.abc import Callable

from textual.geometry import Region
from textual.strip import Strip
from textual.widget import Widget

from pomo.render.canvas import Canvas
from pomo.render.theme import ROOM_BG


class Stage(Widget):
    DEFAULT_CSS = "Stage { width: 1fr; height: 1fr; }"

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
        self._canvas, self._keys = canvas, keys
        if resized:
            self.refresh()
        else:
            for y in changed:
                self.refresh(Region(0, y, width, 1))

    def on_resize(self) -> None:
        self.redraw()

    def render_line(self, y: int) -> Strip:
        if y >= self._canvas.height:
            return Strip.blank(self.size.width)
        return Strip(self._canvas.row_segments(y), self._canvas.width)
