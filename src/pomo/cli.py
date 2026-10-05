"""`pomo` command line: flags → config → app."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path

from pomo import __version__, persist
from pomo.awake import keep_awake
from pomo.clock import RealClock
from pomo.config import (
    Config, ConfigError, display_path, load_config, new_topic, permission_warning, with_overrides, write_starter,
)
from pomo.gallery import GalleryApp
from pomo.lock import acquire
from pomo.notify import Notifier, NullNotifier, send_test_ping
from pomo.paths import config_path, lock_path, log_path, save_path
from pomo.ui.app import PomoApp

log = logging.getLogger(__name__)

INIT_DONE = """\
Wrote {path} (only you can read it).
It holds a private ntfy topic made just for you. For pings on your phone:
  1. Install the ntfy app and subscribe to the topic in that file.
  2. Run: pomo --test-ping"""

DESCRIPTION = (
    "A pomodoro timer for your terminal, with cats. "
    "Pings your desktop, and your phone via ntfy, when each phase ends."
)
EPILOG = """\
keys:
  space  start / pause        s  skip phase        r  reset phase
  + / -  add / remove 5 min   i  idle mode         q  quit
  1-5    pick a care tool: feed, ball, string, pet, scoop     esc  put it down

config file (all keys optional), default ~/.config/pomo/config.toml.
pomo --init writes one for you, with a private ntfy topic; pomo --test-ping checks it:
  ntfy_server = "https://ntfy.sh"
  topic = ""          # your ntfy topic; empty disables phone pings
  focus = 25          # minutes
  short_break = 5
  long_break = 15
  long_every = 4      # a long break after this many focus sessions
  auto_continue = false  # true: go straight on into the next phase instead of waiting for space

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
    parser.add_argument("--idle", action="store_true", help="start in Idle mode: no timer, every care tool unlocked")
    parser.add_argument("--auto-continue", action="store_true",
                        help="go straight on into the next phase instead of waiting for space")
    parser.add_argument("--no-notify", action="store_true", help="no desktop or phone notifications")
    parser.add_argument("--config", type=Path, metavar="PATH", help="config file to use instead of the default")
    parser.add_argument("--init", action="store_true", help="write a starter config file with a private ntfy topic")
    parser.add_argument("--test-ping", action="store_true", help="send a test notification to your desktop and phone")
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
    if args.init:
        return init(args.config.expanduser() if args.config is not None else config_path())
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
            auto_continue=True if args.auto_continue else None,
        )
    except ConfigError as e:
        print(f"pomo: {e}", file=sys.stderr)
        return 2

    setup_logging(log_path())
    if args.test_ping:
        lines, ok = send_test_ping(cfg, display_path(path))
        print("\n".join(lines))
        return 0 if ok else 1
    lock = acquire(lock_path())
    if lock is None:
        print("pomo is already running in another window.", file=sys.stderr)
        return 1
    try:
        return run(args, cfg, path)
    finally:
        lock.release()


def init(path: Path) -> int:
    """`pomo --init`. The topic stays in the file: never printed, so it stays out of scrollback."""
    if not write_starter(path, new_topic()):
        print(f"{display_path(path)} already exists, so pomo left it alone.")
        return 0
    print(INIT_DONE.format(path=display_path(path)))
    return 0


def run(args: argparse.Namespace, cfg: Config, path: Path) -> int:
    """The timer itself, with the lock held."""
    warnings = [w for w in [permission_warning(path, cfg), truecolor_warning(os.environ)] if w]
    try:
        saved = persist.load(save_path())
    except persist.BadSave as e:
        log.warning("unreadable save: %s", e)
        try:
            kept = persist.back_up(save_path(), datetime.now())
        except OSError as move_error:
            print(f"pomo: can't read the save or move it aside ({move_error.strerror})", file=sys.stderr)
            return 2
        saved = None
        warnings.append(f"Your save couldn't be read, so pomo started fresh. The old one is kept as {kept.name}.")
    app = PomoApp(cfg, RealClock(), NullNotifier(), warnings=warnings, keep_awake=keep_awake(), idle=args.idle,
                  saved=saved, save_path=save_path())
    if not args.no_notify:
        # The bell must ring on Textual's thread; notifications arrive from a worker thread.
        app.notifier = Notifier(cfg.ntfy_server, cfg.topic, bell=lambda: app.call_from_thread(app.bell))
    app.run()
    return 0
