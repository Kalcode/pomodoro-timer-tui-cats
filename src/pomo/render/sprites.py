"""Pixel art as text grids: one character per pixel, '.' is transparent (spec §7).

Cat palette slots:
  o outline   f fur    d stripe   c patch (same as fur except on calico)
  w white     p pink   e eye      k pupil  r angry eye
Every cat is one head plus one body. A coat is only a palette, and a mood only
swaps the head's ear, brow and eye rows, so poses × moods × coats never multiply
into more drawing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pomo.render.theme import RGB, hex_rgb

Grid = tuple[str, ...]

CAT_WIDTH = 17
CAT_SLOTS = frozenset("ofdcwpekr")
FACES = ("ok", "blink", "sleep", "meh", "mad")
POSES = ("sit", "loaf")


def mirror(left_half: Sequence[str]) -> Grid:
    """A symmetric grid from its left half."""
    return tuple(row + row[::-1] for row in left_half)


def flip(grid: Sequence[str]) -> Grid:
    """Face the other way."""
    return tuple(row[::-1] for row in grid)


def pad(grid: Sequence[str], width: int) -> Grid:
    return tuple(row.ljust(width, ".") for row in grid)


# --- cats -----------------------------------------------------------------
# Heads are drawn as their left half (7 px) and mirrored to 14 px.

_EARS = {
    "up": ("..o....", ".opo...", ".oppooo"),
    "flat": (".......", ".......", "opppooo"),  # airplane ears
}
_FOREHEAD = ".offfdf"
_BROW = {"calm": "offfffd", "angry": "ofofffd"}
_EYES = {
    "open": ("ofekeff", "ofekeff"),
    "shut": ("offffff", "ofoooff"),
    "half": ("offffff", "ofekeff"),
    "angry": ("offooff", "ofrkrff"),
}
_MUZZLE = ("offfffp", ".offfww", "..offww")

_FACE_PARTS = {  # face: (ears, brow, eyes)
    "ok": ("up", "calm", "open"),
    "blink": ("up", "calm", "shut"),
    "sleep": ("up", "calm", "shut"),
    "meh": ("up", "calm", "half"),
    "mad": ("flat", "angry", "angry"),
}

_BODIES = {
    "sit": (
        ".occfwwwwfffo....",
        ".offfwwwwfffo.oo.",
        "offffwwwwfccfoffo",
        "offffwwwwfcffoffo",
        "offwwffffwwfffffo",
        ".ooooooooooooooo.",
    ),
    "loaf": (
        ".offfwwwwfffo....",
        "offffwwwwfccfoo..",
        "occffffffffcfffo.",
        "ofddddddddddddfo.",
        ".oooooooooooooo..",
    ),
}


def cat_head(face: str) -> Grid:
    ears, brow, eyes = _FACE_PARTS[face]
    half = (*_EARS[ears], _FOREHEAD, _BROW[brow], *_EYES[eyes], *_MUZZLE)
    return pad(mirror(half), CAT_WIDTH)


def cat(pose: str, face: str) -> Grid:
    """A front-facing cat, 17 px wide. Its bottom row is where its feet are."""
    return cat_head(face) + _BODIES[pose]


# --- coats ----------------------------------------------------------------

_SHARED = {"p": hex_rgb("#f09aa6"), "k": hex_rgb("#111111"), "r": hex_rgb("#ff4a3d")}


def _coat(o: str, f: str, d: str, w: str, e: str, c: str | None = None) -> dict[str, RGB]:
    return {**_SHARED, "o": hex_rgb(o), "f": hex_rgb(f), "d": hex_rgb(d),
            "c": hex_rgb(c or f), "w": hex_rgb(w), "e": hex_rgb(e)}


COATS: dict[str, dict[str, RGB]] = {
    "tabby": _coat("#3b2416", "#e8923b", "#b8631e", "#f6eee3", "#8fd16a"),
    "grey": _coat("#1f2330", "#8a93a6", "#6b7385", "#e9ecf2", "#8fd16a"),
    "tuxedo": _coat("#5d5d70", "#2a2a33", "#1e1e25", "#ececf0", "#e8d44d"),
    "siamese": _coat("#5a4636", "#efe0c8", "#8a6a55", "#fffaf2", "#6fb7ff"),
    "black": _coat("#5d5d70", "#1c1c22", "#141418", "#2a2a33", "#e8d44d"),
    "calico": _coat("#3a2a22", "#f4ede2", "#e0913a", "#fbf8f2", "#8fd16a", c="#2b2626"),
}


# --- props ----------------------------------------------------------------

DOOR: Grid = (
    "ooooooo", "obbbbbo", "obbbbbo", "obooobo", "obfffbo", "obfffbo", "obfffbo",
    "obfffbo", "obfffbo", "obooobo", "obbbbbo", "obbbbbo", "obbbbbo", "obbbbbo",
)
DOOR_PALETTE = {"o": hex_rgb("#2e2016"), "b": hex_rgb("#5c3f2a"), "f": hex_rgb("#3d2a1c")}

BOWL_FULL: Grid = (".kkkkkk.", "obbbbbbo", ".obbbbo.")
BOWL_EMPTY: Grid = (".o....o.", "obbbbbbo", ".obbbbo.")
BOWL_PALETTE = {"k": hex_rgb("#b8631e"), "o": hex_rgb("#1f3b66"), "b": hex_rgb("#3d6fb3")}

PROPS: dict[str, tuple[Grid, Mapping[str, RGB]]] = {
    "door": (DOOR, DOOR_PALETTE),
    "bowl_full": (BOWL_FULL, BOWL_PALETTE),
    "bowl_empty": (BOWL_EMPTY, BOWL_PALETTE),
}


def problems(grid: Sequence[str], slots: frozenset[str] | set[str]) -> list[str]:
    """Why a grid is malformed: ragged rows, or characters that aren't '.' or a known slot."""
    found = []
    if len({len(row) for row in grid}) > 1:
        found.append(f"ragged rows: {sorted({len(row) for row in grid})}")
    unknown = set("".join(grid)) - set(slots) - {"."}
    if unknown:
        found.append(f"unknown slots: {sorted(unknown)}")
    return found
