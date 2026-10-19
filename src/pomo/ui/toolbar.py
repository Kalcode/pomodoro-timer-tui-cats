"""The care toolbar under the message line (spec §5.2, §6): a button per tool, the shop, and Pomodoro ↔ Idle.

The shop's tools have fixed keys (6 tuna, 7 catnip, 8 laser) and a button that shows up once you own them.
When everything won't fit across the window, the care tools drop their names and keep their keys and icons.
"""

from __future__ import annotations

from collections.abc import Set

from rich.cells import cell_len
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button

from pomo.game.tools import Tool
from pomo.render.theme import BAR_BG, css

TOOLS = (  # tool, key, icon, name
    (Tool.FEED, "1", "🍗", "Feed"),
    (Tool.BALL, "2", "🧶", "Ball"),
    (Tool.STRING, "3", "🧵", "String"),
    (Tool.PET, "4", "✋", "Pet"),
    (Tool.SCOOP, "5", "🧹", "Scoop"),
    (Tool.TUNA, "6", "🥫", "Tuna"),
    (Tool.CATNIP, "7", "🐭", "Catnip"),
    (Tool.LASER, "8", "🔴", "Laser"),
)
BOUGHT = frozenset({Tool.TUNA, Tool.CATNIP, Tool.LASER})  # from the shop: shown once you have them
LOCK = "🔒"


MODES = ("$ Shop", "🍅 Pomodoro", "💤 Idle")
BUTTON_EXTRA = 3  # a compact button's padding either side, and its margin
BAR_PADDING = 2


def label(tool: Tool, key: int | str, icon: str, name: str, locked: bool, tuna: int = 0, short: bool = False) -> str:
    icon = LOCK if locked else icon
    if tool is Tool.TUNA:
        return f"{key} {icon}×{tuna}"
    return f"{key} {icon}" if short or tool in BOUGHT else f"{key} {icon} {name}"


def fits(width: int, have: Set[Tool], tuna: int) -> bool:
    """Whether every button fits across `width` columns with the care tools' names spelt out."""
    labels = [label(t, k, i, n, False, tuna) for t, k, i, n in TOOLS if t not in BOUGHT or t in have]
    return sum(cell_len(text) + BUTTON_EXTRA for text in [*labels, *MODES]) + BAR_PADDING <= width


class ToolButton(Button, can_focus=False):
    """Never takes keyboard focus, so space and the number keys always reach the app."""


class Toolbar(Horizontal):
    DEFAULT_CSS = f"""
    Toolbar {{ height: 1; background: {css(BAR_BG)}; padding: 0 1; }}
    Toolbar ToolButton {{ min-width: 0; margin-right: 1; }}
    Toolbar ToolButton.-held {{ background: $primary; text-style: bold; }}
    Toolbar ToolButton.-locked {{ color: $text-muted; }}
    Toolbar #modes {{ dock: right; width: auto; height: 1; }}
    Toolbar #modes ToolButton {{ margin: 0 0 0 1; }}
    """

    class Picked(Message):
        def __init__(self, tool: Tool) -> None:
            super().__init__()
            self.tool = tool

    class ModeToggled(Message):
        """The mode you're not in was clicked: Pomodoro or Idle."""

    class ShopOpened(Message):
        """The shop button was clicked."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._shown: tuple | None = None
        self._idle = False

    def compose(self) -> ComposeResult:
        for tool, key, icon, name in TOOLS:
            button = ToolButton(label(tool, key, icon, name, False), id=f"tool-{tool.value}", compact=True)
            button.display = tool not in BOUGHT
            yield button
        with Horizontal(id="modes"):  # the shop, and both modes with the current one highlighted
            for text, button_id in zip(MODES, ("shop", "mode-pomodoro", "mode-idle"), strict=True):
                yield ToolButton(text, id=button_id, compact=True)

    def show(self, held: Tool | None, locked: Set[Tool], idle: bool, have: Set[Tool] = frozenset(),
             tuna: int = 0) -> None:
        """Mark the tool in hand, the locked ones and the mode, and show the shop's tools you have.
        Touches nothing if nothing changed."""
        short = not fits(self.size.width, have, tuna)
        state = (held, frozenset(locked), idle, frozenset(have), tuna, short)
        if state == self._shown:
            return
        self._shown, self._idle = state, idle
        for tool, key, icon, name in TOOLS:
            button = self.query_one(f"#tool-{tool.value}", ToolButton)
            text = label(tool, key, icon, name, tool in locked, tuna, short)
            if cell_len(text) != cell_len(str(button.label)):
                button.refresh(layout=True)  # setting the label doesn't ask for the layout pass a new width needs
            button.label = text
            button.display = tool not in BOUGHT or tool in have
            button.set_class(tool is held, "-held")
            button.set_class(tool in locked, "-locked")
        self.query_one("#mode-pomodoro", ToolButton).set_class(not idle, "-held")
        self.query_one("#mode-idle", ToolButton).set_class(idle, "-held")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        button = event.button.id or ""
        if button == "shop":
            self.post_message(self.ShopOpened())
        elif button.startswith("mode-"):
            if (button == "mode-idle") != self._idle:  # the current mode's button does nothing
                self.post_message(self.ModeToggled())
        else:
            self.post_message(self.Picked(Tool(button.removeprefix("tool-"))))
