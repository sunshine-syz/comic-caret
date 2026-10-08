"""Draw the Powerline symbols U+E0A0–U+E0A2 and U+E0B0–U+E0B3 into the SFD.

Usage: python3 tools/add_powerline.py [SFD]

The separators fill the line box, so a prompt's coloured segments meet them without a seam. The
solid ones run past their flat side into the segment's cell, so a grid that rounds the cell up
to whole pixels leaves no light column there; the thin ones are the box drawing's light stroke.
The branch, line-number and padlock symbols are built from that stroke, round dots and the
font's own L and N. The script owns the seven glyphs and redraws them in place, so running it
again changes nothing but ModificationTime. The Nerd Fonts patcher keeps them because build.sh
passes --careful.
"""
import argparse
import math
import pathlib
import sys

import fontforge
import psMat

import lig_geometry as geo
from add_box_drawing import LIGHT
from project import ADVANCE, CELL_REACH, LINE_BOTTOM, LINE_TOP, SFD, save_checked, validation_errors

BRANCH, LINE_NUMBER, PADLOCK = 0xE0A0, 0xE0A1, 0xE0A2
RIGHT_SOLID, RIGHT_THIN, LEFT_SOLID, LEFT_THIN = 0xE0B0, 0xE0B1, 0xE0B2, 0xE0B3
CODES = (BRANCH, LINE_NUMBER, PADLOCK, RIGHT_SOLID, RIGHT_THIN, LEFT_SOLID, LEFT_THIN)

MIDDLE = (LINE_BOTTOM + LINE_TOP) // 2  # the separators' tip: the middle of the line box

# The measurements below are Fira Code's and Maple Mono's, scaled to our cell and cap height.

# The branch: a trunk with a dot at each end, and a branch curving off it up to a third dot.
# The references draw no dots: a stroke from the bottom bends right into an arrow, beside a
# stub at the top left. Our two strokes stand 300 apart, Fira Code's 350 and Maple Mono's 280.
TRUNK_X, BRANCH_X = ADVANCE // 2 - 150, ADVANCE // 2 + 150
# How far the branch keeps inside the line box, top and bottom. Fira Code's fills it; Maple
# Mono's keeps 27 below and 45 above.
BRANCH_INSET = 30
DOT = 80  # the dots' radius: 160 across, a little more than the period's 152 by 145
TRUNK_BOTTOM = LINE_BOTTOM + BRANCH_INSET + DOT  # the trunk's dots' centres
TRUNK_TOP = LINE_TOP - BRANCH_INSET - DOT
# The third dot's top, at 680, lies between the arrow tips: Fira Code's 663, Maple Mono's 714.
BRANCH_DOT_Y = 600
# Where the branch's centre line leaves the trunk. Its ink parts from the trunk's at 110, where
# Maple Mono's stroke bends off (107); Fira Code's bends off lower, at -38.
FORK_Y = 70
# The fork's two handles stand upright, so the branch leaves the trunk and meets the third dot
# upright. Each is this share of the fork's rise, so the S keeps its shape wherever it forks.
FORK_HANDLE = 300 / 370

# The line-number symbol: L over N, the font's own letters made small. Ours are 0.79 of our
# letters and stand 54 apart; Fira Code's are 0.58 of its own and Maple Mono's 0.80, and
# theirs stand 56 and 52 apart.
LETTER_SCALE = 0.79
LETTER_GAP = 54
# How far N's foot stands above the line box's bottom: Fira Code's 243, Maple Mono's 38. L's
# top then stands 83 under the line box's top: Fira Code's 89, Maple Mono's 25.
LINE_NUMBER_INSET = 50

