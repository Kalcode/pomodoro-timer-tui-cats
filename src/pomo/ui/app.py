"""The Textual app for milestone 1: a plain timer screen (the cats arrive in milestone 2)."""

from __future__ import annotations

from collections.abc import Callable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Digits, Footer, Static

from pomo.clock import Clock
from pomo.config import Config
from pomo.game.events import Event
from pomo.notify import Notifies, ping_for
from pomo.session import Action, Session
from pomo.timer import TimerSettings, Transition
from pomo.ui import view
from pomo.ui.dialogs import ConfirmScreen

TICK_S = 0.25
MESSAGE_TTL_S = 10.0
WARNING_TTL_S = 60.0  # startup warnings are toasts: they wrap in full and outlive the message line
BAR_WIDTH = 38
BLOCKED_WHILE_CONFIRMING = {"toggle", "adjust", "skip", "reset", "request_quit"}


class TimerScreen(Screen):
    DEFAULT_CSS = """
    TimerScreen { align: center middle; }
    #panel { width: 46; height: auto; border: round $primary; padding: 1 2; }
    #phase { text-style: bold; color: $error; }
    #clock { width: auto; margin: 1 0; }
    #next { color: $text-muted; }
    #message { color: $warning; height: 2; margin-top: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="panel"):
            yield Static(id="phase")
            yield Digits("25:00", id="clock")
            yield Static(id="progress")
            yield Static(id="count")
            yield Static(id="next")
            yield Static(id="message")
        yield Footer()

    def show(self, session: Session, message: str) -> None:
        timer = session.timer
        self.query_one("#phase", Static).update(view.phase_line(timer))
        self.query_one("#clock", Digits).update(view.clock_text(timer.remaining()))
        self.query_one("#progress", Static).update(view.progress_bar(timer, BAR_WIDTH))
        self.query_one("#count", Static).update(view.count_line(timer))
        self.query_one("#next", Static).update(view.next_line(timer))
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

    def __init__(self, config: Config, clock: Clock, notifier: Notifies, *, warnings: list[str] | None = None) -> None:
        super().__init__()
        self.config = config
        self.clock = clock
        self.notifier = notifier
        self.session = Session(
            TimerSettings.from_minutes(config.focus, config.short_break, config.long_break, config.long_every),
            clock,
        )
        self.main = TimerScreen()
        self.confirming = False
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
        self.handle(self.session.tick())
        self.refresh_view()

    def handle(self, events: list[Event]) -> None:
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
        self.main.show(self.session, self._message)

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
        """Ask first when the action breaks a rule. Ignore a stale 'yes' if the phase moved on meanwhile."""
        cost = self.session.rule_cost(action)
        if cost is None:
            perform()
            return
        asked_in = self.session.timer.phase
        self.confirming = True

        def answered(ok: bool | None) -> None:
            self.confirming = False
            if ok and self.session.timer.phase is asked_in:
                perform()
            elif ok:
                self.show_message("The phase changed while you were deciding, so nothing was skipped.")
                self.refresh_view()

        self.push_screen(ConfirmScreen(view.confirm_question(self.session.timer, action, cost)), answered)
