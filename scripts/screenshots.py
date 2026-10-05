"""Render the README's screenshots and GIF from the real app, into docs/images/.

    uv run python scripts/screenshots.py

Each scene drives PomoApp headlessly with a fake clock and a seeded random number
generator, so the pictures come out the same every time. Textual exports each frame
as an SVG, headless Google Chrome turns the SVGs into PNGs, and ffmpeg and gifsicle
make the GIF. Needs Google Chrome, ffmpeg and gifsicle (brew install ffmpeg gifsicle).
Nothing here touches your own config or save: no save path is given to the app.
"""

from __future__ import annotations

import asyncio
import random
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from textual.app import App, ComposeResult

import pomo.ui.app as app_module
from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.clock import FakeClock
from pomo.config import Config
from pomo.game.behavior import Doing
from pomo.notify import NullNotifier
from pomo.ui.app import PomoApp
from pomo.ui.stage import Stage

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
SIZE = (100, 30)
GIF_FPS = 8
GIF_SECONDS = 5

app_module.TICK_S = 3600.0  # the scenes tick the app themselves, so the real 8 fps interval stays out of it


def make_app(seed: int, idle: bool = False) -> tuple[PomoApp, FakeClock]:
    clock = FakeClock()
    return PomoApp(Config(), clock, NullNotifier(), rng=random.Random(seed), idle=idle), clock


def tick(app: PomoApp, clock: FakeClock, seconds: float, step: float = 0.125) -> None:
    for _ in range(round(seconds / step)):
        clock.advance(step)
        app.tick()


def svg(app) -> str:
    return app.export_screenshot(title="pomo")


# --- scenes: each returns SVGs, or None when this seed didn't give a good picture ------


async def focus(seed: int) -> list[str] | None:
    """Six minutes into a focus: nap time, and Mango is asleep at the top of the cat tree."""
    app, clock = make_app(seed)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        tick(app, clock, 6 * 60 + 18, step=0.5)  # the clock reads 18:42
        body = app.world.bodies["Mango"]
        if not (body.step and body.step.doing is Doing.NAP and body.surface == "tree_top"):
            return None
        await pilot.pause()
        return [svg(app)]


async def play(seed: int) -> list[str] | None:
    """A break: a yarn ball dropped near the window, and Mango tears after it."""
    app, clock = make_app(seed)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        tick(app, clock, 25 * 60, step=1.0)  # through the focus: on a break now
        mango = app.world.cats[0]
        mango.mood, mango.needs["play"] = 85.0, 90.0  # content, and keen to play
        await pilot.press("2")
        await pilot.click(Stage, offset=(30 + 58, 5))
        await pilot.press("escape")  # put the tool down, so only the real ball shows
        frames, leaps, xs, moving, previous = [], 0, [], 0, None
        for _ in range(GIF_FPS * GIF_SECONDS):
            tick(app, clock, 1 / GIF_FPS)
            await pilot.pause()
            frames.append(svg(app))
            cats = app.world.view().cats
            if not cats:
                return None  # out through the litter door: not much of a picture
            mango = cats[0]
            leaps += mango.pose == "leap" and previous != "leap"
            moving += mango.pose != "sit"
            previous = mango.pose
            xs.append(mango.x)
        lively = leaps >= 3 and moving >= len(frames) * 0.6 and max(xs) - min(xs) > 35
        return frames if lively else None


async def pet(seed: int) -> list[str] | None:
    """Idle mode, the hand stroking Mango: eyes shut, purring, a heart floating up."""
    app, clock = make_app(seed, idle=True)
    async with app.run_test(size=SIZE) as pilot:
        app.world.cats[0].needs["affection"] = 100
        await pilot.press("4")
        for x in list(range(60, 75)) + list(range(74, 63, -1)):
            await pilot.hover(Stage, offset=(x, 26))  # along his back, so his face shows
        tick(app, clock, 0.25)
        await pilot.pause()
        if not app.world.view().effects:
            return None
        return [svg(app)]


async def angry(seed: int) -> list[str] | None:
    """Rules have teeth: a skipped focus, confirmed, and an already-pissy Mango is furious."""
    app, clock = make_app(seed)
    async with app.run_test(size=SIZE) as pilot:
        mango = app.world.cats[0]
        mango.mood, mango.needs["hunger"] = 30.0, 85.0
        app.world.bowl_full = False
        await pilot.press("space")
        tick(app, clock, 12 * 60 + 30, step=0.5)
        await pilot.press("s", "y")  # pomo asks first; yes, skip it
        tick(app, clock, 1.5)
        cats = app.world.view().cats
        if not cats or cats[0].face != "mad" or app.world.bodies["Mango"].surface != "floor":
            return None
        await pilot.pause()
        return [svg(app)]


CAST = (  # coat, pose, face, label
    ("tabby", "sit", "ok", "tabby"),
    ("grey", "loaf", "sleep", "grey, asleep"),
    ("tuxedo", "sit", "meh", "tuxedo, grumpy"),
    ("siamese", "sit", "blink", "siamese"),
    ("black", "sit", "mad", "black, furious"),
    ("calico", "loaf", "ok", "calico, loafing"),
)