# The padlock: a rounded body with a keyhole, under a shackle of the light stroke. It is Maple
# Mono's size, 500 wide and 862 tall, to Fira Code's 598 by 829. Its body is 500 by 500, to
# Fira Code's 598 by 481, and its parts are compared as shares of the body.
BODY = (ADVANCE // 2 - 250, -72, ADVANCE // 2 + 250, 428)  # x0, y0, x1, y1
CORNER = 60  # Maple Mono's 60, 0.12 of the body's width; Fira Code's is 0.19
# The radius of the shackle's outer edge, half its width: Maple Mono's 180, Fira Code's 141.
# The shackle spans 0.72 of the body's width, as Maple Mono's (Fira Code's 0.47). Its top is
# Maple Mono's 790 (Fira Code's 776).
SHACKLE_RADIUS, SHACKLE_TOP = 180, 790
# The legs rise straight from the body to the half circle's centre, 182 above the body; the
# references' rise 224 and 208 under flatter arcs. This is how far they run on into the body,
# out of sight, so the two join as one outline.
SHACKLE_LEGS = 70
# The keyhole's centre at 0.64 of the body's height, between Fira Code's 0.60 and Maple Mono's
# 0.67. It is 150 across, 0.30 of the body's width, between Fira Code's 148 (0.25) and Maple
# Mono's 200 (0.40). Fira Code draws its keyhole in ink inside an outlined body.
KEYHOLE_Y, KEYHOLE_RADIUS = 248, 75
# The slot is 70 wide, 0.14 of the body's width, between Fira Code's 0.13 and Maple Mono's 0.18
# (76 and 89 wide). Its foot is Fira Code's, at 0.26 of the body's height; Maple Mono's is 0.23.
SLOT_WIDTH, SLOT_BOTTOM = 70, 58


def rounded_rect(x0, y0, x1, y1, r):
    """A clockwise rectangle with quarter-circle corners of radius r, as a layer."""
    k = geo.KAPPA * r
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


def solid_separator():
    """: a triangle from the cell's left edge to a point on its right edge, filling the line
    box. Its flat side runs on CELL_REACH into the cell before it, the segment it ends."""
    return geo.polygon([(-CELL_REACH, LINE_BOTTOM), (-CELL_REACH, LINE_TOP), (0, LINE_TOP),
                        (ADVANCE, MIDDLE), (0, LINE_BOTTOM)])


def thin_separator():
    """: the same triangle's right-hand sides as a light stroke, cut off at the cell's left
    edge, so its ends reach the line box's top and bottom."""
    run, rise = ADVANCE, MIDDLE - LINE_BOTTOM
    # The stroke's thickness measured horizontally: what moves the outer edge onto the inner.
    inset = LIGHT * math.hypot(run, rise) / rise
    return geo.cleanup(geo.polygon([(0, LINE_BOTTOM), (0, LINE_BOTTOM + inset * rise / run),
                                    (ADVANCE - inset, MIDDLE), (0, LINE_TOP - inset * rise / run),
                                    (0, LINE_TOP), (ADVANCE, MIDDLE)]))


def branch():
    """: a trunk between two dots, and a branch that leaves it and bends up into a third."""
    trunk = geo.rect(TRUNK_X - LIGHT // 2, TRUNK_BOTTOM, TRUNK_X + LIGHT // 2, TRUNK_TOP)
    end_y = BRANCH_DOT_Y - DOT
    handle = FORK_HANDLE * (end_y - FORK_Y)
    fork = fontforge.contour()
    fork.moveTo(TRUNK_X, FORK_Y)
    fork.cubicTo((TRUNK_X, FORK_Y + handle), (BRANCH_X, end_y - handle), (BRANCH_X, end_y))
    dots = (geo.circle(TRUNK_X, TRUNK_TOP, DOT), geo.circle(TRUNK_X, TRUNK_BOTTOM, DOT),
            geo.circle(BRANCH_X, BRANCH_DOT_Y, DOT))
    return geo.cleanup(geo.union(trunk, geo.stroked(fork, LIGHT), *dots))


def letter(font, name, scale, bottom):
    """The letter's outline scaled, centred in the cell, its lowest point at `bottom`."""
    layer = geo.transformed(font[name].foreground, psMat.scale(scale))
    x0, y0, x1, _ = layer.boundingBox()
    return geo.transformed(layer, psMat.translate(ADVANCE / 2 - (x0 + x1) / 2, bottom - y0))


def line_number(font):
    """: L over N, each the letter at LETTER_SCALE, N's foot LINE_NUMBER_INSET above the line
    box's bottom."""
    below = letter(font, "N", LETTER_SCALE, LINE_BOTTOM + LINE_NUMBER_INSET)
    above = letter(font, "L", LETTER_SCALE, below.boundingBox()[3] + LETTER_GAP)
    out = fontforge.layer()
    out += below.dup()
    out += above.dup()
    return geo.cleanup(out)


def padlock():
    """: a rounded body with a keyhole, under a shackle whose legs rise from inside the body
    and turn over a half circle."""
    x0, y0, x1, y1 = BODY
    cx = ADVANCE / 2
    # The shackle's centre line, LIGHT / 2 inside its outer edge.
    r, cy = SHACKLE_RADIUS - LIGHT / 2, SHACKLE_TOP - SHACKLE_RADIUS
    k = geo.KAPPA * r
    shackle = fontforge.contour()
    shackle.moveTo(cx - r, y1 - SHACKLE_LEGS)
    shackle.lineTo(cx - r, cy)
    shackle.cubicTo((cx - r, cy + k), (cx - k, cy + r), (cx, cy + r))
    shackle.cubicTo((cx + k, cy + r), (cx + r, cy + k), (cx + r, cy))
    shackle.lineTo(cx + r, y1 - SHACKLE_LEGS)
    solid = geo.union(rounded_rect(x0, y0, x1, y1, CORNER), geo.stroked(shackle, LIGHT))
    keyhole = geo.union(geo.circle(cx, KEYHOLE_Y, KEYHOLE_RADIUS),
                        geo.rect(cx - SLOT_WIDTH / 2, SLOT_BOTTOM, cx + SLOT_WIDTH / 2, KEYHOLE_Y))
    solid += geo.holes(keyhole)
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
