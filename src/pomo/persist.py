"""Saving and loading (daily-driver addendum §2): versioned JSON, written atomically.

`snapshot` turns the session and the world into plain data. `read` checks a save over
and turns it back into a `Saved`, or raises `BadSave` saying why. `write` swaps a new
save in with a rename, so a crash can never leave half of one, and `back_up` puts a
bad save aside so pomo can start fresh without losing it.
"""

from __future__ import annotations

import json
import math
import os
import random
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from pomo.game.behavior import Body
from pomo.game.cat import NEEDS, Cat, Trait
from pomo.game.playscape import MIN_HEIGHT, MIN_WIDTH, layout
from pomo.game.world import Poop, World
from pomo.render.sprites import COATS
from pomo.session import Session, SessionState
from pomo.timer import Phase

VERSION = 1
SURFACES = frozenset(s.name for s in layout(MIN_WIDTH, MIN_HEIGHT).surfaces)


class BadSave(Exception):
    """The save can't be used. The message says why."""


@dataclass(frozen=True)
class SavedCat:
    cat: Cat
    surface: str
    x: float


@dataclass(frozen=True)
class Saved:
    saved_at: float  # wall-clock seconds since the epoch
    session: SessionState
    cats: tuple[SavedCat, ...]
    bowl_full: bool
    focus_total: int
    poops: tuple[float, ...]  # columns: poops are always on the floor
    room: tuple[int, int] = (MIN_WIDTH, MIN_HEIGHT)  # the room's size when saved, so columns mean the same


# --- out ---------------------------------------------------------------------------


def snapshot(session: Session, world: World, saved_at: float) -> dict:
    s = session.state()
    return {
        "version": VERSION,
        "saved_at": saved_at,
        "timer": {"phase": s.phase.value, "focus_in_set": s.focus_in_set, "set_clean": s.set_clean,
                  "focus_in_progress": s.focus_in_progress, "break_left": s.break_left, "idle": s.idle},
        "world": {
            "room": {"width": world.scape.width, "height": world.scape.height},
            "bowl_full": world.bowl_full,
            "focus_total": world.focus_total,
            "cats": [_cat_out(cat, world.bodies[cat.name]) for cat in world.cats],
            "poops": [{"x": poop.x} for poop in world.poops],
        },
    }


def _cat_out(cat: Cat, body: Body) -> dict:
    # A cat mid-jump is saved on the surface it jumped from: the column puts it back on its way.
    return {"name": cat.name, "coat": cat.coat, "trait": cat.trait.value, "mood": cat.mood,
            "needs": dict(cat.needs), "surface": body.surface, "x": body.x}


def write(path: Path, data: dict) -> None:
    """Swap a new save in: a temporary file beside it, flushed to disk, then renamed over it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# --- in ----------------------------------------------------------------------------


def load(path: Path) -> Saved | None:
    """The save at path, or None if there isn't one yet. Raises BadSave if it can't be used."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except (OSError, UnicodeDecodeError) as e:
        raise BadSave(f"can't read it ({type(e).__name__})") from None
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise BadSave(f"not valid JSON ({e.msg})") from None
    return read(data)


def read(data: object) -> Saved:
    root = _table(data, "the save")
    if root.get("version") != VERSION:
        raise BadSave(f"unknown version {root.get('version')!r}")
    timer, world = _table(root.get("timer"), "timer"), _table(root.get("world"), "world")
    break_left = timer.get("break_left")
    session = SessionState(
        phase=_choice(timer.get("phase"), {p.value: p for p in Phase}, "timer.phase"),
        focus_in_set=_count(timer.get("focus_in_set"), "timer.focus_in_set"),
        set_clean=_flag(timer.get("set_clean"), "timer.set_clean"),
        focus_in_progress=_flag(timer.get("focus_in_progress"), "timer.focus_in_progress"),
        break_left=None if break_left is None else max(0.0, _number(break_left, "timer.break_left")),
        idle=_flag(timer.get("idle"), "timer.idle"),
    )
    cats = tuple(_cat_in(c, i) for i, c in enumerate(_list(world.get("cats"), "world.cats")))
    if not cats:
        raise BadSave("no cats")
    names = [c.cat.name for c in cats]
    if len(set(names)) != len(names):
        raise BadSave("two cats share a name")
    poops = tuple(_number(_table(p, "a poop").get("x"), "poop x") for p in _list(world.get("poops"), "world.poops"))
    return Saved(_number(root.get("saved_at"), "saved_at"), session, cats,
                 _flag(world.get("bowl_full"), "world.bowl_full"),
                 _count(world.get("focus_total"), "world.focus_total"), poops, _room(world.get("room")))


