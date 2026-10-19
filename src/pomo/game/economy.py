"""Treats, and what they buy (home stretch §3–§4). Pure: events in, treats out, and a purse to spend them from."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum

from pomo.game import balance
from pomo.game.events import BreakCompleted, Event, FocusCompleted, SetCompleted


class Kind(Enum):
    CONSUMABLE = "consumable"  # bought again and again, used up one at a time
    TOY = "toy"  # bought once: a new tool
    FURNITURE = "furniture"  # bought once: a new spot in the room


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    icon: str
    kind: Kind
    blurb: str

    @property
    def price(self) -> int:
        return balance.PRICES[self.id]


CATALOGUE = (
    Item("tuna", "Tuna can", "🥫", Kind.CONSUMABLE, "+20 mood and a full belly, even when furious"),
    Item("catnip", "Catnip mouse", "🐭", Kind.TOY, "drop it and watch them roll around on it"),
    Item("laser", "Laser pointer", "🔴", Kind.TOY, "a red dot they chase at full zoomies"),
    Item("box", "Cardboard box", "📦", Kind.FURNITURE, "the best nap spot in the house"),
    Item("perch", "Window perch", "🪟", Kind.FURNITURE, "a high seat by the window"),
    Item("hammock", "Hammock", "🧺", Kind.FURNITURE, "a sling under the shelf for long naps"),
)
ITEMS = {item.id: item for item in CATALOGUE}


class Purchase(Enum):
    BOUGHT = "bought"
    OWNED = "owned"  # toys and furniture are bought once
    SHORT = "short"  # not enough treats


def treats_for(event: Event) -> int:
    """Treats a session event earns: a treat per 5 minutes of focus, a bonus for a clean set, one per break."""
    match event:
        case FocusCompleted(minutes=minutes):
            return minutes // balance.TREAT_MINUTES
        case SetCompleted():
            return balance.SET_BONUS
        case BreakCompleted():
            return balance.BREAK_TREATS
    return 0


@dataclass
class Wallet:
    treats: int = balance.TREATS_START
    tuna: int = 0  # cans on hand
    owned: set[str] = field(default_factory=set)  # toys and furniture

    def earn(self, events: Iterable[Event]) -> int:
        """Pay out for these events. Returns how many treats they earned."""
        earned = sum(treats_for(e) for e in events)
        self.treats += earned
        return earned

    def buy(self, item_id: str) -> Purchase:
        item = ITEMS[item_id]
        if item.kind is not Kind.CONSUMABLE and item_id in self.owned:
            return Purchase.OWNED
        if not self.spend(item.price):
            return Purchase.SHORT
        if item_id == "tuna":
            self.tuna += 1
        else:
            self.owned.add(item_id)
        return Purchase.BOUGHT

    def spend(self, price: int) -> bool:
        if self.treats < price:
            return False
        self.treats -= price
        return True
