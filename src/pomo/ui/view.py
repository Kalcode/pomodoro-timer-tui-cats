"""Pure text for the timer screen. No Textual here, so it's trivial to test."""

from __future__ import annotations

import math
from collections.abc import Sequence

from pomo.game.balance import ADOPT_PRICE, NEED_ALERT, PENALTIES, SET_BONUS, TUNA_MOOD
from pomo.game.cat import NEEDS, Cat
from pomo.game.economy import ITEMS, Item, Kind, Purchase, Wallet, treats_for
from pomo.game.events import (
    Adopted, BreakCompleted, Event, Fed, FocusCompleted, Petted, Played, RuleBreak, RuleKind, SetCompleted,
    StrayArrived, TunaEaten,
)
from pomo.game.tools import Tool
from pomo.game.world import CursorView, Stray
from pomo.session import Action
from pomo.timer import Phase, PomodoroTimer, Transition

PHASE_NAMES = {Phase.FOCUS: "FOCUS", Phase.SHORT_BREAK: "SHORT BREAK", Phase.LONG_BREAK: "LONG BREAK"}
NEXT_NAMES = {Phase.FOCUS: "focus", Phase.SHORT_BREAK: "break", Phase.LONG_BREAK: "long break"}
RULE_TEXT = {
    RuleKind.ABANDON_FOCUS: "Focus abandoned.",
    RuleKind.SKIP_BREAK: "Break skipped.",
    RuleKind.LONG_PAUSE: "That pause ran long.",
}
MAX_DOTS = 8  # keeps the count line inside the 30-column panel
TOY_NAMES = {"ball": "yarn ball", "string": "string", "catnip": "catnip mouse", "laser": "laser dot"}
LOCKED = "Shh, the cats are napping. During a focus only the scoop and tuna work."
MISSING = {
    Tool.TUNA: "You're out of tuna. The shop ($) sells it.",
    Tool.CATNIP: "You don't have a catnip mouse yet. The shop ($) sells one.",
    Tool.LASER: "You don't have a laser pointer yet. The shop ($) sells one.",
}
TREATS = "🐟"
BOUGHT = {  # what to do with it now
    "tuna": "Press 6 for the tuna, then click a cat, or press 6 again for the unhappiest one.",
    "catnip": "Press 7 and click to drop it in the room.",
    "laser": "Press 8 and point at the room.",
    "box": "It's on the floor. Watch it fill up at nap time.",
    "perch": "It's under the window.",
    "hammock": "It's slung under the wall shelf.",
}
IDLE_ON = "Idle mode: no timer, and every tool works. Press i to go back."
IDLE_OFF = "Back to pomodoro. Press space to start."
WANTS = {"hunger": "{} is waiting by the bowl.", "play": "{} wants to play.", "affection": "{} could use some fuss."}


