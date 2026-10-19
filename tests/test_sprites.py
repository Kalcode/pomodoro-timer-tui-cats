import pytest

from pomo.game import playscape
from pomo.game.tools import Tool
from pomo.render import sprites
from pomo.render.sprites import (
    BOX_BACK, BOX_FRONT, CAT_SLOTS, CAT_WIDTH, COATS, CURSORS, FACES, FRONT_POSES, HAMMOCK_BACK, HAMMOCK_FRONT, HAND,
    POSES, PROPS, ROLL_POSES, SIDE_POSES, SIDE_WIDTH, YARN, cat, cat_head, flip, mirror, problems,
)

HEAD_ROWS = 10
EXPECTED_SIZE = {"sit": (17, 16), "loaf": (17, 15), "walk0": (20, 13), "walk1": (20, 13), "leap": (20, 13),
                 "roll0": (20, 10), "roll1": (20, 10)}
ROLL_HEAD_X = 10  # the roll poses' head starts at this column; everything left of it is body, paws and tail
ROLL_EAR_ROWS, ROLL_EYE_ROW = (2, 3), 6


@pytest.mark.parametrize("pose", POSES)
@pytest.mark.parametrize("face", FACES)
def test_every_cat_is_a_clean_grid_of_the_right_size(pose, face):
    grid = cat(pose, face)
    assert problems(grid, CAT_SLOTS) == []
    width, height = EXPECTED_SIZE[pose]
    assert {len(row) for row in grid} == {width}
    assert len(grid) == height


def test_the_widths_match_the_constants():
    assert {len(cat(p, "ok")[0]) for p in FRONT_POSES} == {CAT_WIDTH}
    assert {len(cat(p, "ok")[0]) for p in SIDE_POSES + ROLL_POSES} == {SIDE_WIDTH}


def test_playscape_sizes_match_the_real_sprites():
    # playscape can't import render (layering), so this keeps its copies honest
    assert playscape.CAT_WIDTH == CAT_WIDTH
    assert playscape.CAT_HEIGHT == max(len(cat(p, "ok")) for p in POSES)


@pytest.mark.parametrize("face", FACES)
def test_front_heads_are_symmetric(face):
    for row in cat_head(face):
        core = row[:14]
        assert core == core[::-1]


@pytest.mark.parametrize("pose", FRONT_POSES)
def test_front_faces_only_change_the_head(pose):
    bodies = {cat(pose, face)[HEAD_ROWS:] for face in FACES}
    assert len(bodies) == 1


@pytest.mark.parametrize("pose", SIDE_POSES)
def test_side_faces_only_change_the_ears_and_eye(pose):
    grids = [cat(pose, face) for face in FACES]
    for row in range(len(grids[0])):
        if row not in (0, 4):
            assert len({g[row] for g in grids}) == 1, row


def test_the_faces_look_different():
    heads = {face: cat_head(face) for face in FACES}
    assert heads["ok"] != heads["blink"] != heads["meh"]
    assert heads["mad"][0] == "." * CAT_WIDTH  # ears flattened out of the top row
    assert "r" in "".join(heads["mad"])  # red eyes
    assert "e" not in "".join(heads["blink"])  # eyes shut
    assert "r" in "".join(cat("walk0", "mad")) and "e" not in "".join(cat("walk0", "sleep"))


def test_the_walk_frames_move_the_legs():
    assert cat("walk0", "ok")[-3:] != cat("walk1", "ok")[-3:]
    assert cat("walk0", "ok")[:-3] == cat("walk1", "ok")[:-3]


def test_facing_left_mirrors_the_cat():
    for pose in POSES:
        assert cat(pose, "ok", facing=-1) == flip(cat(pose, "ok"))
    right = cat("walk0", "ok")
    assert right[4].index("e") > SIDE_WIDTH // 2  # the eye is at the front, on the right


@pytest.mark.parametrize("coat", COATS)
def test_every_coat_colours_every_slot(coat):
    assert set(COATS[coat]) == CAT_SLOTS


def test_patches_only_show_on_calico():
    for name, coat in COATS.items():
        assert (coat["c"] != coat["f"]) == (name == "calico"), name


@pytest.mark.parametrize("name", PROPS)
def test_props_are_clean_grids(name):
    grid, palette = PROPS[name]
    assert problems(grid, set(palette)) == []


def test_mirror_and_flip():
    assert mirror(["ab"]) == ("abba",)
    assert flip(("abc", "d.e")) == ("cba", "e.d")
    assert flip(flip(cat("sit", "ok"))) == cat("sit", "ok")


def test_problems_spots_ragged_rows_and_unknown_slots():
    assert problems(("ab", "a"), {"a", "b"}) == ["ragged rows: [1, 2]"]
    assert problems(("aZ",), {"a"}) == ["unknown slots: ['Z']"]


def test_unknown_pose_or_face_is_a_key_error():
    with pytest.raises(KeyError):
        sprites.cat("backflip", "ok")
    with pytest.raises(KeyError):
        sprites.cat("sit", "smug")
    with pytest.raises(KeyError):
        sprites.cat("walk0", "smug")


def test_every_tool_but_the_string_has_a_cursor():
    assert {tool.value for tool in Tool} - {"string"} <= set(CURSORS)