def _room(value: object) -> tuple[int, int]:
    """The room's size when saved. Optional: without it, the smallest room."""
    if value is None:
        return MIN_WIDTH, MIN_HEIGHT
    room = _table(value, "world.room")
    width, height = _count(room.get("width"), "room width"), _count(room.get("height"), "room height")
    return max(width, MIN_WIDTH), max(height, MIN_HEIGHT)


def _cat_in(data: object, i: int) -> SavedCat:
    d = _table(data, f"cat {i + 1}")
    name = d.get("name")
    if not isinstance(name, str) or not name:
        raise BadSave(f"cat {i + 1} has no name")
    needs = _table(d.get("needs"), f"{name}'s needs")
    cat = Cat(
        name,
        _choice(d.get("coat"), {c: c for c in COATS}, f"{name}'s coat"),
        _choice(d.get("trait"), {t.value: t for t in Trait}, f"{name}'s trait"),
        mood=_percent(d.get("mood"), f"{name}'s mood"),
        needs={n: _percent(needs.get(n), f"{name}'s {n}") for n in NEEDS},
    )
    surface = _choice(d.get("surface"), {s: s for s in SURFACES}, f"{name}'s surface")
    return SavedCat(cat, surface, _number(d.get("x"), f"{name}'s column"))


def _table(value: object, what: str) -> dict:
    if not isinstance(value, dict):
        raise BadSave(f"{what} is missing or not a table")
    return value


def _list(value: object, what: str) -> list:
    if not isinstance(value, list):
        raise BadSave(f"{what} is missing or not a list")
    return value


def _flag(value: object, what: str) -> bool:
    if not isinstance(value, bool):
        raise BadSave(f"{what} is missing or not true/false")
    return value


def _number(value: object, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BadSave(f"{what} is missing or not a number")
    return float(value)


def _percent(value: object, what: str) -> float:
    return min(100.0, max(0.0, _number(value, what)))


def _count(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BadSave(f"{what} is missing or not a whole number")
    return value


def _choice[T](value: object, options: dict[str, T], what: str) -> T:
    if not isinstance(value, str) or value not in options:
        raise BadSave(f"{what} is unknown: {value!r}")
    return options[value]


def build_world(saved: Saved, rng: random.Random) -> World:
    """The room as the save left it, at the size it was. The first draw fits it to today's screen, and cats
    on surfaces that moved are snapped back onto them, as on a resize."""
    world = World([c.cat for c in saved.cats], rng, *saved.room)
    for c in saved.cats:
        world.place(c.cat.name, c.surface, c.x)
    world.bowl_full, world.focus_total = saved.bowl_full, saved.focus_total
    world.poops = [Poop(min(max(x, 0.0), world.scape.width - 1), world.scape.floor.y) for x in saved.poops]
    return world


def back_up(path: Path, when: datetime) -> Path:
    """Put a bad save aside as save.json.bak-<when>, never over an earlier one. Returns where it went."""
    stamp = when.strftime("%Y%m%d-%H%M%S")
    target, n = path.with_name(f"{path.name}.bak-{stamp}"), 2
    while target.exists():
        target, n = path.with_name(f"{path.name}.bak-{stamp}-{n}"), n + 1
    path.rename(target)
    return target
