# pomo Milestone 4: Care and Idle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let you look after the cats, and let you hang out with them without a timer:
- **The toolbar:** a row of buttons under the message line (`1 🍗 Feed`, `2 🧶 Ball`, `3 🧵 String`, `4 ✋ Pet`, `5 🧹 Scoop`, and `🍅 Pomodoro`/`💤 Idle`). Keys `1`–`5` pick a tool and `esc` puts it down.
- **The tools, driven by the mouse:**
  - **Feed:** click the bowl, or press `1` twice, to fill it. This replaces milestone 3's refill-on-break stand-in.
  - **Ball:** drops a yarn ball with real bounce and roll.
  - **String:** dangles a swinging string from the pointer.
  - **Pet:** a hand that strokes cats.
  - **Scoop:** cleans up a poop.
- **Cats respond:**
  - They chase and bat the ball and pounce at the string.
  - Content cats purr and float hearts when petted. Angry cats hiss. Too much petting earns a swat.
  - Every care action meets a need, as in spec §3.4.
- **Focus is nap time:** while a focus is under way every tool but the scoop is locked (🔒).
- **Idle mode (`i`, `--idle`):** puts the timer away and unlocks everything. Going idle mid-focus asks first and costs what abandoning the focus costs.

**Architecture:**
- **Two new pure modules under `game/`:**
  - `tools.py`: the `Tool` enum and when each tool is locked.
  - `toys.py`: ball and string physics in fixed small steps.
- **`world.py` grows the player's hand:**
  - `hold(tool)`, `point(x, y)`, `click(x, y)`, `leave()` and `take_news()`.
  - Poops, floating effects, the ball, the string, and which cats are `playing` with a toy.
  - Everything stays in room coordinates and is fully testable without Textual.
- **`cat.py` gains the care rules:** `pet(rng) → Petting`, `play()` and `toy_interest()`.
- **`session.py` gains Idle:** `enter_idle()` is a reset plus a flag that puts the timer away, and `leave_idle()` clears it.
- **Rendering:**
  - Sprites gain the new props and tool cursors (each with a hotspot).
  - The scene draws poops, the ball, the string, the tool at the pointer and the effects, plus an Idle panel.
  - `scene.room_point` maps a pointer on screen into the room.
- **The app:**
  - A `Toolbar` widget of compact, never-focused buttons.
  - The `Stage` posts `Pointer`, `Pressed` and `Left` messages.
  - The app turns keys, clicks and mouse moves into world commands and shows what happened on the message line.

