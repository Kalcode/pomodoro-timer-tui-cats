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


def text_width(s: str, gap: int = 1) -> int:
    """Columns taken by s: each glyph plus `gap` columns between glyphs."""
    return max(0, sum(len(glyph(ch)[0]) + gap for ch in s) - gap)


def draw_big(canvas: Canvas, x: int, py: int, s: str, color: RGB, gap: int = 1) -> int:
    """Draw s at 1× with its top-left pixel at (x, py), `gap` columns between glyphs.

    Returns where the next glyph would start (the trailing gap included)."""
    for ch in s:
        rows = glyph(ch)
        for dy, row in enumerate(rows):
            for dx, bit in enumerate(row):
                if bit == "#":
                    canvas.pixel(x + dx, py + dy, color)
        x += len(rows[0]) + gap
    return x
