"""Draw the spinner frames into the SFD: the shapes cli-spinners' text spinners cycle through.

Usage: python3 tools/add_shapes.py [SFD]

Each frame is cut or built from the font's own ○ ● ☐ ■ ◦ ✶ and strokes, so a spinner's
frames share one centre and box and it turns without pulsing:

- ◐ ◑ ◒ ◓ and ◴ ◵ ◶ ◷ are ○ with a half or a quarter of ● inside; ◜ ◝ ◞ ◟ ◠ ◡ are pieces
  of ○; ◰ ◱ ◲ ◳ are ☐ with a quarter of ■; ◢ ◣ ◤ ◥ are ■ cut corner to corner; ▯ is ☐
  narrowed and ▮ is it filled.
- ◎ ⦾ are ○ over ◦, ⊙ is ○ over ∙ (the period on the math axis) and ⦿ is ◉; ◌ is ○ in
  eight dashes and ◍ is ○ with bars inside; ⧆ ⧇ are ☐ over a small ∗ and ◦.
- ☰ … ☷ are bars of the hyphen's stroke, ✷ ✸ ✹ ✺ stars of ✶'s size with more points,
  ⊶ ⊷ a small ○ and ● joined by a stroke, ☖ ☗ and ▰ ▱ rings of ☐'s stroke and their fills,
  and ‼ is two !.

The script owns these glyphs and redraws them in place, so running it again changes nothing
but ModificationTime. Run tools/add_marks.py and tools/add_ligatures.py after it.
"""
import argparse
import math
import pathlib
import sys

import fontforge
import psMat

import lig_geometry as geo
import measure
from add_powerline import circle, polygon
from project import ADVANCE, SFD, save_checked, validation_errors

CX, AXIS = ADVANCE / 2, 269  # the cell's middle and the math axis, ○ ● ☐ ■'s centre
DEG = math.pi / 180

CIRCLE, DISC, BOX, SQUARE, WHITE_BULLET = 0x25CB, 0x25CF, 0x2610, 0x25A0, 0x25E6
HALVES = {0x25D0: dict(x1=CX), 0x25D1: dict(x0=CX), 0x25D2: dict(y1=AXIS), 0x25D3: dict(y0=AXIS)}
QUADRANTS = {"upper left": dict(x1=CX, y0=AXIS), "lower left": dict(x1=CX, y1=AXIS),
             "lower right": dict(x0=CX, y1=AXIS), "upper right": dict(x0=CX, y0=AXIS)}
CIRCLE_QUADRANTS = dict(zip((0x25F4, 0x25F5, 0x25F6, 0x25F7), QUADRANTS.values()))
SQUARE_QUADRANTS = dict(zip((0x25F0, 0x25F1, 0x25F2, 0x25F3), QUADRANTS.values()))
# ◰ ◱ ◲ ◳ are references to ☐ and to a quarter of ■, a component of its own, which overlap
# as ∄'s E and slash do (validate() reports the overlap, 0x4, as it does for ∄). Drawn into
# one outline with ☐, the autohinter writes a NaN into a hint mask, which drops the glyph's
# other hints whenever the SFD is read back.
SQUARE_QUARTERS = dict(zip(SQUARE_QUADRANTS, ("square.upperleft", "square.lowerleft",
                                              "square.lowerright", "square.upperright")))
OVERLAPPING_REFERENCES = 0x4
QUARTER_INSET = 6  # the quarters' edges under ☐'s stroke, so none coincides with its outline
ARCS = {0x25DC: QUADRANTS["upper left"], 0x25DD: QUADRANTS["upper right"],
        0x25DE: QUADRANTS["lower right"], 0x25DF: QUADRANTS["lower left"],
        0x25E0: dict(y0=AXIS), 0x25E1: dict(y1=AXIS)}
