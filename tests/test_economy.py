import random

import pytest

from pomo.game.behavior import Doing, Mode, Step
from pomo.game.cat import Cat, Stage, Trait
from pomo.game.economy import CATALOGUE, ITEMS, Purchase, Wallet, treats_for
from pomo.game.events import BreakCompleted, FocusCompleted, RuleBreak, RuleKind, SetCompleted, TunaEaten
from pomo.game.tools import Tool
from pomo.game.world import World
from pomo.timer import Phase


def room(*cats: Cat) -> World:
    return World(list(cats), random.Random(3))


# --- earning -------------------------------------------------------------------


@pytest.mark.parametrize("event, treats", [
    (FocusCompleted(25), 5), (FocusCompleted(50), 10), (FocusCompleted(14), 2), (FocusCompleted(4), 0),
    (SetCompleted(), 5), (BreakCompleted(Phase.SHORT_BREAK), 1), (BreakCompleted(Phase.LONG_BREAK), 1),
    (RuleBreak(RuleKind.SKIP_BREAK), 0),
])
def test_what_each_event_earns(event, treats):
    assert treats_for(event) == treats


def test_a_new_save_starts_with_five_treats():
    assert Wallet().treats == 5
    assert room(Cat("Mango", "tabby", Trait.CLINGY)).view().treats == 5


def test_the_world_pays_out_for_a_finished_set():
    world = room(Cat("Mango", "tabby", Trait.CLINGY))
    world.apply([FocusCompleted(25), SetCompleted()])
    world.apply([BreakCompleted(Phase.LONG_BREAK)])
    assert world.wallet.treats == 5 + 5 + 5 + 1


# --- buying --------------------------------------------------------------------


def test_the_catalogue_has_a_price_for_everything():
    assert [item.id for item in CATALOGUE] == ["tuna", "catnip", "laser", "box", "perch", "hammock"]
    assert all(item.price > 0 for item in CATALOGUE)


def test_buying_spends_treats_and_toys_are_bought_once():
    wallet = Wallet(treats=60)
    assert wallet.buy("laser") is Purchase.BOUGHT
    assert (wallet.treats, wallet.owned) == (20, {"laser"})
    assert wallet.buy("laser") is Purchase.OWNED
    assert wallet.treats == 20


def test_tuna_can_be_bought_again_and_again():
    wallet = Wallet(treats=12)
    assert [wallet.buy("tuna"), wallet.buy("tuna"), wallet.buy("tuna")] == [
        Purchase.BOUGHT, Purchase.BOUGHT, Purchase.SHORT]
    assert (wallet.treats, wallet.tuna) == (2, 2)


def test_nothing_changes_hands_without_enough_treats():
    wallet = Wallet(treats=ITEMS["hammock"].price - 1)
    assert wallet.buy("hammock") is Purchase.SHORT
    assert wallet.owned == set() and wallet.treats == ITEMS["hammock"].price - 1


# --- tuna ----------------------------------------------------------------------


def test_tuna_lifts_any_cat_even_a_furious_one():
    cat = Cat("Tux", "tuxedo", Trait.DIVA, mood=5)
    cat.needs["hunger"] = 90
    cat.eat_tuna()
    assert (cat.mood, cat.needs["hunger"]) == (25, 0)


def test_a_shop_tool_needs_buying_first():
    world = room(Cat("Mango", "tabby", Trait.CLINGY))
    assert not world.has(Tool.TUNA) and not world.hold(Tool.TUNA)
    assert not world.has(Tool.LASER) and not world.hold(Tool.LASER)
    world.wallet.tuna = 1
    world.wallet.owned.add("laser")
    assert world.hold(Tool.TUNA)
    assert world.hold(Tool.LASER)


def test_tuna_works_during_a_focus():
    world = room(Cat("Mango", "tabby", Trait.CLINGY))
    world.wallet.tuna = 1
    world.set_mode(Mode.NAP)
    assert world.hold(Tool.TUNA)


def test_clicking_a_cat_with_tuna_feeds_it_and_uses_a_can():
    world = room(Cat("Mango", "tabby", Trait.CLINGY, mood=30))
    world.wallet.tuna = 2
    world.hold(Tool.TUNA)
    body = world.bodies["Mango"]
    world.click(body.x, body.y - 4)
    assert world.cats[0].mood == 50
    assert world.wallet.tuna == 1
    assert world.take_news() == [TunaEaten("Mango")]
    assert [e.kind for e in world.effects] == ["heart"]


def test_clicking_nothing_with_tuna_wastes_nothing():
    world = room(Cat("Mango", "tabby", Trait.CLINGY))
    world.wallet.tuna = 1
    world.hold(Tool.TUNA)
    world.click(2, 2)
    assert world.wallet.tuna == 1


def test_pressing_tuna_twice_feeds_the_unhappiest_cat_in_sight():
    world = room(Cat("Mango", "tabby", Trait.CLINGY, mood=50), Cat("Tux", "tuxedo", Trait.DIVA, mood=10),
                 Cat("Away", "grey", Trait.CHILL, mood=1))
    world.bodies["Away"].step = Step(Doing.AWAY, seconds=30)  # out through the litter door
    world.wallet.tuna = 1
    world.hold(Tool.TUNA)
    world.hold(Tool.TUNA)
    assert [c.mood for c in world.cats] == [50, 30, 1]
    assert world.cats[1].stage is Stage.PISSY


def test_the_last_can_puts_the_tool_down():
    world = room(Cat("Mango", "tabby", Trait.CLINGY))
    world.wallet.tuna = 1
    world.hold(Tool.TUNA)
    world.hold(Tool.TUNA)
    assert world.tool is None and world.wallet.tuna == 0
    assert not world.give_tuna()


def test_tuna_by_key_goes_to_the_cat_on_the_clock_first():
    world = room(Cat("Mango", "tabby", Trait.CLINGY, mood=12), Cat("Tux", "tuxedo", Trait.DIVA, mood=3))
    world.on_clock = "Mango"
    world.wallet.tuna = 1
    world.hold(Tool.TUNA)
    world.hold(Tool.TUNA)
    assert [c.mood for c in world.cats] == [32, 3]


def test_tuna_by_key_with_every_cat_out_of_sight_keeps_the_can_and_says_so():
    world = room(Cat("Mango", "tabby", Trait.CLINGY))
    world.bodies["Mango"].step = Step(Doing.AWAY, seconds=30)
    world.wallet.tuna = 1
    world.hold(Tool.TUNA)
    world.hold(Tool.TUNA)
    assert world.wallet.tuna == 1
    assert world.take_news() == [TunaEaten(None)]
