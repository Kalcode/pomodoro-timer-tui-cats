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
    """Kibble went into the bowl, unless it was full already. A knocked bowl is stood back up first."""

    already_full: bool = False
    was_knocked: bool = False


@dataclass(frozen=True)
class Petted:
    name: str
    how: str  # a cat.Petting value: purr, tolerate, hiss or swat


@dataclass(frozen=True)
class Played:
    """A cat finished a play session with a toy."""

    name: str
    toy: str


@dataclass(frozen=True)
class TunaEaten:
    name: str


@dataclass(frozen=True)
class StrayArrived:
    name: str


@dataclass(frozen=True)
class Adopted:
    name: str


@dataclass(frozen=True)
class Pooped:
    """An angry cat skipped the litter box and went on the floor (home stretch §5.1)."""

    name: str


@dataclass(frozen=True)
class KnockedBowl:
    """An angry cat knocked the bowl over (home stretch §5.2)."""

    name: str


@dataclass(frozen=True)
class ClockTaken:
    """A furious cat leapt across onto the clock (home stretch §5.3)."""

    name: str


@dataclass(frozen=True)
class ClockLeft:
    """The cat on the clock cheered up enough to give it back."""

    name: str


Event = (Transition | RuleBreak | FocusCompleted | BreakCompleted | SetCompleted | Fed | Petted | Played | TunaEaten
         | StrayArrived | Adopted | Pooped | KnockedBowl | ClockTaken | ClockLeft)
