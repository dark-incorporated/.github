#!/usr/bin/env python3
"""The fix-loop walkthrough's three figures, drawn over real captures.

Pillow only, in the ``house`` subset (``palette.json``). Every pixel is one of its
sixteen colours: the captures are snapped to it with no dithering and the
annotations are drawn in it with no anti-aliasing. Text is the 5x7 font of
``diagrams.py``, scaled by NEAREST.

    python3 art/fix_loop_figure.py                      # write the three figures into art/
    python3 art/fix_loop_figure.py --figure proof       # write one of them
    python3 art/fix_loop_figure.py --out DIR --check    # render into DIR, then fail on
                                                        # a colour outside the subset, an
                                                        # annotation over the UI, sources
                                                        # that disagree, or a figure that
                                                        # differs from the committed one

The figures (``docs/fix-loop.md`` shows them):

    fix-loop-editor.png   the running editor, five things a report can point at
    fix-loop-flow.png     the loop's stages and the routes between route and proof (schematic)
    fix-loop-proof.png    one iteration's before.png and after.png, the same rectangle

Sources, in ``art/sources/`` (a still with no provenance is a claim nobody can check):

    editor-map.png     ``blueprint_capture_still`` of the editor on the sample game's ``courtyard``
                       map in the Map workspace, 2560x1406 (surface pixels, scale factor 2), taken
                       2026-11-24 on an Apple M5. The binary was built from ``bevy_dark_factory``
                       branch ``feat/live-style`` at 55644d5, not yet merged that day. The crop of
                       it at PROOF_RECT is pixel-identical to ``proof-before.png``, which a build
                       of ``main`` took the day before (--check measures that), so the terminal
                       bar did not change between the two builds.
    proof-before.png   ``before.png`` of the fix-loop iteration
    proof-after.png    ``after.png`` of the same iteration, ``20261123T153257Z-drill-chip-padding``
                       (the report "make the chrome chip padding one step larger", route ``style``,
                       file ``style/editor.yaml``, rule ``.chrome-chip``). Both are the
                       ``blueprint_snip`` of PROOF_RECT, 180x100 surface pixels.

Nothing here is a screenshot of a person's game or machine beyond those three files.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

import diagrams

ART_DIR = Path(__file__).resolve().parent
SOURCES_DIR = ART_DIR / "sources"
SUBSET = "house"
FIGURES = {
    "editor": "fix-loop-editor.png",
    "flow": "fix-loop-flow.png",
    "proof": "fix-loop-proof.png",
}
MAX_COLOURS = 16
MAX_FIGURE_BYTES = 4 * 1024 * 1024
MAX_CAPTURE_COLOURS = 1 << 24

# Drawing rules, from the research behind docs/fix-loop.md:
#   - A picture whose cues guide attention to the relevant part is understood more deeply than one
#     without, so the editor figure puts numbered boxes on a real capture rather than beside a
#     drawing of it. van Gog 2021, "The Signaling (or Cueing) Principle in Multimedia Learning",
#     doi:10.1017/9781108894333.022. The size of the effect was not read, and nothing here quotes one.
#   - Words sit beside the thing they name, not in a legend elsewhere, so each label is in the margin
#     nearest its box and joined to it by a leader line. Mayer 2020, "Spatial Contiguity Principle",
#     Multimedia Learning, doi:10.1017/9781316941355.012.
#   - A diagram with arrows is read as a process and one without as a structure, so arrows appear in
#     the flow figure only, where they are the order of the loop. Heiser and Tversky 2006, "Arrows in
#     Comprehending and Producing Mechanical Diagrams", Cognitive Science, doi:10.1207/s15516709cog0000_70.
# House style with no paper behind it: the ``house`` palette and the 5x7 font at 3x to 5x. The text
# sizes are chosen to stay readable when GitHub scales a figure to its page column, which measured
# 861 px in a 1280 px window and 1012 px in a 1600 px or wider one (a file page, 2026-11-24).

# ---- palette roles -------------------------------------------------------------------------------
BLACK = "000000"
WHITE = "FFFFFF"
LIGHT_GREY = "AAAAAA"
CYAN = "55FFFF"
MAGENTA = "FF55FF"
YELLOW = "FFFF55"
PINK = "FF5555"
TITLE_COLOUR = MAGENTA
DETAIL_COLOUR = LIGHT_GREY
ARROW_COLOUR = WHITE

# ---- text, in pixels of the figure; the 5x7 font is 7 px tall at scale 1 --------------------------
GLYPH_ADVANCE_PX = diagrams.GLYPH_W + diagrams.GLYPH_GAP
TITLE_SCALE = 5
NAME_SCALE = 4
DETAIL_SCALE = 3
BADGE_DIGIT_SCALE = 3
NAME_PITCH_PX = 36
DETAIL_PITCH_PX = 26

# ---- the editor figure ---------------------------------------------------------------------------
CAPTURE_SIZE_PX = (2560, 1406)
CAPTURE_REDUCE = 2
SCREEN_SIZE_PX = (CAPTURE_SIZE_PX[0] // CAPTURE_REDUCE, CAPTURE_SIZE_PX[1] // CAPTURE_REDUCE)
# The rectangle the fix loop cut out in the chip-padding iteration (``blueprint_snip``, surface px):
# the terminal bar's right end, padded 40 px round the chips and clamped to the window.
PROOF_RECT = (2380, 1000, 2560, 1100)
EDITOR_MARGIN_PX = 24
EDITOR_GUTTER_PX = 290
EDITOR_GAP_PX = 16
EDITOR_TOP_PX = 150
EDITOR_BOTTOM_PX = 30
BOX_WIDTH_PX = 3
BOX_GAP_PX = 2
SCREEN_FRAME_PX = 2
SCREEN_FRAME_COLOUR = "555555"
LEADER_WIDTH_PX = 3
LEADER_GAP_PX = 8
BADGE_PX = 30
LABEL_BADGE_PX = 36
LABEL_GAP_PX = 12
# A leader may cross a hairline of the interface (a bar's border is 1 px in the reduced capture) and
# nothing wider: a longer run of drawn pixels under a leader is a control or a word it would strike.
MAX_HAIRLINE_PX = 3


@dataclass(frozen=True)
class Mark:
    """One numbered box on the editor, and the label that names it.

    ``rect`` is the landmark in reduced-capture pixels (x0, y0, x1, y1, the last two exclusive).
    ``inside`` draws the outline inside it, for a landmark with no border of its own. ``badge`` is
    the top-left pixel of the number on the box. ``side`` says which margin carries the label, and
    ``attach`` where its leader meets the box: a y for ``left`` and ``right``, an x for ``top-left``
    and ``top-right``.
    """

    number: int
    colour: str
    rect: tuple[int, int, int, int]
    inside: bool
    badge: tuple[int, int]
    side: str
    attach: int
    name: str
    lines: tuple[str, ...]


MARKS = (
    # The terminal bar's chips: the rectangle the proof figure shows twice.
    Mark(1, CYAN, tuple(v // CAPTURE_REDUCE for v in PROOF_RECT), False, (1185, 555), "right", 525,
         "CHIPS", ("A LOOK: THE", "STYLE SHEET")),
    # The INSPECTOR panel's own border.
    Mark(2, MAGENTA, (44, 167, 319, 490), False, (286, 171), "left", 289,
         "INSPECTOR", ("A PANEL",)),
    # The viewport's frame, between the inspector's rail and the PLACE panel.
    Mark(3, YELLOW, (364, 158, 1067, 501), True, (369, 163), "top-left", 750,
         "VIEWPORT", ("A POINT IN", "THE MAP")),
    # The PLACE panel's own border.
    Mark(4, WHITE, (1075, 167, 1266, 490), False, (1233, 171), "right", 330,
         "LIBRARY", ("A LIST ROW",)),
    # The chrome bar's MAP: words.
    Mark(5, PINK, (827, 38, 938, 61), False, (792, 3), "top-right", 882,
         "CHROME BAR", ("WORDS: RUST", "AND A BUILD")),
)

# ---- the proof figure ----------------------------------------------------------------------------
PROOF_ZOOM = 3
PROOF_MARGIN_PX = 40
PROOF_HEADER_PX = 76
PROOF_FOOTER_PX = 100
PROOF_FRAME_PX = 3

# ---- the flow figure -----------------------------------------------------------------------------
FLOW_MARGIN_PX = 28
FLOW_TITLE_Y_PX = 24
FLOW_PLATE_TOP_PX = 112
FLOW_PLATE_LINE_PX = 3
FLOW_PAD_PX = 16
FLOW_GAP_PX = 58
FLOW_ARROW_PX = 4
FLOW_HEAD_LENGTH_PX = 18
FLOW_HEAD_HALF_WIDTH_PX = 10


def text_width(message: str, scale: int) -> int:
    return diagrams.text_width(message, scale)


def text_height(scale: int) -> int:
    return diagrams.GLYPH_H * scale


# ---- the capture ---------------------------------------------------------------------------------

def squared_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> int:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def snap(image: Image.Image, colours: dict[str, tuple[int, int, int]]) -> Image.Image:
    """Every pixel to the nearest subset colour, ties to the earlier one, no dithering.

    Done by hand rather than with ``Image.quantize`` so the answer depends on no library version:
    the figures are checked against the committed ones byte for byte.
    """
    palette = list(colours.values())
    rgb = image.convert("RGB")
    found = rgb.getcolors(maxcolors=MAX_CAPTURE_COLOURS)
    if found is None:
        raise SystemExit(f"more than {MAX_CAPTURE_COLOURS} colours in a capture")
    nearest = {
        colour: min(palette, key=lambda p: (squared_distance(colour, p), palette.index(p)))
        for _, colour in found
    }
    out = Image.new("RGB", rgb.size)
    out.putdata([nearest[pixel] for pixel in rgb.getdata()])
    return out


def load_capture(name: str) -> Image.Image:
    path = SOURCES_DIR / name
    if not path.is_file():
        raise SystemExit(f"missing source {path}")
    return Image.open(path).convert("RGB")


def screen_from_capture(colours: dict[str, tuple[int, int, int]]) -> Image.Image:
    """The editor, reduced by an exact integer box filter, then snapped to the subset."""
    capture = load_capture("editor-map.png")
    if capture.size != CAPTURE_SIZE_PX:
        raise SystemExit(f"editor-map.png is {capture.size}, expected {CAPTURE_SIZE_PX}")
    return snap(capture.reduce(CAPTURE_REDUCE), colours)


# ---- drawing, in exclusive rectangles ------------------------------------------------------------

def fill_box(canvas: diagrams.Canvas, box: tuple[int, int, int, int], name: str) -> None:
    x0, y0, x1, y1 = box
    if x1 > x0 and y1 > y0:
        canvas.fill((x0, y0, x1 - 1, y1 - 1), name)


def frame_box(canvas: diagrams.Canvas, box: tuple[int, int, int, int], name: str, width: int) -> None:
    """An outline drawn inside ``box``."""
    x0, y0, x1, y1 = box
    canvas.rect((x0, y0, x1 - 1, y1 - 1), name, width=width)


def grow(box: tuple[int, int, int, int], by: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return (x0 - by, y0 - by, x1 + by, y1 + by)


def hline(canvas: diagrams.Canvas, x0: int, x1: int, y: int, width: int, name: str) -> None:
    """A horizontal bar from x0 to x1, centred on y, ends included."""
    low, high = sorted((x0, x1))
    top = y - width // 2
    fill_box(canvas, (low, top, high + 1, top + width), name)


def vline(canvas: diagrams.Canvas, x: int, y0: int, y1: int, width: int, name: str) -> None:
    low, high = sorted((y0, y1))
    left = x - width // 2
    fill_box(canvas, (left, low, left + width, high + 1), name)


def arrow_head(
    canvas: diagrams.Canvas, tip: tuple[int, int], direction: str, name: str,
    length: int = FLOW_HEAD_LENGTH_PX, half_width: int = FLOW_HEAD_HALF_WIDTH_PX,
) -> None:
    x, y = tip
    corners = {
        "right": [(x, y), (x - length, y - half_width), (x - length, y + half_width)],
        "left": [(x, y), (x + length, y - half_width), (x + length, y + half_width)],
        "down": [(x, y), (x - half_width, y - length), (x + half_width, y - length)],
        "up": [(x, y), (x - half_width, y + length), (x + half_width, y + length)],
    }[direction]
    canvas.draw.polygon(corners, fill=canvas.colour(name))


def digit_badge(canvas: diagrams.Canvas, top_left: tuple[int, int], size: int, number: int, name: str,
                scale: int) -> tuple[int, int, int, int]:
    """A filled square carrying a black digit; returns its exclusive rectangle."""
    x, y = top_left
    box = (x, y, x + size, y + size)
    fill_box(canvas, box, name)
    digit = str(number)
    canvas.text(
        (x + (size - text_width(digit, scale)) // 2, y + (size - text_height(scale)) // 2),
        digit, BLACK, scale=scale,
    )
    return box


# ---- the editor figure ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Placed:
    """Something drawn over the screenshot, kept so --check can measure what it covers."""

    mark: int
    kind: str
    box: tuple[int, int, int, int]


def outline_box(mark: Mark) -> tuple[int, int, int, int]:
    """The outer rectangle of the mark's 3 px outline, in screen pixels."""
    if mark.inside:
        return mark.rect
    return grow(mark.rect, BOX_GAP_PX + BOX_WIDTH_PX)


