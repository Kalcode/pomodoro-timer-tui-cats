"""A cat's inner life: mood, needs and trait (spec §3.3–§3.5). Pure numbers; movement lives in behavior.py."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum

from pomo.game import balance
from pomo.game.events import BreakCompleted, Event, FocusCompleted, RuleBreak

NEEDS = ("hunger", "play", "affection")


class Trait(Enum):
    CHILL = "chill"
    DIVA = "diva"
    CLINGY = "clingy"
    GREMLIN = "gremlin"


class Stage(Enum):
    CONTENT = "content"
    GRUMPY = "grumpy"
    PISSY = "pissy"
    FURIOUS = "furious"

    @property
    def angry(self) -> bool:
        return self in (Stage.PISSY, Stage.FURIOUS)


class Petting(Enum):
    """How a cat takes one stroke of the hand (spec §3.4)."""

    PURR = "purr"  # content: purrs and floats hearts
    TOLERATE = "tolerate"  # grumpy: puts up with it
    HISS = "hiss"  # pissy or furious: refuses
    SWAT = "swat"  # already had plenty


@dataclass
class Cat:
    name: str
    coat: str
    trait: Trait
    mood: float = balance.MOOD_START
    needs: dict[str, float] = field(default_factory=lambda: dict.fromkeys(NEEDS, 0.0))

    @property
    def stage(self) -> Stage:
        if self.mood >= balance.CONTENT_AT:
            return Stage.CONTENT
        if self.mood >= balance.GRUMPY_AT:
            return Stage.GRUMPY
        if self.mood >= balance.PISSY_AT:
            return Stage.PISSY
        return Stage.FURIOUS

    @property
    def hearts(self) -> int:
        """0–5, one per 20 mood."""
        return min(5, int(self.mood // 20))

    def wants(self) -> str | None:
        """The most urgent need above the alert level, if any."""
        need = max(NEEDS, key=lambda n: self.needs[n])
        return need if self.needs[need] > balance.NEED_ALERT else None

    def apply(self, event: Event) -> None:
        match event:
            case RuleBreak(kind=kind):
                factor = balance.TRAIT_PENALTY.get(self.trait.value, 1.0)
                self._change_mood(-balance.PENALTIES[kind] * factor)
            case FocusCompleted(minutes=minutes) if minutes >= balance.FOCUS_REWARD_MIN_MINUTES:
                self._change_mood(balance.FOCUS_REWARD)
            case BreakCompleted():
                self._change_mood(balance.BREAK_REWARD)

    def tick(self, dt: float) -> None:
        """Needs rise, unmet needs sour the mood (never past grumpy), and anger slowly cools."""
        for need in NEEDS:
            rate = 100 / balance.NEED_FULL_S[need]
            if need == "affection" and self.trait is Trait.CLINGY:
                rate *= balance.CLINGY_AFFECTION
            self.needs[need] = min(100.0, self.needs[need] + rate * dt)
        if self.wants() and self.mood > balance.NEED_FLOOR:
            self.mood = max(balance.NEED_FLOOR, self.mood - balance.NEED_DRAIN_PER_S * dt)
        if self.mood < balance.COOL_CEILING:
            self.mood = min(balance.COOL_CEILING, self.mood + balance.COOL_PER_S * dt)

    def eat(self) -> None:
        """A bowl of kibble: hunger gone, and a little cheer unless the cat is angry."""
        self.needs["hunger"] = 0.0
        if not self.stage.angry:
            self._change_mood(balance.EAT_MOOD)

    def pet(self, rng: random.Random) -> Petting:
        """One stroke of the hand."""
        if self.stage.angry:
            return Petting.HISS
        if self.needs["affection"] < balance.OVERPET_BELOW and rng.random() < balance.SWAT_CHANCE:
            self._change_mood(-balance.SWAT_MOOD)
            return Petting.SWAT
        met = self._meet("affection", balance.STROKE_RELIEF)
        self._change_mood(balance.STROKE_MOOD * met / balance.STROKE_RELIEF)
        return Petting.PURR if self.stage is Stage.CONTENT else Petting.TOLERATE

    def play(self) -> None:
        """A session with a toy: play met, and cheer for as much of it as was needed."""
        met = self._meet("play", balance.PLAY_RELIEF)
        if not self.stage.angry:
            self._change_mood(balance.PLAY_MOOD * met / balance.PLAY_RELIEF)

    def toy_interest(self) -> float:
        """The chance this cat goes for a toy it notices: keener the more it needs to play."""
        if self.stage.angry:
            return 0.0
        chance = min(1.0, balance.TOY_CURIOSITY + self.needs["play"] / 100)
        return chance * balance.GRUMPY_TOY_FACTOR if self.stage is Stage.GRUMPY else chance

    def _meet(self, need: str, relief: float) -> float:
        met = min(self.needs[need], relief)
        self.needs[need] -= met
        return met

    def _change_mood(self, delta: float) -> None:
        self.mood = min(float(balance.MOOD_MAX), max(0.0, self.mood + delta))
