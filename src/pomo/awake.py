"""Keep macOS from idle-sleeping while a phase runs.

time.monotonic() stops while the Mac sleeps, so without this a break you walk away
from freezes part-way through and its "Break's over" ping never fires. Only idle
system sleep is blocked: the display still sleeps, and closing the lid still sleeps
the Mac (the timer then simply resumes where it was).
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from typing import Protocol

log = logging.getLogger(__name__)


class KeepsAwake(Protocol):
    def hold(self, on: bool) -> None: ...


class NoKeepAwake:
    def hold(self, on: bool) -> None:
        pass


class Caffeinate:
    """`caffeinate -i -w <our pid>`: the assertion also dies with us if we crash."""

    def __init__(self, popen: Callable[..., subprocess.Popen] = subprocess.Popen) -> None:
        self._popen = popen
        self._process: subprocess.Popen | None = None
        self._failed = False

    def hold(self, on: bool) -> None:
        if on and self._process is None and not self._failed:
            try:
                self._process = self._popen(
                    ["caffeinate", "-i", "-w", str(os.getpid())],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except OSError as e:
                self._failed = True  # don't retry four times a second
                log.warning("can't keep the Mac awake: %s", type(e).__name__)
        elif not on and self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                pass
            self._process = None


def keep_awake() -> KeepsAwake:
    if sys.platform == "darwin" and shutil.which("caffeinate"):
        return Caffeinate()
    return NoKeepAwake()  # Linux is best effort (spec §14)
