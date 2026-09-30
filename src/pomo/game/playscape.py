"""Where things are in the cat room (spec §6). Pure geometry, in room pixel coordinates.

x is a column from the room's left edge, y a pixel row from the room's top (two per
text row). Everything is anchored to the floor, so a taller room just adds wall above.
The cat tree, window and shelf stay together at the left (the window sits between the
tree and the shelf, where no perched cat can cover it); the bowl and door follow the
right edge, so a wider room is more floor to roam.
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

    @property
    def surfaces(self) -> tuple[Surface, ...]:
        return (self.floor, self.tree_mid, self.tree_top, self.shelf)

    def surface(self, name: str) -> Surface:
        for s in self.surfaces:
            if s.name == name:
                return s
        raise KeyError(name)


def layout(width: int, height: int) -> Playscape:
    floor_y = height - 1
    tree_top = Surface("tree_top", 3, 21, floor_y - 37)
    tree_mid = Surface("tree_mid", 8, 28, floor_y - 18)
    shelf = Surface("shelf", tree_mid.x1 + 18, tree_mid.x1 + 36, floor_y - 29)
    return Playscape(
        width=width,
        height=height,
        floor=Surface("floor", 0, width, floor_y),
        tree_mid=tree_mid,
        tree_top=tree_top,
        shelf=shelf,
        post=Box(11, tree_top.y + 2, 3, floor_y - tree_top.y - 2),
        window=Box(tree_top.x1 + 7, floor_y - 51, 14, 12),
        door=Box(width - 7, floor_y - 14, 7, 14),
        bowl=Box(width - 20, floor_y - 3, 8, 3),
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
