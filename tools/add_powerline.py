"""Draw the Powerline symbols U+E0A0–U+E0A2 and U+E0B0–U+E0B3 into the SFD.

Usage: python3 tools/add_powerline.py [SFD]

The separators fill the cell and the line box exactly, as the block elements do, so a prompt's
coloured segments meet them without a seam; the thin ones are the box drawing's light stroke.
The branch, line-number and padlock symbols are built from that stroke, round dots and the
font's own L and N. The script owns the seven glyphs and redraws them in place, so running it
again changes nothing but ModificationTime.
"""
import argparse
import math
import pathlib
import sys

import fontforge
import psMat

import lig_geometry as geo
from add_box_drawing import KAPPA, LIGHT, LINE_BOTTOM, LINE_TOP
from project import ADVANCE, SFD, save_checked, validation_errors

BRANCH, LINE_NUMBER, PADLOCK = 0xE0A0, 0xE0A1, 0xE0A2
RIGHT_SOLID, RIGHT_THIN, LEFT_SOLID, LEFT_THIN = 0xE0B0, 0xE0B1, 0xE0B2, 0xE0B3
CODES = (BRANCH, LINE_NUMBER, PADLOCK, RIGHT_SOLID, RIGHT_THIN, LEFT_SOLID, LEFT_THIN)

MIDDLE = (LINE_BOTTOM + LINE_TOP) // 2  # the separators' tip: the middle of the line box
INSET = 50  # how far the symbols keep inside the line box, top and bottom

# The branch: a trunk with a dot at each end, and a branch curving off it up to a third dot.
TRUNK_X, BRANCH_X = 140, 410
DOT = 80  # the dots' radius
TRUNK_BOTTOM, TRUNK_TOP = LINE_BOTTOM + INSET + DOT, LINE_TOP - INSET - DOT  # dot centres
BRANCH_DOT_Y = 600
FORK_Y = 150  # where the branch leaves the trunk

# The line-number symbol: L over N, the font's own letters made small.
LETTER_SCALE = 0.75
LETTER_GAP = 100

# The padlock: a rounded body with a keyhole, under a shackle of the light stroke.
BODY = (95, -80, 455, 320)  # x0, y0, x1, y1
CORNER = 40
SHACKLE_RADIUS = 160  # of its outer edge; the shackle's legs run into the body
SHACKLE_LEGS = 70
KEYHOLE_Y, KEYHOLE_RADIUS = 175, 45
SLOT_WIDTH, SLOT_BOTTOM = 50, 40


def polygon(points):
    """A closed straight-sided outline through `points`, as a layer."""
    contour = fontforge.contour()
    contour.moveTo(*points[0])
    for point in points[1:]:
        contour.lineTo(*point)
    contour.closed = True
    layer = fontforge.layer()
    layer += contour
    return layer


def circle(cx, cy, r):
    """A clockwise circle of four cubic quarters, as a layer."""
    k = KAPPA * r
    contour = fontforge.contour()
    contour.moveTo(cx, cy + r)
    contour.cubicTo((cx + k, cy + r), (cx + r, cy + k), (cx + r, cy))
    contour.cubicTo((cx + r, cy - k), (cx + k, cy - r), (cx, cy - r))
    contour.cubicTo((cx - k, cy - r), (cx - r, cy - k), (cx - r, cy))
    contour.cubicTo((cx - r, cy + k), (cx - k, cy + r), (cx, cy + r))
    contour.closed = True
    layer = fontforge.layer()
    layer += contour
    return layer


def rounded_rect(x0, y0, x1, y1, r):
    """A clockwise rectangle with quarter-circle corners of radius r, as a layer."""
    k = KAPPA * r
    contour = fontforge.contour()
    contour.moveTo(x0, y0 + r)
    contour.lineTo(x0, y1 - r)
    contour.cubicTo((x0, y1 - r + k), (x0 + r - k, y1), (x0 + r, y1))
    contour.lineTo(x1 - r, y1)
    contour.cubicTo((x1 - r + k, y1), (x1, y1 - r + k), (x1, y1 - r))
    contour.lineTo(x1, y0 + r)
    contour.cubicTo((x1, y0 + r - k), (x1 - r + k, y0), (x1 - r, y0))
    contour.lineTo(x0 + r, y0)
    contour.cubicTo((x0 + r - k, y0), (x0, y0 + r - k), (x0, y0 + r))
    contour.closed = True
    layer = fontforge.layer()
    layer += contour
    return layer


def stroked(path, width=LIGHT):
    """An open centre-line contour drawn as a stroke with round ends and joins."""
    layer = fontforge.layer()
    layer += path
    return layer.stroke("circular", width, "round", "round")


