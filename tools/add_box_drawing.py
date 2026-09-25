"""Draw Box Drawing and Block Elements (U+2500–U+259F) into the SFD.

Usage: python3 tools/add_box_drawing.py [SFD]

Each glyph is built from its Unicode name: the arms it names and their weight, dashes, arcs,
diagonals, block fractions and shades. The script owns every glyph in the range and redraws it
in place, so glyph indices stay put and running it again changes nothing but ModificationTime.
A glyph whose outline would repeat an earlier one's, moved, becomes a reference to it.
"""
import argparse
import math
import pathlib
import sys
import unicodedata

import fontforge
import psMat

import lig_geometry as geo
from project import ADVANCE, SFD, save_checked, validation_errors

# The Nerd Fonts patcher replaces the whole range unless the font has every glyph in it.
CODES = range(0x2500, 0x25A0)

LINE_BOTTOM, LINE_TOP = -350, 900  # the line box, which block elements fill
LINE_HEIGHT = LINE_TOP - LINE_BOTTOM
OVERLAP = 10  # how far strokes run into the next cell, so lines join without a seam
# Verticals run this far past the line box, so they still meet at 1.5 em line spacing, which
# apps get by adding space evenly above and below.
REACH = (1500 - LINE_HEIGHT) // 2 + OVERLAP
LEFT, RIGHT = -OVERLAP, ADVANCE + OVERLAP
BOTTOM, TOP = LINE_BOTTOM - REACH, LINE_TOP + REACH

MIDDLE_X = ADVANCE // 2  # the centre of the vertical strokes
MIDDLE_Y = 269           # the centre of the horizontal strokes: the math axis, level with - and →

# Stroke weights. Heavy is twice light, as in Intel One Mono and Maple Mono. A double line is
# two light strokes a light stroke apart, as in all three reference fonts.
LIGHT = 84
HEAVY = 2 * LIGHT
GAP = LIGHT // 2  # half the gap between the two strokes of a double line
HALF = {"light": LIGHT // 2, "heavy": HEAVY // 2, "double": GAP + LIGHT}  # half of the width

# Dashes per cell -> the gap between dashes, from Maple Mono, the middle of the three reference
# fonts. Cell edges take half a gap, so the rhythm stays even across cells.
DASH_GAP = {2: 128, 3: 68, 4: 46}
DASH_COUNT = {"DOUBLE": 2, "TRIPLE": 3, "QUADRUPLE": 4}

ARC_RADIUS = ADVANCE // 2  # of the centre line, as in Intel One Mono: arcs span half a cell
KAPPA = 4 * (math.sqrt(2) - 1) / 3  # control-point distance of a cubic quarter circle

# Shades are a grid of pixels 55 x 62.5, which repeats in every cell so shaded areas tile.
SHADE_GRID = (10, 20)
# Which pixel (column, row) of every 2 x 2 is ink. Each shade holds the lighter ones' pixels.
SHADES = {"LIGHT": {(1, 1)}, "MEDIUM": {(1, 1), (0, 0)}, "DARK": {(1, 1), (0, 0), (1, 0)}}

SIDES = {"UP": ("up",), "DOWN": ("down",), "LEFT": ("left",), "RIGHT": ("right",),
         "VERTICAL": ("up", "down"), "HORIZONTAL": ("left", "right")}
WEIGHTS = {"LIGHT": "light", "SINGLE": "light", "HEAVY": "heavy", "DOUBLE": "double"}
OPPOSITE = {"up": "down", "down": "up", "left": "right", "right": "left"}
ACROSS = {"up": ("left", "right"), "down": ("left", "right"),
          "left": ("up", "down"), "right": ("up", "down")}
EIGHTHS = {"ONE EIGHTH": 1, "ONE QUARTER": 2, "THREE EIGHTHS": 3, "HALF": 4, "FIVE EIGHTHS": 5,
           "THREE QUARTERS": 6, "SEVEN EIGHTHS": 7}


def round_half_up(value):
    return math.floor(value + 0.5)


def eighth_x(k):
    return round_half_up(k * ADVANCE / 8)


def eighth_y(k):
    return LINE_BOTTOM + round_half_up(k * LINE_HEIGHT / 8)


def arms(words):
    """{side: weight} from the words of a line glyph's name after BOX DRAWINGS, without AND.

    A name that starts with a weight gives it to the sides after it ("HEAVY DOWN AND RIGHT",
    "LIGHT LEFT AND HEAVY RIGHT"); otherwise each weight follows its sides ("DOWN LIGHT AND
    RIGHT HEAVY").
    """
    result, sides, weight = {}, [], None
    leading = words[0] in WEIGHTS
    for word in words:
        if word in WEIGHTS:
            weight = WEIGHTS[word]
            if not leading:
                result.update(dict.fromkeys(sides, weight))
                sides = []
        elif leading:
            result.update(dict.fromkeys(SIDES[word], weight))
        else:
            sides.extend(SIDES[word])
    return result


def trace(xs, ys, filled):
    """Outlines around the cells of the grid xs x ys for which filled(column, row) is true:
    clockwise, holes counter-clockwise, each starting at its lowest left corner.

    Cells that touch only at a corner get separate outlines.
    """
    ends = {}  # every boundary edge, start -> set of ends; edges between two cells cancel

    def add(a, b):
        if a in ends.get(b, ()):
            ends[b].remove(a)
        else:
            ends.setdefault(a, set()).add(b)

    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            if filled(i, j):
                x0, x1, y0, y1 = xs[i], xs[i + 1], ys[j], ys[j + 1]
                add((x0, y0), (x0, y1))
                add((x0, y1), (x1, y1))
                add((x1, y1), (x1, y0))
                add((x1, y0), (x0, y0))

    def heading(a, b):
        return (b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1])

    def turn(incoming, outgoing):
        # Negative for a right turn: at a corner where two cells touch, turning right keeps
        # to the cell the outline came along.
        return incoming[0] * outgoing[1] - incoming[1] * outgoing[0]

    loops = []
    while any(ends.values()):
        # The lowest left corner is never one where two cells touch, so it has one way out
        # and any heading will do.
        start = min(point for point, out in ends.items() if out)
        loop, point, way = [start], start, (0, 1)
        while True:
            options = ends[point]
            following = min(options, key=lambda end: turn(way, heading(point, end)))
            options.remove(following)
            way, point = heading(point, following), following
            if point == start:
                break
            loop.append(point)
        # Keep only the corners.
        loops.append([p for k, p in enumerate(loop)
                      if heading(loop[k - 1], p) != heading(p, loop[(k + 1) % len(loop)])])
    layer = fontforge.layer()
    for loop in loops:
        contour = fontforge.contour()
        contour.moveTo(*loop[0])
        for point in loop[1:]:
            contour.lineTo(*point)
        contour.closed = True
        layer += contour
    return layer


