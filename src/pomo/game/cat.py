"""A cat's inner life: mood, needs and trait (spec §3.3–§3.5). Pure numbers; movement lives in behavior.py."""

from __future__ import annotations

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

    def _change_mood(self, delta: float) -> None:
        self.mood = min(float(balance.MOOD_MAX), max(0.0, self.mood + delta))
