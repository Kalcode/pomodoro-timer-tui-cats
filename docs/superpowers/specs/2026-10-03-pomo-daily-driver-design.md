# `pomo` daily-driver round: saving, setup, and polish

**Date:** 2026-10-03
**Status:** Approved in conversation; written up for review
**Builds on:** [the main design](2026-09-29-pomo-cats-design.md). Everything there still applies unless this addendum says otherwise.

## 1. Purpose

After milestone 4, `pomo` has a full timer, Mango, the care tools and Idle mode. Before adding more cat features, this round makes it something you can run all day as your real pomodoro timer:
- It remembers where you were across quits and restarts.
- Phone pings are easy to set up and check.
- It degrades gracefully in a small window.
- The rough edges left over from milestone 4 are fixed.

**Success:**
- You can set up phone pings in a couple of minutes and confirm they work without waiting out a focus.
- Restarting `pomo`, or closing its window, never loses Mango or your place in the set.
- Nothing visibly misbehaves in a normal day of use.

**Not in this round:** every milestone 5 cat feature (poop, the knocked bowl, sitting on the clock, treats, the shop, tuna, strays, furniture), plus OSC 22 pointer shapes, snapshot tests and balance tuning. These now come after this round (§8).

## 2. Saving (main spec §9, brought forward)

### 2.1 The file

`$XDG_STATE_HOME/pomo/save.json`, defaulting to `~/.local/state/pomo/save.json`. It is versioned JSON, version 1:

```json
{
  "version": 1,
  "saved_at": 1759500000.0,
  "timer": {"phase": "short_break", "focus_in_set": 2, "set_clean": true,
            "focus_in_progress": false, "break_left": 212.0, "idle": false},
  "world": {"bowl_full": true, "focus_total": 17,
            "cats": [{"name": "Mango", "coat": "tabby", "trait": "clingy", "mood": 72.5,
                      "needs": {"hunger": 31.0, "play": 12.0, "affection": 40.0},
                      "surface": "shelf", "x": 55.0}],
            "poops": [{"x": 20.0}]}
}
```

**The fields:**
- `saved_at` is wall-clock time (seconds since the epoch). The timer's own clock is monotonic and means nothing across runs.
- `focus_in_progress` is true when a focus had started, running or paused, and hadn't been paid for.
- `break_left` is the number of seconds left on the break as of `saved_at`, or `null` when you're not on a break. While you're idle on a break, it's what is left of the break's clock (§2.3).
- `focus_total` is the number of focus sessions you have ever completed. Strays will need it in milestone 5.
- Poops are always on the floor, so only their column is saved.
- Cats' litter timers and the yarn ball are not saved. Litter timers are re-rolled, and the ball goes away.

### 2.2 When it saves

- **On every phase change.**
- **Every 30 s.**
- **On quit,** whichever way the app exits through Textual.

A save is written to a temporary file in the same directory, flushed to disk, then renamed over `save.json`. A crash can never leave half a save.

**If writing fails** (disk full, permissions):
- The app logs a warning and shows one message: *"Couldn't save your cats: <reason>."*
- It keeps running and tries again at the next save point.
- It doesn't repeat the message until a save succeeds and then fails again.

### 2.3 Coming back

Nothing happens while `pomo` is closed (main spec §2). The timer always comes back **ready**, never running. Phase lengths always come from the current config and flags, so changing `--focus` between runs just works.

| How the last run ended | What you come back to |
|---|---|
| A ready focus, or a focus you quit with `q` and confirmed. The dialog already charged −25, and a confirmed quit resets the focus before the final save, so it's never charged twice. | That focus, ready |
| Mid-focus, started or paused, any other way: closing the window, being killed, a crash | The abandon penalty to every cat now (−25, scaled by trait), *"Mango remembers you left."* (*"The cats remember you left."* with more than one cat), then a fresh focus, ready |
| On a break, and the time since `saved_at` is at least `break_left` | A ready focus. The break earned no reward, and there's no penalty. |
| On a break that still had time left | That break, ready to start |
| In Idle mode | Idle again, with the break rule above still running underneath. Coming out of Idle applies it, as it does now. |

**More restore rules:**
- `--idle` always starts in Idle, whatever the save says.
- `focus_in_set` is clamped to the current `long_every` minus one.
- Cats come back on their saved surface and column. They are snapped onto the surface if the room is a different size now, as on a resize.
- If there is no save, `pomo` starts a new save as now: Mango, tabby, clingy.