def region(rects, inside):
    """The outline of the points for which inside(x, y) is true, where every edge lies on an
    edge of one of `rects` (x0, y0, x1, y1)."""
    xs = sorted({x for x0, _, x1, _ in rects for x in (x0, x1)})
    ys = sorted({y for _, y0, _, y1 in rects for y in (y0, y1)})
    return trace(xs, ys, lambda i, j: inside((xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2))


def within(point, rect):
    x, y = point
    return rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]


def union(rects):
    return region(rects, lambda x, y: any(within((x, y), r) for r in rects))


def stroke(side, half_width, start):
    """The rectangle of an arm from the cell's edge on `side` to `start` short of the middle,
    or past it where `start` is negative."""
    return {"right": (MIDDLE_X + start, MIDDLE_Y - half_width, RIGHT, MIDDLE_Y + half_width),
            "left": (LEFT, MIDDLE_Y - half_width, MIDDLE_X - start, MIDDLE_Y + half_width),
            "up": (MIDDLE_X - half_width, MIDDLE_Y + start, MIDDLE_X + half_width, TOP),
            "down": (MIDDLE_X - half_width, BOTTOM, MIDDLE_X + half_width, MIDDLE_Y - start),
            }[side]


def lines(sides):
    """Straight lines from the middle to the named sides, {side: weight}.

    Each light or heavy arm runs past the middle by half the widest arm across it, so corners
    are square outside, or by half a light stroke where nothing crosses it.

    A double line is the two walls of a channel as wide as a light stroke. Channels of double
    arms join into one where they meet, so ╔ ╠ ╬ open into each other; a double arm that ends
    at a single line stops at its near edge, as in ╞ ╥. A single arm that ends at a double line
    stops at its near wall (╟ ╤); one that runs straight through crosses it (╪ ╫).
    """
    solid, stops, channels = [], [], []
    for side, weight in sides.items():
        across = [sides[s] for s in ACROSS[side] if s in sides]
        if weight == "double":
            through = sides.get(OPPOSITE[side]) == "double" or "double" in across or not across
            start = -GAP if through else max(HALF[w] for w in across)
            channels.append(stroke(side, GAP, start))
        else:
            reach = max((HALF[w] for w in across), default=HALF["light"])
            rect = stroke(side, HALF[weight], -reach)
            straight = sides.get(OPPOSITE[side]) in ("light", "heavy")
            (solid if straight else stops).append(rect)
    walls = [(x0 - LIGHT, y0 - LIGHT, x1 + LIGHT, y1 + LIGHT) for x0, y0, x1, y1 in channels]
    cell = (LEFT, BOTTOM, RIGHT, TOP)

    def inside(x, y):
        def hit(rects):
            return any(within((x, y), r) for r in rects)
        return within((x, y), cell) and (
            hit(solid) or not hit(channels) and (hit(stops) or hit(walls)))

    return region([*solid, *stops, *channels, *walls, cell], inside)