def label_lines_width(mark: Mark) -> int:
    name_row = LABEL_BADGE_PX + LABEL_GAP_PX + text_width(mark.name, NAME_SCALE)
    return max([name_row] + [text_width(line, NAME_SCALE) for line in mark.lines])


def label_height(mark: Mark) -> int:
    return LABEL_BADGE_PX + 6 + NAME_PITCH_PX * len(mark.lines)


def draw_label(canvas: diagrams.Canvas, mark: Mark, left: int, top: int, align_right: bool) -> tuple[int, int, int, int]:
    """The gutter label: the number, the name, then one grey line per detail. Returns its rectangle."""
    width = label_lines_width(mark)
    height = label_height(mark)
    x = left
    badge_x = x + (width - LABEL_BADGE_PX - LABEL_GAP_PX - text_width(mark.name, NAME_SCALE) if align_right else 0)
    digit_badge(canvas, (badge_x, top), LABEL_BADGE_PX, mark.number, mark.colour, NAME_SCALE)
    canvas.text(
        (badge_x + LABEL_BADGE_PX + LABEL_GAP_PX, top + (LABEL_BADGE_PX - text_height(NAME_SCALE)) // 2),
        mark.name, mark.colour, scale=NAME_SCALE,
    )
    y = top + LABEL_BADGE_PX + 6
    for line in mark.lines:
        line_x = x + (width - text_width(line, NAME_SCALE) if align_right else 0)
        canvas.text((line_x, y), line, DETAIL_COLOUR, scale=NAME_SCALE)
        y += NAME_PITCH_PX
    return (x, top, x + width, top + height)


def figure_editor(colours: dict[str, tuple[int, int, int]]) -> tuple[Image.Image, list[Placed], Image.Image]:
    """The editor with its five boxes. Returns the figure, what was drawn over the screen, and the screen."""
    screen = screen_from_capture(colours)
    screen_w, screen_h = screen.size
    left_x = EDITOR_MARGIN_PX + EDITOR_GUTTER_PX + EDITOR_GAP_PX
    top_y = EDITOR_TOP_PX
    width = left_x + screen_w + EDITOR_GAP_PX + EDITOR_GUTTER_PX + EDITOR_MARGIN_PX
    height = top_y + screen_h + EDITOR_BOTTOM_PX
    canvas = diagrams.Canvas(width, height, colours, subset=SUBSET)
    canvas.image.paste(screen, (left_x, top_y))
    frame_box(
        canvas, grow((left_x, top_y, left_x + screen_w, top_y + screen_h), SCREEN_FRAME_PX),
        SCREEN_FRAME_COLOUR, SCREEN_FRAME_PX,
    )
    placed: list[Placed] = []
    labels: list[tuple[int, int, int, int]] = []

    def to_canvas(x: int, y: int) -> tuple[int, int]:
        return (left_x + x, top_y + y)

    canvas.text((EDITOR_MARGIN_PX, 22), "THE DARK FACTORY", WHITE, scale=TITLE_SCALE)
    canvas.text((EDITOR_MARGIN_PX, 22 + text_height(TITLE_SCALE) + 12), "COURTYARD MAP", DETAIL_COLOUR, scale=NAME_SCALE)

    for mark in MARKS:
        outer = outline_box(mark)
        frame_box(canvas, tuple_offset(outer, left_x, top_y), mark.colour, BOX_WIDTH_PX)
        badge_x, badge_y = mark.badge
        digit_badge(canvas, to_canvas(badge_x, badge_y), BADGE_PX, mark.number, mark.colour, BADGE_DIGIT_SCALE)
        placed.append(Placed(mark.number, "badge", (badge_x, badge_y, badge_x + BADGE_PX, badge_y + BADGE_PX)))

        width_px = label_lines_width(mark)
        height_px = label_height(mark)
        half = LEADER_WIDTH_PX // 2
        if mark.side == "right":
            label_left = left_x + screen_w + EDITOR_GAP_PX
            y = top_y + mark.attach
            top = y - LABEL_BADGE_PX // 2
            labels.append(draw_label(canvas, mark, label_left, top, align_right=False))
            start = left_x + outer[2]
            hline(canvas, start, label_left - LEADER_GAP_PX, y, LEADER_WIDTH_PX, mark.colour)
            placed.append(Placed(mark.number, "leader", (outer[2], mark.attach - half, screen_w, mark.attach + half + 1)))
        elif mark.side == "left":
            label_right = EDITOR_MARGIN_PX + EDITOR_GUTTER_PX
            y = top_y + mark.attach
            top = y - LABEL_BADGE_PX // 2
            labels.append(draw_label(canvas, mark, label_right - width_px, top, align_right=True))
            end = left_x + outer[0]
            hline(canvas, label_right + LEADER_GAP_PX, end, y, LEADER_WIDTH_PX, mark.colour)
            placed.append(Placed(mark.number, "leader", (0, mark.attach - half, outer[0], mark.attach + half + 1)))
        else:
            pole_x = left_x + mark.attach
            block_bottom = top_y - 18
            top = block_bottom - height_px
            if mark.side == "top-left":
                labels.append(draw_label(canvas, mark, pole_x - LEADER_GAP_PX - width_px, top, align_right=True))
            else:
                labels.append(draw_label(canvas, mark, pole_x + LEADER_GAP_PX, top, align_right=False))
            vline(canvas, pole_x, top, top_y + outer[1], LEADER_WIDTH_PX, mark.colour)
            placed.append(Placed(mark.number, "leader", (mark.attach - half, 0, mark.attach + half + 1, outer[1])))

    assert_disjoint(labels, width, height)
    return canvas.image, placed, screen


def tuple_offset(box: tuple[int, int, int, int], dx: int, dy: int) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = box
    return (x0 + dx, y0 + dy, x1 + dx, y1 + dy)


def assert_disjoint(boxes: list[tuple[int, int, int, int]], width: int, height: int) -> None:
    for index, (x0, y0, x1, y1) in enumerate(boxes):
        if x0 < 0 or y0 < 0 or x1 > width or y1 > height:
            raise SystemExit(f"label {index + 1} leaves the figure: {(x0, y0, x1, y1)} in {width}x{height}")
        for other in boxes[index + 1:]:
            if x0 < other[2] and other[0] < x1 and y0 < other[3] and other[1] < y1:
                raise SystemExit(f"labels overlap: {(x0, y0, x1, y1)} and {other}")


def drawn_pixels(screen: Image.Image, box: tuple[int, int, int, int]) -> int:
    """How many pixels in ``box`` of the screenshot are not black."""
    x0, y0, x1, y1 = box
    region = screen.crop((max(x0, 0), max(y0, 0), min(x1, screen.width), min(y1, screen.height)))
    black = diagrams.load_subset(SUBSET)[BLACK]
    return sum(1 for pixel in region.getdata() if pixel != black)


def longest_run(screen: Image.Image, box: tuple[int, int, int, int], horizontal: bool) -> int:
    """The longest stretch of non-black pixels along the axis of a leader, in any of its rows."""
    x0, y0, x1, y1 = (max(box[0], 0), max(box[1], 0), min(box[2], screen.width), min(box[3], screen.height))
    black = diagrams.load_subset(SUBSET)[BLACK]
    pixels = screen.load()
    best = 0
    lines = range(y0, y1) if horizontal else range(x0, x1)
    for fixed in lines:
        run = 0
        for moving in (range(x0, x1) if horizontal else range(y0, y1)):
            pixel = pixels[moving, fixed] if horizontal else pixels[fixed, moving]
            run = run + 1 if pixel != black else 0
            best = max(best, run)
    return best


def check_editor(placed: list[Placed], screen: Image.Image) -> list[str]:
    problems = []
    for item in placed:
        if item.kind == "badge":
            covered = drawn_pixels(screen, item.box)
            if covered:
                problems.append(f"badge {item.mark} covers {covered} drawn pixels of the interface at {item.box}")
        else:
            horizontal = item.box[2] - item.box[0] > item.box[3] - item.box[1]
            run = longest_run(screen, item.box, horizontal)
            if run > MAX_HAIRLINE_PX:
                problems.append(f"leader {item.mark} runs over {run} px of the interface at {item.box}")
    return problems


# ---- the proof figure ----------------------------------------------------------------------------

def figure_proof(colours: dict[str, tuple[int, int, int]]) -> Image.Image:
    before = snap(load_capture("proof-before.png"), colours)
    after = snap(load_capture("proof-after.png"), colours)
    if before.size != after.size:
        raise SystemExit(f"the proof pair differs in size: {before.size} and {after.size}")
    pane_w, pane_h = before.width * PROOF_ZOOM, before.height * PROOF_ZOOM
    width = PROOF_MARGIN_PX * 3 + pane_w * 2
    height = PROOF_HEADER_PX + pane_h + PROOF_FOOTER_PX
    canvas = diagrams.Canvas(width, height, colours, subset=SUBSET)
    panes = (
        ("BEFORE", "BEFORE.PNG", before, CYAN, PROOF_MARGIN_PX),
        ("AFTER", "AFTER.PNG", after, MAGENTA, PROOF_MARGIN_PX * 2 + pane_w),
    )
    for heading, filename, image, colour, x in panes:
        canvas.text((x, 20), heading, colour, scale=NAME_SCALE)
        canvas.image.paste(image.resize((pane_w, pane_h), Image.NEAREST), (x, PROOF_HEADER_PX))
        frame_box(canvas, grow((x, PROOF_HEADER_PX, x + pane_w, PROOF_HEADER_PX + pane_h), PROOF_FRAME_PX), colour, PROOF_FRAME_PX)
        details = f"{filename}  {before.width} X {before.height} PX"
        canvas.text((x, PROOF_HEADER_PX + pane_h + PROOF_FRAME_PX + 14), details, DETAIL_COLOUR, scale=DETAIL_SCALE)
    canvas.text(
        (PROOF_MARGIN_PX, height - 40), "THE SAME RECTANGLE, COMPARED BY PIXELS: DIFFERS", WHITE, scale=DETAIL_SCALE,
    )
    return canvas.image


# ---- the flow figure -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Plate:
    x: int
    y: int
    w: int
    h: int
    colour: str

    @property
    def right(self) -> int:
        return self.x + self.w

    @property
    def bottom(self) -> int:
        return self.y + self.h

    @property
    def centre_y(self) -> int:
        return self.y + self.h // 2

    @property
    def centre_x(self) -> int:
        return self.x + self.w // 2


def plate_text_size(title: str, title_scale: int, lines: tuple[str, ...], line_scale: int) -> tuple[int, int]:
    width = max([text_width(title, title_scale)] + [text_width(line, line_scale) for line in lines])
    height = text_height(title_scale) + 8 + len(lines) * (text_height(line_scale) + 5)
    return width, height


def draw_plate(canvas: diagrams.Canvas, plate: Plate, title: str, title_scale: int, title_colour: str,
               lines: tuple[str, ...], line_scale: int) -> None:
    frame_box(canvas, (plate.x, plate.y, plate.right, plate.bottom), plate.colour, FLOW_PLATE_LINE_PX)
    x = plate.x + FLOW_PAD_PX
    y = plate.y + FLOW_PAD_PX
    canvas.text((x, y), title, title_colour, scale=title_scale)
    y += text_height(title_scale) + 8
    for line in lines:
        canvas.text((x, y), line, DETAIL_COLOUR, scale=line_scale)
        y += text_height(line_scale) + 5


def sized_plate(x: int, y: int, colour: str, title: str, title_scale: int, lines: tuple[str, ...],
                line_scale: int, min_w: int = 0) -> Plate:
    w, h = plate_text_size(title, title_scale, lines, line_scale)
    return Plate(x, y, max(w + 2 * FLOW_PAD_PX, min_w), h + 2 * FLOW_PAD_PX, colour)


def figure_flow(colours: dict[str, tuple[int, int, int]]) -> Image.Image:
    ask_text = ("YOUR NOTE,", "OR CMD+D")
    route_lines = ("THE FIRST THAT APPLIES",)
    prove_text = ("BEFORE, AFTER,", "COMPARED BY", "PIXELS")
    ship_text = ("TESTS, COMMIT,", "PUSH, STATS")
    style_text = ("NO BUILD", "SAVE, LOOK")
    build_text = ("RUST EDIT:", "54.8 S")
    restart_text = ("TO READY:", "0.9 S")

    # Size every plate from its text first, then place them left to right.
    ask = sized_plate(0, 0, CYAN, "1 ASK", NAME_SCALE, ask_text, DETAIL_SCALE)
    prove = sized_plate(0, 0, CYAN, "3 PROVE", NAME_SCALE, prove_text, DETAIL_SCALE)
    ship = sized_plate(0, 0, WHITE, "4 SHIP", NAME_SCALE, ship_text, DETAIL_SCALE)
    style = sized_plate(0, 0, CYAN, "STYLE OR DATA", DETAIL_SCALE, style_text, DETAIL_SCALE)
    build = sized_plate(0, 0, MAGENTA, "BUILD", DETAIL_SCALE, build_text, DETAIL_SCALE)
    restart = sized_plate(0, 0, MAGENTA, "RESTART", DETAIL_SCALE, restart_text, DETAIL_SCALE)

    lane_gap = 28
    lane_b_w = build.w + FLOW_GAP_PX // 2 + restart.w + 0
    header_h = text_height(NAME_SCALE) + 8 + text_height(DETAIL_SCALE) + 22
    or_h = text_height(DETAIL_SCALE) + 2 * 12
    route_inner_w = max(style.w, lane_b_w, text_width(route_lines[0], DETAIL_SCALE))
    route_w = route_inner_w + 2 * FLOW_PAD_PX
    route_h = FLOW_PAD_PX + header_h + style.h + or_h + max(build.h, restart.h) + FLOW_PAD_PX

    x = FLOW_MARGIN_PX
    top = FLOW_PLATE_TOP_PX
    route = Plate(x + ask.w + FLOW_GAP_PX, top, route_w, route_h, YELLOW)
    centre = route.centre_y
    ask = Plate(x, centre - ask.h // 2, ask.w, ask.h, ask.colour)
    prove = Plate(route.right + FLOW_GAP_PX, centre - prove.h // 2, prove.w, prove.h, prove.colour)
    ship = Plate(prove.right + FLOW_GAP_PX, centre - ship.h // 2, ship.w, ship.h, ship.colour)

    rework_y = route.bottom + 40
    width = ship.right + FLOW_MARGIN_PX
    height = rework_y + text_height(DETAIL_SCALE) + 70 + text_height(DETAIL_SCALE)
    canvas = diagrams.Canvas(width, height, colours, subset=SUBSET)

    canvas.text((FLOW_MARGIN_PX, FLOW_TITLE_Y_PX), "ONE ITERATION OF THE FIX LOOP", TITLE_COLOUR, scale=NAME_SCALE)
    canvas.text(
        (FLOW_MARGIN_PX, FLOW_TITLE_Y_PX + text_height(NAME_SCALE) + 14),
        "SCHEMATIC. MEDIANS OF THREE RUNS ON AN APPLE M5", DETAIL_COLOUR, scale=DETAIL_SCALE,
    )

    draw_plate(canvas, ask, "1 ASK", NAME_SCALE, CYAN, ask_text, DETAIL_SCALE)
    draw_plate(canvas, prove, "3 PROVE", NAME_SCALE, CYAN, prove_text, DETAIL_SCALE)
    draw_plate(canvas, ship, "4 SHIP", NAME_SCALE, WHITE, ship_text, DETAIL_SCALE)

    # The route plate holds the two ways through: no build, or a build and a restart.
    frame_box(canvas, (route.x, route.y, route.right, route.bottom), YELLOW, FLOW_PLATE_LINE_PX)
    canvas.text((route.x + FLOW_PAD_PX, route.y + FLOW_PAD_PX), "2 ROUTE", YELLOW, scale=NAME_SCALE)
    canvas.text(
        (route.x + FLOW_PAD_PX, route.y + FLOW_PAD_PX + text_height(NAME_SCALE) + 8),
        route_lines[0], DETAIL_COLOUR, scale=DETAIL_SCALE,
    )
    lane_a_y = route.y + FLOW_PAD_PX + header_h
    style = Plate(route.x + FLOW_PAD_PX, lane_a_y, style.w, style.h, style.colour)
    draw_plate(canvas, style, "STYLE OR DATA", DETAIL_SCALE, CYAN, style_text, DETAIL_SCALE)
    or_y = style.bottom + 12
    canvas.text((route.x + FLOW_PAD_PX, or_y), "OR", DETAIL_COLOUR, scale=DETAIL_SCALE)
    lane_b_y = style.bottom + or_h
    build = Plate(route.x + FLOW_PAD_PX, lane_b_y, build.w, max(build.h, restart.h), build.colour)
    restart = Plate(build.right + FLOW_GAP_PX // 2, lane_b_y, restart.w, build.h, restart.colour)
    draw_plate(canvas, build, "BUILD", DETAIL_SCALE, MAGENTA, build_text, DETAIL_SCALE)
    draw_plate(canvas, restart, "RESTART", DETAIL_SCALE, MAGENTA, restart_text, DETAIL_SCALE)

    half = FLOW_ARROW_PX // 2
    hline(canvas, build.right, restart.x - FLOW_HEAD_LENGTH_PX, build.centre_y, FLOW_ARROW_PX, ARROW_COLOUR)
    arrow_head(canvas, (restart.x - FLOW_PLATE_LINE_PX, build.centre_y), "right", ARROW_COLOUR)
    for left, right in ((ask, route), (route, prove), (prove, ship)):
        hline(canvas, left.right, right.x - FLOW_HEAD_LENGTH_PX, centre, FLOW_ARROW_PX, ARROW_COLOUR)
        arrow_head(canvas, (right.x - 1, centre), "right", ARROW_COLOUR)

    # A proof that does not show, or that you reject, goes back to the route with the same iteration.
    back_x = route.x + 150
    vline(canvas, prove.centre_x, prove.bottom, rework_y, FLOW_ARROW_PX, PINK)
    hline(canvas, back_x - half, prove.centre_x + half, rework_y, FLOW_ARROW_PX, PINK)
    vline(canvas, back_x, rework_y, route.bottom + FLOW_HEAD_LENGTH_PX, FLOW_ARROW_PX, PINK)
    arrow_head(canvas, (back_x, route.bottom), "up", PINK)
    canvas.text((back_x + 20, rework_y + 14), "SAME PIXELS, OR YOU SAY NOT FIXED", PINK, scale=DETAIL_SCALE)
    canvas.text(
        (FLOW_MARGIN_PX, height - FLOW_MARGIN_PX - text_height(DETAIL_SCALE)),
        "BUILD AND RESTART ARE EDITOR.SH BUILD AND EDITOR.SH RESTART", DETAIL_COLOUR, scale=DETAIL_SCALE,
    )
    return canvas.image


# ---- rendering and checking ----------------------------------------------------------------------

def render(name: str) -> tuple[Image.Image, list[str]]:
    colours = diagrams.load_subset(SUBSET)
    if name == "editor":
        image, placed, screen = figure_editor(colours)
        return image, check_editor(placed, screen)
    if name == "flow":
        return figure_flow(colours), []
    return figure_proof(colours), []


def palette_problems(name: str, image: Image.Image) -> list[str]:
    allowed = set(diagrams.load_subset(SUBSET).values())
    found = image.convert("RGB").getcolors(maxcolors=MAX_CAPTURE_COLOURS) or []
    used = {colour for _, colour in found}
    problems = []
    if len(used) > MAX_COLOURS:
        problems.append(f"{name}: {len(used)} colours, at most {MAX_COLOURS}")
    for colour in sorted(used - allowed):
        problems.append(f"{name}: colour {colour} is not in the {SUBSET} subset")
    return problems


def source_problems() -> list[str]:
    """The three sources must agree with each other: --check measures it, so a stale one cannot hide."""
    before = load_capture("proof-before.png")
    after = load_capture("proof-after.png")
    editor = load_capture("editor-map.png")
    problems = []
    crop = editor.crop(PROOF_RECT)
    if crop.size != before.size or ImageChops.difference(crop, before).getbbox() is not None:
        problems.append("proof-before.png is not the PROOF_RECT crop of editor-map.png: the sources disagree")
    if before.size != after.size:
        problems.append(f"proof-before.png is {before.size} and proof-after.png is {after.size}")
    elif ImageChops.difference(before, after).getbbox() is None:
        problems.append("proof-before.png and proof-after.png are identical: there is nothing to prove")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--figure", choices=[*FIGURES, "all"], default="all")
    parser.add_argument("--out", help="directory to write into; default art/, or a temporary one with --check")
    parser.add_argument("--check", action="store_true", help="measure the figures instead of trusting them")
    args = parser.parse_args(argv)

    names = list(FIGURES) if args.figure == "all" else [args.figure]
    temporary = None
    if args.out:
        out_dir = Path(args.out)
    elif args.check:
        temporary = tempfile.TemporaryDirectory()
        out_dir = Path(temporary.name)
    else:
        out_dir = ART_DIR
    if args.check and out_dir.resolve() == ART_DIR:
        print("--check compares with the committed figures in art/: give it another --out", file=sys.stderr)
        return 1

    problems: list[str] = source_problems() if args.check else []
    for name in names:
        image, overlay_problems = render(name)
        out = out_dir / FIGURES[name]
        out.parent.mkdir(parents=True, exist_ok=True)
        image.save(out)
        size = out.stat().st_size
        used = len(image.getcolors(maxcolors=MAX_CAPTURE_COLOURS) or [])
        print(f"{out}: {image.width}x{image.height}, {used} colours, {size} bytes")
        problems += palette_problems(FIGURES[name], image)
        if size > MAX_FIGURE_BYTES:
            problems.append(f"{FIGURES[name]}: {size} bytes, at most {MAX_FIGURE_BYTES}")
        if args.check:
            problems += [f"{FIGURES[name]}: {problem}" for problem in overlay_problems]
            committed = ART_DIR / FIGURES[name]
            if not committed.is_file():
                problems.append(f"{FIGURES[name]}: not committed in art/")
            else:
                with Image.open(committed) as other:
                    other_rgb = other.convert("RGB")
                if other_rgb.size != image.size or ImageChops.difference(other_rgb, image.convert("RGB")).getbbox():
                    problems.append(f"{FIGURES[name]}: differs from the committed figure; rerun without --check")
    for problem in problems:
        print(problem, file=sys.stderr)
    if temporary is not None:
        temporary.cleanup()
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
