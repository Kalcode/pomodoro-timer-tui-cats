"""Time sources. Anything that needs the time takes a Clock, so tests can control it."""

from __future__ import annotations

import time
from typing import Protocol


class Clock(Protocol):
    def now(self) -> float:
        """Monotonic seconds. Only differences between two readings mean anything."""
        ...


class RealClock:
    def now(self) -> float:
        return time.monotonic()


class WallClock:
    """Seconds since the epoch: comparable across runs, unlike the monotonic clock (for saves)."""

    def now(self) -> float:
        return time.time()


class FakeClock:
    """A clock that only moves when a test tells it to."""

    def __init__(self, start: float = 1000.0) -> None:
        self._now = start

    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("time only moves forward")
        self._now += seconds
