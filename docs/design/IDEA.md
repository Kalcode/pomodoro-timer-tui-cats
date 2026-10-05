# Spec: `pomo` — TUI Pomodoro with ntfy pings

## Overview
A terminal pomodoro timer (TUI) that notifies both the desktop and the user's phone via ntfy when each session/break ends.

## Tech
- Python 3.11+ (or Go — implementer's choice)
- TUI: [Textual](https://github.com/Textualize/textual) (Python) or [Bubble Tea](https://github.com/charmbracelet/bubbletea) (Go)
- Notifications: ntfy HTTP API

## Core behavior
- Classic pomodoro cycle: 25 min focus → 5 min short break; every 4th break is 15 min long break. Durations configurable via CLI flags or config file (`~/.config/pomo/config.toml`).
- Key bindings: `space` start/pause, `r` reset, `s` skip, `q` quit, `+`/`-` add/remove 5 min.
- Display: large countdown, current phase (FOCUS/BREAK), completed pomodoro count, and next-up phase.

## Notification requirements
On each phase transition, send **both**:

1. **Desktop notification:** native OS notification (e.g. `notify-send` on Linux, `osascript` on macOS, `win10toast`/equivalent on Windows). Fall back to terminal bell if unavailable.
2. **Phone push** — HTTP POST to ntfy:

```
POST https://ntfy.sh/{topic}
Headers:
  Title: 🍅 Pomodoro done!
  Priority: default        (or "min" for break-start)
  Tags: tomato, clock
Body: 25 minutes of focus complete. Time for a 5 min break.
```

- `topic` set in config; treat it as a secret (file perms 600, don't log it).
- On POST failure: log a warning, keep the timer running, retry once after 2s, then give up silently (never crash the timer).

## Config (all optional, sane defaults)
```toml
ntfy_server = "https://ntfy.sh"   # override for self-hosted
topic = ""                        # required for phone pings; empty disables them
focus = 25
short_break = 5
long_break = 15
long_every = 4
```

## Non-goals
- No task tracking, no stats/history, no sound playback (desktop notification handles that), no daemon mode.

## Acceptance criteria
- Runs in tmux without issue; redraws cleanly on resize.
- Full cycle completes unattended with correct notifications at each transition.
- Works offline (ntfy errors are non-fatal).
- `pomo --help` documents all flags.