LOWER_RIGHT, LOWER_LEFT, UPPER_LEFT, UPPER_RIGHT = 0x25E2, 0x25E3, 0x25E4, 0x25E5
BLACK_BAR, WHITE_BAR = 0x25AE, 0x25AF
NARROW = 0.527  # ▮'s width over its height in Fira Code, the only reference with ▮ ▯
BULLSEYE, CIRCLED_BULLET, CIRCLED_WHITE_BULLET, DOTTED, FILLED = 0x25CE, 0x2299, 0x29BE, 0x25CC, 0x25CD
FISHEYE, CIRCLED_FISHEYE, BULLET_OPERATOR = 0x25C9, 0x29BF, 0x2219
SQUARED_ASTERISK, SQUARED_CIRCLE = 0x29C6, 0x29C7
# ⧆ is references to ☐ and to ∗ made small, a component of its own: drawn into one outline
# with ☐, the box's and the asterisk's stems give the autohinter overlapping hints, which
# validate() rejects.
SMALL_ASTERISK = "asterisk.small"
DASHES = 8          # ◌: Maple Mono's, the only reference's, has eight
DASH_GAP = 60       # along the ring's middle, so the gaps stay open at 12 px
FILL_BARS = 3       # ◍: three bars of ◦'s stroke leave four gaps of 55 in ○'s counter
THIN = 41           # ◦'s ring, which the bars inside ◍ and between ⊶ ⊷'s ends take
ASTERISK_SCALE = 0.48  # ⧆'s ∗ in ☐'s counter, half a stroke clear of it, thickened like the small figures
TRIGRAMS = range(0x2630, 0x2638)
# Bit k of a trigram's offset from ☰ breaks line k from the top: ☱ (1) breaks the top line,
# ☲ (2) the middle one, ☴ (4) the bottom one, ☷ (7) all three.
TRIGRAM_PITCH = 176  # the bars span 84% of ○'s height, as Fira Code's span its ○'s
TRIGRAM_INSET = 55   # from the cell's sides; Fira Code's bars keep 14% of the cell
BROKEN_GAP = 90      # between a broken line's halves: a fifth of the width, Fira Code's 23%
SIX_STAR = 0x2736
STARS = {0x2737: (8, 0.60), 0x2738: (8, 0.74), 0x2739: (12, 0.72)}  # (points, inner radius)
ASTERISK_STAR, SPOKES, SPOKE = 0x273A, 8, 50  # ✺: sixteen points as eight spokes
TIP = 20  # the stars' tips are rounded as ✶'s are, by pushing a smaller polygon out this far
ORIGINAL_OF, IMAGE_OF = 0x22B6, 0x22B7
SMALL_ROUND = 200  # ⊶ ⊷'s ○ and ● across; their centres 300 apart, the link between them
SHOGI_WHITE, SHOGI_BLACK = 0x2616, 0x2617
SHOGI_SHOULDER, SHOGI_TAPER = 140, 20  # the shoulders this far below the apex, the base narrower
BLACK_PARALLELOGRAM, WHITE_PARALLELOGRAM = 0x25B0, 0x25B1
PARALLELOGRAM_HEIGHT, SLANT = 300, 90  # on the math axis, leaning right
DOUBLE_EXCLAMATION, EXCLAMATION_OFFSET = 0x203C, 123  # the dots 94 apart: Maple Mono's are 93

COMPONENTS = (SMALL_ASTERISK, *SQUARE_QUARTERS.values())  # unencoded, built into the frames
CODES = (*HALVES, *CIRCLE_QUADRANTS, *ARCS, *SQUARE_QUADRANTS,
         LOWER_RIGHT, LOWER_LEFT, UPPER_LEFT, UPPER_RIGHT, BLACK_BAR, WHITE_BAR,
         BULLSEYE, CIRCLED_BULLET, CIRCLED_WHITE_BULLET, CIRCLED_FISHEYE, BULLET_OPERATOR,
         DOTTED, FILLED, SQUARED_ASTERISK, SQUARED_CIRCLE, *TRIGRAMS, *STARS, ASTERISK_STAR,
         ORIGINAL_OF, IMAGE_OF, SHOGI_WHITE, SHOGI_BLACK, BLACK_PARALLELOGRAM,
         WHITE_PARALLELOGRAM, DOUBLE_EXCLAMATION)


class Ref:
    """A glyph made of references: [(glyph name, matrix)], in the order the SFD lists them."""

    def __init__(self, *parts):
        self.parts = [(name, matrix) for name, matrix in parts]


