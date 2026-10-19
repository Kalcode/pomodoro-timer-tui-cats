"""The cat room over time: the cats, where they are, the bowl, and the mood of the moment (spec §3, §6).

Pure: `tick(dt)` moves time on, `apply(events)` feeds in the session's rule breaks and
rewards, the tool commands (`hold`, `point`, `click`, `leave`) are the player's hand
in the room, and `view()` describes what to draw. Randomness comes from an injected RNG.
Cats that go for a toy are `playing` it: they chase it, pounce, and after a session's
worth of time on its surface they've had their play (spec §3.4). Angry cats leave
consequences: poop on the floor, a knocked-over bowl, and a furious cat on the clock
(home stretch §5).
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from pomo.game import balance
from pomo.game.behavior import Body, Doing, Mode, Step, advance, box_spot, choose, clamp, knock, route, walkable
from pomo.game.cat import COATS, Cat, Petting, Stage, Trait
from pomo.game.economy import ITEMS, Kind, Purchase, Wallet
from pomo.game.events import (
    Adopted, ClockLeft, ClockTaken, Event, Fed, FocusCompleted, KnockedBowl, Petted, Played, Pooped, StrayArrived,
    TunaEaten,
)
from pomo.game.playscape import (
    CAT_HEIGHT, CAT_WIDTH, CLOCK_PERCH, FURNITURE, MIN_HEIGHT, MIN_WIDTH, Box, Playscape, Surface, layout,
)
from pomo.game.tools import Tool, locked
from pomo.game.toys import Ball, String
from pomo.timer import Phase

MAX_DT = 1.0  # a stalled tick (process suspended) never jumps the room forward more than this
UNINTERRUPTIBLE = {Doing.JUMP, Doing.AWAY, Doing.EAT, Doing.POOP, Doing.KNOCK}  # finished even when the phase changes
FIRST_SPOT = 38  # where the first cat sits when the room opens
SPACING = 22
BEG_OFFSET = 18  # a cat that finds the bowl taken sits this far to the side
BUBBLES = {"hunger": "🍗", "play": "🧶", "affection": "♥"}
STAGE_FACE = {Stage.CONTENT: "ok", Stage.GRUMPY: "meh", Stage.PISSY: "mad", Stage.FURIOUS: "mad"}
HIT_HALF_WIDTH = CAT_WIDTH / 2 + 1  # a pointer this close to a cat's centre is on it
POOP_REACH = (4.0, 6)  # a scoop this many columns to either side, or pixels above, still gets it
SLACK = 2  # a text row is two pixels, so clicks on props get a row's grace
EFFECT_SIDE = 6  # hearts and hisses rise beside the head, clear of the bubble over it
STRING_REACH = CAT_HEIGHT + balance.POUNCE_HOP[1]  # a tip this far above a surface is in reach from it
UNDER_STRING = 3  # a cat this close under the tip pounces
STRING_MARGIN = CAT_WIDTH // 2  # a tip swinging just past a surface's end is still in reach from it
CLOCK_SPOT = (CLOCK_PERCH.x0 + CLOCK_PERCH.x1) / 2  # a cat on the clock sits over the middle of the digits


@dataclass
class Poop:
    x: float
    y: int  # the surface it's on


@dataclass(frozen=True)
class Stray:
    """A cat at the window, waiting to be adopted (home stretch §6)."""

    name: str
    coat: str
    trait: Trait


@dataclass
class Catnip:
    x: float  # it lies on the floor


@dataclass
class Laser:
    x: float
    surface: str  # the dot lands on whatever is under the pointer


@dataclass
class Play:
    toy: str  # ball, string, catnip or laser
    left: float  # seconds of play to go


@dataclass
class Effect:
    kind: str  # heart, hiss or swat
    x: float
    y: float
    age: float = 0.0


@dataclass(frozen=True)
class CatView:
    """One cat as the scene should draw it. x is the centre column, feet the pixel row under it."""

    name: str
    coat: str
    pose: str
    face: str
    x: float
    feet: int
    facing: int = 1
    bubble: str | None = None
    in_box: bool = False  # napping in the cardboard box: only the head shows over its front
    free: bool = False  # on the clock, or leaping to or from it: drawn over the timer panel, not cut at its edge


@dataclass(frozen=True)
class RosterLine:
    name: str
    hearts: int
    stage: str
    coat: str = "tabby"


@dataclass(frozen=True)
class EffectView:
    kind: str
    x: float
    y: float  # pixel row, already risen


@dataclass(frozen=True)
class CursorView:
    """The tool in hand, drawn at the pointer. busy: the hand is on a cat."""

    tool: str
    x: float
    y: float
    busy: bool = False


@dataclass(frozen=True)
class BallView:
    x: float
    y: int  # the pixel row under it
    frame: int  # 0 or 1: the yarn turns as it rolls


@dataclass(frozen=True)
class StringView:
    anchor: float  # the column it hangs from, at the top of the room
    tip_x: float
    tip_y: float


@dataclass(frozen=True)
class StrayView:
    name: str
    coat: str


@dataclass(frozen=True)
class RoomView:
    cats: tuple[CatView, ...] = ()
    roster: tuple[RosterLine, ...] = ()
    bowl_full: bool = True
    poops: tuple[tuple[float, int], ...] = ()
    effects: tuple[EffectView, ...] = ()
    cursor: CursorView | None = None
    ball: BallView | None = None
    string: StringView | None = None
    treats: int = 0
    stray: StrayView | None = None
    furniture: frozenset[str] = frozenset()
    catnip: float | None = None  # its column, on the floor
    laser: tuple[float, int] | None = None  # the dot: a column and the pixel row it's on
    bowl_knocked: bool = False
    clock_cat: str | None = None  # the cat sitting on the clock, if any: the time moves to the state line


def mode_for(phase: Phase, started: bool, idle: bool = False) -> Mode:
    """Idle, or nothing started → relaxed; focus under way → nap time; a break → play time."""
    if idle:
        return Mode.RELAX
    if phase.is_break:
        return Mode.PLAY
    return Mode.NAP if started else Mode.RELAX


class World:
    def __init__(self, cats: Sequence[Cat], rng: random.Random,
                 width: int = MIN_WIDTH, height: int = MIN_HEIGHT) -> None:
        self.cats = list(cats)
        self.rng = rng
        self.scape: Playscape = layout(width, height)
        self.mode = Mode.RELAX
        self.bowl_full = True
        self.bowl_knocked = False  # on its side, and so empty, until you feed (home stretch §5.2)
        self.focus_total = 0  # every focus ever completed: strays come by this (spec §4)
        self.wallet = Wallet()
        self.stray: Stray | None = None
        self.bodies: dict[str, Body] = {}
        self.litter_in: dict[str, float] = {}
        self.mischief_in: dict[str, float] = {}  # until each cat next feels like knocking the bowl over
        self.furious_for: dict[str, float] = {}  # how long each cat has been furious, without a break
        self.on_clock: str | None = None  # the cat on the clock, or on its way there (home stretch §5.3)
        self.poops: list[Poop] = []
        self.effects: list[Effect] = []
        self.ball: Ball | None = None
        self.string: String | None = None
        self.catnip: Catnip | None = None
        self.laser: Laser | None = None
        self.playing: dict[str, Play] = {}
        self.tool: Tool | None = None
        self.pointer: tuple[float, float] | None = None  # room column and pixel row, while over the room
        self._petting: Cat | None = None  # the cat under the hand
        self._stroked = 0.0  # hand movement on that cat since the last stroke
        self._news: list[Event] = []
        for i, cat in enumerate(self.cats):
            self._settle(cat, FIRST_SPOT + i * SPACING)

    def _settle(self, cat: Cat, x: float) -> None:
        """A cat's place in the room: standing on the floor at column x, with its own timers."""
        x = clamp(x, *walkable(self.scape.floor))
        self.bodies[cat.name] = Body("floor", x, float(self.scape.floor.y))
        self.litter_in[cat.name] = self.rng.uniform(*balance.LITTER_EVERY_S)
        self.mischief_in[cat.name] = self._mischief_roll(cat)

    # --- inputs ------------------------------------------------------------------

    def apply(self, events: Iterable[Event]) -> None:
        events = list(events)
        for event in events:
            for cat in self.cats:
                cat.apply(event)
            if isinstance(event, FocusCompleted):
                self.focus_total += 1
                self._stray_by()
        self.wallet.earn(events)

    def set_mode(self, mode: Mode) -> None:
        """A new phase changes what cats feel like doing, so drop what they were about to do."""
        if mode is self.mode:
            return
        self.mode = mode
        if self.tool is not None and locked(self.tool, mode):
            self.hold(None)  # nap time: the toys go away
        self.playing.clear()
        for name, body in self.bodies.items():
            if name == self.on_clock:
                continue  # it's making a point: a new phase won't move it (home stretch §5.3)
            if body.step is None or body.step.doing not in UNINTERRUPTIBLE:
                self._stop(body)

    @property
    def furniture(self) -> frozenset[str]:
        return frozenset(self.wallet.owned & set(FURNITURE))

    def fit(self, width: int, height: int) -> None:
        """The terminal was resized: rebuild the room and put every cat back on its surface."""
        if (width, height) == (self.scape.width, self.scape.height):
            return
        self.furnish(width, height)

    def furnish(self, width: int | None = None, height: int | None = None) -> None:
        """Lay the room out again, at a new size or with new furniture, and put every cat back on its surface."""
        width, height = width or self.scape.width, height or self.scape.height
        self.scape = layout(width, height, self.furniture)
        for name, body in self.bodies.items():
            if _clockbound(body):  # the panel doesn't change with the room: whatever the leap, it ends on the clock
                if body.step is not None and body.step.doing is Doing.JUMP:
                    if body.surface != CLOCK_PERCH.name:
                        self._news.append(ClockTaken(name))
                    body.surface, body.x, body.y = CLOCK_PERCH.name, CLOCK_SPOT, float(CLOCK_PERCH.y)
                    self._stop(body)
                continue
            if body.step is not None and body.step.doing is Doing.AWAY:
                # out of sight: it comes back through the new door, onto the new floor, and plans afresh
                door = self.scape.door
                body.surface, body.x, body.y = "floor", door.x + door.w / 2, float(self.scape.floor.y)
                body.plan = []
                continue
            if body.step is not None and body.step.doing is Doing.JUMP:
                body.surface = body.step.surface  # land it now
            surface = self.scape.surface(body.surface)
            body.x, body.y = clamp(body.x, *walkable(surface)), float(surface.y)
            self._stop(body)
        for poop in self.poops:
            poop.x, poop.y = clamp(poop.x, 0, width - 1), self.scape.floor.y
        if self.ball is not None:
            self.ball.x = clamp(self.ball.x, balance.BALL_RADIUS, width - balance.BALL_RADIUS)
            self.ball.y, self.ball.vy = self.scape.floor.y, 0.0
        if self.catnip is not None:
            self.catnip.x = clamp(self.catnip.x, 0, width - 1)
        self.pointer, self.string, self.laser = None, None, None  # until the mouse moves again

    def place(self, name: str, surface: str, x: float) -> None:
        """Put a cat back where a save left it, standing still. Never on the clock: it has to take that again.
        Furniture that isn't there puts it on the floor."""
        if self.on_clock == name:
            self.on_clock = None
        if surface == CLOCK_PERCH.name:
            surface, x = self.scape.tree_top.name, walkable(self.scape.tree_top)[0]
        elif surface not in {s.name for s in self.scape.surfaces}:
            surface = "floor"
        where = self.scape.surface(surface)
        body = self.bodies[name]
        body.surface, body.x, body.y = surface, clamp(x, *walkable(where)), float(where.y)
        self._stop(body)

    def feed(self) -> None:
        """Kibble into the bowl, standing it back up first if it was knocked over."""
        self._news.append(Fed(already_full=self.bowl_full, was_knocked=self.bowl_knocked))
        self.bowl_full, self.bowl_knocked = True, False

    @staticmethod
    def save_spot(body: Body) -> tuple[str, float]:
        """The surface and column a save puts this cat on. A save only knows the room, so a cat on the clock, or
        leaping to or from it, is saved on the tree top it leaps from (and climbs back if it's still furious)."""
        if _clockbound(body):
            top = layout(MIN_WIDTH, MIN_HEIGHT).tree_top  # the cat tree is the same in every size of room
            return top.name, walkable(top)[0]
        return body.surface, body.x

    # --- strays (home stretch §6) ------------------------------------------------

    def _stray_by(self) -> None:
        """After a focus, a stray may turn up at the window: one at a time, more as the focus sessions add up."""
        due = balance.STRAY_FIRST + balance.STRAY_EVERY * (len(self.cats) - 1)
        if self.stray is not None or len(self.cats) >= balance.MAX_CATS or self.focus_total < due:
            return
        taken = {c.name for c in self.cats}
        names = [n for n in balance.STRAY_NAMES if n not in taken] or [f"Stray {len(self.cats) + 1}"]
        worn = {c.coat for c in self.cats}
        coats = [c for c in COATS if c not in worn] or list(COATS)
        self.stray = Stray(self.rng.choice(names), self.rng.choice(coats), self.rng.choice(list(Trait)))
        self._news.append(StrayArrived(self.stray.name))

    def stray_at(self, x: float, y: float) -> bool:
        """Is the pointer on the stray in the window, and not on a cat sitting in front of it?"""
        return self.stray is not None and _inside(self.scape.window, x, y) and self._cat_at(x, y) is None

    def adopt(self) -> bool:
        """Take the stray in, if there's one and the treats to pay for it. It comes in through the litter door."""
        if self.stray is None or not self.wallet.spend(balance.ADOPT_PRICE):
            return False
        stray, self.stray = self.stray, None
        cat = Cat(stray.name, stray.coat, stray.trait)
        cat.needs["hunger"] = balance.STRAY_HUNGER
        self.cats.append(cat)
        door = self.scape.door
        self._settle(cat, door.x + door.w / 2)
        body = self.bodies[cat.name]
        body.x = door.x + door.w / 2  # in the doorway, wherever walkable() would have it
        body.facing = -1
        body.plan = [Step(Doing.WALK, x=clamp(body.x - SPACING, *walkable(self.scape.floor)))]
        self._news.append(Adopted(cat.name))
        return True

    # --- the shop ------------------------------------------------------------------

    def buy(self, item_id: str) -> Purchase:
        """Spend treats in the shop. Furniture goes straight into the room."""
        result = self.wallet.buy(item_id)
        if result is Purchase.BOUGHT and ITEMS[item_id].kind is Kind.FURNITURE:
            # furniture only adds places to be, so nobody has to stop what they're doing
            self.scape = layout(self.scape.width, self.scape.height, self.furniture)
        return result

    def give_tuna(self, cat: Cat | None = None) -> bool:
        """A can of tuna for this cat, or else the one on the clock, or else the unhappiest one in sight.
        False if there's no tuna or no cat."""
        if cat is None:
            here = [c for c in self.cats if not self._away(c)]
            on_clock = [c for c in here if c.name == self.on_clock]
            cat = (on_clock or sorted(here, key=lambda c: c.mood) or [None])[0]
        if cat is None or self.wallet.tuna <= 0:
            return False
        self.wallet.tuna -= 1
        cat.eat_tuna()
        body = self.bodies[cat.name]
        self.effects.append(Effect("heart", body.x + EFFECT_SIDE, body.y - CAT_HEIGHT))
        self._news.append(TunaEaten(cat.name))
        if self.wallet.tuna == 0 and self.tool is Tool.TUNA:
            self.hold(None)  # that was the last can
        return True

    # --- the player's hand -------------------------------------------------------

    def has(self, tool: Tool) -> bool:
        """The shop's tools need buying first, and tuna runs out."""
        if tool is Tool.TUNA:
            return self.wallet.tuna > 0
        if tool in (Tool.CATNIP, Tool.LASER):
            return tool.value in self.wallet.owned
        return True

    def hold(self, tool: Tool | None) -> bool:
        """Pick up a tool, or put it down with None. False if it's locked right now, or not yours yet.
        Picking up Feed while holding it fills the bowl (spec §5.2: press 1 twice), and tuna gives a can
        to the unhappiest cat the same way."""
        if tool is not None and (locked(tool, self.mode) or not self.has(tool)):
            return False
        if tool is Tool.TUNA and self.tool is Tool.TUNA:
            if not self.give_tuna():
                self._news.append(TunaEaten(None))  # every cat is out through the door
            return True
        if tool is Tool.FEED and self.tool is Tool.FEED:
            self.feed()
        self.tool = tool
        self._petting, self._stroked = None, 0.0
        self.string = self.laser = None
        if tool is Tool.STRING and self.pointer is not None:
            self._dangle(*self.pointer)
        if tool is Tool.LASER and self.pointer is not None:
            self._aim(*self.pointer)
        return True

    def point(self, x: float, y: float) -> None:
        """The pointer moved to column x, pixel row y of the room."""
        before, self.pointer = self.pointer, (x, y)
        if self.tool is Tool.PET:
            self._move_hand(before, x, y)
        elif self.tool is Tool.STRING:
            self._dangle(x, y)
        elif self.tool is Tool.LASER:
            self._aim(x, y)

    def click(self, x: float, y: float) -> None:
        self.point(x, y)
        if self.tool is Tool.FEED and _inside(self.scape.bowl, x, y):
            self.feed()
        elif self.tool is Tool.BALL:
            self._drop_ball(x, y)
        elif self.tool is Tool.CATNIP:
            self.catnip = Catnip(clamp(x, 0, self.scape.width - 1))  # one mouse: dropping it again moves it
            self._notice("catnip")
        elif self.tool is Tool.SCOOP:
            self._scoop(x, y)
        elif self.tool is Tool.TUNA:
            cat = self._cat_at(x, y)
            if cat is not None:
                self.give_tuna(cat)

    def leave(self) -> None:
        """The pointer left the room."""
        self.pointer, self.string, self.laser = None, None, None
        self._petting, self._stroked = None, 0.0

    def take_news(self) -> list[Event]:
        """What happened in the room since the last call, for the message line."""
        news, self._news = self._news, []
        return news

    def _move_hand(self, before: tuple[float, float] | None, x: float, y: float) -> None:
        cat = self._cat_at(x, y)
        if cat is None or cat is not self._petting or before is None:
            self._petting, self._stroked = cat, 0.0
            return
        self._stroked += abs(x - before[0]) + abs(y - before[1]) / 2  # in cells: a row is two pixels
        if self._stroked >= balance.STROKE_CELLS:
            self._stroked = 0.0
            self._stroke(cat)

    def _stroke(self, cat: Cat) -> None:
        how = cat.pet(self.rng)
        body = self.bodies[cat.name]
        x, head = body.x + EFFECT_SIDE, body.y - CAT_HEIGHT
        self.playing.pop(cat.name, None)  # the hand beats any toy
        if how in (Petting.PURR, Petting.TOLERATE):
            if body.step is None or body.step.doing not in UNINTERRUPTIBLE:
                self._stop(body)
                body.step = Step(Doing.PURR, seconds=balance.PURR_S)  # sits still for more
            if how is Petting.PURR:
                self.effects.append(Effect("heart", x, head))
        else:
            self.effects.append(Effect(how.value, x, head))
            if how is Petting.SWAT and (body.step is None or body.step.doing not in UNINTERRUPTIBLE):
                self._stop(body)  # and off it goes to do something else
        self._news.append(Petted(cat.name, how.value))

    def _cat_at(self, x: float, y: float) -> Cat | None:
        """The front-most visible cat under the pointer (the scene draws higher feet, then x, last)."""
        hits = []
        for cat in self.cats:
            body = self.bodies[cat.name]
            if self._away(cat):
                continue
            if abs(x - body.x) <= HIT_HALF_WIDTH and body.y - CAT_HEIGHT <= y < body.y:
                hits.append((body.y, body.x, cat))
        return max(hits, key=lambda h: (h[0], h[1]))[2] if hits else None

    def _away(self, cat: Cat) -> bool:
        """Out through the litter door, so out of sight and out of reach."""
        step = self.bodies[cat.name].step
        return step is not None and step.doing is Doing.AWAY

    def _drop_ball(self, x: float, y: float) -> None:
        """One ball at a time: dropping it again picks it up from wherever it was."""
        speed = self.rng.uniform(*balance.BALL_DROP_SPEED) * self.rng.choice((-1, 1))
        x = clamp(x, balance.BALL_RADIUS, self.scape.width - balance.BALL_RADIUS)
        self.ball = Ball(x, min(y, self.scape.floor.y), vx=speed)
        self._notice("ball")

    def _dangle(self, x: float, y: float) -> None:
        y = clamp(y, balance.STRING_TOP, self.scape.floor.y - 1)
        if self.string is None:
            self.string = String(x, x, y)
            self._notice("string")
        else:
            self.string.anchor, self.string.tip_y = x, y

    def _aim(self, x: float, y: float) -> None:
        """The laser dot lands on the first surface under the pointer, or the floor."""
        below = [s for s in self.scape.surfaces if s.x0 <= x < s.x1 and s.y >= y]
        surface = min(below, key=lambda s: s.y) if below else self.scape.floor
        first = self.laser is None
        self.laser = Laser(clamp(x, 0, self.scape.width - 1), surface.name)
        if first:
            self._notice("laser")

    def _scoop(self, x: float, y: float) -> bool:
        reach_x, reach_y = POOP_REACH
        near = [p for p in self.poops if abs(p.x - x) <= reach_x and p.y - reach_y <= y <= p.y + SLACK]
        if not near:
            return False
        self.poops.remove(min(near, key=lambda p: abs(p.x - x)))
        return True

    # --- time --------------------------------------------------------------------

    def tick(self, dt: float) -> None:
        dt = min(max(dt, 0.0), MAX_DT)
        if self.ball is not None:
            self.ball.tick(dt, self.scape.width, self.scape.floor.y)
        if self.string is not None:
            self.string.tick(dt)
            self.string.tip_x = clamp(self.string.tip_x, 0, self.scape.width - 1)  # it swings against the walls
        for cat in self.cats:
            cat.tick(dt)
            if self.poops:  # every poop sours the room, though never past pissy (home stretch §5.1)
                cat.sour(balance.POOP_DRAIN_PER_S * len(self.poops) * dt, balance.POOP_FLOOR)
            body = self.bodies[cat.name]
            self.litter_in[cat.name] -= dt
            if cat.name not in self.mischief_in:  # a cat that joined after the room opened
                self.mischief_in[cat.name] = self._mischief_roll(cat)
            self.mischief_in[cat.name] -= dt
            self._temper(cat, body, dt)
            self._keep_playing(cat, body, dt)
            self._next_step(cat, body)
            takeoff = body.surface
            finished = advance(body, self.scape, dt)
            if finished is not None:
                self._finish(cat, body, finished, takeoff)
                self._next_step(cat, body)  # straight on, so no frame is drawn between steps
        if self.tool is Tool.PET and self.pointer is not None:
            under = self._cat_at(*self.pointer)
            if under is not self._petting:  # the cat walked out from under a resting hand: it stops patting
                self._petting, self._stroked = under, 0.0
        for effect in self.effects:
            effect.age += dt
        self.effects = [e for e in self.effects if e.age < balance.EFFECT_S]

    def _next_step(self, cat: Cat, body: Body) -> None:
        if body.step is not None:
            return
        if not body.plan:
            body.plan = self._plan(cat, body)
        body.step = body.plan.pop(0)
        if body.step.doing is Doing.EAT and not self._bowl_free(body):
            # someone else got there first: sit beside them and beg
            body.step = Step(Doing.WALK, x=clamp(body.x - BEG_OFFSET, *walkable(self.scape.floor)))
            body.plan.insert(0, Step(Doing.BEG, seconds=balance.BEG_S))

    def _bowl_free(self, me: Body) -> bool:
        eating = any(b is not me and b.step is not None and b.step.doing is Doing.EAT for b in self.bodies.values())
        return self.bowl_full and not eating

    def _finish(self, cat: Cat, body: Body, step: Step, takeoff: str) -> None:
        """What a step leaves behind once it's done."""
        if step.doing is Doing.EAT and self.bowl_full:
            cat.eat()
            self.bowl_full = False
        elif step.doing is Doing.JUMP and step.hop is not None:
            self._bat(cat, body)
        elif step.doing is Doing.JUMP and step.surface == CLOCK_PERCH.name:
            self._news.append(ClockTaken(cat.name))
        elif step.doing is Doing.JUMP and takeoff == CLOCK_PERCH.name:
            if self.on_clock == cat.name:
                self.on_clock = None
            self._news.append(ClockLeft(cat.name))
        elif step.doing is Doing.POOP:
            self.poops.append(Poop(body.x, self.scape.floor.y))
            self._news.append(Pooped(cat.name))
        elif step.doing is Doing.KNOCK and not self.bowl_knocked:
            self.bowl_full, self.bowl_knocked = False, True
            self._news.append(KnockedBowl(cat.name))

    def _plan(self, cat: Cat, body: Body) -> list[Step]:
        if self.on_clock == cat.name:  # nothing else matters to it: not food, toys or the litter box
            return self._clock_steps(body)
        if body.surface == CLOCK_PERCH.name:  # on the clock with no reason to be: back into the room
            return [self._hop_down()]
        if cat.name in self.playing:
            steps = self._play_steps(cat, body)
            if steps:
                return steps
            del self.playing[cat.name]  # the toy went out of reach
        litter_due = self.litter_in[cat.name] <= 0
        if litter_due:
            self.litter_in[cat.name] = self.rng.uniform(*balance.LITTER_EVERY_S)
        elif self._mischief_due(cat):
            return knock(self.scape, body)
        else:
            # a ball lying still is only exciting when it lands: left alone, cats want you to play
            toy = ("laser" if self.laser is not None else "string" if self.string is not None
                   else "ball" if self.ball and self.ball.moving else None)
            if toy is not None and self._tempted(cat, toy):
                self.playing[cat.name] = Play(toy, balance.PLAY_S)
                return self._play_steps(cat, body)
        return choose(cat, body, self.scape, self.mode, self.rng,
                      bowl_full=self.bowl_full, litter_due=litter_due)

    # --- consequences (home stretch §5) -------------------------------------------

    def _mischief_roll(self, cat: Cat) -> float:
        every = self.rng.uniform(*balance.MISCHIEF_EVERY_S)
        return every * balance.GREMLIN_MISCHIEF if cat.trait is Trait.GREMLIN else every

    def _mischief_due(self, cat: Cat) -> bool:
        """Time to knock the bowl over: the timer has run out, the cat is angry and the bowl is standing.
        Once it has run out, the timer starts again whether or not the bowl goes over."""
        if self.mischief_in[cat.name] > 0:
            return False
        self.mischief_in[cat.name] = self._mischief_roll(cat)
        return cat.stage.angry and not self.bowl_knocked

    def _temper(self, cat: Cat, body: Body, dt: float) -> None:
        """A cat furious for long enough takes the clock, and gives it back once it has cheered up."""
        if cat.stage is Stage.FURIOUS:
            self.furious_for[cat.name] = self.furious_for.get(cat.name, 0.0) + dt
        else:
            self.furious_for[cat.name] = 0.0
        if self.on_clock == cat.name:
            if cat.mood >= balance.CLOCK_LEAVE_AT:
                self._give_clock_back(body)
            return
        wait = balance.GREMLIN_CLOCK_AFTER_S if cat.trait is Trait.GREMLIN else balance.CLOCK_AFTER_S
        busy = body.step is not None and body.step.doing in UNINTERRUPTIBLE
        if self.on_clock is None and self.furious_for[cat.name] >= wait and not busy:
            self.on_clock = cat.name  # one cat at a time: it's spoken for now
            self.playing.pop(cat.name, None)
            self._stop(body)  # and its next plan is the way up

    def _give_clock_back(self, body: Body) -> None:
        """Cheered up: down off the clock onto the tree top or, if it isn't there yet, it thinks better of it."""
        jumping = body.step is not None and body.step.doing is Doing.JUMP
        if jumping and _clockbound(body):
            return  # leaping onto the clock or off it: it lands first
        if body.surface == CLOCK_PERCH.name:
            self._stop(body)
            body.step = self._hop_down()
            return
        self.on_clock = None
        if jumping:
            body.plan = []  # it lands where it was hopping to, and finds something else to do
        else:
            self._stop(body)

    def _clock_steps(self, body: Body) -> list[Step]:
        """Up to the left end of the cat tree's top and a leap across the divider. Once there, it glares."""
        if body.surface == CLOCK_PERCH.name:
            return [Step(Doing.GLARE, seconds=balance.GLARE_S)]
        top = self.scape.tree_top
        return [*route(self.scape, body, top.name, walkable(top)[0]),
                Step(Doing.JUMP, x=CLOCK_SPOT, surface=CLOCK_PERCH.name)]

    def _hop_down(self) -> Step:
        top = self.scape.tree_top
        return Step(Doing.JUMP, x=walkable(top)[0], surface=top.name)

    # --- toys --------------------------------------------------------------------

    def _notice(self, toy: str) -> None:
        """A toy just appeared: cats that fancy it drop what they're doing."""
        for cat in self.cats:
            body = self.bodies[cat.name]
            busy = body.step is not None and body.step.doing in UNINTERRUPTIBLE | {Doing.PURR}
            if cat.name not in self.playing and not busy and self._tempted(cat, toy):
                self._stop(body)
                self.playing[cat.name] = Play(toy, balance.PLAY_S)

    def _tempted(self, cat: Cat, toy: str) -> bool:
        if self.mode is Mode.NAP or cat.needs["hunger"] > balance.NEED_ALERT:
            return False
        if toy == "string" and self._string_surface() is None:
            return False
        if toy == "laser" and self.laser is None:
            return False
        return self.rng.random() < cat.toy_interest()

    def _string_surface(self) -> Surface | None:
        """The surface right under the string's tip, if the tip is in reach from it."""
        s = self.string
        if s is None:
            return None
        under = [f for f in self.scape.surfaces
                 if f.x0 - STRING_MARGIN <= s.tip_x < f.x1 + STRING_MARGIN and 0 <= f.y - s.tip_y <= STRING_REACH]
        return min(under, key=lambda f: f.y) if under else None

    def _toy_at(self, play: Play) -> tuple[Surface, float, float] | None:
        """Where a cat plays with this toy: the surface, the column, and how close is close enough to pounce."""
        if play.toy == "ball":
            if self.ball is None:
                return None
            return self.scape.floor, self.ball.x, balance.BAT_REACH
        if play.toy == "catnip":
            return None if self.catnip is None else (self.scape.floor, self.catnip.x, balance.CATNIP_REACH)
        if play.toy == "laser":
            if self.laser is None:
                return None
            return self.scape.surface(self.laser.surface), self.laser.x, balance.LASER_REACH
        surface = self._string_surface()
        if surface is None:
            return None
        return surface, self.string.tip_x, UNDER_STRING

    def _play_steps(self, cat: Cat, body: Body) -> list[Step]:
        at = self._toy_at(self.playing[cat.name])
        if at is None:
            return []
        surface, x, reach = at
        if body.surface != surface.name:
            return route(self.scape, body, surface.name, x)
        x = clamp(x, *walkable(surface))
        if abs(x - body.x) > reach:
            return [Step(Doing.ZOOM, x=x)]
        toy = self.playing[cat.name].toy
        if toy == "catnip":
            return [Step(Doing.ROLL, seconds=balance.ROLL_S)]
        if toy in ("ball", "laser"):
            hop = balance.POUNCE_HOP[0]
        else:  # high enough for the cat's head to reach the tip
            hop = clamp(surface.y - CAT_HEIGHT - self.string.tip_y + 2, *balance.POUNCE_HOP)
        return [Step(Doing.JUMP, x=x, surface=surface.name, hop=hop),
                Step(Doing.SIT, seconds=self.rng.uniform(*balance.POUNCE_SIT_S))]

    def _keep_playing(self, cat: Cat, body: Body, dt: float) -> None:
        """Count play time on the toy's surface, follow the toy, and give up if it's gone."""
        play = self.playing.get(cat.name)
        if play is None:
            return
        at = self._toy_at(play)
        chasing = body.step is not None and body.step.doing is Doing.ZOOM
        if at is None or cat.stage.angry:
            del self.playing[cat.name]
            if chasing:
                self._stop(body)
            return
        surface, x, reach = at
        if body.surface != surface.name:
            return
        play.left -= dt
        if play.left <= 0:
            del self.playing[cat.name]
            if play.toy == "catnip":
                cat.play(balance.CATNIP_RELIEF, balance.CATNIP_MOOD)
            else:
                cat.play()
            self._news.append(Played(cat.name, play.toy))
        elif chasing:
            x = clamp(x, *walkable(surface))
            if abs(x - body.x) <= reach:
                self._stop(body)  # close enough: pounce
            else:
                body.step.x = x  # it moved: after it

    def _bat(self, cat: Cat, body: Body) -> None:
        """A pounce on the ball sends it flying the way the cat is facing."""
        play, ball = self.playing.get(cat.name), self.ball
        if play is None or play.toy != "ball" or ball is None:
            return
        if abs(ball.x - body.x) <= balance.BAT_REACH and ball.y >= self.scape.floor.y - SLACK * 2:
            ball.vx = body.facing * self.rng.uniform(*balance.BAT_SPEED)
            ball.vy = -self.rng.uniform(*balance.BAT_LIFT)

    @staticmethod
    def _stop(body: Body) -> None:
        body.step, body.plan, body.elapsed, body.launch = None, [], 0.0, None

    # --- output ------------------------------------------------------------------

    def view(self) -> RoomView:
        cats, clock_cat = [], None
        for cat in self.cats:
            body = self.bodies[cat.name]
            doing = body.step.doing if body.step else Doing.SIT
            if doing is Doing.AWAY:
                continue
            free = _clockbound(body)
            bubble = None if free or cat.name in self.playing else _bubble(cat, doing)
            in_box = (doing is Doing.NAP and self.scape.box is not None and body.surface == "floor"
                      and abs(body.x - box_spot(self.scape)) < 1)
            cats.append(CatView(cat.name, cat.coat, _pose(doing, body), _face(cat, doing),
                                body.x, round(body.y), body.facing, bubble, in_box=in_box, free=free))
            if body.surface == CLOCK_PERCH.name:
                clock_cat = cat.name
        roster = tuple(RosterLine(c.name, c.hearts, c.stage.value, c.coat) for c in self.cats)
        effects = tuple(EffectView(e.kind, e.x, e.y - e.age * balance.EFFECT_RISE) for e in self.effects)
        cursor = None
        if self.tool is not None and self.pointer is not None:
            cursor = CursorView(self.tool.value, *self.pointer, busy=self._petting is not None)
        ball = string = None
        if self.ball is not None:
            ball = BallView(self.ball.x, round(self.ball.y), int(self.ball.rolled // 2) % 2)
        if self.string is not None:
            string = StringView(self.string.anchor, self.string.tip_x, self.string.tip_y)
        stray = StrayView(self.stray.name, self.stray.coat) if self.stray else None
        catnip = self.catnip.x if self.catnip else None
        laser = (self.laser.x, self.scape.surface(self.laser.surface).y) if self.laser else None
        return RoomView(tuple(cats), roster, self.bowl_full, tuple((p.x, p.y) for p in self.poops),
                        effects, cursor, ball, string, treats=self.wallet.treats, stray=stray,
                        furniture=self.furniture, catnip=catnip, laser=laser, bowl_knocked=self.bowl_knocked,
                        clock_cat=clock_cat)


def _inside(box: Box, x: float, y: float) -> bool:
    return box.x <= x < box.x + box.w and box.y - SLACK <= y < box.y + box.h


def _clockbound(body: Body) -> bool:
    """On the clock, or leaping onto or off it."""
    step = body.step
    leaping_on = step is not None and step.doing is Doing.JUMP and step.surface == CLOCK_PERCH.name
    return body.surface == CLOCK_PERCH.name or leaping_on


def _pose(doing: Doing, body: Body) -> str:
    if doing in (Doing.WALK, Doing.ZOOM):
        return f"walk{int(body.walked // 3) % 2}"
    if doing is Doing.ROLL:
        return f"roll{int(body.elapsed // balance.ROLL_FRAME_S) % 2}"
    if doing is Doing.JUMP:
        return "leap"
    return "loaf" if doing in (Doing.LOAF, Doing.NAP, Doing.SULK, Doing.GLARE) else "sit"


def _face(cat: Cat, doing: Doing) -> str:
    if doing is Doing.NAP:
        return "sleep"
    if doing is Doing.SULK:
        return "meh"
    if doing is Doing.GLARE:
        return "mad"
    if doing in (Doing.PURR, Doing.ROLL) and cat.stage is Stage.CONTENT:
        return "blink"  # eyes shut, enjoying it
    return STAGE_FACE[cat.stage]


def _bubble(cat: Cat, doing: Doing) -> str | None:
    if doing is Doing.EAT:
        return "nom"
    if doing is Doing.BEG:
        return "meow"
    if doing is Doing.PURR:
        return "prr" if cat.stage is Stage.CONTENT else None
    if doing is Doing.NAP:
        return None
    want = cat.wants()
    return BUBBLES[want] if want else None
