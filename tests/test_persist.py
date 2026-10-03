import json
import random
from datetime import datetime

import pytest

from pomo import persist
from pomo.clock import FakeClock
from pomo.game.cat import Cat, Trait
from pomo.game.world import Poop, World
from pomo.persist import BadSave, Saved
from pomo.session import Session, SessionState
from pomo.timer import Phase, TimerSettings

MIN = 60.0


def a_day_in_progress() -> tuple[Session, World]:
    """Mango on the shelf, a little grumpy and hungry, two focus sessions into a set, on a break."""
    clock = FakeClock()
    session = Session(TimerSettings.from_minutes(25, 5, 15, 4), clock)
    for _ in range(3):  # focus, break, focus: now on the second break
        if not session.timer.running:
            session.toggle()
        clock.advance(session.timer.remaining())
        session.tick()
    clock.advance(2 * MIN)
    mango = Cat("Mango", "tabby", Trait.CLINGY, mood=62.5, needs={"hunger": 75.0, "play": 10.0, "affection": 33.0})
    world = World([mango], random.Random(1))
    world.place("Mango", "shelf", 55.0)
    world.bowl_full, world.focus_total = False, 17
    world.poops = [Poop(20.0, world.scape.floor.y)]
    return session, world


def saved_dict() -> dict:
    session, world = a_day_in_progress()
    return json.loads(json.dumps(persist.snapshot(session, world, saved_at=1_759_500_000.0)))


def test_a_save_comes_back_exactly():
    saved = persist.read(saved_dict())
    assert saved.saved_at == 1_759_500_000.0
    assert saved.session == SessionState(Phase.SHORT_BREAK, 2, True, False, 3 * MIN, False)
    (mango,) = saved.cats
    assert (mango.cat.name, mango.cat.coat, mango.cat.trait, mango.cat.mood) == ("Mango", "tabby", Trait.CLINGY, 62.5)
    assert mango.cat.needs == {"hunger": 75.0, "play": 10.0, "affection": 33.0}
    assert (mango.surface, mango.x) == ("shelf", 55.0)
    assert (saved.bowl_full, saved.focus_total, saved.poops) == (False, 17, (20.0,))


def test_the_saved_world_is_rebuilt_as_it_was():
    world = persist.build_world(persist.read(saved_dict()), random.Random(2))
    (mango,) = world.cats
    body = world.bodies["Mango"]
    assert (mango.mood, mango.needs["hunger"]) == (62.5, 75.0)
    assert (body.surface, body.x, body.y) == ("shelf", 55.0, world.scape.shelf.y)
    assert (world.bowl_full, world.focus_total) == (False, 17)
    assert [(p.x, p.y) for p in world.poops] == [(20.0, world.scape.floor.y)]


def test_the_file_holds_what_the_spec_says(tmp_path):
    path = tmp_path / "save.json"
    persist.write(path, saved_dict())
    data = json.loads(path.read_text())
    assert data["version"] == 1
    assert data["timer"] == {"phase": "short_break", "focus_in_set": 2, "set_clean": True,
                             "focus_in_progress": False, "break_left": 180.0, "idle": False}
    assert data["world"]["cats"][0]["surface"] == "shelf"


def test_writing_replaces_the_save_and_leaves_nothing_else_behind(tmp_path):
    path = tmp_path / "state" / "save.json"
    persist.write(path, {"n": 1})
    persist.write(path, {"n": 2})
    assert json.loads(path.read_text()) == {"n": 2}
    assert [p.name for p in path.parent.iterdir()] == ["save.json"]


def test_a_write_that_fails_leaves_the_old_save_alone(tmp_path):
    path = tmp_path / "save.json"
    persist.write(path, {"n": 1})
    with pytest.raises(TypeError):
        persist.write(path, {"n": object()})  # can't be written as JSON
    assert json.loads(path.read_text()) == {"n": 1}
    assert [p.name for p in tmp_path.iterdir()] == ["save.json"]


def test_no_save_yet_is_none(tmp_path):
    assert persist.load(tmp_path / "save.json") is None


def test_load_reads_a_written_save(tmp_path):
    path = tmp_path / "save.json"
    persist.write(path, saved_dict())
    assert isinstance(persist.load(path), Saved)


def broken(change) -> dict:
    data = saved_dict()
    change(data)
    return data


