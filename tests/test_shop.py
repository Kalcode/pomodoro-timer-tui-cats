import random

from textual.widgets import Label, Static

from pomo.clock import FakeClock
from pomo.config import Config
from pomo.game.tools import Tool
from pomo.notify import NullNotifier
from pomo.ui import view
from pomo.ui.app import PomoApp
from pomo.ui.shop import ShopScreen
from pomo.ui.toolbar import ToolButton

SIZE = (100, 30)


def make_app(treats=5):
    clock = FakeClock()
    app = PomoApp(Config(), clock, NullNotifier(), rng=random.Random(0))
    app.world.wallet.treats = treats
    return app, clock


def message(app):
    return str(app.main.query_one("#message", Static).render())


def status(app):
    return str(app.screen.query_one("#status", Label).render())


async def test_dollar_opens_the_shop_and_a_number_buys():
    app, _ = make_app(treats=7)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("dollar_sign")
        assert isinstance(app.screen, ShopScreen)
        await pilot.press("1")
        assert (app.world.wallet.treats, app.world.wallet.tuna) == (2, 1)
        assert status(app).startswith("Bought: tuna can.")
        await pilot.press("1")
        assert status(app) == "The tuna can is 5 🐟: you need 3 more."
        await pilot.press("escape")
        assert app.screen is app.main


async def test_the_shop_button_opens_it_too():
    app, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.click("#shop")
        assert isinstance(app.screen, ShopScreen)


async def test_clicking_a_line_buys_it():
    app, _ = make_app(treats=40)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("dollar_sign")
        await pilot.click("#item-box")
        assert app.world.wallet.owned == {"box"}
        assert app.world.wallet.treats == 25


async def test_the_timer_and_tools_wait_while_the_shop_is_open():
    app, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("dollar_sign", "space", "2")
        assert not app.session.timer.running
        assert app.world.tool is None
        await pilot.press("escape", "space")
        assert app.session.timer.running


async def test_bought_tools_show_up_on_the_toolbar_and_everything_still_fits():
    app, _ = make_app(treats=200)
    async with app.run_test(size=SIZE) as pilot:
        assert not app.main.query_one("#tool-tuna", ToolButton).display
        await pilot.press("dollar_sign", "1", "1", "2", "3", "escape")
        tuna = app.main.query_one("#tool-tuna", ToolButton)
        assert tuna.display and str(tuna.label) == "6 🥫×2"
        await pilot.pause()
        buttons = sorted(app.main.query(ToolButton), key=lambda b: b.region.x)
        assert all(b.region.width > 0 for b in buttons)
        for left, right in zip(buttons, buttons[1:]):
            assert left.region.right <= right.region.x, (left.id, right.id)
        assert buttons[-1].region.right <= SIZE[0]


async def test_a_tool_you_dont_have_says_where_to_get_it():
    app, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("6")
        assert message(app) == view.MISSING[Tool.TUNA]
        await pilot.press("8")
        assert message(app) == view.MISSING[Tool.LASER]


async def test_tuna_in_a_focus_cheers_up_the_unhappiest_cat():
    app, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        app.world.wallet.tuna = 1
        app.world.cats[0].mood = 30
        await pilot.press("space", "6", "6")
        assert app.world.cats[0].mood == 50
        assert message(app) == "Mango wolfs down the tuna (+20)."
        assert app.world.tool is None  # that was the last can