class Cast(App[None]):
    """Six coats in a row, each in a different mood."""

    def compose(self) -> ComposeResult:
        yield Stage(self.draw)

    def draw(self, canvas: Canvas) -> None:
        canvas.fill(0, 0, canvas.width, canvas.height, theme.ROOM_BG)
        for i, (coat, pose, face, label) in enumerate(CAST):
            x, grid = 3 + i * 20, sprites.cat(pose, face)
            canvas.sprite(x, 4 + 16 - len(grid), grid, sprites.COATS[coat])
            canvas.text(x, 11, label, theme.DIM)


async def cast(seed: int) -> list[str] | None:
    app = Cast()
    async with app.run_test(size=(122, 13)) as pilot:
        await pilot.pause()
        return [svg(app)]


# --- rendering ------------------------------------------------------------------------


def svg_size(text: str) -> tuple[int, int]:
    _, _, w, h = (float(n) for n in re.search(r'viewBox="([^"]+)"', text).group(1).split())
    return round(w), round(h)


def render(svgs: list[str], png: Path, scale: int, columns: int = 1) -> tuple[int, int]:
    """All the SVGs on one page in a grid, one Chrome screenshot of it. Returns one frame's size in pixels."""
    w, h = svg_size(svgs[0])
    rows = -(-len(svgs) // columns)
    with tempfile.TemporaryDirectory() as tmp:
        for i, text in enumerate(svgs):
            Path(tmp, f"{i}.svg").write_text(text)
        cells = "".join(f'<img src="{i}.svg" width="{w}" height="{h}">' for i in range(len(svgs)))
        page = Path(tmp, "page.html")
        page.write_text("<html><body style='margin:0;display:grid;"
                        f"grid-template-columns:repeat({columns},{w}px);line-height:0'>{cells}</body></html>")
        png.unlink(missing_ok=True)
        chrome = subprocess.Popen(
            [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}",
             "--default-background-color=00000000", f"--window-size={w * columns},{h * rows}",
             f"--user-data-dir={tmp}/chrome", f"--screenshot={png}", f"file://{page}"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        try:
            wait_for_file(png)
        finally:  # headless Chrome doesn't always exit once the screenshot is written
            chrome.terminate()
            chrome.wait(timeout=10)
    return w * scale, h * scale


def wait_for_file(path: Path, timeout: float = 90.0) -> None:
    """Until the file exists and has stopped growing."""
    last, deadline = -1, time.monotonic() + timeout
    while time.monotonic() < deadline:
        size = path.stat().st_size if path.exists() else -1
        if size > 0 and size == last:
            return
        last = size
        time.sleep(0.5)
    raise SystemExit(f"Chrome didn't write {path.name}")


def make_gif(svgs: list[str], gif: Path) -> None:
    columns = 8
    with tempfile.TemporaryDirectory() as tmp:
        sheet = Path(tmp, "sheet.png")
        w, h = render(svgs, sheet, scale=1, columns=columns)
        frames = Path(tmp, "frames")
        frames.mkdir()
        for i in range(len(svgs)):
            x, y = (i % columns) * w, (i // columns) * h
            subprocess.run(["magick", str(sheet), "-crop", f"{w}x{h}+{x}+{y}", "+repage",
                            "-background", "#0d1117", "-flatten", "-resize", "900x",
                            str(frames / f"{i:03d}.png")], check=True)
        palette = Path(tmp, "palette.png")
        source = ["-framerate", str(GIF_FPS), "-i", str(frames / "%03d.png")]
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *source, "-vf", "palettegen=max_colors=128", str(palette)],
                       check=True)
        raw = Path(tmp, "raw.gif")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *source, "-i", str(palette),
                        "-lavfi", "paletteuse=dither=none", "-loop", "0", str(raw)], check=True)
        subprocess.run(["gifsicle", "-O3", str(raw), "-o", str(gif)], check=True)


async def first_good(scene: Callable[[int], Awaitable[list[str] | None]]) -> list[str]:
    for seed in range(100):
        frames = await scene(seed)
        if frames:
            print(f"  {scene.__name__}: seed {seed}")
            return frames
    raise SystemExit(f"no seed gave a good {scene.__name__} picture")


async def main() -> None:
    for tool in ("magick", "ffmpeg", "gifsicle"):
        if not shutil.which(tool):
            raise SystemExit(f"needs {tool}: brew install ffmpeg gifsicle imagemagick")
    if not Path(CHROME).exists():
        raise SystemExit(f"needs Google Chrome at {CHROME}")
    OUT.mkdir(parents=True, exist_ok=True)
    for scene in (focus, pet, angry, cast):
        render(await first_good(scene), OUT / f"{scene.__name__}.png", scale=2)
    make_gif(await first_good(play), OUT / "play.gif")
    for image in sorted(OUT.iterdir()):
        print(f"  {image.name}: {image.stat().st_size // 1024} KB")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