@pytest.mark.parametrize("data", [
    [],
    broken(lambda d: d.update(version=2)),
    broken(lambda d: d.pop("timer")),
    broken(lambda d: d["timer"].update(phase="lunch")),
    broken(lambda d: d["timer"].update(idle="no")),
    broken(lambda d: d["timer"].update(focus_in_set=-1)),
    broken(lambda d: d["timer"].update(break_left="soon")),
    broken(lambda d: d["world"].update(cats=[])),
    broken(lambda d: d["world"]["cats"].append(dict(d["world"]["cats"][0]))),
    broken(lambda d: d["world"]["cats"][0].update(coat="plaid")),
    broken(lambda d: d["world"]["cats"][0].update(trait="sleepy")),
    broken(lambda d: d["world"]["cats"][0].update(surface="fridge")),
    broken(lambda d: d["world"]["cats"][0].update(name="")),
    broken(lambda d: d["world"]["cats"][0].update(mood=True)),
    broken(lambda d: d["world"]["cats"][0]["needs"].pop("play")),
    broken(lambda d: d["world"].update(focus_total=2.5)),
    broken(lambda d: d["world"].update(poops=[{"y": 3}])),
], ids=["not-a-table", "version", "no-timer", "phase", "idle", "count", "break-left", "no-cats", "twins", "coat",
        "trait", "surface", "nameless", "mood-bool", "needs", "total", "poop"])
def test_a_save_that_cannot_be_used_says_why(data):
    with pytest.raises(BadSave):
        persist.read(data)


@pytest.mark.parametrize("text", ["{not json", '{"version": 1, "saved_at": NaN}', "\udcff"])
def test_files_that_are_not_saves(tmp_path, text):
    path = tmp_path / "save.json"
    path.write_text(text, encoding="utf-8", errors="surrogateescape")
    with pytest.raises(BadSave):
        persist.load(path)


def test_numbers_out_of_range_are_clamped_not_rejected():
    def stretch(d):
        cat = d["world"]["cats"][0]
        cat["mood"], cat["needs"]["hunger"] = 150, -5
        d["timer"]["break_left"] = -3
    saved = persist.read(broken(stretch))
    assert (saved.cats[0].cat.mood, saved.cats[0].cat.needs["hunger"], saved.session.break_left) == (100, 0, 0)


def test_a_bad_save_is_put_aside_never_over_an_earlier_one(tmp_path):
    path = tmp_path / "save.json"
    when = datetime(2026, 10, 3, 9, 30, 5)
    path.write_text("first")
    first = persist.back_up(path, when)
    path.write_text("second")
    second = persist.back_up(path, when)
    assert (first.name, second.name) == ("save.json.bak-20261003-093005", "save.json.bak-20261003-093005-2")
    assert (first.read_text(), second.read_text()) == ("first", "second")
    assert not path.exists()



def a_wide_room() -> World:
    """A 170-column room (a 200-column terminal): Mango and a poop over by the bowl, far right."""
    world = World([Cat("Mango", "tabby", Trait.CLINGY)], random.Random(1), 170, 78)
    world.place("Mango", "floor", 150.0)
    world.poops = [Poop(150.0, world.scape.floor.y)]
    return world


def test_a_cat_by_the_bowl_in_a_wide_room_comes_back_where_it_was():
    session = Session(TimerSettings.from_minutes(25, 5, 15, 4), FakeClock())
    data = json.loads(json.dumps(persist.snapshot(session, a_wide_room(), saved_at=0.0)))
    world = persist.build_world(persist.read(data), random.Random(2))
    assert (world.scape.width, world.scape.height) == (170, 78)
    assert world.bodies["Mango"].x == 150.0
    assert [p.x for p in world.poops] == [150.0]


def test_a_save_without_a_room_size_uses_the_smallest_room():
    data = saved_dict()
    data["world"].pop("room", None)
    world = persist.build_world(persist.read(data), random.Random(2))
    assert (world.scape.width, world.scape.height) == (70, 54)


@pytest.mark.parametrize("room", [{"width": "wide", "height": 56}, {"width": 100}, [170, 78]])
def test_a_room_size_that_makes_no_sense_is_a_bad_save(room):
    data = saved_dict()
    data["world"]["room"] = room
    with pytest.raises(BadSave):
        persist.read(data)
