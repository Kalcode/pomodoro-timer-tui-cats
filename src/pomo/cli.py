"""`pomo` command line: flags → config → app."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path

from pomo import __version__
from pomo.awake import keep_awake
from pomo.clock import RealClock
from pomo.config import ConfigError, load_config, permission_warning, with_overrides
from pomo.gallery import GalleryApp
from pomo.notify import Notifier, NullNotifier
from pomo.paths import config_path, log_path
from pomo.ui.app import PomoApp

DESCRIPTION = (
    "A pomodoro timer for your terminal, with cats. "
    "Pings your desktop, and your phone via ntfy, when each phase ends."
)
EPILOG = """\
keys:
  space  start / pause        s  skip phase        r  reset phase
  + / -  add / remove 5 min   q  quit

config file (all keys optional), default ~/.config/pomo/config.toml:
  ntfy_server = "https://ntfy.sh"
  topic = ""          # your ntfy topic; empty disables phone pings
  focus = 25          # minutes
  short_break = 5
  long_break = 15
  long_every = 4      # a long break after this many focus sessions

The ntfy topic is a secret: it is read only from the config file (chmod 600 it),
never from a flag, and never logged.
"""


def positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, got {value}")
    return value


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pomo",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--focus", type=positive_int, metavar="MIN", help="focus length in minutes (default 25)")
    parser.add_argument("--short-break", type=positive_int, metavar="MIN", help="short break in minutes (default 5)")
    parser.add_argument("--long-break", type=positive_int, metavar="MIN", help="long break in minutes (default 15)")
    parser.add_argument(
        "--long-every", type=positive_int, metavar="N", help="long break after every N focus sessions (default 4)"
    )
    parser.add_argument("--no-notify", action="store_true", help="no desktop or phone notifications")
    parser.add_argument("--config", type=Path, metavar="PATH", help="config file to use instead of the default")
    parser.add_argument("--gallery", action="store_true", help="show every cat sprite and prop (for tuning the art)")
    parser.add_argument("--version", action="version", version=f"pomo {__version__}")
    return parser


def setup_logging(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=path,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def truecolor_warning(environ: Mapping[str, str]) -> str | None:
    """iTerm2 and Ghostty set COLORTERM=truecolor. Without it the pixel art gets approximated."""
    if environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return None
    return "This terminal doesn't report 24-bit colour (COLORTERM), so the cats may look a bit off."


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.gallery:
        GalleryApp().run()
        return 0
    if args.config is not None:
        path = args.config.expanduser()  # shells don't expand ~ in --config=~/...
        if not path.is_file():
            print(f"pomo: config file not found: {path}", file=sys.stderr)
            return 2
    else:
        path = config_path()  # the default may be missing: that just means defaults
    try:
        cfg = with_overrides(
            load_config(path),
            focus=args.focus,
            short_break=args.short_break,
            long_break=args.long_break,
            long_every=args.long_every,
        )
    except ConfigError as e:
        print(f"pomo: {e}", file=sys.stderr)
        return 2

    setup_logging(log_path())
    warnings = [w for w in [permission_warning(path, cfg), truecolor_warning(os.environ)] if w]
    app = PomoApp(cfg, RealClock(), NullNotifier(), warnings=warnings, keep_awake=keep_awake())
    if not args.no_notify:
        # The bell must ring on Textual's thread; notifications arrive from a worker thread.
        app.notifier = Notifier(cfg.ntfy_server, cfg.topic, bell=lambda: app.call_from_thread(app.bell))
    app.run()
    return 0
