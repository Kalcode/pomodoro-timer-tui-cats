import pytest

from pomo.render import sprites
from pomo.render.sprites import CAT_SLOTS, CAT_WIDTH, COATS, FACES, POSES, PROPS, cat, cat_head, flip, mirror, problems

HEAD_ROWS = 10
EXPECTED_HEIGHT = {"sit": 16, "loaf": 15}


@pytest.mark.parametrize("pose", POSES)
@pytest.mark.parametrize("face", FACES)
def test_every_cat_is_a_clean_17_wide_grid(pose, face):
    grid = cat(pose, face)
    assert problems(grid, CAT_SLOTS) == []
    assert {len(row) for row in grid} == {CAT_WIDTH}
    assert len(grid) == EXPECTED_HEIGHT[pose]


@pytest.mark.parametrize("face", FACES)
def test_heads_are_symmetric(face):
    for row in cat_head(face):
        core = row[:14]
        assert core == core[::-1]


@pytest.mark.parametrize("pose", POSES)
def test_faces_only_change_the_head(pose):
    bodies = {cat(pose, face)[HEAD_ROWS:] for face in FACES}
    assert len(bodies) == 1


def test_the_faces_look_different():
    heads = {face: cat_head(face) for face in FACES}
    assert heads["ok"] != heads["blink"] != heads["meh"]
    assert heads["mad"][0] == "." * CAT_WIDTH  # ears flattened out of the top row
    assert "r" in "".join(heads["mad"])  # red eyes
    assert "e" not in "".join(heads["blink"])  # eyes shut


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
