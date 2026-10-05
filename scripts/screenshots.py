"""Render the README's screenshots and GIF from the real app, into docs/images/.

    uv run --with pillow python scripts/screenshots.py

Each scene drives PomoApp headlessly with a fake clock and a seeded random number
generator, so the pictures come out the same every time. The screen is read back as
terminal cells and painted here with Pillow: half-block characters become exact squares
of colour, so the pixel art has no seams. Text uses Menlo and emoji Apple Color Emoji
(macOS fonts); gifsicle, if installed, shrinks the GIF. Nothing here touches your own
config or save: the app is never given a save path.
"""

from __future__ import annotations

import asyncio
import io
import random
import shutil
import subprocess
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from rich.cells import cell_len
from rich.console import Console
from rich.segment import Segment
from textual.app import App, ComposeResult

import pomo.ui.app as app_module
from pomo.clock import FakeClock
from pomo.config import Config
from pomo.game.behavior import Doing
from pomo.notify import NullNotifier
from pomo.render import sprites, theme
from pomo.render.canvas import Canvas
from pomo.ui.app import PomoApp
from pomo.ui.stage import Stage

OUT = Path(__file__).resolve().parent.parent / "docs" / "images"
SIZE = (100, 30)
GIF_FPS = 8
GIF_SECONDS = 5
TEXT_FONT = "/System/Library/Fonts/Menlo.ttc"  # face 0 regular, face 1 bold
EMOJI_FONT = "/System/Library/Fonts/Apple Color Emoji.ttc"
EMOJI_SIZE = 160  # Apple Color Emoji only comes in a few bitmap sizes
CHROME = {"bar": (42, 43, 48), "title": (190, 190, 196), "lights": [(255, 95, 87), (254, 188, 46), (40, 200, 64)]}

app_module.TICK_S = 3600.0  # the scenes tick the app themselves, so the real 8 fps interval stays out of it


@dataclass(frozen=True)
class Cell:
    char: str
    fg: tuple[int, int, int]
    bg: tuple[int, int, int]
    bold: bool
    width: int  # 1, or 2 for an emoji (which covers the next cell too)


Screen = list[list[Cell]]


def make_app(seed: int, idle: bool = False) -> tuple[PomoApp, FakeClock]:
    clock = FakeClock()
    return PomoApp(Config(), clock, NullNotifier(), rng=random.Random(seed), idle=idle), clock


def tick(app: PomoApp, clock: FakeClock, seconds: float, step: float = 0.125) -> None:
    for _ in range(round(seconds / step)):
        clock.advance(step)
        app.tick()


def screen(app: App) -> Screen:
    """The whole screen as cells: the same render Textual's own screenshots start from."""
    width, height = app.size
    console = Console(width=width, height=height, file=io.StringIO(), force_terminal=True,
                      color_system="truecolor", record=True, legacy_windows=False, safe_box=False)
    console.print(app.screen._compositor.render_update(full=True, screen_stack=app._background_screens))
    rows: Screen = [[]]
    for segment in Segment.filter_control(console._record_buffer):
        style = segment.style
        fg = style.color.get_truecolor() if style and style.color else (255, 255, 255)
        bg = style.bgcolor.get_truecolor() if style and style.bgcolor else (0, 0, 0)
        if style and style.reverse:
            fg, bg = bg, fg
        for char in segment.text:
            if char == "\n":
                continue
            if sum(c.width for c in rows[-1]) >= width:
                rows.append([])
            rows[-1].append(Cell(char, tuple(fg), tuple(bg), bool(style and style.bold), max(1, cell_len(char))))
    return rows[:height]


# --- scenes: each returns screens, or None when this seed didn't give a good picture ------


async def focus(seed: int) -> list[Screen] | None:
    """Six minutes into a focus: nap time, and Mango is asleep at the top of the cat tree."""
    app, clock = make_app(seed)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        tick(app, clock, 6 * 60 + 18, step=0.5)  # the clock reads 18:42
        body = app.world.bodies["Mango"]
        if not (body.step and body.step.doing is Doing.NAP and body.surface == "tree_top"):
            return None
        await pilot.pause()
        return [screen(app)]


async def play(seed: int) -> list[Screen] | None:
    """A break: a yarn ball dropped near the window, and Mango tears after it."""
    app, clock = make_app(seed)
    async with app.run_test(size=SIZE) as pilot:
        await pilot.press("space")
        tick(app, clock, 25 * 60, step=1.0)  # through the focus: the break waits for space
        await pilot.press("space")
        app.show_message("")
        mango = app.world.cats[0]
        mango.mood, mango.needs["play"] = 85.0, 90.0  # content, and keen to play
        await pilot.press("2")
        await pilot.click(Stage, offset=(30 + 58, 5))
        await pilot.press("escape")  # put the tool down, so only the real ball shows
        frames, leaps, xs, moving, previous = [], 0, [], 0, None
        for _ in range(GIF_FPS * GIF_SECONDS):
            tick(app, clock, 1 / GIF_FPS)
            await pilot.pause()
            frames.append(screen(app))
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


async def pet(seed: int) -> list[Screen] | None:
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
        return [screen(app)]


async def angry(seed: int) -> list[Screen] | None:
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
        app.frame = 0  # the waiting break's clock pulses: catch it lit
        app.main.stage.redraw()
        await pilot.pause()
        return [screen(app)]


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