def holes(layer):
    """The outline's contours turned to run the other way, so they cut holes where they lie
    inside another outline."""
    out = layer.dup()
    for contour in out:
        contour.reverseDirection()
    return out


def solid_separator():
    """: a triangle from the cell's left edge to a point on its right edge, filling the line
    box, so the segment it ends meets it without a seam."""
    return polygon([(0, LINE_BOTTOM), (0, LINE_TOP), (ADVANCE, MIDDLE)])


def thin_separator():
    """: the same triangle's right-hand sides as a light stroke, cut off at the cell's left
    edge, so its ends reach the line box's top and bottom."""
    run, rise = ADVANCE, MIDDLE - LINE_BOTTOM
    # The stroke's thickness measured horizontally: what moves the outer edge onto the inner.
    inset = LIGHT * math.hypot(run, rise) / rise
    return geo.cleanup(polygon([(0, LINE_BOTTOM), (0, LINE_BOTTOM + inset * rise / run),
                                (ADVANCE - inset, MIDDLE), (0, LINE_TOP - inset * rise / run),
                                (0, LINE_TOP), (ADVANCE, MIDDLE)]))


def branch():
    """: a trunk between two dots, and a branch that leaves it and bends up into a third."""
    trunk = geo.rect(TRUNK_X - LIGHT // 2, TRUNK_BOTTOM, TRUNK_X + LIGHT // 2, TRUNK_TOP)
    fork = fontforge.contour()
    fork.moveTo(TRUNK_X, FORK_Y)
    fork.cubicTo((TRUNK_X, FORK_Y + 300), (BRANCH_X, BRANCH_DOT_Y - 380),
                 (BRANCH_X, BRANCH_DOT_Y - DOT))
    dots = (circle(TRUNK_X, TRUNK_TOP, DOT), circle(TRUNK_X, TRUNK_BOTTOM, DOT),
            circle(BRANCH_X, BRANCH_DOT_Y, DOT))
    return geo.cleanup(geo.union(trunk, stroked(fork), *dots))


def letter(font, name, scale, bottom):
    """The letter's outline scaled, centred in the cell, its lowest point at `bottom`."""
    layer = geo.transformed(font[name].foreground, psMat.scale(scale))
    x0, y0, x1, _ = layer.boundingBox()
    return geo.transformed(layer, psMat.translate(ADVANCE / 2 - (x0 + x1) / 2, bottom - y0))


def line_number(font):
    """: L over N, each the letter at LETTER_SCALE, N on the line box's bottom inset."""
    n = letter(font, "N", LETTER_SCALE, LINE_BOTTOM + INSET)
    l = letter(font, "L", LETTER_SCALE, n.boundingBox()[3] + LETTER_GAP)
    out = fontforge.layer()
    out += n.dup()
    out += l.dup()
    return geo.cleanup(out)


def padlock():
    """: a rounded body with a keyhole, and a shackle whose legs run into the body."""
    x0, y0, x1, y1 = BODY
    cx = ADVANCE / 2
    ring = circle(cx, y1, SHACKLE_RADIUS)
    ring += holes(circle(cx, y1, SHACKLE_RADIUS - LIGHT))[0]
    shackle = geo.trim(ring, y0=y1 - SHACKLE_LEGS)
    solid = geo.union(rounded_rect(x0, y0, x1, y1, CORNER), shackle)
    keyhole = geo.union(circle(cx, KEYHOLE_Y, KEYHOLE_RADIUS),
                        geo.rect(cx - SLOT_WIDTH / 2, SLOT_BOTTOM, cx + SLOT_WIDTH / 2, KEYHOLE_Y))
    solid += holes(keyhole)
    return geo.cleanup(solid)


def build(font):
    """Every symbol: code point -> outline layer."""
    right_solid, right_thin = solid_separator(), thin_separator()
    return {BRANCH: branch(), LINE_NUMBER: line_number(font), PADLOCK: padlock(),
            RIGHT_SOLID: right_solid, RIGHT_THIN: right_thin,
            LEFT_SOLID: geo.mirrored_x(right_solid, ADVANCE / 2),
            LEFT_THIN: geo.mirrored_x(right_thin, ADVANCE / 2)}


def add_glyphs(font, outlines):
    for code, layer in outlines.items():
        glyph = font[code] if code in font else font.createChar(code, f"uni{code:04X}")
        glyph.references = ()
        glyph.foreground = layer
        glyph.correctDirection()
        glyph.width = ADVANCE
        glyph.autoHint()


def check(path):
    """Exit non-zero if a symbol in the SFD at `path` fails validate()."""
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
    add_glyphs(font, build(font))
    save_checked(font, sfd, __file__)


if __name__ == "__main__":
    main()
