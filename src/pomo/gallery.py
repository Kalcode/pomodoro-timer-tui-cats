"""`pomo --gallery`: every front pose × face and the side poses for one coat at a time,
plus the props and tools (spec §7). For tuning the art: flip through the coats with ←/→.
Needs a 100×46 terminal.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding

from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.ui.stage import Stage

COLUMN = 19  # a 17-pixel front cat plus a gap
SIDE_COLUMN = 22  # a 20-pixel side cat plus a gap
SIT_PY, LOAF_PY, SIDE_PY, PROPS_PY = 4, 24, 44, 64
PROP_GAP = 3  # columns between props
LABEL_PX = 4  # a label row under each row of props, and a gap
SIDE_SHOWN = (("walk0", "ok"), ("walk1", "ok"), ("leap", "ok"), ("walk0", "mad"))


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
        for i, (pose, face) in enumerate(SIDE_SHOWN):
            x = 2 + i * SIDE_COLUMN
            grid = sprites.cat(pose, face)
            canvas.sprite(x, SIDE_PY, grid, palette)
            canvas.text(x, _label_row(SIDE_PY, grid), f"{pose} {face}", theme.DIM)
        x, py, tallest = 2, PROPS_PY, 0
        for name, (grid, prop_palette) in sprites.PROPS.items():
            width = max(len(grid[0]), len(name))
            if x + width >= canvas.width:  # wrap onto another row
                x, py, tallest = 2, py + tallest + LABEL_PX, 0
            canvas.sprite(x, py, grid, prop_palette)
            canvas.text(x, _label_row(py, grid), name, theme.DIM)
            x += width + PROP_GAP
            tallest = max(tallest, len(grid))


def _label_row(py: int, grid: sprites.Grid) -> int:
    """The text row just under a sprite drawn at pixel row py."""
    return (py + len(grid) + 1) // 2