def test_the_tuna_and_the_toys_have_cursors_too():
    assert {"tuna", "catnip", "laser"} <= set(CURSORS)


@pytest.mark.parametrize("tool", CURSORS)
def test_each_cursor_is_clean_and_its_hotspot_is_on_a_drawn_pixel(tool):
    grid, palette, (hx, hy) = CURSORS[tool]
    assert problems(grid, set(palette)) == []
    assert grid[hy][hx] in palette


@pytest.mark.parametrize("frames", [YARN, HAND], ids=["yarn", "hand"])
def test_two_frame_props_differ_but_keep_their_size(frames):
    first, second = frames
    assert first != second
    assert (len(first), len(first[0])) == (len(second), len(second[0]))


# --- rolling in the catnip ------------------------------------------------------


@pytest.mark.parametrize("pose", ROLL_POSES)
def test_a_rolling_cat_looks_at_you_from_the_right_end(pose):
    grid = cat(pose, "ok")
    assert "e" in grid[ROLL_EYE_ROW] and "k" in grid[ROLL_EYE_ROW]
    assert "".join(grid).count("e") == "".join(grid[ROLL_EYE_ROW]).count("e")  # no stray eye pixels
    assert grid[ROLL_EYE_ROW].index("e") >= ROLL_HEAD_X
    assert cat(pose, "ok", facing=-1)[ROLL_EYE_ROW].rindex("e") < SIDE_WIDTH - ROLL_HEAD_X


@pytest.mark.parametrize("pose", ROLL_POSES)
def test_roll_faces_only_change_the_ears_and_eyes(pose):
    grids = [cat(pose, face) for face in FACES]
    for row in range(len(grids[0])):
        if row not in (*ROLL_EAR_ROWS, ROLL_EYE_ROW):
            assert len({g[row] for g in grids}) == 1, row
    assert len({tuple(row[:ROLL_HEAD_X] for row in g) for g in grids}) == 1  # the body never changes


def test_rolling_cats_close_their_eyes_and_get_mad_like_the_others():
    assert "e" not in "".join(cat("roll0", "blink")) and "e" not in "".join(cat("roll1", "sleep"))
    mad = cat("roll0", "mad")
    assert "r" in mad[ROLL_EYE_ROW]
    assert all(set(mad[row][ROLL_HEAD_X:]) == {"."} for row in ROLL_EAR_ROWS)  # ears flattened


def test_the_roll_frames_wriggle_the_paws_and_tail_but_not_the_head():
    first, second = (cat(pose, "ok") for pose in ROLL_POSES)
    assert first != second
    assert [row[ROLL_HEAD_X + 1:] for row in first] == [row[ROLL_HEAD_X + 1:] for row in second]


@pytest.mark.parametrize("coat", COATS)
def test_every_coat_colours_every_pixel_of_every_pose(coat):
    used = {ch for pose in POSES for face in FACES for row in cat(pose, face) for ch in row} - {"."}
    assert used <= set(COATS[coat])


# --- furniture a cat goes into: its back layer, the cat, then its front layer ---


def stack(back, front, inside=(), left=0):
    """Which layer shows at each pixel when back, a cat at column left, and front are drawn with their
    bottom rows level: 'b', 'c', 'f' or '.'."""
    height = max(len(back), len(inside), len(front))
    shown = [["."] * len(back[0]) for _ in range(height)]
    for grid, x0, mark in ((back, 0, "b"), (inside, left, "c"), (front, 0, "f")):
        for dy, row in enumerate(grid):
            for dx, ch in enumerate(row):
                if ch != ".":
                    shown[height - len(grid) + dy][x0 + dx] = mark
    return ["".join(row) for row in shown]


@pytest.mark.parametrize("back, front", [(BOX_BACK, BOX_FRONT), (HAMMOCK_BACK, HAMMOCK_FRONT)], ids=["box", "hammock"])
def test_the_back_and_front_layers_line_up(back, front):
    assert len(back[0]) == len(front[0])
    assert len(back) >= len(front)


def test_a_cat_in_the_box_peeks_over_the_front():
    loaf = cat("loaf", "ok")
    shown = stack(BOX_BACK, BOX_FRONT, loaf, left=2)  # both centred on the same column
    over_the_edge = len(loaf) - len(BOX_FRONT)
    assert all("c" not in row for row in shown[over_the_edge:])  # the front hides the rest of it
    assert "e" in "".join(loaf[:over_the_edge]) and "p" in "".join(loaf[:over_the_edge])  # eyes and nose


def test_the_empty_box_has_no_holes():
    shown = stack(BOX_BACK, BOX_FRONT)
    assert all(row[x] != "." for row in shown for x in range(3, 18))  # everything between its walls


@pytest.mark.parametrize("left", [0, 1])  # 17 pixels of cat centred on 18 of sling round either way
def test_a_cat_lies_in_the_hammock(left):
    shown = stack(HAMMOCK_BACK, HAMMOCK_FRONT, cat("loaf", "sleep"), left)
    sling = shown[-len(HAMMOCK_FRONT):]
    assert all("c" not in row for row in sling[-3:])  # the sling holds its lower body
    middle = len(HAMMOCK_FRONT[0]) // 2
    assert sling[0][0] == "f" and sling[1][middle] == "c"  # its near edge sags in the middle, showing its chest
