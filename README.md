# pomo

A pomodoro timer for your terminal, with a room full of cats. (The cats move in with milestone 2.)

## Install

```bash
uv tool install .    # run from this directory; puts `pomo` on your PATH
```

## Use

```bash
pomo                               # 25 min focus, 5 min breaks, 15 min long break every 4
pomo --focus 50 --short-break 10
pomo --help                        # every flag, key and config option
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
