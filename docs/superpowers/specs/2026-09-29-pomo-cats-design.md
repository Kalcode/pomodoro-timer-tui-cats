# `pomo`: Pomodoro TUI with a cat idle game

**Date:** 2026-09-29
**Status:** Draft for review
**Builds on:** [IDEA.md](../../../IDEA.md). Everything there still applies unless this spec overrides it.

## 1. Summary

`pomo` is a terminal pomodoro timer with desktop and ntfy phone pings, as described in IDEA.md. It adds a room of pixel-art cats that live next to the timer. Following your pomodoros earns treats and keeps the cats happy. Breaking the rules makes them grumpy, then pissy (they poop on the floor), then furious (one of them sits on your clock). You care for them with a mouse-driven toolbar: feed, ball, string, pet (a hand that follows the mouse) and scoop.

**Who it's for:** one person who keeps it open all day in iTerm2 or Ghostty on macOS.
**Success:** the cats feel alive, and keeping them happy nudges you to stick to your pomodoros.

## 2. Decisions made during brainstorming

| Topic | Decision |
|---|---|
| Game style | Light progression: focus earns treats, treats buy food extras, toys and furniture, and new cats arrive over time |
| Consequences | Escalating mess: grumpy, then pissy (poop), then furious (sits on the clock). Cats never leave. |
| Focus behavior | Focus is nap time: care tools are locked during focus and breaks are play time |
| Idle mode | A timer-free sandbox. All tools work and no treats are earned. |
| App closed | The world is frozen. Nothing happens while `pomo` isn't running. |
| Art | Half-block (`▀`) truecolor pixel sprites, coats done as palette swaps |
| Layout | Split panels: timer on the left, a multi-level playscape room on the right |
| Cats in the timer panel | Only when furious. Getting in the way is the punishment. |
| Terminals | iTerm2 and Ghostty on macOS. tmux is **not** a target (this replaces IDEA.md's tmux criterion). |
| Stack | Python 3.12+ and Textual. The only third-party runtime dependency is Textual. |

## 3. Game rules

### 3.1 Phases and the cycle

The pomodoro cycle is as in IDEA.md: focus (25) → short break (5) → … → long break (15) after every `long_every` (4) focus sessions. The cycle advances on its own through focus and break transitions. At launch the timer is **ready but not running**. `space` starts it, and not starting it is never a rule break.

| Phase | Cat behavior | Tools |
|---|---|---|
| Focus | Nap time: mostly loaf and sleep, low activity | Only Scoop and Tuna. Everything else shows 🔒 |
| Break | Play time: wake up, zoomies, beg at the bowl | All |
| Idle mode | Mixed, relaxed activity | All. No timer, no treats. |

### 3.2 Rule breaks

These apply to **every** cat, scaled by trait (§3.5). Every rule-breaking action asks for confirmation first and shows its cost, for example *"Skip your break? The cats will be upset (−20)"*.

| Action | Mood |
|---|---|
| Abandon focus: skip, reset, quit, or switch to Idle mid-focus | −25 |
| Skip a break | −20 |
| Pause focus for more than 3 min total in one session (charged once per session) | −10 |

A quit you confirm in the dialog applies the penalty immediately and saves. If the app exits during focus without going through the quit dialog (Ctrl+C, closing the window, a crash), the abandon penalty is applied on the next launch. A message line says so: *"Mango remembers you left."*

Quitting, resetting or switching to Idle during a break is free, but that break earns no reward. Skipping a break is still a rule break.

### 3.3 Mood

Each cat has a mood from 0 to 100. A new cat starts at 80.

| Stage | Range | Behavior |
|---|---|---|
| Content | 70–100 | Naps, wanders, plays, walks off-screen through the litter door |
| Grumpy | 40–69 | Sulks (loafs with a flat face), sometimes ignores toys |
| Pissy | 15–39 | Poops on the floor instead of using the door, knocks the bowl over, refuses toys and petting |
| Furious | 0–14 | Everything pissy does, plus: hisses at the hand, gets the zoomies, and **moves onto the clock** (§3.6) |

**What raises mood:**
- Each completed focus of at least 15 min: +10 to all cats.
- Each break taken to the end: +5 to all cats.
- Care actions (§3.4).
- Natural cooling: below 70, mood drifts up by +1 per 10 min of runtime. Drift never goes above 70.

**What lowers mood:**
- Rule breaks (§3.2).
- Unmet needs (§3.4).
- Poop on the floor: −2 to all cats every 10 min per uncleaned poop.

### 3.4 Needs and care

Each cat has three needs from 0 (satisfied) to 100 (desperate). Needs only rise while the app is running.

| Need | Time from 0 to 100 | Satisfied by |
|---|---|---|
| Hunger | 3 h | Eating kibble (hunger → 0, +3 mood) or tuna (§4) |
| Play | 2 h | Chasing the ball or batting the string for about 10 s (play −50, +5 mood) |
| Affection | 2.5 h | Petting strokes (affection −25 and +2 mood per stroke, at most +8 per petting session) |

- When a need is above 70, a small bubble floats over the cat (🍗 / 🧶 / ♥) and its mood drops by −1 per minute. **Needs alone can never take mood below 40.** Anger only comes from breaking rules.
- **Over-petting:** petting a cat whose affection is already under 10 has a 30% chance per stroke of a swat, which costs −2 mood.
- **Pissy and furious cats refuse** toys and petting, and hiss. They still eat kibble, which fixes hunger but gives no mood. Tuna still works on them.

### 3.5 Traits

Each cat gets one trait at adoption:

| Trait | Effect |
|---|---|
| Chill | Rule-break penalties ×0.5 |
| Diva | Rule-break penalties ×1.5 |
| Clingy | Affection rises ×1.5 as fast |
| Gremlin | Moves onto the clock after 15 s of being furious instead of 60 s, and knocks things over twice as often |

### 3.6 Taking over the clock

- A furious cat waits (60 s, or 15 s for a gremlin), walks to the room's left edge, hops across the divider, and sits on the clock digits in the timer panel.
- Only one cat sits on the clock at a time. Other furious cats get the zoomies and knock things over.
- The cat leaves once its mood reaches 25. This gap above 15 keeps it from hopping on and off.
- Petting it gets a hiss. Tuna works.
- The phase label and the cat roster stay visible. The digits and the progress bar are covered.

### 3.7 Litter and poop

- Every 20–40 min of runtime a cat needs the litter box.
- Content and grumpy cats walk to the door at the right edge, leave the screen, and come back 20–40 s later.
- Pissy and furious cats poop on the floor wherever they are standing instead.
- A poop stays until you scoop it.

## 4. Economy and progression

**Treats 🐟** are the currency, shown in the timer panel.

| Earned by | Amount |
|---|---|
| Focus completed | floor(focus length in minutes ÷ 5), using the length at completion after any `+`/`-` (so a standard 25 min earns 5). Shortening focus shortens the reward instead of being penalized. |
| Set completed (`long_every` focus sessions with no rule breaks during the set) | +5 bonus |
| Break taken to the end | +1 |
| Idle mode | 0 |

**Free, always:** kibble, scooping, petting, the yarn ball and the string. New save: 1 cat (Mango, tabby, clingy) and 5 🐟.

**Shop** (the `$` key or the toolbar button, as a modal):

| Item | Price | Kind | Effect |
|---|---|---|---|
| Tuna can | 5 | Consumable | +20 mood and hunger → 0 for the cat you click. A furious cat accepts nothing else. |
| Catnip mouse | 25 | Toy unlock | Cats roll around and act silly. Play −100, +8 mood. |
| Laser pointer | 40 | Toy unlock | A red dot follows the mouse and cats chase it at full zoomies. Play −50 per chase. |
| Cardboard box | 15 | Furniture | A floor nap spot. Cats peek out of it. |
| Wall shelf #2 | 20 | Furniture | A new mid-level surface |
| Window perch | 30 | Furniture | A high surface by the window |
| Hammock | 35 | Furniture | A high nap spot hung under the top of the cat tree |

Unlocked toys and consumables you own get their own toolbar buttons.

**New cats:**
- The first stray appears in the window after 4 completed focus sessions in total, then another every 12, up to 5 cats.
- The stray sits outside with a `?` bubble until you click it: *"Adopt Pebble for 10 🐟?"*. If you say yes, it comes in through the door.
- Each new cat gets a name from a pool (Pebble, Miso, Tux, Noodle, Biscuit, Ziggy, Pickles, …), a random coat and a random trait.

## 5. Interaction

### 5.1 Keys

These are IDEA.md's keys plus the new ones:

| Key | Action |
|---|---|
| `space` | Start / pause |
| `s` | Skip the phase (confirms if it breaks a rule) |
| `r` | Reset the phase (confirms during focus) |
| `+` / `-` | Add or remove 5 min from the current phase (never below 5 min) |
| `i` | Toggle Pomodoro ↔ Idle (confirms mid-focus) |
| `1`–`5` | Pick a tool: Feed, Ball, String, Pet, Scoop |
| `6`, `7`, … | Pick an unlocked toy or consumable |
| `$` | Open the shop |
| `esc` | Put the tool down, or close a dialog |
| `q` | Quit (confirms mid-focus) |

### 5.2 Mouse tools

Clicking a toolbar button, or pressing its key, picks a tool. Over the room the tool is drawn as a sprite that follows the mouse.

| Tool | Use |
|---|---|
| Feed | Click the bowl, or press `1` twice, to fill it with kibble. Hungry cats come to eat. Also stands a knocked-over bowl back up. |
| Ball | Click to drop the yarn ball. It rolls with simple physics (velocity, friction, bounces off walls). Cats that want to play chase it. Only one ball is out at a time. |
| String | A string hangs from the ceiling at the mouse's x position and follows the mouse, so moving the mouse dangles it. Cats nearby bat and jump at it. |
| Pet | A hand sprite follows the mouse. Moving the hand across a cat's body counts as a stroke: about 6 cells of movement inside the cat's box. Content cats purr and float hearts. |
| Scoop | Click a poop to scoop it. Allowed in every phase. |
| Tuna / toys | Tuna: click a cat. Catnip: click to drop. Laser: the dot follows the mouse. |

The terminal's own mouse pointer can't be hidden, so the tool sprite is drawn with its hotspot at the pointer. As a best effort, the app also sends OSC 22 (a request to change the pointer shape to `pointer` or `grab`), which Ghostty supports. Terminals that don't support it ignore it.

## 6. Screen layout

The minimum terminal size is **100×30**. Anything smaller shows a *"the cats need more room"* screen with a small sad cat. The timer keeps running behind it.

```
┌─ timer panel (30 cols) ─┬─ room (rest of the width) ─────────────────────┐
│ ● FOCUS                 │  cat tree top   window        wall shelf       │
│ 18:42  (5×7 pixel font) │  cat tree mid                                  │
│ ███████░░░░░ progress   │  floor: bowl, ball, poop, box …   litter door →│
│ pomodoro 2 of 4 ●●○○    │                                                │
│ next: 5 min break       │                                                │
│ 🐟 42 treats            │                                                │
│ cats: name ♥♥♥♥ mood    │                                                │
│ key hints               │                                                │
├─────────────────────────┴────────────────────────────────────────────────┤
│ message line: "You skipped a break. Tux is FURIOUS."                      │
│ [1 🍗 Feed][2 🧶 Ball][3 🧵 String][4 ✋ Pet][5 🧹 Scoop] … [$] [⏱ Pomodoro|💤 Idle]│
└───────────────────────────────────────────────────────────────────────────┘
```

- **Timer panel:** a fixed 30 columns. In Idle mode it shows `IDLE · just hanging out` in place of the clock.
- **Cat roster:** each cat's name, 0–5 hearts (one per 20 mood) and its stage word, colored by stage.
- **Room:** fills the rest of the screen.
  - The floor is anchored to the bottom.
  - The cat tree, the window and the wall shelf stay together at the left of the room. The window sits between the tree and the shelf, where no perched cat can cover it. The bowl and the litter door follow the right edge.
  - Extra width adds floor space. Extra height adds wall above.
  - Purchased furniture goes in predefined slots.
- **Surfaces** are the places cats can stand: the floor, tree top, tree middle, wall shelf and any furniture bought. Cats walk along a surface and jump between surfaces that are within reach: at most 20 pixel rows apart vertically and at most 24 columns apart horizontally. Every surface is reachable from the floor.
- **Message line:** shows the most recent event and fades after 10 s.
- **Toolbar:** a row of Textual buttons. Locked tools are dimmed with 🔒.

The approved mockups are in `.superpowers/brainstorm/*/content/layout-v2.html`.

## 7. Rendering

**Canvas:**
- The canvas is a cell buffer. Each cell is either a *pixel pair* (top and bottom 24-bit color, drawn as `▀` with fg = top and bg = bottom) or a *text cell* (a glyph, fg and bg).
- Text is aware of double-width glyphs: emoji take 2 cells.
- Drawing a pixel over a text cell turns it back into a pixel cell. This is how a cat covers the clock digits.

**Draw order**, back to front:
- Room: background, wall and window, furniture, floor props (bowl, ball, poop), cats sorted by surface y then x, string, the tool sprite, effects (hearts, `z`, `#@!`, need bubbles).
- Timer panel: background, text and clock, a cat sitting on the clock, effects.

**Frame loop:**
- 8 fps, driven by Textual's `set_interval`.
- Each frame, `world.tick(dt)` runs and the scene is redrawn onto the canvas.
- The Stage widget compares canvas rows with the previous frame and refreshes only the lines that changed.
- Rich `Style` objects are cached by (fg, bg).
- Textual's synchronized output, which both iTerm2 and Ghostty support, prevents tearing.

**Sprites:**
- Sprites are text grids in Python modules, one character per pixel.
- Palette slots:

  | Slot | Meaning |
  |---|---|
  | `.` | transparent |
  | `o` | outline |
  | `f` | fur |
  | `d` | stripe |
  | `c` | patch (equals `f` except on calico) |
  | `w` | white |
  | `p` | pink |
  | `e` | eye |
  | `k` | pupil |
  | `r` | angry eye |

- Helpers:
  - `mirror` builds a symmetric head from its left half.
  - `flip` makes a left-facing version.
  - `compose` stacks a head and a body.
  - Face variants (`ok`, `blink`, `sleep`, `meh`, `mad`) swap only the ear, brow and eye rows.
- First-version poses:
  - Front-facing: sit and loaf, each with every face variant.
  - Side view: 2-frame walk and a jump/pounce, both flipped for direction.
- Coats: tabby, grey, tuxedo, siamese, black, calico. A coat is a palette.
- Props: poop, yarn (2 rolling frames), bowl (empty, full, knocked over), hand (2 frames), door, tuna, catnip mouse, laser dot, box, and the furniture.
- The string is drawn by code, not as a sprite.
- Clock digits use a 5×7 pixel font at 1× (`18:42` is 25 columns).
- Colors are a Tokyo Night-style palette defined in one theme module.

**`pomo --gallery`** is a developer view that renders every sprite × coat × face on one screen for tuning the art.

## 8. Architecture

```
pomo/
  cli.py            argparse → Config → launches app (or gallery)
  config.py         Config dataclass; TOML load; CLI overrides; permission check
  clock.py          Clock protocol (monotonic now()); RealClock, FakeClock
  timer.py          PomodoroTimer state machine; stores the phase end time, not a countdown
  session.py        Session: wraps the timer, applies the rules (pause allowance, abandon), emits events
  notify.py         desktop + ntfy; runs in a worker thread; retries once; never raises
  persist.py        versioned JSON save/load, atomic write
  game/
    balance.py      every tunable number in this spec
    events.py       event dataclasses (RuleBreak, Reward, CareAction, …)
    cat.py          Cat: mood, needs, trait, stage(), apply(event)
    economy.py      wallet, shop catalog, purchase()
    playscape.py    surfaces and furniture slots for a given room size
    behavior.py     per-cat activity state machine; paths over the surface graph
    world.py        World: cats, props, poops, strays; tick(dt); tool commands
  render/
    canvas.py       cell/pixel buffer → Rich Strips, style cache, dirty rows
    sprites.py      sprite grids, coats, helpers, validation
    font.py         5×7 digits
    theme.py        colors
    scene.py        pure: (World, TimerView, UIState) → Canvas
  ui/
    app.py          Textual App: wires timer, rules, world, notify and persist; 8 fps interval
    stage.py        Stage widget: draws the scene; mouse → tool commands
    toolbar.py      tool buttons, lock states
    dialogs.py      confirm dialogs
    shop.py         shop modal
  gallery.py
```

**Data flow:**
1. Key or mouse input goes to `app`, which calls the timer (start, pause, skip) or `world` (tool commands).
2. Timer transitions and actions go through `session`, which applies the rules and emits events.
3. `world.apply(events)` updates mood and treats. `notify` sends pings on phase transitions. `persist` saves.
4. Each frame, `world.tick(dt)` runs and `scene.draw(...)` renders onto the Stage.

**Rules for the core:**
- Everything under `game/`, plus `timer.py` and `session.py`, is pure Python with no Textual imports.
- Time comes from an injected `Clock`, and randomness from an injected `random.Random(seed)`.
- This keeps scenarios such as *"skip a break → Tux furious → Tux sits on the clock"* deterministic and fast to test.

## 9. Persistence, config and notifications

**Save file:** `$XDG_STATE_HOME/pomo/save.json`, defaulting to `~/.local/state/pomo/`.
- **Contents:** schema version, cats (name, coat, trait, mood, needs, surface and position), treats, owned items, placed furniture, poops, strays, progression counters (completed focus total, set progress), and the timer session (phase, remaining time, whether a focus is in progress).
- **Counters only:** there is no history or stats view, which is a non-goal in IDEA.md.
- **When it saves:** on every phase transition, every 30 s, and on quit. Writes go to a temporary file first, which is then renamed over the old one, so a crash can't leave a half-written save.
- **Frozen world:** loading a save does not simulate the time that passed.
- **Corrupt or unknown save:** rename it to `save.json.bak-<timestamp>`, start fresh, and show a message.

**Config:** `~/.config/pomo/config.toml`, the keys from IDEA.md, all optional:

```toml
ntfy_server = "https://ntfy.sh"
topic = ""            # empty disables phone pings
focus = 25
short_break = 5
long_break = 15
long_every = 4
```

- CLI flags: `--focus`, `--short-break`, `--long-break`, `--long-every`, `--idle` (start in Idle mode), `--no-notify`, `--config PATH`, `--gallery` and `--help`. `pomo --help` documents all of them.
- The topic is deliberately **not** a flag, so it stays out of shell history.
- If `topic` is set and the config file is readable by anyone other than you, `pomo` shows a warning (it doesn't chmod the file).
- The topic is never logged, and it's kept out of `repr(Config)` because Textual's crash tracebacks print local variables.

**Notifications** go out when a focus or a break runs to its end in Pomodoro mode. They are not sent for phases you skip (you already know), and never in Idle mode. If one tick finishes several phases (for example after pomo was suspended and resumed), only one ping goes out, for the latest.
- **Desktop:** `osascript` on macOS, `notify-send` on Linux, otherwise the terminal bell.
- **ntfy:** as in IDEA.md. POST to `{ntfy_server}/{topic}` with `Title`, `Priority: default` and `Tags: tomato,clock`.
  - Both transitions use `default` priority. IDEA.md's "min for break-start" contradicts its own example for the focus→break ping, and the example wins.
  - The message body adds one cat line, for example *"25 minutes of focus complete. Time for a 5 min break. Mango is waiting by the bowl."*
- **Failures:** log a warning, retry once after 2 s, then give up silently. Pings go through `urllib` in a worker thread and never block or crash the timer.
- **Log file:** `~/.local/state/pomo/pomo.log`.

## 10. Error handling

| Situation | Behavior |
|---|---|
| ntfy or desktop notification fails | Log, retry once (ntfy), carry on |
| Offline | Everything except phone pings works as normal |
| The Mac would idle-sleep mid-phase | While a phase runs, `caffeinate -i -w <pid>` blocks idle system sleep (the display can still sleep). The monotonic clock stops while the Mac sleeps, so without this an unattended break would stall and never ping. Closing the lid still sleeps the Mac, and the timer pauses and resumes rather than catching up. |
| Save file corrupt or from an unknown version | Back it up, start fresh, show a message |
| Terminal smaller than 100×30 | "Need more room" screen. The timer and the simulation keep running. |
| Resize | Recompute the playscape. Cats on surfaces that moved snap to the nearest valid spot. |
| No truecolor (`COLORTERM` isn't `truecolor`/`24bit`) | Run anyway, since Textual downsamples colors, and show a one-time warning |
| Exit during focus without going through the quit dialog | Abandon penalty on the next launch (§3.2) |

Bugs in game logic are not swallowed. Tests are what guard against them.

## 11. Testing

- **Unit tests (pytest), with FakeClock and a seeded RNG:**
  - Timer: full unattended cycle, pause and resume, skip, reset, `+`/`-`, the long break every 4th.
  - Rules: pause allowance, each abandon path, the penalty for an exit during focus on the next launch.
  - Cat: stage thresholds, needs capped at grumpy, trait multipliers, refusals, over-petting.
  - Economy: treats scaling with minutes, the set bonus, purchases.
  - World: poop only when pissy or worse, clock takeover timing and the leave-at-25 threshold, litter trips, stray milestones.
  - Persist: save/load round trip, the corrupt-file backup, the atomic write.
  - Notify: ntfy request built through a fake transport, the single retry, failures swallowed, the topic never logged.
  - Config: defaults, TOML, CLI overrides, the permission warning.
- **Sprite validation:** every grid is rectangular and uses only known slots, and every coat defines every slot.
- **Render tests:** golden text dumps of small canvases, and z-order checks (a cat pixel over a clock digit).
- **App tests:** the Textual Pilot (headless) presses keys, clicks toolbar buttons and answers confirm dialogs.
- **Snapshot tests:** `pytest-textual-snapshot` for the calm and angry screens and for the too-small screen.
- **Scenario test:** skip a break with Tux at mood 30, fast-forward the clock, and assert that Tux sits on the clock and leaves once his mood reaches 25.
- **Manual smoke test:** a full cycle in iTerm2 and in Ghostty.

## 12. Acceptance criteria

- Runs in iTerm2 and Ghostty at 100×30 or larger. Redraws cleanly on resize. Animates at 8 fps without flicker.
- A full cycle completes unattended, with the correct desktop and ntfy notifications at each transition. Works offline.
- `pomo --help` documents every flag.
- Every tool works with the mouse, and tools can be picked with `1`–`5`. Tools are locked during focus except Scoop and Tuna.
- Each rule break changes mood as in §3.2. Pissy cats poop on the floor. A furious cat sits on the clock and leaves once its mood reaches 25.
- Idle mode has no timer, earns no treats and allows every tool.
- Treats, the shop, strays and adoption work as in §4.
- State persists across restarts, and nothing changes while the app is closed.
- `pomo --gallery` shows every sprite.

## 13. Build order

Each milestone ends with something that runs.

1. **Timer parity with IDEA.md:** timer, session rules, notifications, config and CLI, confirm dialogs, plus a plain Textual screen. This alone is a usable pomodoro.
2. **Canvas and art:** the canvas, sprites, font and theme, the split layout, the static playscape, one cat sitting there, and `--gallery`.
3. **Living cats:** cat model, needs and moods, behavior and movement across surfaces, the effects of each phase.
4. **Care:** toolbar and tools (feed, ball, string, pet, scoop), Idle mode, confirm dialogs.
5. **Consequences and progression:** poop, knocked bowl, clock takeover, treats, shop, tuna, strays and adoption, furniture.
6. **Persistence and polish:** save/load, the too-small screen, OSC 22, snapshot tests, tuning the balance numbers.

## 14. Non-goals

- From IDEA.md: no task tracking, no stats or history (beyond the progression counters), no sound playback, no daemon mode.
- Nothing happens while the app is closed. There is no offline progression.
- No tmux support and no Windows support. Linux is best effort.
- No petting from the keyboard. Care tools need a mouse, though keys pick them.
- No user-editable balance file. The numbers live in `balance.py` and get tuned in code.
