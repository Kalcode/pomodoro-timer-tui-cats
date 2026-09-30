from rich.color import Color
from rich.segment import Segment

from pomo.render.canvas import HALF_BLOCK, Canvas
from pomo.render.theme import hex_rgb

BG = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
WHITE = (255, 255, 255)


def test_hex_rgb():
    assert hex_rgb("#15161e") == (0x15, 0x16, 0x1E)


def test_a_new_canvas_is_blank():
    canvas = Canvas(4, 2, BG)
    assert canvas.row_text(0) == "    "
    assert canvas.pixel_at(3, 3) == BG


def test_even_pixel_rows_are_the_top_half_and_odd_rows_the_bottom():
    canvas = Canvas(2, 2, BG)
    canvas.pixel(1, 2, RED)
    canvas.pixel(1, 3, BLUE)
    assert (canvas.pixel_at(1, 2), canvas.pixel_at(1, 3)) == (RED, BLUE)
    assert canvas.pixel_at(1, 1) == BG


def test_drawing_off_the_edge_is_clipped_not_an_error():
    canvas = Canvas(3, 2, BG)
    canvas.pixel(-1, 0, RED)
    canvas.pixel(0, -1, RED)
    canvas.pixel(3, 0, RED)
    canvas.pixel(0, 4, RED)
    canvas.rect(-5, -5, 20, 20, BLUE)
    assert all(canvas.pixel_at(x, py) == BLUE for x in range(3) for py in range(4))


def test_zero_size_canvas_is_fine():
    canvas = Canvas(0, 0, BG)
    canvas.rect(0, 0, 5, 5, RED)
    canvas.text(0, 0, "hi", WHITE)


def test_sprites_skip_transparent_and_unknown_keys():
    canvas = Canvas(3, 1, BG)
    canvas.sprite(0, 0, ["a.z", "aaa"], {"a": RED})
    assert [canvas.pixel_at(x, 0) for x in range(3)] == [RED, BG, BG]
    assert [canvas.pixel_at(x, 1) for x in range(3)] == [RED, RED, RED]


def test_text_writes_glyphs_and_returns_the_next_column():
    canvas = Canvas(6, 1, BG)
    assert canvas.text(1, 0, "hey", WHITE) == 4
    assert canvas.row_text(0) == " hey  "


def test_text_is_cut_at_the_right_edge():
    canvas = Canvas(4, 1, BG)
    canvas.text(2, 0, "hello", WHITE)
    assert canvas.row_text(0) == "  he"


def test_text_background_defaults_to_whats_already_there():
    canvas = Canvas(2, 1, BG)
    canvas.fill(0, 0, 2, 1, BLUE)
    canvas.text(0, 0, "x", WHITE)
    (segment,) = [s for s in canvas.row_segments(0) if s.text.startswith("x")]
    assert segment.style.bgcolor == Color.from_rgb(*BLUE)


def test_wide_glyphs_take_two_cells():
    canvas = Canvas(5, 1, BG)
    assert canvas.text(0, 0, "🐟42", WHITE) == 4
    assert canvas.char_at(0, 0) == "🐟"
    assert canvas.row_text(0).startswith("🐟")
    assert Segment.get_line_length(canvas.row_segments(0)) == 5


def test_a_wide_glyph_that_would_not_fit_is_dropped():
    canvas = Canvas(3, 1, BG)
    assert canvas.text(2, 0, "🐟", WHITE) == 2
    assert canvas.row_text(0) == "   "


def test_a_pixel_over_text_turns_the_cell_back_into_pixels():
    canvas = Canvas(3, 1, BG)
    canvas.text(0, 0, "abc", WHITE)
    canvas.pixel(1, 0, RED)
    assert canvas.row_text(0) == "a c"
    assert canvas.pixel_at(1, 0) == RED


def test_covering_half_of_a_wide_glyph_removes_all_of_it():
    canvas = Canvas(3, 1, BG)
    canvas.text(0, 0, "🐟", WHITE)
    canvas.pixel(1, 1, RED)
    assert canvas.row_text(0) == "   "


def test_segments_merge_runs_and_use_half_blocks_for_split_cells():
    canvas = Canvas(4, 1, BG)
    canvas.pixel(2, 0, RED)  # top red, bottom black
    canvas.pixel(3, 0, RED)
    segments = canvas.row_segments(0)
    assert [s.text for s in segments] == ["  ", HALF_BLOCK * 2]
    assert segments[1].style.color == Color.from_rgb(*RED)
    assert segments[1].style.bgcolor == Color.from_rgb(*BG)
    assert Segment.get_line_length(segments) == 4


def test_row_keys_change_only_when_the_row_looks_different():
    a, b = Canvas(3, 2, BG), Canvas(3, 2, BG)
    for canvas in (a, b):
        canvas.text(0, 0, "hi", WHITE)
    assert a.row_key(0) == b.row_key(0)
    b.pixel(2, 3, RED)
    assert a.row_key(0) == b.row_key(0)
    assert a.row_key(1) != b.row_key(1)
