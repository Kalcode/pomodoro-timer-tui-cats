import random

from textual.widgets import Static

from canvas_reading import read_big, screen_text
from pomo.clock import FakeClock
from pomo.config import Config
from pomo.game.behavior import Mode
from pomo.game.tools import Tool
from pomo.render import sprites, theme
from pomo.render.scene import CLOCK_PY, CLOCK_X, PANEL_WIDTH
from pomo.timer import Phase
from pomo.ui import view
from pomo.ui.app import PomoApp
from pomo.ui.dialogs import ConfirmScreen
from pomo.ui.stage import Stage
from pomo.ui.toolbar import ToolButton

MIN = 60.0
SIZE = (100, 30)


class FakeNotifier:
    def __init__(self):
        self.pings = []

    def send(self, ping):
        self.pings.append(ping)


def make_app(idle=False, **config):
    clock, notifier = FakeClock(), FakeNotifier()
    return PomoApp(Config(**config), clock, notifier, rng=random.Random(0), idle=idle), clock, notifier


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


async def test_the_stage_fills_the_screen_above_the_message_line_and_toolbar():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        canvas = app.main.stage.canvas
        assert (canvas.width, canvas.height) == (100, 28)


async def test_each_tick_advances_the_animation():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        before = app.frame
        app.tick()
        assert app.frame == before + 1


async def test_an_unchanged_tick_repaints_nothing():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        app.frame = 1  # frames 2 → 3: no blink, no twinkle, and the timer isn't running
        app.tick()
        calls = []
        for widget in (app.main.stage, app.main.query_one("#message"), *app.main.toolbar.query(ToolButton)):
            original = widget.refresh
            widget.refresh = lambda *a, _w=widget.id, _o=original, **k: (calls.append((_w, a, k)), _o(*a, **k))[1]
        app.tick()
        assert calls == []


async def test_the_roster_shows_mango_and_his_mood():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        assert "Mango  ♥♥♥♥♡ content" in on_screen(app)
        await pilot.press("s", "y")  # skipping a focus: −25
        assert app.world.cats[0].mood == 55
        assert "Mango  ♥♥♡♡♡ grumpy" in on_screen(app)


async def test_the_phase_sets_the_cats_mode():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        app.tick()
        assert app.world.mode is Mode.RELAX
        await pilot.press("space")
        app.tick()
        assert app.world.mode is Mode.NAP
        clock.advance(25 * MIN)
        app.tick()
        assert app.world.mode is Mode.PLAY


async def test_time_passing_moves_the_cats():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE):
        seen = set()
        for _ in range(240):
            clock.advance(0.5)
            app.tick()
            (mango,) = app.world.view().cats or (None,)
            seen.add(None if mango is None else (round(mango.x), mango.pose))
        assert len(seen) > 5


async def test_the_world_fits_the_room_on_screen():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        assert (app.world.scape.width, app.world.scape.height) == (70, 56)


async def test_a_terminal_below_the_minimum_keeps_the_minimum_room():
    app, _, _ = make_app()
    async with app.run_test(size=(60, 20)):
        assert (app.world.scape.width, app.world.scape.height) == (70, 54)


# --- the toolbar and the care tools (milestone 4) -------------------------------
# At 100×30 the room is 70×56: its column x is screen column 30 + x, and its pixel
# row y is on screen row y // 2. Mango starts on the floor (pixel row 55) at x = 38.

def label(app, button_id):
    return str(app.main.toolbar.query_one(f"#{button_id}", ToolButton).label)


