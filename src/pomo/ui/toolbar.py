"""The care toolbar under the message line (spec §5.2, §6): a button per tool, and Pomodoro ↔ Idle."""

from __future__ import annotations

from collections.abc import Set

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button

from pomo.game.tools import Tool

TOOLS = (  # tool, key, icon, name
    (Tool.FEED, "1", "🍗", "Feed"),
    (Tool.BALL, "2", "🧶", "Ball"),
    (Tool.STRING, "3", "🧵", "String"),
    (Tool.PET, "4", "✋", "Pet"),
    (Tool.SCOOP, "5", "🧹", "Scoop"),
)
MODE_LABELS = {False: "🍅 Pomodoro", True: "💤 Idle"}
LOCK = "🔒"


class ToolButton(Button, can_focus=False):
    """Never takes keyboard focus, so space and the number keys always reach the app."""


class Toolbar(Horizontal):
    DEFAULT_CSS = """
    Toolbar { height: 1; background: #1a1c28; padding: 0 1; }
    Toolbar ToolButton { min-width: 0; margin-right: 1; }
    Toolbar ToolButton.-held { background: $primary; text-style: bold; }
    Toolbar ToolButton.-locked { color: $text-muted; }
    Toolbar #mode { dock: right; margin-right: 0; }
    """

    class Picked(Message):
        def __init__(self, tool: Tool) -> None:
            super().__init__()
            self.tool = tool

    class ModeToggled(Message):
        """The Pomodoro/Idle button was clicked."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._shown: tuple | None = None

    def compose(self) -> ComposeResult:
        for tool, key, icon, name in TOOLS:
            yield ToolButton(f"{key} {icon} {name}", id=f"tool-{tool.value}", compact=True)
        yield ToolButton(MODE_LABELS[False], id="mode", compact=True)

    def show(self, held: Tool | None, locked: Set[Tool], idle: bool) -> None:
        """Mark the tool in hand and the locked ones. Touches nothing if nothing changed."""
        state = (held, frozenset(locked), idle)
        if state == self._shown:
            return
        self._shown = state
        for tool, key, icon, name in TOOLS:
            button = self.query_one(f"#tool-{tool.value}", ToolButton)
            button.label = f"{key} {LOCK if tool in locked else icon} {name}"
            button.set_class(tool is held, "-held")
            button.set_class(tool in locked, "-locked")
        self.query_one("#mode", ToolButton).label = MODE_LABELS[idle]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "mode":
            self.post_message(self.ModeToggled())
        else:
            self.post_message(self.Picked(Tool(event.button.id.removeprefix("tool-"))))
