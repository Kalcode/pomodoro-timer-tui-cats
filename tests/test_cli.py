import random

import pytest

from pomo import cli, persist
from pomo.clock import FakeClock
from pomo.game.cat import Cat, Trait
from pomo.game.world import World
from pomo.lock import acquire
from pomo.paths import lock_path, save_path
from pomo.session import Session
from pomo.timer import TimerSettings
from pomo.gallery import GalleryApp
from pomo.notify import NullNotifier, Notifier
from pomo.ui.app import PomoApp


@pytest.fixture
def launched(monkeypatch):
    """Stop main() before it takes over the terminal and hand back the app it built."""
    apps = []
    monkeypatch.setattr(PomoApp, "run", lambda self: apps.append(self))
    return apps


def test_help_documents_every_flag(capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--help"])
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    for flag in ["--focus", "--short-break", "--long-break", "--long-every", "--no-notify", "--config", "--gallery",
                 "--version"]:
        assert flag in out
    assert "config.toml" in out and "topic" in out


def test_topic_is_not_a_flag(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--topic", "abc"])
    assert "unrecognized arguments" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["0", "-5", "ten"])
def test_bad_durations_are_rejected_by_argparse(value, capsys):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--focus", value])
    assert exit_info.value.code == 2


def test_broken_config_prints_one_line_and_exits_2(tmp_path, capsys, launched):
    path = tmp_path / "config.toml"
    path.write_text("focus = = 1")
    assert cli.main(["--config", str(path)]) == 2
    err = capsys.readouterr().err
    assert err.startswith("pomo: ") and "Traceback" not in err
    assert launched == []


def test_flags_override_the_config_file(tmp_path, launched):
    path = tmp_path / "config.toml"
    path.write_text("focus = 30\nshort_break = 10\n")
    assert cli.main(["--config", str(path), "--focus", "50"]) == 0
    (app,) = launched
    assert (app.config.focus, app.config.short_break) == (50, 10)


def test_notifications_are_on_by_default_and_off_with_no_notify(launched):
    cli.main([])
    cli.main(["--no-notify"])
    assert isinstance(launched[0].notifier, Notifier)
    assert isinstance(launched[1].notifier, NullNotifier)


def test_permission_warning_reaches_the_app(tmp_path, launched):
    path = tmp_path / "config.toml"
    path.write_text('topic = "s3cret"')
    path.chmod(0o644)
    cli.main(["--config", str(path)])
    assert any("chmod 600" in w for w in launched[0]._warnings)


def test_logs_go_to_the_state_dir(tmp_path, launched):
    cli.main([])
    assert (tmp_path / "state" / "pomo").is_dir()


def test_a_missing_config_named_by_flag_exits_2(tmp_path, capsys, launched):
    missing = tmp_path / "confg-typo.toml"
    assert cli.main(["--config", str(missing)]) == 2
    assert "not found" in capsys.readouterr().err
    assert launched == []


def test_config_flag_expands_the_home_directory(tmp_path, monkeypatch, launched):
    # zsh and bash leave "~" alone in --config=~/..., so pomo expands it itself.
    monkeypatch.setenv("HOME", str(tmp_path))
    (tmp_path / "pomo.toml").write_text("focus = 42\n")
    assert cli.main(["--config=~/pomo.toml"]) == 0
    assert launched[0].config.focus == 42


def test_gallery_flag_opens_the_gallery_instead_of_the_timer(monkeypatch, launched):
    galleries = []
    monkeypatch.setattr(GalleryApp, "run", lambda self: galleries.append(self))
    assert cli.main(["--gallery"]) == 0
    assert len(galleries) == 1 and launched == []


def test_truecolor_warning():
    assert cli.truecolor_warning({"COLORTERM": "truecolor"}) is None
    assert cli.truecolor_warning({"COLORTERM": "24bit"}) is None
    assert "24-bit" in cli.truecolor_warning({})


def test_a_terminal_without_truecolor_gets_warned(monkeypatch, launched):
    monkeypatch.delenv("COLORTERM", raising=False)
    cli.main([])
    assert any("24-bit" in w for w in launched[0]._warnings)
    monkeypatch.setenv("COLORTERM", "truecolor")
    cli.main([])
    assert not any("24-bit" in w for w in launched[1]._warnings)


def test_idle_flag_starts_the_app_in_idle_mode(launched):
    cli.main([])
    cli.main(["--idle"])
    assert [app.session.idle for app in launched] == [False, True]


def test_help_mentions_idle_and_the_tool_keys(capsys):
    with pytest.raises(SystemExit):
        cli.main(["--help"])
    out = capsys.readouterr().out
    assert "--idle" in out
    assert "i  idle mode" in out and "1-5" in out


def a_written_save(focus_total: int) -> None:
    clock = FakeClock()
    session = Session(TimerSettings.from_minutes(25, 5, 15, 4), clock)
    world = World([Cat("Mango", "tabby", Trait.CLINGY)], random.Random(0))
    world.focus_total = focus_total
    persist.write(save_path(), persist.snapshot(session, world, saved_at=0.0))


def test_the_save_is_loaded_and_saving_goes_back_to_it(launched):
    a_written_save(focus_total=12)
    assert cli.main([]) == 0
    (app,) = launched
    assert app.world.focus_total == 12
    assert app.save_path == save_path()


def test_with_no_save_mango_starts_fresh(launched):
    cli.main([])
    assert [c.name for c in launched[0].world.cats] == ["Mango"]


def test_an_unreadable_save_is_kept_aside_and_pomo_starts_fresh(launched):
    save_path().parent.mkdir(parents=True, exist_ok=True)
    save_path().write_text("not a save")
    assert cli.main([]) == 0
    (app,) = launched
    assert app.world.focus_total == 0
    (kept,) = save_path().parent.glob("save.json.bak-*")
    assert kept.read_text() == "not a save"
    assert not save_path().exists()
    assert any("couldn't be read" in w and kept.name in w for w in app._warnings)


def test_a_second_pomo_is_turned_away(launched, capsys):
    held = acquire(lock_path())
    try:
        assert cli.main([]) == 1
    finally:
        held.release()
    assert launched == []
    assert "already running" in capsys.readouterr().err


def test_the_lock_is_let_go_when_pomo_ends(launched):
    cli.main([])
    lock = acquire(lock_path())
    assert lock is not None
    lock.release()
