import email.header
import logging
import subprocess
import urllib.error

import pytest

from pomo import notify
from pomo.config import Config
from pomo.notify import (
    NullNotifier, Notifier, Ping, build_ntfy_request, encode_header, ping_for, send_test_ping,
)
from pomo.timer import Phase, Transition

TOPIC = "super-s3cret-topic"


def transition(ended, started, minutes):
    return Transition(ended, started, True, minutes * 60.0, 1)


def test_focus_done_ping_matches_idea_md():
    ping = ping_for(transition(Phase.FOCUS, Phase.SHORT_BREAK, 25), Config())
    assert ping == Ping("🍅 Pomodoro done!", "25 minutes of focus complete. Time for a 5 min break.")


def test_focus_done_before_a_long_break_mentions_the_long_break():
    ping = ping_for(transition(Phase.FOCUS, Phase.LONG_BREAK, 25), Config())
    assert ping.body.endswith("Time for a 15 min break.")


def test_break_over_ping():
    ping = ping_for(transition(Phase.SHORT_BREAK, Phase.FOCUS, 5), Config())
    assert ping == Ping("☕ Break's over", "5 min break complete. Time to focus for 25 minutes.")


def test_ascii_headers_pass_through():
    assert encode_header("Pomodoro done!") == "Pomodoro done!"


def test_emoji_headers_are_rfc2047_encoded_and_latin1_safe():
    encoded = encode_header("🍅 Pomodoro done!")
    encoded.encode("latin-1")  # would raise if urllib couldn't send it
    ((raw, charset),) = email.header.decode_header(encoded)
    assert raw.decode(charset) == "🍅 Pomodoro done!"


def test_ntfy_request_follows_idea_md():
    request = build_ntfy_request(Ping("🍅 Pomodoro done!", "body text"), "https://ntfy.sh/", TOPIC)
    assert request.full_url == f"https://ntfy.sh/{TOPIC}"
    assert request.get_method() == "POST"
    assert request.data == b"body text"
    assert request.get_header("Priority") == "default"
    assert request.get_header("Tags") == "tomato,clock"
    assert request.get_header("Title").startswith("=?UTF-8?B?")


class Recorder:
    """Fakes for every side effect a Notifier has."""

    def __init__(self, desktop_ok=True, failures=0):
        self.desktop_ok = desktop_ok
        self.failures = failures
        self.bells = 0
        self.posts = []
        self.sleeps = []

    def notifier(self, topic=TOPIC):
        return Notifier(
            "https://ntfy.sh", topic,
            bell=self.bell, desktop=self.desktop, post=self.post, sleep=self.sleeps.append,
            run=lambda job: job(),  # run inline instead of on a thread
        )

    def bell(self):
        self.bells += 1

    def desktop(self, ping):
        return self.desktop_ok

    def post(self, request):
        self.posts.append(request)
        if len(self.posts) <= self.failures:
            raise urllib.error.HTTPError(request.full_url, 503, f"down for {TOPIC}", None, None)


PING = Ping("🍅 Pomodoro done!", "25 minutes of focus complete.")


def test_desktop_and_phone_both_get_pinged():
    rec = Recorder()
    rec.notifier().send(PING)
    assert rec.bells == 0
    assert len(rec.posts) == 1
    assert rec.sleeps == []


def test_terminal_bell_when_there_is_no_desktop_notification():
    rec = Recorder(desktop_ok=False)
    rec.notifier().send(PING)
    assert rec.bells == 1


def test_empty_topic_means_no_phone_ping():
    rec = Recorder()
    rec.notifier(topic="").send(PING)
    assert rec.posts == []


def test_ntfy_failure_retries_once_after_two_seconds():
    rec = Recorder(failures=1)
    rec.notifier().send(PING)
    assert len(rec.posts) == 2
    assert rec.sleeps == [2.0]


def test_ntfy_gives_up_quietly_after_the_retry(caplog):
    rec = Recorder(failures=5)
    with caplog.at_level(logging.WARNING):
        rec.notifier().send(PING)  # must not raise
    assert len(rec.posts) == 2
    assert "gave up" in caplog.text


