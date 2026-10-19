"""Pixel art as text grids: one character per pixel, '.' is transparent (spec §7).

Cat palette slots:
  o outline   f fur    d stripe   c patch (same as fur except on calico)
  w white     p pink   e eye      k pupil  r angry eye
Front poses (sit, loaf) are one head plus one body; side poses (walk0, walk1,
leap) share one side-view torso with different legs; the roll poses (roll0,
roll1) lie on their backs, paws up, with the face turned to you. A coat is only
a palette, a mood only swaps ear and eye pixels, and facing left is a mirror
image, so poses × moods × coats × directions never multiply into more drawing.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from pomo.render.theme import RGB, hex_rgb

Grid = tuple[str, ...]

CAT_WIDTH = 17  # front poses
SIDE_WIDTH = 20  # side poses
CAT_SLOTS = frozenset("ofdcwpekr")
FACES = ("ok", "blink", "sleep", "meh", "mad")
FRONT_POSES = ("sit", "loaf")
SIDE_POSES = ("walk0", "walk1", "leap")
ROLL_POSES = ("roll0", "roll1")  # on its back in the catnip: two frames of wriggling
POSES = FRONT_POSES + SIDE_POSES + ROLL_POSES


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


# Side view, facing right: tail on the left, head on the right. Row 4 holds the eye.
_SIDE_TORSO = (
    "..............o...o.",
    ".oo..........opo.opo",
    "ofo..........offfffo",
    "ofo.........offffffo",
    ".ofo........offfekfo",
    "..oooooooooofffffffp",
    "..offdffdffdffffwwo.",
    "..offffffffffffffoo.",
    "..offffffffffffffo..",
    "...offoooooooffo....",
)
_SIDE_LEGS = {
    "walk0": ("...offo.....offo....", "...offo.....offo....", "...oooo.....oooo...."),
    "walk1": ("..offo.......offo...", ".offo.........offo..", ".oooo.........oooo.."),
    "leap": (".offo.........offo..", "oooo............oooo", "...................."),
}
_SIDE_EYE_ROW = 4
_SIDE_EYES = {  # face: what the eye (e) and pupil (k) pixels become
    "ok": ("e", "k"), "blink": ("o", "o"), "sleep": ("o", "o"), "meh": ("o", "k"), "mad": ("r", "k"),
}


def _side(pose: str, face: str) -> Grid:
    eye, pupil = _SIDE_EYES[face]
    rows = list(_SIDE_TORSO + _SIDE_LEGS[pose])
    rows[_SIDE_EYE_ROW] = rows[_SIDE_EYE_ROW].replace("e", eye).replace("k", pupil)
    if face == "mad":
        rows[0] = "." * SIDE_WIDTH  # ears pinned back
    return tuple(rows)


# On its back, facing right: tail on the floor at the left, two hind paws in the
# air (toe beans up), and the head turned to look at you. Between the frames the
# paws pedal and the tail flicks; the head (from column 10) stays put.
_ROLLS = {
    "roll0": (
        ".......pp...........",
        "..pp..owwo..........",
        ".owwo.offo.o......o.",
        ".offo.offoopo....opo",
        "...ooooooooppooooppo",
        "o.owwwwwwwofffddfffo",
        "ofowwwwwwwofekffkefo",
        "ofooffccffofffppfffo",
        ".offffdccdfoffwwffo.",
        "..oooooooooooooooo..",
    ),
    "roll1": (
        "..pp................",
        ".owwo..pp...........",
        ".offo.owwo.o......o.",
        ".offo.offoopo....opo",
        "...ooooooooppooooppo",
        "..owwwwwwwofffddfffo",
        ".owwwwwwwwofekffkefo",
        "ooofffccffofffppfffo",
        "offoffdccdfoffwwffo.",
        ".ooooooooooooooooo..",
    ),
}
_ROLL_HEAD_X = 10
_ROLL_EAR_ROWS = (2, 3)
_ROLL_EYE_ROW = 6


def _roll(pose: str, face: str) -> Grid:
    eye, pupil = _SIDE_EYES[face]  # the same eyes as the side poses, here a pair of them
    rows = list(_ROLLS[pose])
    rows[_ROLL_EYE_ROW] = rows[_ROLL_EYE_ROW].replace("e", eye).replace("k", pupil)
    if face == "mad":  # ears flattened, like the front poses
        for i in _ROLL_EAR_ROWS:
            rows[i] = rows[i][:_ROLL_HEAD_X].ljust(SIDE_WIDTH, ".")
    return tuple(rows)


def cat(pose: str, face: str, facing: int = 1) -> Grid:
    """A cat whose bottom row is where its feet are. facing=-1 mirrors it to face left."""
    if pose in _BODIES:
        grid = cat_head(face) + _BODIES[pose]
    elif pose in _ROLLS:
        grid = _roll(pose, face)
    else:
        grid = _side(pose, face)
    return flip(grid) if facing < 0 else grid


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
BOWL_KNOCKED: Grid = (".obo....", "obbbo.k.", ".obbok.k")  # on its side, rim to the right, kibble spilled out
BOWL_PALETTE = {"k": hex_rgb("#b8631e"), "o": hex_rgb("#1f3b66"), "b": hex_rgb("#3d6fb3")}

POOP: Grid = ("...o...", "..obo..", ".obhbo.", "obbbbbo")
POOP_PALETTE = {"o": hex_rgb("#2e1d12"), "b": hex_rgb("#6b4226"), "h": hex_rgb("#9c6b43")}

# The yarn ball rolls: its two frames swap the light and dark strands.
YARN: tuple[Grid, Grid] = (
    (".ooo.", "orrlo", "olrro", "orlro", ".ooo."),
    (".ooo.", "olrro", "orlro", "orrlo", ".ooo."),
)
YARN_PALETTE = {"o": hex_rgb("#6b2440"), "r": hex_rgb("#f7768e"), "l": hex_rgb("#ffc8d4")}

TEASER: Grid = (".f.", "fFf", "fFf", ".f.")  # the feather on the end of the string
TEASER_PALETTE = {"f": hex_rgb("#9d7cd8"), "F": hex_rgb("#e0cffc")}

# --- tools: what the pointer carries over the room (spec §5.2) --------------

HAND: tuple[Grid, Grid] = (  # open, and patting a cat
    (".ooooo...", "osdsdso..", "osdsdso..", "osdsdsooo", "osssssoso", "ossssssso", ".osssssso", "..oooooo."),
    (".........", ".ooooo...", "osdsdsooo", "osdsdsoso", "ossssssso", "ossssssso", ".osssssso", "..oooooo."),
)
HAND_PALETTE = {"o": hex_rgb("#5a3a28"), "s": hex_rgb("#f2c9a0"), "d": hex_rgb("#d9a67c")}

KIBBLE: Grid = (".kkkk..", "okkkkko", "obbbbbo", ".obbbo.", "..ooo..")  # a scoop of kibble
KIBBLE_PALETTE = {"k": hex_rgb("#b8631e"), "b": hex_rgb("#9aa5ce"), "o": hex_rgb("#3b4261")}

SCOOPER: Grid = ("......h", ".....h.", "....h..", "bbbbh..", "bgbgb..", "bgbgb..", ".bbb...")
SCOOPER_PALETTE = {"h": hex_rgb("#7aa2f7"), "b": hex_rgb("#7dcfff"), "g": hex_rgb("#1a1b26")}

# Each tool's sprite and the pixel of it that sits on the pointer. The string has
# none: the string itself hangs from the pointer. The hand's second frame is for patting.
CURSORS: dict[str, tuple[Grid, Mapping[str, RGB], tuple[int, int]]] = {
    "feed": (KIBBLE, KIBBLE_PALETTE, (3, 1)),
    "ball": (YARN[0], YARN_PALETTE, (2, 2)),
    "pet": (HAND[0], HAND_PALETTE, (4, 4)),
    "scoop": (SCOOPER, SCOOPER_PALETTE, (2, 5)),
}

# --- the shop: treats, toys and furniture (home stretch spec §4) -------------

TUNA: Grid = (".oooooo.", "osSSSSso", "obwwbwbo", "owwwwbbo", "obwwbwbo", ".oooooo.")  # a fish on the label
TUNA_PALETTE = {"o": hex_rgb("#24304f"), "S": hex_rgb("#dfe4f0"), "s": hex_rgb("#9aa5ce"),
                "b": hex_rgb("#3d6fb3"), "w": hex_rgb("#ffb38a")}

CATNIP: Grid = (".....pp..", "..ooopoo.", ".oFFffkfo", "toFfffffp", ".toooooo.")  # a felt mouse, facing right
CATNIP_PALETTE = {"o": hex_rgb("#3b4261"), "F": hex_rgb("#c0caf5"), "f": hex_rgb("#9aa5ce"),
                  "p": hex_rgb("#f09aa6"), "k": hex_rgb("#111111"), "t": hex_rgb("#e0899a")}

# The dot is drawn on whatever the pointer is over; the pen, with the same red in its button and lens, is
# the pointer itself.
LASER_DOT: Grid = (".g.", "gRg", ".g.")
LASER_PEN: Grid = (".oogoo.", "ohhhhhR", ".ooooo.")
LASER_PALETTE = {"g": hex_rgb("#e0303a"), "R": hex_rgb("#ffd0c8"), "o": hex_rgb("#414868"),
                 "h": hex_rgb("#c0caf5")}

# Furniture a cat goes into is two layers with their bottom rows level: the back is drawn behind the cat
# and the front over it. A cat loafing in the box shows its face over the front; drawn with nothing between
# them, the two make the whole empty box.
BOX_BACK: Grid = (
    "...ooooooooooooooo...",
    "oo.oTTTTTTTTTTTTTo.oo",
    "oToossssssssssssso.so",
    "oTTooooooooooooooooso",
    ".oToiiiiiiiiiiiiiosso",
    "..oIIIIIIIIIIIIIIIoo.",
    "..oIIIIIIIIIIIIIIIo..",
    "..oIIIIIIIIIIIIIIIo..",
    "..oIIIIIIIIIIIIIIIo..",
    "..oIIIIIIIIIIIIIIIo..",
    "..oIIIIIIIIIIIIIIIo..",
    "..ooooooooooooooooo..",
)
BOX_FRONT: Grid = (
    "..ooooooooooooooooo..",
    "..oTTTTTTTaaaTTTTTo..",
    "..otttttttaaattttso..",
    "..otttttttaaattttso..",
    "..ottttttttttttttso..",
    "..otttttttttttttsso..",
    "..ooooooooooooooooo..",
)
BOX_PALETTE = {"o": hex_rgb("#3a2618"), "t": hex_rgb("#c48a50"), "T": hex_rgb("#dcab6e"),
               "s": hex_rgb("#a06c3a"), "i": hex_rgb("#6e4a2a"), "I": hex_rgb("#4a301b"),
               "a": hex_rgb("#e6cc96")}

PERCH: Grid = (  # its top row is the surface, like the cat tree's platforms
    ".hhhhhhhhhhhhhhhhhh.",
    "hccccccccccccccccccs",
    ".ssssssssssssssssss.",
    "wwwwwwwwwwwwwwwwwwww",
    "dddddddddddddddddddd",
    "..ddd..........ddd..",
    "..d..............d..",
)
PERCH_PALETTE = {"h": hex_rgb("#7cc7c4"), "c": hex_rgb("#4fa3a5"), "s": hex_rgb("#357a7c"),
                 "w": hex_rgb("#7a5236"), "d": hex_rgb("#5c3f2a")}

# A striped canvas sling. The ropes go up from its two top corners. The back is the far side, seen from
# inside; the front's top edge sags in the middle, so a cat lying in it shows its chest.
HAMMOCK_BACK: Grid = (
    "oo..............oo",
    "oCddddddddddddddCo",
    "oCiiddiiddiiddiiCo",
    "oCiiddiiddiiddiiCo",
    "oCSSCCSSCCSSCCSSCo",
    ".oSSCCSSCCSSCCSSo.",
)
HAMMOCK_FRONT: Grid = (
    "oo..............oo",
    "oCoo..........ooCo",
    "oCSSoo......ooSSCo",
    "oCSSCCooooooCCSSCo",
    "oCSSCCSSCCSSCCSSCo",
    ".oooooooooooooooo.",
)
HAMMOCK_PALETTE = {"o": hex_rgb("#33202a"), "C": hex_rgb("#eadfc8"), "S": hex_rgb("#d0505a"),
                   "d": hex_rgb("#a89880"), "i": hex_rgb("#7a3540")}

# The tuna and the toys are carried over the room like the other tools.
CURSORS.update({
    "tuna": (TUNA, TUNA_PALETTE, (4, 3)),
    "catnip": (CATNIP, CATNIP_PALETTE, (4, 2)),
    "laser": (LASER_PEN, LASER_PALETTE, (6, 1)),  # the lens
})

PROPS: dict[str, tuple[Grid, Mapping[str, RGB]]] = {
    "door": (DOOR, DOOR_PALETTE),
    "bowl_full": (BOWL_FULL, BOWL_PALETTE),
    "bowl_empty": (BOWL_EMPTY, BOWL_PALETTE),
    "bowl_knocked": (BOWL_KNOCKED, BOWL_PALETTE),
    "poop": (POOP, POOP_PALETTE),
    "yarn0": (YARN[0], YARN_PALETTE),
    "yarn1": (YARN[1], YARN_PALETTE),
    "teaser": (TEASER, TEASER_PALETTE),
    "hand0": (HAND[0], HAND_PALETTE),
    "hand1": (HAND[1], HAND_PALETTE),
    "kibble": (KIBBLE, KIBBLE_PALETTE),
    "scooper": (SCOOPER, SCOOPER_PALETTE),
    "tuna": (TUNA, TUNA_PALETTE),
    "catnip": (CATNIP, CATNIP_PALETTE),
    "laser_dot": (LASER_DOT, LASER_PALETTE),
    "laser_pen": (LASER_PEN, LASER_PALETTE),
    "box_back": (BOX_BACK, BOX_PALETTE),
    "box_front": (BOX_FRONT, BOX_PALETTE),
    "perch": (PERCH, PERCH_PALETTE),
    "hammock_back": (HAMMOCK_BACK, HAMMOCK_PALETTE),
    "hammock_front": (HAMMOCK_FRONT, HAMMOCK_PALETTE),
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
