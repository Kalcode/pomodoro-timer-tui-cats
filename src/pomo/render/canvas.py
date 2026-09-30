"""A cell buffer where each cell is either two stacked pixels (drawn as ▀) or one text glyph (spec §7).

Coordinates: x is a column, y a text row, py a pixel row (two per text row).
Every drawing call clips at the edges, so callers can draw partly off-canvas.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from rich.cells import cell_len
from rich.color import Color
from rich.segment import Segment
from rich.style import Style

from pomo.render.theme import RGB

HALF_BLOCK = "▀"
WIDE_TAIL = ""  # stands in the cell to the right of a double-width glyph

_STYLES: dict[tuple[RGB | None, RGB, bool], Style] = {}


def _style(fg: RGB | None, bg: RGB, bold: bool) -> Style:
    key = (fg, bg, bold)
    style = _STYLES.get(key)
    if style is None:
        style = _STYLES[key] = Style(
            color=Color.from_rgb(*fg) if fg is not None else None,
            bgcolor=Color.from_rgb(*bg),
            bold=bold or None,
        )
    return style


class Canvas:
    def __init__(self, width: int, height: int, background: RGB) -> None:
        self.width = max(0, width)
        self.height = max(0, height)
        self._top = [[background] * self.width for _ in range(self.height)]
        self._bottom = [[background] * self.width for _ in range(self.height)]
        self._char: list[list[str | None]] = [[None] * self.width for _ in range(self.height)]
        self._fg = [[background] * self.width for _ in range(self.height)]
        self._bold = [[False] * self.width for _ in range(self.height)]

    # --- drawing -------------------------------------------------------

    def fill(self, x: int, y: int, w: int, h: int, color: RGB) -> None:
        """Paint whole cells."""
        for row in range(max(0, y), min(self.height, y + h)):
            for col in range(max(0, x), min(self.width, x + w)):
                self._clear_text(col, row)
                self._top[row][col] = self._bottom[row][col] = color

    def pixel(self, x: int, py: int, color: RGB) -> None:
        y, lower = divmod(py, 2)
        if not (0 <= x < self.width and 0 <= y < self.height):
            return
        self._clear_text(x, y)
        (self._bottom if lower else self._top)[y][x] = color

    def rect(self, x: int, py: int, w: int, h: int, color: RGB) -> None:
        """Paint a block of pixels."""
        for row in range(py, py + h):
            for col in range(x, x + w):
                self.pixel(col, row, color)

    def sprite(self, x: int, py: int, rows: Sequence[str], palette: Mapping[str, RGB]) -> None:
        """Draw a text-grid sprite. Characters missing from the palette (like '.') are transparent."""
        for dy, row in enumerate(rows):
            for dx, key in enumerate(row):
                color = palette.get(key)
                if color is not None:
                    self.pixel(x + dx, py + dy, color)

    def text(self, x: int, y: int, s: str, fg: RGB, bg: RGB | None = None, bold: bool = False) -> int:
        """Write s from column x. Emoji and other wide glyphs take two cells. Returns the next column."""
        if not 0 <= y < self.height:
            return x
        for ch in s:
            w = cell_len(ch)
            if w == 0:
                continue
            if x + w > self.width:
                break
            if x >= 0:
                for col in range(x, x + w):
                    self._clear_text(col, y)
                back = bg if bg is not None else self._top[y][x]
                self._char[y][x], self._fg[y][x], self._bold[y][x] = ch, fg, bold
                self._top[y][x] = self._bottom[y][x] = back
                if w == 2:
                    self._char[y][x + 1] = WIDE_TAIL
                    self._top[y][x + 1] = self._bottom[y][x + 1] = back
            x += w
        return x

    def _clear_text(self, x: int, y: int) -> None:
        ch = self._char[y][x]
        if ch is None:
            return
        if ch == WIDE_TAIL:
            if x > 0:
                self._char[y][x - 1] = None
        elif cell_len(ch) == 2 and x + 1 < self.width:
            self._char[y][x + 1] = None
        self._char[y][x] = None

    # --- reading -------------------------------------------------------

    def pixel_at(self, x: int, py: int) -> RGB:
        y, lower = divmod(py, 2)
        return (self._bottom if lower else self._top)[y][x]

    def char_at(self, x: int, y: int) -> str | None:
        return self._char[y][x]

    def row_text(self, y: int) -> str:
        """The row's glyphs, with pixel cells shown as spaces."""
        return "".join(" " if ch is None else ch for ch in self._char[y])

    def row_key(self, y: int) -> tuple:
        """Equal keys mean the row looks the same, so it needn't be repainted."""
        return (
            tuple(self._char[y]),
            tuple(self._fg[y]),
            tuple(self._top[y]),
            tuple(self._bottom[y]),
            tuple(self._bold[y]),
        )

    def row_segments(self, y: int) -> list[Segment]:
        """The row as Rich segments, with neighbouring cells of the same style merged."""
        segments: list[Segment] = []
        run: list[str] = []
        run_style: Style | None = None
        for x in range(self.width):
            ch = self._char[y][x]
            if ch == WIDE_TAIL:
                continue
            top, bottom = self._top[y][x], self._bottom[y][x]
            if ch is not None:
                glyph, style = ch, _style(self._fg[y][x], top, self._bold[y][x])
            elif top == bottom:
                glyph, style = " ", _style(None, top, False)
            else:
                glyph, style = HALF_BLOCK, _style(top, bottom, False)
            if style is run_style:
                run.append(glyph)
            else:
                if run:
                    segments.append(Segment("".join(run), run_style))
                run, run_style = [glyph], style
        if run:
            segments.append(Segment("".join(run), run_style))
        return segments
