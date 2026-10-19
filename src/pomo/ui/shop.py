"""The shop (home stretch §4): what treats buy. A number key or a click buys on the spot; esc or $ closes it."""

from __future__ import annotations

from collections.abc import Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import Label, Static

from pomo.game.economy import CATALOGUE, Item, Kind, Wallet
from pomo.ui import view


class ShopLine(Static):
    class Picked(Message):
        def __init__(self, key: int) -> None:
            super().__init__()
            self.key = key

    def __init__(self, key: int, item: Item) -> None:
        super().__init__(id=f"item-{item.id}", classes="line")
        self.key, self.item = key, item

    def on_click(self) -> None:
        self.post_message(self.Picked(self.key))


class ShopScreen(ModalScreen[None]):
    DEFAULT_CSS = """
    ShopScreen { align: center middle; }
    #shop { width: 88; height: auto; border: thick $accent; padding: 1 2; background: $surface; }
    #purse { text-style: bold; margin-bottom: 1; }
    ShopScreen .line { height: 1; }
    ShopScreen .line:hover { background: $boost; }
    ShopScreen .line.-short { color: $text-muted; }
    #status { margin-top: 1; height: auto; color: $warning; }
    #hint { color: $text-muted; }
    """
    BINDINGS = [
        *(Binding(str(key), f"buy({key})", show=False) for key in range(1, len(CATALOGUE) + 1)),
        Binding("escape,dollar_sign", "dismiss", "Close"),
    ]

    def __init__(self, wallet: Wallet, buy: Callable[[str], str]) -> None:
        """buy: spends the treats on an item and says how it went."""
        super().__init__()
        self.wallet = wallet
        self._buy = buy
        self._shown: tuple | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="shop"):
            yield Label(id="purse")
            for key, item in enumerate(CATALOGUE, 1):
                yield ShopLine(key, item)
            yield Label("", id="status")
            yield Label(f"1-{len(CATALOGUE)} or click to buy     esc close", id="hint")

    def on_mount(self) -> None:
        self.show()

    def action_buy(self, key: int) -> None:
        self.query_one("#status", Label).update(self._buy(CATALOGUE[key - 1].id))
        self.show()

    def on_shop_line_picked(self, message: ShopLine.Picked) -> None:
        self.action_buy(message.key)

    def show(self) -> None:
        """Bring the lines up to date. The app calls this every tick too, since treats can arrive while it's open."""
        state = (self.wallet.treats, self.wallet.tuna, frozenset(self.wallet.owned))
        if state == self._shown:
            return
        self._shown = state
        self.query_one("#purse", Label).update(f"Shop · you have {self.wallet.treats} {view.TREATS}")
        for line in self.query(ShopLine):
            owned = line.item.kind is not Kind.CONSUMABLE and line.item.id in self.wallet.owned
            line.update(view.shop_line(line.key, line.item, self.wallet))
            line.set_class(not owned and line.item.price > self.wallet.treats, "-short")
