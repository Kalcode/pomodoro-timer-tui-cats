"""Yes/no dialog shown before any rule-breaking action (spec §3.2)."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label


class ConfirmScreen(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmScreen { align: center middle; }
    #dialog { width: 54; height: auto; border: thick $warning; padding: 1 2; background: $surface; }
    #hint { color: $text-muted; margin-top: 1; }
    """
    BINDINGS = [
        Binding("y", "answer(True)", "Yes"),
        Binding("n,escape", "answer(False)", "No"),
    ]

    def __init__(self, question: str) -> None:
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.question, id="question")
            yield Label("y  yes     n / esc  no", id="hint")

    def action_answer(self, ok: bool) -> None:
        self.dismiss(ok)
