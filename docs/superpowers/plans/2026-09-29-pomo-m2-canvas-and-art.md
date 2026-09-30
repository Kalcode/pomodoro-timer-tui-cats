# pomo Milestone 2: Canvas and Art Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace milestone 1's plain timer screen with the approved split layout: a 30-column timer panel with a pixel clock on the left, and a pixel-art room with a cat tree, window, shelf, bowl and door on the right. Mango the tabby sits on the floor and blinks. The milestone also adds `pomo --gallery` for tuning the art and a truecolor warning.

**Architecture:** Everything is drawn onto one `Canvas`, a cell buffer where each cell is either two stacked pixels drawn as `▀` or one text glyph.
- **The sprites are data.** They are text grids, coats are palettes, and a mood only swaps the head's ear, brow and eye rows.
- **The geometry is pure.** `game/playscape.py` computes the surfaces and furniture for any room size. Milestone 3 will use the surfaces for movement.
- **The scene is pure.** `render/scene.py` turns the timer, the cats and a frame number into pixels.
- **The widget is thin.** A Textual `Stage` shows the canvas and repaints only the rows that changed. The app ticks at 8 fps: each tick advances the session, then redraws the scene.

**Tech Stack:** Python ≥ 3.12, Textual 8.2 (the Line API: `render_line` → `Strip`), and Rich `Segment`/`Style`, which ship with Textual, so there is no new dependency. pytest and pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-09-29-pomo-cats-design.md`, §6 (layout), §7 (rendering) and §13 (milestone 2). This is **milestone 2 of 6**. It builds on milestone 1, which is on `main` (127 tests).

## Global Constraints

- Everything from the milestone 1 plan still holds: a pure core, an injected `Clock`, the topic never logged or shown, and notifications that never raise.
- `timer.py`, `session.py`, `game/*` and `render/*` must not import Textual. `ui/*` and `gallery.py` may.
- Colours are defined only in `render/theme.py`, as `(r, g, b)` tuples.
- Sprites are text grids with one character per pixel, and `.` means transparent. Cat palette slots are `o f d c w p e k r` (spec §7). Cats are 17 px wide; `sit` is 16 px tall and `loaf` is 15.
- Coats: `tabby`, `grey`, `tuxedo`, `siamese`, `black`, `calico`. The `c` slot equals `f` on every coat except calico.
- Faces: `ok`, `blink`, `sleep`, `meh`, `mad`. Poses: `sit`, `loaf`. Side-view walk and jump poses come in milestone 3.
- The timer panel is exactly 30 columns wide (`PANEL_WIDTH`). Nothing drawn for the panel may land at column 30 or beyond.
- Surface limits (spec §6): a cat can jump at most 20 px up or down and at most 24 columns across, and every surface must be reachable from the floor.
- The frame rate is 8 fps (`TICK_S = 1/8`). An unchanged frame repaints nothing, and a changed frame repaints only the rows that changed.
- The screen is the Stage plus a one-line message bar. The Footer is gone, and the key hints now sit at the bottom of the timer panel. The toolbar arrives in milestone 4.
- Tests read pixels and text straight off the canvas through `tests/canvas_reading.py`. They never scrape Textual's output.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

**Not in this milestone:**
- Cat movement, moods, needs and walk sprites (milestone 3).
- The toolbar, mouse tools, the hand, yarn and Idle mode (milestone 4).
- Poop, the knocked-over bowl, taking over the clock, treats and the shop (milestone 5).
- The too-small-terminal screen and the save file (milestone 6).

## Review Focus

1. **The terminal is resized to an odd or tiny size, or 0×0, mid-run:** drawing clips, and nothing crashes. Tests: Task 5 `test_small_or_empty_screens_do_not_crash`, Task 6 `test_a_resize_repaints_everything_at_the_new_size`.
2. **A clock too wide for the panel** (`+` pressed until it reads 125:00, which is 31 columns): it is cut at the panel edge and never drawn into the room. Test: Task 5 `test_a_clock_too_wide_for_the_panel_is_cut_at_the_edge`.
3. **Redraw cost at 8 fps:** an unchanged frame repaints nothing, and a one-pixel change repaints one row. Tests: Task 6 `test_an_unchanged_frame_repaints_nothing`, `test_a_change_repaints_only_its_row`.
4. **A sprite pixel lands on half of a wide glyph** (an emoji message or label): the whole glyph goes, so there's no half-emoji garbage. Test: Task 1 `test_covering_half_of_a_wide_glyph_removes_all_of_it`.
5. **A terminal without truecolor** (`COLORTERM` unset): the app still runs and shows a warning. Tests: Task 7 `test_truecolor_warning`, `test_a_terminal_without_truecolor_gets_warned`.

## File Map

| File | Responsibility | Task |
|---|---|---|
| `src/pomo/render/__init__.py` | Package marker | 1 |
| `src/pomo/render/theme.py` | Every colour, plus `hex_rgb` | 1 |
| `src/pomo/render/canvas.py` | `Canvas`: pixels, text, wide glyphs, clipping, Rich segments, row keys | 1 |
| `src/pomo/render/font.py` | 5×7 clock digits: `FONT`, `text_width`, `draw_big` | 2 |
| `tests/canvas_reading.py` | Test helpers: `read_big` (decodes the clock off the canvas) and `screen_text` | 2 |
| `src/pomo/render/sprites.py` | Cat grids from head plus body, faces, coats, props, `problems()` validation | 3 |
| `src/pomo/game/playscape.py` | `Surface`, `Box`, `Playscape`, `layout()`, `can_jump`, `reachable` | 4 |
| `src/pomo/ui/view.py` (modify) | `phase_label` and `phase_state` replace `phase_line`; `MAX_DOTS` 12 → 8 | 5, 6 |
| `src/pomo/render/scene.py` | `CatSprite`, `draw()`: the timer panel plus the room, blinking, z's, twinkling stars | 5 |
| `src/pomo/ui/stage.py` | `Stage` widget: shows a Canvas and repaints only the changed rows | 6 |
| `src/pomo/ui/app.py` (replace) | `TimerScreen` = Stage + message line; 8 fps tick; `draw_scene` | 6 |
| `src/pomo/gallery.py` | `GalleryApp` for `--gallery` | 7 |
| `src/pomo/cli.py` (replace) | `--gallery` flag, `truecolor_warning` | 7 |
| `README.md` (replace) | Terminal requirements, `--gallery` | 7 |

---

### Task 1: Colours and the canvas

**Files:**
- Create: `src/pomo/render/__init__.py`, `src/pomo/render/theme.py`, `src/pomo/render/canvas.py`
- Test: `tests/test_canvas.py`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `theme.RGB = tuple[int, int, int]`, `theme.hex_rgb("#rrggbb") -> RGB`, and colour constants: `ROOM_BG`, `PANEL_BG`, `TEXT`, `DIM`, `BAR_EMPTY`, `FOCUS`, `BREAK`, `IDLE_CLOCK`, `SLEEP_Z`, `FLOOR`, `SISAL`, `SISAL_DARK`, `PLATFORM`, `PLATFORM_EDGE`, `SHELF`, `SHELF_BRACKET`, `WINDOW_FRAME`, `WINDOW_GLASS`, `WINDOW_SILL`, `STAR`.
  - `Canvas(width, height, background)` with `.width` and `.height`.
    - Drawing: `.fill(x, y, w, h, color)` for whole cells, `.pixel(x, py, color)`, `.rect(x, py, w, h, color)`, `.sprite(x, py, rows, palette)`, and `.text(x, y, s, fg, bg=None, bold=False) -> next_x`.
    - Reading: `.pixel_at(x, py)`, `.char_at(x, y)`, `.row_text(y)`, `.row_key(y)`, `.row_segments(y) -> list[Segment]`.
  - Constants: `HALF_BLOCK = "▀"` and `WIDE_TAIL = ""`.

- [ ] **Step 1: Write the failing tests**

`tests/test_canvas.py`:

```python
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_canvas.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.render'`

- [ ] **Step 3: Create the package and the theme**

`src/pomo/render/__init__.py`:

```python
"""Drawing: the pixel canvas, sprites, font, colours and the scene."""
```

`src/pomo/render/theme.py`:

```python
"""Every colour on screen, as (r, g, b). A Tokyo Night-style palette (spec §7)."""

from __future__ import annotations

RGB = tuple[int, int, int]


def hex_rgb(value: str) -> RGB:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


# screen
ROOM_BG = hex_rgb("#15161e")
PANEL_BG = hex_rgb("#1f2335")
TEXT = hex_rgb("#c0caf5")
DIM = hex_rgb("#565f89")
BAR_EMPTY = hex_rgb("#2f3549")

# phases
FOCUS = hex_rgb("#ff6b5b")
BREAK = hex_rgb("#9ece6a")
IDLE_CLOCK = hex_rgb("#737aa2")  # a phase that isn't running

# effects
SLEEP_Z = hex_rgb("#7aa2f7")

# room
FLOOR = hex_rgb("#24283b")
SISAL = hex_rgb("#c9a66b")
SISAL_DARK = hex_rgb("#a8844d")
PLATFORM = hex_rgb("#6b5b8a")
PLATFORM_EDGE = hex_rgb("#4d4166")
SHELF = hex_rgb("#7a5236")
SHELF_BRACKET = hex_rgb("#5c3f2a")
WINDOW_FRAME = hex_rgb("#2a2f45")
WINDOW_GLASS = hex_rgb("#0d1026")
WINDOW_SILL = hex_rgb("#3a3f5a")
STAR = hex_rgb("#e0e0ff")
```

- [ ] **Step 4: Implement the canvas**

`src/pomo/render/canvas.py`:

```python
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
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -v`
Expected: `142 passed` (127 from milestone 1, plus 15)

- [ ] **Step 6: Commit**

```bash
git add src/pomo/render tests/test_canvas.py
git commit -m "feat: half-block pixel canvas with text, wide glyphs and row diffing" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Clock font and the canvas-reading test helper

**Files:**
- Create: `src/pomo/render/font.py`, `tests/canvas_reading.py`
- Test: `tests/test_font.py`

**Interfaces:**
- Consumes: `Canvas` and `RGB` from Task 1.
- Produces:
  - `font.GLYPH_HEIGHT = 7`
  - `font.FONT: dict[str, tuple[str, ...]]`, covering the digits, `:` and a space.
  - `font.glyph(ch)`
  - `font.text_width(s) -> int`. `"18:42"` is **25** columns.
  - `font.draw_big(canvas, x, py, s, color) -> next_x`
  - Test helpers: `canvas_reading.read_big(canvas, x, py, background, max_chars=8) -> str` and `canvas_reading.screen_text(canvas) -> str`. pytest puts `tests/` on `sys.path`, so tests import them as `from canvas_reading import ...`.

- [ ] **Step 1: Write the test helper and the failing tests**

`tests/canvas_reading.py`, test-only code that decodes 5×7 digits off a canvas:

```python
"""Test helpers that read things back off a Canvas."""

from pomo.render.canvas import Canvas
from pomo.render.font import FONT, GLYPH_HEIGHT
from pomo.render.theme import RGB

_TRY_ORDER = [*"0123456789", ":", " "]  # blank last: it matches any empty patch


def read_big(canvas: Canvas, x: int, py: int, background: RGB, max_chars: int = 8) -> str:
    """Decode 5×7 font text drawn at (x, py): any pixel that isn't the background counts as ink."""

    def ink(col: int, row: int) -> bool:
        return 0 <= col < canvas.width and 0 <= row < canvas.height * 2 and canvas.pixel_at(col, row) != background

    out = ""
    while len(out) < max_chars:
        for ch in _TRY_ORDER:
            rows = FONT[ch]
            if all(ink(x + dx, py + dy) == (bit == "#")
                   for dy in range(GLYPH_HEIGHT) for dx, bit in enumerate(rows[dy])):
                out += ch
                x += len(rows[0]) + 1
                break
        else:
            break
    return out.rstrip()


def screen_text(canvas: Canvas) -> str:
    return "\n".join(canvas.row_text(y) for y in range(canvas.height))
```

`tests/test_font.py`:

```python
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
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_font.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.render.font'`

- [ ] **Step 3: Implement the font**

`src/pomo/render/font.py`:

```python
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
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -v`
Expected: `149 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pomo/render/font.py tests/canvas_reading.py tests/test_font.py
git commit -m "feat: 5x7 pixel clock font" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Sprites: cats, coats and props

**Files:**
- Create: `src/pomo/render/sprites.py`
- Test: `tests/test_sprites.py`

**Interfaces:**
- Consumes: `theme.hex_rgb` and `theme.RGB` from Task 1.
- Produces:
  - `Grid = tuple[str, ...]`
  - Constants: `CAT_WIDTH = 17`, `CAT_SLOTS` (a frozenset of `ofdcwpekr`), `FACES`, `POSES`
  - Helpers: `mirror(left_half)`, `flip(grid)`, `pad(grid, width)`
  - Cats: `cat_head(face) -> Grid` and `cat(pose, face) -> Grid`. An unknown pose or face raises `KeyError`.
  - `COATS: dict[str, dict[str, RGB]]`
  - Props: `DOOR`, `DOOR_PALETTE`, `BOWL_FULL`, `BOWL_EMPTY`, `BOWL_PALETTE`, and `PROPS: dict[str, (Grid, palette)]`
  - `problems(grid, slots) -> list[str]`
- Art rules, carried over from the approved mockups:
  - A head is 10 rows, drawn as its 7-px left half and mirrored, so every head is symmetric.
  - Faces change only the head rows.
  - `mad` flattens the ears out of the top row and turns the eyes red.

- [ ] **Step 1: Write the failing tests**

`tests/test_sprites.py`:

```python
import pytest

from pomo.render import sprites
from pomo.render.sprites import CAT_SLOTS, CAT_WIDTH, COATS, FACES, POSES, PROPS, cat, cat_head, flip, mirror, problems

HEAD_ROWS = 10
EXPECTED_HEIGHT = {"sit": 16, "loaf": 15}


@pytest.mark.parametrize("pose", POSES)
@pytest.mark.parametrize("face", FACES)
def test_every_cat_is_a_clean_17_wide_grid(pose, face):
    grid = cat(pose, face)
    assert problems(grid, CAT_SLOTS) == []
    assert {len(row) for row in grid} == {CAT_WIDTH}
    assert len(grid) == EXPECTED_HEIGHT[pose]


@pytest.mark.parametrize("face", FACES)
def test_heads_are_symmetric(face):
    for row in cat_head(face):
        core = row[:14]
        assert core == core[::-1]


@pytest.mark.parametrize("pose", POSES)
def test_faces_only_change_the_head(pose):
    bodies = {cat(pose, face)[HEAD_ROWS:] for face in FACES}
    assert len(bodies) == 1


def test_the_faces_look_different():
    heads = {face: cat_head(face) for face in FACES}
    assert heads["ok"] != heads["blink"] != heads["meh"]
    assert heads["mad"][0] == "." * CAT_WIDTH  # ears flattened out of the top row
    assert "r" in "".join(heads["mad"])  # red eyes
    assert "e" not in "".join(heads["blink"])  # eyes shut


@pytest.mark.parametrize("coat", COATS)
def test_every_coat_colours_every_slot(coat):
    assert set(COATS[coat]) == CAT_SLOTS


def test_patches_only_show_on_calico():
    for name, coat in COATS.items():
        assert (coat["c"] != coat["f"]) == (name == "calico"), name


@pytest.mark.parametrize("name", PROPS)
def test_props_are_clean_grids(name):
    grid, palette = PROPS[name]
    assert problems(grid, set(palette)) == []


def test_mirror_and_flip():
    assert mirror(["ab"]) == ("abba",)
    assert flip(("abc", "d.e")) == ("cba", "e.d")
    assert flip(flip(cat("sit", "ok"))) == cat("sit", "ok")


def test_problems_spots_ragged_rows_and_unknown_slots():
    assert problems(("ab", "a"), {"a", "b"}) == ["ragged rows: [1, 2]"]
    assert problems(("aZ",), {"a"}) == ["unknown slots: ['Z']"]


def test_unknown_pose_or_face_is_a_key_error():
    with pytest.raises(KeyError):
        sprites.cat("backflip", "ok")
    with pytest.raises(KeyError):
        sprites.cat("sit", "smug")
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_sprites.py -v`
Expected: FAIL during collection with `ImportError: cannot import name 'sprites' from 'pomo.render'`

- [ ] **Step 3: Implement the sprites**

`src/pomo/render/sprites.py`:

```python
"""Pixel art as text grids: one character per pixel, '.' is transparent (spec §7).

Cat palette slots:
  o outline   f fur    d stripe   c patch (same as fur except on calico)
  w white     p pink   e eye      k pupil  r angry eye
Every cat is one head plus one body. A coat is only a palette, and a mood only
swaps the head's ear, brow and eye rows, so poses × moods × coats never multiply
into more drawing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pomo.render.theme import RGB, hex_rgb

Grid = tuple[str, ...]

CAT_WIDTH = 17
CAT_SLOTS = frozenset("ofdcwpekr")
FACES = ("ok", "blink", "sleep", "meh", "mad")
POSES = ("sit", "loaf")


def mirror(left_half: Sequence[str]) -> Grid:
    """A symmetric grid from its left half."""
    return tuple(row + row[::-1] for row in left_half)


def flip(grid: Sequence[str]) -> Grid:
    """Face the other way."""
    return tuple(row[::-1] for row in grid)


def pad(grid: Sequence[str], width: int) -> Grid:
    return tuple(row.ljust(width, ".") for row in grid)


# --- cats -----------------------------------------------------------------
# Heads are drawn as their left half (7 px) and mirrored to 14 px.

_EARS = {
    "up": ("..o....", ".opo...", ".oppooo"),
    "flat": (".......", ".......", "opppooo"),  # airplane ears
}
_FOREHEAD = ".offfdf"
_BROW = {"calm": "offfffd", "angry": "ofofffd"}
_EYES = {
    "open": ("ofekeff", "ofekeff"),
    "shut": ("offffff", "ofoooff"),
    "half": ("offffff", "ofekeff"),
    "angry": ("offooff", "ofrkrff"),
}
_MUZZLE = ("offfffp", ".offfww", "..offww")

_FACE_PARTS = {  # face: (ears, brow, eyes)
    "ok": ("up", "calm", "open"),
    "blink": ("up", "calm", "shut"),
    "sleep": ("up", "calm", "shut"),
    "meh": ("up", "calm", "half"),
    "mad": ("flat", "angry", "angry"),
}

_BODIES = {
    "sit": (
        ".occfwwwwfffo....",
        ".offfwwwwfffo.oo.",
        "offffwwwwfccfoffo",
        "offffwwwwfcffoffo",
        "offwwffffwwfffffo",
        ".ooooooooooooooo.",
    ),
    "loaf": (
        ".offfwwwwfffo....",
        "offffwwwwfccfoo..",
        "occffffffffcfffo.",
        "ofddddddddddddfo.",
        ".oooooooooooooo..",
    ),
}


def cat_head(face: str) -> Grid:
    ears, brow, eyes = _FACE_PARTS[face]
    half = (*_EARS[ears], _FOREHEAD, _BROW[brow], *_EYES[eyes], *_MUZZLE)
    return pad(mirror(half), CAT_WIDTH)


def cat(pose: str, face: str) -> Grid:
    """A front-facing cat, 17 px wide. Its bottom row is where its feet are."""
    return cat_head(face) + _BODIES[pose]


# --- coats ----------------------------------------------------------------

_SHARED = {"p": hex_rgb("#f09aa6"), "k": hex_rgb("#111111"), "r": hex_rgb("#ff4a3d")}


def _coat(o: str, f: str, d: str, w: str, e: str, c: str | None = None) -> dict[str, RGB]:
    return {**_SHARED, "o": hex_rgb(o), "f": hex_rgb(f), "d": hex_rgb(d),
            "c": hex_rgb(c or f), "w": hex_rgb(w), "e": hex_rgb(e)}


COATS: dict[str, dict[str, RGB]] = {
    "tabby": _coat("#3b2416", "#e8923b", "#b8631e", "#f6eee3", "#8fd16a"),
    "grey": _coat("#1f2330", "#8a93a6", "#6b7385", "#e9ecf2", "#8fd16a"),
    "tuxedo": _coat("#5d5d70", "#2a2a33", "#1e1e25", "#ececf0", "#e8d44d"),
    "siamese": _coat("#5a4636", "#efe0c8", "#8a6a55", "#fffaf2", "#6fb7ff"),
    "black": _coat("#5d5d70", "#1c1c22", "#141418", "#2a2a33", "#e8d44d"),
    "calico": _coat("#3a2a22", "#f4ede2", "#e0913a", "#fbf8f2", "#8fd16a", c="#2b2626"),
}


# --- props ----------------------------------------------------------------

DOOR: Grid = (
    "ooooooo", "obbbbbo", "obbbbbo", "obooobo", "obfffbo", "obfffbo", "obfffbo",
    "obfffbo", "obfffbo", "obooobo", "obbbbbo", "obbbbbo", "obbbbbo", "obbbbbo",
)
DOOR_PALETTE = {"o": hex_rgb("#2e2016"), "b": hex_rgb("#5c3f2a"), "f": hex_rgb("#3d2a1c")}

BOWL_FULL: Grid = (".kkkkkk.", "obbbbbbo", ".obbbbo.")
BOWL_EMPTY: Grid = (".o....o.", "obbbbbbo", ".obbbbo.")
BOWL_PALETTE = {"k": hex_rgb("#b8631e"), "o": hex_rgb("#1f3b66"), "b": hex_rgb("#3d6fb3")}

PROPS: dict[str, tuple[Grid, Mapping[str, RGB]]] = {
    "door": (DOOR, DOOR_PALETTE),
    "bowl_full": (BOWL_FULL, BOWL_PALETTE),
    "bowl_empty": (BOWL_EMPTY, BOWL_PALETTE),
}


def problems(grid: Sequence[str], slots: frozenset[str] | set[str]) -> list[str]:
    """Why a grid is malformed: ragged rows, or characters that aren't '.' or a known slot."""
    found = []
    if len({len(row) for row in grid}) > 1:
        found.append(f"ragged rows: {sorted({len(row) for row in grid})}")
    unknown = set("".join(grid)) - set(slots) - {"."}
    if unknown:
        found.append(f"unknown slots: {sorted(unknown)}")
    return found
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -v`
Expected: `180 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pomo/render/sprites.py tests/test_sprites.py
git commit -m "feat: cat sprites (sit/loaf x 5 faces), 6 coats, door and bowl" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Playscape geometry

**Files:**
- Create: `src/pomo/game/playscape.py`
- Test: `tests/test_playscape.py`

**Interfaces:**
- Consumes: nothing. This is pure geometry.
- Produces:
  - Constants: `CAT_WIDTH = 17`, `CAT_HEIGHT = 16`, `MAX_JUMP_UP = 20`, `MAX_JUMP_ACROSS = 24`, `MIN_WIDTH = 70`, `MIN_HEIGHT = 54`
  - `Surface(name, x0, x1, y)`. A standing sprite's bottom row is at `y - 1`.
  - `Box(x, y, w, h)`
  - `Playscape`:
    - Fields: `width`, `height`, `floor`, `tree_mid`, `tree_top`, `shelf`, `post`, `window`, `door`, `bowl`.
    - `.surfaces`, and `.surface(name)`, which raises `KeyError` for an unknown name.
  - `layout(width, height) -> Playscape`
  - `can_jump(a, b) -> bool`
  - `reachable(scape) -> set[str]`
- Layout, relative to the floor, which is `floor.y = height - 1`:

  | Thing | Position |
  |---|---|
  | Tree top | x 3–21, 37 px above the floor |
  | Tree middle | x 8–28, 18 px above |
  | Shelf | x 46–64, 29 px above |
  | Window | 14×12, from x 28, its top 51 px above the floor |
  | Door | 7×14, at the right edge |
  | Bowl | 8×3, 20 columns from the right edge |

  - The tree, window and shelf stay at the left at every width. Extra height only adds wall above.
- **Ruling (deviation from spec §6):** the window is anchored between the tree and the shelf instead of centered. When centered in wider rooms it slid behind the shelf, so a cat perched there would cover it. Task 7 updates the spec.

- [ ] **Step 1: Write the failing tests**

`tests/test_playscape.py`:

```python
import pytest

from pomo.game.playscape import (
    CAT_HEIGHT, CAT_WIDTH, MIN_HEIGHT, MIN_WIDTH, Surface, can_jump, layout, reachable,
)

SIZES = [(MIN_WIDTH, MIN_HEIGHT), (MIN_WIDTH, 58), (120, 80), (250, 120)]


@pytest.mark.parametrize("width, height", SIZES)
def test_every_surface_fits_a_cat_inside_the_room(width, height):
    scape = layout(width, height)
    for s in scape.surfaces:
        assert 0 <= s.x0 and s.x1 <= width, s
        assert s.x1 - s.x0 >= CAT_WIDTH, s
        assert s.y - CAT_HEIGHT >= 0, s  # headroom for the tallest pose
        assert s.y < height, s


@pytest.mark.parametrize("width, height", SIZES)
def test_every_surface_can_be_reached_from_the_floor(width, height):
    scape = layout(width, height)
    assert reachable(scape) == {s.name for s in scape.surfaces}


def test_the_floor_is_the_bottom_pixel_row():
    assert layout(80, 60).floor.y == 59


def test_a_taller_room_only_adds_wall_above():
    short, tall = layout(80, 60), layout(80, 100)
    for a, b in zip(short.surfaces, tall.surfaces):
        assert (a.x0, a.x1) == (b.x0, b.x1)
        assert short.floor.y - a.y == tall.floor.y - b.y


def test_a_wider_room_keeps_the_furniture_and_moves_the_bowl_and_door():
    narrow, wide = layout(70, 60), layout(150, 60)
    assert (narrow.tree_top, narrow.shelf, narrow.window) == (wide.tree_top, wide.shelf, wide.window)
    assert wide.door.x + wide.door.w == 150
    assert wide.bowl.x > narrow.bowl.x


@pytest.mark.parametrize("width, height", SIZES)
def test_door_and_bowl_sit_on_the_floor_without_overlapping(width, height):
    scape = layout(width, height)
    for box in (scape.door, scape.bowl):
        assert box.y + box.h == scape.floor.y
    assert scape.bowl.x + scape.bowl.w <= scape.door.x


@pytest.mark.parametrize("width, height", SIZES)
def test_the_window_stays_clear_of_the_tree_top_and_the_shelf(width, height):
    scape = layout(width, height)
    window = scape.window
    assert window.y >= 0
    assert window.x >= scape.tree_top.x1  # right of any cat on the tree top
    assert window.x + window.w <= scape.shelf.x0  # left of any cat on the shelf


def test_surfaces_are_found_by_name():
    scape = layout(80, 60)
    assert scape.surface("shelf") is scape.shelf
    with pytest.raises(KeyError):
        scape.surface("fridge")


def test_jump_limits():
    floor = Surface("a", 0, 10, 50)
    assert can_jump(floor, Surface("b", 0, 10, 30))  # 20 up
    assert not can_jump(floor, Surface("b", 0, 10, 29))  # 21 up
    assert can_jump(floor, Surface("b", 34, 50, 50))  # 24 across
    assert not can_jump(floor, Surface("b", 35, 50, 50))  # 25 across
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_playscape.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.game.playscape'`

- [ ] **Step 3: Implement the playscape**

`src/pomo/game/playscape.py`:

```python
"""Where things are in the cat room (spec §6). Pure geometry, in room pixel coordinates.

x is a column from the room's left edge, y a pixel row from the room's top (two per
text row). Everything is anchored to the floor, so a taller room just adds wall above.
The cat tree, window and shelf stay together at the left (the window sits between the
tree and the shelf, where no perched cat can cover it); the bowl and door follow the
right edge, so a wider room is more floor to roam.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

CAT_WIDTH = 17
CAT_HEIGHT = 16  # the tallest pose
MAX_JUMP_UP = 20  # spec §6: surfaces a cat can hop between
MAX_JUMP_ACROSS = 24
MIN_WIDTH = 70  # 100 columns minus the 30-column timer panel
MIN_HEIGHT = 54  # the tree top still has room for a sitting cat


@dataclass(frozen=True)
class Surface:
    """Something a cat can stand on. A standing sprite's bottom row is y - 1."""

    name: str
    x0: int
    x1: int  # exclusive
    y: int


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class Playscape:
    width: int
    height: int
    floor: Surface
    tree_mid: Surface
    tree_top: Surface
    shelf: Surface
    post: Box
    window: Box
    door: Box
    bowl: Box

    @property
    def surfaces(self) -> tuple[Surface, ...]:
        return (self.floor, self.tree_mid, self.tree_top, self.shelf)

    def surface(self, name: str) -> Surface:
        for s in self.surfaces:
            if s.name == name:
                return s
        raise KeyError(name)


def layout(width: int, height: int) -> Playscape:
    floor_y = height - 1
    tree_top = Surface("tree_top", 3, 21, floor_y - 37)
    tree_mid = Surface("tree_mid", 8, 28, floor_y - 18)
    shelf = Surface("shelf", tree_mid.x1 + 18, tree_mid.x1 + 36, floor_y - 29)
    return Playscape(
        width=width,
        height=height,
        floor=Surface("floor", 0, width, floor_y),
        tree_mid=tree_mid,
        tree_top=tree_top,
        shelf=shelf,
        post=Box(11, tree_top.y + 2, 3, floor_y - tree_top.y - 2),
        window=Box(tree_top.x1 + 7, floor_y - 51, 14, 12),
        door=Box(width - 7, floor_y - 14, 7, 14),
        bowl=Box(width - 20, floor_y - 3, 8, 3),
    )


def can_jump(a: Surface, b: Surface) -> bool:
    gap = max(0, max(a.x0, b.x0) - min(a.x1, b.x1))
    return abs(a.y - b.y) <= MAX_JUMP_UP and gap <= MAX_JUMP_ACROSS


def reachable(scape: Playscape) -> set[str]:
    """Names of the surfaces a cat on the floor can get to."""
    seen = {scape.floor.name}
    queue = deque([scape.floor])
    while queue:
        here = queue.popleft()
        for there in scape.surfaces:
            if there.name not in seen and can_jump(here, there):
                seen.add(there.name)
                queue.append(there)
    return seen
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -v`
Expected: `201 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pomo/game/playscape.py tests/test_playscape.py
git commit -m "feat: playscape layout: floor, cat tree, shelf, window, door, bowl" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: The scene

**Files:**
- Modify: `src/pomo/ui/view.py` (add two functions and change one constant; `phase_line` stays until Task 6, because the app still uses it)
- Modify: `tests/test_view.py`
- Create: `src/pomo/render/scene.py`
- Test: `tests/test_scene.py`

**Interfaces:**
- Consumes:
  - Tasks 1–4: `Canvas`, `theme`, `draw_big`, `sprites`, `layout`, `Box`, `Playscape`.
  - Milestone 1: `PomodoroTimer`, and `view.clock_text`, `progress_bar`, `count_line`, `next_line`.
- Produces:
  - `view.phase_label(timer) -> "● FOCUS"` and `view.phase_state(timer)`, which returns `"" | "paused" | "space to start"`.
  - `view.MAX_DOTS = 8`.
  - `CatSprite(name, coat, pose, face, surface, x)`, a frozen dataclass. `x` is the room column of the sprite's left edge.
  - `draw(canvas, timer, cats, frame) -> None`
  - `phase_color(timer)` and `blinking(name, frame) -> bool`
  - Constants: `PANEL_WIDTH = 30`, `TEXT_X = 2`, `PHASE_ROW = 1`, `STATE_ROW = 2`, `CLOCK_X = 2`, `CLOCK_PY = 8`, `BAR_ROW = 9`, `BAR_WIDTH = 25`, `COUNT_ROW = 11`, `NEXT_ROW = 12`, `KEY_HINTS`, `BLINK_EVERY = 48`, `BLINK_FRAMES = 2`, `STARS`, `TWINKLE_FRAMES = 12`.
- Behavior:
  - Clock colour: `IDLE_CLOCK` when not running, `FOCUS` during a running focus, `BREAK` during a running break.
  - Panel text is cut at column 28.
  - The room is drawn after the panel and fills its own background, which also trims a clock too wide for the panel.
  - Cats are drawn from back to front: surfaces higher up first, then by x.
  - An `ok` face blinks for 2 of every 48 frames, offset by the sum of the name's character codes.
  - A `sleep` face floats a `z`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_view.py`, add this test directly after `test_phase_line_states`:

```python
def test_phase_label_and_state(timer, clock):
    assert (view.phase_label(timer), view.phase_state(timer)) == ("● FOCUS", "space to start")
    timer.start()
    assert view.phase_state(timer) == ""
    clock.advance(1)
    timer.pause()
    assert view.phase_state(timer) == "paused"
    timer.skip()
    assert view.phase_label(timer) == "● SHORT BREAK"
```

and replace `test_huge_sets_skip_the_dots` with:

```python
def test_big_sets_skip_the_dots_so_the_line_fits_the_panel(clock):
    timer = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 9), clock)
    assert view.count_line(timer) == "pomodoro 1 of 9"
    timer = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 8), clock)
    assert view.count_line(timer) == "pomodoro 1 of 8  ○○○○○○○○"
```

Create `tests/test_scene.py`:

```python
import pytest

from canvas_reading import read_big, screen_text
from pomo.clock import FakeClock
from pomo.game.playscape import MIN_HEIGHT, layout
from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.render.scene import (
    BLINK_EVERY, CLOCK_PY, CLOCK_X, PANEL_WIDTH, TWINKLE_FRAMES, CatSprite, blinking, draw,
)
from pomo.timer import PomodoroTimer, TimerSettings

W, H = 100, 29  # 100×30 terminal minus the message line
MANGO = CatSprite("Mango", "tabby", "sit", "ok", "floor", 30)


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def timer(clock):
    return PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), clock)


def render(timer, cats=(), frame=1, width=W, height=H) -> Canvas:
    canvas = Canvas(width, height, (0, 0, 0))
    draw(canvas, timer, cats, frame)
    return canvas


def clock_ink(canvas: Canvas) -> set:
    return {canvas.pixel_at(x, py) for x in range(CLOCK_X, CLOCK_X + 25)
            for py in range(CLOCK_PY, CLOCK_PY + 7)} - {theme.PANEL_BG}


def test_the_panel_shows_the_phase_counts_and_keys(timer):
    text = screen_text(render(timer))
    for expected in ["● FOCUS", "space to start", "pomodoro 1 of 4", "next: 5 min break",
                     "space start/pause", "q quit"]:
        assert expected in text


def test_the_clock_shows_the_time_left(timer, clock):
    assert read_big(render(timer), CLOCK_X, CLOCK_PY, theme.PANEL_BG) == "25:00"
    timer.start()
    clock.advance(61)
    assert read_big(render(timer), CLOCK_X, CLOCK_PY, theme.PANEL_BG) == "23:59"


def test_the_clock_colour_follows_the_phase(timer, clock):
    assert clock_ink(render(timer)) == {theme.IDLE_CLOCK}
    timer.start()
    assert clock_ink(render(timer)) == {theme.FOCUS}
    clock.advance(25 * 60)
    timer.tick()
    assert clock_ink(render(timer)) == {theme.BREAK}


def test_panel_text_never_spills_into_the_room(clock):
    timer = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 1), clock)
    timer.start()
    clock.advance(25 * 60)
    timer.tick()
    timer.pause()  # "● LONG BREAK" / "paused"
    canvas = render(timer)
    assert "LONG BREAK" in screen_text(canvas)
    assert all(canvas.row_text(y)[PANEL_WIDTH:].strip() == "" for y in range(H))


def test_a_clock_too_wide_for_the_panel_is_cut_at_the_edge(timer):
    timer.adjust(+100)  # 125:00 would be 31 columns
    canvas = render(timer)
    assert all(canvas.pixel_at(PANEL_WIDTH, py) == theme.ROOM_BG for py in range(CLOCK_PY, CLOCK_PY + 7))


def test_the_room_has_its_furniture(timer):
    canvas = render(timer)
    room = layout(W - PANEL_WIDTH, H * 2)
    assert canvas.pixel_at(PANEL_WIDTH + room.tree_top.x0, room.tree_top.y) == theme.PLATFORM
    assert canvas.pixel_at(PANEL_WIDTH + room.shelf.x0, room.shelf.y) == theme.SHELF
    assert canvas.pixel_at(PANEL_WIDTH + room.door.x, room.door.y) == sprites.DOOR_PALETTE["o"]
    assert canvas.pixel_at(PANEL_WIDTH, room.floor.y) == theme.FLOOR


def test_a_cat_stands_on_its_surface(timer):
    canvas = render(timer, [MANGO])
    floor = layout(W - PANEL_WIDTH, H * 2).floor
    tabby = sprites.COATS["tabby"]
    x = PANEL_WIDTH + MANGO.x
    assert canvas.pixel_at(x + 1, floor.y - 1) == tabby["o"]  # bottom outline, just above the floor
    assert canvas.pixel_at(x + 2, floor.y - 16) == tabby["o"]  # ear tip
    assert canvas.pixel_at(x, floor.y - 16) == theme.ROOM_BG  # transparent corner


def test_a_cat_on_the_tree_top_fits_in_the_smallest_room(timer):
    height = MIN_HEIGHT // 2
    top_cat = CatSprite("Pebble", "grey", "sit", "ok", "tree_top", 3)
    canvas = render(timer, [top_cat], width=PANEL_WIDTH + 70, height=height)
    assert canvas.pixel_at(PANEL_WIDTH + 3 + 2, 0) == sprites.COATS["grey"]["o"]  # the ear tip is on screen


def test_higher_cats_are_drawn_behind_lower_ones(timer):
    room = layout(W - PANEL_WIDTH, H * 2)
    back = CatSprite("Pebble", "grey", "sit", "ok", "tree_mid", 8)
    front = CatSprite("Mango", "tabby", "sit", "ok", "floor", 8)
    canvas = render(timer, [front, back])  # given in the wrong order on purpose
    # the floor cat's ear tip overlaps the tree-mid cat's body
    assert canvas.pixel_at(PANEL_WIDTH + 8 + 2, room.floor.y - 16) == sprites.COATS["tabby"]["o"]


def test_ok_cats_blink_now_and_then():
    blinks = [frame for frame in range(BLINK_EVERY) if blinking("Mango", frame)]
    assert len(blinks) == 2
    assert blinking("Mango", blinks[0] + BLINK_EVERY)


def test_a_blinking_cat_closes_its_eyes(timer):
    frame = next(f for f in range(BLINK_EVERY) if blinking("Mango", f))
    floor = layout(W - PANEL_WIDTH, H * 2).floor
    eye = (PANEL_WIDTH + MANGO.x + 2, floor.y - 16 + 5)  # head row 5: "ofekeff", column 2 is eye
    assert render(timer, [MANGO], frame=frame + 10).pixel_at(*eye) == sprites.COATS["tabby"]["e"]
    assert render(timer, [MANGO], frame=frame).pixel_at(*eye) != sprites.COATS["tabby"]["e"]


def test_sleeping_cats_float_a_z(timer):
    sleeper = CatSprite("Pebble", "grey", "loaf", "sleep", "tree_top", 3)
    assert "z" in screen_text(render(timer, [sleeper]))
    assert "z" not in screen_text(render(timer, [MANGO]))


def test_the_stars_twinkle(timer):
    frames = [render(timer, frame=f * TWINKLE_FRAMES) for f in range(3)]
    keys = [tuple(c.row_key(y) for y in range(H)) for c in frames]
    assert len(set(keys)) == 3


@pytest.mark.parametrize("size", [(0, 0), (10, 3), (40, 10), (PANEL_WIDTH, H)])
def test_small_or_empty_screens_do_not_crash(timer, size):
    render(timer, [MANGO], width=size[0], height=size[1])
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_view.py tests/test_scene.py -v`
Expected: `test_scene.py` fails during collection with `ModuleNotFoundError: No module named 'pomo.render.scene'`. In `test_view.py`, `test_phase_label_and_state` fails with `AttributeError: module 'pomo.ui.view' has no attribute 'phase_label'`, and `test_big_sets_skip_the_dots_so_the_line_fits_the_panel` fails because 9 dots are still drawn.

- [ ] **Step 3: Update view.py**

In `src/pomo/ui/view.py`, replace `MAX_DOTS = 12` with:

```python
MAX_DOTS = 8  # keeps the count line inside the 30-column panel
```

and add these two functions directly after `phase_line`. Leave `phase_line` in place; Task 6 deletes it.

```python
def phase_label(timer: PomodoroTimer) -> str:
    return f"● {PHASE_NAMES[timer.phase]}"


def phase_state(timer: PomodoroTimer) -> str:
    """Shown under the phase name while the timer isn't running."""
    if timer.running:
        return ""
    return "paused" if timer.started else "space to start"
```

- [ ] **Step 4: Implement the scene**

`src/pomo/render/scene.py`:

```python
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
from pomo.render.font import draw_big
from pomo.render.theme import RGB
from pomo.timer import PomodoroTimer
from pomo.ui import view

PANEL_WIDTH = 30
TEXT_X = 2
PHASE_ROW, STATE_ROW = 1, 2
CLOCK_X, CLOCK_PY = 2, 8  # the 7-pixel clock covers text rows 4-7
BAR_ROW = 9
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
    draw_big(canvas, CLOCK_X, CLOCK_PY, view.clock_text(timer.remaining()), color)
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
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -v`
Expected: `219 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/ui/view.py tests/test_view.py src/pomo/render/scene.py tests/test_scene.py
git commit -m "feat: scene: timer panel with pixel clock, the room, Mango blinking" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Stage widget, and the app on the canvas

**Files:**
- Create: `src/pomo/ui/stage.py`
- Test: `tests/test_stage.py`
- Replace: `src/pomo/ui/app.py`, `tests/test_app.py`
- Modify: `src/pomo/ui/view.py` and `tests/test_view.py` (delete `phase_line` and its test)

**Interfaces:**
- Consumes:
  - From Task 1: `Canvas` and `theme.ROOM_BG`.
  - From Task 5: `scene.draw`, `CatSprite`, `CLOCK_X`, `CLOCK_PY`, `PANEL_WIDTH`.
  - From Task 2: `canvas_reading.read_big` and `screen_text`.
  - Everything the milestone 1 app used.
- Produces:
  - `Stage(draw: Callable[[Canvas], None], *, id=None)` with `.canvas` (the last frame) and `.redraw()`.
    - `.redraw()` refreshes all of the widget on a size change, and otherwise refreshes `Region(0, y, width, 1)` only for rows whose `row_key` changed.
    - It also has `.render_line(y) -> Strip`.
  - `TimerScreen(draw)` with `.stage` and `.show(message)`.
  - `PomoApp`: the same constructor as before, plus `.cats: list[CatSprite]`, `.frame: int` and `.draw_scene(canvas)`.
  - Module constants: `TICK_S = 1/8` and `MANGO = CatSprite("Mango", "tabby", "sit", "ok", "floor", 30)`.
- Behavior:
  - `PomoApp.tick()` adds 1 to `frame`, then runs `session.tick()`, then redraws.
  - Everything in milestone 1 still works: confirmations, stale "yes" handling, keeping the Mac awake, toast warnings, and the disabled command palette.
  - Only the display changed. `app.main.stage.canvas` is 100×29 on a 100×30 terminal, because the message bar takes one row.

- [ ] **Step 1: Write the failing tests**

`tests/test_stage.py`:

```python
from textual.app import App, ComposeResult
from textual.geometry import Region

from pomo.render.canvas import Canvas
from pomo.ui.stage import Stage

RED = (255, 0, 0)


class SpyStage(Stage):
    """Records which regions get repainted."""

    def __init__(self, draw):
        super().__init__(draw)
        self.repaints = []

    def refresh(self, *regions, **kwargs):
        self.repaints.append(regions)
        return super().refresh(*regions, **kwargs)


class StageApp(App[None]):
    def __init__(self):
        super().__init__()
        self.red_pixel: tuple[int, int] | None = None
        self.stage = SpyStage(self.draw)

    def compose(self) -> ComposeResult:
        yield self.stage

    def draw(self, canvas: Canvas) -> None:
        canvas.text(0, 0, "hello", (255, 255, 255))
        if self.red_pixel:
            canvas.pixel(*self.red_pixel, RED)


async def test_the_stage_matches_its_size_and_shows_the_canvas():
    app = StageApp()
    async with app.run_test(size=(20, 6)):
        assert (app.stage.canvas.width, app.stage.canvas.height) == (20, 6)
        assert app.stage.canvas.row_text(0).startswith("hello")
        assert app.stage.render_line(0).text.startswith("hello")


async def test_an_unchanged_frame_repaints_nothing():
    app = StageApp()
    async with app.run_test(size=(20, 6)):
        app.stage.repaints.clear()
        app.stage.redraw()
        assert app.stage.repaints == []


async def test_a_change_repaints_only_its_row():
    app = StageApp()
    async with app.run_test(size=(20, 6)):
        app.stage.repaints.clear()
        app.red_pixel = (3, 7)  # pixel row 7 is text row 3
        app.stage.redraw()
        assert app.stage.repaints == [(Region(0, 3, 20, 1),)]


async def test_a_resize_repaints_everything_at_the_new_size():
    app = StageApp()
    async with app.run_test(size=(20, 6)) as pilot:
        await pilot.resize_terminal(30, 8)
        await pilot.pause()
        assert (app.stage.canvas.width, app.stage.canvas.height) == (30, 8)


async def test_lines_below_the_canvas_are_blank():
    app = StageApp()
    async with app.run_test(size=(20, 6)):
        assert app.stage.render_line(50).text == " " * 20
```

Replace all of `tests/test_app.py`. The milestone 1 tests stay; only the helpers now read the canvas, and three tests are new at the end.

```python
from textual.widgets import Static

from canvas_reading import read_big, screen_text
from pomo.clock import FakeClock
from pomo.config import Config
from pomo.render import sprites, theme
from pomo.render.scene import CLOCK_PY, CLOCK_X, PANEL_WIDTH
from pomo.timer import Phase
from pomo.ui.app import PomoApp
from pomo.ui.dialogs import ConfirmScreen

MIN = 60.0
SIZE = (100, 30)


class FakeNotifier:
    def __init__(self):
        self.pings = []

    def send(self, ping):
        self.pings.append(ping)


def make_app(**config):
    clock, notifier = FakeClock(), FakeNotifier()
    return PomoApp(Config(**config), clock, notifier), clock, notifier


def text(app, widget_id):
    return str(app.main.query_one(f"#{widget_id}", Static).render())


def clock_value(app):
    return read_big(app.main.stage.canvas, CLOCK_X, CLOCK_PY, theme.PANEL_BG)


def on_screen(app):
    return screen_text(app.main.stage.canvas)


async def test_shows_a_ready_focus():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        assert clock_value(app) == "25:00"
        assert "● FOCUS" in on_screen(app)
        assert "next: 5 min break" in on_screen(app)


async def test_space_starts_and_the_clock_counts_down():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(61)
        app.tick()
        assert clock_value(app) == "23:59"


async def test_finishing_focus_pings_once_and_starts_the_break():
    app, clock, notifier = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(25 * MIN)
        app.tick()
        assert app.session.timer.phase is Phase.SHORT_BREAK
        assert [p.title for p in notifier.pings] == ["🍅 Pomodoro done!"]
        assert "Time for a break" in text(app, "message")


async def test_a_sleep_wake_jump_sends_one_ping_not_a_flood():
    app, clock, notifier = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(3 * 60 * MIN)  # several phases went by
        app.tick()
        assert len(notifier.pings) == 1


async def test_plus_and_minus_adjust_the_clock():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("plus")
        assert clock_value(app) == "30:00"
        await pilot.press("minus", "minus")
        assert clock_value(app) == "20:00"


async def test_skipping_focus_asks_first_and_no_leaves_it_alone():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s")
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press("n")
        assert app.session.timer.phase is Phase.FOCUS
        assert not isinstance(app.screen, ConfirmScreen)


async def test_confirmed_skip_breaks_the_rule_without_a_ping():
    app, _, notifier = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s", "y")
        assert app.session.timer.phase is Phase.SHORT_BREAK
        assert "(−25)" in text(app, "message")
        assert notifier.pings == []


async def test_resetting_an_unstarted_focus_does_not_ask():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("r")
        assert not isinstance(app.screen, ConfirmScreen)


async def test_keys_are_ignored_while_the_dialog_is_open():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s")
        await pilot.press("space", "s", "r", "plus", "q")
        assert len(app.screen_stack) == 2  # no stacked dialogs
        assert not app.session.timer.running
        assert app.session.timer.length == 25 * MIN
        assert app.is_running


async def test_a_stale_yes_does_not_skip_the_next_phase():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space", "s")  # asked while in focus...
        clock.advance(25 * MIN)
        app.tick()  # ...focus finished on its own meanwhile
        await pilot.press("y")
        assert app.session.timer.phase is Phase.SHORT_BREAK  # the break was not skipped
        assert "phase changed" in text(app, "message")


async def test_quit_before_starting_just_quits():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running


async def test_quit_mid_focus_asks_first():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(1)
        await pilot.press("q")
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press("y")
        await pilot.pause()
        assert not app.is_running


async def test_messages_fade_after_ten_seconds():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s", "y")
        assert text(app, "message")
        clock.advance(11)
        app.tick()
        assert text(app, "message") == ""


def toasts(app):
    return [str(toast.render()) for toast in app.screen.query("Toast")]


async def test_startup_warnings_are_shown_in_full_and_outlive_the_message_line():
    warning = "~/.config/pomo/config.toml holds your ntfy topic but others can read it. Run: chmod 600 ~/.config/pomo/config.toml"
    clock = FakeClock()
    app = PomoApp(Config(), clock, FakeNotifier(), warnings=[warning])
    async with app.run_test(size=SIZE, notifications=True) as pilot:
        await pilot.pause()
        assert any(warning in toast for toast in toasts(app))
        clock.advance(11)
        app.tick()
        await pilot.pause()
        assert any(warning in toast for toast in toasts(app))


async def test_the_command_palette_cannot_quit_around_the_confirm_dialog():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(1)
        await pilot.press("ctrl+p")
        assert type(app.screen).__name__ != "CommandPalette"
        assert app.is_running


async def test_a_stale_yes_to_quit_still_quits_once_quitting_is_free():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(1)
        await pilot.press("q")  # asked mid-focus...
        clock.advance(25 * MIN)
        app.tick()  # ...but the focus ended, and quitting on a break is free
        await pilot.press("y")
        await pilot.pause()
        assert not app.is_running


async def test_a_stale_yes_after_a_full_cycle_leaves_the_new_focus_alone():
    app, clock, _ = make_app(focus=1, short_break=1)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(30)
        await pilot.press("r")  # asked to restart focus 1...
        clock.advance(120)
        app.tick()  # ...focus 1 and its break both ended; focus 2 has run 30 s
        assert app.session.timer.phase is Phase.FOCUS
        await pilot.press("y")
        assert app.session.timer.remaining() == 30  # focus 2 was not reset
        assert "nothing was reset" in text(app, "message")


class FakeKeepAwake:
    def __init__(self):
        self.on = False
        self.changes = []

    def hold(self, on):
        if on != self.on:
            self.on = on
            self.changes.append(on)


async def test_the_mac_is_kept_awake_only_while_a_phase_runs():
    clock, awake = FakeClock(), FakeKeepAwake()
    app = PomoApp(Config(), clock, FakeNotifier(), keep_awake=awake)
    async with app.run_test(size=SIZE) as pilot:
        assert awake.changes == []  # nothing running yet
        await pilot.press("space")
        assert awake.on
        await pilot.press("space")  # paused
        assert not awake.on
        await pilot.press("space")
        clock.advance(25 * MIN)
        app.tick()  # the break starts on its own and keeps running
        assert awake.on
        await pilot.press("q")  # quitting on a break is free
        await pilot.pause()
    assert awake.changes == [True, False, True, False]


async def test_the_room_has_mango_in_it():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        canvas = app.main.stage.canvas
        fur = sprites.COATS["tabby"]["f"]
        assert any(canvas.pixel_at(x, py) == fur
                   for x in range(PANEL_WIDTH, canvas.width) for py in range(canvas.height * 2))


async def test_the_stage_fills_the_screen_above_the_message_line():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        canvas = app.main.stage.canvas
        assert (canvas.width, canvas.height) == (100, 29)


async def test_each_tick_advances_the_animation():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        before = app.frame
        app.tick()
        assert app.frame == before + 1
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_stage.py tests/test_app.py -v`
Expected: `test_stage.py` fails during collection with `ModuleNotFoundError: No module named 'pomo.ui.stage'`, and `test_app.py` fails on `AttributeError: 'TimerScreen' object has no attribute 'stage'`, or on the old `Digits`-based screen.

- [ ] **Step 3: Implement the Stage**

`src/pomo/ui/stage.py`:

```python
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
```

- [ ] **Step 4: Replace the app**

`src/pomo/ui/app.py`:

```python
"""The Textual app: the timer panel and the cat room on one canvas, plus a message line."""

from __future__ import annotations

from collections.abc import Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static

from pomo.awake import KeepsAwake, NoKeepAwake
from pomo.clock import Clock
from pomo.config import Config
from pomo.game.events import Event
from pomo.notify import Notifies, ping_for
from pomo.render import scene
from pomo.render.canvas import Canvas
from pomo.render.scene import CatSprite
from pomo.session import Action, Session
from pomo.timer import TimerSettings, Transition
from pomo.ui import view
from pomo.ui.dialogs import ConfirmScreen
from pomo.ui.stage import Stage

TICK_S = 1 / 8  # 8 fps: the session ticks and the scene redraws together
MESSAGE_TTL_S = 10.0
WARNING_TTL_S = 60.0  # startup warnings are toasts: they wrap in full and outlive the message line
BLOCKED_WHILE_CONFIRMING = {"toggle", "adjust", "skip", "reset", "request_quit"}
MANGO = CatSprite("Mango", "tabby", "sit", "ok", "floor", 30)  # milestone 3 brings the cats to life


class TimerScreen(Screen):
    DEFAULT_CSS = """
    TimerScreen { layout: vertical; }
    #message { height: 1; padding: 0 2; color: $warning; background: #1a1c28; }
    """

    def __init__(self, draw: Callable[[Canvas], None]) -> None:
        super().__init__()
        self._draw = draw

    def compose(self) -> ComposeResult:
        yield Stage(self._draw, id="stage")
        yield Static(id="message")

    @property
    def stage(self) -> Stage:
        return self.query_one(Stage)

    def show(self, message: str) -> None:
        self.stage.redraw()
        self.query_one("#message", Static).update(message)


class PomoApp(App[None]):
    TITLE = "pomo"
    # The palette's "Quit" would exit mid-focus without the confirm dialog (spec §3.2).
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("space", "toggle", "Start/Pause"),
        Binding("s", "skip", "Skip"),
        Binding("r", "reset", "Reset"),
        Binding("plus", "adjust(5)", "+5 min"),
        Binding("minus", "adjust(-5)", "-5 min"),
        Binding("q,ctrl+q", "request_quit", "Quit", key_display="q", priority=True),
    ]

    def __init__(
        self,
        config: Config,
        clock: Clock,
        notifier: Notifies,
        *,
        warnings: list[str] | None = None,
        keep_awake: KeepsAwake | None = None,
    ) -> None:
        super().__init__()
        self.config = config
        self.clock = clock
        self.notifier = notifier
        self.keep_awake = keep_awake or NoKeepAwake()
        self.session = Session(
            TimerSettings.from_minutes(config.focus, config.short_break, config.long_break, config.long_every),
            clock,
        )
        self.cats = [MANGO]
        self.frame = 0
        self.main = TimerScreen(self.draw_scene)
        self.confirming = False
        self._transitions = 0  # every phase change bumps this, so a dialog can tell it went stale
        self._warnings = list(warnings or [])
        self._message = ""
        self._message_at = 0.0

    def get_default_screen(self) -> Screen:
        return self.main

    def on_ready(self) -> None:
        # on_ready, not on_mount: the timer screen's widgets exist by now.
        for warning in self._warnings:
            self.notify(warning, title="pomo", severity="warning", timeout=WARNING_TTL_S)
        self.refresh_view()
        self.set_interval(TICK_S, self.tick)

    def tick(self) -> None:
        self.frame += 1
        self.handle(self.session.tick())
        self.refresh_view()

    def draw_scene(self, canvas: Canvas) -> None:
        scene.draw(canvas, self.session.timer, self.cats, self.frame)

    def handle(self, events: list[Event]) -> None:
        self._transitions += sum(isinstance(e, Transition) for e in events)
        finished = [e for e in events if isinstance(e, Transition) and e.completed]
        if finished:
            # A sleep/wake jump can finish several phases in one tick: ping once, for the latest.
            self.notifier.send(ping_for(finished[-1], self.config))
        for event in events:
            text = view.describe(event)
            if text:
                self.show_message(text)

    def show_message(self, text: str) -> None:
        self._message = text
        self._message_at = self.clock.now()

    def refresh_view(self) -> None:
        if self._message and self.clock.now() - self._message_at > MESSAGE_TTL_S:
            self._message = ""
        self.main.show(self._message)
        # A sleeping Mac stops the clock, so stay awake exactly while a phase runs.
        self.keep_awake.hold(self.session.timer.running)

    def on_unmount(self) -> None:
        self.keep_awake.hold(False)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        return not (self.confirming and action in BLOCKED_WHILE_CONFIRMING)

    def action_toggle(self) -> None:
        self.session.toggle()
        self.refresh_view()

    def action_adjust(self, minutes: int) -> None:
        self.session.adjust(minutes)
        self.refresh_view()

    def action_skip(self) -> None:
        self._guarded(Action.SKIP, lambda: self._apply(self.session.skip()))

    def action_reset(self) -> None:
        self._guarded(Action.RESET, lambda: self._apply(self.session.reset()))

    def action_request_quit(self) -> None:
        self._guarded(Action.QUIT, self._quit)

    def _apply(self, events: list[Event]) -> None:
        self.handle(events)
        self.refresh_view()

    def _quit(self) -> None:
        self.handle(self.session.quit())
        self.exit()

    def _guarded(self, action: Action, perform: Callable[[], None]) -> None:
        """Ask first when the action breaks a rule. A 'yes' that arrives after the phase moved on is stale."""
        cost = self.session.rule_cost(action)
        if cost is None:
            perform()
            return
        asked_at = self._transitions
        self.confirming = True

        def answered(ok: bool | None) -> None:
            self.confirming = False
            if not ok:
                return
            if self._transitions == asked_at:
                perform()
            elif action is Action.QUIT:
                self._guarded(action, perform)  # still wants out: quit now if it's free, else ask at today's price
            else:
                done = "skipped" if action is Action.SKIP else "reset"
                self.show_message(f"The phase changed while you were deciding, so nothing was {done}.")
                self.refresh_view()

        self.push_screen(ConfirmScreen(view.confirm_question(self.session.timer, action, cost)), answered)
```

- [ ] **Step 5: Delete the now-unused `phase_line`**

In `src/pomo/ui/view.py`, delete the whole `phase_line` function. In `tests/test_view.py`, delete the whole `test_phase_line_states` test.

- [ ] **Step 6: Run the tests**

Run: `uv run pytest -v`
Expected: `226 passed`

- [ ] **Step 7: Commit**

```bash
git add src/pomo/ui/stage.py tests/test_stage.py src/pomo/ui/app.py tests/test_app.py src/pomo/ui/view.py tests/test_view.py
git commit -m "feat: split-panel timer screen on the pixel canvas at 8 fps" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Gallery, truecolor warning, README, spec, and a look at it

**Files:**
- Create: `src/pomo/gallery.py`
- Test: `tests/test_gallery.py`
- Replace: `src/pomo/cli.py`, `tests/test_cli.py`, `README.md`
- Modify: `docs/superpowers/specs/2026-09-29-pomo-cats-design.md` (two lines)

**Interfaces:**
- Consumes: `sprites.*` (Task 3), `Stage` (Task 6), `theme` (Task 1).
- Produces:
  - `GalleryApp` with `.coats`, `.index`, `.coat` and `.stage`. Keys: `right`/`n` next coat, `left`/`p` previous coat (both wrap), `q`/`escape` quit.
  - `cli.truecolor_warning(environ) -> str | None`.
  - A `--gallery` flag, which runs the gallery **before** the config is loaded, so a broken config can't block it.

- [ ] **Step 1: Write the failing tests**

`tests/test_gallery.py`:

```python
from canvas_reading import screen_text
from pomo.gallery import GalleryApp
from pomo.render import sprites

SIZE = (100, 30)


def shows_coat(app, coat) -> bool:
    canvas = app.stage.canvas
    fur = sprites.COATS[coat]["f"]
    return any(canvas.pixel_at(x, py) == fur for x in range(canvas.width) for py in range(canvas.height * 2))


async def test_the_gallery_opens_on_the_first_coat_with_every_pose_and_face():
    app = GalleryApp()
    async with app.run_test(size=SIZE):
        text = screen_text(app.stage.canvas)
        assert "tabby  (1/6)" in text
        for pose in sprites.POSES:
            for face in sprites.FACES:
                assert f"{pose} {face}" in text
        for prop in sprites.PROPS:
            assert prop in text
        assert shows_coat(app, "tabby")


async def test_arrows_flip_through_the_coats_and_wrap():
    app = GalleryApp()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("right")
        assert app.coat == "grey" and shows_coat(app, "grey")
        await pilot.press("left", "left")
        assert app.coat == "calico" and shows_coat(app, "calico")


async def test_every_coat_draws():
    app = GalleryApp()
    async with app.run_test(size=SIZE) as pilot:
        for _ in sprites.COATS:
            await pilot.press("right")
            assert shows_coat(app, app.coat)


async def test_q_quits():
    app = GalleryApp()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running
```

Replace all of `tests/test_cli.py`. The milestone 1 tests stay, `--gallery` joins the help test, and three tests are new at the end.

```python
import pytest

from pomo import cli
from pomo.gallery import GalleryApp
from pomo.notify import NullNotifier, Notifier
from pomo.ui.app import PomoApp


@pytest.fixture
def launched(monkeypatch):
    """Stop main() before it takes over the terminal and hand back the app it built."""
    apps = []
    monkeypatch.setattr(PomoApp, "run", lambda self: apps.append(self))
    return apps


def test_help_documents_every_flag(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--help"])
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    for flag in ["--focus", "--short-break", "--long-break", "--long-every", "--no-notify", "--config", "--gallery",
                 "--version"]:
        assert flag in out
    assert "config.toml" in out and "topic" in out


def test_topic_is_not_a_flag(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--topic", "abc"])
    assert "unrecognized arguments" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["0", "-5", "ten"])
def test_bad_durations_are_rejected_by_argparse(value, capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--focus", value])
    assert exit_info.value.code == 2


def test_broken_config_prints_one_line_and_exits_2(tmp_path, capsys, launched):
    path = tmp_path / "config.toml"
    path.write_text("focus = = 1")
    assert cli.main(["--config", str(path)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("pomo: ") and "Traceback" not in err
    assert launched == []


def test_flags_override_the_config_file(tmp_path, launched):
    path = tmp_path / "config.toml"
    path.write_text("focus = 30\nshort_break = 10\n")
    assert cli.main(["--config", str(path), "--focus", "50"]) == 0
    (app,) = launched
    assert (app.config.focus, app.config.short_break) == (50, 10)


def test_notifications_are_on_by_default_and_off_with_no_notify(launched):
    cli.main([])
    cli.main(["--no-notify"])
    assert isinstance(launched[0].notifier, Notifier)
    assert isinstance(launched[1].notifier, NullNotifier)


def test_permission_warning_reaches_the_app(tmp_path, launched):
    path = tmp_path / "config.toml"
    path.write_text('topic = "s3cret"')
    path.chmod(0o644)
    cli.main(["--config", str(path)])
    assert any("chmod 600" in w for w in launched[0]._warnings)


def test_logs_go_to_the_state_dir(tmp_path, launched):
    cli.main([])
    assert (tmp_path / "state" / "pomo").is_dir()


def test_a_missing_config_named_by_flag_exits_2(tmp_path, capsys, launched):
    missing = tmp_path / "confg-typo.toml"
    assert cli.main(["--config", str(missing)]) == 2
    assert "not found" in capsys.readouterr().err
    assert launched == []


def test_config_flag_expands_the_home_directory(tmp_path, monkeypatch, launched):
    # zsh and bash leave "~" alone in --config=~/..., so pomo expands it itself.
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "pomo.toml").write_text("focus = 42\n")
    assert cli.main(["--config=~/pomo.toml"]) == 0
    assert launched[0].config.focus == 42


def test_gallery_flag_opens_the_gallery_instead_of_the_timer(monkeypatch, launched):
    galleries = []
    monkeypatch.setattr(GalleryApp, "run", lambda self: galleries.append(self))
    assert cli.main(["--gallery"]) == 0
    assert len(galleries) == 1 and launched == []


def test_truecolor_warning():
    assert cli.truecolor_warning({"COLORTERM": "truecolor"}) is None
    assert cli.truecolor_warning({"COLORTERM": "24bit"}) is None
    assert "24-bit" in cli.truecolor_warning({})


def test_a_terminal_without_truecolor_gets_warned(monkeypatch, launched):
    monkeypatch.delenv("COLORTERM", raising=False)
    cli.main([])
    assert any("24-bit" in w for w in launched[0]._warnings)
    monkeypatch.setenv("COLORTERM", "truecolor")
    cli.main([])
    assert not any("24-bit" in w for w in launched[1]._warnings)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_gallery.py tests/test_cli.py -v`
Expected: `test_gallery.py` fails during collection with `ModuleNotFoundError: No module named 'pomo.gallery'`. `test_cli.py` also fails during collection, on its `from pomo.gallery import GalleryApp` line.

- [ ] **Step 3: Implement the gallery**

`src/pomo/gallery.py`:

```python
"""`pomo --gallery`: every pose × face for one coat at a time, plus the props (spec §7).

For tuning the art: flip through the coats with ←/→.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding

from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.ui.stage import Stage

COLUMN = 19  # a 17-pixel cat plus a gap
SIT_PY, LOAF_PY, PROPS_PY = 4, 24, 44


class GalleryApp(App[None]):
    TITLE = "pomo gallery"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("right,n", "coat(1)", "Next coat"),
        Binding("left,p", "coat(-1)", "Previous coat"),
        Binding("q,escape", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.coats = list(sprites.COATS)
        self.index = 0
        self.stage = Stage(self.draw)

    @property
    def coat(self) -> str:
        return self.coats[self.index]

    def compose(self) -> ComposeResult:
        yield self.stage

    def action_coat(self, step: int) -> None:
        self.index = (self.index + step) % len(self.coats)
        self.stage.redraw()

    def draw(self, canvas: Canvas) -> None:
        canvas.fill(0, 0, canvas.width, canvas.height, theme.ROOM_BG)
        title = f"{self.coat}  ({self.index + 1}/{len(self.coats)})    ←/→ coat   q quit"
        canvas.text(2, 0, title, theme.TEXT, bold=True)
        palette = sprites.COATS[self.coat]
        for py, pose in ((SIT_PY, "sit"), (LOAF_PY, "loaf")):
            for i, face in enumerate(sprites.FACES):
                x = 2 + i * COLUMN
                grid = sprites.cat(pose, face)
                canvas.sprite(x, py, grid, palette)
                canvas.text(x, _label_row(py, grid), f"{pose} {face}", theme.DIM)
        x = 2
        for name, (grid, prop_palette) in sprites.PROPS.items():
            canvas.sprite(x, PROPS_PY, grid, prop_palette)
            canvas.text(x, _label_row(PROPS_PY, grid), name, theme.DIM)
            x += max(len(grid[0]), len(name)) + 3


def _label_row(py: int, grid: sprites.Grid) -> int:
    """The text row just under a sprite drawn at pixel row py."""
    return (py + len(grid) + 1) // 2
```

- [ ] **Step 4: Replace the CLI**

`src/pomo/cli.py`:

```python
"""`pomo` command line: flags → config → app."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from pomo import __version__
from pomo.awake import keep_awake
from pomo.clock import RealClock
from pomo.config import ConfigError, load_config, permission_warning, with_overrides
from pomo.gallery import GalleryApp
from pomo.notify import Notifier, NullNotifier
from pomo.paths import config_path, log_path
from pomo.ui.app import PomoApp

DESCRIPTION = (
    "A pomodoro timer for your terminal, with cats. "
    "Pings your desktop, and your phone via ntfy, when each phase ends."
)
EPILOG = """\
keys:
  space  start / pause        s  skip phase        r  reset phase
  + / -  add / remove 5 min   q  quit

config file (all keys optional), default ~/.config/pomo/config.toml:
  ntfy_server = "https://ntfy.sh"
  topic = ""          # your ntfy topic; empty disables phone pings
  focus = 25          # minutes
  short_break = 5
  long_break = 15
  long_every = 4      # a long break after this many focus sessions

The ntfy topic is a secret: it is read only from the config file (chmod 600 it),
never from a flag, and never logged.
"""


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pomo",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--focus", type=positive_int, metavar="MIN", help="focus length in minutes (default 25)")
    parser.add_argument("--short-break", type=positive_int, metavar="MIN", help="short break in minutes (default 5)")
    parser.add_argument("--long-break", type=positive_int, metavar="MIN", help="long break in minutes (default 15)")
    parser.add_argument(
        "--long-every", type=positive_int, metavar="N", help="long break after every N focus sessions (default 4)"
    )
    parser.add_argument("--no-notify", action="store_true", help="no desktop or phone notifications")
    parser.add_argument("--config", type=Path, metavar="PATH", help="config file to use instead of the default")
    parser.add_argument("--gallery", action="store_true", help="show every cat sprite and prop (for tuning the art)")
    parser.add_argument("--version", action="version", version=f"pomo {__version__}")
    return parser


def setup_logging(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def truecolor_warning(environ: Mapping[str, str]) -> str | None:
    """iTerm2 and Ghostty set COLORTERM=truecolor. Without it the pixel art gets approximated."""
    if environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return None
    return "This terminal doesn't report 24-bit colour (COLORTERM), so the cats may look a bit off."


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.gallery:
        GalleryApp().run()
        return 0
    if args.config is not None:
        path = args.config.expanduser()  # shells don't expand ~ in --config=~/...
        if not path.is_file():
            print(f"pomo: config file not found: {path}", file=sys.stderr)
            return 2
    else:
        path = config_path()  # the default may be missing: that just means defaults
    try:
        cfg = with_overrides(
            load_config(path),
            focus=args.focus,
            short_break=args.short_break,
            long_break=args.long_break,
            long_every=args.long_every,
        )
    except ConfigError as e:
        print(f"pomo: {e}", file=sys.stderr)
        return 2

    setup_logging(log_path())
    warnings = [w for w in [permission_warning(path, cfg), truecolor_warning(os.environ)] if w]
    app = PomoApp(cfg, RealClock(), NullNotifier(), warnings=warnings, keep_awake=keep_awake())
    if not args.no_notify:
        # The bell must ring on Textual's thread; notifications arrive from a worker thread.
        app.notifier = Notifier(cfg.ntfy_server, cfg.topic, bell=lambda: app.call_from_thread(app.bell))
    app.run()
    return 0
```

- [ ] **Step 5: Replace the README**

`README.md`:

````markdown
# pomo

A pomodoro timer for your terminal, with a room full of pixel-art cats. Mango has moved in;
the others, and their moods, arrive in later milestones.

Needs a terminal with 24-bit colour and at least 100×30 cells. iTerm2 and Ghostty are the targets.

## Install

```bash
uv tool install .    # run from this directory; puts `pomo` on your PATH
```

## Use

```bash
pomo                               # 25 min focus, 5 min breaks, 15 min long break every 4
pomo --focus 50 --short-break 10
pomo --help                        # every flag, key and config option
pomo --gallery                     # every cat pose, face and coat, for tuning the art
```

Keys: `space` start/pause · `s` skip · `r` reset · `+`/`-` 5 min · `q` quit

Skipping or abandoning a focus, skipping a break, or pausing a focus for more than
3 minutes breaks a rule. `pomo` asks before letting you, because the cats will remember.

## Phone pings (ntfy)

Put your topic in `~/.config/pomo/config.toml` and keep the file private:

```toml
topic = "your-secret-topic"
```

```bash
chmod 600 ~/.config/pomo/config.toml
```

## Develop

```bash
uv sync
uv run pytest
```
````

- [ ] **Step 6: Update the spec to match the Task 4 ruling and the real clock width**

In `docs/superpowers/specs/2026-09-29-pomo-cats-design.md`, replace:

```
  - The cat tree is anchored near the left of the room, the litter door to the right edge, and the wall shelf to the right side. The window is centered.
```

with:

```
  - The cat tree, the window and the wall shelf stay together at the left of the room. The window sits between the tree and the shelf, where no perched cat can cover it. The bowl and the litter door follow the right edge.
```

and replace `` (`18:42` is 26 columns) `` with `` (`18:42` is 25 columns) ``.

- [ ] **Step 7: Run everything**

Run: `uv run pytest -v`
Expected: `233 passed`

Run: `uv run pomo --help`
Expected: the flag list includes `--gallery`.

- [ ] **Step 8: Look at it**

Render the app and the gallery to images and check them by eye. Use a scratch script (not committed) that calls `app.export_screenshot()` inside `run_test(size=(100, 30))` for a `PomoApp` with a running focus and for `GalleryApp`, then converts the SVGs to PNGs with headless Chrome. Check each of these:
- The panel shows the red pixel clock, the bar, the counts and the key hints.
- The room shows the purple cat tree, the window with stars, the brown shelf, the blue bowl and the door.
- Mango sits on the floor between the tree and the bowl.
- The gallery shows 5 sit and 5 loaf faces for the coat, labelled, with the props below. ←/→ changes the coat.

Then, if a real terminal is at hand: `uv run pomo --gallery` and `uv run pomo --focus 1`, in both iTerm2 and Ghostty.

- [ ] **Step 9: Commit**

```bash
git add src/pomo/gallery.py tests/test_gallery.py src/pomo/cli.py tests/test_cli.py README.md docs/superpowers/specs/2026-09-29-pomo-cats-design.md
git commit -m "feat: pomo --gallery, truecolor warning; spec: window placement, clock width" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
