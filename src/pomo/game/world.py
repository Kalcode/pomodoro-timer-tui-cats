"""The cat room over time: the cats, where they are, the bowl, and the mood of the moment (spec §3, §6).

Pure: `tick(dt)` moves time on, `apply(events)` feeds in the session's rule breaks and
rewards, and `view()` describes what to draw. Randomness comes from an injected RNG.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from pomo.game import balance
from pomo.game.behavior import Body, Doing, Mode, Step, advance, choose, clamp, walkable
from pomo.game.cat import Cat, Stage
from pomo.game.events import BreakCompleted, Event
from pomo.game.playscape import MIN_HEIGHT, MIN_WIDTH, Playscape, layout
from pomo.timer import Phase

MAX_DT = 1.0  # a stalled tick (process suspended) never jumps the room forward more than this
UNINTERRUPTIBLE = {Doing.JUMP, Doing.AWAY, Doing.EAT}  # finished even when the phase changes
FIRST_SPOT = 38  # where the first cat sits when the room opens
SPACING = 22
BEG_OFFSET = 18  # a cat that finds the bowl taken sits this far to the side
BUBBLES = {"hunger": "🍗", "play": "🧶", "affection": "♥"}
STAGE_FACE = {Stage.CONTENT: "ok", Stage.GRUMPY: "meh", Stage.PISSY: "mad", Stage.FURIOUS: "mad"}


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


@dataclass(frozen=True)
class RosterLine:
    name: str
    hearts: int
    stage: str


@dataclass(frozen=True)
class RoomView:
    cats: tuple[CatView, ...] = ()
    roster: tuple[RosterLine, ...] = ()
    bowl_full: bool = True


def mode_for(phase: Phase, started: bool) -> Mode:
    """Focus under way → nap time; a break → play time; nothing started → relaxed."""
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
        self.bodies: dict[str, Body] = {}
        self.litter_in: dict[str, float] = {}
        for i, cat in enumerate(self.cats):
            x = clamp(FIRST_SPOT + i * SPACING, *walkable(self.scape.floor))
            self.bodies[cat.name] = Body("floor", x, float(self.scape.floor.y))
            self.litter_in[cat.name] = rng.uniform(*balance.LITTER_EVERY_S)

    # --- inputs ------------------------------------------------------------------

    def apply(self, events: Iterable[Event]) -> None:
        for event in events:
            for cat in self.cats:
                cat.apply(event)
            if isinstance(event, BreakCompleted):
                self.refill()  # stand-in until milestone 4's feed button: a break taken tops the bowl up

    def set_mode(self, mode: Mode) -> None:
        """A new phase changes what cats feel like doing, so drop what they were about to do."""
        if mode is self.mode:
            return
        self.mode = mode
        for body in self.bodies.values():
            if body.step is None or body.step.doing not in UNINTERRUPTIBLE:
                self._stop(body)

    def fit(self, width: int, height: int) -> None:
        """The terminal was resized: rebuild the room and put every cat back on its surface."""
        if (width, height) == (self.scape.width, self.scape.height):
            return
        self.scape = layout(width, height)
        for body in self.bodies.values():
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

    def refill(self) -> None:
        self.bowl_full = True

    # --- time --------------------------------------------------------------------

    def tick(self, dt: float) -> None:
        dt = min(max(dt, 0.0), MAX_DT)
        for cat in self.cats:
            cat.tick(dt)
            body = self.bodies[cat.name]
            self.litter_in[cat.name] -= dt
            if body.step is None:
                if not body.plan:
                    body.plan = self._plan(cat, body)
                body.step = body.plan.pop(0)
                if body.step.doing is Doing.EAT and not self._bowl_free(body):
                    # someone else got there first: sit beside them and beg
                    body.step = Step(Doing.WALK, x=clamp(body.x - BEG_OFFSET, *walkable(self.scape.floor)))
                    body.plan.insert(0, Step(Doing.BEG, seconds=balance.BEG_S))
            finished = advance(body, self.scape, dt)
            if finished is not None and finished.doing is Doing.EAT and self.bowl_full:
                cat.eat()
                self.bowl_full = False

    def _bowl_free(self, me: Body) -> bool:
        eating = any(b is not me and b.step is not None and b.step.doing is Doing.EAT for b in self.bodies.values())
        return self.bowl_full and not eating

    def _plan(self, cat: Cat, body: Body) -> list[Step]:
        litter_due = self.litter_in[cat.name] <= 0
        if litter_due:
            self.litter_in[cat.name] = self.rng.uniform(*balance.LITTER_EVERY_S)
        return choose(cat, body, self.scape, self.mode, self.rng,
                      bowl_full=self.bowl_full, litter_due=litter_due)

    @staticmethod
    def _stop(body: Body) -> None:
        body.step, body.plan, body.elapsed, body.launch = None, [], 0.0, None

    # --- output ------------------------------------------------------------------

    def view(self) -> RoomView:
        cats = []
        for cat in self.cats:
            body = self.bodies[cat.name]
            doing = body.step.doing if body.step else Doing.SIT
            if doing is Doing.AWAY:
                continue
            cats.append(CatView(cat.name, cat.coat, _pose(doing, body), _face(cat, doing),
                                body.x, round(body.y), body.facing, _bubble(cat, doing)))
        roster = tuple(RosterLine(c.name, c.hearts, c.stage.value) for c in self.cats)
        return RoomView(tuple(cats), roster, self.bowl_full)


def _pose(doing: Doing, body: Body) -> str:
    if doing in (Doing.WALK, Doing.ZOOM):
        return f"walk{int(body.walked // 3) % 2}"
    if doing is Doing.JUMP:
        return "leap"
    return "loaf" if doing in (Doing.LOAF, Doing.NAP, Doing.SULK) else "sit"


def _face(cat: Cat, doing: Doing) -> str:
    if doing is Doing.NAP:
        return "sleep"
    if doing is Doing.SULK:
        return "meh"
    return STAGE_FACE[cat.stage]


def _bubble(cat: Cat, doing: Doing) -> str | None:
    if doing is Doing.EAT:
        return "nom"
    if doing is Doing.BEG:
        return "meow"
    if doing is Doing.NAP:
        return None
    want = cat.wants()
    return BUBBLES[want] if want else None
