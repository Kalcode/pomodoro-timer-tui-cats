"""`pomo --gallery`: every front pose × face and the side and roll poses for one coat at a time,
plus the props and tools (spec §7). For tuning the art: flip through the coats with ←/→.
Needs a 100×46 terminal.
"""

from __future__ import annotations

from collections.abc import Mapping

from textual.app import App, ComposeResult
from textual.binding import Binding

from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.render.theme import RGB
from pomo.ui.stage import Stage

COLUMN = 19  # a 17-pixel front cat plus a gap
SIT_PY, LOAF_PY, FLOW_PY = 4, 22, 40
GAP = 3  # columns between the things in the flowing part below the front poses
LABEL_PX = 3  # under each row of the flowing part: a label row and a gap
SIDE_SHOWN = (("walk0", "ok"), ("walk1", "ok"), ("leap", "ok"), ("walk0", "mad"), ("roll0", "ok"), ("roll1", "blink"))

Layer = tuple[sprites.Grid, Mapping[str, RGB]]
Piece = tuple[str, list[Layer]]  # a label, and what to draw over it, back to front


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
                canvas.text(x, _label_row(py, len(grid)), f"{pose} {face}", theme.DIM)
        cats: list[Piece] = [(f"{pose} {face}", [(sprites.cat(pose, face), palette)]) for pose, face in SIDE_SHOWN]
        _flow(canvas, FLOW_PY, cats + _props())


def _props() -> list[Piece]:
    """Every prop, tallest first so the rows pack tight. A back and its front (box_back, box_front) are one
    piece under their shared name, put together the way the room draws them."""
    pieces: dict[str, list[Layer]] = {}
    for name, layer in sprites.PROPS.items():  # PROPS lists each back before its front
        pieces.setdefault(name.removesuffix("_back").removesuffix("_front"), []).append(layer)
    return sorted(pieces.items(), key=lambda piece: -_height(piece[1]))


def _flow(canvas: Canvas, py: int, pieces: list[Piece]) -> None:
    """Lay pieces out left to right from pixel row py, wrapping onto another row at the right edge."""
    x, tallest = 2, 0
    for label, layers in pieces:
        height = _height(layers)
        width = max(*(len(grid[0]) for grid, _ in layers), len(label))
        if x + width >= canvas.width:
            x, py, tallest = 2, py + tallest + LABEL_PX, 0
        for grid, palette in layers:  # bottom rows level
            canvas.sprite(x, py + height - len(grid), grid, palette)
        canvas.text(x, _label_row(py, height), label, theme.DIM)
        x += width + GAP
        tallest = max(tallest, height)


def _height(layers: list[Layer]) -> int:
    return max(len(grid) for grid, _ in layers)


def _label_row(py: int, height: int) -> int:
    """The text row just under a sprite this tall drawn at pixel row py."""
    return (py + height + 1) // 2
