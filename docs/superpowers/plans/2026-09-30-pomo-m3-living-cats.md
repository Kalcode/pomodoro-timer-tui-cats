# pomo Milestone 3: Living Cats Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the cats to life:
- **Moods and needs:** each cat has a mood, a stage and needs that respond to your pomodoro discipline.
- **Movement:** cats walk and jump between the floor, the cat tree and the shelf.
- **Phases:** a focus is nap time, when cats curl up high. A break is play time: zoomies, climbing and wandering.
- **Hunger and the litter door:** hungry cats eat from the bowl, or beg once it's empty, and they pop out through the litter door now and then.
- **The roster:** the timer panel shows every cat's hearts and mood.

**Architecture:** Three new pure modules under `game/`, plus a new render path:
- `cat.py`: a cat's inner life (mood, needs, trait and stage) as plain numbers, reacting to the session's `RuleBreak`, `FocusCompleted` and `BreakCompleted` events.
- `behavior.py`: how cats move (routes over the playscape's surface graph, walking, jump arcs) and what they choose to do next (weighted by mode and stage, with hunger and litter first). It uses an injected `random.Random`.
- `world.py`: the room over time. `tick(dt)` moves time on, `apply(events)` passes events to the cats, `set_mode(...)` reacts to the phase, `fit(w, h)` follows the terminal size, and `view()` returns the `RoomView` that the pure scene draws.
- **Sprites:** gain side-view walk and leap poses, facing and side-view faces.
- **The app:** owns one `World` (Mango, per spec §4's new save). Each 8 fps tick passes it the real elapsed time from the injected clock.

**Tech Stack:** Python ≥ 3.12, Textual 8.2, pytest and pytest-asyncio. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-29-pomo-cats-design.md`: §3.1 (phases), §3.3 (mood), §3.4 (needs; care comes later), §3.5 (traits), §3.7 (litter; poop comes later), §6 (surfaces and jumps), §7 (poses) and §13 (milestone 3). This is **milestone 3 of 6**. It builds on milestone 2, which is on `main` (235 tests).

## Global Constraints

- Everything from the milestone 1 and 2 plans still holds: a pure core, an injected `Clock`, the topic never logged, colours only in `theme.py`, the panel exactly 30 columns, and 8 fps with row-diff repaints.
- `game/*` must not import Textual or `pomo.render`. `render/*` may import `game/*`.
- **All randomness comes from an injected `random.Random`.** Tests always seed it, so every behaviour test is deterministic.
- **Time comes only from `dt` passed to `tick`, capped at 1 s** (`MAX_DT`), so a suspended process never fast-forwards the room.
- **Mood numbers are exactly spec §3.2–§3.5:**
  - Starting mood and stages: start 80. Content ≥ 70, grumpy ≥ 40, pissy ≥ 15, furious below 15.
  - Rewards: +10 per completed focus of at least 15 min, and +5 per completed break.
  - Penalties: −25, −20 and −10, scaled ×0.5 for chill and ×1.5 for diva.
  - Needs: 0→100 takes 3 h for hunger, 2 h for play and 2.5 h for affection. Clingy cats' affection rises ×1.5 as fast.
  - Unmet needs: above 70, a need drains mood by 1 per minute, never below 40.
  - Cooling: +1 per 10 min, up to 70.
  - Eating: +3, but not for pissy or furious cats.
- **Mode mapping:**
  - Focus phase, started (running or paused) → NAP.
  - Any break phase → PLAY.
  - Focus not yet started → RELAX. Idle mode joins this in milestone 4.
- **The first cat is spec §4's new save:** Mango, tabby, clingy.
- A cat's position is its **centre** column `x` and its **feet** pixel row. The scene works out the left edge from the sprite's width.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

**Not in this milestone:**
- Care tools: feed, ball, string, pet and scoop, plus the refill button. `World.refill()` exists for milestone 4.
- Idle mode and the toolbar (milestone 4).
- Poop, the knocked-over bowl, sitting on the clock, treats, the shop and strays (milestone 5).
- Saving cats between runs (milestone 6). Until then every launch starts with a fresh Mango.

## Review Focus

1. **A room left running all day:** cats never get stuck or freeze, never drift off their surfaces, and everyone keeps using the litter door. Test: Task 4 `test_a_long_day_in_the_room_never_gets_stuck` (4 simulated hours, 3 cats, cycling NAP and PLAY).
2. **Resizing mid-jump or while a cat is out through the door:** the cat lands on its surface, or plans a fresh walk back in. Tests: Task 4 `test_resizing_mid_jump_lands_the_cat`, `test_resizing_puts_every_cat_back_on_its_surface`.
3. **The process is suspended for an hour** (Ctrl+Z, a debugger): the room moves at most 1 s. Test: Task 4 `test_a_stalled_tick_is_capped_at_one_second`.
4. **Two hungry cats and one bowl:** only one eats, the other sits beside it and begs, and nobody fakes a "nom". Tests: Task 4 `test_two_cats_never_eat_from_the_bowl_at_once`, `test_a_hungry_cat_eats_and_the_next_one_begs`.
5. **A terminal below 100×30:** the world keeps the minimum room geometry, so cats are clipped rather than planning routes in a degenerate room. Test: Task 5 `test_a_terminal_below_the_minimum_keeps_the_minimum_room`.

## File Map

| File | Responsibility | Task |
|---|---|---|
| `src/pomo/game/balance.py` (replace, then append) | Mood, need and trait numbers (T1); behaviour numbers (T3) | 1, 3 |
| `src/pomo/game/cat.py` | `Cat`, `Trait`, `Stage`, `NEEDS`: mood, needs, `apply`, `tick`, `eat`, `wants`, `hearts` | 1 |
| `src/pomo/render/sprites.py` (replace) | Adds the side-view `walk0`, `walk1` and `leap` poses, `facing`, side faces; `FRONT_POSES`, `SIDE_POSES`, `SIDE_WIDTH` | 2 |
| `src/pomo/gallery.py` (replace) | Adds a side-pose row; needs 100×40 | 2 |
| `src/pomo/game/behavior.py` | `Mode`, `Doing`, `Step`, `Body`, `walkable`, `path`, `route`, `advance`, `choose`, `pick` | 3 |
| `src/pomo/game/world.py` | `World`, `CatView`, `RosterLine`, `RoomView`, `mode_for` | 4 |
| `src/pomo/render/theme.py` (append) | Roster colours: `HEART`, `HEART_EMPTY`, `STAGE_COLORS` | 5 |
| `src/pomo/render/scene.py` (replace) | Draws a `RoomView`: centre-positioned cats that can face left, bubbles, the bowl state, the roster | 5 |
| `src/pomo/ui/app.py` (replace) | Owns a `World`; passes `dt`, the mode and events to it; fits it to the room on screen | 5 |
| `README.md` (replace) | Describes the living room | 5 |

---

### Task 1: The cat's inner life

**Files:**
- Replace: `src/pomo/game/balance.py`
- Create: `src/pomo/game/cat.py`
- Test: `tests/test_cat.py`

**Interfaces:**
- Consumes: from milestone 1, `RuleBreak`, `RuleKind`, `FocusCompleted`, `BreakCompleted`, `SetCompleted`, the `Event` union, `PENALTIES` and `Phase`.
- Produces:
  - Balance constants: `MOOD_START`, `MOOD_MAX`, `CONTENT_AT`, `GRUMPY_AT`, `PISSY_AT`, `FOCUS_REWARD`, `FOCUS_REWARD_MIN_MINUTES`, `BREAK_REWARD`, `COOL_PER_S`, `COOL_CEILING`, `NEED_FULL_S`, `NEED_ALERT`, `NEED_DRAIN_PER_S`, `NEED_FLOOR`, `EAT_MOOD`, `TRAIT_PENALTY`, `CLINGY_AFFECTION`.
  - `NEEDS = ("hunger", "play", "affection")`.
  - `Trait` enum: `CHILL`, `DIVA`, `CLINGY`, `GREMLIN`.
  - `Stage` enum: `CONTENT`, `GRUMPY`, `PISSY`, `FURIOUS`, with the property `.angry`, which is true for pissy and furious.
  - `Cat(name, coat, trait, mood=80, needs={...0})`:
    - Properties: `.stage` and `.hearts` (0–5, `mood // 20`, capped at 5).
    - Methods: `.wants() -> str | None`, `.apply(event)`, `.tick(dt)`, `.eat()`.

- [ ] **Step 1: Write the failing tests**

`tests/test_cat.py`:

```python
import pytest

from pomo.game.cat import Cat, Stage, Trait
from pomo.game.events import BreakCompleted, FocusCompleted, RuleBreak, RuleKind, SetCompleted
from pomo.timer import Phase

HOUR = 3600.0


def cat(trait=Trait.CLINGY, mood=80.0) -> Cat:
    c = Cat("Mango", "tabby", trait)
    c.mood = mood
    return c


def run(c: Cat, seconds: float, step: float = 1.0) -> None:
    for _ in range(int(seconds / step)):
        c.tick(step)


def test_a_new_cat_is_content_and_wants_nothing():
    c = Cat("Mango", "tabby", Trait.CLINGY)
    assert (c.mood, c.stage, c.hearts, c.wants()) == (80, Stage.CONTENT, 4, None)


@pytest.mark.parametrize("mood, stage", [
    (100, Stage.CONTENT), (70, Stage.CONTENT), (69.9, Stage.GRUMPY), (40, Stage.GRUMPY),
    (39.9, Stage.PISSY), (15, Stage.PISSY), (14.9, Stage.FURIOUS), (0, Stage.FURIOUS),
])
def test_stages(mood, stage):
    assert cat(mood=mood).stage is stage


@pytest.mark.parametrize("mood, hearts", [(100, 5), (99, 4), (80, 4), (40, 2), (19, 0), (0, 0)])
def test_hearts(mood, hearts):
    assert cat(mood=mood).hearts == hearts


@pytest.mark.parametrize("kind, lost", [
    (RuleKind.ABANDON_FOCUS, 25), (RuleKind.SKIP_BREAK, 20), (RuleKind.LONG_PAUSE, 10),
])
def test_rule_breaks_cost_mood(kind, lost):
    c = cat()
    c.apply(RuleBreak(kind))
    assert c.mood == 80 - lost


def test_traits_scale_the_penalties():
    chill, diva, gremlin = cat(Trait.CHILL), cat(Trait.DIVA), cat(Trait.GREMLIN)
    for c in (chill, diva, gremlin):
        c.apply(RuleBreak(RuleKind.SKIP_BREAK))
    assert (chill.mood, diva.mood, gremlin.mood) == (70, 50, 60)


def test_mood_never_leaves_0_to_100():
    c = cat(mood=10)
    c.apply(RuleBreak(RuleKind.ABANDON_FOCUS))
    assert c.mood == 0
    c = cat(mood=95)
    c.apply(FocusCompleted(25))
    assert c.mood == 100


def test_finished_focus_and_breaks_cheer_cats_up():
    c = cat(mood=50)
    c.apply(FocusCompleted(25))
    c.apply(BreakCompleted(Phase.SHORT_BREAK))
    assert c.mood == 65


def test_a_focus_shorter_than_15_minutes_earns_no_mood():
    c = cat(mood=50)
    c.apply(FocusCompleted(10))
    assert c.mood == 50


def test_other_events_leave_the_mood_alone():
    c = cat(mood=50)
    c.apply(SetCompleted())
    assert c.mood == 50


@pytest.mark.parametrize("need, hours", [("hunger", 3), ("play", 2), ("affection", 2.5)])
def test_needs_fill_up_over_runtime(need, hours):
    c = cat(Trait.CHILL)
    run(c, hours * HOUR / 2, step=60)
    assert c.needs[need] == pytest.approx(50)
    run(c, hours * HOUR, step=60)
    assert c.needs[need] == 100


def test_clingy_cats_want_affection_sooner():
    clingy, chill = cat(Trait.CLINGY), cat(Trait.CHILL)
    for c in (clingy, chill):
        run(c, HOUR, step=60)
    assert clingy.needs["affection"] == pytest.approx(chill.needs["affection"] * 1.5)


def test_wants_names_the_most_urgent_need_over_70():
    c = cat()
    c.needs.update(hunger=65, play=90, affection=75)
    assert c.wants() == "play"
    c.needs.update(play=60, affection=60)
    assert c.wants() is None


def test_unmet_needs_sour_the_mood_but_never_past_grumpy():
    c = cat(mood=80)
    c.needs.update(hunger=100)
    run(c, 10 * 60)
    assert c.mood == pytest.approx(70, abs=0.2)  # about 1 per minute
    run(c, 2 * HOUR, step=5)
    assert c.mood == pytest.approx(40, abs=0.05)
    assert c.stage is Stage.GRUMPY


def test_unmet_needs_cannot_make_an_angry_cat_angrier():
    c = cat(mood=30)
    c.needs.update(hunger=100)
    run(c, 10 * 60)
    assert c.mood == pytest.approx(31)  # only the slow cooling


def test_anger_cools_slowly_and_only_up_to_content():
    c = cat(mood=50)
    run(c, 10 * 60)
    assert c.mood == pytest.approx(51)
    c = cat(mood=69.5)
    run(c, HOUR, step=10)
    assert c.mood == 70


def test_eating_fixes_hunger_and_cheers_up_calm_cats_only():
    content, pissy = cat(mood=60), cat(mood=30)
    for c in (content, pissy):
        c.needs["hunger"] = 90
        c.eat()
        assert c.needs["hunger"] == 0
    assert (content.mood, pissy.mood) == (63, 30)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_cat.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.game.cat'`

- [ ] **Step 3: Replace balance.py**

Replace all of `src/pomo/game/balance.py` with:

```python
"""Every tunable game number lives here (spec §3–§4). Later milestones add to this file."""

from pomo.game.events import RuleKind

PAUSE_ALLOWANCE_S = 3 * 60  # total pause per focus before it counts as a rule break

PENALTIES = {  # mood lost by every cat (spec §3.2)
    RuleKind.ABANDON_FOCUS: 25,
    RuleKind.SKIP_BREAK: 20,
    RuleKind.LONG_PAUSE: 10,
}

# --- mood (spec §3.3) -------------------------------------------------------
MOOD_START = 80
MOOD_MAX = 100
CONTENT_AT = 70  # stage lower bounds: content ≥ 70 > grumpy ≥ 40 > pissy ≥ 15 > furious
GRUMPY_AT = 40
PISSY_AT = 15
FOCUS_REWARD = 10
FOCUS_REWARD_MIN_MINUTES = 15
BREAK_REWARD = 5
COOL_PER_S = 1 / 600  # anger cools by 1 per 10 minutes of runtime...
COOL_CEILING = 70  # ...but never past content on its own

# --- needs (spec §3.4) ------------------------------------------------------
NEED_FULL_S = {"hunger": 3 * 3600, "play": 2 * 3600, "affection": 2.5 * 3600}  # 0 → 100
NEED_ALERT = 70  # above this the cat wants something, shows a bubble, and gets sulky
NEED_DRAIN_PER_S = 1 / 60  # mood lost while a need is above the alert level...
NEED_FLOOR = 40  # ...which on its own never goes past grumpy
EAT_MOOD = 3  # kibble; pissy and furious cats eat but don't cheer up

# --- traits (spec §3.5) -----------------------------------------------------
TRAIT_PENALTY = {"chill": 0.5, "diva": 1.5}
CLINGY_AFFECTION = 1.5
```

- [ ] **Step 4: Implement the cat**

`src/pomo/game/cat.py`:

```python
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
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -v`
Expected: `267 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/game/balance.py src/pomo/game/cat.py tests/test_cat.py
git commit -m "feat: cat mood, needs, traits and stages (spec 3.3-3.5)" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Side-view sprites and facing

**Files:**
- Replace: `src/pomo/render/sprites.py`, `tests/test_sprites.py`, `src/pomo/gallery.py`, `tests/test_gallery.py`

**Interfaces:**
- Consumes: from milestone 2, `theme.hex_rgb` and `RGB`, and `playscape.CAT_WIDTH` and `CAT_HEIGHT`, which a test checks against the sprites.
- Produces:
  - Constants: `SIDE_WIDTH = 20`, `FRONT_POSES = ("sit", "loaf")`, `SIDE_POSES = ("walk0", "walk1", "leap")`, and `POSES = FRONT_POSES + SIDE_POSES`.
  - `cat(pose, face, facing=1) -> Grid`. `facing=-1` mirrors the cat.
  - Side sprites are 20×13: tail on the left, head on the right, and the eye on row 4.
  - Side faces change only row 0 (the ears, removed when `mad`) and row 4 (the eye). The mapping is: `ok` → e/k, `blink`/`sleep` → o/o, `meh` → o/k, `mad` → r/k.
  - Everything from milestone 2 (`CAT_WIDTH`, `FACES`, coats, props, `problems`) is unchanged.
  - The gallery adds a side row (walk0 ok, walk1 ok, leap ok, walk0 mad) at `SIDE_PY = 44`, with the props at `PROPS_PY = 64`. It needs a 100×40 terminal.

- [ ] **Step 1: Write the failing tests**

Replace all of `tests/test_sprites.py`:

```python
import pytest

from pomo.game import playscape
from pomo.render import sprites
from pomo.render.sprites import (
    CAT_SLOTS, CAT_WIDTH, COATS, FACES, FRONT_POSES, POSES, PROPS, SIDE_POSES, SIDE_WIDTH,
    cat, cat_head, flip, mirror, problems,
)

HEAD_ROWS = 10
EXPECTED_SIZE = {"sit": (17, 16), "loaf": (17, 15), "walk0": (20, 13), "walk1": (20, 13), "leap": (20, 13)}


@pytest.mark.parametrize("pose", POSES)
@pytest.mark.parametrize("face", FACES)
def test_every_cat_is_a_clean_grid_of_the_right_size(pose, face):
    grid = cat(pose, face)
    assert problems(grid, CAT_SLOTS) == []
    width, height = EXPECTED_SIZE[pose]
    assert {len(row) for row in grid} == {width}
    assert len(grid) == height


def test_the_widths_match_the_constants():
    assert {len(cat(p, "ok")[0]) for p in FRONT_POSES} == {CAT_WIDTH}
    assert {len(cat(p, "ok")[0]) for p in SIDE_POSES} == {SIDE_WIDTH}


def test_playscape_sizes_match_the_real_sprites():
    # playscape can't import render (layering), so this keeps its copies honest
    assert playscape.CAT_WIDTH == CAT_WIDTH
    assert playscape.CAT_HEIGHT == max(len(cat(p, "ok")) for p in POSES)


@pytest.mark.parametrize("face", FACES)
def test_front_heads_are_symmetric(face):
    for row in cat_head(face):
        core = row[:14]
        assert core == core[::-1]


@pytest.mark.parametrize("pose", FRONT_POSES)
def test_front_faces_only_change_the_head(pose):
    bodies = {cat(pose, face)[HEAD_ROWS:] for face in FACES}
    assert len(bodies) == 1


@pytest.mark.parametrize("pose", SIDE_POSES)
def test_side_faces_only_change_the_ears_and_eye(pose):
    grids = [cat(pose, face) for face in FACES]
    for row in range(len(grids[0])):
        if row not in (0, 4):
            assert len({g[row] for g in grids}) == 1, row


def test_the_faces_look_different():
    heads = {face: cat_head(face) for face in FACES}
    assert heads["ok"] != heads["blink"] != heads["meh"]
    assert heads["mad"][0] == "." * CAT_WIDTH  # ears flattened out of the top row
    assert "r" in "".join(heads["mad"])  # red eyes
    assert "e" not in "".join(heads["blink"])  # eyes shut
    assert "r" in "".join(cat("walk0", "mad")) and "e" not in "".join(cat("walk0", "sleep"))


def test_the_walk_frames_move_the_legs():
    assert cat("walk0", "ok")[-3:] != cat("walk1", "ok")[-3:]
    assert cat("walk0", "ok")[:-3] == cat("walk1", "ok")[:-3]


def test_facing_left_mirrors_the_cat():
    for pose in POSES:
        assert cat(pose, "ok", facing=-1) == flip(cat(pose, "ok"))
    right = cat("walk0", "ok")
    assert right[4].index("e") > SIDE_WIDTH // 2  # the eye is at the front, on the right


@pytest.mark.parametrize("coat", COATS)
def test_every_coat_colours_every_slot(coat):
    assert set(COATS[coat]) == CAT_SLOTS


def test_patches_only_show_on_calico():
    for name, coat in COATS.items():
        assert (coat["c"] != coat["f"]) == (name == "calico"), name


@pytest.mark.parametrize("name", PROPS)
def test_props_are_clean_grids(name):
    grid, palette = PROPS[name]
    assert problems(grid, set(palette)) == []


def test_mirror_and_flip():
    assert mirror(["ab"]) == ("abba",)
    assert flip(("abc", "d.e")) == ("cba", "e.d")
    assert flip(flip(cat("sit", "ok"))) == cat("sit", "ok")


def test_problems_spots_ragged_rows_and_unknown_slots():
    assert problems(("ab", "a"), {"a", "b"}) == ["ragged rows: [1, 2]"]
    assert problems(("aZ",), {"a"}) == ["unknown slots: ['Z']"]


def test_unknown_pose_or_face_is_a_key_error():
    with pytest.raises(KeyError):
        sprites.cat("backflip", "ok")
    with pytest.raises(KeyError):
        sprites.cat("sit", "smug")
    with pytest.raises(KeyError):
        sprites.cat("walk0", "smug")
```

Replace all of `tests/test_gallery.py`:

```python
from canvas_reading import screen_text
from pomo.gallery import GalleryApp
from pomo.render import sprites

SIZE = (100, 40)


def shows_coat(app, coat) -> bool:
    canvas = app.stage.canvas
    fur = sprites.COATS[coat]["f"]
    return any(canvas.pixel_at(x, py) == fur for x in range(canvas.width) for py in range(canvas.height * 2))


async def test_the_gallery_opens_on_the_first_coat_with_every_pose_and_face():
    app = GalleryApp()
    async with app.run_test(size=SIZE):
        text = screen_text(app.stage.canvas)
        assert "tabby  (1/6)" in text
        for pose in sprites.FRONT_POSES:
            for face in sprites.FACES:
                assert f"{pose} {face}" in text
        for label in ["walk0 ok", "walk1 ok", "leap ok", "walk0 mad"]:
            assert label in text
        for prop in sprites.PROPS:
            assert prop in text
        assert shows_coat(app, "tabby")


async def test_arrows_flip_through_the_coats_and_wrap():
    app = GalleryApp()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("right")
        assert app.coat == "grey" and shows_coat(app, "grey")
        await pilot.press("left", "left")
        assert app.coat == "calico" and shows_coat(app, "calico")


async def test_every_coat_draws():
    app = GalleryApp()
    async with app.run_test(size=SIZE) as pilot:
        for _ in sprites.COATS:
            await pilot.press("right")
            assert shows_coat(app, app.coat)


async def test_q_quits():
    app = GalleryApp()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_sprites.py tests/test_gallery.py -v`
Expected: FAIL during collection with `ImportError: cannot import name 'FRONT_POSES' from 'pomo.render.sprites'`

- [ ] **Step 3: Replace the sprites**

`src/pomo/render/sprites.py`:

```python
"""Pixel art as text grids: one character per pixel, '.' is transparent (spec §7).

Cat palette slots:
  o outline   f fur    d stripe   c patch (same as fur except on calico)
  w white     p pink   e eye      k pupil  r angry eye
Front poses (sit, loaf) are one head plus one body; side poses (walk0, walk1,
leap) share one side-view torso with different legs. A coat is only a palette,
a mood only swaps ear and eye pixels, and facing left is a mirror image, so
poses × moods × coats × directions never multiply into more drawing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pomo.render.theme import RGB, hex_rgb

Grid = tuple[str, ...]

CAT_WIDTH = 17  # front poses
SIDE_WIDTH = 20  # side poses
CAT_SLOTS = frozenset("ofdcwpekr")
FACES = ("ok", "blink", "sleep", "meh", "mad")
FRONT_POSES = ("sit", "loaf")
SIDE_POSES = ("walk0", "walk1", "leap")
POSES = FRONT_POSES + SIDE_POSES


def mirror(left_half: Sequence[str]) -> Grid:
    """A symmetric grid from its left half."""
    return tuple(row + row[::-1] for row in left_half)


def flip(grid: Sequence[str]) -> Grid:
    """Face the other way."""
    return tuple(row[::-1] for row in grid)


def pad(grid: Sequence[str], width: int) -> Grid:
    return tuple(row.ljust(width, ".") for row in grid)


# --- cats -----------------------------------------------------------------
# Heads are drawn as their left half (7 px) and mirrored to 14 px.

_EARS = {
    "up": ("..o....", ".opo...", ".oppooo"),
    "flat": (".......", ".......", "opppooo"),  # airplane ears
}
_FOREHEAD = ".offfdf"
_BROW = {"calm": "offfffd", "angry": "ofofffd"}
_EYES = {
    "open": ("ofekeff", "ofekeff"),
    "shut": ("offffff", "ofoooff"),
    "half": ("offffff", "ofekeff"),
    "angry": ("offooff", "ofrkrff"),
}
_MUZZLE = ("offfffp", ".offfww", "..offww")

_FACE_PARTS = {  # face: (ears, brow, eyes)
    "ok": ("up", "calm", "open"),
    "blink": ("up", "calm", "shut"),
    "sleep": ("up", "calm", "shut"),
    "meh": ("up", "calm", "half"),
    "mad": ("flat", "angry", "angry"),
}

_BODIES = {
    "sit": (
        ".occfwwwwfffo....",
        ".offfwwwwfffo.oo.",
        "offffwwwwfccfoffo",
        "offffwwwwfcffoffo",
        "offwwffffwwfffffo",
        ".ooooooooooooooo.",
    ),
    "loaf": (
        ".offfwwwwfffo....",
        "offffwwwwfccfoo..",
        "occffffffffcfffo.",
        "ofddddddddddddfo.",
        ".oooooooooooooo..",
    ),
}


def cat_head(face: str) -> Grid:
    ears, brow, eyes = _FACE_PARTS[face]
    half = (*_EARS[ears], _FOREHEAD, _BROW[brow], *_EYES[eyes], *_MUZZLE)
    return pad(mirror(half), CAT_WIDTH)


# Side view, facing right: tail on the left, head on the right. Row 4 holds the eye.
_SIDE_TORSO = (
    "..............o...o.",
    ".oo..........opo.opo",
    "ofo..........offfffo",
    "ofo.........offffffo",
    ".ofo........offfekfo",
    "..oooooooooofffffffp",
    "..offdffdffdffffwwo.",
    "..offffffffffffffoo.",
    "..offffffffffffffo..",
    "...offoooooooffo....",
)
_SIDE_LEGS = {
    "walk0": ("...offo.....offo....", "...offo.....offo....", "...oooo.....oooo...."),
    "walk1": ("..offo.......offo...", ".offo.........offo..", ".oooo.........oooo.."),
    "leap": (".offo.........offo..", "oooo............oooo", "...................."),
}
_SIDE_EYE_ROW = 4
_SIDE_EYES = {  # face: what the eye (e) and pupil (k) pixels become
    "ok": ("e", "k"), "blink": ("o", "o"), "sleep": ("o", "o"), "meh": ("o", "k"), "mad": ("r", "k"),
}


def _side(pose: str, face: str) -> Grid:
    eye, pupil = _SIDE_EYES[face]
    rows = list(_SIDE_TORSO + _SIDE_LEGS[pose])
    rows[_SIDE_EYE_ROW] = rows[_SIDE_EYE_ROW].replace("e", eye).replace("k", pupil)
    if face == "mad":
        rows[0] = "." * SIDE_WIDTH  # ears pinned back
    return tuple(rows)


def cat(pose: str, face: str, facing: int = 1) -> Grid:
    """A cat whose bottom row is where its feet are. facing=-1 mirrors it to face left."""
    grid = cat_head(face) + _BODIES[pose] if pose in _BODIES else _side(pose, face)
    return flip(grid) if facing < 0 else grid


# --- coats ----------------------------------------------------------------

_SHARED = {"p": hex_rgb("#f09aa6"), "k": hex_rgb("#111111"), "r": hex_rgb("#ff4a3d")}


def _coat(o: str, f: str, d: str, w: str, e: str, c: str | None = None) -> dict[str, RGB]:
    return {**_SHARED, "o": hex_rgb(o), "f": hex_rgb(f), "d": hex_rgb(d),
            "c": hex_rgb(c or f), "w": hex_rgb(w), "e": hex_rgb(e)}


COATS: dict[str, dict[str, RGB]] = {
    "tabby": _coat("#3b2416", "#e8923b", "#b8631e", "#f6eee3", "#8fd16a"),
    "grey": _coat("#1f2330", "#8a93a6", "#6b7385", "#e9ecf2", "#8fd16a"),
    "tuxedo": _coat("#5d5d70", "#2a2a33", "#1e1e25", "#ececf0", "#e8d44d"),
    "siamese": _coat("#5a4636", "#efe0c8", "#8a6a55", "#fffaf2", "#6fb7ff"),
    "black": _coat("#5d5d70", "#1c1c22", "#141418", "#2a2a33", "#e8d44d"),
    "calico": _coat("#3a2a22", "#f4ede2", "#e0913a", "#fbf8f2", "#8fd16a", c="#2b2626"),
}


# --- props ----------------------------------------------------------------

DOOR: Grid = (
    "ooooooo", "obbbbbo", "obbbbbo", "obooobo", "obfffbo", "obfffbo", "obfffbo",
    "obfffbo", "obfffbo", "obooobo", "obbbbbo", "obbbbbo", "obbbbbo", "obbbbbo",
)
DOOR_PALETTE = {"o": hex_rgb("#2e2016"), "b": hex_rgb("#5c3f2a"), "f": hex_rgb("#3d2a1c")}

BOWL_FULL: Grid = (".kkkkkk.", "obbbbbbo", ".obbbbo.")
BOWL_EMPTY: Grid = (".o....o.", "obbbbbbo", ".obbbbo.")
BOWL_PALETTE = {"k": hex_rgb("#b8631e"), "o": hex_rgb("#1f3b66"), "b": hex_rgb("#3d6fb3")}

PROPS: dict[str, tuple[Grid, Mapping[str, RGB]]] = {
    "door": (DOOR, DOOR_PALETTE),
    "bowl_full": (BOWL_FULL, BOWL_PALETTE),
    "bowl_empty": (BOWL_EMPTY, BOWL_PALETTE),
}


def problems(grid: Sequence[str], slots: frozenset[str] | set[str]) -> list[str]:
    """Why a grid is malformed: ragged rows, or characters that aren't '.' or a known slot."""
    found = []
    if len({len(row) for row in grid}) > 1:
        found.append(f"ragged rows: {sorted({len(row) for row in grid})}")
    unknown = set("".join(grid)) - set(slots) - {"."}
    if unknown:
        found.append(f"unknown slots: {sorted(unknown)}")
    return found
```

- [ ] **Step 4: Replace the gallery**

`src/pomo/gallery.py`:

```python
"""`pomo --gallery`: every front pose × face and the side poses for one coat at a time,
plus the props (spec §7). For tuning the art: flip through the coats with ←/→.
Needs a 100×40 terminal.
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
        x = 2
        for name, (grid, prop_palette) in sprites.PROPS.items():
            canvas.sprite(x, PROPS_PY, grid, prop_palette)
            canvas.text(x, _label_row(PROPS_PY, grid), name, theme.DIM)
            x += max(len(grid[0]), len(name)) + 3


def _label_row(py: int, grid: sprites.Grid) -> int:
    """The text row just under a sprite drawn at pixel row py."""
    return (py + len(grid) + 1) // 2
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -v`
Expected: `289 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/render/sprites.py tests/test_sprites.py src/pomo/gallery.py tests/test_gallery.py
git commit -m "feat: side-view walk and leap sprites, facing, side faces; gallery row" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Behaviour: getting around and choosing what to do

**Files:**
- Modify: `src/pomo/game/balance.py` (append the behaviour section)
- Create: `src/pomo/game/behavior.py`
- Test: `tests/test_behavior.py`

**Interfaces:**
- Consumes:
  - From Task 1: `Cat`, `Stage` and the balance numbers.
  - From milestone 2: `Playscape`, `Surface`, `can_jump` and `layout`.
- Produces:
  - Constants: `HALF_WIDTH = 9`, and `MOVING = {WALK, ZOOM}`.
  - `Mode` enum: `NAP`, `PLAY`, `RELAX`.
  - `Doing` enum: `SIT`, `LOAF`, `NAP`, `SULK`, `WALK`, `ZOOM`, `JUMP`, `EAT`, `BEG`, `AWAY`.
  - `Step(doing, seconds=0, x=0, surface="")`
  - `Body(surface, x, y, facing=1, step=None, plan=[], elapsed=0, walked=0, launch=None)`
  - `walkable(surface) -> (lo, hi)` and `clamp(v, lo, hi)`
  - `path(scape, start, goal) -> list[str]`. It raises `ValueError` if the goal is unreachable.
  - `route(scape, body, goal, x) -> list[Step]`
  - `jump_seconds(...)`
  - `advance(body, scape, dt) -> Step | None`, which returns the step that just finished.
  - `choose(cat, body, scape, mode, rng, *, bowl_full, litter_due) -> list[Step]`
  - `pick(stage, mode, rng) -> str`
- Rules:
  - **Priority:** the litter door comes first, then hunger (walk to `bowl.x − 6`, then EAT, or BEG if the bowl is empty), then an activity weighted by `ACTIVITY_WEIGHTS[mode]`.
  - **Mood changes the choices:** a grumpy cat's zoom becomes a sulk. For pissy and furious cats, zoom, sit and loaf all become sulks.
  - **Naps pick a spot** by `NAP_SPOTS`, which is weighted toward high places.
  - **Jumps** follow `y = lerp(y0, y1, p) − hop·4p(1−p)`, where `hop = JUMP_ARC_PX + |y1 − y0|/2`, so a cat rises above the higher end before landing. A jump lands exactly on `surface.y`.

- [ ] **Step 1: Write the failing tests**

`tests/test_behavior.py`:

```python
import dataclasses
import random
from collections import Counter

import pytest

from pomo.game import balance
from pomo.game.behavior import Body, Doing, Mode, Step, advance, choose, path, pick, route, walkable
from pomo.game.cat import Cat, Stage, Trait
from pomo.game.playscape import Surface, can_jump, layout

SCAPE = layout(70, 58)


def body_on(surface: str, x: float | None = None) -> Body:
    s = SCAPE.surface(surface)
    return Body(surface, walkable(s)[0] if x is None else x, float(s.y))


def carry_out(body: Body, steps, dt=0.1, limit_s=900.0, watch=None) -> list[Step]:
    """Run a plan to the end; returns the steps in the order they finished."""
    body.plan = list(steps)
    finished, t = [], 0.0
    while (body.step or body.plan) and t < limit_s:
        if body.step is None:
            body.step = body.plan.pop(0)
        if watch:
            watch(body)
        done = advance(body, SCAPE, dt)
        if done:
            finished.append(done)
        t += dt
    assert not body.step and not body.plan, "the plan never finished"
    return finished


def a_cat(mood=80.0, **needs) -> Cat:
    cat = Cat("Mango", "tabby", Trait.CLINGY, mood=mood)
    cat.needs.update(needs)
    return cat


def test_walkable_keeps_the_centre_inside_and_narrow_surfaces_are_one_spot():
    assert walkable(SCAPE.floor) == (9, 61)
    assert walkable(SCAPE.tree_top) == (12, 12)


def test_paths_only_hop_between_surfaces_a_cat_can_jump():
    hops = path(SCAPE, "floor", "shelf")
    assert hops[-1] == "shelf"
    for a, b in zip(["floor", *hops], hops):
        assert can_jump(SCAPE.surface(a), SCAPE.surface(b))
    assert path(SCAPE, "floor", "floor") == []


def test_an_unreachable_surface_is_an_error():
    stranded = dataclasses.replace(SCAPE, shelf=Surface("shelf", 50, 70, -40))  # far out of reach
    with pytest.raises(ValueError):
        path(stranded, "floor", "shelf")


@pytest.mark.parametrize("start, goal", [("floor", "tree_top"), ("tree_top", "floor"), ("floor", "shelf"),
                                         ("shelf", "tree_top"), ("tree_mid", "floor")])
def test_a_route_ends_standing_on_the_goal(start, goal):
    body = body_on(start)
    target = walkable(SCAPE.surface(goal))[1]
    carry_out(body, route(SCAPE, body, goal, target))
    assert (body.surface, body.x, body.y) == (goal, target, SCAPE.surface(goal).y)


def test_route_targets_are_clamped_onto_the_surface():
    body = body_on("floor", 30)
    carry_out(body, route(SCAPE, body, "floor", 500))
    assert body.x == walkable(SCAPE.floor)[1]


def test_walking_moves_at_walking_speed_and_faces_the_way_it_goes():
    body = body_on("floor", 20)
    body.step = Step(Doing.WALK, x=40)
    advance(body, SCAPE, 1.0)
    assert (body.x, body.facing, body.walked) == (20 + balance.WALK_SPEED, 1, balance.WALK_SPEED)
    body.step = Step(Doing.WALK, x=20)
    advance(body, SCAPE, 0.5)
    assert body.facing == -1


def test_zooming_is_faster_than_walking():
    body = body_on("floor", 10)
    body.step = Step(Doing.ZOOM, x=60)
    advance(body, SCAPE, 1.0)
    assert body.x == 10 + balance.ZOOM_SPEED


def test_a_walk_stops_exactly_on_its_target():
    body = body_on("floor", 20)
    body.step = Step(Doing.WALK, x=21.5)
    done = advance(body, SCAPE, 1.0)
    assert done is not None and body.x == 21.5 and body.step is None


def test_jumps_arc_above_the_straight_line_and_land_exactly():
    body = body_on("floor", 18)
    heights = []
    carry_out(body, [Step(Doing.JUMP, x=18, surface="tree_mid")], dt=0.05, watch=lambda b: heights.append(b.y))
    assert body.surface == "tree_mid" and body.y == SCAPE.tree_mid.y
    floor_y, mid_y = SCAPE.floor.y, SCAPE.tree_mid.y
    assert min(heights) < mid_y  # the arc peaks above the landing spot
    assert all(y <= floor_y for y in heights)


def test_timed_steps_last_their_seconds():
    body = body_on("floor")
    body.step = Step(Doing.LOAF, seconds=2.0)
    assert advance(body, SCAPE, 1.9) is None
    assert advance(body, SCAPE, 0.2) is not None


def test_a_hungry_cat_heads_to_the_bowl_and_eats_or_begs():
    body = body_on("tree_top")
    plan = choose(a_cat(hunger=90), body, SCAPE, Mode.NAP, random.Random(1), bowl_full=True, litter_due=False)
    assert plan[-1].doing is Doing.EAT
    carry_out(body, plan)
    assert body.surface == "floor" and body.x == SCAPE.bowl.x - 6
    plan = choose(a_cat(hunger=90), body, SCAPE, Mode.NAP, random.Random(1), bowl_full=False, litter_due=False)
    assert plan[-1].doing is Doing.BEG


def test_a_litter_trip_goes_out_the_door_and_comes_back():
    body = body_on("shelf")
    plan = choose(a_cat(), body, SCAPE, Mode.PLAY, random.Random(2), bowl_full=True, litter_due=True)
    door_x = SCAPE.door.x + SCAPE.door.w / 2
    doings = [s.doing for s in plan]
    assert Doing.AWAY in doings
    away = doings.index(Doing.AWAY)
    assert plan[away - 1] == Step(Doing.WALK, x=door_x)
    carry_out(body, plan)
    lo, hi = walkable(SCAPE.floor)
    assert body.surface == "floor" and lo <= body.x <= hi


def test_the_litter_box_comes_before_hunger():
    plan = choose(a_cat(hunger=100), body_on("floor"), SCAPE, Mode.NAP, random.Random(3),
                  bowl_full=True, litter_due=True)
    assert Doing.AWAY in [s.doing for s in plan]


def picks(stage: Stage, mode: Mode, n=3000) -> Counter:
    rng = random.Random(7)
    return Counter(pick(stage, mode, rng) for _ in range(n))


def test_focus_is_nap_time_and_breaks_are_play_time():
    nap, play = picks(Stage.CONTENT, Mode.NAP), picks(Stage.CONTENT, Mode.PLAY)
    assert nap["nap"] / 3000 > 0.5 and nap["zoom"] == 0
    assert play["zoom"] / 3000 > 0.15 and play["nap"] / 3000 < 0.1


def test_grumpy_cats_sulk_instead_of_zooming():
    play = picks(Stage.GRUMPY, Mode.PLAY)
    assert play["zoom"] == 0 and play["sulk"] > 0


def test_angry_cats_only_sulk_wander_climb_or_nap():
    for stage in (Stage.PISSY, Stage.FURIOUS):
        chosen = set(picks(stage, Mode.PLAY))
        assert chosen <= {"sulk", "wander", "climb", "nap"}


def test_naps_mostly_happen_up_high():
    rng = random.Random(11)
    napped_on = Counter()
    for _ in range(200):
        body = body_on("floor", 40)
        plan = choose(a_cat(), body, SCAPE, Mode.NAP, rng, bowl_full=True, litter_due=False)
        if plan[-1].doing is Doing.NAP:
            carry_out(body, plan[:-1])
            napped_on[body.surface] += 1
    assert sum(napped_on.values()) > 50
    assert napped_on["floor"] < sum(napped_on.values()) / 3


@pytest.mark.parametrize("seed", range(5))
def test_every_plan_can_be_carried_out_and_keeps_the_cat_in_the_room(seed):
    rng = random.Random(seed)
    body = body_on("floor", 40)
    for _ in range(60):
        mode = rng.choice(list(Mode))
        cat = a_cat(mood=rng.uniform(0, 100), hunger=rng.choice([0, 90]))

        def inside(b: Body):
            assert -5 <= b.x <= SCAPE.width + 5 and 0 <= b.y <= SCAPE.floor.y

        plan = choose(cat, body, SCAPE, mode, rng, bowl_full=rng.random() < 0.5, litter_due=rng.random() < 0.1)
        carry_out(body, plan, dt=0.25, watch=inside)
        assert body.y == SCAPE.surface(body.surface).y
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_behavior.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.game.behavior'`

- [ ] **Step 3: Append the behaviour numbers**

Append to the end of `src/pomo/game/balance.py`, after one blank line:

```python
# --- behaviour (spec §3.1, §3.7, §6) ----------------------------------------
WALK_SPEED = 10.0  # columns per second
ZOOM_SPEED = 30.0
JUMP_BASE_S = 0.35
JUMP_PER_PX_S = 0.012
JUMP_ARC_PX = 4  # a jump rises this much plus half the height difference above the straight line
SIT_S = (8.0, 25.0)  # (min, max) seconds
LOAF_S = (15.0, 45.0)
NAP_S = (90.0, 300.0)
SULK_S = (20.0, 60.0)
EAT_S = 6.0
BEG_S = 10.0
AWAY_S = (20.0, 40.0)  # a trip through the litter door
LITTER_EVERY_S = (20 * 60.0, 40 * 60.0)
ZOOM_LEGS = (3, 5)
NAP_SPOTS = {"tree_top": 3, "tree_mid": 2, "shelf": 2, "floor": 1}  # cats like to nap up high
ACTIVITY_WEIGHTS = {  # per mode: focus is nap time, a break is play time (spec §3.1)
    "nap": {"nap": 60, "loaf": 20, "sit": 10, "wander": 8, "climb": 2},
    "play": {"zoom": 25, "wander": 25, "climb": 20, "sit": 15, "loaf": 10, "nap": 5},
    "relax": {"wander": 25, "climb": 15, "sit": 25, "loaf": 20, "nap": 15},
}
```

- [ ] **Step 4: Implement the behaviour**

`src/pomo/game/behavior.py`:

```python
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
```

- [ ] **Step 5: Run the tests**

Run: `uv run pytest -v`
Expected: `315 passed`

- [ ] **Step 6: Commit**

```bash
git add src/pomo/game/balance.py src/pomo/game/behavior.py tests/test_behavior.py
git commit -m "feat: cat movement (routes, walking, jump arcs) and activity choice by mode and mood" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: The world

**Files:**
- Create: `src/pomo/game/world.py`
- Test: `tests/test_world.py`

**Interfaces:**
- Consumes: Tasks 1 and 3; from milestone 2, `layout`, `MIN_WIDTH` and `MIN_HEIGHT`; from milestone 1, `Phase` and `Event`.
- Produces:
  - Constants: `MAX_DT = 1.0`, `UNINTERRUPTIBLE = {JUMP, AWAY, EAT}`, `FIRST_SPOT = 38`, `SPACING = 22`, `BEG_OFFSET = 18`, `BUBBLES`, `STAGE_FACE`.
  - `CatView(name, coat, pose, face, x, feet, facing=1, bubble=None)`. `x` is the centre column.
  - `RosterLine(name, hearts, stage)`
  - `RoomView(cats=(), roster=(), bowl_full=True)`
  - `mode_for(phase, started) -> Mode`
  - `World(cats, rng, width=MIN_WIDTH, height=MIN_HEIGHT)`:
    - Attributes: `.cats`, `.bodies`, `.litter_in`, `.scape`, `.mode`, `.bowl_full`.
    - Methods: `.apply(events)`, `.set_mode(mode)`, `.fit(width, height)`, `.refill()`, `.tick(dt)`, `.view() -> RoomView`.
- Behaviour:
  - **Mode changes:** a new mode drops every plan that isn't a jump, a litter trip or a meal.
  - **Resizing** rebuilds the room:
    - A cat mid-jump lands.
    - A cat out through the door drops its plan and walks back in fresh.
    - Every cat snaps onto its surface, inside the walkable range.
  - **Eating:** only one cat eats at a time. A cat that finds the bowl empty or taken walks `BEG_OFFSET` to the side and begs.
  - **The view:**
    - Cats out through the door are hidden.
    - Poses: `walk0`/`walk1` alternate every 3 columns walked; a jump shows `leap`; loaf, nap and sulk show `loaf`; everything else shows `sit`.
    - Faces: `sleep` while napping and `meh` while sulking; otherwise from the stage (content `ok`, grumpy `meh`, pissy and furious `mad`).
    - Bubbles: "nom" while eating, "meow" while begging, none while napping, otherwise the emoji for the cat's most urgent need.

- [ ] **Step 1: Write the failing tests**

`tests/test_world.py`:

```python
import random

import pytest

from pomo.game.behavior import Doing, Mode, walkable
from pomo.game.cat import Cat, Trait
from pomo.game.events import RuleBreak, RuleKind
from pomo.game.world import World, mode_for
from pomo.timer import Phase

TICK = 0.125


def world_with(*names: str, seed: int = 1, width: int = 70, height: int = 58) -> World:
    cats = [Cat(name, "tabby", Trait.CLINGY) for name in names]
    return World(cats, random.Random(seed), width, height)


def run(world: World, seconds: float, each=None) -> None:
    for _ in range(int(seconds / TICK)):
        world.tick(TICK)
        if each:
            each(world)


def test_a_new_room_has_its_cats_sitting_on_the_floor():
    world = world_with("Mango")
    view = world.view()
    (mango,) = view.cats
    assert (mango.name, mango.pose, mango.face, mango.feet) == ("Mango", "sit", "ok", world.scape.floor.y)
    assert [(r.name, r.hearts, r.stage) for r in view.roster] == [("Mango", 4, "content")]
    assert view.bowl_full


def test_cats_start_spaced_apart():
    world = world_with("Mango", "Pebble")
    xs = [c.x for c in world.view().cats]
    assert xs[1] - xs[0] >= 17


def test_rule_breaks_and_rewards_reach_every_cat():
    world = world_with("Mango", "Pebble")
    world.apply([RuleBreak(RuleKind.SKIP_BREAK)])
    assert [c.mood for c in world.cats] == [60, 60]
    assert [r.stage for r in world.view().roster] == ["grumpy", "grumpy"]


@pytest.mark.parametrize("phase, started, mode", [
    (Phase.FOCUS, False, Mode.RELAX), (Phase.FOCUS, True, Mode.NAP),
    (Phase.SHORT_BREAK, False, Mode.PLAY), (Phase.LONG_BREAK, True, Mode.PLAY),
])
def test_the_phase_sets_the_mode(phase, started, mode):
    assert mode_for(phase, started) is mode


@pytest.mark.parametrize("seed", range(3))
def test_cats_keep_moving_around_and_stay_in_the_room(seed):
    world = world_with("Mango", "Pebble", seed=seed)
    world.set_mode(Mode.PLAY)
    visited = set()

    def check(w: World):
        for view in w.view().cats:
            assert -10 <= view.x <= w.scape.width + 10
            assert 0 <= view.feet <= w.scape.floor.y
        visited.update(body.surface for body in w.bodies.values())

    run(world, 20 * 60, check)
    assert visited == {"floor", "tree_mid", "tree_top", "shelf"}


def test_focus_is_mostly_nap_time():
    world = world_with("Mango", seed=4)
    world.set_mode(Mode.NAP)
    faces = []
    run(world, 30 * 60, lambda w: faces.append(w.view().cats[0].face if w.view().cats else "away"))
    assert faces.count("sleep") / len(faces) > 0.5


def test_a_break_wakes_the_nappers():
    world = world_with("Mango", seed=5)
    world.set_mode(Mode.NAP)
    for _ in range(20000):
        world.tick(TICK)
        if world.view().cats and world.view().cats[0].face == "sleep":
            break
    assert world.view().cats[0].face == "sleep"
    world.set_mode(Mode.PLAY)
    world.tick(TICK)
    assert world.view().cats[0].face != "sleep"


def test_a_hungry_cat_eats_and_the_next_one_begs():
    world = world_with("Mango", "Pebble", seed=6)
    for cat in world.cats:
        cat.needs["hunger"] = 90
    bubbles = set()
    run(world, 60, lambda w: bubbles.update(c.bubble for c in w.view().cats))
    assert not world.bowl_full
    assert sorted(c.needs["hunger"] < 5 for c in world.cats) == [False, True]  # exactly one ate
    assert {"nom", "meow"} <= bubbles
    world.refill()
    run(world, 60)
    assert all(c.needs["hunger"] < 5 for c in world.cats)


def test_a_litter_trip_hides_the_cat_then_brings_it_back():
    world = world_with("Mango", seed=7)
    world.litter_in["Mango"] = 0
    seen = []
    run(world, 120, lambda w: seen.append(bool(w.view().cats)))
    assert False in seen and seen[-1] is True
    assert world.litter_in["Mango"] > 15 * 60


def test_needs_show_as_bubbles():
    world = world_with("Mango", seed=8)
    world.cats[0].needs["play"] = 90
    world.tick(TICK)
    body = world.bodies["Mango"]
    if body.step.doing is not Doing.NAP:
        assert world.view().cats[0].bubble == "🧶"


def test_faces_follow_the_mood():
    world = world_with("Mango", seed=9)
    world.cats[0].mood = 50
    world.bodies["Mango"].step = None
    world.bodies["Mango"].plan = []
    assert world.view().cats[0].face == "meh"
    world.cats[0].mood = 10
    assert world.view().cats[0].face == "mad"


def test_resizing_puts_every_cat_back_on_its_surface():
    world = world_with("Mango", seed=10)
    body = world.bodies["Mango"]
    body.surface, body.x, body.y = "shelf", 55.0, float(world.scape.shelf.y)
    world.fit(120, 80)
    assert body.y == world.scape.shelf.y
    lo, hi = walkable(world.scape.shelf)
    assert lo <= body.x <= hi
    assert body.step is None and body.plan == []


def test_resizing_mid_jump_lands_the_cat():
    world = world_with("Mango", seed=11)
    world.set_mode(Mode.PLAY)
    for _ in range(20000):
        world.tick(TICK)
        if world.bodies["Mango"].step and world.bodies["Mango"].step.doing is Doing.JUMP:
            break
    target = world.bodies["Mango"].step.surface
    world.fit(100, 70)
    assert world.bodies["Mango"].surface == target
    assert world.bodies["Mango"].y == world.scape.surface(target).y


def test_a_stalled_tick_is_capped_at_one_second():
    world = world_with("Mango")
    world.tick(3600)
    assert world.cats[0].needs["hunger"] == pytest.approx(100 / (3 * 3600))


def test_two_cats_never_eat_from_the_bowl_at_once():
    world = world_with("Mango", "Pebble", seed=6)
    for cat in world.cats:
        cat.needs["hunger"] = 90

    def one_at_a_time(w: World):
        eaters = [b for b in w.bodies.values() if b.step and b.step.doing is Doing.EAT]
        assert len(eaters) <= 1
        beggars = [b for b in w.bodies.values() if b.step and b.step.doing is Doing.BEG]
        for beggar in beggars:
            for eater in eaters:
                assert abs(beggar.x - eater.x) >= 17  # sitting beside, not on top

    run(world, 60, one_at_a_time)


def test_a_long_day_in_the_room_never_gets_stuck():
    world = world_with("Mango", "Pebble", "Tux", seed=12)
    world.cats[2].mood = 20  # one angry cat in the mix
    last_change = {name: 0.0 for name in world.bodies}
    previous = {}
    trips = set()
    t = 0.0
    for minute in range(4 * 60):  # four hours of 25/5 pomodoros
        world.set_mode(Mode.NAP if minute % 30 < 25 else Mode.PLAY)
        if minute % 90 == 0:
            world.refill()
        for _ in range(60):
            world.tick(1.0)
            t += 1.0
            for name, body in world.bodies.items():
                state = (body.surface, round(body.x), body.step.doing if body.step else None)
                if state != previous.get(name):
                    previous[name], last_change[name] = state, t
                if body.step and body.step.doing is Doing.AWAY:
                    trips.add(name)
                if body.step is None or body.step.doing is not Doing.JUMP:
                    assert body.y == world.scape.surface(body.surface).y
            for name in world.bodies:
                assert t - last_change[name] <= 400  # longest nap is 300 s
    assert trips == {"Mango", "Pebble", "Tux"}  # everyone used the litter door
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_world.py -v`
Expected: FAIL during collection with `ModuleNotFoundError: No module named 'pomo.game.world'`

- [ ] **Step 3: Implement the world**

`src/pomo/game/world.py`:

```python
"""The cat room over time: the cats, where they are, the bowl, and the mood of the moment (spec §3, §6).

Pure: `tick(dt)` moves time on, `apply(events)` feeds in the session's rule breaks and
rewards, and `view()` describes what to draw. Randomness comes from an injected RNG.
"""

from __future__ import annotations

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from pomo.game import balance
from pomo.game.behavior import Body, Doing, Mode, Step, advance, choose, clamp, walkable
from pomo.game.cat import Cat, Stage
from pomo.game.events import Event
from pomo.game.playscape import MIN_HEIGHT, MIN_WIDTH, Playscape, layout
from pomo.timer import Phase

MAX_DT = 1.0  # a stalled tick (process suspended) never jumps the room forward more than this
UNINTERRUPTIBLE = {Doing.JUMP, Doing.AWAY, Doing.EAT}  # finished even when the phase changes
FIRST_SPOT = 38  # where the first cat sits when the room opens
SPACING = 22
BEG_OFFSET = 18  # a cat that finds the bowl taken sits this far to the side
BUBBLES = {"hunger": "🍗", "play": "🧶", "affection": "♥"}
STAGE_FACE = {Stage.CONTENT: "ok", Stage.GRUMPY: "meh", Stage.PISSY: "mad", Stage.FURIOUS: "mad"}


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
class RoomView:
    cats: tuple[CatView, ...] = ()
    roster: tuple[RosterLine, ...] = ()
    bowl_full: bool = True


def mode_for(phase: Phase, started: bool) -> Mode:
    """Focus under way → nap time; a break → play time; nothing started → relaxed."""
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
                body.plan = []  # out of sight: plan the walk back in once it returns
                continue
            if body.step is not None and body.step.doing is Doing.JUMP:
                body.surface = body.step.surface  # land it now
            surface = self.scape.surface(body.surface)
            body.x, body.y = clamp(body.x, *walkable(surface)), float(surface.y)
            self._stop(body)

    def refill(self) -> None:
        self.bowl_full = True

    # --- time --------------------------------------------------------------------

    def tick(self, dt: float) -> None:
        dt = min(max(dt, 0.0), MAX_DT)
        for cat in self.cats:
            cat.tick(dt)
            body = self.bodies[cat.name]
            self.litter_in[cat.name] -= dt
            if body.step is None:
                if not body.plan:
                    body.plan = self._plan(cat, body)
                body.step = body.plan.pop(0)
                if body.step.doing is Doing.EAT and not self._bowl_free(body):
                    # someone else got there first: sit beside them and beg
                    body.step = Step(Doing.WALK, x=clamp(body.x - BEG_OFFSET, *walkable(self.scape.floor)))
                    body.plan.insert(0, Step(Doing.BEG, seconds=balance.BEG_S))
            finished = advance(body, self.scape, dt)
            if finished is not None and finished.doing is Doing.EAT and self.bowl_full:
                cat.eat()
                self.bowl_full = False

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
        return RoomView(tuple(cats), roster, self.bowl_full)


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
    return STAGE_FACE[cat.stage]


def _bubble(cat: Cat, doing: Doing) -> str | None:
    if doing is Doing.EAT:
        return "nom"
    if doing is Doing.BEG:
        return "meow"
    if doing is Doing.NAP:
        return None
    want = cat.wants()
    return BUBBLES[want] if want else None
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest -v`
Expected: `336 passed`

- [ ] **Step 5: Commit**

```bash
git add src/pomo/game/world.py tests/test_world.py
git commit -m "feat: the world: cats over time, bowl, litter trips, phase modes, resizing" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Draw the living room, and wire it into the app

**Files:**
- Modify: `src/pomo/render/theme.py` (append)
- Replace: `src/pomo/render/scene.py`, `tests/test_scene.py`, `src/pomo/ui/app.py`, `tests/test_app.py`, `README.md`

**Interfaces:**
- Consumes: from Task 4, `World`, `CatView`, `RoomView`, `RosterLine` and `mode_for`; from Task 1, `Cat` and `Trait`; from Task 2, `sprites.cat(pose, face, facing)`.
- Produces:
  - `scene.draw(canvas, timer, room_view: RoomView, frame)`. `scene.CatSprite` is gone.
  - `scene.ROSTER_ROW = 14`: a "cats" header, then one `name(6) hearts(♥/♡ ×5) stage` line per cat, with the stage coloured by `STAGE_COLORS`.
  - `PomoApp(..., rng: random.Random | None = None)` with `.world`.
  - Each tick computes `dt` from the clock, calls `world.set_mode(mode_for(...))` and then `world.tick(dt)`.
  - `handle(events)` calls `world.apply(events)` first.
  - `draw_scene` calls `world.fit(max(MIN_WIDTH, room_w), max(MIN_HEIGHT, room_h))` before drawing.

- [ ] **Step 1: Write the failing tests**

Replace all of `tests/test_scene.py`:

```python
import pytest
from rich.color import Color

from canvas_reading import read_big, screen_text
from pomo.clock import FakeClock
from pomo.game.playscape import MIN_HEIGHT, layout
from pomo.game.world import CatView, RoomView, RosterLine
from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.render.scene import (
    BLINK_EVERY, CLOCK_PY, CLOCK_X, PANEL_WIDTH, ROSTER_ROW, TWINKLE_FRAMES, blinking, draw,
)
from pomo.timer import PomodoroTimer, TimerSettings

W, H = 100, 29  # 100×30 terminal minus the message line
ROOM = layout(W - PANEL_WIDTH, H * 2)
FLOOR = ROOM.floor.y
MANGO = CatView("Mango", "tabby", "sit", "ok", x=38.5, feet=FLOOR)  # centre 38.5 → left edge at room column 30


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def timer(clock):
    return PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), clock)


def render(timer, cats=(), frame=1, width=W, height=H, roster=(), bowl_full=True) -> Canvas:
    canvas = Canvas(width, height, (0, 0, 0))
    draw(canvas, timer, RoomView(tuple(cats), tuple(roster), bowl_full), frame)
    return canvas


def clock_ink(canvas: Canvas) -> set:
    return {canvas.pixel_at(x, py) for x in range(CLOCK_X, CLOCK_X + 25)
            for py in range(CLOCK_PY, CLOCK_PY + 7)} - {theme.PANEL_BG}


def test_the_panel_shows_the_phase_counts_and_keys(timer):
    text = screen_text(render(timer))
    for expected in ["● FOCUS", "space to start", "pomodoro 1 of 4", "next: 5 min break",
                     "space start/pause", "q quit"]:
        assert expected in text


def test_the_clock_shows_the_time_left(timer, clock):
    assert read_big(render(timer), CLOCK_X, CLOCK_PY, theme.PANEL_BG) == "25:00"
    timer.start()
    clock.advance(61)
    assert read_big(render(timer), CLOCK_X, CLOCK_PY, theme.PANEL_BG) == "23:59"


def test_the_clock_colour_follows_the_phase(timer, clock):
    assert clock_ink(render(timer)) == {theme.IDLE_CLOCK}
    timer.start()
    assert clock_ink(render(timer)) == {theme.FOCUS}
    clock.advance(25 * 60)
    timer.tick()
    assert clock_ink(render(timer)) == {theme.BREAK}


def test_panel_text_never_spills_into_the_room(clock):
    timer = PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 1), clock)
    timer.start()
    clock.advance(25 * 60)
    timer.tick()
    timer.pause()  # "● LONG BREAK" / "paused"
    canvas = render(timer, roster=[RosterLine("Butterscotch", 5, "furious")])
    assert "LONG BREAK" in screen_text(canvas)
    assert all(canvas.row_text(y)[PANEL_WIDTH:].strip() == "" for y in range(H))


def test_a_clock_too_wide_for_the_panel_is_cut_at_the_edge(timer):
    timer.adjust(+100)  # 125:00 would be 31 columns
    canvas = render(timer)
    assert all(canvas.pixel_at(PANEL_WIDTH, py) == theme.ROOM_BG for py in range(CLOCK_PY, CLOCK_PY + 7))


def test_a_clock_of_100_minutes_or_more_closes_up_to_fit_the_panel(clock):
    timer = PomodoroTimer(TimerSettings.from_minutes(120, 5, 15, 4), clock)
    canvas = render(timer)
    assert read_big(canvas, CLOCK_X, CLOCK_PY, theme.PANEL_BG, gap=0) == "120:00"
    assert read_big(render(PomodoroTimer(TimerSettings.from_minutes(25, 5, 15, 4), clock)),
                    CLOCK_X, CLOCK_PY, theme.PANEL_BG) == "25:00"  # normal clocks keep their spacing


def test_the_room_has_its_furniture(timer):
    canvas = render(timer)
    assert canvas.pixel_at(PANEL_WIDTH + ROOM.tree_top.x0, ROOM.tree_top.y) == theme.PLATFORM
    assert canvas.pixel_at(PANEL_WIDTH + ROOM.shelf.x0, ROOM.shelf.y) == theme.SHELF
    assert canvas.pixel_at(PANEL_WIDTH + ROOM.door.x, ROOM.door.y) == sprites.DOOR_PALETTE["o"]
    assert canvas.pixel_at(PANEL_WIDTH, FLOOR) == theme.FLOOR


def test_the_bowl_shows_whether_it_has_kibble(timer):
    kibble = (PANEL_WIDTH + ROOM.bowl.x + 1, ROOM.bowl.y)  # BOWL_FULL row 0: ".kkkkkk."
    assert render(timer).pixel_at(*kibble) == sprites.BOWL_PALETTE["k"]
    assert render(timer, bowl_full=False).pixel_at(*kibble) == sprites.BOWL_PALETTE["o"]


def test_a_cat_stands_where_the_world_says(timer):
    canvas = render(timer, [MANGO])
    tabby = sprites.COATS["tabby"]
    x = PANEL_WIDTH + 30
    assert canvas.pixel_at(x + 1, FLOOR - 1) == tabby["o"]  # bottom outline, just above the floor
    assert canvas.pixel_at(x + 2, FLOOR - 16) == tabby["o"]  # ear tip
    assert canvas.pixel_at(x, FLOOR - 16) == theme.ROOM_BG  # transparent corner


def test_a_cat_on_the_tree_top_fits_in_the_smallest_room(timer):
    small = layout(70, MIN_HEIGHT)
    top_cat = CatView("Pebble", "grey", "sit", "ok", x=small.tree_top.x0 + 8.5, feet=small.tree_top.y)
    canvas = render(timer, [top_cat], width=PANEL_WIDTH + 70, height=MIN_HEIGHT // 2)
    assert canvas.pixel_at(PANEL_WIDTH + small.tree_top.x0 + 2, 0) == sprites.COATS["grey"]["o"]  # ear tip


def test_higher_cats_are_drawn_behind_lower_ones(timer):
    back = CatView("Pebble", "grey", "sit", "ok", x=16.5, feet=ROOM.tree_mid.y)
    front = CatView("Mango", "tabby", "sit", "ok", x=16.5, feet=FLOOR)
    canvas = render(timer, [front, back])  # given in the wrong order on purpose
    # the floor cat's ear tip overlaps the tree-mid cat's body
    assert canvas.pixel_at(PANEL_WIDTH + 8 + 2, FLOOR - 16) == sprites.COATS["tabby"]["o"]


def test_side_view_cats_face_the_way_they_walk(timer):
    def eye_column(facing: int) -> int:
        walker = CatView("Mango", "tabby", "walk0", "ok", x=40, feet=FLOOR, facing=facing)
        canvas = render(timer, [walker], frame=10)
        eye_py = FLOOR - 13 + 4  # side sprites are 13 tall; row 4 holds the eye
        return next(x for x in range(PANEL_WIDTH, W) if canvas.pixel_at(x, eye_py) == sprites.COATS["tabby"]["e"])

    centre = PANEL_WIDTH + 40
    assert eye_column(1) > centre > eye_column(-1)


def test_a_cat_mid_jump_is_drawn_in_the_air(timer):
    leaper = CatView("Mango", "tabby", "leap", "ok", x=40, feet=FLOOR - 10)
    canvas = render(timer, [leaper])
    assert all(canvas.pixel_at(x, FLOOR - 1) != sprites.COATS["tabby"]["o"]
               for x in range(PANEL_WIDTH + 25, PANEL_WIDTH + 55))  # nothing touching the floor


def test_ok_cats_blink_now_and_then():
    blinks = [frame for frame in range(BLINK_EVERY) if blinking("Mango", frame)]
    assert len(blinks) == 2
    assert blinking("Mango", blinks[0] + BLINK_EVERY)


def test_a_blinking_cat_closes_its_eyes(timer):
    frame = next(f for f in range(BLINK_EVERY) if blinking("Mango", f))
    eye = (PANEL_WIDTH + 30 + 2, FLOOR - 16 + 5)  # head row 5: "ofekeff", column 2 is eye
    assert render(timer, [MANGO], frame=frame + 10).pixel_at(*eye) == sprites.COATS["tabby"]["e"]
    assert render(timer, [MANGO], frame=frame).pixel_at(*eye) != sprites.COATS["tabby"]["e"]


def test_sleeping_cats_float_a_z(timer):
    sleeper = CatView("Pebble", "grey", "loaf", "sleep", x=ROOM.tree_top.x0 + 8.5, feet=ROOM.tree_top.y)
    assert "z" in screen_text(render(timer, [sleeper]))
    assert "z" not in screen_text(render(timer, [MANGO]))


def test_bubbles_float_over_the_cat(timer):
    beggar = CatView("Mango", "tabby", "sit", "ok", x=38.5, feet=FLOOR, bubble="meow")
    text = screen_text(render(timer, [beggar]))
    assert "meow" in text
    row = next(y for y in range(H) if "meow" in render(timer, [beggar]).row_text(y))
    assert row < (FLOOR - 16) // 2  # above the head


def test_the_roster_lists_each_cat_with_hearts_and_mood(timer):
    roster = [RosterLine("Mango", 4, "content"), RosterLine("Pebble", 2, "grumpy")]
    canvas = render(timer, roster=roster)
    assert canvas.row_text(ROSTER_ROW).strip() == "cats"
    assert canvas.row_text(ROSTER_ROW + 1).strip() == "Mango  ♥♥♥♥♡ content"
    assert canvas.row_text(ROSTER_ROW + 2).strip() == "Pebble ♥♥♡♡♡ grumpy"
    (grumpy,) = [s for s in canvas.row_segments(ROSTER_ROW + 2) if "grumpy" in s.text]
    assert grumpy.style.color == Color.from_rgb(*theme.STAGE_COLORS["grumpy"])


def test_no_cats_means_no_roster_header(timer):
    assert "cats" not in screen_text(render(timer))


def test_the_stars_twinkle(timer):
    frames = [render(timer, frame=f * TWINKLE_FRAMES) for f in range(3)]
    keys = [tuple(c.row_key(y) for y in range(H)) for c in frames]
    assert len(set(keys)) == 3


@pytest.mark.parametrize("size", [(0, 0), (10, 3), (40, 10), (PANEL_WIDTH, H)])
def test_small_or_empty_screens_do_not_crash(timer, size):
    render(timer, [MANGO], width=size[0], height=size[1], roster=[RosterLine("Mango", 4, "content")])
```

Replace all of `tests/test_app.py`. The earlier tests stay, `make_app` now seeds the world, and five tests are new at the end.

```python
import random

from textual.widgets import Static

from canvas_reading import read_big, screen_text
from pomo.clock import FakeClock
from pomo.config import Config
from pomo.game.behavior import Mode
from pomo.render import sprites, theme
from pomo.render.scene import CLOCK_PY, CLOCK_X, PANEL_WIDTH
from pomo.timer import Phase
from pomo.ui.app import PomoApp
from pomo.ui.dialogs import ConfirmScreen

MIN = 60.0
SIZE = (100, 30)


class FakeNotifier:
    def __init__(self):
        self.pings = []

    def send(self, ping):
        self.pings.append(ping)


def make_app(**config):
    clock, notifier = FakeClock(), FakeNotifier()
    return PomoApp(Config(**config), clock, notifier, rng=random.Random(0)), clock, notifier


def text(app, widget_id):
    return str(app.main.query_one(f"#{widget_id}", Static).render())


def clock_value(app):
    return read_big(app.main.stage.canvas, CLOCK_X, CLOCK_PY, theme.PANEL_BG)


def on_screen(app):
    return screen_text(app.main.stage.canvas)


async def test_shows_a_ready_focus():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        assert clock_value(app) == "25:00"
        assert "● FOCUS" in on_screen(app)
        assert "next: 5 min break" in on_screen(app)


async def test_space_starts_and_the_clock_counts_down():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(61)
        app.tick()
        assert clock_value(app) == "23:59"


async def test_finishing_focus_pings_once_and_starts_the_break():
    app, clock, notifier = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(25 * MIN)
        app.tick()
        assert app.session.timer.phase is Phase.SHORT_BREAK
        assert [p.title for p in notifier.pings] == ["🍅 Pomodoro done!"]
        assert "Time for a break" in text(app, "message")


async def test_a_sleep_wake_jump_sends_one_ping_not_a_flood():
    app, clock, notifier = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(3 * 60 * MIN)  # several phases went by
        app.tick()
        assert len(notifier.pings) == 1


async def test_plus_and_minus_adjust_the_clock():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("plus")
        assert clock_value(app) == "30:00"
        await pilot.press("minus", "minus")
        assert clock_value(app) == "20:00"


async def test_skipping_focus_asks_first_and_no_leaves_it_alone():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s")
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press("n")
        assert app.session.timer.phase is Phase.FOCUS
        assert not isinstance(app.screen, ConfirmScreen)


async def test_confirmed_skip_breaks_the_rule_without_a_ping():
    app, _, notifier = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s", "y")
        assert app.session.timer.phase is Phase.SHORT_BREAK
        assert "(−25)" in text(app, "message")
        assert notifier.pings == []


async def test_resetting_an_unstarted_focus_does_not_ask():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("r")
        assert not isinstance(app.screen, ConfirmScreen)


async def test_keys_are_ignored_while_the_dialog_is_open():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s")
        await pilot.press("space", "s", "r", "plus", "q")
        assert len(app.screen_stack) == 2  # no stacked dialogs
        assert not app.session.timer.running
        assert app.session.timer.length == 25 * MIN
        assert app.is_running


async def test_a_stale_yes_does_not_skip_the_next_phase():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space", "s")  # asked while in focus...
        clock.advance(25 * MIN)
        app.tick()  # ...focus finished on its own meanwhile
        await pilot.press("y")
        assert app.session.timer.phase is Phase.SHORT_BREAK  # the break was not skipped
        assert "phase changed" in text(app, "message")


async def test_quit_before_starting_just_quits():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running


async def test_quit_mid_focus_asks_first():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(1)
        await pilot.press("q")
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.press("y")
        await pilot.pause()
        assert not app.is_running


async def test_messages_fade_after_ten_seconds():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("s", "y")
        assert text(app, "message")
        clock.advance(11)
        app.tick()
        assert text(app, "message") == ""


def toasts(app):
    return [str(toast.render()) for toast in app.screen.query("Toast")]


async def test_startup_warnings_are_shown_in_full_and_outlive_the_message_line():
    warning = "~/.config/pomo/config.toml holds your ntfy topic but others can read it. Run: chmod 600 ~/.config/pomo/config.toml"
    clock = FakeClock()
    app = PomoApp(Config(), clock, FakeNotifier(), warnings=[warning])
    async with app.run_test(size=SIZE, notifications=True) as pilot:
        await pilot.pause()
        assert any(warning in toast for toast in toasts(app))
        clock.advance(11)
        app.tick()
        await pilot.pause()
        assert any(warning in toast for toast in toasts(app))


async def test_the_command_palette_cannot_quit_around_the_confirm_dialog():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(1)
        await pilot.press("ctrl+p")
        assert type(app.screen).__name__ != "CommandPalette"
        assert app.is_running


async def test_a_stale_yes_to_quit_still_quits_once_quitting_is_free():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(1)
        await pilot.press("q")  # asked mid-focus...
        clock.advance(25 * MIN)
        app.tick()  # ...but the focus ended, and quitting on a break is free
        await pilot.press("y")
        await pilot.pause()
        assert not app.is_running


async def test_a_stale_yes_after_a_full_cycle_leaves_the_new_focus_alone():
    app, clock, _ = make_app(focus=1, short_break=1)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        clock.advance(30)
        await pilot.press("r")  # asked to restart focus 1...
        clock.advance(120)
        app.tick()  # ...focus 1 and its break both ended; focus 2 has run 30 s
        assert app.session.timer.phase is Phase.FOCUS
        await pilot.press("y")
        assert app.session.timer.remaining() == 30  # focus 2 was not reset
        assert "nothing was reset" in text(app, "message")


class FakeKeepAwake:
    def __init__(self):
        self.on = False
        self.changes = []

    def hold(self, on):
        if on != self.on:
            self.on = on
            self.changes.append(on)


async def test_the_mac_is_kept_awake_only_while_a_phase_runs():
    clock, awake = FakeClock(), FakeKeepAwake()
    app = PomoApp(Config(), clock, FakeNotifier(), keep_awake=awake)
    async with app.run_test(size=SIZE) as pilot:
        assert awake.changes == []  # nothing running yet
        await pilot.press("space")
        assert awake.on
        await pilot.press("space")  # paused
        assert not awake.on
        await pilot.press("space")
        clock.advance(25 * MIN)
        app.tick()  # the break starts on its own and keeps running
        assert awake.on
        await pilot.press("q")  # quitting on a break is free
        await pilot.pause()
    assert awake.changes == [True, False, True, False]


async def test_the_room_has_mango_in_it():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        canvas = app.main.stage.canvas
        fur = sprites.COATS["tabby"]["f"]
        assert any(canvas.pixel_at(x, py) == fur
                   for x in range(PANEL_WIDTH, canvas.width) for py in range(canvas.height * 2))


async def test_the_stage_fills_the_screen_above_the_message_line():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        canvas = app.main.stage.canvas
        assert (canvas.width, canvas.height) == (100, 29)


async def test_each_tick_advances_the_animation():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        before = app.frame
        app.tick()
        assert app.frame == before + 1


async def test_an_unchanged_tick_repaints_nothing():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        app.frame = 1  # frames 2 → 3: no blink, no twinkle, and the timer isn't running
        app.tick()
        calls = []
        for widget in (app.main.stage, app.main.query_one("#message")):
            original = widget.refresh
            widget.refresh = lambda *a, _w=widget.id, _o=original, **k: (calls.append((_w, a, k)), _o(*a, **k))[1]
        app.tick()
        assert calls == []


async def test_the_roster_shows_mango_and_his_mood():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        assert "Mango  ♥♥♥♥♡ content" in on_screen(app)
        await pilot.press("s", "y")  # skipping a focus: −25
        assert app.world.cats[0].mood == 55
        assert "Mango  ♥♥♡♡♡ grumpy" in on_screen(app)


async def test_the_phase_sets_the_cats_mode():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE) as pilot:
        app.tick()
        assert app.world.mode is Mode.RELAX
        await pilot.press("space")
        app.tick()
        assert app.world.mode is Mode.NAP
        clock.advance(25 * MIN)
        app.tick()
        assert app.world.mode is Mode.PLAY


async def test_time_passing_moves_the_cats():
    app, clock, _ = make_app()
    async with app.run_test(size=SIZE):
        seen = set()
        for _ in range(240):
            clock.advance(0.5)
            app.tick()
            (mango,) = app.world.view().cats or (None,)
            seen.add(None if mango is None else (round(mango.x), mango.pose))
        assert len(seen) > 5


async def test_the_world_fits_the_room_on_screen():
    app, _, _ = make_app()
    async with app.run_test(size=SIZE):
        assert (app.world.scape.width, app.world.scape.height) == (70, 58)


async def test_a_terminal_below_the_minimum_keeps_the_minimum_room():
    app, _, _ = make_app()
    async with app.run_test(size=(60, 20)):
        assert (app.world.scape.width, app.world.scape.height) == (70, 54)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `uv run pytest tests/test_scene.py tests/test_app.py -v`
Expected: `test_scene.py` fails during collection with `ImportError: cannot import name 'ROSTER_ROW' from 'pomo.render.scene'`, and `test_app.py` fails with `TypeError: PomoApp.__init__() got an unexpected keyword argument 'rng'`.

- [ ] **Step 3: Append the roster colours**

Append to the end of `src/pomo/render/theme.py`, after one blank line:

```python
# cat roster
HEART = hex_rgb("#f7768e")
HEART_EMPTY = hex_rgb("#3b4261")
STAGE_COLORS = {
    "content": hex_rgb("#9ece6a"),
    "grumpy": hex_rgb("#e0af68"),
    "pissy": hex_rgb("#ff9e64"),
    "furious": hex_rgb("#ff4a3d"),
}
```

- [ ] **Step 4: Replace the scene**

`src/pomo/render/scene.py`:

```python
"""The whole screen: the timer panel on the left, the cat room on the right (spec §6–§7).

Pure: the timer, a RoomView from the world and an animation frame number in, pixels
out. It never reads the clock and never changes the game.
"""

from __future__ import annotations

from pomo.game.playscape import Box, Playscape, layout
from pomo.game.world import CatView, RoomView, RosterLine
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
KEY_HINTS = ("space start/pause   s skip", "r reset  +/- 5 min  q quit")

BLINK_EVERY = 48  # frames: about every 6 s at 8 fps
BLINK_FRAMES = 2
STARS = ((2, 3), (9, 2), (8, 8))  # inside the window
TWINKLE_FRAMES = 12


def draw(canvas: Canvas, timer: PomodoroTimer, room_view: RoomView, frame: int) -> None:
    canvas.fill(0, 0, canvas.width, canvas.height, theme.ROOM_BG)
    _panel(canvas, timer, room_view.roster)
    room = layout(max(0, canvas.width - PANEL_WIDTH), canvas.height * 2)
    _room(canvas, PANEL_WIDTH, room, room_view, frame)


def phase_color(timer: PomodoroTimer) -> RGB:
    if not timer.running:
        return theme.IDLE_CLOCK
    return theme.BREAK if timer.phase.is_break else theme.FOCUS


# --- timer panel ------------------------------------------------------------


def _panel(canvas: Canvas, timer: PomodoroTimer, roster: tuple[RosterLine, ...]) -> None:
    canvas.fill(0, 0, PANEL_WIDTH, canvas.height, theme.PANEL_BG)
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
    if roster:
        _panel_text(canvas, ROSTER_ROW, "cats", theme.DIM)
    for i, line in enumerate(roster):
        row = ROSTER_ROW + 1 + i
        _panel_text(canvas, row, line.name[:6], theme.TEXT)
        hearts_end = canvas.text(ROSTER_HEARTS_X, row, "♥" * line.hearts, theme.HEART)
        canvas.text(hearts_end, row, "♡" * (5 - line.hearts), theme.HEART_EMPTY)
        canvas.text(ROSTER_STAGE_X, row, line.stage, theme.STAGE_COLORS[line.stage])
    first_hint_row = canvas.height - len(KEY_HINTS) - 1
    for i, hint in enumerate(KEY_HINTS):
        _panel_text(canvas, first_hint_row + i, hint, theme.DIM)


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
    for cat in sorted(room_view.cats, key=lambda c: (c.feet, c.x)):  # back (high up) to front (floor)
        _cat(canvas, ox, cat, frame)


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


def _cat(canvas: Canvas, ox: int, cat: CatView, frame: int) -> None:
    face = "blink" if cat.face == "ok" and blinking(cat.name, frame) else cat.face
    grid = sprites.cat(cat.pose, face, cat.facing)
    width = len(grid[0])
    left = ox + round(cat.x - width / 2)
    top = cat.feet - len(grid)
    canvas.sprite(left, top, grid, sprites.COATS[cat.coat])
    if face == "sleep":
        step = (frame // 6) % 3
        canvas.text(left + width - 2 + step % 2, top // 2 - step, "z", theme.SLEEP_Z, bold=True)
    elif cat.bubble:
        canvas.text(left + width // 2 - 1, top // 2 - 1, cat.bubble, theme.TEXT, bold=True)


def blinking(name: str, frame: int) -> bool:
    offset = sum(map(ord, name))  # stable per cat (hash() changes every run)
    return (frame + offset) % BLINK_EVERY < BLINK_FRAMES
```

- [ ] **Step 5: Replace the app**

`src/pomo/ui/app.py`:

```python
"""The Textual app: the timer panel and the cat room on one canvas, plus a message line."""

from __future__ import annotations

import random
from collections.abc import Callable

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
from pomo.game.world import World, mode_for
from pomo.notify import Notifies, ping_for
from pomo.render import scene
from pomo.render.canvas import Canvas
from pomo.session import Action, Session
from pomo.timer import TimerSettings, Transition
from pomo.ui import view
from pomo.ui.dialogs import ConfirmScreen
from pomo.ui.stage import Stage

TICK_S = 1 / 8  # 8 fps: the session ticks and the scene redraws together
MESSAGE_TTL_S = 10.0
WARNING_TTL_S = 60.0  # startup warnings are toasts: they wrap in full and outlive the message line
BLOCKED_WHILE_CONFIRMING = {"toggle", "adjust", "skip", "reset", "request_quit"}


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

    @property
    def stage(self) -> Stage:
        return self.query_one(Stage)

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
        now = self.clock.now()
        dt, self._last_tick = now - self._last_tick, now
        self.frame += 1
        self.handle(self.session.tick())
        timer = self.session.timer
        self.world.set_mode(mode_for(timer.phase, timer.started))
        self.world.tick(dt)
        self.refresh_view()

    def draw_scene(self, canvas: Canvas) -> None:
        # The room on screen decides the geometry; below the minimum the cats keep the minimum room.
        room_w, room_h = canvas.width - scene.PANEL_WIDTH, canvas.height * 2
        self.world.fit(max(MIN_WIDTH, room_w), max(MIN_HEIGHT, room_h))
        scene.draw(canvas, self.session.timer, self.world.view(), self.frame)

    def handle(self, events: list[Event]) -> None:
        self.world.apply(events)
        self._transitions += sum(isinstance(e, Transition) for e in events)
        finished = [e for e in events if isinstance(e, Transition) and e.completed]
        if finished:
            # A sleep/wake jump can finish several phases in one tick: ping once, for the latest.
            self.notifier.send(ping_for(finished[-1], self.config))
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
        self.main.show(self._message)
        # A sleeping Mac stops the clock, so stay awake exactly while a phase runs.
        self.keep_awake.hold(self.session.timer.running)

    def on_unmount(self) -> None:
        self.keep_awake.hold(False)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        return not (self.confirming and action in BLOCKED_WHILE_CONFIRMING)

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
            elif action is Action.QUIT:
                self._guarded(action, perform)  # still wants out: quit now if it's free, else ask at today's price
            else:
                done = "skipped" if action is Action.SKIP else "reset"
                self.show_message(f"The phase changed while you were deciding, so nothing was {done}.")
                self.refresh_view()

        self.push_screen(ConfirmScreen(view.confirm_question(self.session.timer, action, cost)), answered)
```

- [ ] **Step 6: Replace the README**

`README.md`:

````markdown
# pomo

A pomodoro timer for your terminal, with a room full of pixel-art cats. Mango lives in the
room: he naps up high while you focus, gets the zoomies on your breaks, eats from the bowl
when he's hungry, pops out through the litter door now and then, and remembers every rule
you break. The toolbar, more cats, and real consequences arrive in later milestones.

Needs a terminal with 24-bit colour and at least 100×30 cells. iTerm2 and Ghostty are the targets.

## Install

```bash
uv tool install .    # run from this directory; puts `pomo` on your PATH
```

## Use

```bash
pomo                               # 25 min focus, 5 min breaks, 15 min long break every 4
pomo --focus 50 --short-break 10
pomo --help                        # every flag, key and config option
pomo --gallery                     # every cat pose, face and coat, for tuning the art
```

Keys: `space` start/pause · `s` skip · `r` reset · `+`/`-` 5 min · `q` quit

Skipping or abandoning a focus, skipping a break, or pausing a focus for more than
3 minutes breaks a rule. `pomo` asks before letting you, because the cats will remember.

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

- [ ] **Step 7: Run everything**

Run: `uv run pytest -v`
Expected: `347 passed`

- [ ] **Step 8: Look at it**

Using a scratch script that isn't committed:
1. Build a `PomoApp` with `rng=random.Random(3)`.
2. Replace its world with three cats for the picture: Mango (tabby, clingy), Pebble (grey, chill, play need 85) and Tux (tuxedo, diva, mood 30).
3. Start a focus and run the fake clock through the whole focus in 0.5 s ticks, then 70 s into the break in 0.125 s ticks.
4. Call `export_screenshot()` and convert the SVG to a PNG with headless Chrome.

Check each of these:
- Cats stand on their surfaces: a napper high up with a `z`, and a cat wanting to play showing 🧶.
- The roster shows three lines with hearts and coloured moods.
- The clock is green during the break.

Then run `uv run pomo --focus 1 --short-break 1` in a real terminal (or a pseudo-terminal run) and watch Mango move between the floor, the tree and the shelf.

- [ ] **Step 9: Commit**

```bash
git add src/pomo/render/theme.py src/pomo/render/scene.py tests/test_scene.py src/pomo/ui/app.py tests/test_app.py README.md
git commit -m "feat: the living room on screen: moving cats, bubbles, bowl state, cat roster" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