def clockwise(layer):
    """Every contour turned to run clockwise, as a filled outline must; a stroked path or a
    polygon can come out the other way, which removeOverlap would take for a hole."""
    out = layer.dup()
    for contour in out:
        if not contour.isClockwise():
            contour.reverseDirection()
    return out


def clip(layer, mask):
    """The part of `layer` inside the one-contour `mask`."""
    out = layer.dup()
    out += clockwise(mask)
    out.intersect()
    return out


def as_ring(layer):
    """The outline with its widest contour clockwise and the others counter-clockwise: a
    ring, whichever way a stroke came out."""
    out = layer.dup()
    widest = max(out, key=lambda c: c.boundingBox()[2] - c.boundingBox()[0])
    for contour in out:
        if contour.isClockwise() != (contour == widest):
            contour.reverseDirection()
    return out


def outer(layer):
    """The outline's clockwise contour: a ring filled in."""
    [contour] = [c for c in layer if c.isClockwise()]
    out = fontforge.layer()
    out += contour
    return out


def line(p0, p1, width):
    """A straight stroke with round ends."""
    contour = fontforge.contour()
    contour.moveTo(*p0)
    contour.lineTo(*p1)
    layer = fontforge.layer()
    layer += contour
    return layer.stroke("circular", width, "round", "round")


def moved(layer, dx, dy):
    return geo.transformed(layer, psMat.translate(dx, dy))


def centred(layer, cx=CX, cy=AXIS):
    x0, y0, x1, y1 = layer.boundingBox()
    return moved(layer, cx - (x0 + x1) / 2, cy - (y0 + y1) / 2)


def turned(cx=CX, cy=AXIS):
    """The matrix that turns a glyph 180° about the cell's centre."""
    return geo.about(psMat.rotate(math.pi), cx, cy)


def glyph_for(font, key):
    """The glyph at a code point, or with a name for a component, created if missing."""
    if key in font:
        return font[key]
    if not isinstance(key, str):
        return font.createChar(key, f"uni{key:04X}")
    glyph = font.createChar(-1, key)
    font.encoding = "UnicodeBmp"  # an unencoded glyph switches the font to a Custom encoding
    return glyph


def weighted(font, key, layer, delta):
    """`layer` with its strokes `delta` heavier. changeWeight only works on a glyph, so the
    glyph at `key`, which the caller is about to redraw, is the workspace."""
    glyph = glyph_for(font, key)
    glyph.references = ()
    glyph.foreground = layer
    glyph.changeWeight(delta, "CJK", 0, 0, "auto")
    glyph.correctDirection()  # changeWeight can leave contours reversed
    return glyph.foreground.dup()


def bar(font, x0, x1, yc):
    """The hyphen's stroke, its straight middle stretched or shrunk to run x0..x1, centred on
    yc."""
    hyphen = measure.ink(font, "hyphen")
    hx0, _, hx1, _ = hyphen.boundingBox()
    layer = geo.stretch_span(hyphen, hx0 + 60, hx1 - 60, (x1 - x0) - (hx1 - hx0))
    bx0, by0, bx1, by1 = layer.boundingBox()
    return moved(layer, x0 - bx0, yc - (by0 + by1) / 2)


def inset(points, d):
    """A clockwise polygon's corners moved inward so every edge lies `d` closer to the middle:
    the centre line of a ring of stroke 2d that fills the polygon."""
    n = len(points)
    edges = []
    for i in range(n):
        (x0, y0), (x1, y1) = points[i], points[(i + 1) % n]
        dx, dy = x1 - x0, y1 - y0
        length = math.hypot(dx, dy)
        nx, ny = dy / length, -dx / length  # the right-hand normal points inward
        edges.append(((x0 + nx * d, y0 + ny * d), (dx, dy)))
    out = []
    for i in range(n):
        (px, py), (dx1, dy1) = edges[i - 1]
        (qx, qy), (dx2, dy2) = edges[i]
        t = ((qx - px) * dy2 - (qy - py) * dx2) / (dx1 * dy2 - dy1 * dx2)
        out.append((px + dx1 * t, py + dy1 * t))
    return out


