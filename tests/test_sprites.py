import pytest

from pomo.game import playscape
from pomo.render import sprites
from pomo.render.sprites import (
    CAT_SLOTS, CAT_WIDTH, COATS, FACES, FRONT_POSES, POSES, PROPS, SIDE_POSES, SIDE_WIDTH,
    cat, cat_head, flip, mirror, problems,
)

HEAD_ROWS = 10
EXPECTED_SIZE = {"sit": (17, 16), "loaf": (17, 15), "walk0": (20, 13), "walk1": (20, 13), "leap": (20, 13)}


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
    assert {len(cat(p, "ok")[0]) for p in SIDE_POSES} == {SIDE_WIDTH}


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
