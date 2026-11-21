#!/usr/bin/env python3
"""Scripted hero stills for Dark Inc. crates that have no visual output.

Pillow only, in the ``night_city`` subset (``palette.json``). Every pixel is one
of those colours; text is PIL's built-in bitmap font scaled by NEAREST, so it
stays on the pixel grid.

    python3 art/diagrams.py devshot --out PATH        # 960x270
    python3 art/diagrams.py light_grid --out PATH     # 960x540

Each still is labelled ``schematic`` in the caption the crate's README carries:
it shows what the crate does, not a screenshot of it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ART_DIR = Path(__file__).resolve().parent
PALETTE_FILE = ART_DIR / "palette.json"
SUBSET = "night_city"

DEVPANEL_W = 960
DEVPANEL_H = 270
GRID_W = 960
GRID_H = 540
TEXT_SCALE = 3
GRID_COLS = 32
GRID_ROWS = 18
CELL_PX = 25
GRID_LEFT = 40
GRID_TOP = 72
WALL_COL = 24
WALL_ROW = 6
WALL_H = 5
WALL_W = 6

# Lighting ramps up from the darkest floor tone; a cell in shadow drops to black,
# so "the wall blocks this lamp" reads differently from "this corner is far away".
LIGHT_RAMP = ("000055", "0000AA", "5500AA", "AA00AA", "FF55FF", "FF55FF")
SHADOW_COLOUR = "000000"
LAMPS = ((7.5, 5.5, 1.0), (25.5, 14.5, 0.85))
LIGHT_RADIUS_CELLS = 3.6
LIT_BELOW = 0.10
FLOOR_OUTLINE = "000055"


# A 5x7 bitmap font: one entry per character, seven rows of five cells. Uppercase
# only, because a schematic's labels are short and small caps read cleanly at 1x.
GLYPHS: dict[str, tuple[str, ...]] = {
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".####"),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("#####", "...#.", "..#..", "...#.", "....#", "#...#", ".###."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": ("..##.", ".#...", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "...#.", ".##.."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", "..#.."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "$": ("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
}
GLYPH_W = 5
GLYPH_H = 7
GLYPH_GAP = 1


def load_subset() -> dict[str, tuple[int, int, int]]:
    data = json.loads(PALETTE_FILE.read_text())
    colours = {}
    for entry in data["subsets"][SUBSET]:
        digits = str(entry).lstrip("#").upper()
        colours[digits] = tuple(int(digits[i : i + 2], 16) for i in (0, 2, 4))
    return colours


class Canvas:
    def __init__(self, width: int, height: int, colours: dict[str, tuple[int, int, int]]) -> None:
        self.image = Image.new("RGB", (width, height), colours["000000"])
        self.draw = ImageDraw.Draw(self.image)
        self._colours = colours

    def colour(self, name: str) -> tuple[int, int, int]:
        if name not in self._colours:
            raise SystemExit(f"{name} is not in the {SUBSET} subset")
        return self._colours[name]

    def rect(self, box: tuple[int, int, int, int], name: str, width: int = 1) -> None:
        self.draw.rectangle(box, outline=self.colour(name), width=width)

    def fill(self, box: tuple[int, int, int, int], name: str) -> None:
        self.draw.rectangle(box, fill=self.colour(name))

    def text(self, xy: tuple[int, int], message: str, name: str, scale: int = TEXT_SCALE) -> None:
        """Draw GLYPHS at ``scale`` with NEAREST; unknown characters are refused."""
        upper = message.upper()
        width = (len(upper) * (GLYPH_W + GLYPH_GAP) - GLYPH_GAP) * scale
        mask = Image.new("L", (width, GLYPH_H * scale), 0)
        pen = ImageDraw.Draw(mask)
        for index, character in enumerate(upper):
            try:
                rows = GLYPHS[character]
            except KeyError:
                raise SystemExit(f"no glyph for {character!r} in {message!r}") from None
            origin_x = index * (GLYPH_W + GLYPH_GAP) * scale
            for row, pattern in enumerate(rows):
                for column, cell in enumerate(pattern):
                    if cell != "#":
                        continue
                    x = origin_x + column * scale
                    y = row * scale
                    pen.rectangle((x, y, x + scale - 1, y + scale - 1), fill=255)
        self.image.paste(self.colour(name), (xy[0], xy[1]), mask)

    def save(self, out: Path) -> None:
        out.parent.mkdir(parents=True, exist_ok=True)
        self.image.save(out)


def text_width(message: str, scale: int) -> int:
    return (len(message) * (GLYPH_W + GLYPH_GAP) - GLYPH_GAP) * scale


def arrow(canvas: Canvas, x0: int, y0: int, x1: int, name: str) -> None:
    canvas.draw.line((x0, y0, x1, y0), fill=canvas.colour(name), width=3)
    canvas.draw.line((x1, y0, x1 - 8, y0 - 6), fill=canvas.colour(name), width=3)
    canvas.draw.line((x1, y0, x1 - 8, y0 + 6), fill=canvas.colour(name), width=3)


def devshot(out: Path) -> None:
    """Terminal -> game window -> the written screenshot.png."""
    canvas = Canvas(DEVPANEL_W, DEVPANEL_H, load_subset())
    mid = DEVPANEL_H // 2

    # Panel 1: the terminal that asks for a screenshot.
    canvas.fill((24, 38, 320, 190), "000055")
    canvas.rect((24, 38, 320, 190), "00AAAA", width=2)
    canvas.fill((30, 40, 314, 62), "00AAAA")
    canvas.text((42, 74), "touch", "55FFFF", scale=2)
    canvas.text((42, 98), "screenshot.request", "55FFFF", scale=2)
    canvas.text((42, 148), "$ _", "AAAAAA", scale=2)

    # Panel 2: the game window.
    canvas.fill((360, 40, 700, 180), "000055")
    canvas.rect((360, 40, 700, 180), "AA00AA", width=2)
    canvas.fill((366, 42, 694, 68), "550055")
    canvas.text((380, 48), "game", "55FFFF", scale=2)
    canvas.fill((366, 68, 694, 178), "000055")
    canvas.fill((498, 82, 536, 120), "FF55FF")
    canvas.fill((366, 140, 694, 178), "005555")
    canvas.draw.polygon([(360, 178), (428, 112), (504, 178)], fill=canvas.colour("0000AA"))
    canvas.draw.polygon([(480, 178), (580, 128), (700, 178)], fill=canvas.colour("5500AA"))
    canvas.fill((604, 152, 626, 178), "00AAAA")

    # Panel 3: the page written to disk, its corner folded, a frame on it.
    canvas.draw.polygon(
        [(776, 56), (864, 56), (884, 76), (884, 152), (776, 152)],
        fill=canvas.colour("AAAAAA"),
    )
    canvas.draw.polygon(
        [(864, 56), (864, 76), (884, 76)], fill=canvas.colour("555555")
    )
    canvas.fill((784, 64, 876, 144), "000055")
    canvas.fill((792, 76, 868, 132), "0000AA")
    canvas.fill((806, 88, 854, 120), "FF55FF")
    canvas.fill((792, 120, 868, 132), "005555")
    caption = "screenshot.png"
    canvas.text(((760 + 880 - text_width(caption, 2)) // 2, 164), caption, "FFFFFF", scale=2)

    arrow(canvas, 324, mid + 4, 352, "55FFFF")
    arrow(canvas, 706, mid + 4, 752, "55FFFF")
    canvas.text((24, 2), "bevy_devshot", "FF55FF")
    canvas.text((24, 220), "touch a request, get a png", "AAAAAA", scale=2)
    canvas.save(out)


def light_shade(factor: float) -> tuple[int, int, int]:
    """The subset colour nearest ``factor`` brightness, from LIGHT_RAMP."""
    level = max(0.0, min(1.0, factor))
    index = min(len(LIGHT_RAMP) - 1, int(level * (len(LIGHT_RAMP) - 1) + 0.5))
    digits = LIGHT_RAMP[index]
    return tuple(int(digits[i : i + 2], 16) for i in (0, 2, 4))


def in_wall(x: float, y: float) -> bool:
    return WALL_COL <= x < WALL_COL + WALL_W and WALL_ROW <= y < WALL_ROW + WALL_H


def shadowed_by_wall(lamp: tuple[float, float], x: float, y: float) -> bool:
    """Is the wall strictly between the lamp and (x, y)?"""
    lamp_x, lamp_y = lamp
    steps = 240
    for step in range(1, steps):
        t = step / steps
        px, py = lamp_x + (x - lamp_x) * t, lamp_y + (y - lamp_y) * t
        if in_wall(px, py):
            return True
    return False


def cell_box(col: int, row: int) -> tuple[int, int, int, int]:
    return (
        GRID_LEFT + col * CELL_PX,
        GRID_TOP + row * CELL_PX,
        GRID_LEFT + (col + 1) * CELL_PX,
        GRID_TOP + (row + 1) * CELL_PX,
    )


def light_grid(out: Path) -> None:
    """A 32x18 cell grid lit by two lamps, one wall casting a hard shadow."""
    colours = load_subset()
    canvas = Canvas(GRID_W, GRID_H, colours)
    canvas.text((GRID_LEFT, 6), "bevy_light_grid", "FF55FF", scale=2)
    canvas.text((GRID_LEFT, 36), "two lamps, one wall, one hard shadow", "AAAAAA")

    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            box = cell_box(col, row)
            if in_wall(col + 0.5, row + 0.5):
                # Stone: light grey blocks split by dark mortar, so the wall reads
                # as an obstruction rather than as another floor colour.
                canvas.draw.rectangle(box, fill=colours["AAAAAA"], outline=colours["555555"])
                continue
            light = 0.0
            shadowed = False
            for lamp_x, lamp_y, power in LAMPS:
                if shadowed_by_wall((lamp_x, lamp_y), col + 0.5, row + 0.5):
                    shadowed = True
                    continue
                dx, dy = col + 0.5 - lamp_x, row + 0.5 - lamp_y
                light += power / (1.0 + (dx * dx + dy * dy) / (LIGHT_RADIUS_CELLS ** 2))
            if shadowed:
                shade = colours[SHADOW_COLOUR]
            elif light >= LIT_BELOW:
                shade = light_shade(light)
            else:
                shade = colours["000055"]
            canvas.draw.rectangle(box, fill=shade, outline=colours[FLOOR_OUTLINE])

    # A border, so the floor's footprint still reads where the light does not reach.
    canvas.draw.rectangle(
        (
            GRID_LEFT - 2,
            GRID_TOP - 2,
            GRID_LEFT + GRID_COLS * CELL_PX + 1,
            GRID_TOP + GRID_ROWS * CELL_PX + 1,
        ),
        outline=colours["00AAAA"],
        width=2,
    )
    for lamp_x, lamp_y, _power in LAMPS:
        cx, cy = GRID_LEFT + int(lamp_x * CELL_PX), GRID_TOP + int(lamp_y * CELL_PX)
        canvas.draw.ellipse((cx - 6, cy - 6, cx + 6, cy + 6), fill=colours["55FFFF"])
    canvas.save(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("devshot", "light_grid"):
        command = sub.add_parser(name)
        command.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out)
    if args.command == "devshot":
        devshot(out)
    else:
        light_grid(out)
    with Image.open(out) as image:
        used = image.convert("RGB").getcolors(maxcolors=1 << 24) or []
        print(f"{out}: {image.width}x{image.height}, {len(used)} colours")
        if len(used) > 16:
            print("more than 16 colours", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
