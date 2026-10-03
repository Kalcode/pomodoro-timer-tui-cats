"""Desktop and ntfy phone pings on phase transitions (spec §9, IDEA.md).

Nothing in here may ever raise into the timer: every failure is logged and dropped.
The ntfy topic is a secret, so it never appears in a log line.
"""

from __future__ import annotations

import base64
import logging
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pomo.config import Config
from pomo.timer import Phase, Transition

log = logging.getLogger(__name__)

RETRY_DELAY_S = 2.0
HTTP_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class Ping:
    title: str
    body: str


TEST_PING = Ping("🍅 pomo test", "If you can read this, pings work. Mango says hi.")
BANNER_HINT = " No banner? Allow notifications for Script Editor in System Settings → Notifications."


class Notifies(Protocol):
    def send(self, ping: Ping) -> None: ...


def ping_for(transition: Transition, cfg: Config, cat_line: str = "") -> Ping:
    """The ping for a finished phase. cat_line, if any, ends the body (spec §9)."""
    minutes = round(transition.ended_length_s / 60)
    tail = f" {cat_line}" if cat_line else ""
    if transition.ended is Phase.FOCUS:
        break_minutes = cfg.long_break if transition.started is Phase.LONG_BREAK else cfg.short_break
        return Ping(
            "🍅 Pomodoro done!",
            f"{minutes} minutes of focus complete. Time for a {break_minutes} min break.{tail}",
        )
    return Ping("☕ Break's over", f"{minutes} min break complete. Time to focus for {cfg.focus} minutes.{tail}")


def encode_header(value: str) -> str:
    """urllib only sends latin-1 headers. ntfy accepts RFC 2047 for everything else."""
    if value.isascii():
        return value
    return "=?UTF-8?B?" + base64.b64encode(value.encode("utf-8")).decode("ascii") + "?="


def build_ntfy_request(ping: Ping, server: str, topic: str) -> urllib.request.Request:
    return urllib.request.Request(
        f"{server.rstrip('/')}/{urllib.parse.quote(topic, safe='')}",
        data=ping.body.encode("utf-8"),
        method="POST",
        headers={"Title": encode_header(ping.title), "Priority": "default", "Tags": "tomato,clock"},
    )


def urlopen_post(request: urllib.request.Request) -> None:
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_S) as response:
        response.read()


def desktop_notify(ping: Ping) -> bool:
    """Show a native notification. False when this machine has no way to show one."""
    if sys.platform == "darwin" and shutil.which("osascript"):
        # Title and body travel as argv, never spliced into the script, so quotes can't break it.
        command = [
            "osascript",
            "-e", "on run argv",
            "-e", "display notification (item 2 of argv) with title (item 1 of argv)",
            "-e", "end run",
            ping.title, ping.body,
        ]
    elif shutil.which("notify-send"):
        command = ["notify-send", ping.title, ping.body]
    else:
        return False
    try:
        subprocess.run(command, check=True, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError) as e:
        log.warning("desktop notification failed: %s", type(e).__name__)
        return False
    return True


def run_in_thread(job: Callable[[], None]) -> None:
    threading.Thread(target=job, daemon=True).start()


def _describe(error: Exception) -> str:
    """A log-safe description: never the URL, which contains the topic."""
    if isinstance(error, urllib.error.HTTPError):
        return f"HTTP {error.code}"
    return type(error).__name__


def send_test_ping(
    cfg: Config,
    config_shown: str,
    *,
    desktop: Callable[[Ping], bool] | None = None,
    post: Callable[[urllib.request.Request], None] | None = None,
    platform: str = sys.platform,
) -> tuple[list[str], bool]:
    """`pomo --test-ping`: one notification, sent now on this thread. Returns a line per channel, and
    whether every channel it tried worked. The lines never show the topic or the URL."""
    desktop, post = desktop or desktop_notify, post or urlopen_post
    lines, ok = [], True
    if desktop(TEST_PING):
        lines.append("desktop: sent." + (BANNER_HINT if platform == "darwin" else ""))
    else:
        lines.append("desktop: couldn't show a notification here.")
        ok = False
    if not cfg.topic:
        lines.append(f"phone: no topic set in {config_shown} (run pomo --init).")
    else:
        try:
            post(build_ntfy_request(TEST_PING, cfg.ntfy_server, cfg.topic))
        except Exception as e:  # whatever went wrong is the answer the user asked for
            lines.append(f"phone: failed ({_describe(e)}).")
            ok = False
        else:
            lines.append("phone: sent to your ntfy topic.")
    return lines, ok


class Notifier:
    def __init__(
        self,
        server: str,
        topic: str,
        *,
        bell: Callable[[], None],
        desktop: Callable[[Ping], bool] = desktop_notify,
        post: Callable[[urllib.request.Request], None] = urlopen_post,
        sleep: Callable[[float], None] = time.sleep,
        run: Callable[[Callable[[], None]], None] = run_in_thread,
    ) -> None:
        self._server = server
        self._topic = topic
        self._bell = bell
        self._desktop = desktop
        self._post = post
        self._sleep = sleep
        self._run = run

    def send(self, ping: Ping) -> None:
        self._run(lambda: self._deliver(ping))

    def _deliver(self, ping: Ping) -> None:
        try:
            if not self._desktop(ping):
                self._bell()
        except Exception as e:  # never let a notification take the timer down
            log.warning("desktop notification crashed: %s", type(e).__name__)
        if self._topic:
            self._publish(ping)

    def _publish(self, ping: Ping) -> None:
        request = build_ntfy_request(ping, self._server, self._topic)
        for attempt in (1, 2):
            try:
                self._post(request)
                return
            except Exception as e:  # offline, DNS, HTTP 5xx...: all non-fatal
                log.warning("ntfy publish failed (attempt %d of 2): %s", attempt, _describe(e))
                if attempt == 1:
                    self._sleep(RETRY_DELAY_S)
        log.warning("ntfy publish gave up")


class NullNotifier:
    """--no-notify."""

    def send(self, ping: Ping) -> None:
        pass
