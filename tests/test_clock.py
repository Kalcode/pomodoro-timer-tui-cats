import pytest

from pomo.clock import FakeClock, RealClock


def test_fake_clock_only_moves_when_advanced():
    clock = FakeClock(start=50.0)
    assert clock.now() == 50.0
    clock.advance(1.5)
    assert clock.now() == 51.5


def test_fake_clock_refuses_to_go_backwards():
    with pytest.raises(ValueError):
        FakeClock().advance(-1)


def test_real_clock_never_goes_backwards():
    clock = RealClock()
    first = clock.now()
    assert clock.now() >= first
