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