### 2.4 Bad saves

`pomo` treats a save as bad when any of these is true:
- It isn't valid JSON.
- Its version is unknown.
- A field is missing or has the wrong type.
- A coat, trait or surface is unknown.
- A number isn't finite.

A bad save is renamed to `save.json.bak-<YYYYmmdd-HHMMSS>`. `pomo` then starts fresh and shows *"Your save couldn't be read, so pomo started fresh. The old one is kept as <name>."*

Out-of-range numbers are clamped rather than rejected: mood and needs to 0–100, and a negative `break_left` to 0.

Later versions will migrate older saves forward instead of discarding them. A save from a newer `pomo` counts as unknown.

### 2.5 One `pomo` at a time

- The app holds an exclusive lock (`fcntl.flock`) on `$XDG_STATE_HOME/pomo/pomo.lock` for its whole run.
- A second `pomo` prints *"pomo is already running in another window."* to stderr and exits with code 1. Without the lock, two timers would ping twice and overwrite each other's save.
- The operating system releases the lock when the process ends, even after a crash, so a stale lock can't happen.
- `--help`, `--version`, `--gallery`, `--init` and `--test-ping` don't take the lock.

### 2.6 Architecture

- **`persist.py`:**
  - `snapshot(session, world, saved_at) -> dict`.
  - `load(path) -> dict | None`, which raises `BadSave` with a reason when the save is bad.
  - `write(path, data)`, which is atomic.
  - `back_up(path, now) -> Path`.
  - Validation lives here. It may import `render.sprites.COATS` to check coats.
- **`Session`** gains:
  - `state(now) -> SessionState`.
  - `restore(state, closed_for) -> list[Event]`. This returns the abandon `RuleBreak` and/or the break-over `Transition`. It stays pure and is tested with `FakeClock`.
- **`PomodoroTimer`** gains `restore(phase, focus_in_set)`, which leaves the timer ready.
- **`World`** gains:
  - `focus_total`, incremented on `FocusCompleted`.
  - `restore_cats(...)`, or a `World` built from saved cats, bodies, the bowl and poops.
- **`PomoApp`** takes:
  - An optional save store (a path), plus a wall clock to inject.
  - With no store, nothing is saved, which keeps every existing test as it is.
- **`cli.py`:**
  - Takes the lock.
  - Loads the save, backing up a bad one.
  - Hands both to the app.
- **`clock.py`** gains `WallClock` (`time.time()`).

## 3. Setup helpers

### 3.1 `pomo --init`

Creates the config file at `--config PATH` if given, otherwise at `~/.config/pomo/config.toml`:
- Parent directories are created as needed.
- The file is opened with `O_CREAT | O_EXCL` and mode 600, so it is private from the first byte and can never overwrite an existing file. If the file exists, `pomo --init` prints *"<path> already exists, so pomo left it alone."* and exits with code 0.

The file lists every key with its default and a comment:
- `topic` is set to a freshly generated topic, `pomo-` plus `secrets.token_urlsafe(16)`, which ntfy accepts.
- The comment explains that anyone who knows the topic can read the pings, and how to subscribe in the ntfy app.

It prints, **without the topic**:

```
Wrote ~/.config/pomo/config.toml (only you can read it).
It holds a private ntfy topic made just for you. For pings on your phone:
  1. Install the ntfy app and subscribe to the topic in that file.
  2. Run: pomo --test-ping
```

### 3.2 `pomo --test-ping`

Loads the config the usual way and sends one notification right away, synchronously, in this process, with no worker thread:
- **Title:** "🍅 pomo test".
- **Body:** "If you can read this, pings work. Mango says hi."

It reports each channel on its own line and never prints the topic or the URL:

```
desktop: sent. No banner? Allow notifications for Script Editor in System Settings → Notifications.
phone: sent to your ntfy topic.
```

**Other phone outcomes:**
- `phone: no topic set in ~/.config/pomo/config.toml (run pomo --init).`
- `phone: failed (HTTP 403).` The error is described by the existing `_describe` helper.

**Exit code:** 0 if every channel it tried succeeded, otherwise 1. `--test-ping` tests even when `--no-notify` is also given. The README gains a short "phone pings in 3 steps" section.

## 4. The too-small screen (main spec §6, brought forward)

