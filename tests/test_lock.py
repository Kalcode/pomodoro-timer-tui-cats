from pomo.lock import acquire


def test_only_one_holder_at_a_time(tmp_path):
    path = tmp_path / "state" / "pomo.lock"
    first = acquire(path)
    assert first is not None
    assert acquire(path) is None
    first.release()
    second = acquire(path)
    assert second is not None
    second.release()


def test_releasing_twice_is_harmless(tmp_path):
    lock = acquire(tmp_path / "pomo.lock")
    lock.release()
    lock.release()
