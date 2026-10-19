# How pomo was designed

pomo was built in rounds with [Claude Code](https://claude.com/claude-code). It started as a one-page idea. That became a design spec, and the spec was built one milestone at a time, each from a step-by-step implementation plan worked test-first and checked by a fresh reviewer at the end.

These are those documents, kept as they were written. Paths inside them point at their old home, `docs/superpowers/`.

## The idea and the specs

| Document | What it is |
|---|---|
| [IDEA.md](IDEA.md) | The original one-pager: a terminal pomodoro timer that pings your desktop and your phone. |
| [specs/2026-09-29-pomo-cats-design.md](specs/2026-09-29-pomo-cats-design.md) | The main design: the timer, the cat game and its rules, the art, the architecture. Some of it isn't built yet (see below). |
| [specs/2026-10-03-pomo-daily-driver-design.md](specs/2026-10-03-pomo-daily-driver-design.md) | An addendum: saving, setup helpers, the too-small screen, polish, and waiting for you between phases. Where the two differ, the addendum wins. |
| [specs/2026-10-19-pomo-home-stretch-design.md](specs/2026-10-19-pomo-home-stretch-design.md) | The last round: consequences, treats, the shop, strays and the save's version 2, with the calls made along the way. Where it differs from the others, it wins. |

## The plans, in the order they were built

| Plan | What it delivered |
|---|---|
| [1. Timer core](plans/2026-09-29-pomo-m1-timer-core.md) | The timer, the rules, desktop and ntfy pings, config, and the command line |
| [2. Canvas and art](plans/2026-09-29-pomo-m2-canvas-and-art.md) | Half-block pixel rendering, the sprites, the split layout, and `--gallery` |
| [3. Living cats](plans/2026-09-30-pomo-m3-living-cats.md) | Moods, needs, and cats that walk, climb, nap, eat and use the litter door |
| [4. Care and Idle](plans/2026-09-30-pomo-m4-care-and-idle.md) | The toolbar and its mouse tools, toys, petting, and Idle mode |
| [5. Daily driver](plans/2026-10-03-pomo-daily-driver.md) | Saving, `--init`, `--test-ping`, the too-small screen, and fixes |

## Built without a plan

The home stretch was handed over with "take the reins" and built in one sitting, so it has a spec of the calls made, not a step-by-step plan. Its spec lists what was cut (§9): a second wall shelf, snapshot tests, and balance tuning that has to wait for a few weeks of real use.
