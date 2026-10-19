"""Where things are in the cat room (spec §6). Pure geometry, in room pixel coordinates.

x is a column from the room's left edge, y a pixel row from the room's top (two per
text row). Everything is anchored to the floor, so a taller room just adds wall above.
The cat tree, window and shelf stay together at the left (the window sits between the
tree and the shelf, where no perched cat can cover it); the bowl and door follow the
right edge, so a wider room is more floor to roam.

Furniture from the shop (home stretch §4) has fixed spots, chosen so it fits at the
smallest size: a box on the floor under the window, a perch under the window level
with the tree top, and a hammock slung under the wall shelf.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass

CAT_WIDTH = 17
CAT_HEIGHT = 16  # the tallest pose
MAX_JUMP_UP = 20  # spec §6: surfaces a cat can hop between
MAX_JUMP_ACROSS = 24
MIN_WIDTH = 70  # 100 columns minus the 30-column timer panel
MIN_HEIGHT = 54  # the tree top still has room for a sitting cat
FURNITURE = ("box", "perch", "hammock")
BOX_W, BOX_H = 21, 10  # the cardboard box, which cats nap in on the floor
HAMMOCK_DROP = 9  # the hammock hangs this far above the floor: a cat in it clears the shelf's brackets


@dataclass(frozen=True)
class Surface:
    """Something a cat can stand on. A standing sprite's bottom row is y - 1."""

    name: str
    x0: int
    x1: int  # exclusive
    y: int


@dataclass(frozen=True)
class Box:
    x: int
    y: int
    w: int
    h: int


# Where a furious cat sits on the timer panel's big clock (home stretch §5.3). The panel is the 30 columns left of
# the room, so the perch is at negative columns, and it never moves: the panel doesn't grow with the screen. A cat
# loafing on it covers the digits and the progress bar but not the phase label or the state line above them. It
# isn't one of the room's surfaces, so wandering and climbing never go there: only a cat set on the clock does.
CLOCK_PERCH = Surface("clock", -28, -3, 21)


@dataclass(frozen=True)
class Playscape:
    width: int
    height: int
    floor: Surface
    tree_mid: Surface
    tree_top: Surface
    shelf: Surface
    post: Box
    window: Box
    door: Box
    bowl: Box
    box: Box | None = None
    perch: Surface | None = None
    hammock: Surface | None = None

    @property
    def surfaces(self) -> tuple[Surface, ...]:
        extra = tuple(s for s in (self.perch, self.hammock) if s is not None)
        return (self.floor, self.tree_mid, self.tree_top, self.shelf, *extra)

    def surface(self, name: str) -> Surface:
        """A surface by name, the clock perch included."""
        for s in (*self.surfaces, CLOCK_PERCH):
            if s.name == name:
                return s
        raise KeyError(name)


def layout(width: int, height: int, furniture: frozenset[str] | set[str] = frozenset()) -> Playscape:
    """The room at this size, with whichever furniture has been bought."""
    floor_y = height - 1
    tree_top = Surface("tree_top", 3, 21, floor_y - 37)
    tree_mid = Surface("tree_mid", 8, 28, floor_y - 18)
    shelf = Surface("shelf", tree_mid.x1 + 18, tree_mid.x1 + 36, floor_y - 29)
    window = Box(tree_top.x1 + 7, floor_y - 51, 14, 12)
    box = perch = hammock = None
    if "box" in furniture:
        box = Box(tree_mid.x1 - 4, floor_y - BOX_H, BOX_W, BOX_H)
    if "perch" in furniture:
        perch = Surface("perch", window.x - 3, window.x + window.w + 3, tree_top.y)
    if "hammock" in furniture:
        hammock = Surface("hammock", shelf.x0, shelf.x1, floor_y - HAMMOCK_DROP)
    return Playscape(
        width=width,
        height=height,
        floor=Surface("floor", 0, width, floor_y),
        tree_mid=tree_mid,
        tree_top=tree_top,
        shelf=shelf,
        post=Box(11, tree_top.y + 2, 3, floor_y - tree_top.y - 2),
        window=window,
        door=Box(width - 7, floor_y - 14, 7, 14),
        bowl=Box(width - 20, floor_y - 3, 8, 3),
        box=box,
        perch=perch,
        hammock=hammock,
    )


def can_jump(a: Surface, b: Surface) -> bool:
    gap = max(0, max(a.x0, b.x0) - min(a.x1, b.x1))
    return abs(a.y - b.y) <= MAX_JUMP_UP and gap <= MAX_JUMP_ACROSS


def reachable(scape: Playscape) -> set[str]:
    """Names of the surfaces a cat on the floor can get to."""
    seen = {scape.floor.name}
    queue = deque([scape.floor])
    while queue:
        here = queue.popleft()
        for there in scape.surfaces:
            if there.name not in seen and can_jump(here, there):
                seen.add(there.name)
                queue.append(there)
    return seen