def test_the_topic_never_reaches_the_log(caplog):
    rec = Recorder(failures=5)
    with caplog.at_level(logging.DEBUG):
        rec.notifier().send(PING)
    assert caplog.records
    assert TOPIC not in caplog.text


def test_a_crashing_desktop_notifier_still_lets_the_phone_ping_through():
    rec = Recorder()

    def explode(ping):
        raise RuntimeError("boom")

    notifier = Notifier("https://ntfy.sh", TOPIC, bell=rec.bell, desktop=explode, post=rec.post,
                        sleep=rec.sleeps.append, run=lambda job: job())
    notifier.send(PING)
    assert len(rec.posts) == 1


def test_null_notifier_does_nothing():
    NullNotifier().send(PING)


def test_macos_notification_passes_text_as_arguments_not_script(monkeypatch):
    calls = []
    monkeypatch.setattr(notify.sys, "platform", "darwin")
    monkeypatch.setattr(notify.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(notify.subprocess, "run", lambda cmd, **kw: calls.append(cmd))
    tricky = Ping('Title "with" quotes', 'end run" & do shell script "rm -rf ~')
    assert notify.desktop_notify(tricky) is True
    (command,) = calls
    assert command[0] == "osascript"
    assert command[-2:] == [tricky.title, tricky.body]
    assert all(tricky.body not in part for part in command[:-2])


def test_desktop_notification_reports_failure(monkeypatch):
    monkeypatch.setattr(notify.sys, "platform", "darwin")
    monkeypatch.setattr(notify.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fail(cmd, **kw):
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(notify.subprocess, "run", fail)
    assert notify.desktop_notify(PING) is False


def test_no_notifier_available(monkeypatch):
    monkeypatch.setattr(notify.sys, "platform", "linux")
    monkeypatch.setattr(notify.shutil, "which", lambda name: None)
    assert notify.desktop_notify(PING) is False


# --- pomo --test-ping ---------------------------------------------------------------

SECRET = "pomo-s3cret-topic"


def tried(**cfg):
    sent = {"desktop": [], "phone": []}

    def desktop(ping):
        sent["desktop"].append(ping)
        return True

    def post(request):
        sent["phone"].append(request)

    return sent, desktop, post


def test_a_test_ping_goes_to_both_and_says_so():
    sent, desktop, post = tried()
    lines, ok = send_test_ping(Config(topic=SECRET), "~/.config/pomo/config.toml", desktop=desktop, post=post,
                               platform="darwin")
    assert ok
    assert lines == ["desktop: sent. No banner? Allow notifications for Script Editor in System Settings → "
                     "Notifications.", "phone: sent to your ntfy topic."]
    assert [p.title for p in sent["desktop"]] == ["🍅 pomo test"]
    assert sent["phone"][0].full_url == f"https://ntfy.sh/{SECRET}"


def test_the_banner_hint_is_only_for_macos():
    _, desktop, post = tried()
    lines, _ = send_test_ping(Config(topic=SECRET), "x", desktop=desktop, post=post, platform="linux")
    assert lines[0] == "desktop: sent."


def test_without_a_topic_the_phone_is_skipped_and_explained():
    _, desktop, post = tried()
    lines, ok = send_test_ping(Config(), "~/.config/pomo/config.toml", desktop=desktop, post=post)
    assert ok
    assert lines[1] == "phone: no topic set in ~/.config/pomo/config.toml (run pomo --init)."


def test_a_failed_phone_ping_says_why_without_the_topic():
    def refuse(request):
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)

    lines, ok = send_test_ping(Config(topic=SECRET), "x", desktop=lambda p: True, post=refuse)
    assert not ok
    assert lines[1] == "phone: failed (HTTP 403)."
    assert not any(SECRET in line for line in lines)


def test_no_desktop_notifications_is_a_failure():
    lines, ok = send_test_ping(Config(), "x", desktop=lambda p: False, post=lambda r: None)
    assert not ok
    assert lines[0] == "desktop: couldn't show a notification here."