**Tech Stack:** Python ≥ 3.12, Textual 8.2 (compact `Button`s; mouse events with `pointer_x`/`pointer_y`), pytest and pytest-asyncio. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-29-pomo-cats-design.md`:
- §2 and §3.1: Idle mode, and the tools locked during focus.
- §3.2: going Idle mid-focus is abandoning it.
- §3.3–§3.4: care, refusals and over-petting.
- §5.1: keys. §5.2: mouse tools. §6: the toolbar. §7: draw order and props.
- §13: milestone 4.

This is **milestone 4 of 6**. It builds on milestone 3, which is on `main` (351 tests).

## Global Constraints

- **Everything from the milestone 1–3 plans still holds:**
  - A pure core with an injected `Clock` and `random.Random`.
  - `game/*` imports neither Textual nor `pomo.render`.
  - The topic is never logged.
  - Colours live only in `theme.py`.
  - The panel is exactly 30 columns.
  - 8 fps with row-diff repaints.
  - `dt` is capped at 1 s.
- **Care numbers are spec §3.4:**
  - A stroke meets 25 affection for +2 mood.
  - A ~10 s play session meets 50 play for +5 mood.
  - Petting a cat whose affection is under 10 has a 30% chance per stroke of a swat, which costs −2.
  - Pissy and furious cats refuse toys and petting, and hiss.
  - Grumpy cats sometimes ignore toys (half the time).
  - At most +8 mood per petting session.
- **Care pays mood in proportion to the need it meets.** A cat at affection 10 gets +0.8 from a stroke, and one at 0 gets nothing. This makes the +8 cap hold by construction (100 affection is 4 strokes, so +8). It also means care can never be farmed to undo a rule break.
- **Locks:**
  - Every tool but Scoop is locked while a focus is under way, running or paused (the cats' NAP mode).
  - A ready, unstarted focus, any break and Idle mode unlock everything.
  - Starting a focus puts a locked tool down.
- **Idle mode:**
  - Going idle resets the current phase: −25 mid-focus, asked first; free otherwise.
  - It then puts the timer away: `space`, `s`, `r` and `+`/`-` do nothing.
  - Leaving Idle gives back that same phase, ready to start. Idle during a break is therefore a free reset of the break, not a free skip.
  - Cats are in RELAX mode while idle. No transitions happen, so there are no pings and no keep-awake.
- **A stroke is 6 cells of hand movement inside one cat's box.** A pixel row counts as half a cell, and the move that lands on the cat doesn't count.
- **The toolbar is one row high**, so a 100×30 terminal gives the stage 28 rows (a 70×56 room, still ≥ `MIN_HEIGHT` 54).
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

**Design decisions this plan makes where the spec is silent:**
- **Toy interest:** a cat notices a toy with a chance of 30% plus its play need, capped at 1. Grumpy cats have half that chance. Hungry cats (over 70) and a due litter trip come first. Toys are ignored in NAP mode.
- **The ball** always falls to the floor. It bounces off the room's walls, and only one is out at a time: clicking again re-drops it.
- **The string:**
  - It hangs from the top of the room above the pointer, and its tip swings on a damped spring.
  - Cats go for it from the surface just under the tip, when the tip is at most 30 px above that surface (a cat's height plus the highest pounce). A tip 8 columns past a surface's end still counts.
- **Play time:** it counts only while the cat is on the toy's surface.
- **Play ends early, with nothing earned,** if:
  - the toy goes away (the string put down, or the mouse leaving the room),
  - a focus starts,
  - the cat turns angry,
  - or you pet it.
- **Petting** makes a content or grumpy cat sit still (`Doing.PURR`) for 3 s after each stroke. Content cats shut their eyes, show `prr` and float a ♥. A swat sends the cat off to do something else.
- **Effects** (♥, `#@!`, `swat!`) rise 6 px/s for 1.5 s, starting beside the head so they never collide with the bubble over it.
- **Scoop:** it works on `World.poops`. Nothing adds a poop until milestone 5, so the tool is tested with poops placed directly.
- **Pointer precision:** cursor positions and hit-tests work to a column. They work to a pixel row when the terminal reports the pointer finer than a cell (Textual's `pointer_y`); otherwise to a cell row.
- **The gallery wraps its props onto a second row and needs 100×46.**
- **Shutdown:** the 8 fps tick returns early once the app has stopped running. This fixes a race inherited from milestone 3: the interval could fire while Textual tears the screen down, and a quit then rarely ended in a `NoMatches` traceback.

**Not in this milestone:**
- Tuna, catnip, the laser, the `$` shop and treats (milestone 5).
- Cats pooping on the floor, the knocked-over bowl and sitting on the clock (milestone 5).
- Cats claiming spots so they don't pile up (milestone 5). Only Mango exists until strays arrive.
- OSC 22 pointer shapes, the too-small screen and saving (milestone 6).

## Review Focus

1. **The mouse leaves the room with a tool in hand** (over the panel, the message line, the toolbar, or out of the window). The tool sprite and the string disappear, and a half-finished stroke doesn't count. Tests:
   - Task 3 `test_leaving_the_room_lifts_the_hand`.
   - Task 4 `test_the_string_hangs_where_the_pointer_is_and_goes_with_it`.
   - Task 7 `test_the_tool_follows_the_mouse_over_the_room_and_hides_over_the_panel`.
2. **A focus starts mid-play.** The toy tool is put down, play ends with nothing earned, and the ball stays where it is. Tests:
   - Task 3 `test_a_focus_starting_puts_the_toys_away_but_not_the_scoop`.
   - Task 4 `test_a_focus_starting_ends_play_and_leaves_the_ball_where_it_is`.
   - Task 7 `test_starting_a_focus_puts_the_toy_down`.
3. **A stalled tick or a resize with toys out.** The ball never leaves the room or sinks through the floor, the string never flies off, and a resize rests the ball on the new floor. Tests:
   - Task 4 `test_a_long_tick_cannot_throw_the_ball_out_of_the_room`.
   - Task 4 `test_a_long_tick_cannot_make_the_string_fly_off`.
   - Task 4 `test_resizing_rests_the_ball_on_the_new_floor_and_takes_the_string_down`.
4. **An hour with toys constantly out.** Nobody freezes or leaves their surface, and play sessions keep completing. Test: Task 4 `test_an_hour_of_toys_never_gets_anyone_stuck` (2 cats, a new toy every 10 s, mode changes and feeding).
5. **Keys and clicks while a confirm dialog is up, and quitting mid-tick.** Tool keys and `i` are ignored while a dialog is open, and quitting never ends in a traceback. Tests:
   - Task 7 `test_tool_keys_are_ignored_while_a_dialog_is_open`.
   - Task 7 `test_a_tick_that_fires_during_shutdown_does_nothing`.

## File Map

| File | Responsibility | Task |
|---|---|---|
| `src/pomo/game/balance.py` (append) | Care numbers (T1, T3), toy physics and play numbers (T4) | 1, 3, 4 |
| `src/pomo/game/cat.py` (replace) | `Petting`; `Cat.pet`, `Cat.play`, `Cat.toy_interest` | 1 |
| `src/pomo/session.py` (replace) | `Action.IDLE`; `Session.idle`, `enter_idle`, `leave_idle`; the timer put away while idle | 2 |
| `src/pomo/ui/view.py` (edit, then replace) | The Idle confirm question (T2); messages for care events, the lock, and Idle (T7) | 2, 7 |
| `src/pomo/game/tools.py` | `Tool`, `WORKS_DURING_FOCUS`, `locked(tool, mode)` | 3 |
| `src/pomo/game/events.py` (replace) | `Fed`, `Petted`, `Played` | 3 |
| `src/pomo/game/behavior.py` (edits) | `Doing.PURR` (T3); `Step.hop` for pounces (T4) | 3, 4 |
| `src/pomo/game/world.py` (replace twice) | The hand: tools, feed, scoop, strokes, effects, news (T3); the ball, the string, cats playing (T4) | 3, 4 |
| `src/pomo/game/toys.py` | `Ball`, `String`: physics in small fixed steps | 4 |
| `src/pomo/render/sprites.py` (edit) | Poop, yarn, feather, hand, kibble scoop, scooper; `CURSORS` with hotspots | 5 |
| `src/pomo/gallery.py` (replace) | Props wrap onto a second row; needs 100×46 | 5 |
| `src/pomo/render/theme.py` (append) | `IDLE`, `STRING`, `EFFECT_COLORS` | 6 |
| `src/pomo/render/scene.py` (replace) | Draws poops, ball, string, the tool, effects; the Idle panel; `room_point` | 6 |
| `src/pomo/ui/toolbar.py` | `Toolbar`, `ToolButton`, `TOOLS` | 7 |
| `src/pomo/ui/stage.py` (replace) | `Pointer`, `Pressed`, `Left` messages | 7 |
| `src/pomo/ui/app.py` (replace) | Toolbar, keys `1`–`5`/`esc`/`i`, mouse → world, Idle with confirm, the shutdown guard | 7 |
| `src/pomo/cli.py` (replace) | `--idle`; keys in `--help` | 7 |
| `README.md` (replace) | Care tools and Idle | 7 |

---

### Task 1: The cat's care rules

**Files:**
- Modify: `src/pomo/game/balance.py` (append)
- Replace: `src/pomo/game/cat.py`
- Test: `tests/test_cat.py` (one import, and new tests at the end)

**Interfaces:**
- Consumes: milestone 3's `Cat`, `Stage` (`.angry`), `balance`.
- Produces:
  - Balance: `STROKE_RELIEF=25`, `STROKE_MOOD=2`, `OVERPET_BELOW=10`, `SWAT_CHANCE=0.3`, `SWAT_MOOD=2`, `PLAY_RELIEF=50`, `PLAY_MOOD=5`, `TOY_CURIOSITY=0.3`, `GRUMPY_TOY_FACTOR=0.5`.
  - `Petting` enum: `PURR`, `TOLERATE`, `HISS`, `SWAT`. Values are `"purr"`, `"tolerate"`, `"hiss"` and `"swat"`.
  - `Cat.pet(rng: random.Random) -> Petting`: one stroke.
  - `Cat.play() -> None`: one finished play session.
  - `Cat.toy_interest() -> float`: the chance, from 0 to 1, of going for a toy.

- [ ] **Step 1: Write the failing tests**

In `tests/test_cat.py`, change the import:

Replace:

```python
from pomo.game.cat import Cat, Stage, Trait
```

with:

```python
from pomo.game.cat import Cat, Petting, Stage, Trait
```

Then append to the end of `tests/test_cat.py`:

```python
class FixedRandom:
    """Stands in for random.Random: every roll comes out the same."""

    def __init__(self, value: float):
        self.value = value

    def random(self) -> float:
        return self.value


NO_SWAT, SWAT = FixedRandom(0.99), FixedRandom(0.1)


def test_a_stroke_meets_affection_and_a_content_cat_purrs():
    c = cat()
    c.needs["affection"] = 60.0
    assert c.pet(NO_SWAT) is Petting.PURR
    assert (c.needs["affection"], c.mood) == (35, 82)


def test_a_stroke_pays_only_for_the_affection_it_meets():
    c = cat()
    c.needs["affection"] = 10.0
    c.pet(NO_SWAT)
    assert c.needs["affection"] == 0
    assert c.mood == pytest.approx(80.8)


def test_a_petting_session_tops_out_at_8_mood():
    c = cat()
    c.needs["affection"] = 100.0
    for _ in range(10):
        c.pet(NO_SWAT)
    assert c.mood == 88


def test_petting_a_satisfied_cat_can_earn_a_swat():
    c = cat()
    c.needs["affection"] = 5.0
    assert c.pet(SWAT) is Petting.SWAT
    assert (c.needs["affection"], c.mood) == (5, 78)


def test_a_satisfied_cat_that_doesnt_swat_still_purrs():
    c = cat()
    c.needs["affection"] = 5.0
    assert c.pet(NO_SWAT) is Petting.PURR
    assert c.needs["affection"] == 0


def test_only_a_satisfied_cat_swats():
    c = cat()
    c.needs["affection"] = 10.0
    assert c.pet(SWAT) is Petting.PURR


def test_a_grumpy_cat_tolerates_petting():
    c = cat(mood=50.0)
    c.needs["affection"] = 50.0
    assert c.pet(NO_SWAT) is Petting.TOLERATE
    assert (c.needs["affection"], c.mood) == (25, 52)


@pytest.mark.parametrize("mood", [30.0, 10.0])
def test_pissy_and_furious_cats_hiss_and_nothing_changes(mood):
    c = cat(mood=mood)
    c.needs["affection"] = 90.0
    assert c.pet(NO_SWAT) is Petting.HISS
    assert (c.needs["affection"], c.mood) == (90, mood)


def test_playing_meets_play_and_cheers_the_cat_up():
    c = cat()
    c.needs["play"] = 80.0
    c.play()
    assert (c.needs["play"], c.mood) == (30, 85)


def test_playing_pays_only_for_the_play_it_meets():
    c = cat()
    c.needs["play"] = 10.0
    c.play()
    assert (c.needs["play"], c.mood) == (0, 81)


def test_an_angry_cat_made_to_play_gets_no_cheer():
    c = cat(mood=30.0)
    c.needs["play"] = 80.0
    c.play()
    assert (c.needs["play"], c.mood) == (30, 30)


@pytest.mark.parametrize("mood, play, interest", [
    (80.0, 0.0, 0.3), (80.0, 50.0, 0.8), (80.0, 90.0, 1.0),
    (50.0, 50.0, 0.4), (30.0, 90.0, 0.0), (10.0, 90.0, 0.0),
])
def test_how_likely_a_cat_is_to_go_for_a_toy(mood, play, interest):
    c = cat(mood=mood)
    c.needs["play"] = play
    assert c.toy_interest() == pytest.approx(interest)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_cat.py -v`
Expected: FAIL during collection with `ImportError: cannot import name 'Petting' from 'pomo.game.cat'`

- [ ] **Step 3: Add the care numbers**

Append to the end of `src/pomo/game/balance.py`, after a blank line:

```python
# --- care (spec §3.4, §5.2) -------------------------------------------------
# Care pays mood in proportion to the need it meets, so a cat with nothing left
# to meet gives nothing more. That caps a petting session at +8 by construction,
# and keeps care from being farmed to undo a rule break.
STROKE_RELIEF = 25  # affection met by one stroke of the hand...
STROKE_MOOD = 2  # ...and the mood it brings when it meets all of that
OVERPET_BELOW = 10  # petting a cat whose affection is this low risks a swat
SWAT_CHANCE = 0.3
SWAT_MOOD = 2  # lost to a swat
PLAY_RELIEF = 50  # play met by one session with a toy...
PLAY_MOOD = 5  # ...and the mood it brings when it meets all of that
TOY_CURIOSITY = 0.3  # even a cat that has just played sometimes goes for a toy
GRUMPY_TOY_FACTOR = 0.5  # grumpy cats ignore toys half the time
```

- [ ] **Step 4: Implement the care rules**

Replace all of `src/pomo/game/cat.py` with:

```python
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
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -q`
Expected: `369 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/game/balance.py src/pomo/game/cat.py tests/test_cat.py
git commit -m "feat: petting, play and toy interest on the cat, paid in proportion to the need met" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Idle mode in the session

**Files:**
- Replace: `src/pomo/session.py`
- Modify: `src/pomo/ui/view.py` (one line in `confirm_question`)
- Test: `tests/test_session.py`, `tests/test_view.py` (new tests at the end)

**Interfaces:**
- Consumes: milestone 1's `Session`, `Action`, `PomodoroTimer.reset()`, `timer.started`.
- Produces:
  - `Action.IDLE`. `Session.rule_cost(Action.IDLE)` works like a reset: `ABANDON_FOCUS` once a focus has started, otherwise `None`.
  - `Session.idle: bool`.
  - `Session.enter_idle() -> list[Event]`: resets the phase, and returns the rule break if there is one.
  - `Session.leave_idle() -> None`.
  - While idle: `toggle()` and `adjust()` do nothing, and `skip()` and `reset()` return `[]`.
  - `view.confirm_question(timer, Action.IDLE, cost)` → `"Switch to Idle in the middle of a focus? The cats will be upset (−25)."`

- [ ] **Step 1: Write the failing tests**

Append to the end of `tests/test_session.py`:

```python
def test_idle_costs_what_a_reset_costs(session, clock):
    assert session.rule_cost(Action.IDLE) is None  # focus not started
    session.toggle()
    assert session.rule_cost(Action.IDLE) is RuleKind.ABANDON_FOCUS
    clock.advance(1)
    session.toggle()  # paused is still mid-focus
    assert session.rule_cost(Action.IDLE) is RuleKind.ABANDON_FOCUS
    session.toggle()
    finish(session, clock)
    assert session.rule_cost(Action.IDLE) is None  # a break


def test_going_idle_mid_focus_abandons_it(session, clock):
    session.toggle()
    clock.advance(5 * MIN)
    assert session.enter_idle() == [RuleBreak(RuleKind.ABANDON_FOCUS)]
    assert session.idle
    assert (session.timer.phase, session.timer.started, session.timer.remaining()) == (Phase.FOCUS, False, 25 * MIN)


def test_going_idle_before_starting_is_free(session):
    assert session.enter_idle() == []
    assert session.idle


def test_going_idle_on_a_break_is_free_and_the_break_waits(session, clock):
    finish(session, clock)
    clock.advance(2 * MIN)
    assert session.enter_idle() == []
    session.leave_idle()
    assert not session.idle
    assert (session.timer.phase, session.timer.started, session.timer.remaining()) == (
        Phase.SHORT_BREAK, False, 5 * MIN)


def test_the_timer_is_put_away_while_idle(session, clock):
    session.enter_idle()
    session.toggle()
    session.adjust(5)
    assert session.skip() == []
    assert session.reset() == []
    clock.advance(30 * MIN)
    assert session.tick() == []
    assert (session.timer.phase, session.timer.started, session.timer.remaining()) == (Phase.FOCUS, False, 25 * MIN)


def test_after_idle_the_timer_works_again(session, clock):
    session.enter_idle()
    session.leave_idle()
    session.toggle()
    clock.advance(MIN)
    session.tick()
    assert session.timer.remaining() == 24 * MIN


def test_going_idle_twice_changes_nothing(session, clock):
    session.toggle()
    session.enter_idle()
    assert session.enter_idle() == []


def test_going_idle_mid_focus_loses_the_set_bonus(session, clock):
    session.toggle()
    session.enter_idle()
    session.leave_idle()
    events = []
    for _ in range(7):
        events += finish(session, clock)
    assert session.timer.phase is Phase.LONG_BREAK
    assert SetCompleted() not in events
```

Append to the end of `tests/test_view.py`:

```python
def test_confirm_question_for_going_idle(timer):
    timer.start()
    assert view.confirm_question(timer, Action.IDLE, RuleKind.ABANDON_FOCUS) == (
        "Switch to Idle in the middle of a focus? The cats will be upset (−25)."
    )
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_session.py tests/test_view.py -q`
Expected: `9 failed, 34 passed`. The failures are `AttributeError: type object 'Action' has no attribute 'IDLE'` and `'Session' object has no attribute 'enter_idle'`.

- [ ] **Step 3: Implement Idle in the session**

Replace all of `src/pomo/session.py` with:

```python
"""The timer plus the rules: user actions in, events out (spec §3.1–§3.2).

Idle mode (spec §2, §3.1) lives here too: going idle resets the phase, which costs
what a reset costs, and puts the timer away until you come back to it.
"""

from __future__ import annotations

from enum import Enum

from pomo.clock import Clock
from pomo.game import balance
from pomo.game.events import BreakCompleted, Event, FocusCompleted, RuleBreak, RuleKind, SetCompleted
from pomo.timer import Phase, PomodoroTimer, TimerSettings, Transition


class Action(Enum):
    """User actions that can break a rule, and so may need confirming first."""

    SKIP = "skip"
    RESET = "reset"
    QUIT = "quit"
    IDLE = "idle"


class Session:
    def __init__(
        self,
        settings: TimerSettings,
        clock: Clock,
        pause_allowance_s: float = balance.PAUSE_ALLOWANCE_S,
    ) -> None:
        self.timer = PomodoroTimer(settings, clock)
        self._clock = clock
        self._allowance = pause_allowance_s
        self._paused_total = 0.0
        self._paused_since: float | None = None
        self._pause_charged = False
        self._set_clean = True
        self.idle = False

    def rule_cost(self, action: Action) -> RuleKind | None:
        """Which rule this action would break right now, if any."""
        if self.timer.phase is Phase.FOCUS:
            if action is Action.SKIP or self.timer.started:
                return RuleKind.ABANDON_FOCUS
            return None
        return RuleKind.SKIP_BREAK if action is Action.SKIP else None

    def toggle(self) -> None:
        if self.idle:
            return
        now = self._clock.now()
        if self.timer.running:
            self.timer.pause()
            if self.timer.phase is Phase.FOCUS:
                self._paused_since = now
        else:
            if self._paused_since is not None:
                self._paused_total += now - self._paused_since
                self._paused_since = None
            self.timer.start()

    def adjust(self, minutes: int) -> None:
        if not self.idle:
            self.timer.adjust(minutes)

    def tick(self) -> list[Event]:
        events: list[Event] = []
        for transition in self.timer.tick():
            events += self._on_transition(transition)
        return events + self._check_pause()

    def skip(self) -> list[Event]:
        if self.idle:
            return []
        events = self._break_rule(self.rule_cost(Action.SKIP))
        return events + self._on_transition(self.timer.skip())

    def reset(self) -> list[Event]:
        if self.idle:
            return []
        events = self._break_rule(self.rule_cost(Action.RESET))
        self.timer.reset()
        self._reset_pause_tracking()
        return events

    def quit(self) -> list[Event]:
        return self._break_rule(self.rule_cost(Action.QUIT))

    def enter_idle(self) -> list[Event]:
        """Reset the phase and put the timer away. Mid-focus, that's abandoning it."""
        events = self.reset()
        self.idle = True
        return events

    def leave_idle(self) -> None:
        """Back to pomodoro: the phase that was reset waits, ready to start."""
        self.idle = False

    def _on_transition(self, transition: Transition) -> list[Event]:
        events: list[Event] = [transition]
        if transition.completed:
            if transition.ended is Phase.FOCUS:
                events.append(FocusCompleted(minutes=round(transition.ended_length_s / 60)))
                if transition.started is Phase.LONG_BREAK and self._set_clean:
                    events.append(SetCompleted())
            else:
                events.append(BreakCompleted(transition.ended))
        if transition.ended is Phase.LONG_BREAK:
            self._set_clean = True  # a new set starts
        self._reset_pause_tracking()
        return events

    def _check_pause(self) -> list[Event]:
        if self._pause_charged or self._paused_since is None:
            return []
        paused = self._paused_total + (self._clock.now() - self._paused_since)
        if paused <= self._allowance:
            return []
        self._pause_charged = True
        return self._break_rule(RuleKind.LONG_PAUSE)

    def _break_rule(self, kind: RuleKind | None) -> list[Event]:
        if kind is None:
            return []
        self._set_clean = False
        return [RuleBreak(kind)]

    def _reset_pause_tracking(self) -> None:
        self._paused_total = 0.0
        self._paused_since = None
        self._pause_charged = False
```

- [ ] **Step 4: Ask before going idle mid-focus**

In `src/pomo/ui/view.py`, in `confirm_question`:

Replace:

```python
        Action.QUIT: "Quit in the middle of a focus?",
```

with:

```python
        Action.QUIT: "Quit in the middle of a focus?",
        Action.IDLE: "Switch to Idle in the middle of a focus?",
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -q`
Expected: `378 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/session.py src/pomo/ui/view.py tests/test_session.py tests/test_view.py
git commit -m "feat: Idle mode in the session: going idle resets the phase and puts the timer away" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: The tools, the bowl, the scoop and the petting hand

**Files:**
- Create: `src/pomo/game/tools.py`
- Replace: `src/pomo/game/events.py`
- Replace: `src/pomo/game/world.py` (this version has no toys; Task 4 replaces it again)
- Modify: `src/pomo/game/behavior.py` (`Doing.PURR`)
- Modify: `src/pomo/game/balance.py` (append)
- Test: create `tests/test_care.py`, and modify `tests/test_world.py`

**Interfaces:**
- Consumes:
  - From Task 1: `Cat.pet`, `Petting`.
  - From milestone 3: `Mode`, `Doing`, `Step`, `Body`, `advance`, `choose`, `clamp`, `walkable`; `playscape.CAT_WIDTH`, `CAT_HEIGHT`, `Box`.
- Produces:
  - `tools.py`:
    - `Tool` enum: `FEED`, `BALL`, `STRING`, `PET`, `SCOOP`, with values `"feed"`, `"ball"`, `"string"`, `"pet"` and `"scoop"`.
    - `WORKS_DURING_FOCUS = {Tool.SCOOP}`.
    - `locked(tool: Tool, mode: Mode) -> bool`.
  - `events.py`: `Fed(already_full: bool = False)`, `Petted(name: str, how: str)` and `Played(name: str, toy: str)`, all in the `Event` union.
  - `Doing.PURR`.
  - Balance: `STROKE_CELLS=6`, `PURR_S=3.0`, `EFFECT_S=1.5`, `EFFECT_RISE=6.0`.
  - `world.py`:
    - `mode_for(phase, started, idle=False)`: idle means `Mode.RELAX`.
    - `Poop(x, y)` and `Effect(kind, x, y, age=0.0)`.
    - `EffectView(kind, x, y)`, where y is the risen pixel row.
    - `CursorView(tool: str, x, y, busy=False)`.
    - `RoomView` gains `poops: tuple[tuple[float, int], ...]`, `effects: tuple[EffectView, ...]` and `cursor: CursorView | None`.
  - `World`:
    - State: `.tool`, `.pointer` (room column and pixel row, or `None`), `.poops`, `.effects`.
    - `.feed()`, which replaces `refill()` and records a `Fed` in the news.
    - `.hold(tool | None) -> bool`: False if the tool is locked. Picking Feed again feeds.
    - `.point(x, y)`, `.click(x, y)`, `.leave()`.
    - `.take_news() -> list[Event]`.
    - `BreakCompleted` no longer fills the bowl.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_care.py`:

```python
import random

import pytest

from pomo.game.behavior import Doing, Mode, Step
from pomo.game.cat import Cat, Trait
from pomo.game.events import Fed, Petted
from pomo.game.tools import Tool, locked
from pomo.game.world import Poop, World, mode_for
from pomo.timer import Phase

TICK = 0.125


def room(*names: str, seed: int = 1) -> World:
    """Cats on the floor of a 70×58 room: the first at x=38, the next 22 columns on."""
    return World([Cat(name, "tabby", Trait.CLINGY) for name in names], random.Random(seed), 70, 58)


def run(world: World, seconds: float) -> None:
    for _ in range(int(seconds / TICK)):
        world.tick(TICK)


def stroke(world: World, x0: float, cells: int, y: float = 50) -> None:
    """Move the hand one column at a time, from x0 across `cells` columns."""
    for i in range(cells + 1):
        world.point(x0 + i, y)


class AlwaysLow(random.Random):
    """Every roll comes out 0.1: a 30% swat always happens."""

    def random(self) -> float:
        return 0.1


# --- tools -------------------------------------------------------------------

@pytest.mark.parametrize("mode, open_tools", [
    (Mode.NAP, {Tool.SCOOP}),
    (Mode.PLAY, set(Tool)),
    (Mode.RELAX, set(Tool)),
])
def test_a_focus_locks_every_tool_but_the_scoop(mode, open_tools):
    assert {t for t in Tool if not locked(t, mode)} == open_tools


def test_idle_is_relaxed():
    assert mode_for(Phase.FOCUS, True, idle=True) is Mode.RELAX
    assert mode_for(Phase.SHORT_BREAK, False, idle=True) is Mode.RELAX


def test_a_locked_tool_cannot_be_picked_up():
    world = room("Mango")
    world.set_mode(Mode.NAP)
    assert not world.hold(Tool.BALL)
    assert world.tool is None
    assert world.hold(Tool.SCOOP)
    assert world.tool is Tool.SCOOP


def test_a_focus_starting_puts_the_toys_away_but_not_the_scoop():
    world = room("Mango")
    world.hold(Tool.PET)
    world.set_mode(Mode.NAP)
    assert world.tool is None
    world.hold(Tool.SCOOP)
    world.set_mode(Mode.PLAY)
    world.set_mode(Mode.NAP)
    assert world.tool is Tool.SCOOP


def test_the_tool_in_hand_follows_the_pointer_over_the_room():
    world = room("Mango")
    world.hold(Tool.BALL)
    assert world.view().cursor is None  # the pointer hasn't come over the room yet
    world.point(10, 20)
    cursor = world.view().cursor
    assert (cursor.tool, cursor.x, cursor.y, cursor.busy) == ("ball", 10, 20, False)
    world.leave()
    assert world.view().cursor is None
    world.point(10, 20)
    world.hold(None)
    assert world.view().cursor is None


# --- feed ----------------------------------------------------------------------

def test_clicking_the_bowl_with_kibble_fills_it():
    world = room("Mango")
    world.bowl_full = False
    world.hold(Tool.FEED)
    bowl = world.scape.bowl
    world.click(bowl.x - 3, bowl.y + 1)  # beside it
    assert not world.bowl_full
    world.click(bowl.x + 3, bowl.y + 1)
    assert world.bowl_full
    assert world.take_news() == [Fed()]
    assert world.take_news() == []


def test_the_bowl_can_be_clicked_from_the_row_above():
    world = room("Mango")
    world.bowl_full = False
    world.hold(Tool.FEED)
    world.click(world.scape.bowl.x + 3, world.scape.bowl.y - 2)
    assert world.bowl_full


def test_picking_feed_twice_fills_the_bowl():
    world = room("Mango")
    world.bowl_full = False
    world.hold(Tool.FEED)
    assert not world.bowl_full
    world.hold(Tool.FEED)
    assert world.bowl_full


def test_feeding_a_full_bowl_says_so():
    world = room("Mango")
    world.feed()
    assert world.take_news() == [Fed(already_full=True)]


def test_only_the_feed_tool_fills_the_bowl():
    world = room("Mango")
    world.bowl_full = False
    world.hold(Tool.SCOOP)
    world.click(world.scape.bowl.x + 3, world.scape.bowl.y + 1)
    assert not world.bowl_full


def test_a_hungry_cat_comes_to_eat_once_the_bowl_is_filled():
    world = room("Mango")
    world.bowl_full = False
    world.cats[0].needs["hunger"] = 90
    run(world, 30)
    assert world.cats[0].needs["hunger"] > 80  # begging at an empty bowl
    world.hold(Tool.FEED)
    world.hold(Tool.FEED)
    run(world, 60)
    assert world.cats[0].needs["hunger"] < 5


# --- scoop ---------------------------------------------------------------------

def test_clicking_a_poop_scoops_it_up():
    world = room("Mango")
    floor = world.scape.floor.y
    world.poops = [Poop(20, floor), Poop(50, floor)]
    world.hold(Tool.SCOOP)
    world.click(30, floor - 2)  # nowhere near either
    assert len(world.poops) == 2
    world.click(21, floor - 2)
    assert [p.x for p in world.poops] == [50]
    assert world.view().poops == ((50, floor),)


def test_scooping_works_during_a_focus():
    world = room("Mango")
    floor = world.scape.floor.y
    world.poops = [Poop(20, floor)]
    world.set_mode(Mode.NAP)
    world.hold(Tool.SCOOP)
    world.click(20, floor - 1)
    assert world.poops == []


def test_poops_stay_on_the_floor_when_the_room_is_resized():
    world = room("Mango")
    world.poops = [Poop(65, world.scape.floor.y)]
    world.fit(100, 80)
    assert (world.poops[0].x, world.poops[0].y) == (65, 79)
    world.fit(70, 54)
    assert (world.poops[0].x, world.poops[0].y) == (65, 53)


# --- pet -----------------------------------------------------------------------

def test_six_cells_of_hand_movement_on_a_cat_is_one_stroke():
    world = room("Mango")
    mango = world.cats[0]
    mango.needs["affection"] = 60
    world.hold(Tool.PET)
    stroke(world, 33, 5)
    assert mango.needs["affection"] == 60
    world.point(39, 50)
    assert (mango.needs["affection"], mango.mood) == (35, 82)
    assert world.take_news() == [Petted("Mango", "purr")]


def test_a_purring_cat_sits_still_shuts_its_eyes_and_floats_a_heart():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    body = world.bodies["Mango"]
    assert body.step.doing is Doing.PURR
    (mango,) = world.view().cats
    assert (mango.pose, mango.face, mango.bubble) == ("sit", "blink", "prr")
    (heart,) = world.view().effects
    assert (heart.kind, heart.x) == ("heart", 44)  # beside the head, clear of the "prr" over it
    x = body.x
    run(world, 2)
    assert body.x == x and body.step.doing is Doing.PURR


def test_effects_float_up_and_fade():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    start = world.view().effects[0].y
    run(world, 1)
    assert world.view().effects[0].y == pytest.approx(start - 6)
    run(world, 0.5)
    assert world.view().effects == ()


def test_the_hand_is_busy_while_it_is_on_a_cat():
    world = room("Mango")
    world.hold(Tool.PET)
    world.point(10, 50)
    assert not world.view().cursor.busy
    world.point(38, 50)
    assert world.view().cursor.busy


def test_moving_onto_a_cat_is_not_a_stroke_yet():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.PET)
    world.point(10, 50)
    world.point(38, 50)  # a 28-column jump onto the cat
    assert world.cats[0].needs["affection"] == 60


def test_up_and_down_counts_half_as_much_as_across():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.PET)
    for y in (42, 44, 46, 48, 50, 52):  # five moves of one row each: 5 cells
        world.point(38, y)
    assert world.cats[0].needs["affection"] == 60
    world.point(38, 54)
    assert world.cats[0].needs["affection"] == 35


def test_leaving_the_room_lifts_the_hand():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.PET)
    stroke(world, 33, 3)
    world.leave()
    stroke(world, 36, 3)
    assert world.cats[0].needs["affection"] == 60


def test_only_the_hand_pets():
    world = room("Mango")
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.BALL)
    stroke(world, 33, 10)
    assert world.cats[0].needs["affection"] == 60


def test_an_angry_cat_hisses_at_the_hand():
    world = room("Mango")
    mango = world.cats[0]
    mango.mood, mango.needs["affection"] = 30, 60
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    assert (mango.mood, mango.needs["affection"]) == (30, 60)
    assert [e.kind for e in world.view().effects] == ["hiss"]
    assert world.bodies["Mango"].step is None or world.bodies["Mango"].step.doing is not Doing.PURR
    assert world.take_news() == [Petted("Mango", "hiss")]


def test_too_much_petting_earns_a_swat():
    world = room("Mango")
    mango = world.cats[0]
    mango.needs["affection"] = 5
    world.rng = AlwaysLow()
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    assert mango.mood == 78
    assert [e.kind for e in world.view().effects] == ["swat"]
    assert world.take_news() == [Petted("Mango", "swat")]


def test_a_grumpy_cat_sits_for_petting_without_hearts():
    world = room("Mango")
    mango = world.cats[0]
    mango.mood, mango.needs["affection"] = 50, 60
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    assert mango.mood == 52
    assert world.bodies["Mango"].step.doing is Doing.PURR
    (view,) = world.view().cats
    assert (view.face, view.bubble) == ("meh", None)
    assert world.view().effects == ()


def test_the_hand_pets_the_cat_in_front():
    world = room("Mango", "Pebble")
    for cat in world.cats:
        cat.needs["affection"] = 60
    world.bodies["Pebble"].x = 42  # overlapping Mango at 38, and drawn over him
    world.hold(Tool.PET)
    stroke(world, 34, 6)
    assert [c.needs["affection"] for c in world.cats] == [60, 35]


def test_a_cat_out_through_the_door_cannot_be_petted():
    world = room("Mango")
    mango = world.cats[0]
    mango.needs["affection"] = 60
    world.bodies["Mango"].step = Step(Doing.AWAY, seconds=30)
    world.hold(Tool.PET)
    stroke(world, 33, 6)
    assert mango.needs["affection"] == 60
```

In `tests/test_world.py`, replace milestone 3's stand-in test:

Replace:

```python
def test_until_there_is_a_feed_button_a_finished_break_refills_the_bowl():
    from pomo.game.events import BreakCompleted, FocusCompleted
    world = world_with("Mango")
    world.bowl_full = False
    world.apply([FocusCompleted(25)])
    assert not world.bowl_full
    world.apply([BreakCompleted(Phase.SHORT_BREAK)])
    assert world.bowl_full
```

with:

```python
def test_a_finished_break_leaves_the_bowl_to_you():
    from pomo.game.events import BreakCompleted
    world = world_with("Mango")
    world.bowl_full = False
    world.apply([BreakCompleted(Phase.SHORT_BREAK)])
    assert not world.bowl_full
```

Then rename every `world.refill()` in `tests/test_world.py` to `world.feed()`. There are two, in `test_a_hungry_cat_eats_and_the_next_one_begs` and `test_a_long_day_in_the_room_never_gets_stuck`.

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_care.py tests/test_world.py -q`
Expected: FAIL during collection with `ImportError: cannot import name 'Fed' from 'pomo.game.events'`

- [ ] **Step 3: The tools and the care events**

Create `src/pomo/game/tools.py`:

```python
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


WORKS_DURING_FOCUS = frozenset({Tool.SCOOP})  # tuna joins it in milestone 5


def locked(tool: Tool, mode: Mode) -> bool:
    """A focus under way is nap time: every tool but the scoop waits for the break."""
    return mode is Mode.NAP and tool not in WORKS_DURING_FOCUS
```

Replace all of `src/pomo/game/events.py` with:

```python
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
```

In `src/pomo/game/behavior.py`, in `class Doing`:

Replace:

```python
    AWAY = "away"  # out through the litter door
```

with:

```python
    AWAY = "away"  # out through the litter door
    PURR = "purr"  # being petted: sits still and enjoys it
```

Append to the end of `src/pomo/game/balance.py`, right after `GRUMPY_TOY_FACTOR`:

```python
STROKE_CELLS = 6  # hand movement inside a cat's box, in cells, that makes one stroke
PURR_S = 3.0  # a petted cat sits still this long after the last stroke
EFFECT_S = 1.5  # hearts, hisses and swats float this long...
EFFECT_RISE = 6.0  # ...rising this many pixels a second
```

- [ ] **Step 4: The hand in the world**

Replace all of `src/pomo/game/world.py` with:

```python
"""The cat room over time: the cats, where they are, the bowl, and the mood of the moment (spec §3, §6).

Pure: `tick(dt)` moves time on, `apply(events)` feeds in the session's rule breaks and
rewards, the tool commands (`hold`, `point`, `click`, `leave`) are the player's hand
in the room, and `view()` describes what to draw. Randomness comes from an injected RNG.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from pomo.game import balance
from pomo.game.behavior import Body, Doing, Mode, Step, advance, choose, clamp, walkable
from pomo.game.cat import Cat, Petting, Stage
from pomo.game.events import Event, Fed, Petted
from pomo.game.playscape import CAT_HEIGHT, CAT_WIDTH, MIN_HEIGHT, MIN_WIDTH, Box, Playscape, layout
from pomo.game.tools import Tool, locked
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


@dataclass
class Poop:
    x: float
    y: int  # the surface it's on


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
class RoomView:
    cats: tuple[CatView, ...] = ()
    roster: tuple[RosterLine, ...] = ()
    bowl_full: bool = True
    poops: tuple[tuple[float, int], ...] = ()
    effects: tuple[EffectView, ...] = ()
    cursor: CursorView | None = None


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
        self.pointer = None  # until the mouse moves again

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
        return True

    def point(self, x: float, y: float) -> None:
        """The pointer moved to column x, pixel row y of the room."""
        before, self.pointer = self.pointer, (x, y)
        if self.tool is Tool.PET:
            self._move_hand(before, x, y)

    def click(self, x: float, y: float) -> None:
        self.point(x, y)
        if self.tool is Tool.FEED and _inside(self.scape.bowl, x, y):
            self.feed()
        elif self.tool is Tool.SCOOP:
            self._scoop(x, y)

    def leave(self) -> None:
        """The pointer left the room."""
        self.pointer = None
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
        for cat in self.cats:
            cat.tick(dt)
            body = self.bodies[cat.name]
            self.litter_in[cat.name] -= dt
            self._next_step(cat, body)
            finished = advance(body, self.scape, dt)
            if finished is not None:
                if finished.doing is Doing.EAT and self.bowl_full:
                    cat.eat()
                    self.bowl_full = False
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
        effects = tuple(EffectView(e.kind, e.x, e.y - e.age * balance.EFFECT_RISE) for e in self.effects)
        cursor = None
        if self.tool is not None and self.pointer is not None:
            cursor = CursorView(self.tool.value, *self.pointer, busy=self._petting is not None)
        return RoomView(tuple(cats), roster, self.bowl_full, tuple((p.x, p.y) for p in self.poops),
                        effects, cursor)


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
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -q`
Expected: `407 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/game/tools.py src/pomo/game/events.py src/pomo/game/behavior.py src/pomo/game/balance.py src/pomo/game/world.py tests/test_care.py tests/test_world.py
git commit -m "feat: the tools in the world: feed the bowl, scoop poop, pet with the hand, lock during focus" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Toys: the yarn ball and the string

**Files:**
- Create: `src/pomo/game/toys.py`
- Modify: `src/pomo/game/behavior.py` (`Step.hop`)
- Modify: `src/pomo/game/balance.py` (append)
- Replace: `src/pomo/game/world.py`
- Test: create `tests/test_toys.py`

**Interfaces:**
- Consumes:
  - From Task 3: the whole of the `World` hand (`hold`, `point`, `click`, `leave`, `_stroke`, `_news`, `Played`).
  - From milestone 3: `route`, `Surface`, `advance`.
- Produces:
  - `toys.py`:
    - `Ball(x, y, vx=0, vy=0, rolled=0)` with `.tick(dt, width, floor)`. `y` is the pixel row under the ball.
    - `String(anchor, tip_x, tip_y, vx=0)` with `.tick(dt)`.
  - `Step.hop: float | None`: a jump's arc height when set (a pounce).
  - Balance: `PLAY_S=10.0`, `PHYSICS_STEP_S`, `BALL_*`, `BAT_*`, `POUNCE_HOP=(3, 14)`, `POUNCE_SIT_S`, `STRING_SPRING`, `STRING_DAMPING`, `STRING_TOP=2`.
  - `World`:
    - `.ball: Ball | None`, `.string: String | None`, `.playing: dict[str, Play]`.
    - `Play(toy, left)`.
    - Constants `STRING_REACH`, `UNDER_STRING`, `STRING_MARGIN`.
  - `BallView(x, y, frame)` and `StringView(anchor, tip_x, tip_y)`.
  - `RoomView` gains `ball: BallView | None` and `string: StringView | None`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_toys.py`:

```python
import random

import pytest

from pomo.game.behavior import Doing, Mode
from pomo.game.cat import Cat, Trait
from pomo.game.events import Played
from pomo.game.tools import Tool
from pomo.game.toys import Ball, String
from pomo.game.world import World

TICK = 0.125
FLOOR = 57  # in a 70×58 room


def room(*names: str, seed: int = 1, width: int = 70) -> World:
    world = World([Cat(name, "tabby", Trait.CLINGY) for name in names], random.Random(seed), width, 58)
    world.set_mode(Mode.PLAY)
    return world


def run(world: World, seconds: float, each=None) -> None:
    for _ in range(int(seconds / TICK)):
        world.tick(TICK)
        if each:
            each(world)


def playful(world: World) -> Cat:
    """Mango, content and keen to play."""
    mango = world.cats[0]
    mango.needs["play"] = 90
    return mango


class AlwaysHigh(random.Random):
    """Every roll comes out 0.99: a cat goes for a toy only if it's certain to."""

    def random(self) -> float:
        return 0.99


# --- the ball on its own ----------------------------------------------------------

def test_a_dropped_ball_bounces_lower_each_time_then_rests():
    ball = Ball(30, 10)
    peaks, rising = [], False
    for _ in range(5 * 32):
        before = ball.y
        ball.tick(1 / 32, 70, FLOOR)
        if ball.y < before:
            rising = True
        elif rising:
            peaks.append(before)
            rising = False
    assert len(peaks) >= 2
    assert all(later > earlier for earlier, later in zip(peaks, peaks[1:]))  # lower bounces: bigger y
    assert (ball.y, ball.vy) == (FLOOR, 0)


def test_a_rolling_ball_slows_to_a_stop():
    ball = Ball(10, FLOOR, vx=20)
    ball.tick(2.0, 70, FLOOR)
    assert ball.vx == 0
    assert ball.x == pytest.approx(20, abs=0.5)  # v² / 2a = 400 / 40


def test_the_ball_bounces_off_the_walls():
    ball = Ball(60, FLOOR, vx=40)
    ball.tick(0.5, 70, FLOOR)
    assert ball.vx < 0
    assert ball.x <= 67.5


def test_a_long_tick_cannot_throw_the_ball_out_of_the_room():
    ball = Ball(35, 10, vx=300)
    ball.tick(1.0, 70, FLOOR)
    assert 2.5 <= ball.x <= 67.5
    assert ball.y <= FLOOR


def test_the_string_tip_swings_past_the_mouse_and_settles_under_it():
    string = String(20, 20, 30)
    string.anchor = 30
    furthest = 0.0
    for _ in range(3 * 32):
        string.tick(1 / 32)
        furthest = max(furthest, string.tip_x)
    assert furthest > 31  # it swung past
    assert string.tip_x == pytest.approx(30, abs=0.5)


def test_a_long_tick_cannot_make_the_string_fly_off():
    string = String(20, 20, 30)
    string.anchor = 40
    string.tick(1.0)
    assert 20 <= string.tip_x <= 60


# --- the ball in the room -----------------------------------------------------------

def test_clicking_with_the_ball_drops_it_at_the_pointer():
    world = room("Mango")
    world.hold(Tool.BALL)
    world.click(30, 20)
    ball = world.view().ball
    assert (ball.x, ball.y) == (30, 20)
    run(world, 3)
    assert world.view().ball.y == FLOOR


def test_there_is_only_ever_one_ball():
    world = room("Mango")
    world.hold(Tool.BALL)
    world.click(30, 20)
    world.click(50, 40)
    assert (world.ball.x, world.ball.y) == (50, 40)


def test_the_yarn_turns_as_it_rolls():
    world = room("Mango")
    world.hold(Tool.BALL)
    world.click(30, FLOOR)
    frames = set()
    run(world, 1, lambda w: frames.add(w.view().ball.frame))
    assert frames == {0, 1}


def test_a_playful_cat_chases_bats_and_finishes_a_session():
    world = room("Mango")
    mango = playful(world)
    world.hold(Tool.BALL)
    world.click(60, 30)
    fastest, poses = 0.0, set()

    def watch(w):
        nonlocal fastest
        fastest = max(fastest, abs(w.ball.vx))
        poses.update(c.pose for c in w.view().cats)

    run(world, 12, watch)
    assert fastest >= 25  # batted: a dropped ball never rolls faster than 20
    assert "leap" in poses  # pounced
    assert Played("Mango", "ball") in world.take_news()
    assert mango.needs["play"] == pytest.approx(40, abs=1)
    assert mango.mood > 84


def test_a_cat_with_no_need_to_play_can_ignore_the_ball():
    world = room("Mango")
    world.rng = AlwaysHigh()
    world.hold(Tool.BALL)
    world.click(60, 30)
    run(world, 20)
    assert world.playing == {}
    assert world.take_news() == []


@pytest.mark.parametrize("mood", [30, 10])
def test_angry_cats_refuse_toys(mood):
    world = room("Mango")
    mango = playful(world)
    mango.mood = mood
    world.hold(Tool.BALL)
    world.click(60, 30)
    run(world, 20)
    assert world.playing == {}
    assert mango.needs["play"] > 90


def test_a_hungry_cat_eats_before_it_plays():
    world = room("Mango")
    mango = playful(world)
    mango.needs["hunger"] = 90
    world.hold(Tool.BALL)
    world.click(20, 30)
    assert world.playing == {}
    run(world, 20)
    assert mango.needs["hunger"] < 5


def test_a_focus_starting_ends_play_and_leaves_the_ball_where_it_is():
    world = room("Mango")
    mango = playful(world)
    world.hold(Tool.BALL)
    world.click(60, 30)
    run(world, 2)
    assert "Mango" in world.playing
    world.set_mode(Mode.NAP)
    assert (world.playing, world.tool) == ({}, None)
    run(world, 30)
    assert world.ball is not None
    assert world.take_news() == []
    assert mango.needs["play"] > 85


def test_petting_a_playing_cat_stops_the_game():
    world = room("Mango")
    playful(world)
    world.cats[0].needs["affection"] = 60
    world.hold(Tool.BALL)
    world.click(60, 30)
    run(world, 1)
    x = world.bodies["Mango"].x
    world.hold(Tool.PET)
    for i in range(7):
        world.point(x - 3 + i, FLOOR - 6)
    assert world.playing == {}
    assert world.bodies["Mango"].step.doing is Doing.PURR


# --- the string ---------------------------------------------------------------------

def test_the_string_hangs_where_the_pointer_is_and_goes_with_it():
    world = room("Mango")
    world.hold(Tool.STRING)
    assert world.view().string is None
    world.point(20, 30)
    string = world.view().string
    assert (string.anchor, string.tip_x, string.tip_y) == (20, 20, 30)
    world.leave()
    assert world.view().string is None
    world.point(25, 30)
    world.hold(None)
    assert world.view().string is None


def test_picking_up_the_string_with_the_pointer_over_the_room_hangs_it_there():
    world = room("Mango")
    world.hold(Tool.BALL)
    world.point(20, 30)
    world.hold(Tool.STRING)
    assert world.view().string.anchor == 20


def test_the_string_tip_stays_inside_the_room():
    world = room("Mango")
    world.hold(Tool.STRING)
    world.point(20, -5)
    assert world.string.tip_y == 2
    world.point(20, 80)
    assert world.string.tip_y == FLOOR - 1


def test_a_playful_cat_climbs_up_to_bat_at_a_high_string():
    world = room("Mango", seed=0)
    playful(world)
    world.hold(Tool.STRING)
    world.point(20, 30)  # 9 pixels above the tree's middle platform
    leaps_up_there = []

    def watch(w):
        body = w.bodies["Mango"]
        if body.step is not None and body.step.doing is Doing.JUMP and body.step.hop is not None:
            leaps_up_there.append(body.surface)

    run(world, 20, watch)
    assert "tree_mid" in leaps_up_there
    assert Played("Mango", "string") in world.take_news()


def test_a_string_too_high_above_everything_is_ignored():
    world = room("Mango", width=120)
    playful(world)
    world.hold(Tool.STRING)
    world.point(100, 3)  # over bare floor, 54 pixels up
    run(world, 20)
    assert world.playing == {}
    assert world.take_news() == []


def test_putting_the_string_away_mid_game_ends_it_with_nothing_earned():
    world = room("Mango")
    mango = playful(world)
    world.hold(Tool.STRING)
    world.point(45, 40)
    run(world, 4)
    assert "Mango" in world.playing
    world.hold(None)
    run(world, 12)
    assert world.playing == {}
    assert Played("Mango", "string") not in world.take_news()
    assert mango.needs["play"] > 90


def test_resizing_rests_the_ball_on_the_new_floor_and_takes_the_string_down():
    world = room("Mango")
    world.hold(Tool.BALL)
    world.click(65, 20)
    world.hold(Tool.STRING)
    world.point(20, 30)
    world.fit(100, 80)
    assert (world.ball.y, world.string) == (79, None)
    world.fit(50, 54)
    assert world.ball.x <= 47.5


def test_an_hour_of_toys_never_gets_anyone_stuck():
    world = room("Mango", "Pebble", seed=4)
    rng = random.Random(9)
    world.hold(Tool.BALL)
    world.click(40, 20)
    last_change = {name: 0.0 for name in world.bodies}
    previous = {}
    sessions = 0
    t = 0.0
    for second in range(3600):
        if second % 600 == 0:
            world.set_mode(Mode.PLAY if second % 1200 else Mode.RELAX)
            world.feed()
        if second % 10 == 0:
            if rng.random() < 0.5:
                world.hold(Tool.STRING)
                world.point(rng.uniform(0, 70), rng.uniform(0, 57))
            else:
                world.hold(Tool.BALL)
                world.click(rng.uniform(0, 70), rng.uniform(0, 57))
        for _ in range(8):
            world.tick(TICK)
            t += TICK
            for name, body in world.bodies.items():
                state = (body.surface, round(body.x), body.step.doing if body.step else None)
                if state != previous.get(name):
                    previous[name], last_change[name] = state, t
                if body.step is None or body.step.doing is not Doing.JUMP:
                    assert body.y == world.scape.surface(body.surface).y
                assert 0 <= body.x <= 70
                assert t - last_change[name] <= 400  # the longest nap is 300 s
        sessions += sum(isinstance(e, Played) for e in world.take_news())
    assert sessions >= 10
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_toys.py -q`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.game.toys'`

- [ ] **Step 3: The toy numbers and physics**

Append to the end of `src/pomo/game/balance.py`:

```python
# --- toys (spec §5.2) -------------------------------------------------------
PLAY_S = 10.0  # a play session: about 10 s with a toy
PHYSICS_STEP_S = 1 / 32  # toys move in steps this small, however long the tick
BALL_RADIUS = 2.5  # half the yarn sprite's width
BALL_GRAVITY = 160.0  # pixels per second²
BALL_BOUNCE = 0.45  # speed kept bouncing off the floor...
BALL_WALL_BOUNCE = 0.6  # ...and off a wall
BALL_SETTLE = 12.0  # a bounce slower than this is over
BALL_FRICTION = 20.0  # columns per second², rolling
BALL_DROP_SPEED = (8.0, 20.0)  # a dropped ball rolls off this fast, left or right
BAT_REACH = 8  # a cat this close to the ball pounces on it...
BAT_SPEED = (25.0, 45.0)  # ...and bats it away this fast...
BAT_LIFT = (15.0, 35.0)  # ...and this fast upwards
POUNCE_HOP = (3, 14)  # a pounce rises at least, and at most, this many pixels
POUNCE_SIT_S = (0.3, 0.8)  # a pause to eye the string before the next pounce
STRING_SPRING = 40.0  # how hard the tip swings back under the mouse...
STRING_DAMPING = 5.0  # ...and how fast the swinging dies down
STRING_TOP = 2  # the tip never goes higher than this pixel row
```

Create `src/pomo/game/toys.py`:

```python
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
```

- [ ] **Step 4: Pounces**

In `src/pomo/game/behavior.py`, in `class Step`:

Replace:

```python
    surface: str = ""  # JUMP: what to land on
```

with:

```python
    surface: str = ""  # JUMP: what to land on
    hop: float | None = None  # JUMP: how high the arc rises, if not the usual (a pounce)
```

and in `advance`, in the `Doing.JUMP` branch:

Replace:

```python
        hop = balance.JUMP_ARC_PX + abs(y1 - y0) / 2  # rise above the higher end, then drop onto it
```

with:

```python
        hop = step.hop  # a pounce sets its own height
        if hop is None:
            hop = balance.JUMP_ARC_PX + abs(y1 - y0) / 2  # rise above the higher end, then drop onto it
```

- [ ] **Step 5: Cats playing with toys**

Replace all of `src/pomo/game/world.py` with:

```python
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
```

- [ ] **Step 6: Run the tests**

Run: `uv run pytest -q`
Expected: `431 passed`

- [ ] **Step 7: Commit**

```bash
git add src/pomo/game/toys.py src/pomo/game/behavior.py src/pomo/game/balance.py src/pomo/game/world.py tests/test_toys.py
git commit -m "feat: the yarn ball and the string: toy physics, and cats that chase, bat and pounce" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: The art for toys and tools

**Files:**
- Modify: `src/pomo/render/sprites.py` (replace the `PROPS` dict)
- Replace: `src/pomo/gallery.py`
- Test: `tests/test_sprites.py` (imports, and new tests at the end), `tests/test_gallery.py` (size)

**Interfaces:**
- Consumes: `Tool` from Task 3 (tests only).
- Produces:
  - Sprites and palettes:
    - `POOP` / `POOP_PALETTE`.
    - `YARN: tuple[Grid, Grid]` / `YARN_PALETTE`: two rolling frames, 5×5.
    - `TEASER` / `TEASER_PALETTE`.
    - `HAND: tuple[Grid, Grid]` / `HAND_PALETTE`: open, and patting.
    - `KIBBLE` / `KIBBLE_PALETTE` and `SCOOPER` / `SCOOPER_PALETTE`.
  - `CURSORS: dict[str, tuple[Grid, palette, (hx, hy)]]` for `"feed"`, `"ball"`, `"pet"` and `"scoop"`. The string has no cursor.
  - `PROPS` gains `poop`, `yarn0`, `yarn1`, `teaser`, `hand0`, `hand1`, `kibble` and `scooper`.
  - `pomo --gallery` wraps its props and needs 100×46.

- [ ] **Step 1: Write the failing tests**

In `tests/test_sprites.py`, change the imports:

Replace:

```python
from pomo.game import playscape
from pomo.render import sprites
from pomo.render.sprites import (
    CAT_SLOTS, CAT_WIDTH, COATS, FACES, FRONT_POSES, POSES, PROPS, SIDE_POSES, SIDE_WIDTH,
    cat, cat_head, flip, mirror, problems,
)
```

with:

```python
from pomo.game import playscape
from pomo.game.tools import Tool
from pomo.render import sprites
from pomo.render.sprites import (
    CAT_SLOTS, CAT_WIDTH, COATS, CURSORS, FACES, FRONT_POSES, HAND, POSES, PROPS, SIDE_POSES, SIDE_WIDTH, YARN,
    cat, cat_head, flip, mirror, problems,
)
```

Append to the end of `tests/test_sprites.py`:

```python
def test_every_tool_but_the_string_has_a_cursor():
    assert set(CURSORS) == {tool.value for tool in Tool} - {"string"}


@pytest.mark.parametrize("tool", CURSORS)
def test_each_cursor_is_clean_and_its_hotspot_is_on_a_drawn_pixel(tool):
    grid, palette, (hx, hy) = CURSORS[tool]
    assert problems(grid, set(palette)) == []
    assert grid[hy][hx] in palette


@pytest.mark.parametrize("frames", [YARN, HAND], ids=["yarn", "hand"])
def test_two_frame_props_differ_but_keep_their_size(frames):
    first, second = frames
    assert first != second
    assert (len(first), len(first[0])) == (len(second), len(second[0]))
```

In `tests/test_gallery.py`:

Replace:

```python
SIZE = (100, 40)
```

with:

```python
SIZE = (100, 46)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_sprites.py tests/test_gallery.py -q`
Expected: FAIL during collection with `ImportError: cannot import name 'CURSORS' from 'pomo.render.sprites'`

- [ ] **Step 3: Draw the props and tools**

In `src/pomo/render/sprites.py`:

Replace:

```python
PROPS: dict[str, tuple[Grid, Mapping[str, RGB]]] = {
    "door": (DOOR, DOOR_PALETTE),
    "bowl_full": (BOWL_FULL, BOWL_PALETTE),
    "bowl_empty": (BOWL_EMPTY, BOWL_PALETTE),
}
```

with:

```python
POOP: Grid = ("...o...", "..obo..", ".obhbo.", "obbbbbo")
POOP_PALETTE = {"o": hex_rgb("#2e1d12"), "b": hex_rgb("#6b4226"), "h": hex_rgb("#9c6b43")}

# The yarn ball rolls: its two frames swap the light and dark strands.
YARN: tuple[Grid, Grid] = (
    (".ooo.", "orrlo", "olrro", "orlro", ".ooo."),
    (".ooo.", "olrro", "orlro", "orrlo", ".ooo."),
)
YARN_PALETTE = {"o": hex_rgb("#6b2440"), "r": hex_rgb("#f7768e"), "l": hex_rgb("#ffc8d4")}

TEASER: Grid = (".f.", "fFf", "fFf", ".f.")  # the feather on the end of the string
TEASER_PALETTE = {"f": hex_rgb("#9d7cd8"), "F": hex_rgb("#e0cffc")}

# --- tools: what the pointer carries over the room (spec §5.2) --------------

HAND: tuple[Grid, Grid] = (  # open, and patting a cat
    (".ooooo...", "osdsdso..", "osdsdso..", "osdsdsooo", "osssssoso", "ossssssso", ".osssssso", "..oooooo."),
    (".........", ".ooooo...", "osdsdsooo", "osdsdsoso", "ossssssso", "ossssssso", ".osssssso", "..oooooo."),
)
HAND_PALETTE = {"o": hex_rgb("#5a3a28"), "s": hex_rgb("#f2c9a0"), "d": hex_rgb("#d9a67c")}

KIBBLE: Grid = (".kkkk..", "okkkkko", "obbbbbo", ".obbbo.", "..ooo..")  # a scoop of kibble
KIBBLE_PALETTE = {"k": hex_rgb("#b8631e"), "b": hex_rgb("#9aa5ce"), "o": hex_rgb("#3b4261")}

SCOOPER: Grid = ("......h", ".....h.", "....h..", "bbbbh..", "bgbgb..", "bgbgb..", ".bbb...")
SCOOPER_PALETTE = {"h": hex_rgb("#7aa2f7"), "b": hex_rgb("#7dcfff"), "g": hex_rgb("#1a1b26")}

# Each tool's sprite and the pixel of it that sits on the pointer. The string has
# none: the string itself hangs from the pointer. The hand's second frame is for patting.
CURSORS: dict[str, tuple[Grid, Mapping[str, RGB], tuple[int, int]]] = {
    "feed": (KIBBLE, KIBBLE_PALETTE, (3, 1)),
    "ball": (YARN[0], YARN_PALETTE, (2, 2)),
    "pet": (HAND[0], HAND_PALETTE, (4, 4)),
    "scoop": (SCOOPER, SCOOPER_PALETTE, (2, 5)),
}

PROPS: dict[str, tuple[Grid, Mapping[str, RGB]]] = {
    "door": (DOOR, DOOR_PALETTE),
    "bowl_full": (BOWL_FULL, BOWL_PALETTE),
    "bowl_empty": (BOWL_EMPTY, BOWL_PALETTE),
    "poop": (POOP, POOP_PALETTE),
    "yarn0": (YARN[0], YARN_PALETTE),
    "yarn1": (YARN[1], YARN_PALETTE),
    "teaser": (TEASER, TEASER_PALETTE),
    "hand0": (HAND[0], HAND_PALETTE),
    "hand1": (HAND[1], HAND_PALETTE),
    "kibble": (KIBBLE, KIBBLE_PALETTE),
    "scooper": (SCOOPER, SCOOPER_PALETTE),
}
```

- [ ] **Step 4: Let the gallery wrap**

Replace all of `src/pomo/gallery.py` with:

```python
"""`pomo --gallery`: every front pose × face and the side poses for one coat at a time,
plus the props and tools (spec §7). For tuning the art: flip through the coats with ←/→.
Needs a 100×46 terminal.
"""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding

from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.ui.stage import Stage

COLUMN = 19  # a 17-pixel front cat plus a gap
SIDE_COLUMN = 22  # a 20-pixel side cat plus a gap
SIT_PY, LOAF_PY, SIDE_PY, PROPS_PY = 4, 24, 44, 64
PROP_GAP = 3  # columns between props
LABEL_PX = 4  # a label row under each row of props, and a gap
SIDE_SHOWN = (("walk0", "ok"), ("walk1", "ok"), ("leap", "ok"), ("walk0", "mad"))


class GalleryApp(App[None]):
    TITLE = "pomo gallery"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("right,n", "coat(1)", "Next coat"),
        Binding("left,p", "coat(-1)", "Previous coat"),
        Binding("q,escape", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.coats = list(sprites.COATS)
        self.index = 0
        self.stage = Stage(self.draw)

    @property
    def coat(self) -> str:
        return self.coats[self.index]

    def compose(self) -> ComposeResult:
        yield self.stage

    def action_coat(self, step: int) -> None:
        self.index = (self.index + step) % len(self.coats)
        self.stage.redraw()

    def draw(self, canvas: Canvas) -> None:
        canvas.fill(0, 0, canvas.width, canvas.height, theme.ROOM_BG)
        title = f"{self.coat}  ({self.index + 1}/{len(self.coats)})    ←/→ coat   q quit"
        canvas.text(2, 0, title, theme.TEXT, bold=True)
        palette = sprites.COATS[self.coat]
        for py, pose in ((SIT_PY, "sit"), (LOAF_PY, "loaf")):
            for i, face in enumerate(sprites.FACES):
                x = 2 + i * COLUMN
                grid = sprites.cat(pose, face)
                canvas.sprite(x, py, grid, palette)
                canvas.text(x, _label_row(py, grid), f"{pose} {face}", theme.DIM)
        for i, (pose, face) in enumerate(SIDE_SHOWN):
            x = 2 + i * SIDE_COLUMN
            grid = sprites.cat(pose, face)
            canvas.sprite(x, SIDE_PY, grid, palette)
            canvas.text(x, _label_row(SIDE_PY, grid), f"{pose} {face}", theme.DIM)
        x, py, tallest = 2, PROPS_PY, 0
        for name, (grid, prop_palette) in sprites.PROPS.items():
            width = max(len(grid[0]), len(name))
            if x + width >= canvas.width:  # wrap onto another row
                x, py, tallest = 2, py + tallest + LABEL_PX, 0
            canvas.sprite(x, py, grid, prop_palette)
            canvas.text(x, _label_row(py, grid), name, theme.DIM)
            x += width + PROP_GAP
            tallest = max(tallest, len(grid))


def _label_row(py: int, grid: sprites.Grid) -> int:
    """The text row just under a sprite drawn at pixel row py."""
    return (py + len(grid) + 1) // 2
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -q`
Expected: `446 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/render/sprites.py src/pomo/gallery.py tests/test_sprites.py tests/test_gallery.py
git commit -m "feat: sprites for poop, the yarn ball, the string's feather and the tool cursors" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Drawing the care, and the Idle panel

**Files:**
- Modify: `src/pomo/render/theme.py` (append)
- Replace: `src/pomo/render/scene.py`
- Test: `tests/test_scene.py` (imports, and new tests at the end)

**Interfaces:**
- Consumes:
  - From Tasks 3–4: `RoomView.poops`, `.effects`, `.cursor`, `.ball`, `.string`, and the view dataclasses.
  - From Task 5: the sprites and `CURSORS`.
- Produces:
  - `scene.draw(canvas, timer, room_view, frame, idle=False)`.
  - `scene.room_point(col: float, row: float) -> tuple[float, float] | None`: `(column − 30, int(row × 2))`, or `None` over the panel.
  - `KEY_HINTS` gains `"1-5 tools  esc drop  i idle"`.
  - `IDLE_LABEL`, `IDLE_HINT`, `IDLE_TEXT`, `EFFECT_TEXT`.
  - Theme: `IDLE`, `STRING`, `EFFECT_COLORS`.
- **Draw order** (spec §7): floor props (bowl, poops, ball), cats, the string, the tool, then marks (z's, bubbles) and effects.

- [ ] **Step 1: Write the failing tests**

In `tests/test_scene.py`, change the imports:

Replace:

```python
from pomo.game.world import CatView, RoomView, RosterLine
```

with:

```python
from pomo.game.world import BallView, CatView, CursorView, EffectView, RoomView, RosterLine, StringView
```

Replace:

```python
    BLINK_EVERY, CLOCK_PY, CLOCK_X, PANEL_WIDTH, ROSTER_ROW, TWINKLE_FRAMES, blinking, draw,
```

with:

```python
    BLINK_EVERY, CLOCK_PY, CLOCK_X, PANEL_WIDTH, ROSTER_ROW, TWINKLE_FRAMES, blinking, draw, room_point,
```

Append to the end of `tests/test_scene.py`:

```python
def render_room(timer, **room) -> Canvas:
    canvas = Canvas(W, H, (0, 0, 0))
    draw(canvas, timer, RoomView(**room), 1)
    return canvas


def column_colours(canvas: Canvas, x: int, rows: range) -> set:
    return {canvas.pixel_at(x, py) for py in rows}


def test_the_idle_panel_hides_the_timer(timer):
    canvas = Canvas(W, H, (0, 0, 0))
    draw(canvas, timer, RoomView(roster=(RosterLine("Mango", 4, "content"),)), 1, idle=True)
    text = screen_text(canvas)
    for expected in ["● IDLE", "i to go back to pomodoro", "just hanging out", "Mango  ♥♥♥♥♡ content", "i idle"]:
        assert expected in text
    for gone in ["FOCUS", "pomodoro 1 of 4", "next:"]:
        assert gone not in text
    assert clock_ink(canvas) == set()


def test_the_key_hints_name_the_tools_and_idle(timer):
    assert "1-5 tools  esc drop  i idle" in screen_text(render(timer))


def test_poops_sit_on_the_floor(timer):
    canvas = render_room(timer, poops=((20.5, FLOOR),))  # 7 wide, so the left edge is column 17
    assert canvas.pixel_at(PANEL_WIDTH + 17, FLOOR - 1) == sprites.POOP_PALETTE["o"]
    assert canvas.pixel_at(PANEL_WIDTH + 20, FLOOR - 4) == sprites.POOP_PALETTE["o"]  # the tip


def test_the_ball_rolls_between_its_two_frames(timer):
    frames = [render_room(timer, ball=BallView(40.0, FLOOR, f)) for f in (0, 1)]
    spot = (PANEL_WIDTH + 38 + 1, FLOOR - 5 + 1)  # 5×5 yarn: left edge 37.5 → 38, top at FLOOR - 5
    assert frames[0].pixel_at(*spot) == sprites.YARN_PALETTE["r"]
    assert frames[1].pixel_at(*spot) == sprites.YARN_PALETTE["l"]


def test_the_string_hangs_from_the_ceiling_to_a_feather(timer):
    canvas = render_room(timer, string=StringView(anchor=40.0, tip_x=40.0, tip_y=20.0))
    assert column_colours(canvas, PANEL_WIDTH + 40, range(0, 20)) == {theme.STRING}
    assert canvas.pixel_at(PANEL_WIDTH + 40, 21) == sprites.TEASER_PALETTE["F"]


def test_a_swinging_string_leans_towards_its_tip(timer):
    canvas = render_room(timer, string=StringView(anchor=40.0, tip_x=50.0, tip_y=20.0))
    assert canvas.pixel_at(PANEL_WIDTH + 40, 0) == theme.STRING
    assert canvas.pixel_at(PANEL_WIDTH + 45, 10) == theme.STRING
    assert canvas.pixel_at(PANEL_WIDTH + 49, 19) in (theme.STRING, theme.ROOM_BG)
    assert canvas.pixel_at(PANEL_WIDTH + 50, 21) == sprites.TEASER_PALETTE["F"]


@pytest.mark.parametrize("tool", ["feed", "ball", "pet", "scoop"])
def test_the_tool_is_drawn_with_its_hotspot_on_the_pointer(timer, tool):
    grid, palette, (hx, hy) = sprites.CURSORS[tool]
    canvas = render_room(timer, cursor=CursorView(tool, 20.0, 30.0))
    assert canvas.pixel_at(PANEL_WIDTH + 20, 30) == palette[grid[hy][hx]]
    assert canvas.pixel_at(PANEL_WIDTH + 20 - hx, 30 - hy) == palette.get(grid[0][0], theme.ROOM_BG)


def test_the_hand_pats_while_it_is_on_a_cat(timer):
    still = render_room(timer, cursor=CursorView("pet", 20.0, 30.0))
    patting = render_room(timer, cursor=CursorView("pet", 20.0, 30.0, busy=True))
    top_row = [(PANEL_WIDTH + 16 + dx, 26) for dx in range(9)]  # hotspot (4, 4): the sprite's top row
    assert any(still.pixel_at(*p) != theme.ROOM_BG for p in top_row)
    assert all(patting.pixel_at(*p) == theme.ROOM_BG for p in top_row)  # the patting hand's top row is empty


def test_the_string_tool_has_no_sprite_of_its_own(timer):
    plain = render_room(timer)
    holding = render_room(timer, cursor=CursorView("string", 20.0, 30.0))
    assert all(plain.row_key(y) == holding.row_key(y) for y in range(H))


def test_the_tool_is_drawn_over_the_cats(timer):
    grid, palette, (hx, hy) = sprites.CURSORS["pet"]
    canvas = render_room(timer, cats=(MANGO,), cursor=CursorView("pet", 38.0, float(FLOOR - 8)))
    assert canvas.pixel_at(PANEL_WIDTH + 38, FLOOR - 8) == palette[grid[hy][hx]]


@pytest.mark.parametrize("kind, text", [("heart", "♥"), ("hiss", "#@!"), ("swat", "swat!")])
def test_effects_float_over_the_room(timer, kind, text):
    canvas = render_room(timer, cats=(MANGO,), effects=(EffectView(kind, 38.0, 30.0),))
    assert text in canvas.row_text(15)
    (segment,) = [s for s in canvas.row_segments(15) if text in s.text]
    assert segment.style.color == Color.from_rgb(*theme.EFFECT_COLORS[kind])


def test_an_effect_that_floated_off_the_top_is_gone(timer):
    canvas = render_room(timer, effects=(EffectView("heart", 38.0, -3.0),))
    assert "♥" not in screen_text(canvas)


@pytest.mark.parametrize("col, row, point", [
    (35, 10, (5.0, 20.0)),
    (35.4, 10.5, (5.0, 21.0)),  # a terminal that reports pixels: the lower half of the cell
    (PANEL_WIDTH, 0, (0.0, 0.0)),
    (PANEL_WIDTH - 1, 10, None),  # over the timer panel
])
def test_room_point_maps_the_pointer_into_the_room(col, row, point):
    assert room_point(col, row) == point
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_scene.py -q`
Expected: FAIL during collection with `ImportError: cannot import name 'room_point' from 'pomo.render.scene'`

- [ ] **Step 3: The new colours**

Append to the end of `src/pomo/render/theme.py`:

```python
# idle mode and the care tools
IDLE = hex_rgb("#bb9af7")
STRING = hex_rgb("#a9b1d6")
EFFECT_COLORS = {"heart": HEART, "hiss": STAGE_COLORS["furious"], "swat": STAGE_COLORS["pissy"]}
```

- [ ] **Step 4: Draw it all**

Replace all of `src/pomo/render/scene.py` with:

```python
"""The whole screen: the timer panel on the left, the cat room on the right (spec §6–§7).

Pure: the timer, a RoomView from the world and an animation frame number in, pixels
out. It never reads the clock and never changes the game. `room_point` goes the other
way, from where the mouse is on screen to where that is in the room.
"""

from __future__ import annotations

from collections.abc import Mapping

from pomo.game.playscape import Box, Playscape, layout
from pomo.game.world import BallView, CatView, CursorView, EffectView, RoomView, RosterLine, StringView
from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.render.font import draw_big, text_width
from pomo.render.theme import RGB
from pomo.timer import PomodoroTimer
from pomo.ui import view

PANEL_WIDTH = 30
TEXT_X = 2
PHASE_ROW, STATE_ROW = 1, 2
CLOCK_X, CLOCK_PY = 2, 8  # the 7-pixel clock covers text rows 4-7
BAR_ROW = 9
CLOCK_ROOM = PANEL_WIDTH - CLOCK_X - 1  # columns the clock may use
BAR_WIDTH = 25  # the same width as "18:42"
COUNT_ROW, NEXT_ROW = 11, 12
ROSTER_ROW = 14  # "cats", then one line per cat
ROSTER_HEARTS_X = TEXT_X + 7
ROSTER_STAGE_X = ROSTER_HEARTS_X + 6
KEY_HINTS = ("space start/pause   s skip", "r reset  +/- 5 min  q quit", "1-5 tools  esc drop  i idle")
IDLE_LABEL, IDLE_HINT, IDLE_TEXT = "● IDLE", "i to go back to pomodoro", "just hanging out"
IDLE_TEXT_ROW = 6  # where the clock would be
EFFECT_TEXT = {"heart": "♥", "hiss": "#@!", "swat": "swat!"}

BLINK_EVERY = 48  # frames: about every 6 s at 8 fps
BLINK_FRAMES = 2
STARS = ((2, 3), (9, 2), (8, 8))  # inside the window
TWINKLE_FRAMES = 12


def draw(canvas: Canvas, timer: PomodoroTimer, room_view: RoomView, frame: int, idle: bool = False) -> None:
    canvas.fill(0, 0, canvas.width, canvas.height, theme.ROOM_BG)
    _panel(canvas, timer, room_view.roster, idle)
    room = layout(max(0, canvas.width - PANEL_WIDTH), canvas.height * 2)
    _room(canvas, PANEL_WIDTH, room, room_view, frame)


def room_point(col: float, row: float) -> tuple[float, float] | None:
    """Where a pointer at (col, row) on screen is in the room: a column and a pixel row. None over the panel.
    Terminals that report the pointer finer than a cell give the half-cell too."""
    if col < PANEL_WIDTH:
        return None
    return float(int(col) - PANEL_WIDTH), float(int(row * 2))


def phase_color(timer: PomodoroTimer) -> RGB:
    if not timer.running:
        return theme.IDLE_CLOCK
    return theme.BREAK if timer.phase.is_break else theme.FOCUS


# --- timer panel ------------------------------------------------------------


def _panel(canvas: Canvas, timer: PomodoroTimer, roster: tuple[RosterLine, ...], idle: bool) -> None:
    canvas.fill(0, 0, PANEL_WIDTH, canvas.height, theme.PANEL_BG)
    if idle:
        _panel_text(canvas, PHASE_ROW, IDLE_LABEL, theme.IDLE, bold=True)
        _panel_text(canvas, STATE_ROW, IDLE_HINT, theme.DIM)
        _panel_text(canvas, IDLE_TEXT_ROW, IDLE_TEXT, theme.TEXT)
    else:
        _timer(canvas, timer)
    _roster(canvas, roster)
    first_hint_row = canvas.height - len(KEY_HINTS) - 1
    for i, hint in enumerate(KEY_HINTS):
        _panel_text(canvas, first_hint_row + i, hint, theme.DIM)


def _timer(canvas: Canvas, timer: PomodoroTimer) -> None:
    color = phase_color(timer)
    _panel_text(canvas, PHASE_ROW, view.phase_label(timer), color, bold=True)
    _panel_text(canvas, STATE_ROW, view.phase_state(timer), theme.DIM)
    clock = view.clock_text(timer.remaining())
    gap = 1 if text_width(clock) <= CLOCK_ROOM else 0  # 100+ minutes: close up so "120:00" still fits
    draw_big(canvas, CLOCK_X, CLOCK_PY, clock, color, gap)
    bar = view.progress_bar(timer, BAR_WIDTH)
    filled = bar.count("█")
    canvas.text(TEXT_X, BAR_ROW, bar[:filled], color)
    canvas.text(TEXT_X + filled, BAR_ROW, bar[filled:], theme.BAR_EMPTY)
    _panel_text(canvas, COUNT_ROW, view.count_line(timer), theme.TEXT)
    _panel_text(canvas, NEXT_ROW, view.next_line(timer), theme.DIM)


def _roster(canvas: Canvas, roster: tuple[RosterLine, ...]) -> None:
    if roster:
        _panel_text(canvas, ROSTER_ROW, "cats", theme.DIM)
    for i, line in enumerate(roster):
        row = ROSTER_ROW + 1 + i
        _panel_text(canvas, row, line.name[:6], theme.TEXT)
        hearts_end = canvas.text(ROSTER_HEARTS_X, row, "♥" * line.hearts, theme.HEART)
        canvas.text(hearts_end, row, "♡" * (5 - line.hearts), theme.HEART_EMPTY)
        canvas.text(ROSTER_STAGE_X, row, line.stage, theme.STAGE_COLORS[line.stage])


def _panel_text(canvas: Canvas, row: int, s: str, color: RGB, bold: bool = False) -> None:
    canvas.text(TEXT_X, row, s[: PANEL_WIDTH - TEXT_X - 1], color, bold=bold)


# --- cat room ---------------------------------------------------------------


def _room(canvas: Canvas, ox: int, room: Playscape, room_view: RoomView, frame: int) -> None:
    canvas.fill(ox, 0, room.width, canvas.height, theme.ROOM_BG)  # also trims a clock too wide for the panel
    _window(canvas, ox, room.window, frame)
    _cat_tree(canvas, ox, room)
    _shelf(canvas, ox, room)
    canvas.rect(ox, room.floor.y, room.width, 1, theme.FLOOR)
    canvas.sprite(ox + room.door.x, room.door.y, sprites.DOOR, sprites.DOOR_PALETTE)
    bowl = sprites.BOWL_FULL if room_view.bowl_full else sprites.BOWL_EMPTY
    canvas.sprite(ox + room.bowl.x, room.bowl.y, bowl, sprites.BOWL_PALETTE)
    for x, y in room_view.poops:
        _standing(canvas, ox, x, y, sprites.POOP, sprites.POOP_PALETTE)
    if room_view.ball is not None:
        _ball(canvas, ox, room_view.ball)
    cats = sorted(room_view.cats, key=lambda c: (c.feet, c.x))  # back (high up) to front (floor)
    drawn = [_cat(canvas, ox, cat, frame) for cat in cats]
    if room_view.string is not None:
        _string(canvas, ox, room_view.string)
    if room_view.cursor is not None:
        _cursor(canvas, ox, room_view.cursor)
    for cat, face, left, top, width in drawn:  # effects go over everything
        _cat_marks(canvas, cat, face, left, top, width, frame)
    for effect in room_view.effects:
        _effect(canvas, ox, effect)


def _window(canvas: Canvas, ox: int, w: Box, frame: int) -> None:
    x = ox + w.x
    canvas.rect(x, w.y, w.w, w.h, theme.WINDOW_FRAME)
    canvas.rect(x + 1, w.y + 1, w.w - 2, w.h - 2, theme.WINDOW_GLASS)
    canvas.rect(x + w.w // 2, w.y + 1, 1, w.h - 2, theme.WINDOW_FRAME)
    canvas.rect(x + 1, w.y + w.h // 2, w.w - 2, 1, theme.WINDOW_FRAME)
    canvas.rect(x - 1, w.y + w.h, w.w + 2, 1, theme.WINDOW_SILL)
    for i, (sx, sy) in enumerate(STARS):
        if (frame // TWINKLE_FRAMES + i) % 3:
            canvas.pixel(x + sx, w.y + sy, theme.STAR)


def _cat_tree(canvas: Canvas, ox: int, room: Playscape) -> None:
    post = room.post
    for y in range(post.y, post.y + post.h):
        canvas.rect(ox + post.x, y, post.w, 1, theme.SISAL if y % 2 else theme.SISAL_DARK)
    for platform in (room.tree_top, room.tree_mid):
        width = platform.x1 - platform.x0
        canvas.rect(ox + platform.x0, platform.y, width, 2, theme.PLATFORM)
        canvas.rect(ox + platform.x0, platform.y + 2, width, 1, theme.PLATFORM_EDGE)
    canvas.rect(ox + post.x - 5, room.floor.y - 2, post.w + 10, 2, theme.PLATFORM)  # base


def _shelf(canvas: Canvas, ox: int, room: Playscape) -> None:
    shelf = room.shelf
    canvas.rect(ox + shelf.x0, shelf.y, shelf.x1 - shelf.x0, 2, theme.SHELF)
    canvas.rect(ox + shelf.x0 + 2, shelf.y + 2, 1, 3, theme.SHELF_BRACKET)
    canvas.rect(ox + shelf.x1 - 3, shelf.y + 2, 1, 3, theme.SHELF_BRACKET)


def _standing(canvas: Canvas, ox: int, x: float, y: int, grid: sprites.Grid, palette: Mapping[str, RGB]) -> None:
    """A sprite centred on column x, standing on pixel row y."""
    canvas.sprite(ox + round(x - len(grid[0]) / 2), y - len(grid), grid, palette)


def _ball(canvas: Canvas, ox: int, ball: BallView) -> None:
    _standing(canvas, ox, ball.x, ball.y, sprites.YARN[ball.frame], sprites.YARN_PALETTE)


def _string(canvas: Canvas, ox: int, string: StringView) -> None:
    """A line from the ceiling above the mouse down to the swinging tip, with a feather on the end."""
    tip_y = round(string.tip_y)
    for py in range(tip_y):
        x = string.anchor + (string.tip_x - string.anchor) * py / tip_y
        canvas.pixel(ox + round(x), py, theme.STRING)
    canvas.sprite(ox + round(string.tip_x) - 1, tip_y, sprites.TEASER, sprites.TEASER_PALETTE)


def _cursor(canvas: Canvas, ox: int, cursor: CursorView) -> None:
    if cursor.tool not in sprites.CURSORS:
        return  # the string is drawn as itself
    grid, palette, (hx, hy) = sprites.CURSORS[cursor.tool]
    if cursor.tool == "pet" and cursor.busy:
        grid = sprites.HAND[1]
    canvas.sprite(ox + round(cursor.x) - hx, round(cursor.y) - hy, grid, palette)


def _effect(canvas: Canvas, ox: int, effect: EffectView) -> None:
    text = EFFECT_TEXT[effect.kind]
    canvas.text(ox + round(effect.x) - len(text) // 2, int(effect.y) // 2, text, theme.EFFECT_COLORS[effect.kind],
                bold=True)


def _cat(canvas: Canvas, ox: int, cat: CatView, frame: int) -> tuple[CatView, str, int, int, int]:
    face = "blink" if cat.face == "ok" and blinking(cat.name, frame) else cat.face
    grid = sprites.cat(cat.pose, face, cat.facing)
    width = len(grid[0])
    left = ox + round(cat.x - width / 2)
    top = cat.feet - len(grid)
    canvas.sprite(left, top, grid, sprites.COATS[cat.coat])
    return cat, face, left, top, width


def _cat_marks(canvas: Canvas, cat: CatView, face: str, left: int, top: int, width: int, frame: int) -> None:
    """A sleeping cat's z, or its bubble."""
    if face == "sleep":
        step = (frame // 6) % 3
        canvas.text(left + width - 2 + step % 2, top // 2 - step, "z", theme.SLEEP_Z, bold=True)
    elif cat.bubble:
        canvas.text(left + width // 2 - 1, top // 2 - 1, cat.bubble, theme.TEXT, bold=True)


def blinking(name: str, frame: int) -> bool:
    offset = sum(map(ord, name))  # stable per cat (hash() changes every run)
    return (frame + offset) % BLINK_EVERY < BLINK_FRAMES
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -q`
Expected: `467 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/render/theme.py src/pomo/render/scene.py tests/test_scene.py
git commit -m "feat: draw poops, the ball, the string, the tool at the pointer, effects, and the Idle panel" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: The toolbar, the mouse and Idle in the app

**Files:**
- Create: `src/pomo/ui/toolbar.py`
- Replace: `src/pomo/ui/stage.py`, `src/pomo/ui/view.py`, `src/pomo/ui/app.py`, `src/pomo/cli.py`, `README.md`
- Test: `tests/test_app.py`, `tests/test_stage.py`, `tests/test_view.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: everything above:
  - `World.hold`/`point`/`click`/`leave`/`take_news`/`feed`, `world.tool` and `world.mode`.
  - `locked`.
  - `Session.enter_idle`/`leave_idle`/`idle`.
  - `scene.draw(..., idle=)` and `scene.room_point`.
- Produces:
  - `Toolbar`:
    - `.show(held, locked, idle)`, which changes nothing when nothing changed.
    - Messages `Toolbar.Picked(tool)` and `Toolbar.ModeToggled`.
    - Button ids `#tool-feed`, `#tool-ball`, `#tool-string`, `#tool-pet`, `#tool-scoop` and `#mode`.
  - `ToolButton` (never focused), `TOOLS`, `MODE_LABELS`.
  - `Stage.Pointer(col, row)`, `Stage.Pressed(col, row)`, `Stage.Left()`.
  - `PomoApp(..., idle: bool = False)`:
    - Bindings: `i` → `toggle_idle`, `1`–`5` → `tool('<name>')`, `escape` → `drop_tool`.
    - `TimerScreen.toolbar`.
  - `view`: `LOCKED`, `IDLE_ON`, `IDLE_OFF`, `TOY_NAMES`, and `describe()` for `Fed`, `Petted` (`hiss`, `swat`) and `Played`.
  - `pomo --idle`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_app.py`, change the imports:

Replace:

```python
from pomo.game.behavior import Mode
from pomo.render import sprites, theme
from pomo.render.scene import CLOCK_PY, CLOCK_X, PANEL_WIDTH
from pomo.timer import Phase
from pomo.ui.app import PomoApp
from pomo.ui.dialogs import ConfirmScreen
```

with:

```python
from pomo.game.behavior import Mode
from pomo.game.tools import Tool
from pomo.render import sprites, theme
from pomo.render.scene import CLOCK_PY, CLOCK_X, PANEL_WIDTH
from pomo.timer import Phase
from pomo.ui import view
from pomo.ui.app import PomoApp
from pomo.ui.dialogs import ConfirmScreen
from pomo.ui.stage import Stage
from pomo.ui.toolbar import ToolButton
```

Let `make_app` start in Idle:

Replace:

```python
def make_app(**config):
    clock, notifier = FakeClock(), FakeNotifier()
    return PomoApp(Config(**config), clock, notifier, rng=random.Random(0)), clock, notifier
```

with:

```python
def make_app(idle=False, **config):
    clock, notifier = FakeClock(), FakeNotifier()
    return PomoApp(Config(**config), clock, notifier, rng=random.Random(0), idle=idle), clock, notifier
```

The stage is a row shorter now that the toolbar sits under the message line:

Replace:

```python
async def test_the_stage_fills_the_screen_above_the_message_line():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        canvas = app.main.stage.canvas
        assert (canvas.width, canvas.height) == (100, 29)
```

with:

```python
async def test_the_stage_fills_the_screen_above_the_message_line_and_toolbar():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        canvas = app.main.stage.canvas
        assert (canvas.width, canvas.height) == (100, 28)
```

Replace:

```python
        assert (app.world.scape.width, app.world.scape.height) == (70, 58)
```

with:

```python
        assert (app.world.scape.width, app.world.scape.height) == (70, 56)
```

An unchanged tick must not repaint the toolbar either:

Replace:

```python
        for widget in (app.main.stage, app.main.query_one("#message")):
```

with:

```python
        for widget in (app.main.stage, app.main.query_one("#message"), *app.main.toolbar.query(ToolButton)):
```

Append to the end of `tests/test_app.py`:

```python
# --- the toolbar and the care tools (milestone 4) -------------------------------
# At 100×30 the room is 70×56: its column x is screen column 30 + x, and its pixel
# row y is on screen row y // 2. Mango starts on the floor (pixel row 55) at x = 38.

def label(app, button_id):
    return str(app.main.toolbar.query_one(f"#{button_id}", ToolButton).label)


def on_room(x, y):
    """Screen offset of room column x, pixel row y."""
    return (PANEL_WIDTH + x, y // 2)


async def test_the_toolbar_offers_every_tool_and_the_mode():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        assert [label(app, f"tool-{t}") for t in ("feed", "ball", "string", "pet", "scoop")] == [
            "1 🍗 Feed", "2 🧶 Ball", "3 🧵 String", "4 ✋ Pet", "5 🧹 Scoop"]
        assert label(app, "mode") == "🍅 Pomodoro"


async def test_number_keys_pick_tools_and_escape_puts_them_down():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("2")
        assert app.world.tool is Tool.BALL
        assert app.main.toolbar.query_one("#tool-ball").has_class("-held")
        await pilot.press("4")
        assert app.world.tool is Tool.PET
        assert not app.main.toolbar.query_one("#tool-ball").has_class("-held")
        await pilot.press("escape")
        assert app.world.tool is None


async def test_clicking_a_toolbar_button_picks_its_tool():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.click("#tool-string")
        assert app.world.tool is Tool.STRING


async def test_a_focus_locks_every_tool_but_the_scoop_and_says_why():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        assert label(app, "tool-ball") == "2 🔒 Ball"
        assert app.main.toolbar.query_one("#tool-ball").has_class("-locked")
        assert label(app, "tool-scoop") == "5 🧹 Scoop"
        await pilot.press("2")
        assert app.world.tool is None
        assert text(app, "message") == view.LOCKED
        await pilot.press("5")
        assert app.world.tool is Tool.SCOOP


async def test_starting_a_focus_puts_the_toy_down():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("3", "space")
        assert app.world.tool is None


async def test_the_tools_unlock_on_the_break():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(25 * MIN)
        app.tick()
        assert label(app, "tool-ball") == "2 🧶 Ball"
        await pilot.press("2")
        assert app.world.tool is Tool.BALL


async def test_pressing_1_twice_fills_the_bowl():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        app.world.bowl_full = False
        await pilot.press("1")
        assert not app.world.bowl_full
        await pilot.press("1")
        assert app.world.bowl_full
        assert text(app, "message") == "Kibble's in the bowl."


async def test_clicking_the_bowl_with_kibble_fills_it():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        app.world.bowl_full = False
        await pilot.press("1")
        bowl = app.world.scape.bowl
        await pilot.click(Stage, offset=on_room(bowl.x + 3, bowl.y))
        assert app.world.bowl_full


async def test_the_ball_drops_where_you_click():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("2")
        await pilot.click(Stage, offset=on_room(30, 20))
        assert (app.world.ball.x, app.world.ball.y) == (30, 20)


async def test_the_tool_follows_the_mouse_over_the_room_and_hides_over_the_panel():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("4")
        await pilot.hover(Stage, offset=on_room(20, 20))
        assert app.world.pointer == (20, 20)
        grid, palette, (hx, hy) = sprites.CURSORS["pet"]
        assert app.main.stage.canvas.pixel_at(PANEL_WIDTH + 20, 20) == palette[grid[hy][hx]]
        await pilot.hover(Stage, offset=(10, 10))
        assert app.world.pointer is None


async def test_stroking_mango_with_the_mouse_pets_him():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        mango = app.world.cats[0]
        mango.needs["affection"] = 60
        await pilot.press("4")
        for x in range(33, 40):  # six cells across his back
            await pilot.hover(Stage, offset=on_room(x, 48))
        assert mango.needs["affection"] == 35
        assert [e.kind for e in app.world.view().effects] == ["heart"]


async def test_a_hiss_makes_the_message_line():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        mango = app.world.cats[0]
        mango.mood = 30
        await pilot.press("4")
        for x in range(33, 40):
            await pilot.hover(Stage, offset=on_room(x, 48))
        assert text(app, "message") == "Mango hisses at your hand. Not now."


async def test_i_switches_to_idle_and_back():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("i")
        assert app.session.idle
        assert "● IDLE" in on_screen(app)
        assert "just hanging out" in on_screen(app)
        assert clock_value(app) == ""
        assert label(app, "mode") == "💤 Idle"
        assert text(app, "message") == view.IDLE_ON
        await pilot.press("i")
        assert not app.session.idle
        assert clock_value(app) == "25:00"
        assert text(app, "message") == view.IDLE_OFF


async def test_the_mode_button_switches_to_idle():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.click("#mode")
        assert app.session.idle


async def test_going_idle_mid_focus_asks_first_and_costs_25():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space", "i")
        assert isinstance(app.screen, ConfirmScreen)
        assert "Switch to Idle in the middle of a focus?" in app.screen.question
        await pilot.press("n")
        assert not app.session.idle and app.session.timer.running
        await pilot.press("i", "y")
        assert app.session.idle
        assert app.world.cats[0].mood == 55


async def test_idle_puts_the_timer_keys_away_and_unlocks_every_tool():
    app, clock, _ = make_app(idle=True)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space", "plus", "s", "r")
        assert not isinstance(app.screen, ConfirmScreen)
        clock.advance(30 * MIN)
        app.tick()
        assert not app.session.timer.started
        assert app.session.timer.remaining() == 25 * MIN
        await pilot.press("2")
        assert app.world.tool is Tool.BALL


async def test_the_idle_flag_starts_in_idle_mode():
    app, _, _ = make_app(idle=True)
    async with app.run_test(size=SIZE):
        assert app.session.idle
        assert "● IDLE" in on_screen(app)


async def test_a_stale_yes_to_idle_goes_idle_for_free_once_the_focus_is_over():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space", "i")
        clock.advance(25 * MIN)
        app.tick()  # the focus finished while the dialog was up: +10
        await pilot.press("y")
        assert app.session.idle
        assert app.world.cats[0].mood == 90


async def test_tool_keys_are_ignored_while_a_dialog_is_open():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("5", "space", "s", "escape")  # s asks; escape answers no
        assert app.world.tool is Tool.SCOOP
        await pilot.press("s", "1", "i")
        assert isinstance(app.screen, ConfirmScreen)
        assert app.world.tool is Tool.SCOOP
        assert not app.session.idle


async def test_a_tick_that_fires_during_shutdown_does_nothing():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        pass
    app.tick()  # the screen has been taken apart: this used to raise NoMatches, now and then, on quit
```

In `tests/test_stage.py`, add the import:

Replace:

```python
from textual.app import App, ComposeResult
```

with:

```python
from textual import events
from textual.app import App, ComposeResult
```

and append to the end of `tests/test_stage.py`:

```python
class MouseApp(StageApp):
    """Records what the stage says about the mouse."""

    def __init__(self):
        super().__init__()
        self.heard = []

    def on_stage_pointer(self, message: Stage.Pointer) -> None:
        self.heard.append(("Pointer", message.col, message.row))

    def on_stage_pressed(self, message: Stage.Pressed) -> None:
        self.heard.append(("Pressed", message.col, message.row))

    def on_stage_left(self, message: Stage.Left) -> None:
        self.heard.append(("Left",))


async def test_the_stage_reports_the_mouse_in_its_own_cells():
    app = MouseApp()
    async with app.run_test(size=(20, 6)) as pilot:
        await pilot.hover(Stage, offset=(5, 2))
        await pilot.click(Stage, offset=(7, 3))
        await pilot.pause()
        assert ("Pointer", 5, 2) in app.heard
        assert ("Pressed", 7, 3) in app.heard


async def test_the_stage_says_when_the_mouse_leaves():
    app = MouseApp()
    async with app.run_test(size=(20, 6)) as pilot:
        await pilot.hover(Stage, offset=(5, 2))
        app.stage.post_message(events.Leave(app.stage))
        await pilot.pause()
        assert app.heard[-1] == ("Left",)
```

In `tests/test_view.py`, change the import:

Replace:

```python
from pomo.game.events import FocusCompleted, RuleBreak, RuleKind, SetCompleted
```

with:

```python
from pomo.game.events import Fed, FocusCompleted, Petted, Played, RuleBreak, RuleKind, SetCompleted
```

and append to the end of `tests/test_view.py`:

```python
@pytest.mark.parametrize("event, text", [
    (Fed(), "Kibble's in the bowl."),
    (Fed(already_full=True), "The bowl is already full."),
    (Petted("Mango", "hiss"), "Mango hisses at your hand. Not now."),
    (Petted("Mango", "swat"), "Mango swats your hand. That's enough petting."),
    (Played("Mango", "ball"), "Mango had a good play with the yarn ball."),
    (Played("Mango", "string"), "Mango had a good play with the string."),
])
def test_describe_what_happens_in_the_room(event, text):
    assert view.describe(event) == text


@pytest.mark.parametrize("how", ["purr", "tolerate"])
def test_a_happy_stroke_needs_no_words(how):
    assert view.describe(Petted("Mango", how)) is None
```

Append to the end of `tests/test_cli.py`:

```python
def test_idle_flag_starts_the_app_in_idle_mode(launched):
    cli.main([])
    cli.main(["--idle"])
    assert [app.session.idle for app in launched] == [False, True]


def test_help_mentions_idle_and_the_tool_keys(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    assert "--idle" in out
    assert "i  idle mode" in out and "1-5" in out
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_app.py tests/test_stage.py tests/test_view.py tests/test_cli.py -q`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.ui.toolbar'`

- [ ] **Step 3: The toolbar**

Create `src/pomo/ui/toolbar.py`:

```python
"""The care toolbar under the message line (spec §5.2, §6): a button per tool, and Pomodoro ↔ Idle."""

from __future__ import annotations

from collections.abc import Set

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Button

from pomo.game.tools import Tool

TOOLS = (  # tool, key, icon, name
    (Tool.FEED, "1", "🍗", "Feed"),
    (Tool.BALL, "2", "🧶", "Ball"),
    (Tool.STRING, "3", "🧵", "String"),
    (Tool.PET, "4", "✋", "Pet"),
    (Tool.SCOOP, "5", "🧹", "Scoop"),
)
MODE_LABELS = {False: "🍅 Pomodoro", True: "💤 Idle"}
LOCK = "🔒"


class ToolButton(Button, can_focus=False):
    """Never takes keyboard focus, so space and the number keys always reach the app."""


class Toolbar(Horizontal):
    DEFAULT_CSS = """
    Toolbar { height: 1; background: #1a1c28; padding: 0 1; }
    Toolbar ToolButton { min-width: 0; margin-right: 1; }
    Toolbar ToolButton.-held { background: $primary; text-style: bold; }
    Toolbar ToolButton.-locked { color: $text-muted; }
    Toolbar #mode { dock: right; margin-right: 0; }
    """

    class Picked(Message):
        def __init__(self, tool: Tool) -> None:
            super().__init__()
            self.tool = tool

    class ModeToggled(Message):
        """The Pomodoro/Idle button was clicked."""

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._shown: tuple | None = None

    def compose(self) -> ComposeResult:
        for tool, key, icon, name in TOOLS:
            yield ToolButton(f"{key} {icon} {name}", id=f"tool-{tool.value}", compact=True)
        yield ToolButton(MODE_LABELS[False], id="mode", compact=True)

    def show(self, held: Tool | None, locked: Set[Tool], idle: bool) -> None:
        """Mark the tool in hand and the locked ones. Touches nothing if nothing changed."""
        state = (held, frozenset(locked), idle)
        if state == self._shown:
            return
        self._shown = state
        for tool, key, icon, name in TOOLS:
            button = self.query_one(f"#tool-{tool.value}", ToolButton)
            button.label = f"{key} {LOCK if tool in locked else icon} {name}"
            button.set_class(tool is held, "-held")
            button.set_class(tool in locked, "-locked")
        self.query_one("#mode", ToolButton).label = MODE_LABELS[idle]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "mode":
            self.post_message(self.ModeToggled())
        else:
            self.post_message(self.Picked(Tool(event.button.id.removeprefix("tool-"))))
```

- [ ] **Step 4: The stage reports the mouse**

Replace all of `src/pomo/ui/stage.py` with:

```python
"""A widget that shows a Canvas and repaints only the rows that changed (spec §7).

It also reports the mouse, in its own cells, for the app to turn into tool commands.
"""

from __future__ import annotations

from collections.abc import Callable

from textual import events
from textual.geometry import Region
from textual.message import Message
from textual.strip import Strip
from textual.widget import Widget

from pomo.render.canvas import Canvas
from pomo.render.theme import ROOM_BG


class Stage(Widget):
    DEFAULT_CSS = "Stage { width: 1fr; height: 1fr; }"

    class Pointer(Message):
        """The mouse moved to (col, row). Terminals that report pixels give fractions of a cell."""

        def __init__(self, col: float, row: float) -> None:
            super().__init__()
            self.col, self.row = col, row

    class Pressed(Message):
        """A click at (col, row)."""

        def __init__(self, col: float, row: float) -> None:
            super().__init__()
            self.col, self.row = col, row

    class Left(Message):
        """The mouse left the stage."""

    def __init__(self, draw: Callable[[Canvas], None], *, id: str | None = None) -> None:
        super().__init__(id=id)
        self._draw = draw
        self._canvas = Canvas(0, 0, ROOM_BG)
        self._keys: list[tuple] = []

    @property
    def canvas(self) -> Canvas:
        """The last frame drawn."""
        return self._canvas

    def redraw(self) -> None:
        width, height = self.size.width, self.size.height
        canvas = Canvas(width, height, ROOM_BG)
        self._draw(canvas)
        keys = [canvas.row_key(y) for y in range(height)]
        resized = (width, height) != (self._canvas.width, self._canvas.height)
        changed = [y for y in range(height) if resized or keys[y] != self._keys[y]]
        self._canvas, self._keys = canvas, keys
        if resized:
            self.refresh()
        else:
            for y in changed:
                self.refresh(Region(0, y, width, 1))

    def on_resize(self) -> None:
        self.redraw()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        self.post_message(self.Pointer(event.pointer_x, event.pointer_y))

    def on_click(self, event: events.Click) -> None:
        self.post_message(self.Pressed(event.pointer_x, event.pointer_y))

    def on_leave(self, event: events.Leave) -> None:
        self.post_message(self.Left())

    def render_line(self, y: int) -> Strip:
        if y >= self._canvas.height:
            return Strip.blank(self.size.width)
        return Strip(self._canvas.row_segments(y), self._canvas.width)
```

- [ ] **Step 5: The messages**

Replace all of `src/pomo/ui/view.py` with:

```python
"""Pure text for the timer screen. No Textual here, so it's trivial to test."""

from __future__ import annotations

import math

from pomo.game.balance import PENALTIES
from pomo.game.events import Event, Fed, Petted, Played, RuleBreak, RuleKind, SetCompleted
from pomo.session import Action
from pomo.timer import Phase, PomodoroTimer, Transition

PHASE_NAMES = {Phase.FOCUS: "FOCUS", Phase.SHORT_BREAK: "SHORT BREAK", Phase.LONG_BREAK: "LONG BREAK"}
NEXT_NAMES = {Phase.FOCUS: "focus", Phase.SHORT_BREAK: "break", Phase.LONG_BREAK: "long break"}
RULE_TEXT = {
    RuleKind.ABANDON_FOCUS: "Focus abandoned.",
    RuleKind.SKIP_BREAK: "Break skipped.",
    RuleKind.LONG_PAUSE: "That pause ran long.",
}
MAX_DOTS = 8  # keeps the count line inside the 30-column panel
TOY_NAMES = {"ball": "yarn ball", "string": "string"}
LOCKED = "Shh, the cats are napping. During a focus only the scoop works."
IDLE_ON = "Idle mode: no timer, and every tool works. Press i to go back."
IDLE_OFF = "Back to pomodoro. Press space to start."


def clock_text(seconds: float) -> str:
    """MM:SS, rounded up so it reads 25:00 until a whole second has passed and 00:00 only at the end."""
    total = math.ceil(max(0.0, seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def phase_label(timer: PomodoroTimer) -> str:
    return f"● {PHASE_NAMES[timer.phase]}"


def phase_state(timer: PomodoroTimer) -> str:
    """Shown under the phase name while the timer isn't running."""
    if timer.running:
        return ""
    return "paused" if timer.started else "space to start"


def progress_bar(timer: PomodoroTimer, width: int) -> str:
    done = 1.0 - timer.remaining() / timer.length if timer.length else 1.0
    filled = round(min(1.0, max(0.0, done)) * width)
    return "█" * filled + "░" * (width - filled)


def count_line(timer: PomodoroTimer) -> str:
    total = timer.settings.long_every
    done = timer.focus_in_set
    dots = "●" * done + "○" * (total - done) if total <= MAX_DOTS else ""
    if timer.phase is Phase.FOCUS:
        return f"pomodoro {done + 1} of {total}  {dots}".rstrip()
    return f"{done} of {total} done  {dots}".rstrip()


def next_line(timer: PomodoroTimer) -> str:
    upcoming = timer.next_phase()
    minutes = timer.base_length(upcoming) / 60
    return f"next: {minutes:g} min {NEXT_NAMES[upcoming]}"


def describe(event: Event) -> str | None:
    """The message-line text for an event, if it deserves one."""
    match event:
        case RuleBreak(kind=kind):
            return f"{RULE_TEXT[kind]} The cats will remember (−{PENALTIES[kind]})."
        case Transition(completed=True, ended=Phase.FOCUS):
            return "Focus complete. Time for a break!"
        case Transition(completed=True):
            return "Break's over. Back to focus."
        case SetCompleted():
            return "A full set with no rules broken. Bonus!"
        case Fed(already_full=True):
            return "The bowl is already full."
        case Fed():
            return "Kibble's in the bowl."
        case Petted(name=name, how="hiss"):
            return f"{name} hisses at your hand. Not now."
        case Petted(name=name, how="swat"):
            return f"{name} swats your hand. That's enough petting."
        case Played(name=name, toy=toy):
            return f"{name} had a good play with the {TOY_NAMES[toy]}."
    return None


def confirm_question(timer: PomodoroTimer, action: Action, cost: RuleKind) -> str:
    question = {
        Action.SKIP: "Skip your break?" if timer.phase.is_break else "Skip this focus?",
        Action.RESET: "Restart this focus from the top?",
        Action.QUIT: "Quit in the middle of a focus?",
        Action.IDLE: "Switch to Idle in the middle of a focus?",
    }[action]
    return f"{question} The cats will be upset (−{PENALTIES[cost]})."
```

- [ ] **Step 6: Wire it into the app**

Replace all of `src/pomo/ui/app.py` with:

```python
"""The Textual app: the timer panel and the cat room on one canvas, a message line, and the toolbar."""

from __future__ import annotations

import random
from collections.abc import Callable, Iterable

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static

from pomo.awake import KeepsAwake, NoKeepAwake
from pomo.clock import Clock
from pomo.config import Config
from pomo.game.cat import Cat, Trait
from pomo.game.events import Event
from pomo.game.playscape import MIN_HEIGHT, MIN_WIDTH
from pomo.game.tools import Tool, locked
from pomo.game.world import World, mode_for
from pomo.notify import Notifies, ping_for
from pomo.render import scene
from pomo.render.canvas import Canvas
from pomo.session import Action, Session
from pomo.timer import TimerSettings, Transition
from pomo.ui import view
from pomo.ui.dialogs import ConfirmScreen
from pomo.ui.stage import Stage
from pomo.ui.toolbar import TOOLS, Toolbar

TICK_S = 1 / 8  # 8 fps: the session ticks and the scene redraws together
MESSAGE_TTL_S = 10.0
WARNING_TTL_S = 60.0  # startup warnings are toasts: they wrap in full and outlive the message line
TIMER_ACTIONS = {"toggle", "adjust", "skip", "reset"}  # put away in Idle mode
BLOCKED_WHILE_CONFIRMING = TIMER_ACTIONS | {"request_quit", "tool", "drop_tool", "toggle_idle"}


class TimerScreen(Screen):
    DEFAULT_CSS = """
    TimerScreen { layout: vertical; }
    #message { height: 1; padding: 0 2; color: $warning; background: #1a1c28; }
    """

    def __init__(self, draw: Callable[[Canvas], None]) -> None:
        super().__init__()
        self._draw = draw
        self._shown_message: str | None = None

    def compose(self) -> ComposeResult:
        yield Stage(self._draw, id="stage")
        yield Static(id="message")
        yield Toolbar(id="toolbar")

    @property
    def stage(self) -> Stage:
        return self.query_one(Stage)

    @property
    def toolbar(self) -> Toolbar:
        return self.query_one(Toolbar)

    def show(self, message: str) -> None:
        self.stage.redraw()
        if message != self._shown_message:  # an unchanged tick must repaint nothing
            self._shown_message = message
            self.query_one("#message", Static).update(message, layout=False)  # fixed height: no layout pass


class PomoApp(App[None]):
    TITLE = "pomo"
    # The palette's "Quit" would exit mid-focus without the confirm dialog (spec §3.2).
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("space", "toggle", "Start/Pause"),
        Binding("s", "skip", "Skip"),
        Binding("r", "reset", "Reset"),
        Binding("plus", "adjust(5)", "+5 min"),
        Binding("minus", "adjust(-5)", "-5 min"),
        Binding("i", "toggle_idle", "Idle"),
        *(Binding(key, f"tool('{tool.value}')", name, show=False) for tool, key, _, name in TOOLS),
        Binding("escape", "drop_tool", "Put the tool down", show=False),
        Binding("q,ctrl+q", "request_quit", "Quit", key_display="q", priority=True),
    ]

    def __init__(
        self,
        config: Config,
        clock: Clock,
        notifier: Notifies,
        *,
        warnings: list[str] | None = None,
        keep_awake: KeepsAwake | None = None,
        rng: random.Random | None = None,
        idle: bool = False,
    ) -> None:
        super().__init__()
        self.config = config
        self.clock = clock
        self.notifier = notifier
        self.keep_awake = keep_awake or NoKeepAwake()
        self.session = Session(
            TimerSettings.from_minutes(config.focus, config.short_break, config.long_break, config.long_every),
            clock,
        )
        if idle:
            self.session.enter_idle()  # free: nothing has started
        self.world = World([Cat("Mango", "tabby", Trait.CLINGY)], rng or random.Random())  # spec §4: a new save
        self.frame = 0
        self._last_tick = clock.now()
        self.main = TimerScreen(self.draw_scene)
        self.confirming = False
        self._transitions = 0  # every phase change bumps this, so a dialog can tell it went stale
        self._warnings = list(warnings or [])
        self._message = ""
        self._message_at = 0.0

    def get_default_screen(self) -> Screen:
        return self.main

    def on_ready(self) -> None:
        # on_ready, not on_mount: the timer screen's widgets exist by now.
        for warning in self._warnings:
            self.notify(warning, title="pomo", severity="warning", timeout=WARNING_TTL_S)
        self.refresh_view()
        self.set_interval(TICK_S, self.tick)

    def tick(self) -> None:
        if not self.is_running:
            return  # quitting: the interval can still fire while the screen is taken apart
        now = self.clock.now()
        dt, self._last_tick = now - self._last_tick, now
        self.frame += 1
        self.handle(self.session.tick())
        self._sync_mode()
        self.world.tick(dt)
        self._report(self.world.take_news())
        self.refresh_view()

    def draw_scene(self, canvas: Canvas) -> None:
        # The room on screen decides the geometry; below the minimum the cats keep the minimum room.
        room_w, room_h = canvas.width - scene.PANEL_WIDTH, canvas.height * 2
        self.world.fit(max(MIN_WIDTH, room_w), max(MIN_HEIGHT, room_h))
        scene.draw(canvas, self.session.timer, self.world.view(), self.frame, idle=self.session.idle)

    def handle(self, events: list[Event]) -> None:
        self.world.apply(events)
        self._transitions += sum(isinstance(e, Transition) for e in events)
        finished = [e for e in events if isinstance(e, Transition) and e.completed]
        if finished:
            # A sleep/wake jump can finish several phases in one tick: ping once, for the latest.
            self.notifier.send(ping_for(finished[-1], self.config))
        self._report(events)

    def _report(self, events: Iterable[Event]) -> None:
        for event in events:
            text = view.describe(event)
            if text:
                self.show_message(text)

    def show_message(self, text: str) -> None:
        self._message = text
        self._message_at = self.clock.now()

    def refresh_view(self) -> None:
        if self._message and self.clock.now() - self._message_at > MESSAGE_TTL_S:
            self._message = ""
        self._sync_mode()
        self.main.toolbar.show(self.world.tool, {t for t in Tool if locked(t, self.world.mode)}, self.session.idle)
        self.main.show(self._message)
        # A sleeping Mac stops the clock, so stay awake exactly while a phase runs.
        self.keep_awake.hold(self.session.timer.running)

    def _sync_mode(self) -> None:
        timer = self.session.timer
        self.world.set_mode(mode_for(timer.phase, timer.started, self.session.idle))

    def on_unmount(self) -> None:
        self.keep_awake.hold(False)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        if self.confirming and action in BLOCKED_WHILE_CONFIRMING:
            return False
        return not (self.session.idle and action in TIMER_ACTIONS)

    # --- the timer -----------------------------------------------------------------

    def action_toggle(self) -> None:
        self.session.toggle()
        self.refresh_view()

    def action_adjust(self, minutes: int) -> None:
        self.session.adjust(minutes)
        self.refresh_view()

    def action_skip(self) -> None:
        self._guarded(Action.SKIP, lambda: self._apply(self.session.skip()))

    def action_reset(self) -> None:
        self._guarded(Action.RESET, lambda: self._apply(self.session.reset()))

    def action_request_quit(self) -> None:
        self._guarded(Action.QUIT, self._quit)

    def action_toggle_idle(self) -> None:
        if self.session.idle:
            self.session.leave_idle()
            self.show_message(view.IDLE_OFF)
            self.refresh_view()
        else:
            self._guarded(Action.IDLE, self._go_idle)

    def _go_idle(self) -> None:
        events = self.session.enter_idle()
        self.handle(events)
        if not events:  # a rule break's message matters more
            self.show_message(view.IDLE_ON)
        self.refresh_view()

    def _apply(self, events: list[Event]) -> None:
        self.handle(events)
        self.refresh_view()

    def _quit(self) -> None:
        self.handle(self.session.quit())
        self.exit()

    def _guarded(self, action: Action, perform: Callable[[], None]) -> None:
        """Ask first when the action breaks a rule. A 'yes' that arrives after the phase moved on is stale."""
        cost = self.session.rule_cost(action)
        if cost is None:
            perform()
            return
        asked_at = self._transitions
        self.confirming = True

        def answered(ok: bool | None) -> None:
            self.confirming = False
            if not ok:
                return
            if self._transitions == asked_at:
                perform()
            elif action in (Action.QUIT, Action.IDLE):
                self._guarded(action, perform)  # still wants it: do it now if it's free, else ask at today's price
            else:
                done = "skipped" if action is Action.SKIP else "reset"
                self.show_message(f"The phase changed while you were deciding, so nothing was {done}.")
                self.refresh_view()

        self.push_screen(ConfirmScreen(view.confirm_question(self.session.timer, action, cost)), answered)

    # --- the care tools ------------------------------------------------------------

    def action_tool(self, name: str) -> None:
        if not self.world.hold(Tool(name)):
            self.show_message(view.LOCKED)
        self._after_hand()

    def action_drop_tool(self) -> None:
        self.world.hold(None)
        self._after_hand()

    def on_toolbar_picked(self, message: Toolbar.Picked) -> None:
        if not self.confirming:
            self.action_tool(message.tool.value)

    def on_toolbar_mode_toggled(self, message: Toolbar.ModeToggled) -> None:
        if not self.confirming:
            self.action_toggle_idle()

    def on_stage_pointer(self, message: Stage.Pointer) -> None:
        point = scene.room_point(message.col, message.row)
        if point is None:
            self.world.leave()  # over the timer panel
        else:
            self.world.point(*point)
        self._after_hand()

    def on_stage_pressed(self, message: Stage.Pressed) -> None:
        point = scene.room_point(message.col, message.row)
        if point is not None:
            self.world.click(*point)
        self._after_hand()

    def on_stage_left(self, message: Stage.Left) -> None:
        self.world.leave()
        self._after_hand()

    def _after_hand(self) -> None:
        self._report(self.world.take_news())
        self.refresh_view()
```

- [ ] **Step 7: The `--idle` flag**

Replace all of `src/pomo/cli.py` with:

```python
"""`pomo` command line: flags → config → app."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from pomo import __version__
from pomo.awake import keep_awake
from pomo.clock import RealClock
from pomo.config import ConfigError, load_config, permission_warning, with_overrides
from pomo.gallery import GalleryApp
from pomo.notify import Notifier, NullNotifier
from pomo.paths import config_path, log_path
from pomo.ui.app import PomoApp

DESCRIPTION = (
    "A pomodoro timer for your terminal, with cats. "
    "Pings your desktop, and your phone via ntfy, when each phase ends."
)
EPILOG = """\
keys:
  space  start / pause        s  skip phase        r  reset phase
  + / -  add / remove 5 min   i  idle mode         q  quit
  1-5    pick a care tool: feed, ball, string, pet, scoop     esc  put it down

config file (all keys optional), default ~/.config/pomo/config.toml:
  ntfy_server = "https://ntfy.sh"
  topic = ""          # your ntfy topic; empty disables phone pings
  focus = 25          # minutes
  short_break = 5
  long_break = 15
  long_every = 4      # a long break after this many focus sessions

The ntfy topic is a secret: it is read only from the config file (chmod 600 it),
never from a flag, and never logged.
"""


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pomo",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--focus", type=positive_int, metavar="MIN", help="focus length in minutes (default 25)")
    parser.add_argument("--short-break", type=positive_int, metavar="MIN", help="short break in minutes (default 5)")
    parser.add_argument("--long-break", type=positive_int, metavar="MIN", help="long break in minutes (default 15)")
    parser.add_argument(
        "--long-every", type=positive_int, metavar="N", help="long break after every N focus sessions (default 4)"
    )
    parser.add_argument("--idle", action="store_true", help="start in Idle mode: no timer, every care tool unlocked")
    parser.add_argument("--no-notify", action="store_true", help="no desktop or phone notifications")
    parser.add_argument("--config", type=Path, metavar="PATH", help="config file to use instead of the default")
    parser.add_argument("--gallery", action="store_true", help="show every cat sprite and prop (for tuning the art)")
    parser.add_argument("--version", action="version", version=f"pomo {__version__}")
    return parser


def setup_logging(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def truecolor_warning(environ: Mapping[str, str]) -> str | None:
    """iTerm2 and Ghostty set COLORTERM=truecolor. Without it the pixel art gets approximated."""
    if environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return None
    return "This terminal doesn't report 24-bit colour (COLORTERM), so the cats may look a bit off."


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.gallery:
        GalleryApp().run()
        return 0
    if args.config is not None:
        path = args.config.expanduser()  # shells don't expand ~ in --config=~/...
        if not path.is_file():
            print(f"pomo: config file not found: {path}", file=sys.stderr)
            return 2
    else:
        path = config_path()  # the default may be missing: that just means defaults
    try:
        cfg = with_overrides(
            load_config(path),
            focus=args.focus,
            short_break=args.short_break,
            long_break=args.long_break,
            long_every=args.long_every,
        )
    except ConfigError as e:
        print(f"pomo: {e}", file=sys.stderr)
        return 2

    setup_logging(log_path())
    warnings = [w for w in [permission_warning(path, cfg), truecolor_warning(os.environ)] if w]
    app = PomoApp(cfg, RealClock(), NullNotifier(), warnings=warnings, keep_awake=keep_awake(), idle=args.idle)
    if not args.no_notify:
        # The bell must ring on Textual's thread; notifications arrive from a worker thread.
        app.notifier = Notifier(cfg.ntfy_server, cfg.topic, bell=lambda: app.call_from_thread(app.bell))
    app.run()
    return 0
```

- [ ] **Step 8: The README**

Replace all of `README.md` with:

````markdown
# pomo

A pomodoro timer for your terminal, with a room full of pixel-art cats. Mango lives in the
room: he naps up high while you focus, gets the zoomies on your breaks, eats from the bowl
when he's hungry, pops out through the litter door now and then, and remembers every rule
you break. Look after him with the toolbar: fill his bowl, roll him a yarn ball, dangle a
string, and pet him with the mouse. More cats and real consequences arrive in later milestones.

Needs a terminal with 24-bit colour and at least 100×30 cells. iTerm2 and Ghostty are the targets.

## Install

```bash
uv tool install .    # run from this directory; puts `pomo` on your PATH
```

## Use

```bash
pomo                               # 25 min focus, 5 min breaks, 15 min long break every 4
pomo --focus 50 --short-break 10
pomo --idle                        # no timer: just hang out with the cats
pomo --help                        # every flag, key and config option
pomo --gallery                     # every cat pose, face and coat, for tuning the art
```

Keys: `space` start/pause · `s` skip · `r` reset · `+`/`-` 5 min · `i` idle mode · `q` quit

Skipping or abandoning a focus (switching to Idle mid-focus counts), skipping a break, or
pausing a focus for more than 3 minutes breaks a rule. `pomo` asks before letting you,
because the cats will remember.

## Looking after the cats

Pick a tool with `1`–`5` or the toolbar, and put it down with `esc`:

- **1 Feed:** click the bowl, or press `1` again, to fill it. Hungry cats come to eat.
- **2 Ball:** click to drop a yarn ball. Cats that want to play chase it and bat it around.
- **3 String:** a string hangs from the mouse. Wiggle it and cats pounce at it.
- **4 Pet:** stroke a cat with the mouse. Content cats purr; angry ones hiss; too much earns a swat.
- **5 Scoop:** click a poop to clean it up. (Angry cats start pooping on the floor in the next milestone.)

A focus is nap time, so only the scoop works until your break. Idle mode (`i`) puts the
timer away and unlocks everything.

## Phone pings (ntfy)

Put your topic in `~/.config/pomo/config.toml` and keep the file private:

```toml
topic = "your-secret-topic"
```

```bash
chmod 600 ~/.config/pomo/config.toml
```

## Develop

```bash
uv sync
uv run pytest
```
````

- [ ] **Step 9: Run the tests**

Run: `uv run pytest -q`
Expected: `499 passed`

- [ ] **Step 10: Try it in a real terminal**

1. Run `uv run pomo --idle` in iTerm2 or Ghostty at 100×30 or larger.
2. Press `4` and stroke Mango with the mouse: he shuts his eyes, `prr` shows and hearts float up.
3. Press `2` and click in the room: a yarn ball drops, and Mango chases and bats it.
4. Press `3` and move the mouse: a string swings from the pointer.
5. Press `i`, then `space`: the tools lock (🔒), and pressing `2` explains why.
6. Press `q` to quit. It should exit cleanly with no traceback.

- [ ] **Step 11: Commit**

```bash
git add src/pomo/ui/toolbar.py src/pomo/ui/stage.py src/pomo/ui/view.py src/pomo/ui/app.py src/pomo/cli.py README.md tests/test_app.py tests/test_stage.py tests/test_view.py tests/test_cli.py
git commit -m "feat: the care toolbar, mouse tools and Idle mode in the app; --idle" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