def on_room(x, y):
    """Screen offset of room column x, pixel row y."""
    return (PANEL_WIDTH + x, y // 2)


async def test_the_toolbar_offers_every_tool_and_the_mode():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        assert [label(app, f"tool-{t}") for t in ("feed", "ball", "string", "pet", "scoop")] == [
            "1 🍗 Feed", "2 🧶 Ball", "3 🧵 String", "4 ✋ Pet", "5 🧹 Scoop"]
        assert label(app, "mode") == "🍅 Pomodoro"


async def test_number_keys_pick_tools_and_escape_puts_them_down():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("2")
        assert app.world.tool is Tool.BALL
        assert app.main.toolbar.query_one("#tool-ball").has_class("-held")
        await pilot.press("4")
        assert app.world.tool is Tool.PET
        assert not app.main.toolbar.query_one("#tool-ball").has_class("-held")
        await pilot.press("escape")
        assert app.world.tool is None


async def test_clicking_a_toolbar_button_picks_its_tool():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.click("#tool-string")
        assert app.world.tool is Tool.STRING


async def test_a_focus_locks_every_tool_but_the_scoop_and_says_why():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        assert label(app, "tool-ball") == "2 🔒 Ball"
        assert app.main.toolbar.query_one("#tool-ball").has_class("-locked")
        assert label(app, "tool-scoop") == "5 🧹 Scoop"
        await pilot.press("2")
        assert app.world.tool is None
        assert text(app, "message") == view.LOCKED
        await pilot.press("5")
        assert app.world.tool is Tool.SCOOP


async def test_starting_a_focus_puts_the_toy_down():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("3", "space")
        assert app.world.tool is None


async def test_the_tools_unlock_on_the_break():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(25 * MIN)
        app.tick()
        assert label(app, "tool-ball") == "2 🧶 Ball"
        await pilot.press("2")
        assert app.world.tool is Tool.BALL


async def test_pressing_1_twice_fills_the_bowl():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        app.world.bowl_full = False
        await pilot.press("1")
        assert not app.world.bowl_full
        await pilot.press("1")
        assert app.world.bowl_full
        assert text(app, "message") == "Kibble's in the bowl."


async def test_clicking_the_bowl_with_kibble_fills_it():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        app.world.bowl_full = False
        await pilot.press("1")
        bowl = app.world.scape.bowl
        await pilot.click(Stage, offset=on_room(bowl.x + 3, bowl.y))
        assert app.world.bowl_full


async def test_the_ball_drops_where_you_click():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("2")
        await pilot.click(Stage, offset=on_room(30, 20))
        assert (app.world.ball.x, app.world.ball.y) == (30, 20)


async def test_the_tool_follows_the_mouse_over_the_room_and_hides_over_the_panel():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("4")
        await pilot.hover(Stage, offset=on_room(20, 20))
        assert app.world.pointer == (20, 20)
        grid, palette, (hx, hy) = sprites.CURSORS["pet"]
        assert app.main.stage.canvas.pixel_at(PANEL_WIDTH + 20, 20) == palette[grid[hy][hx]]
        await pilot.hover(Stage, offset=(10, 10))
        assert app.world.pointer is None


async def test_stroking_mango_with_the_mouse_pets_him():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        mango = app.world.cats[0]
        mango.needs["affection"] = 60
        await pilot.press("4")
        for x in range(33, 40):  # six cells across his back
            await pilot.hover(Stage, offset=on_room(x, 48))
        assert mango.needs["affection"] == 35
        assert [e.kind for e in app.world.view().effects] == ["heart"]


async def test_a_hiss_makes_the_message_line():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        mango = app.world.cats[0]
        mango.mood = 30
        await pilot.press("4")
        for x in range(33, 40):
            await pilot.hover(Stage, offset=on_room(x, 48))
        assert text(app, "message") == "Mango hisses at your hand. Not now."


async def test_i_switches_to_idle_and_back():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("i")
        assert app.session.idle
        assert "● IDLE" in on_screen(app)
        assert "just hanging out" in on_screen(app)
        assert clock_value(app) == ""
        assert label(app, "mode") == "💤 Idle"
        assert text(app, "message") == view.IDLE_ON
        await pilot.press("i")
        assert not app.session.idle
        assert clock_value(app) == "25:00"
        assert text(app, "message") == view.IDLE_OFF


async def test_the_mode_button_switches_to_idle():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.click("#mode")
        assert app.session.idle


async def test_going_idle_mid_focus_asks_first_and_costs_25():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space", "i")
        assert isinstance(app.screen, ConfirmScreen)
        assert "Switch to Idle in the middle of a focus?" in app.screen.question
        await pilot.press("n")
        assert not app.session.idle and app.session.timer.running
        await pilot.press("i", "y")
        assert app.session.idle
        assert app.world.cats[0].mood == 55


async def test_idle_puts_the_timer_keys_away_and_unlocks_every_tool():
    app, clock, _ = make_app(idle=True)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space", "plus", "s", "r")
        assert not isinstance(app.screen, ConfirmScreen)
        clock.advance(30 * MIN)
        app.tick()
        assert not app.session.timer.started
        assert app.session.timer.remaining() == 25 * MIN
        await pilot.press("2")
        assert app.world.tool is Tool.BALL


async def test_the_idle_flag_starts_in_idle_mode():
    app, _, _ = make_app(idle=True)
    async with app.run_test(size=SIZE):
        assert app.session.idle
        assert "● IDLE" in on_screen(app)


async def test_a_stale_yes_to_idle_goes_idle_for_free_once_the_focus_is_over():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space", "i")
        clock.advance(25 * MIN)
        app.tick()  # the focus finished while the dialog was up: +10
        await pilot.press("y")
        assert app.session.idle
        assert app.world.cats[0].mood == 90


async def test_tool_keys_are_ignored_while_a_dialog_is_open():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("5", "space", "s", "escape")  # s asks; escape answers no
        assert app.world.tool is Tool.SCOOP
        await pilot.press("s", "1", "i")
        assert isinstance(app.screen, ConfirmScreen)
        assert app.world.tool is Tool.SCOOP
        assert not app.session.idle


async def test_a_tick_that_fires_during_shutdown_does_nothing():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        pass
    app.tick()  # the screen has been taken apart: this used to raise NoMatches, now and then, on quit
