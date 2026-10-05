import re
import stat
from pathlib import Path

import pytest

from pomo.config import (
    Config, ConfigError, load_config, new_topic, permission_warning, with_overrides, write_starter,
)
from pomo.paths import config_path, log_path, state_dir


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(text)
    return path


def test_missing_file_gives_defaults(tmp_path):
    assert load_config(tmp_path / "nope.toml") == Config()


def test_defaults_match_idea_md():
    cfg = Config()
    assert (cfg.ntfy_server, cfg.topic) == ("https://ntfy.sh", "")
    assert (cfg.focus, cfg.short_break, cfg.long_break, cfg.long_every) == (25, 5, 15, 4)


def test_reads_every_key(tmp_path):
    path = write(tmp_path, 'ntfy_server = "https://ntfy.example.com"\ntopic = "s3cret"\n'
                           "focus = 50\nshort_break = 10\nlong_break = 30\nlong_every = 3\n")
    assert load_config(path) == Config("https://ntfy.example.com", "s3cret", 50, 10, 30, 3)


def test_invalid_toml_is_a_config_error(tmp_path):
    with pytest.raises(ConfigError, match="not valid TOML"):
        load_config(write(tmp_path, "focus = = 5"))


def test_unknown_key_is_an_error_so_typos_are_not_silently_ignored(tmp_path):
    with pytest.raises(ConfigError, match="unknown key.*focus_minutes"):
        load_config(write(tmp_path, "focus_minutes = 30"))


@pytest.mark.parametrize("line, message", [
    ('focus = "25"', "focus must be a whole number"),
    ("focus = 2.5", "focus must be a whole number"),
    ("long_every = true", "long_every must be a whole number"),
    ("short_break = 0", "short_break must be between 1 and 1440"),
    ("long_break = -5", "long_break must be between 1 and 1440"),
    ("long_every = 0", "long_every must be between 1 and 100"),
    ("topic = 42", "topic must be a string"),
    ('ntfy_server = "ntfy.sh"', "must start with http"),
])
def test_bad_values_are_config_errors(tmp_path, line, message):
    with pytest.raises(ConfigError, match=message):
        load_config(write(tmp_path, line))


def test_overrides_replace_only_given_values():
    cfg = with_overrides(Config(focus=30), focus=None, short_break=7, long_break=None, long_every=None)
    assert (cfg.focus, cfg.short_break) == (30, 7)


def test_overrides_are_validated_too():
    with pytest.raises(ConfigError, match="command line: focus"):
        with_overrides(Config(), focus=0)


def test_permission_warning_when_topic_is_world_readable(tmp_path):
    path = write(tmp_path, 'topic = "s3cret"')
    path.chmod(0o644)
    warning = permission_warning(path, Config(topic="s3cret"))
    assert warning is not None and "chmod 600" in warning
    assert "s3cret" not in warning


def test_no_permission_warning_when_private_or_no_topic(tmp_path):
    path = write(tmp_path, 'topic = "s3cret"')
    path.chmod(0o600)
    assert permission_warning(path, Config(topic="s3cret")) is None
    path.chmod(0o644)
    assert permission_warning(path, Config(topic="")) is None


def test_paths_follow_xdg(tmp_path):
    # conftest points XDG_CONFIG_HOME / XDG_STATE_HOME into tmp_path
    assert config_path() == tmp_path / "config" / "pomo" / "config.toml"
    assert state_dir() == tmp_path / "state" / "pomo"
    assert log_path() == tmp_path / "state" / "pomo" / "pomo.log"


def test_relative_xdg_paths_are_ignored(monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", "relative/dir")
    assert config_path() == Path.home() / ".config" / "pomo" / "config.toml"


def test_the_topic_stays_out_of_reprs_so_crash_tracebacks_cannot_leak_it():
    # Textual prints tracebacks with show_locals=True, which reprs every Config in scope.
    assert "s3cret" not in repr(Config(topic="s3cret"))


def test_permission_warning_shortens_the_home_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    path = write(tmp_path, 'topic = "s3cret"')
    path.chmod(0o644)
    assert permission_warning(path, Config(topic="s3cret")) == (
        "~/config.toml holds your ntfy topic but others can read it. Run: chmod 600 ~/config.toml"
    )


def test_a_new_topic_is_long_random_and_safe_for_ntfy():
    topics = {new_topic() for _ in range(50)}
    assert len(topics) == 50
    assert all(re.fullmatch(r"pomo-[A-Za-z0-9_-]{22}", t) for t in topics)


def test_the_starter_file_is_private_and_loads(tmp_path):
    path = tmp_path / "pomo" / "config.toml"
    assert write_starter(path, "pomo-abc_DEF-123")
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    cfg = load_config(path)
    assert cfg == Config(topic="pomo-abc_DEF-123")
    assert cfg.topic == "pomo-abc_DEF-123"
    assert permission_warning(path, cfg) is None


def test_the_starter_never_overwrites_a_config(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text("focus = 50\n")
    assert not write_starter(path, "pomo-new")
    assert path.read_text() == "focus = 50\n"


def test_phases_wait_for_you_unless_auto_continue_is_on(tmp_path):
    assert Config().auto_continue is False
    assert load_config(write(tmp_path, "auto_continue = true\n")).auto_continue is True
    assert with_overrides(Config(), auto_continue=True).auto_continue is True
    assert with_overrides(Config(auto_continue=True), auto_continue=None).auto_continue is True


def test_auto_continue_must_be_true_or_false(tmp_path):
    with pytest.raises(ConfigError, match="auto_continue must be true or false"):
        load_config(write(tmp_path, 'auto_continue = "yes"\n'))


def test_the_starter_config_mentions_auto_continue(tmp_path):
    path = tmp_path / "config.toml"
    write_starter(path, "pomo-x")
    assert "auto_continue = false" in path.read_text()