def dashes(count, weight, orientation):
    """`count` dashes per cell, evenly spaced across cells."""
    half, gap = HALF[weight], DASH_GAP[count]
    rects = []
    for k in range(count):
        if orientation == "HORIZONTAL":
            period = ADVANCE / count
            rects.append((round_half_up(k * period + gap / 2), MIDDLE_Y - half,
                          round_half_up((k + 1) * period - gap / 2), MIDDLE_Y + half))
        else:
            period = LINE_HEIGHT / count
            rects.append((MIDDLE_X - half, LINE_BOTTOM + round_half_up(k * period + gap / 2),
                          MIDDLE_X + half, LINE_BOTTOM + round_half_up((k + 1) * period - gap / 2)))
    return union(rects)


def arc(vertical, horizontal):
    """A quarter circle joining the arm on the `vertical` side to the one on the `horizontal`
    side, with straight ends that meet ─ and │ in the next cells."""
    sx = 1 if horizontal == "right" else -1
    sy = 1 if vertical == "up" else -1
    half = HALF["light"]
    cx, cy = MIDDLE_X + sx * ARC_RADIUS, MIDDLE_Y + sy * ARC_RADIUS  # the circle's centre
    y_end = TOP if sy > 0 else BOTTOM
    x_end = RIGHT if sx > 0 else LEFT
    outer, inner = ARC_RADIUS + half, ARC_RADIUS - half
    contour = fontforge.contour()
    contour.moveTo(MIDDLE_X - sx * half, y_end)
    contour.lineTo(MIDDLE_X - sx * half, cy)
    contour.cubicTo((MIDDLE_X - sx * half, cy - sy * KAPPA * outer),
                    (cx - sx * KAPPA * outer, MIDDLE_Y - sy * half),
                    (cx, MIDDLE_Y - sy * half))
    contour.lineTo(x_end, MIDDLE_Y - sy * half)
    contour.lineTo(x_end, MIDDLE_Y + sy * half)
    contour.lineTo(cx, MIDDLE_Y + sy * half)
    contour.cubicTo((cx - sx * KAPPA * inner, MIDDLE_Y + sy * half),
                    (MIDDLE_X + sx * half, cy - sy * KAPPA * inner),
                    (MIDDLE_X + sx * half, cy))
    contour.lineTo(MIDDLE_X + sx * half, y_end)
    contour.closed = True
    layer = fontforge.layer()
    layer += contour
    return layer


def diagonal():
    """╱: a light stroke from corner to corner of the line box, so diagonal neighbours at 1.25
    em line spacing continue it. It runs on into the next cells as far as ─ does, which keeps
    the stroke full width where two cells meet."""
    slope = LINE_HEIGHT / ADVANCE
    # How far the stroke's edges lie above and below its centre line, measured vertically.
    rise = HALF["light"] * math.hypot(ADVANCE, LINE_HEIGHT) / ADVANCE

    def centre(x):
        return LINE_BOTTOM + slope * x

    contour = fontforge.contour()
    contour.moveTo(LEFT, centre(LEFT) - rise)
    contour.lineTo(LEFT, centre(LEFT) + rise)
    contour.lineTo(RIGHT, centre(RIGHT) + rise)
    contour.lineTo(RIGHT, centre(RIGHT) - rise)
    contour.closed = True
    layer = fontforge.layer()
    layer += contour
    return layer


def box_drawing(words):
    """The outline of a Box Drawings character from its name's words after BOX DRAWINGS."""
    words = [word for word in words if word != "AND"]
    if "DASH" in words:
        dash = words.index("DASH")
        return dashes(DASH_COUNT[words[dash - 1]], WEIGHTS[words[0]], words[dash + 1])
    if words[1] == "ARC":
        return geo.cleanup(arc(*(SIDES[word][0] for word in words[2:])))
    if words[1] == "DIAGONAL":
        rising = diagonal()
        falling = geo.mirrored_x(rising, ADVANCE / 2)
        return geo.cleanup({"UPPER RIGHT TO LOWER LEFT": rising,
                            "UPPER LEFT TO LOWER RIGHT": falling,
                            "CROSS": geo.union(rising, falling)}[" ".join(words[2:])])
    return lines(arms(words))