def ring_and_fill(points, stroke):
    """(ring, fill): a closed polygon drawn as a ring of `stroke` with round corners, filling
    the polygon, and the ring filled in."""
    path = clockwise(polygon(inset(points, stroke / 2)))
    ring = as_ring(geo.cleanup(path.stroke("circular", stroke, "round", "round")))
    return ring, outer(ring)


def circle_cuts(font):
    ring, disc = measure.ink(font, f"uni{CIRCLE:04X}"), measure.ink(font, f"uni{DISC:04X}")
    out = {}
    for code, cut in {**HALVES, **CIRCLE_QUADRANTS}.items():
        out[code] = geo.cleanup(geo.union(ring, geo.trim(disc, **cut)))
    for code, cut in ARCS.items():
        out[code] = geo.cleanup(geo.trim(ring, **cut))
    return out


def square_cuts(font):
    box, square = measure.ink(font, f"uni{BOX:04X}"), measure.ink(font, f"uni{SQUARE:04X}")
    # The quarters are cut from ■ shrunk by QUARTER_INSET on every side, under ☐'s stroke:
    # a segment that coincides with another's troubles some rasterizers.
    x0, y0, x1, y1 = square.boundingBox()
    shrink = psMat.scale(1 - 2 * QUARTER_INSET / (x1 - x0), 1 - 2 * QUARTER_INSET / (y1 - y0))
    inset = geo.transformed(square, geo.about(shrink, (x0 + x1) / 2, (y0 + y1) / 2))
    out = {}
    for code, cut in SQUARE_QUADRANTS.items():
        out[SQUARE_QUARTERS[code]] = geo.cleanup(geo.trim(inset, **cut))
        out[code] = Ref((f"uni{BOX:04X}", psMat.identity()), (SQUARE_QUARTERS[code], psMat.identity()))
    # ■ cut along its diagonal from the top right to the bottom left, by a triangle that
    # reaches well past it.
    far = 200
    lower_right = geo.cleanup(clip(square, polygon([(x1 + far, y1 + far), (x1 + far, y0 - far),
                                                    (x0 - far, y0 - far)])))
    out[LOWER_RIGHT] = lower_right
    out[LOWER_LEFT] = geo.mirrored_x(lower_right, CX)
    out[UPPER_LEFT] = Ref((f"uni{LOWER_RIGHT:04X}", turned()))
    out[UPPER_RIGHT] = Ref((f"uni{LOWER_LEFT:04X}", turned()))
    # ▯: ☐ with the straight middle of its top and bottom shrunk, its corners kept.
    width = round(NARROW * (y1 - y0))
    narrow = centred(geo.stretch_span(box, x0 + 100, x1 - 100, width - (x1 - x0)))
    out[WHITE_BAR] = geo.cleanup(narrow)
    out[BLACK_BAR] = outer(out[WHITE_BAR])
    return out


