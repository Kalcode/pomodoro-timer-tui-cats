"""The care tools (spec §5.2) and when they're locked (spec §3.1)."""

from __future__ import annotations

from enum import Enum

from pomo.game.behavior import Mode


class Tool(Enum):
    FEED = "feed"
    BALL = "ball"
    STRING = "string"
    PET = "pet"
    SCOOP = "scoop"
    TUNA = "tuna"  # these three come from the shop
    CATNIP = "catnip"
    LASER = "laser"


WORKS_DURING_FOCUS = frozenset({Tool.SCOOP, Tool.TUNA})


def locked(tool: Tool, mode: Mode) -> bool:
    """A focus under way is nap time: every tool but the scoop and tuna waits for the break."""
    return mode is Mode.NAP and tool not in WORKS_DURING_FOCUS
