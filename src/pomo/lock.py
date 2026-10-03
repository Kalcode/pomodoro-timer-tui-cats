"""One pomo at a time (daily-driver addendum §2.5).

An exclusive flock on a lock file, held for the whole run. The operating system drops it
when the process ends, however it ends, so there's never a stale lock to clean up.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path


class Lock:
    def __init__(self, fd: int) -> None:
        self._fd = fd

    def release(self) -> None:
        if self._fd >= 0:
            os.close(self._fd)  # closing the file lets the lock go
            self._fd = -1


def acquire(path: Path) -> Lock | None:
    """The lock, or None while another pomo holds it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        return None
    return Lock(fd)
