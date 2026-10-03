"""The care toolbar under the message line (spec §5.2, §6): a button per tool, and Pomodoro ↔ Idle."""

from __future__ import annotations

from collections.abc import Set

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
)
LOCK = "🔒"


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

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._shown: tuple | None = None
        self._idle = False

    def compose(self) -> ComposeResult:
        for tool, key, icon, name in TOOLS:
            yield ToolButton(f"{key} {icon} {name}", id=f"tool-{tool.value}", compact=True)
        with Horizontal(id="modes"):  # both modes, the current one highlighted
            yield ToolButton("🍅 Pomodoro", id="mode-pomodoro", compact=True)
            yield ToolButton("💤 Idle", id="mode-idle", compact=True)

    def show(self, held: Tool | None, locked: Set[Tool], idle: bool) -> None:
        """Mark the tool in hand, the locked ones and the mode. Touches nothing if nothing changed."""
        state = (held, frozenset(locked), idle)
        if state == self._shown:
            return
        self._shown, self._idle = state, idle
        for tool, key, icon, name in TOOLS:
            button = self.query_one(f"#tool-{tool.value}", ToolButton)
            button.label = f"{key} {LOCK if tool in locked else icon} {name}"
            button.set_class(tool is held, "-held")
            button.set_class(tool in locked, "-locked")
        self.query_one("#mode-pomodoro", ToolButton).set_class(not idle, "-held")
        self.query_one("#mode-idle", ToolButton).set_class(idle, "-held")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        button = event.button.id or ""
        if button.startswith("mode-"):
            if (button == "mode-idle") != self._idle:  # the current mode's button does nothing
                self.post_message(self.ModeToggled())
        else:
            self.post_message(self.Picked(Tool(button.removeprefix("tool-"))))
