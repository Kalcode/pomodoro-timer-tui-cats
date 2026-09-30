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
