import pytest

from pomo.game.playscape import (
    BOX_H, CAT_HEIGHT, CAT_WIDTH, FURNITURE, MIN_HEIGHT, MIN_WIDTH, Surface, can_jump, layout, reachable,
)

SIZES = [(MIN_WIDTH, MIN_HEIGHT), (MIN_WIDTH, 58), (120, 80), (250, 120)]
ALL = frozenset(FURNITURE)


@pytest.mark.parametrize("furniture", [frozenset(), ALL])
@pytest.mark.parametrize("width, height", SIZES)
def test_every_surface_fits_a_cat_inside_the_room(width, height, furniture):
    scape = layout(width, height, furniture)
    for s in scape.surfaces:
        assert 0 <= s.x0 and s.x1 <= width, s
        assert s.x1 - s.x0 >= CAT_WIDTH, s
        assert s.y - CAT_HEIGHT >= 0, s  # headroom for the tallest pose
        assert s.y < height, s


@pytest.mark.parametrize("furniture", [frozenset(), ALL, {"perch"}, {"hammock"}])
@pytest.mark.parametrize("width, height", SIZES)
def test_every_surface_can_be_reached_from_the_floor(width, height, furniture):
    scape = layout(width, height, furniture)
    assert reachable(scape) == {s.name for s in scape.surfaces}


def test_the_floor_is_the_bottom_pixel_row():
    assert layout(80, 60).floor.y == 59


def test_a_taller_room_only_adds_wall_above():
    short, tall = layout(80, 60), layout(80, 100)
    for a, b in zip(short.surfaces, tall.surfaces):
        assert (a.x0, a.x1) == (b.x0, b.x1)
        assert short.floor.y - a.y == tall.floor.y - b.y


def test_a_wider_room_keeps_the_furniture_and_moves_the_bowl_and_door():
    narrow, wide = layout(70, 60), layout(150, 60)
    assert (narrow.tree_top, narrow.shelf, narrow.window) == (wide.tree_top, wide.shelf, wide.window)
    assert wide.door.x + wide.door.w == 150
    assert wide.bowl.x > narrow.bowl.x


@pytest.mark.parametrize("width, height", SIZES)
def test_door_and_bowl_sit_on_the_floor_without_overlapping(width, height):
    scape = layout(width, height)
    for box in (scape.door, scape.bowl):
        assert box.y + box.h == scape.floor.y
    assert scape.bowl.x + scape.bowl.w <= scape.door.x


@pytest.mark.parametrize("width, height", SIZES)
def test_the_window_stays_clear_of_the_tree_top_and_the_shelf(width, height):
    scape = layout(width, height)
    window = scape.window
    assert window.y >= 0
    assert window.x >= scape.tree_top.x1  # right of any cat on the tree top
    assert window.x + window.w <= scape.shelf.x0  # left of any cat on the shelf


def test_surfaces_are_found_by_name():
    scape = layout(80, 60)
    assert scape.surface("shelf") is scape.shelf
    with pytest.raises(KeyError):
        scape.surface("fridge")


def test_jump_limits():
    floor = Surface("a", 0, 10, 50)
    assert can_jump(floor, Surface("b", 0, 10, 30))  # 20 up
    assert not can_jump(floor, Surface("b", 0, 10, 29))  # 21 up
    assert can_jump(floor, Surface("b", 34, 50, 50))  # 24 across
    assert not can_jump(floor, Surface("b", 35, 50, 50))  # 25 across


def test_furniture_is_only_there_once_bought():
    bare, furnished = layout(MIN_WIDTH, MIN_HEIGHT), layout(MIN_WIDTH, MIN_HEIGHT, ALL)
    assert (bare.box, bare.perch, bare.hammock) == (None, None, None)
    assert [s.name for s in furnished.surfaces][-2:] == ["perch", "hammock"]
    assert furnished.surface("perch") is furnished.perch


def test_the_perch_sits_under_the_window_level_with_the_tree_top():
    scape = layout(MIN_WIDTH, MIN_HEIGHT, ALL)
    perch, window = scape.perch, scape.window
    assert perch.x0 < window.x and window.x + window.w < perch.x1
    assert perch.y == scape.tree_top.y > window.y + window.h


def test_a_cat_in_the_hammock_hangs_below_the_shelf_and_above_the_floor():
    scape = layout(MIN_WIDTH, MIN_HEIGHT, ALL)
    hammock, shelf = scape.hammock, scape.shelf
    assert (hammock.x0, hammock.x1) == (shelf.x0, shelf.x1)
    assert hammock.y - (CAT_HEIGHT - 1) > shelf.y + 4  # a loafing cat (15 tall) clears the brackets (y+2..y+4)
    assert hammock.y < scape.floor.y


def test_the_box_stands_on_the_floor_clear_of_the_tree_and_the_bowl():
    for width in (MIN_WIDTH, 200):
        scape = layout(width, MIN_HEIGHT, ALL)
        box = scape.box
        assert box.y + box.h == scape.floor.y and box.h == BOX_H
        assert box.x >= scape.post.x + scape.post.w + 5  # past the tree's base
        assert box.x + box.w <= scape.bowl.x - 4
