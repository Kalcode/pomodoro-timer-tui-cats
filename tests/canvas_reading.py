"""Test helpers that read things back off a Canvas."""

from pomo.render.canvas import Canvas
from pomo.render.font import FONT, GLYPH_HEIGHT
from pomo.render.theme import RGB

_TRY_ORDER = [*"0123456789", ":", " "]  # blank last: it matches any empty patch


def read_big(canvas: Canvas, x: int, py: int, background: RGB, max_chars: int = 8, gap: int = 1) -> str:
    """Decode 5×7 font text drawn at (x, py) with `gap` columns between glyphs: any non-background pixel is ink."""

    def ink(col: int, row: int) -> bool:
        return 0 <= col < canvas.width and 0 <= row < canvas.height * 2 and canvas.pixel_at(col, row) != background

    out = ""
    while len(out) < max_chars:
        for ch in _TRY_ORDER:
            rows = FONT[ch]
            if all(ink(x + dx, py + dy) == (bit == "#")
                   for dy in range(GLYPH_HEIGHT) for dx, bit in enumerate(rows[dy])):
                out += ch
                x += len(rows[0]) + gap
                break
        else:
            break
    return out.rstrip()


def screen_text(canvas: Canvas) -> str:
    return "\n".join(canvas.row_text(y) for y in range(canvas.height))
