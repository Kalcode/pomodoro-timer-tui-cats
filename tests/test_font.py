import pytest

from canvas_reading import read_big
from pomo.render.canvas import Canvas
from pomo.render.font import FONT, GLYPH_HEIGHT, draw_big, text_width

BG = (0, 0, 0)
INK = (255, 107, 91)


def test_every_glyph_is_seven_rows_of_equal_width():
    for ch, rows in FONT.items():
        assert len(rows) == GLYPH_HEIGHT, ch
        assert len({len(row) for row in rows}) == 1, ch
        assert set("".join(rows)) <= {"#", " "}, ch


def test_the_clock_fits_the_timer_panel():
    assert text_width("18:42") == 25  # 4 digits × 5 + colon 1 + 4 one-column gaps
    assert text_width("") == 0


@pytest.mark.parametrize("s", ["0123456789", "25:00", "04:07", "120:00"])
def test_drawn_text_reads_back(s):
    canvas = Canvas(80, 5, BG)
    end = draw_big(canvas, 2, 1, s, INK)
    assert end == 2 + text_width(s) + 1
    assert read_big(canvas, 2, 1, BG, max_chars=len(s)) == s


def test_unknown_characters_draw_as_blanks():
    canvas = Canvas(20, 5, BG)
    draw_big(canvas, 0, 0, "?", INK)
    assert all(canvas.pixel_at(x, py) == BG for x in range(20) for py in range(10))