def clock_text(seconds: float) -> str:
    """MM:SS, rounded up so it reads 25:00 until a whole second has passed and 00:00 only at the end."""
    total = math.ceil(max(0.0, seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def phase_label(timer: PomodoroTimer) -> str:
    return f"● {PHASE_NAMES[timer.phase]}"


def phase_state(timer: PomodoroTimer, waiting: bool = False) -> str:
    """Shown under the phase name while the timer isn't running. waiting: a phase just ended and this one
    waits for you to start it."""
    if timer.running:
        return ""
    if waiting:
        return "break time: space to start" if timer.phase.is_break else "focus time: space to start"
    return "paused" if timer.started else "space to start"


def progress_bar(timer: PomodoroTimer, width: int) -> str:
    done = 1.0 - timer.remaining() / timer.length if timer.length else 1.0
    filled = round(min(1.0, max(0.0, done)) * width)
    return "█" * filled + "░" * (width - filled)


def count_line(timer: PomodoroTimer) -> str:
    total = timer.settings.long_every
    done = timer.focus_in_set
    dots = "●" * done + "○" * (total - done) if total <= MAX_DOTS else ""
    if timer.phase is Phase.FOCUS:
        return f"pomodoro {done + 1} of {total}  {dots}".rstrip()
    return f"{done} of {total} done  {dots}".rstrip()


def next_line(timer: PomodoroTimer) -> str:
    upcoming = timer.next_phase()
    minutes = timer.base_length(upcoming) / 60
    return f"next: {minutes:g} min {NEXT_NAMES[upcoming]}"


def earned(treats: int) -> str:
    return f" (+{treats} {TREATS})" if treats else ""


def describe(event: Event, waits: bool = False) -> str | None:
    """The message-line text for an event, if it deserves one. waits: phases wait for space between them."""
    match event:
        case Transition(completed=True, ended=Phase.FOCUS) as t:
            pay = earned(treats_for(FocusCompleted(round(t.ended_length_s / 60))))
            if waits:
                return f"Focus complete{pay}. Break time! Press space to start your break."
            return f"Focus complete{pay}. Time for a break!"
        case Transition(completed=True) as t:
            pay = earned(treats_for(BreakCompleted(t.ended)))
            if waits:
                return f"Break's over{pay}. Press space when you're ready to focus."
            return f"Break's over{pay}. Back to focus."
        case RuleBreak(kind=kind):
            return f"{RULE_TEXT[kind]} The cats will remember (−{PENALTIES[kind]})."
        case SetCompleted():
            after = "Press space to start your long break." if waits else "Enjoy your long break."
            return f"A full set with no rules broken: a {SET_BONUS} {TREATS} bonus! {after}"
        case TunaEaten(name=name):
            return f"{name} wolfs down the tuna (+{TUNA_MOOD})."
        case StrayArrived(name=name):
            return f"A stray called {name} is peering in at the window. Press a to adopt."
        case Adopted(name=name):
            return f"{name} comes in through the door. Welcome home, {name}!"
        case Fed(already_full=True):
            return "The bowl is already full."
        case Fed():
            return "Kibble's in the bowl."
        case Petted(name=name, how="hiss"):
            return f"{name} hisses at your hand. Not now."
        case Petted(name=name, how="swat"):
            return f"{name} swats your hand. That's enough petting."
        case Played(name=name, toy=toy):
            return f"{name} had a good play with the {TOY_NAMES[toy]}."
    return None


def cat_line(cats: Sequence[Cat], starting: Phase) -> str:
    """One line about the unhappiest cat, for the end of a ping (addendum §5)."""
    if not cats:
        return ""
    cat = min(cats, key=lambda c: c.mood)  # the first, on a tie
    if cat.stage.angry:
        return f"{cat.name} is still sulking."
    for need in NEEDS:  # food, then play, then affection
        if cat.needs[need] > NEED_ALERT:
            return WANTS[need].format(cat.name)
    return f"{cat.name} is stretching for playtime." if starting.is_break else f"{cat.name} is curling up for a nap."


def remembers(cats: Sequence[Cat]) -> str:
    """The message for a focus left without the quit dialog, charged on the next launch (spec §3.2)."""
    return f"{cats[0].name} remembers you left." if len(cats) == 1 else "The cats remember you left."


def confirm_question(timer: PomodoroTimer, action: Action, cost: RuleKind) -> str:
    question = {
        Action.SKIP: "Skip your break?" if timer.phase.is_break else "Skip this focus?",
        Action.RESET: "Restart this focus from the top?",
        Action.QUIT: "Quit in the middle of a focus?",
        Action.IDLE: "Switch to Idle in the middle of a focus?",
    }[action]
    return f"{question} The cats will be upset (−{PENALTIES[cost]})."


def pointer_shape(cursor: CursorView | None) -> str:
    """The terminal's own pointer (OSC 22, home stretch §8): a hand-ish pointer while a tool is over the room,
    grabbing while the hand is on a cat, and crosshairs for the laser. Terminals without OSC 22 ignore it."""
    if cursor is None:
        return "default"
    if cursor.tool == "pet" and cursor.busy:
        return "grab"
    return "crosshair" if cursor.tool == "laser" else "pointer"


def shop_line(key: int, item: Item, wallet: Wallet) -> str:
    """One line of the shop: key, icon, name, price (or owned) and what it does."""
    name = f"{item.name} ×{wallet.tuna}" if item.id == "tuna" and wallet.tuna else item.name
    owned = item.kind is not Kind.CONSUMABLE and item.id in wallet.owned
    price = "owned" if owned else f"{item.price:>2} {TREATS}"
    return f"{key}  {item.icon} {name:<16} {price:>6}  {item.blurb}"


def purchase(item_id: str, result: Purchase, wallet: Wallet) -> str:
    item = ITEMS[item_id]
    match result:
        case Purchase.OWNED:
            return f"You already have the {item.name.lower()}."
        case Purchase.SHORT:
            return f"The {item.name.lower()} is {item.price} {TREATS}: you need {item.price - wallet.treats} more."
    return f"Bought: {item.name.lower()}. {BOUGHT[item_id]}"


TRAIT_TEXT = {"chill": "chill", "diva": "a bit of a diva", "clingy": "clingy", "gremlin": "a little gremlin"}
NO_STRAY = "Nobody's at the window right now. Strays turn up as your focus sessions add up."


def adopt_question(stray: Stray) -> str:
    return f"Adopt {stray.name} for {ADOPT_PRICE} {TREATS}? A {stray.coat} cat, and {TRAIT_TEXT[stray.trait.value]}."


def adopt_short(stray: Stray, treats: int) -> str:
    return f"{stray.name} would love to come in. Adopting is {ADOPT_PRICE} {TREATS}: you need {ADOPT_PRICE - treats} more."
