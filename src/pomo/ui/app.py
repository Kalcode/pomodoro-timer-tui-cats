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
        self._shown_message: str | None = None

    def compose(self) -> ComposeResult:
        yield Stage(self._draw, id="stage")
        yield Static(id="message")

    @property
    def stage(self) -> Stage:
        return self.query_one(Stage)

    def show(self, message: str) -> None:
        self.stage.redraw()
        if message != self._shown_message:  # an unchanged tick must repaint nothing
            self._shown_message = message
            self.query_one("#message", Static).update(message, layout=False)  # fixed height: no layout pass


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
