"""How cats get around the room and what they choose to do next (spec §3.1, §3.7, §6).

Pure: playscape geometry, a cat's mood and needs, and a seeded random.Random in;
plans of steps and positions out. A cat's position is its centre column `x` and the
pixel row its feet are on `y`, in room coordinates.
"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

from pomo.game import balance
from pomo.game.cat import Cat, Stage
from pomo.game.playscape import Playscape, Surface, can_jump

HALF_WIDTH = 9  # a cat's centre stays this far inside a surface's ends


class Mode(Enum):
    NAP = "nap"  # a focus is under way: nap time
    PLAY = "play"  # a break: play time
    RELAX = "relax"  # nothing running


class Doing(Enum):
    SIT = "sit"
    LOAF = "loaf"
    NAP = "nap"
    SULK = "sulk"
    WALK = "walk"
    ZOOM = "zoom"
    JUMP = "jump"
    EAT = "eat"
    BEG = "beg"
    AWAY = "away"  # out through the litter door


MOVING = {Doing.WALK, Doing.ZOOM}


@dataclass
class Step:
    doing: Doing
    seconds: float = 0.0  # how long, for everything but moves and jumps
    x: float = 0.0  # WALK/ZOOM: where to; JUMP: where to land
    surface: str = ""  # JUMP: what to land on


@dataclass
class Body:
    surface: str
    x: float
    y: float
    facing: int = 1  # 1 right, -1 left
    step: Step | None = None
    plan: list[Step] = field(default_factory=list)
    elapsed: float = 0.0  # time spent in the current step
    walked: float = 0.0  # total distance covered, which drives the walk cycle
    launch: tuple[float, float] | None = None  # where the current jump took off


def walkable(surface: Surface) -> tuple[float, float]:
    """The range a cat's centre can take on this surface (a single spot if it's narrow)."""
    lo, hi = surface.x0 + HALF_WIDTH, surface.x1 - HALF_WIDTH
    if lo > hi:
        mid = (surface.x0 + surface.x1) / 2
        return mid, mid
    return lo, hi


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def path(scape: Playscape, start: str, goal: str) -> list[str]:
    """Surfaces to hop through to get from start to goal, fewest hops first (goal included)."""
    parent: dict[str, str | None] = {start: None}
    queue = deque([start])
    while queue:
        here = queue.popleft()
        if here == goal:
            break
        for there in scape.surfaces:
            if there.name not in parent and can_jump(scape.surface(here), there):
                parent[there.name] = here
                queue.append(there.name)
    if goal not in parent:
        raise ValueError(f"no way from {start} to {goal}")
    hops = []
    node: str | None = goal
    while node != start:
        hops.append(node)
        node = parent[node]
    return hops[::-1]


def route(scape: Playscape, body: Body, goal: str, x: float) -> list[Step]:
    """Walk and jump from where the body is to x on the goal surface."""
    steps: list[Step] = []
    here, at = scape.surface(body.surface), body.x
    for name in path(scape, body.surface, goal):
        there = scape.surface(name)
        takeoff = clamp(clamp(at, *walkable(there)), *walkable(here))  # the edge nearest the next surface
        landing = clamp(takeoff, *walkable(there))
        steps += [Step(Doing.WALK, x=takeoff), Step(Doing.JUMP, x=landing, surface=name)]
        here, at = there, landing
    steps.append(Step(Doing.WALK, x=clamp(x, *walkable(here))))
    return steps


def jump_seconds(x0: float, y0: float, x1: float, y1: float) -> float:
    return balance.JUMP_BASE_S + balance.JUMP_PER_PX_S * math.hypot(x1 - x0, y1 - y0)


def advance(body: Body, scape: Playscape, dt: float) -> Step | None:
    """Move time forward for the current step. Returns the step if it just finished."""
    step = body.step
    if step is None:
        return None
    body.elapsed += dt
    if step.doing in MOVING:
        speed = balance.ZOOM_SPEED if step.doing is Doing.ZOOM else balance.WALK_SPEED
        gap = step.x - body.x
        if gap:
            body.facing = 1 if gap > 0 else -1
            moved = min(abs(gap), speed * dt)
            body.x += moved * body.facing
            body.walked += moved
        done = abs(step.x - body.x) < 1e-9
    elif step.doing is Doing.JUMP:
        if body.launch is None:
            body.launch = (body.x, body.y)
            if step.x != body.x:
                body.facing = 1 if step.x > body.x else -1
        x0, y0 = body.launch
        y1 = scape.surface(step.surface).y
        p = min(1.0, body.elapsed / jump_seconds(x0, y0, step.x, y1))
        body.x = x0 + (step.x - x0) * p
        hop = balance.JUMP_ARC_PX + abs(y1 - y0) / 2  # rise above the higher end, then drop onto it
        body.y = y0 + (y1 - y0) * p - hop * 4 * p * (1 - p)
        done = p >= 1.0
        if done:
            body.surface, body.x, body.y, body.launch = step.surface, step.x, float(y1), None
    else:
        done = body.elapsed >= step.seconds
    if done:
        body.step, body.elapsed = None, 0.0
        return step
    return None


def choose(
    cat: Cat,
    body: Body,
    scape: Playscape,
    mode: Mode,
    rng: random.Random,
    *,
    bowl_full: bool,
    litter_due: bool,
) -> list[Step]:
    """What the cat does next: the litter box and hunger first, then something that suits the mode and mood."""
    if litter_due:
        door = scape.door.x + scape.door.w / 2
        back = walkable(scape.floor)[1] - rng.uniform(5, 20)
        return [*route(scape, body, "floor", door), Step(Doing.WALK, x=door),
                Step(Doing.AWAY, seconds=rng.uniform(*balance.AWAY_S)), Step(Doing.WALK, x=back)]
    if cat.wants() == "hunger":
        meal = Step(Doing.EAT, seconds=balance.EAT_S) if bowl_full else Step(Doing.BEG, seconds=balance.BEG_S)
        return [*route(scape, body, "floor", scape.bowl.x - 6), meal]
    return _activity(pick(cat.stage, mode, rng), body, scape, rng)


def pick(stage: Stage, mode: Mode, rng: random.Random) -> str:
    weights = dict(balance.ACTIVITY_WEIGHTS[mode.value])
    sulky = ("zoom",) if stage is Stage.GRUMPY else ("zoom", "sit", "loaf") if stage.angry else ()
    for name in sulky:
        weights["sulk"] = weights.get("sulk", 0) + weights.pop(name, 0)
    names = list(weights)
    return rng.choices(names, [weights[n] for n in names])[0]


def _activity(name: str, body: Body, scape: Playscape, rng: random.Random) -> list[Step]:
    here = scape.surface(body.surface)
    if name == "nap":
        spots = list(balance.NAP_SPOTS)
        spot = rng.choices(spots, [balance.NAP_SPOTS[s] for s in spots])[0]
        x = rng.uniform(*walkable(scape.surface(spot)))
        return [*route(scape, body, spot, x), Step(Doing.NAP, seconds=rng.uniform(*balance.NAP_S))]
    if name == "wander":
        lo, hi = walkable(here)
        if hi - lo < 4:
            return [Step(Doing.SIT, seconds=rng.uniform(*balance.SIT_S))]
        return [Step(Doing.WALK, x=rng.uniform(lo, hi))]
    if name == "climb":
        others = [s for s in scape.surfaces if s.name != here.name]
        there = rng.choice(others)
        return [*route(scape, body, there.name, rng.uniform(*walkable(there))),
                Step(Doing.SIT, seconds=rng.uniform(*balance.SIT_S))]
    if name == "zoom":
        lo, hi = walkable(scape.floor)
        steps = route(scape, body, "floor", body.x)
        for leg in range(rng.randint(*balance.ZOOM_LEGS)):
            steps.append(Step(Doing.ZOOM, x=hi - rng.uniform(0, 10) if leg % 2 == 0 else lo + rng.uniform(0, 10)))
        return steps
    seconds = {"sit": balance.SIT_S, "loaf": balance.LOAF_S, "sulk": balance.SULK_S}[name]
    return [Step(Doing(name), seconds=rng.uniform(*seconds))]
