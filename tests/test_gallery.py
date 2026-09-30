from canvas_reading import screen_text
from pomo.gallery import GalleryApp
from pomo.render import sprites

SIZE = (100, 46)


def shows_coat(app, coat) -> bool:
    canvas = app.stage.canvas
    fur = sprites.COATS[coat]["f"]
    return any(canvas.pixel_at(x, py) == fur for x in range(canvas.width) for py in range(canvas.height * 2))


async def test_the_gallery_opens_on_the_first_coat_with_every_pose_and_face():
    app = GalleryApp()
    async with app.run_test(size=SIZE):
        text = screen_text(app.stage.canvas)
        assert "tabby  (1/6)" in text
        for pose in sprites.FRONT_POSES:
            for face in sprites.FACES:
                assert f"{pose} {face}" in text
        for label in ["walk0 ok", "walk1 ok", "leap ok", "walk0 mad"]:
            assert label in text
        for prop in sprites.PROPS:
            assert prop in text
        assert shows_coat(app, "tabby")


async def test_arrows_flip_through_the_coats_and_wrap():
    app = GalleryApp()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("right")
        assert app.coat == "grey" and shows_coat(app, "grey")
        await pilot.press("left", "left")
        assert app.coat == "calico" and shows_coat(app, "calico")


async def test_every_coat_draws():
    app = GalleryApp()
    async with app.run_test(size=SIZE) as pilot:
        for _ in sprites.COATS:
            await pilot.press("right")
            assert shows_coat(app, app.coat)


async def test_q_quits():
    app = GalleryApp()
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("q")
        await pilot.pause()
        assert not app.is_running
