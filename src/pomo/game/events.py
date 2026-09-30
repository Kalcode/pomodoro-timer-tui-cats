"""What the session tells the rest of the game (spec §3.2, §4), and what the room tells the player."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pomo.timer import Phase, Transition


class RuleKind(Enum):
    ABANDON_FOCUS = "abandon_focus"
    SKIP_BREAK = "skip_break"
    LONG_PAUSE = "long_pause"


@dataclass(frozen=True)
class RuleBreak:
    kind: RuleKind


@dataclass(frozen=True)
class FocusCompleted:
    minutes: int  # length at completion, including +/- adjustments


@dataclass(frozen=True)
class BreakCompleted:
    phase: Phase


@dataclass(frozen=True)
class SetCompleted:
    """A full set of focus sessions finished with no rule broken along the way."""


@dataclass(frozen=True)
class Fed:
    """Kibble went into the bowl, unless it was full already."""

    already_full: bool = False


@dataclass(frozen=True)
class Petted:
    name: str
    how: str  # a cat.Petting value: purr, tolerate, hiss or swat


@dataclass(frozen=True)
class Played:
    """A cat finished a play session with a toy."""

    name: str
    toy: str


Event = Transition | RuleBreak | FocusCompleted | BreakCompleted | SetCompleted | Fed | Petted | Played