When the terminal is narrower than 100 columns or shorter than 30 rows (a stage under 100×28), the stage shows a different screen:
- A small sad Mango: the loaf pose with the `meh` face, in Mango's coat. It's shown only if it fits.
- *"The cats need more room."*
- *"Make the window at least 100×30 (it's W×H now)."*
- The timer as text: `● FOCUS 18:42`, plus `paused` or `space to start` when relevant, or `● IDLE`.

**While the screen is too small:**
- Every key works as normal.
- The toolbar is hidden.
- The mouse tools are off: the hand is lifted and the pointer counts as outside the room.
- The world keeps its last room geometry.
- Growing the window back brings everything back as it was.

## 5. A cat line in pings (main spec §9)

Every ping's body gains one line about the unhappiest cat (the lowest mood; on a tie, the first). It uses the first of these that applies:

1. Pissy or furious: *"Mango is still sulking."*
2. Wants food: *"Mango is waiting by the bowl."*
3. Wants to play: *"Mango wants to play."*
4. Wants affection: *"Mango could use some fuss."*
5. A break is starting: *"Mango is stretching for playtime."*
6. A focus is starting: *"Mango is curling up for a nap."*

**Example:** *"25 minutes of focus complete. Time for a 5 min break. Mango is waiting by the bowl."* The line is built by a pure function from the cats and the phase that's starting, and `ping_for` takes it as an argument.

## 6. The six fixes deferred from milestone 4

1. **Mouse moves redraw only when something visible changes.**
   - A move that maps to the same room point as before does nothing.
   - With no tool held, the pointer is recorded but nothing is redrawn.
2. **Leaving the window puts the tool away.**
   - Textual never reports the mouse leaving the window, so the stage's top row and its last column count as outside the room. Sliding out across the top or right edge lifts the hand and takes the string down. (The bottom and left edges already border other widgets, which send `Leave`.)
   - Losing window focus (`AppBlur`) does the same.
3. **Idle key hints:** in Idle, the panel's hints become `i back to pomodoro`, `1-5 tools  esc drop` and `q quit`.
4. **The mode toggle:**
   - It's two buttons, `🍅 Pomodoro` and `💤 Idle`, with the current one highlighted.
   - Clicking the other one switches, asking first mid-focus as `i` does. Clicking the current one does nothing.
5. **The toolbar and message line background** becomes a theme colour, `theme.BAR_BG`, instead of a hex string in CSS.
6. **The hand stops patting** as soon as no cat is under it. The world re-checks the cat under a resting hand every tick, which also resets the stroke in progress.

## 7. Testing

- **persist:**
  - A round trip of every field.
  - The atomic write leaves no temporary file behind and never truncates the old save on failure.
  - Each bad-save case is backed up and the app starts fresh.
  - Out-of-range numbers are clamped.
  - An unknown version is backed up.
- **Session restore,** one test per row of §2.3, using `FakeClock` as both clocks.
- **The lock:** a second acquire fails while the first is held, and succeeds after it's released.
- **`--init`:**
  - Creates mode 600.
  - Contains a valid topic, and the config loads.
  - Never overwrites an existing file.
  - Never prints the topic.
- **`--test-ping`:**
  - Fake desktop and transport: each outcome is reported correctly.
  - The topic never appears in the output.
  - The exit codes are right.
- **The too-small screen:** the scene at 80×24 and the app at 80×24 show the message and the timer text, keys still work, and the toolbar is hidden.
- **The cat line:** one test per rule, and the ping body includes it.
- **The six fixes:** a test each.
- **The app:**
  - It saves on a phase change, every 30 s and on quit.
  - It loads at startup, including the penalty message.
  - `--idle` overrides the save.
- **A real-terminal check in a pseudo-terminal:**
  1. Quit and relaunch, and see the state come back.
  2. Kill mid-focus, and see the message and penalty on relaunch.
  3. A second instance is refused.

## 8. Changes to the main spec

- **§9:** the save holds what exists today. Treats, owned items, furniture and strays join it in milestone 5 as version 2, which migrates version 1 saves.
- **§13 build order** becomes:
  1. Timer parity.
  2. Canvas and art.
  3. Living cats.
  4. Care.
  5. **Daily driver (this round):** saving, setup helpers, the too-small screen, the cat line, and milestone 4's fixes.
  6. Consequences and progression (the old milestone 5).
  7. Polish: OSC 22, snapshot tests, balance tuning.
