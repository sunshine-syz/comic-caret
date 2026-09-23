"""Build Comic Caret's coding ligatures into the SFD: the glyphs, then src/ligatures.fea.

Usage: python3 tools/add_ligatures.py [--head-scale S] [SFD]

Replaces every glyph and GSUB lookup an earlier run made, so running it again changes nothing
but ModificationTime.
"""
import argparse
import math
import os
import pathlib
import re
import subprocess
import sys
from typing import NamedTuple

import fontforge
import psMat

import lig_geometry as geo
from lig_geometry import FAR

ROOT = pathlib.Path(__file__).resolve().parent.parent
SFD = ROOT / "src" / "ComicCaret-Regular.sfd"
FEA = ROOT / "src" / "ligatures.fea"

ADVANCE = 550
OVERLAP = 10     # how far joined strokes reach into the neighbouring cell
AXIS = 269       # math axis: the centre of - = + and of the arrow shafts
STRETCH = 600    # pushes a stroke's cap past any cut the pieces need
HEAD_SCALE = 1.1  # arrowheads relative to < >; chosen at the prototype checkpoint
HEAD_SCALES = (0.85, 1.15)  # beyond this, stroke weight drifts from the rest of the font

# The names of everything this script makes, and of nothing else in the font.
GENERATED = re.compile(r"LIG|colon\.eq|.+\.(sta|mid|end|mid\.low|end\.low|arrow|darrow"
                       r"|liga|tight_l|tight_r)")

VALIDATED = 0x1  # validate() sets this bit on every glyph it has checked


class Bar(NamedTuple):
    cuts: tuple     # x of the stretch lines, left and right, inside the bar's straight part
    band: tuple     # y range holding this bar, and nothing else, beyond the cuts
    profile: tuple  # canonical (bottom, top) that the bar's flat edges snap to


# Straight run strokes, one Bar per horizontal stroke.
RUNS = {
    "hyphen": (Bar((200, 350), (215, 325), (231, 310)),),
    "equal": (Bar((200, 350), (135, 228), (143, 219)), Bar((200, 350), (318, 410), (326, 403))),
}

# Arrowheads: the point of > and < sits on the axis at these x.
GREATER_TIP, LESS_TIP = 462, 88
SHAFT_INTO_HEAD = 80   # a - shaft ends this far inside the point, where the arms have met
BARS_INTO_HEAD = 162   # = bars end this far inside the point, within both arms

# != !==: the / at 95 %, centred on the bars.
SLASH_SCALE = 0.95
EQUAL_MIDDLE = 275     # stretch line through the middle of the = bars
EQUAL_PITCH = 326 - 143  # distance between the two = bars

# <= >=: the arms of < > turned flatter about the point and lengthened so their ends keep
# their height, widening the angle from 374 to 530 like the references' angles.
ANGLE_WIDTH_GAIN = 156
ARM_ENDS = {"greater": ((115, 510), (115, 28)),   # centres of the upper and lower end caps
            "less": ((435, 510), (435, 28))}
HYPHEN_SPAN = 210      # distance between the centres of the hyphen's two end caps
BAR_GAP = 140          # lower arm to bar, centre to centre: a stroke plus our ≤'s 60 gap

COLON_LIFT = 38        # raises the colon's centre (234) to the = centre (272)


def outline(font, name):
    return font[name].foreground.dup()


def stroke(font, name, x0=None, x1=None):
    """A run character cut flat at x0 and x1, where None keeps that end's cap.

    Each bar is first stretched past both cuts, so any x0 < x1 works.
    """
    layer = outline(font, name)
    bars = RUNS[name]
    for bar in bars:
        if x0 is not None:
            layer = geo.stretch(layer, bar.cuts[0], -STRETCH, bar.band)
        if x1 is not None:
            layer = geo.stretch(layer, bar.cuts[1], STRETCH, bar.band)
    layer = geo.trim(layer, -FAR if x0 is None else x0, FAR if x1 is None else x1)
    profile = [y for bar in bars for y in bar.profile]
    for x in (x0, x1):
        if x is not None:
            geo.snap_edge(layer, x, profile)
    return layer


def run_pieces(font):
    glyphs = {}
    for name in RUNS:
        glyphs[f"{name}.sta"] = stroke(font, name, x1=ADVANCE + OVERLAP)
        glyphs[f"{name}.mid"] = stroke(font, name, -OVERLAP, ADVANCE + OVERLAP)
        glyphs[f"{name}.end"] = stroke(font, name, x0=-OVERLAP)
    return glyphs


