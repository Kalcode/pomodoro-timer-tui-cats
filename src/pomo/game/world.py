"""The cat room over time: the cats, where they are, the bowl, and the mood of the moment (spec §3, §6).

Pure: `tick(dt)` moves time on, `apply(events)` feeds in the session's rule breaks and
rewards, the tool commands (`hold`, `point`, `click`, `leave`) are the player's hand
in the room, and `view()` describes what to draw. Randomness comes from an injected RNG.
Cats that go for a toy are `playing` it: they chase it, pounce, and after a session's
worth of time on its surface they've had their play (spec §3.4).
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from pomo.game import balance
from pomo.game.behavior import Body, Doing, Mode, Step, advance, choose, clamp, route, walkable
from pomo.game.cat import Cat, Petting, Stage
from pomo.game.events import Event, Fed, Petted, Played
from pomo.game.playscape import CAT_HEIGHT, CAT_WIDTH, MIN_HEIGHT, MIN_WIDTH, Box, Playscape, Surface, layout
from pomo.game.tools import Tool, locked
from pomo.game.toys import Ball, String
from pomo.timer import Phase

MAX_DT = 1.0  # a stalled tick (process suspended) never jumps the room forward more than this
UNINTERRUPTIBLE = {Doing.JUMP, Doing.AWAY, Doing.EAT}  # finished even when the phase changes
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


@dataclass
class Poop:
    x: float
    y: int  # the surface it's on


@dataclass
class Play:
    toy: str  # ball or string
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


@dataclass(frozen=True)
class RosterLine:
    name: str
    hearts: int
    stage: str


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
class RoomView:
    cats: tuple[CatView, ...] = ()
    roster: tuple[RosterLine, ...] = ()
    bowl_full: bool = True
    poops: tuple[tuple[float, int], ...] = ()
    effects: tuple[EffectView, ...] = ()
    cursor: CursorView | None = None
    ball: BallView | None = None
    string: StringView | None = None


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
        self.bodies: dict[str, Body] = {}
        self.litter_in: dict[str, float] = {}
        self.poops: list[Poop] = []
        self.effects: list[Effect] = []
        self.ball: Ball | None = None
        self.string: String | None = None
        self.playing: dict[str, Play] = {}
        self.tool: Tool | None = None
        self.pointer: tuple[float, float] | None = None  # room column and pixel row, while over the room
        self._petting: Cat | None = None  # the cat under the hand
        self._stroked = 0.0  # hand movement on that cat since the last stroke
        self._news: list[Event] = []
        for i, cat in enumerate(self.cats):
            x = clamp(FIRST_SPOT + i * SPACING, *walkable(self.scape.floor))
            self.bodies[cat.name] = Body("floor", x, float(self.scape.floor.y))
            self.litter_in[cat.name] = rng.uniform(*balance.LITTER_EVERY_S)

    # --- inputs ------------------------------------------------------------------

    def apply(self, events: Iterable[Event]) -> None:
        for event in events:
            for cat in self.cats:
                cat.apply(event)

    def set_mode(self, mode: Mode) -> None:
        """A new phase changes what cats feel like doing, so drop what they were about to do."""
        if mode is self.mode:
            return
        self.mode = mode
        if self.tool is not None and locked(self.tool, mode):
            self.hold(None)  # nap time: the toys go away
        self.playing.clear()
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
        for poop in self.poops:
            poop.x, poop.y = clamp(poop.x, 0, width - 1), self.scape.floor.y
        if self.ball is not None:
            self.ball.x = clamp(self.ball.x, balance.BALL_RADIUS, width - balance.BALL_RADIUS)
            self.ball.y, self.ball.vy = self.scape.floor.y, 0.0
        self.pointer, self.string = None, None  # until the mouse moves again

    def feed(self) -> None:
        """Kibble into the bowl."""
        self._news.append(Fed(already_full=self.bowl_full))
        self.bowl_full = True

    # --- the player's hand -------------------------------------------------------

    def hold(self, tool: Tool | None) -> bool:
        """Pick up a tool, or put it down with None. False if it's locked right now.
        Picking up Feed while holding it fills the bowl (spec §5.2: press 1 twice)."""
        if tool is not None and locked(tool, self.mode):
            return False
        if tool is Tool.FEED and self.tool is Tool.FEED:
            self.feed()
        self.tool = tool
        self._petting, self._stroked = None, 0.0
        self.string = None
        if tool is Tool.STRING and self.pointer is not None:
            self._dangle(*self.pointer)
        return True

    def point(self, x: float, y: float) -> None:
        """The pointer moved to column x, pixel row y of the room."""
        before, self.pointer = self.pointer, (x, y)
        if self.tool is Tool.PET:
            self._move_hand(before, x, y)
        elif self.tool is Tool.STRING:
            self._dangle(x, y)

    def click(self, x: float, y: float) -> None:
        self.point(x, y)
        if self.tool is Tool.FEED and _inside(self.scape.bowl, x, y):
            self.feed()
        elif self.tool is Tool.BALL:
            self._drop_ball(x, y)
        elif self.tool is Tool.SCOOP:
            self._scoop(x, y)

    def leave(self) -> None:
        """The pointer left the room."""
        self.pointer, self.string = None, None
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
            if body.step is not None and body.step.doing is Doing.AWAY:
                continue
            if abs(x - body.x) <= HIT_HALF_WIDTH and body.y - CAT_HEIGHT <= y < body.y:
                hits.append((body.y, body.x, cat))
        return max(hits, key=lambda h: (h[0], h[1]))[2] if hits else None

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
        for cat in self.cats:
            cat.tick(dt)
            body = self.bodies[cat.name]
            self.litter_in[cat.name] -= dt
            self._keep_playing(cat, body, dt)
            self._next_step(cat, body)
            finished = advance(body, self.scape, dt)
            if finished is not None:
                if finished.doing is Doing.EAT and self.bowl_full:
                    cat.eat()
                    self.bowl_full = False
                if finished.doing is Doing.JUMP and finished.hop is not None:
                    self._bat(cat, body)
                self._next_step(cat, body)  # straight on, so no frame is drawn between steps
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

    def _plan(self, cat: Cat, body: Body) -> list[Step]:
        if cat.name in self.playing:
            steps = self._play_steps(cat, body)
            if steps:
                return steps
            del self.playing[cat.name]  # the toy went out of reach
        litter_due = self.litter_in[cat.name] <= 0
        if litter_due:
            self.litter_in[cat.name] = self.rng.uniform(*balance.LITTER_EVERY_S)
        else:
            toy = "string" if self.string is not None else "ball" if self.ball is not None else None
            if toy is not None and self._tempted(cat, toy):
                self.playing[cat.name] = Play(toy, balance.PLAY_S)
                return self._play_steps(cat, body)
        return choose(cat, body, self.scape, self.mode, self.rng,
                      bowl_full=self.bowl_full, litter_due=litter_due)

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
        if self.playing[cat.name].toy == "ball":
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
        cats = []
        for cat in self.cats:
            body = self.bodies[cat.name]
            doing = body.step.doing if body.step else Doing.SIT
            if doing is Doing.AWAY:
                continue
            bubble = None if cat.name in self.playing else _bubble(cat, doing)
            cats.append(CatView(cat.name, cat.coat, _pose(doing, body), _face(cat, doing),
                                body.x, round(body.y), body.facing, bubble))
        roster = tuple(RosterLine(c.name, c.hearts, c.stage.value) for c in self.cats)
        effects = tuple(EffectView(e.kind, e.x, e.y - e.age * balance.EFFECT_RISE) for e in self.effects)
        cursor = None
        if self.tool is not None and self.pointer is not None:
            cursor = CursorView(self.tool.value, *self.pointer, busy=self._petting is not None)
        ball = string = None
        if self.ball is not None:
            ball = BallView(self.ball.x, round(self.ball.y), int(self.ball.rolled // 2) % 2)
        if self.string is not None:
            string = StringView(self.string.anchor, self.string.tip_x, self.string.tip_y)
        return RoomView(tuple(cats), roster, self.bowl_full, tuple((p.x, p.y) for p in self.poops),
                        effects, cursor, ball, string)


def _inside(box: Box, x: float, y: float) -> bool:
    return box.x <= x < box.x + box.w and box.y - SLACK <= y < box.y + box.h


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
    if doing is Doing.PURR and cat.stage is Stage.CONTENT:
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