async def cast(seed: int) -> list[Screen] | None:
    app = Cast()
    async with app.run_test(size=(122, 13)) as pilot:
        await pilot.pause()
        return [screen(app)]


# --- painting ---------------------------------------------------------------------------


@cache
def text_font(size: int, bold: bool) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(TEXT_FONT, size, index=1 if bold else 0)


@cache
def emoji(char: str, width: int, height: int) -> Image.Image:
    """An emoji drawn big in colour, cropped, and scaled down to fit a two-cell box."""
    font = ImageFont.truetype(EMOJI_FONT, EMOJI_SIZE)
    big = Image.new("RGBA", (EMOJI_SIZE * 2, EMOJI_SIZE * 2))
    ImageDraw.Draw(big).text((0, 0), char, font=font, embedded_color=True)
    big = big.crop(big.getbbox())
    scale = min(width / big.width, height * 0.8 / big.height)
    return big.resize((max(1, round(big.width * scale)), max(1, round(big.height * scale))), Image.LANCZOS)


def mix(a: tuple, b: tuple, t: float) -> tuple[int, int, int]:
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def paint(rows: Screen, cw: int) -> Image.Image:
    """The cells as an image: cw pixels per column and twice that per row, so a half-block is a square."""
    ch = cw * 2
    image = Image.new("RGB", (sum(c.width for c in rows[0]) * cw, len(rows) * ch))
    draw = ImageDraw.Draw(image)
    for y, row in enumerate(rows):
        x, top = 0, y * ch
        for cell in row:
            box = (x, top, x + cell.width * cw - 1, top + ch - 1)
            if cell.char == "▀":
                draw.rectangle(box, fill=cell.bg)
                draw.rectangle((x, top, box[2], top + cw - 1), fill=cell.fg)
            elif cell.char == "▄":
                draw.rectangle(box, fill=cell.bg)
                draw.rectangle((x, top + cw, box[2], box[3]), fill=cell.fg)
            elif cell.char == "█":
                draw.rectangle(box, fill=cell.fg)
            elif cell.char == "░":
                draw.rectangle(box, fill=mix(cell.bg, cell.fg, 0.3))
            else:
                draw.rectangle(box, fill=cell.bg)
                if cell.width == 2:
                    glyph = emoji(cell.char, 2 * cw, ch)
                    image.paste(glyph, (x + (2 * cw - glyph.width) // 2, top + (ch - glyph.height) // 2), glyph)
                elif cell.char != " ":
                    font = text_font(round(cw * 1.62), cell.bold)
                    draw.text((x + cw / 2, top + ch / 2), cell.char, font=font, fill=cell.fg, anchor="mm")
            x += cell.width * cw
    return image


def window(content: Image.Image, cw: int, title: str = "pomo", rounded: bool = True) -> Image.Image:
    """A macOS-style window around the terminal: a title bar with traffic lights, rounded corners."""
    pad, bar, radius = cw, round(cw * 2.6), (cw if rounded else 0)
    w, h = content.width + 2 * pad, content.height + 2 * pad + bar
    frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(frame)
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=theme.ROOM_BG)
    draw.rounded_rectangle((0, 0, w - 1, bar + radius), radius=radius, fill=CHROME["bar"])
    draw.rectangle((0, bar, w - 1, bar + radius), fill=theme.ROOM_BG)
    for i, color in enumerate(CHROME["lights"]):
        r, cx = cw * 0.5, cw * (1.6 + i * 1.5)
        draw.ellipse((cx - r, bar / 2 - r, cx + r, bar / 2 + r), fill=color)
    draw.text((w / 2, bar / 2), title, font=text_font(round(cw * 1.62), True), fill=CHROME["title"], anchor="mm")
    frame.paste(content, (pad, bar + pad))
    return frame


def save_png(rows: Screen, path: Path, cw: int = 24) -> None:
    window(paint(rows, cw), cw).save(path, optimize=True)


def save_gif(frames: list[Screen], path: Path, cw: int = 9) -> None:
    images = [window(paint(rows, cw), cw, rounded=False).convert("RGB") for rows in frames]
    sheet = Image.new("RGB", (images[0].width, images[0].height * len(images)))
    for i, image in enumerate(images):
        sheet.paste(image, (0, i * image.height))
    palette = sheet.quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    quantized = [image.quantize(palette=palette, dither=Image.Dither.NONE) for image in images]
    quantized[0].save(path, save_all=True, append_images=quantized[1:], duration=round(1000 / GIF_FPS), loop=0)
    if shutil.which("gifsicle"):
        subprocess.run(["gifsicle", "-O3", "--batch", str(path)], check=True)


async def first_good(scene: Callable[[int], Awaitable[list[Screen] | None]]) -> list[Screen]:
    for seed in range(100):
        frames = await scene(seed)
        if frames:
            print(f"  {scene.__name__}: seed {seed}")
            return frames
    raise SystemExit(f"no seed gave a good {scene.__name__} picture")


async def main() -> None:
    for font in (TEXT_FONT, EMOJI_FONT):
        if not Path(font).exists():
            raise SystemExit(f"needs the macOS font {font}")
    OUT.mkdir(parents=True, exist_ok=True)
    for scene in (focus, pet, angry, cast):
        save_png((await first_good(scene))[0], OUT / f"{scene.__name__}.png")
    save_gif(await first_good(play), OUT / "play.gif")
    for image in sorted(OUT.iterdir()):
        print(f"  {image.name}: {image.stat().st_size // 1024} KB")


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
