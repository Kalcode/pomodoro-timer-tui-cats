from textual import events
from textual.app import App, ComposeResult
from textual.geometry import Region

from pomo.render.canvas import Canvas
from pomo.ui.stage import Stage

RED = (255, 0, 0)


class SpyStage(Stage):
    """Records which regions get repainted."""

    def __init__(self, draw):
        super().__init__(draw)
        self.repaints = []

    def refresh(self, *regions, **kwargs):
        self.repaints.append(regions)
        return super().refresh(*regions, **kwargs)


class StageApp(App[None]):
    def __init__(self):
        super().__init__()
        self.red_pixel: tuple[int, int] | None = None
        self.stage = SpyStage(self.draw)

    def compose(self) -> ComposeResult:
        yield self.stage

    def draw(self, canvas: Canvas) -> None:
        canvas.text(0, 0, "hello", (255, 255, 255))
        if self.red_pixel:
            canvas.pixel(*self.red_pixel, RED)


async def test_the_stage_matches_its_size_and_shows_the_canvas():
    app = StageApp()
    async with app.run_test(size=(20, 6)):
        assert (app.stage.canvas.width, app.stage.canvas.height) == (20, 6)
        assert app.stage.canvas.row_text(0).startswith("hello")
        assert app.stage.render_line(0).text.startswith("hello")


async def test_an_unchanged_frame_repaints_nothing():
    app = StageApp()
    async with app.run_test(size=(20, 6)):
        app.stage.repaints.clear()
        app.stage.redraw()
        assert app.stage.repaints == []


async def test_a_change_repaints_only_the_cells_that_changed():
    app = StageApp()
    async with app.run_test(size=(20, 6)):
        app.stage.repaints.clear()
        app.red_pixel = (3, 7)  # pixel row 7 is text row 3
        app.stage.redraw()
        assert app.stage.repaints == [(Region(2, 3, 3, 1),)]  # column 3, and one either side for wide glyphs


async def test_changes_far_apart_on_a_row_repaint_the_span_between_them():
    app = StageApp()
    async with app.run_test(size=(20, 6)):
        app.red_pixel = (0, 7)
        app.stage.redraw()
        app.stage.repaints.clear()
        app.red_pixel = (19, 7)
        app.stage.redraw()
        assert app.stage.repaints == [(Region(0, 3, 20, 1),)]


async def test_a_resize_repaints_everything_at_the_new_size():
    app = StageApp()
    async with app.run_test(size=(20, 6)) as pilot:
        await pilot.resize_terminal(30, 8)
        await pilot.pause()
        assert (app.stage.canvas.width, app.stage.canvas.height) == (30, 8)


async def test_lines_below_the_canvas_are_blank():
    app = StageApp()
    async with app.run_test(size=(20, 6)):
        assert app.stage.render_line(50).text == " " * 20


class MouseApp(StageApp):
    """Records what the stage says about the mouse."""

    def __init__(self):
        super().__init__()
        self.heard = []

    def on_stage_pointer(self, message: Stage.Pointer) -> None:
        self.heard.append(("Pointer", message.col, message.row))

    def on_stage_pressed(self, message: Stage.Pressed) -> None:
        self.heard.append(("Pressed", message.col, message.row))

    def on_stage_left(self, message: Stage.Left) -> None:
        self.heard.append(("Left",))


async def test_the_stage_reports_the_mouse_in_its_own_cells():
    app = MouseApp()
    async with app.run_test(size=(20, 6)) as pilot:
        await pilot.hover(Stage, offset=(5, 2))
        await pilot.click(Stage, offset=(7, 3))
        await pilot.pause()
        assert ("Pointer", 5, 2) in app.heard
        assert ("Pressed", 7, 3) in app.heard


async def test_the_stage_says_when_the_mouse_leaves():
    app = MouseApp()
    async with app.run_test(size=(20, 6)) as pilot:
        await pilot.hover(Stage, offset=(5, 2))
        app.stage.post_message(events.Leave(app.stage))
        await pilot.pause()
        assert app.heard[-1] == ("Left",)
