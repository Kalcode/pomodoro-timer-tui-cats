import pytest

from pomo import cli
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
    for flag in ["--focus", "--short-break", "--long-break", "--long-every", "--no-notify", "--config", "--version"]:
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