def pixels(xs, ys, ink):
    """The outline of the cells (column, row) in `ink` of the grid xs x ys.

    FontForge counts outlines that meet at a single point as intersecting, so where two cells
    meet only at a corner, the lower one reaches 1 unit up into the empty cell above it and
    the two share an edge, as Fira Code's ▚ does.
    """
    rects = []
    for i, j in ink:
        pinched = any((i + d, j + 1) in ink and (i + d, j) not in ink and (i, j + 1) not in ink
                      for d in (-1, 1))
        rects.append((xs[i], ys[j], xs[i + 1], ys[j + 1] + (1 if pinched else 0)))
    return union(rects)


def quadrants(names):
    """The quadrants named, such as UPPER LEFT."""
    columns, rows = {"LEFT": 0, "RIGHT": 1}, {"LOWER": 0, "UPPER": 1}
    ink = set()
    for name in names:
        row, column = name.split()
        ink.add((columns[column], rows[row]))
    return pixels((0, eighth_x(4), ADVANCE), (LINE_BOTTOM, eighth_y(4), LINE_TOP), ink)


def shade(pattern):
    """The shade that inks the pixels `pattern` of every 2 x 2 in the grid."""
    columns, rows = SHADE_GRID
    xs = [round_half_up(i * ADVANCE / columns) for i in range(columns + 1)]
    ys = [LINE_BOTTOM + round_half_up(j * LINE_HEIGHT / rows) for j in range(rows + 1)]
    return pixels(xs, ys, {(i, j) for i in range(columns) for j in range(rows)
                           if (i % 2, j % 2) in pattern})


def block_element(name):
    """The outline of a Block Elements character from its name."""
    if name.endswith(" SHADE"):
        return shade(SHADES[name.split()[0]])
    if name.startswith("QUADRANT "):
        return quadrants(name.removeprefix("QUADRANT ").split(" AND "))
    if name == "FULL BLOCK":
        return union([(0, LINE_BOTTOM, ADVANCE, LINE_TOP)])
    side, fraction = name.removesuffix(" BLOCK").split(" ", 1)
    n = EIGHTHS[fraction]
    return union([{"UPPER": (0, eighth_y(8 - n), ADVANCE, LINE_TOP),
                   "LOWER": (0, LINE_BOTTOM, ADVANCE, eighth_y(n)),
                   "LEFT": (0, LINE_BOTTOM, eighth_x(n), LINE_TOP),
                   "RIGHT": (eighth_x(8 - n), LINE_BOTTOM, ADVANCE, LINE_TOP)}[side]])


def outline(code):
    name = unicodedata.name(chr(code))
    if name.startswith("BOX DRAWINGS "):
        return box_drawing(name.split()[2:])
    return block_element(name)


def build():
    """Every glyph in the range: code point -> outline layer.

    Straight-edged outlines are traced on whole units and need no cleanup; removeOverlap
    would merge the squares of ▒ where their corners touch.
    """
    return {code: outline(code) for code in CODES}


def shape_key(layer):
    """The outline moved to the origin, and how far it was moved: equal keys are copies."""
    x0, y0, _, _ = layer.boundingBox()
    return tuple(sorted(tuple((p.x - x0, p.y - y0, p.on_curve) for p in contour)
                        for contour in layer)), (x0, y0)


def add_glyphs(font, outlines):
    drawn = {}  # shape -> (glyph name, its outline's lower left corner)
    for code, layer in outlines.items():
        glyph = font[code] if code in font else font.createChar(code, f"uni{code:04X}")
        glyph.references = ()
        glyph.foreground = layer
        glyph.correctDirection()
        key, (x, y) = shape_key(glyph.foreground)
        if key in drawn:
            base, (bx, by) = drawn[key]
            glyph.foreground = fontforge.layer()
            glyph.addReference(base, psMat.translate(x - bx, y - by))
        else:
            drawn[key] = glyph.glyphname, (x, y)
        glyph.width = ADVANCE
        glyph.autoHint()


def check(path):
    """Exit non-zero if a glyph in the range in the SFD at `path` fails validate()."""
    font = fontforge.open(str(path))
    failed = {font[code].glyphname: hex(flags) for code in CODES
              if (flags := validation_errors(font[code]))}
    if failed:
        sys.exit(f"validate() failed: {failed}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("sfd", nargs="?", default=str(SFD), help="default: %(default)s")
    parser.add_argument("--check", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check:
        return check(args.sfd)

    sfd = pathlib.Path(args.sfd)
    font = fontforge.open(str(sfd))
    add_glyphs(font, build())
    save_checked(font, sfd, __file__)


if __name__ == "__main__":
    main()