def head(font, name, tip, scale):
    return geo.transformed(outline(font, name), geo.about(psMat.scale(scale), tip, AXIS))


def arrowheads(font, scale):
    right, left = GREATER_TIP, LESS_TIP
    return {
        "less.arrow": geo.union(head(font, "less", left, scale),
                                stroke(font, "hyphen", left + SHAFT_INTO_HEAD, ADVANCE + OVERLAP)),
        "greater.arrow": geo.union(head(font, "greater", right, scale),
                                   stroke(font, "hyphen", -OVERLAP, right - SHAFT_INTO_HEAD)),
        "less.darrow": geo.union(head(font, "less", left, scale),
                                 stroke(font, "equal", left + BARS_INTO_HEAD, ADVANCE + OVERLAP)),
        "greater.darrow": geo.union(head(font, "greater", right, scale),
                                    stroke(font, "equal", -OVERLAP, right - BARS_INTO_HEAD)),
    }


def not_equal(font, cells):
    """!= over two cells or !== over three: = bars across all of them (three bars for !==, as
    in both references) and a / centred on the span."""
    span = ADVANCE * (cells - 1)
    bars = geo.transformed(geo.stretch(outline(font, "equal"), EQUAL_MIDDLE, span),
                           psMat.translate(-span, 0))
    if cells == 3:
        third = geo.transformed(geo.trim(bars, y1=AXIS), psMat.translate(0, -EQUAL_PITCH))
        bars = geo.transformed(geo.union(bars, third), psMat.translate(0, EQUAL_PITCH / 2))
    slash = outline(font, "slash")
    sx0, sy0, sx1, sy1 = slash.boundingBox()
    _, by0, _, by1 = bars.boundingBox()
    centre = ((ADVANCE - span) / 2, (by0 + by1) / 2)
    slash = geo.transformed(slash, psMat.compose(
        geo.about(psMat.scale(SLASH_SCALE), (sx0 + sx1) / 2, (sy0 + sy1) / 2),
        psMat.translate(centre[0] - (sx0 + sx1) / 2, centre[1] - (sy0 + sy1) / 2)))
    return geo.union(bars, slash)


def flatter_angle(font, name, tip):
    """< or > with each arm turned flatter about the point and lengthened so its end keeps
    its height, which widens the angle by ANGLE_WIDTH_GAIN."""
    angle = outline(font, name)
    outward = -1 if name == "greater" else 1  # from the point toward the arm ends
    # Each half reaches 30 past the axis so the turned halves overlap instead of meeting at a
    # shallow crossing, which removeOverlap turns into a self-intersection.
    halves = (geo.trim(angle, y0=AXIS - 30), geo.trim(angle, y1=AXIS + 30))
    arms = []
    for (end_x, end_y), half in zip(ARM_ENDS[name], halves):
        dx, dy = end_x - tip, end_y - AXIS
        new_dx = dx + outward * ANGLE_WIDTH_GAIN
        old_direction, new_direction = math.atan2(dy, dx), math.atan2(dy, new_dx)
        gain = math.hypot(new_dx, dy) - math.hypot(dx, dy)
        # Lay the arm along +x from the point, lengthen its far half, then turn it into place.
        flat = geo.transformed(half, geo.about(psMat.rotate(-old_direction), tip, AXIS))
        flat = geo.stretch(flat, tip + 150, gain)
        arms.append(geo.transformed(flat, geo.about(psMat.rotate(new_direction), tip, AXIS)))
    return geo.union(*arms)


def or_equal(font, name, tip):
    """<= or >= as ⩽ ⩾: the flatter angle with a bar under its lower arm, centred on the
    boundary between the two cells. The point stays on the axis, level with < >."""
    outward = -1 if name == "greater" else 1
    end_x, end_y = ARM_ENDS[name][1]
    far = (end_x + outward * ANGLE_WIDTH_GAIN, end_y)
    direction = math.atan2(far[1] - AXIS, far[0] - tip)
    length = math.hypot(far[0] - tip, far[1] - AXIS)
    bar = geo.stretch(outline(font, "hyphen"), 275, length - HYPHEN_SPAN - 20)
    x0, y0, x1, y1 = bar.boundingBox()
    drop = BAR_GAP / abs(math.cos(direction))
    bar = geo.transformed(bar, psMat.compose(
        psMat.compose(psMat.translate(-(x0 + x1) / 2, -(y0 + y1) / 2), psMat.rotate(direction)),
        psMat.translate((tip + far[0]) / 2, (AXIS + far[1]) / 2 - drop)))
    symbol = geo.union(flatter_angle(font, name, tip), bar)
    x0, _, x1, _ = symbol.boundingBox()
    return geo.transformed(symbol, psMat.translate(-(x0 + x1) / 2, 0))


