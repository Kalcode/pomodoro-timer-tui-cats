# pomo 🍅

**A pomodoro timer for your terminal, with a room full of pixel-art cats who notice when you skip your breaks.**

[![tests](https://github.com/Kalcode/pomodoro-timer-tui-cats/actions/workflows/tests.yml/badge.svg)](https://github.com/Kalcode/pomodoro-timer-tui-cats/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

<p align="center">
  <img src="docs/images/play.gif" alt="A break in pomo: Mango the tabby chases a yarn ball across the room, pounces on it and bats it into the corner, while the timer counts down" width="900">
</p>

pomo is a classic pomodoro timer: 25 minutes of focus, a 5 minute break, and a long break after every fourth round. When each one ends it pings your desktop, and your phone through [ntfy](https://ntfy.sh).

It also has Mango, who lives in the room next to the clock. Mango naps up on the cat tree while you focus, gets the zoomies on your breaks, eats, plays, pops out through the litter door, and keeps score. Stick to your pomodoros and Mango stays content. Skip a focus, skip a break or pause for too long, and Mango gets grumpy, then pissy, then furious.

<table>
  <tr>
    <td><img src="docs/images/focus.png" alt="Six minutes into a focus: a big red 18:42 clock on the left, and Mango asleep on top of the cat tree"></td>
    <td><img src="docs/images/clock.png" alt="A minute after a skipped focus: Mango is furious and loafing on the big clock, glaring with red eyes. The time still shows in small text under the phase name, and the message line says Mango is sitting on your clock."></td>
  </tr>
  <tr>
    <td align="center"><b>Focus is nap time.</b> The tools lock and Mango sleeps up high.</td>
    <td align="center"><b>Rules have teeth.</b> Skip enough of them and Mango sits on your clock.</td>
  </tr>
</table>

## What you get

- **A real pomodoro timer:** a big pixel clock, a progress bar, your place in the set, and `+`/`-` to add or take away 5 minutes. When a phase ends, the next one waits for you to press space, so a break never slips by while you're heads-down. It keeps exact time, keeps your Mac awake while a phase runs, and asks before you break a rule.
- **Pings when each phase ends,** on your desktop and on your phone through ntfy, with a line about how Mango is doing.
- **A cat with an inner life:** mood, hunger, playfulness and affection. Mango walks, climbs, jumps between the cat tree and the shelf, naps, eats from the bowl and begs when it's empty.
- **Ways to look after him:** fill the bowl, roll him a yarn ball, dangle a string, pet him with the mouse.
- **Treats for sticking to it:** every focus and break earns treats 🐟, and a clean set earns a bonus. Spend them in the shop on tuna, a catnip mouse, a laser pointer, and furniture for the room.
- **More cats over time:** strays turn up at the window as your focus sessions add up. Adopt them and they move in, up to five cats.
- **Consequences:** angry cats poop on the floor and knock the bowl over, and a furious one climbs onto your clock until it calms down.
- **Idle mode:** put the timer away and just hang out with the cats.
- **It remembers you:** quit and come back later, and the cats, your treats and your place in the set are still there.

<p align="center">
  <img src="docs/images/pet.png" alt="Idle mode: the hand strokes Mango, who shuts his eyes and purrs, with a heart floating up" width="640">
</p>

## Install

You need:
- **Python 3.12 or newer** and [uv](https://docs.astral.sh/uv/).
- **A terminal with 24-bit colour and room for 100×30 cells.** iTerm2 and Ghostty on macOS are what pomo is made for. Other modern terminals should work. Linux is best effort, and tmux isn't supported.

```bash
uv tool install git+https://github.com/Kalcode/pomodoro-timer-tui-cats
```

That puts `pomo` on your PATH, and `uv tool upgrade pomo` updates it later. `pipx install git+https://github.com/Kalcode/pomodoro-timer-tui-cats` works too.

## Use

```bash
pomo                               # 25 min focus, 5 min breaks, 15 min long break every 4
pomo --focus 50 --short-break 10   # your own lengths, in minutes
pomo --idle                        # no timer: just hang out with the cats
pomo --auto-continue               # go straight on into the next phase instead of waiting for space
pomo --init                        # write a starter config file, with a private ntfy topic
pomo --test-ping                   # check desktop and phone notifications right now
pomo --help                        # every flag, key and config option
```

| Key | What it does |
|---|---|
| `space` | Start or pause, or start the next phase when one ends |
| `s` | Skip to the next phase |
| `r` | Restart this phase |
| `+` / `-` | Add or take away 5 minutes |
| `i` | Switch between Pomodoro and Idle |
| `1`–`5` | Pick up a care tool (feed, ball, string, pet, scoop) |
| `6`–`8` | Once you've bought them: tuna, the catnip mouse, the laser pointer |
| `esc` | Put the tool down |
| `$` | Open the shop |
| `a` | Adopt the stray at the window |
| `q` | Quit |

## What Mango cares about

Mango starts at mood 80. The roster under the clock shows his hearts (one per 20 mood) and how he feels.

| You… | Mood |
|---|---|
| Finish a focus of 15 minutes or more | +10 |
| Take a break all the way to the end | +5 |
| Abandon a focus: skip it, restart it, quit, or switch to Idle partway through | −25 |
| Skip a break | −20 |
| Pause a focus for more than 3 minutes in total | −10 |

Anything that breaks a rule asks first and tells you what it'll cost. Closing the window mid-focus counts as abandoning it: Mango remembers you left.

Mood sets how he behaves:
- **Content** (70 and up): naps, wanders, plays.
- **Grumpy** (40–69): sulks and sometimes ignores his toys.
- **Pissy** (15–39): red eyes, and he won't play or be petted.
- **Furious** (below 15): the same, for now.

Anger cools slowly on its own, back up to content but no further.

His needs fill up as pomo runs: hunger in 3 hours, play in 2, and affection in under 2 (Mango is clingy, so he wants fuss sooner). A need over 70 shows a bubble and slowly sours his mood, though needs alone never take him below grumpy. Looking after him meets those needs and cheers him up, but only as much as he actually needed it, so you can't pet away a skipped break.

## Looking after Mango

Pick a tool with `1`–`5` or the toolbar under the message line:

- **1 Feed:** click the bowl, or press `1` again, to fill it. Hungry cats come to eat.
- **2 Ball:** click to drop a yarn ball. It bounces and rolls, and a cat who wants to play will chase it and bat it around.
- **3 String:** a string hangs from your mouse. Wiggle it and Mango pounces, even up on the cat tree.
- **4 Pet:** stroke him with the mouse. Content cats purr and float hearts, angry ones hiss, and too much petting earns a swat.
- **5 Scoop:** click a poop to clean it up.
- **6 Tuna** (from the shop): click a cat, or press `6` again for the unhappiest one. +20 mood and a full belly, and it works on any cat, even a furious one, even mid-focus.
- **7 Catnip** (from the shop): click to drop the mouse. Cats who want to play roll around on it.
- **8 Laser** (from the shop): a red dot lands on whatever is under your mouse, and the cats chase it flat out.

A focus is nap time, so only the scoop and tuna work until your break. Idle mode (`i`) puts the timer away and unlocks everything.

## When the rules get broken

Mood isn't just a number. An angry cat makes a mess you have to deal with:
- **Pissy and furious cats poop on the floor** instead of going out through the litter door. Every poop left lying there sours every cat's mood a little, and stops an angry cat calming down, until you scoop it.
- **Angry cats knock the bowl over.** Feed (`1` twice, or click the bowl) stands it back up.
- **Furious cats get the zoomies,** and after a minute of fury one of them climbs the cat tree and leaps onto your clock. It sits on the big digits, glaring, until its mood is back up to 25. The time stays readable: the line under the phase shows it while the cat is there. Tuna gets it down fastest.

Only breaking the rules makes a cat furious. Poop and unmet needs can keep a cat cross, but they can't push it all the way to furious.

## Treats, the shop and new cats

You earn treats 🐟 by sticking to the timer:

| You… | Treats |
|---|---|
| Finish a focus | 1 per 5 minutes (5 for a standard 25) |
| Finish a set of 4 without breaking a rule | +5 bonus |
| Take a break all the way to the end | +1 |

Your treats show next to the cat roster. Press `$` to spend them:

| Item | 🐟 | What it does |
|---|---|---|
| 🥫 Tuna can | 5 | +20 mood and a full belly for one cat. Buy as many as you like. |
| 🐭 Catnip mouse | 25 | A new toy. Cats roll around on it, silly. |
| 🔴 Laser pointer | 40 | A new toy. A red dot to chase at full zoomies. |
| 📦 Cardboard box | 15 | The best nap spot in the house. A cat in it peeks out over the edge. |
| 🪟 Window perch | 30 | A high seat under the window. |
| 🧺 Hammock | 35 | A sling under the wall shelf, for long naps. |

<p align="center">
  <img src="docs/images/home.png" alt="A few weeks in: Mango naps in a cardboard box, a grey cat sleeps in the hammock under the wall shelf, a calico sits on the shelf and a tuxedo naps on top of the cat tree. The window perch is empty, and a siamese stray peers in through the window with a question mark over it. The panel shows 23 treats and says Biscuit is at the window." width="900">
</p>

**New cats.** After your 4th completed focus, a stray turns up at the window, peering in with a `?` over its head. Click it or press `a` to adopt it for 10 🐟. It comes in through the litter door with its own name, coat and personality: chill, a bit of a diva, clingy, or a little gremlin. The next stray comes after 12 more focus sessions, and so on, up to five cats.

## Phone pings in 3 steps

1. `pomo --init` writes `~/.config/pomo/config.toml`, readable only by you, with a random private ntfy topic in it.
2. Install the [ntfy](https://ntfy.sh) app on your phone, tap +, and subscribe to the topic from that file.
3. `pomo --test-ping` sends a test notification to your desktop and your phone right now, and says how each went.

Anyone who knows the topic can read your pings, so keep it to yourself. pomo never prints or logs it, and it's deliberately not a command-line flag, so it stays out of your shell history. On macOS, if no desktop banner shows up, allow notifications for Script Editor in System Settings → Notifications.

The config file holds the rest of the settings. Every key is optional:

```toml
ntfy_server = "https://ntfy.sh"   # or your own ntfy server
topic = "pomo-…"                  # empty means no phone pings
focus = 25                        # minutes
short_break = 5
long_break = 15
long_every = 4                    # a long break after this many focus sessions
auto_continue = false             # true: go straight on into the next phase
```

## Good to know

- **pomo remembers where you were.** It saves to `~/.local/state/pomo/save.json` on every phase change, every 30 seconds and when you quit. Nothing happens while it's closed: Mango doesn't get hungry while you're away.
- **Only one pomo runs at a time.** A second one tells you and exits.
- **It keeps your Mac awake, but only while a phase is running.** It does this with `caffeinate`. The screen can still sleep, and closing the lid still sleeps the Mac.
- **In a window smaller than 100×30**, a sad Mango asks for more room and the timer carries on as text.

## The cast

<p align="center">
  <img src="docs/images/cast.png" alt="Six pixel-art cats in a row: a tabby, a sleeping grey, a grumpy tuxedo, a siamese, a furious black cat with red eyes, and a loafing calico" width="900">
</p>

Every cat is drawn in half-block pixels from text grids, with six coats and five moods. Mango starts out alone, and the rest arrive as strays.

`pomo --gallery` shows every pose, face and prop.

## Develop

```bash
git clone https://github.com/Kalcode/pomodoro-timer-tui-cats
cd pomodoro-timer-tui-cats
uv sync
uv run pytest                          # the whole suite, in about 15 seconds
uv run pomo --gallery                  # every sprite, for tuning the art
uv run --with pillow python scripts/screenshots.py   # redraw the pictures in this README
```

`uv tool install --editable .` puts a `pomo` on your PATH that always runs your working copy.

How it's put together:

| Path | What's there |
|---|---|
| `src/pomo/timer.py`, `session.py` | The timer and its rules, which send events to the rest of the game |
| `src/pomo/game/` | The cats, their moods and needs, how they move, the toys, and the world they live in. Plain Python, no UI. |
| `src/pomo/render/` | The pixel canvas, the sprites, the font and the theme. A pure function draws each frame. |
| `src/pomo/ui/` | The [Textual](https://textual.textualize.io) app: the screen, the toolbar and the dialogs |
| `src/pomo/persist.py`, `notify.py`, `config.py` | Saving, notifications and settings |

The game core never reads the clock or the dice directly: both are passed in. So a test can fast-forward hours of cat life in a fraction of a second.

pomo was designed and built with [Claude Code](https://claude.com/claude-code), one milestone at a time. The specs and plans it was built from are in [docs/design/](docs/design/).

## License

[MIT](LICENSE) © David Clausen
