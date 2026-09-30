"""Every colour on screen, as (r, g, b). A Tokyo Night-style palette (spec §7)."""

from __future__ import annotations

RGB = tuple[int, int, int]


def hex_rgb(value: str) -> RGB:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


# screen
ROOM_BG = hex_rgb("#15161e")
PANEL_BG = hex_rgb("#1f2335")
TEXT = hex_rgb("#c0caf5")
DIM = hex_rgb("#565f89")
BAR_EMPTY = hex_rgb("#2f3549")

# phases
FOCUS = hex_rgb("#ff6b5b")
BREAK = hex_rgb("#9ece6a")
IDLE_CLOCK = hex_rgb("#737aa2")  # a phase that isn't running

# effects
SLEEP_Z = hex_rgb("#7aa2f7")

# room
FLOOR = hex_rgb("#24283b")
SISAL = hex_rgb("#c9a66b")
SISAL_DARK = hex_rgb("#a8844d")
PLATFORM = hex_rgb("#6b5b8a")
PLATFORM_EDGE = hex_rgb("#4d4166")
SHELF = hex_rgb("#7a5236")
SHELF_BRACKET = hex_rgb("#5c3f2a")
WINDOW_FRAME = hex_rgb("#2a2f45")
WINDOW_GLASS = hex_rgb("#0d1026")
WINDOW_SILL = hex_rgb("#3a3f5a")
STAR = hex_rgb("#e0e0ff")

# cat roster
HEART = hex_rgb("#f7768e")
HEART_EMPTY = hex_rgb("#3b4261")
STAGE_COLORS = {
    "content": hex_rgb("#9ece6a"),
    "grumpy": hex_rgb("#e0af68"),
    "pissy": hex_rgb("#ff9e64"),
    "furious": hex_rgb("#ff4a3d"),
}
