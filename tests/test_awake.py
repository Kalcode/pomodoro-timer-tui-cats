import logging
import os

from pomo import awake
from pomo.awake import Caffeinate, NoKeepAwake, keep_awake


class FakeProcess:
    def __init__(self, argv):
        self.argv = argv
        self.terminated = False
        self.waited = False

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.waited = True


class FakePopen:
    def __init__(self, fail=False):
        self.fail = fail
        self.spawned = []

    def __call__(self, argv, **kwargs):
        if self.fail:
            raise FileNotFoundError("caffeinate")
        process = FakeProcess(argv)
        self.spawned.append(process)
        return process


def test_holding_starts_one_caffeinate_tied_to_this_process():
    popen = FakePopen()
    caffeinate = Caffeinate(popen=popen)
    caffeinate.hold(True)
    caffeinate.hold(True)
    assert [p.argv for p in popen.spawned] == [["caffeinate", "-i", "-w", str(os.getpid())]]


def test_letting_go_stops_it_and_holding_again_starts_a_new_one():
    popen = FakePopen()
    caffeinate = Caffeinate(popen=popen)
    caffeinate.hold(True)
    caffeinate.hold(False)
    caffeinate.hold(False)
    first = popen.spawned[0]
    assert first.terminated and first.waited
    caffeinate.hold(True)
    assert len(popen.spawned) == 2


def test_a_missing_caffeinate_is_logged_once_and_never_retried(caplog):
    popen = FakePopen(fail=True)
    caffeinate = Caffeinate(popen=popen)
    with caplog.at_level(logging.WARNING):
        for _ in range(5):
            caffeinate.hold(True)  # must not raise
    assert len([r for r in caplog.records if "awake" in r.getMessage()]) == 1


def test_keep_awake_picks_caffeinate_only_on_a_mac_that_has_it(monkeypatch):
    monkeypatch.setattr(awake.sys, "platform", "darwin")
    monkeypatch.setattr(awake.shutil, "which", lambda name: "/usr/bin/caffeinate")
    assert isinstance(keep_awake(), Caffeinate)
    monkeypatch.setattr(awake.sys, "platform", "linux")
    assert isinstance(keep_awake(), NoKeepAwake)