def build(font, head_scale=HEAD_SCALE):
    """Every generated glyph in SFD order: name -> outline layer, or a list of
    (glyph, dx, dy) references for pure shifts."""
    glyphs = {"LIG": []}  # the empty spacer before a .liga glyph
    glyphs.update(run_pieces(font))
    glyphs.update(arrowheads(font, head_scale))
    glyphs["exclam_equal.liga"] = not_equal(font, 2)
    glyphs["exclam_equal_equal.liga"] = not_equal(font, 3)
    glyphs["colon.eq"] = [("colon", 0, COLON_LIFT)]
    glyphs["less_equal.liga"] = or_equal(font, "less", LESS_TIP)
    glyphs["greater_equal.liga"] = or_equal(font, "greater", GREATER_TIP)
    return glyphs


def remove_previous(font):
    # Chain lookups call the single substitutions, so remove them first.
    for lookup in reversed(font.gsub_lookups):
        if lookup.startswith("lig_"):
            font.removeLookup(lookup)
    for name in [g.glyphname for g in font.glyphs() if GENERATED.fullmatch(g.glyphname)]:
        font.removeGlyph(name)
    # Removed glyphs keep their encoding slots; re-encoding frees them, so a rerun puts the
    # new glyphs in the same slots.
    font.encoding = "UnicodeBmp"


def add_glyphs(font, glyphs):
    for name, shape in glyphs.items():
        glyph = font.createChar(-1, name)
        glyph.width = ADVANCE
        if isinstance(shape, list):
            for base, dx, dy in shape:
                glyph.addReference(base, psMat.translate(dx, dy))
        else:
            glyph.foreground = geo.cleanup(shape)
            glyph.correctDirection()
        glyph.autoHint()


def merge_features(font):
    font.mergeFeature(str(FEA))
    # On a parse error FontForge prints to stderr and merges nothing, so check the result.
    declared = re.findall(r"^\s*lookup\s+(lig_\w+)\s*\{", FEA.read_text(), re.M)
    missing = sorted(set(declared) - set(font.gsub_lookups))
    if missing:
        sys.exit(f"{FEA.name} did not merge; missing lookups: {', '.join(missing)}")


def check(path):
    """Exit non-zero if a generated glyph in the SFD at `path` fails validate()."""
    font = fontforge.open(str(path))
    failed = {}
    for glyph in font.glyphs():
        if GENERATED.fullmatch(glyph.glyphname):
            flags = glyph.validate(True) & ~VALIDATED
            if flags:
                failed[glyph.glyphname] = hex(flags)
    if failed:
        sys.exit(f"validate() failed: {failed}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("sfd", nargs="?", default=str(SFD), help="default: %(default)s")
    parser.add_argument("--head-scale", type=float, default=HEAD_SCALE,
                        help="arrowhead size relative to < > (default %(default)s)")
    parser.add_argument("--check", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.check:
        return check(args.sfd)
    if not HEAD_SCALES[0] <= args.head_scale <= HEAD_SCALES[1]:
        parser.error(f"--head-scale must be within {HEAD_SCALES[0]}..{HEAD_SCALES[1]}")

    sfd = pathlib.Path(args.sfd)
    font = fontforge.open(str(sfd))
    remove_previous(font)
    add_glyphs(font, build(font, args.head_scale))
    merge_features(font)
    # Validating in this process would write "Validated:" into the saved glyphs, so a fresh
    # process checks the saved copy before it replaces the SFD.
    tmp = sfd.with_name(f".{sfd.name}.tmp")
    font.save(str(tmp))
    if subprocess.run([sys.executable, __file__, "--check", str(tmp)]).returncode:
        tmp.unlink()
        sys.exit(f"{sfd} is unchanged.")
    os.replace(tmp, sfd)

if __name__ == "__main__":
    main()