def rings(font):
    ring, disc = measure.ink(font, f"uni{CIRCLE:04X}"), measure.ink(font, f"uni{DISC:04X}")
    circle_name, box_name = f"uni{CIRCLE:04X}", f"uni{BOX:04X}"
    bullet_name = f"uni{WHITE_BULLET:04X}"
    out = {BULLSEYE: Ref((circle_name, psMat.identity()), (bullet_name, psMat.identity())),
           CIRCLED_WHITE_BULLET: Ref((circle_name, psMat.identity()), (bullet_name, psMat.identity())),
           CIRCLED_FISHEYE: Ref((f"uni{FISHEYE:04X}", psMat.identity())),
           SQUARED_CIRCLE: Ref((box_name, psMat.identity()), (bullet_name, psMat.identity()))}
    # ∙: the period moved onto the math axis, centred in the cell.
    px0, py0, px1, py1 = font["period"].boundingBox()
    dot = psMat.translate(round(CX - (px0 + px1) / 2), round(AXIS - (py0 + py1) / 2))
    out[BULLET_OPERATOR] = Ref(("period", dot))
    out[CIRCLED_BULLET] = Ref((circle_name, psMat.identity()),
                              (f"uni{BULLET_OPERATOR:04X}", psMat.identity()))
    # ◌: the ring cut into dashes by wedges from the centre, one dash on each axis.
    rx0, ry0, rx1, ry1 = ring.boundingBox()
    (_, inner_left), (inner_right, _) = measure.spans_at_y(ring, AXIS)
    r_out = ((rx1 - rx0) + (ry1 - ry0)) / 4
    r_mid = (r_out + (inner_right - inner_left) / 2) / 2
    span, gap = 2 * math.pi / DASHES, DASH_GAP / r_mid
    pieces = []
    for k in range(DASHES):
        a0, a1 = k * span - span / 2 + gap / 2, k * span + span / 2 - gap / 2
        reach = 2 * r_out
        wedge = polygon([(CX, AXIS)] + [(CX + reach * math.cos(a), AXIS + reach * math.sin(a))
                                        for a in (a0, (a0 + a1) / 2, a1)])
        pieces.append(clip(ring, wedge))
    out[DOTTED] = geo.cleanup(geo.union(*pieces))
    # ◍: bars of ◦'s stroke spaced evenly across the counter, ending inside the ring: cut by
    # ● shrunk into the ring's band, since removeOverlap mishandles ends on the ring's edge.
    step = (inner_right - inner_left) / (FILL_BARS + 1)
    inside = geo.transformed(disc, geo.about(psMat.scale(r_mid / r_out), CX, AXIS))
    bars = [clip(geo.rect(x - THIN / 2, ry0, x + THIN / 2, ry1), inside)
            for x in (inner_left + step * (k + 1) for k in range(FILL_BARS))]
    out[FILLED] = geo.cleanup(geo.union(ring, *bars))
    # ⧆: ☐ over ∗ at half size, thickened back like the small figures, centred in the cell.
    asterisk = measure.ink(font, "asterisk")
    ax0, ay0, ax1, ay1 = asterisk.boundingBox()
    small = geo.transformed(asterisk, geo.about(psMat.scale(ASTERISK_SCALE),
                                                (ax0 + ax1) / 2, (ay0 + ay1) / 2))
    out[SMALL_ASTERISK] = geo.cleanup(centred(weighted(font, SMALL_ASTERISK, small, 12)))
    out[SQUARED_ASTERISK] = Ref((box_name, psMat.identity()), (SMALL_ASTERISK, psMat.identity()))
    return out


def trigrams(font):
    x0, x1 = TRIGRAM_INSET, ADVANCE - TRIGRAM_INSET
    out = {}
    for code in TRIGRAMS:
        parts = []
        for k, y in enumerate((AXIS + TRIGRAM_PITCH, AXIS, AXIS - TRIGRAM_PITCH)):
            if (code - TRIGRAMS.start) >> k & 1:
                parts += [bar(font, x0, CX - BROKEN_GAP / 2, y), bar(font, CX + BROKEN_GAP / 2, x1, y)]
            else:
                parts.append(bar(font, x0, x1, y))
        out[code] = geo.cleanup(geo.union(*parts))
    return out


def stars(font):
    """Stars of ✶'s radius: a polygon with `points` tips, one straight up, pushed out by TIP
    so its tips round off as ✶'s do; ✺ is eight spokes of the stroke SPOKE."""
    _, y0, _, y1 = font[SIX_STAR].boundingBox()  # ✶ points up, so its height is 2 radii
    radius = (y1 - y0) / 2 - TIP
    out = {}
    for code, (points, inner) in STARS.items():
        corners = []
        for k in range(2 * points):
            a = 90 * DEG + k * math.pi / points
            r = radius if k % 2 == 0 else radius * inner
            corners.append((CX + r * math.cos(a), AXIS + r * math.sin(a)))
        poly = clockwise(polygon(corners))
        pushed = clockwise(poly.stroke("circular", 2 * TIP, "round", "round"))
        out[code] = geo.cleanup(geo.union(poly, pushed))
    reach = radius + TIP - SPOKE / 2
    spokes = [line((CX - reach * math.cos(a), AXIS - reach * math.sin(a)),
                   (CX + reach * math.cos(a), AXIS + reach * math.sin(a)), SPOKE)
              for a in (90 * DEG + k * math.pi / SPOKES for k in range(SPOKES))]
    out[ASTERISK_STAR] = geo.cleanup(geo.union(*spokes))
    return out


