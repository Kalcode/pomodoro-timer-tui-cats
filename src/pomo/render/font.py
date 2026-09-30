"""5×7 pixel digits for the clock (spec §7). "18:42" is 25 columns wide."""

from __future__ import annotations

from pomo.render.canvas import Canvas
from pomo.render.theme import RGB

GLYPH_HEIGHT = 7

FONT: dict[str, tuple[str, ...]] = {
    "0": (" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "),
    "1": ("  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "),
    "2": (" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"),
    "3": ("#####", "   # ", "  #  ", "   # ", "    #", "#   #", " ### "),
    "4": ("   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "),
    "5": ("#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "),
    "6": ("  ## ", " #   ", "#    ", "#### ", "#   #", "#   #", " ### "),
    "7": ("#####", "    #", "   # ", "  #  ", " #   ", " #   ", " #   "),
    "8": (" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "),
    "9": (" ### ", "#   #", "#   #", " ####", "    #", "   # ", " ##  "),
    ":": (" ", " ", "#", " ", "#", " ", " "),
    " ": (" ", " ", " ", " ", " ", " ", " "),
}


def glyph(ch: str) -> tuple[str, ...]:
    return FONT.get(ch, FONT[" "])


def text_width(s: str) -> int:
    """Columns taken by s: each glyph plus a one-column gap between glyphs."""
    return max(0, sum(len(glyph(ch)[0]) + 1 for ch in s) - 1)


def draw_big(canvas: Canvas, x: int, py: int, s: str, color: RGB) -> int:
    """Draw s at 1× with its top-left pixel at (x, py). Returns the column after the last glyph."""
    for ch in s:
        rows = glyph(ch)
        for dy, row in enumerate(rows):
            for dx, bit in enumerate(row):
                if bit == "#":
                    canvas.pixel(x + dx, py + dy, color)
        x += len(rows[0]) + 1
    return x
