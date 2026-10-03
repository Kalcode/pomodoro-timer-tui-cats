"""The Textual app: the timer panel and the cat room on one canvas, a message line, and the toolbar."""

from __future__ import annotations

import logging
import random
from collections.abc import Callable, Iterable
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static

from pomo import persist
from pomo.awake import KeepsAwake, NoKeepAwake
from pomo.clock import Clock, WallClock
from pomo.config import Config
from pomo.game.cat import Cat, Trait
from pomo.game.events import Event, RuleBreak
from pomo.game.playscape import MIN_HEIGHT, MIN_WIDTH
from pomo.game.tools import Tool, locked
from pomo.game.world import World, mode_for
from pomo.notify import Notifies, ping_for
from pomo.render import scene
from pomo.render.canvas import Canvas
from pomo.session import Action, Session
from pomo.timer import TimerSettings, Transition
from pomo.ui import view
from pomo.ui.dialogs import ConfirmScreen
from pomo.ui.stage import Stage
from pomo.ui.toolbar import TOOLS, Toolbar

log = logging.getLogger(__name__)

TICK_S = 1 / 8  # 8 fps: the session ticks and the scene redraws together
SAVE_EVERY_S = 30.0  # and on every phase change, and on the way out (addendum §2.2)
MESSAGE_TTL_S = 10.0
WARNING_TTL_S = 60.0  # startup warnings are toasts: they wrap in full and outlive the message line
TIMER_ACTIONS = {"toggle", "adjust", "skip", "reset"}  # put away in Idle mode
BLOCKED_WHILE_CONFIRMING = TIMER_ACTIONS | {"request_quit", "tool", "drop_tool", "toggle_idle"}


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
        yield Toolbar(id="toolbar")

    @property
    def stage(self) -> Stage:
        return self.query_one(Stage)

    @property
    def toolbar(self) -> Toolbar:
        return self.query_one(Toolbar)

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
        Binding("i", "toggle_idle", "Idle"),
        *(Binding(key, f"tool('{tool.value}')", name, show=False) for tool, key, _, name in TOOLS),
        Binding("escape", "drop_tool", "Put the tool down", show=False),
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
        rng: random.Random | None = None,
        idle: bool = False,
        saved: persist.Saved | None = None,
        save_path: Path | None = None,
        wall: Clock | None = None,
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
        rng = rng or random.Random()
        self.save_path = save_path  # None: nothing is saved (tests, mostly)
        self.wall = wall or WallClock()
        self.frame = 0
        self._last_tick = self._last_save = clock.now()
        self._save_failing = False
        self.main = TimerScreen(self.draw_scene)
        self.confirming = False
        self._transitions = 0  # every phase change bumps this, so a dialog can tell it went stale
        self._warnings = list(warnings or [])
        self._message = ""
        self._message_at = 0.0
        if saved is None:
            self.world = World([Cat("Mango", "tabby", Trait.CLINGY)], rng)  # spec §4: a new save
        else:
            self.world = persist.build_world(saved, rng)
            events = self.session.restore(saved.session, max(0.0, self.wall.now() - saved.saved_at))
            self.handle(events)
            if any(isinstance(e, RuleBreak) for e in events):
                self.show_message(view.remembers(self.world.cats))
        if idle and not self.session.idle:
            self.session.enter_idle()  # --idle wins over the save; free, since nothing restored is running

    def get_default_screen(self) -> Screen:
        return self.main

    def on_ready(self) -> None:
        # on_ready, not on_mount: the timer screen's widgets exist by now.
        for warning in self._warnings:
            self.notify(warning, title="pomo", severity="warning", timeout=WARNING_TTL_S)
        self.refresh_view()
        self.set_interval(TICK_S, self.tick)

    def tick(self) -> None:
        if not self.is_running:
            return  # quitting: the interval can still fire while the screen is taken apart
        now = self.clock.now()
        dt, self._last_tick = now - self._last_tick, now
        self.frame += 1
        self.handle(self.session.tick())
        self._sync_mode()
        self.world.tick(dt)
        self._report(self.world.take_news())
        if now - self._last_save >= SAVE_EVERY_S:
            self.save()
        self.refresh_view()

    @property
    def too_small(self) -> bool:
        return scene.too_small(self.size.width, self.size.height)

    def draw_scene(self, canvas: Canvas) -> None:
        if not self.too_small:  # the room on screen decides the geometry; a too-small one leaves it as it was
            room_w, room_h = canvas.width - scene.PANEL_WIDTH, canvas.height * 2
            self.world.fit(max(MIN_WIDTH, room_w), max(MIN_HEIGHT, room_h))
        scene.draw(canvas, self.session.timer, self.world.view(), self.frame, idle=self.session.idle,
                   terminal=(self.size.width, self.size.height))

    def handle(self, events: list[Event]) -> None:
        self.world.apply(events)
        changes = sum(isinstance(e, Transition) for e in events)
        self._transitions += changes
        if changes:
            self.save()
        finished = [e for e in events if isinstance(e, Transition) and e.completed]
        if finished:
            # A sleep/wake jump can finish several phases in one tick: ping once, for the latest.
            last = finished[-1]
            self.notifier.send(ping_for(last, self.config, view.cat_line(self.world.cats, last.started)))
        self._report(events)

    def _report(self, events: Iterable[Event]) -> None:
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
        self._sync_mode()
        toolbar = self.main.toolbar
        if toolbar.display == self.too_small:  # hidden while the window is too small, back when it grows
            toolbar.display = not self.too_small
            self.world.leave()
        toolbar.show(self.world.tool, {t for t in Tool if locked(t, self.world.mode)}, self.session.idle)
        self.main.show(self._message)
        # A sleeping Mac stops the clock, so stay awake exactly while a phase runs.
        self.keep_awake.hold(self.session.timer.running)

    def _sync_mode(self) -> None:
        timer = self.session.timer
        self.world.set_mode(mode_for(timer.phase, timer.started, self.session.idle))

    def save(self) -> None:
        """Write the save (addendum §2.2). A failure is shown once, and tried again at the next save point."""
        self._last_save = self.clock.now()
        if self.save_path is None:
            return
        try:
            persist.write(self.save_path, persist.snapshot(self.session, self.world, self.wall.now()))
        except OSError as e:
            log.warning("saving failed: %s", type(e).__name__)
            if not self._save_failing:
                self.show_message(f"Couldn't save your cats: {e.strerror or type(e).__name__}.")
            self._save_failing = True
        else:
            self._save_failing = False

    def on_unmount(self) -> None:
        self.keep_awake.hold(False)
        self.save()  # however the app is closing; a focus still under way is charged on the next launch

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.confirming and action in BLOCKED_WHILE_CONFIRMING:
            return False
        return not (self.session.idle and action in TIMER_ACTIONS)

    # --- the timer -----------------------------------------------------------------

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

    def action_toggle_idle(self) -> None:
        if self.session.idle:
            self.handle(self.session.leave_idle())
            self.show_message(view.IDLE_OFF)
            self.refresh_view()
        else:
            self._guarded(Action.IDLE, self._go_idle)

    def _go_idle(self) -> None:
        events = self.session.enter_idle()
        self.handle(events)
        if not events:  # a rule break's message matters more
            self.show_message(view.IDLE_ON)
        self.refresh_view()

    def _apply(self, events: list[Event]) -> None:
        self.handle(events)
        self.refresh_view()

    def _quit(self) -> None:
        self.handle(self.session.quit())
        self.save()
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
            elif action in (Action.QUIT, Action.IDLE):
                self._guarded(action, perform)  # still wants it: do it now if it's free, else ask at today's price
            else:
                done = "skipped" if action is Action.SKIP else "reset"
                self.show_message(f"The phase changed while you were deciding, so nothing was {done}.")
                self.refresh_view()

        self.push_screen(ConfirmScreen(view.confirm_question(self.session.timer, action, cost)), answered)

    # --- the care tools ------------------------------------------------------------

    def action_tool(self, name: str) -> None:
        if not self.world.hold(Tool(name)):
            self.show_message(view.LOCKED)
        self._after_hand()

    def action_drop_tool(self) -> None:
        self.world.hold(None)
        self._after_hand()

    def on_toolbar_picked(self, message: Toolbar.Picked) -> None:
        if not self.confirming:
            self.action_tool(message.tool.value)

    def on_toolbar_mode_toggled(self, message: Toolbar.ModeToggled) -> None:
        if not self.confirming:
            self.action_toggle_idle()

    def _room_point(self, col: float, row: float) -> tuple[float, float] | None:
        return None if self.too_small else scene.room_point(col, row)

    def on_stage_pointer(self, message: Stage.Pointer) -> None:
        point = self._room_point(message.col, message.row)
        if point is None:
            self.world.leave()  # over the timer panel
        else:
            self.world.point(*point)
        self._after_hand()

    def on_stage_pressed(self, message: Stage.Pressed) -> None:
        point = self._room_point(message.col, message.row)
        if point is not None:
            self.world.click(*point)
        self._after_hand()

    def on_stage_left(self, message: Stage.Left) -> None:
        self.world.leave()
        self._after_hand()

    def _after_hand(self) -> None:
        self._report(self.world.take_news())
        self.refresh_view()
