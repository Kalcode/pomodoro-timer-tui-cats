"""The yarn ball and the string (spec §5.2): a little physics and no cats.

Room coordinates, like the cats: x is a column, y a pixel row. A ball's y is the row
under it, as a cat's feet are. Both move in small fixed steps, so a long tick can't
make them tunnel through the floor or swing wildly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from pomo.game import balance


def _steps(dt: float) -> tuple[int, float]:
    n = max(1, math.ceil(dt / balance.PHYSICS_STEP_S))
    return n, dt / n


@dataclass
class Ball:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    rolled: float = 0.0  # how far it has rolled, which turns the yarn

    @property
    def moving(self) -> bool:
        return self.vx != 0.0 or self.vy != 0.0

    def tick(self, dt: float, width: float, floor: float) -> None:
        n, h = _steps(dt)
        for _ in range(n):
            self._step(h, width, floor)

    def _step(self, h: float, width: float, floor: float) -> None:
        self.vy += balance.BALL_GRAVITY * h
        self.x += self.vx * h
        self.y += self.vy * h
        self.rolled += abs(self.vx * h)
        lo, hi = balance.BALL_RADIUS, width - balance.BALL_RADIUS
        if self.x < lo:
            self.x, self.vx = lo, abs(self.vx) * balance.BALL_WALL_BOUNCE
        elif self.x > hi:
            self.x, self.vx = hi, -abs(self.vx) * balance.BALL_WALL_BOUNCE
        if self.y >= floor:
            self.y = floor
            self.vy = -self.vy * balance.BALL_BOUNCE if self.vy > balance.BALL_SETTLE else 0.0
        if self.y == floor and self.vy == 0.0:  # rolling along the floor
            slow = balance.BALL_FRICTION * h
            self.vx = 0.0 if abs(self.vx) <= slow else self.vx - math.copysign(slow, self.vx)


@dataclass
class String:
    """Hangs from the ceiling at `anchor` (the mouse's column). Its tip lags behind and swings."""

    anchor: float
    tip_x: float
    tip_y: float
    vx: float = 0.0

    def tick(self, dt: float) -> None:
        n, h = _steps(dt)
        for _ in range(n):
            pull = balance.STRING_SPRING * (self.anchor - self.tip_x) - balance.STRING_DAMPING * self.vx
            self.vx += pull * h
            self.tip_x += self.vx * h
