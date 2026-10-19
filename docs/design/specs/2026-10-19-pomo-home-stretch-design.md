# `pomo` home stretch: consequences, progression and polish

**Date:** 2026-10-19
**Status:** Decided. This round was handed over with "take the reins": the decisions below are calls made while building, not questions left open.
**Builds on:** [the main design](2026-09-29-pomo-cats-design.md) and [the daily-driver addendum](2026-10-03-pomo-daily-driver-design.md). Where this differs from them, this wins.

## 1. Purpose

This round builds what the main spec still promised: the consequences of breaking the rules (milestone 6), treats and what they buy (milestone 6), and the polish that's worth having (milestone 7). After it, pomo is the whole game the spec describes, apart from the cuts in §9.

**Success:**
- Breaking the rules has visible, recoverable consequences: a mess to clean up, a bowl to stand back up, a cat in your way.
- Sticking to your pomodoros earns treats, and treats buy things that change the room and bring in new cats.
- Nothing here gets between you and the timer. The time is always readable, and nothing asks for your attention mid-focus.

## 2. Decisions that differ from the main spec

| Topic | Main spec | Now | Why |
|---|---|---|---|
| A cat on the clock | Digits and progress bar covered | The big digits are covered, and the state line under the phase shows the time as small text, e.g. `18:42 · Tux is on it` | A timer that hides the time is broken. The punishment is a furious cat in your face, not losing track of time. |
| Poop's mood drain | −2 per 10 min per poop, no limit | The same, but poop alone can't take a cat below 15 | Only you make a cat furious, by breaking rules (in the spirit of §3.4's "anger only comes from breaking rules"). Poop instead pins a pissy cat at pissy until you scoop, so it never cools down. |
| Wall shelf #2 | A new mid-level surface | Cut | At 100×30 there's nowhere to put another shelf that a cat can sit on without overlapping the tree, the shelf or the window. |
| Hammock | Hung under the top of the cat tree | Hung from the wall shelf's brackets, low over the floor | Under the tree top, a cat in it would overlap both platforms. |
| Keys for items | `6`, `7`, … for unlocked items, in order | Fixed: `6` tuna, `7` catnip, `8` laser. A button appears once you own the item. | Keys that never move can become muscle memory. |
| Tuna | Click a cat | Click a cat, or press `6` again to give it to the unhappiest cat | The same as Feed's "press 1 twice". It's also the only way to reach a cat on the clock, since the tools work over the room, not the panel. |
| Adopting | Click the stray | Click the stray, or press `a` | Keyboard first. |
| Strays | After 4 completed focus sessions, then every 12 | The same, but a new stray turns up only when a focus completes | So a save with plenty of past focus sessions brings strays one at a time, not all at once. |

## 3. Treats

Treats 🐟 are earned as in main spec §4:
- A completed focus earns floor(minutes ÷ 5), using its length at completion (a standard 25 min earns 5).
- A clean set earns a +5 bonus.
- A break taken to the end earns +1.
- Idle has no timer, so it earns nothing.

The balance shows on the cat roster's header line, right-aligned: `cats              🐟 12`. The message line says what you earned, e.g. *"Focus complete (+5 🐟). Break time! Press space to start your break."*

A new save starts with 5 🐟. A version 1 save gets 5 🐟 plus 1 for every focus it has ever completed, as a little back pay.

## 4. The shop

`$` (or the toolbar's `$ Shop` button) opens the shop as a modal, at any time. Each line shows the item, what it does and its price. A number key or a click buys it on the spot. The shop is the confirmation, so there's no second dialog. A line you can't afford is dimmed. Buying it anyway says how many more treats you need. Furniture and toys you own say `owned`.

| # | Item | Price | Kind | Effect |
|---|---|---|---|---|
| 1 | Tuna can 🥫 | 5 | Consumable | +20 mood and hunger to 0 for one cat. Works on any cat, including an angry one or one on the clock. Works during focus. |
| 2 | Catnip mouse 🐭 | 25 | Toy | Drop it like the ball. Cats that want to play roll around on it: play −100, +8 mood. |
| 3 | Laser pointer 🔴 | 40 | Toy | A red dot on whatever surface is under the pointer. Cats chase it at full zoomies: play −50 per chase. |
| 4 | Cardboard box 📦 | 15 | Furniture | A floor nap spot that cats love. A cat napping in it peeks out over the edge. |
| 5 | Window perch 🪟 | 30 | Furniture | A high surface under the window, level with the tree top. |
| 6 | Hammock 🧺 | 35 | Furniture | A nap spot slung under the wall shelf. |

## 5. Consequences

### 5.1 Poop

- When the litter box is due, a pissy or furious cat goes down to the floor and poops where it stands, instead of using the door.
- Every poop on the floor costs every cat 2 mood per 10 minutes, but never takes a cat below 15 on its own (§2).
- The scoop works in every phase, as now.

### 5.2 The knocked bowl

- Every 10–20 minutes (5–10 for a gremlin), an angry cat walks to the bowl and knocks it over, if it's standing.
- A knocked bowl is empty and on its side. Hungry cats beg at it.
- Feed (`1` twice, or a click on the bowl) stands it up and fills it.

### 5.3 Furious cats

- Furious cats get the zoomies instead of sulking. Pissy cats still sulk.
- **The clock.** A cat that has been furious for 60 seconds (15 for a gremlin) climbs to the top of the cat tree and leaps across the divider onto the clock.
  - Only one cat sits on the clock at a time.
  - It loafs there, glaring, over the digits and the progress bar. The phase label, the state line and the roster stay visible, and the state line carries the time (§2).
  - It leaves, back to the room, once its mood reaches 25.
  - It stays put through phase changes and Idle.
- Tuna is the quick way to get it off: each can is +20 mood.

## 6. Strays and adoption

- A stray shows up when a focus completes, the room has fewer than 5 cats and no stray is already waiting, and `focus_total` has reached 4 + 12 × (cats − 1). That's 4, 16, 28 and 40 for the four strays.
- It peers in through the window, with a `?` over it, until you adopt it. It is drawn as a head behind the glass. Strays are never charged or rewarded.
- Clicking it (with any tool or none) or pressing `a` asks *"Adopt Pebble for 10 🐟? A grey cat, and chill."* With too few treats it says how many you need instead.
- An adopted cat comes in through the litter door, starts at mood 80 with some hunger, and joins the roster.
- Each stray gets an unused name from a pool (Pebble, Miso, Tux, Noodle, Biscuit, Ziggy, Pickles, Olive, Mochi, Bean), a coat not yet in the room where possible, and a random trait.

## 7. Saving: version 2

Version 2 adds the following to `world`:
- `treats` (an integer) and `tuna` (how many cans you own).
- `owned` (the toys and furniture you own: `catnip`, `laser`, `box`, `perch`, `hammock`).
- `bowl_knocked` (a knocked bowl always loads empty).
- `stray` (`{name, coat, trait}` or `null`).

It also stores a cat that was on the clock as sitting at the top of the cat tree, so it leaps back on a minute after launch if it is still furious.

A version 1 save is migrated, not backed up: it gets the treats in §3, no items, an upright bowl and no stray. A save from a newer version still counts as unknown.

## 8. Polish

- **OSC 22 pointer shapes:**
  - While a tool is held over the room, pomo asks the terminal for `pointer` (`grab` while the hand is on a cat).
  - It asks for `default` otherwise.
  - Best effort: Ghostty honours it, and other terminals ignore it.
- The README, the help text, the gallery and the screenshots cover everything new.

## 9. Not in this round

- **Wall shelf #2,** for the reason in §2.
- **Snapshot tests** with `pytest-textual-snapshot`. The scene and app tests already read the canvas back, and `scripts/screenshots.py` renders the real app. A third way to check the same pixels isn't worth another dependency.
- **Balance tuning** beyond the numbers above. It needs a few weeks of real use first, and every number lives in `game/balance.py`.