def joined_rounds(font):
    """⊶ ⊷: ○ and ● made small (their ring thickened back towards ◦'s), 300 apart, joined
    by a stroke of ◦'s ring that ends inside both."""
    ring, disc = measure.ink(font, f"uni{CIRCLE:04X}"), measure.ink(font, f"uni{DISC:04X}")
    rx0, _, rx1, _ = ring.boundingBox()
    scale = SMALL_ROUND / (rx1 - rx0)
    small_ring = weighted(font, ORIGINAL_OF, geo.transformed(ring, psMat.scale(scale)), 6)
    small_disc = geo.transformed(disc, psMat.scale(scale))
    left, right = CX - 150, CX + 150
    link = line((left + SMALL_ROUND / 2 - 10, AXIS), (right - SMALL_ROUND / 2 + 10, AXIS), THIN)
    return {ORIGINAL_OF: geo.cleanup(geo.union(centred(small_ring, left), link,
                                               centred(small_disc, right))),
            IMAGE_OF: geo.cleanup(geo.union(centred(small_disc, left), link,
                                            centred(small_ring, right)))}


def polygons(font):
    """☖ ☗: a shogi piece filling ☐'s box, its apex at the top and its base a little narrower
    than its shoulders; ▰ ▱: a parallelogram on the math axis leaning right. Both are rings
    of ☐'s stroke and their fills, drawn as strokes (a sheared ring would thin)."""
    box = measure.ink(font, f"uni{BOX:04X}")
    x0, y0, x1, y1 = box.boundingBox()
    (a, b), *_ = measure.spans_at_x(box, CX)
    stroke = b - a
    shogi = [(CX, y1), (x1, y1 - SHOGI_SHOULDER), (x1 - SHOGI_TAPER, y0), (x0 + SHOGI_TAPER, y0),
             (x0, y1 - SHOGI_SHOULDER)]
    top, bottom = AXIS + PARALLELOGRAM_HEIGHT / 2, AXIS - PARALLELOGRAM_HEIGHT / 2
    parallelogram = [(x0 + SLANT, top), (x1, top), (x1 - SLANT, bottom), (x0, bottom)]
    out = {}
    out[SHOGI_WHITE], out[SHOGI_BLACK] = ring_and_fill(shogi, stroke)
    out[WHITE_PARALLELOGRAM], out[BLACK_PARALLELOGRAM] = ring_and_fill(parallelogram, stroke)
    return out


def build(font):
    """Every frame: code point (or a component's name) -> outline layer, or Ref for a glyph
    made of references."""
    out = {}
    for family in (circle_cuts, square_cuts, rings, trigrams, stars, joined_rounds, polygons):
        out.update(family(font))
    out[DOUBLE_EXCLAMATION] = Ref(("exclam", psMat.translate(-EXCLAMATION_OFFSET, 0)),
                                  ("exclam", psMat.translate(EXCLAMATION_OFFSET, 0)))
    return out


def add_glyphs(font, outlines):
    for key, drawn in outlines.items():
        glyph = glyph_for(font, key)
        glyph.references = ()
        glyph.foreground = fontforge.layer()
        if isinstance(drawn, Ref):
            # FontForge writes references in reverse order.
            for name, matrix in reversed(drawn.parts):
                glyph.addReference(name, matrix)
        else:
            glyph.foreground = drawn
            glyph.correctDirection()
        glyph.width = ADVANCE
        glyph.autoHint()
    font.encoding = "UnicodeBmp"


def check(path):
    """Exit non-zero if a frame in the SFD at `path` fails validate()."""
    font = fontforge.open(str(path))
    allowed = {code: OVERLAPPING_REFERENCES for code in SQUARE_QUADRANTS}
    failed = {font[key].glyphname: hex(flags) for key in (*CODES, *COMPONENTS)
              if (flags := validation_errors(font[key]) & ~allowed.get(key, 0))}
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
    add_glyphs(font, build(font))
    save_checked(font, sfd, __file__)


if __name__ == "__main__":
    main()
