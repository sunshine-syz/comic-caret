"""Build Comic Caret's coding ligatures into the SFD: the glyphs, then src/ligatures.fea.

Usage: python3 tools/add_ligatures.py [SFD]

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
from project import ADVANCE, ROOT, SFD, validation_errors

FEA = ROOT / "src" / "ligatures.fea"

OVERLAP = 10     # how far joined strokes reach into the neighbouring cell
AXIS = 269       # math axis: the centre of - = + and of the arrow shafts
STRETCH = 600    # pushes a stroke's cap past any cut the pieces need
HEAD_SCALE = 1.1  # arrowheads relative to < >, as large as the references' heads

# The names of everything this script makes, and of nothing else in the font.
GENERATED = re.compile(r"LIG|colon\.eq|.+\.(sta|mid|end|mid\.low|end\.low|arrow|darrow"
                       r"|liga|tight_l|tight_r)")


class Bar(NamedTuple):
    cuts: tuple     # x of the stretch lines, left and right, inside the bar's straight part
    band: tuple     # y range holding this bar, and nothing else, beyond the cuts
    profile: tuple  # canonical (bottom, top) that the bar's flat edges snap to


# Straight run strokes, one Bar per horizontal stroke.
RUNS = {
    "hyphen": (Bar((200, 350), (215, 325), (231, 310)),),
    "equal": (Bar((200, 350), (135, 228), (143, 219)), Bar((200, 350), (318, 410), (326, 403))),
    "underscore": (Bar((200, 350), (-100, -5), (-92, -14)),),
    # The crossbars stick out past the slanted verticals, each by a different amount.
    "numbersign": (Bar((100, 440), (170, 262), (178, 255)),
                   Bar((150, 465), (408, 502), (415, 494))),
}

# ~ is a wave: a fall from crest to trough and its mirror image, each 174 wide, repeat. Three
# fill a cell, so a cell ends at the other extreme from where it began and the pieces
# alternate between starting low (.sta, .mid.low, .end.low) and high (.mid, .end).
TILDE_CREST, TILDE_TROUGH = 182, 356
TILDE_HALF = TILDE_TROUGH - TILDE_CREST
CREST_PROFILE, TROUGH_PROFILE = (295, 394), (145, 243)
TILDE_MIDDLE = (TROUGH_PROFILE[0] + CREST_PROFILE[1]) / 2  # mirroring about it swaps the two

# The point of > and < sits on the axis at these x, and their arms run from it this way.
TIP = {"greater": 462, "less": 88}
OUTWARD = {"greater": -1, "less": 1}
SHAFT_INTO_HEAD = 80   # a - shaft ends this far inside the point, where the arms have met
BARS_INTO_HEAD = 162   # = bars end this far inside the point, within both arms
ARM_SPAN = (150, 330)  # along an arm from the point: straight, clear of the join and cap

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

# |> <|: the head 115 % the size of > <, its arm ends over the round ends of a bar as tall
# as the head, so each corner turns as one round stroke end.
PIPE_HEAD_SCALE = 1.15
PIPE_BAR_EDGE = {"greater": 270 - ADVANCE, "less": 830 - ADVANCE}  # references' outer edge
BAR_SPAN = (0, 600)    # heights of |'s straight part, clear of its round ends

COLON_LIFT = 38        # raises the colon's centre (234) to the = centre (272)

# How far each glyph moves toward its partner in a tightened pair.
TIGHT = {"colon": 92, "period": 92, "ampersand": 37, "plus": 56, "slash": 65, "asterisk": 45,
         "less": 40, "greater": 40, "question": 60, "bar": 100}


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
    layer = geo.trim(layer, -geo.FAR if x0 is None else x0, geo.FAR if x1 is None else x1)
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


def tilde_pieces(font):
    tilde = outline(font, "asciitilde")
    fall = geo.snap_edge(geo.snap_edge(geo.trim(tilde, TILDE_CREST, TILDE_TROUGH),
                                       TILDE_CREST, CREST_PROFILE), TILDE_TROUGH, TROUGH_PROFILE)
    rise = geo.mirrored_x(fall, TILDE_TROUGH)
    rise_before = geo.transformed(rise, psMat.translate(-2 * TILDE_HALF, 0))
    start = geo.snap_edge(geo.trim(tilde, x1=TILDE_CREST), TILDE_CREST, CREST_PROFILE)
    finish = geo.snap_edge(geo.trim(tilde, x0=TILDE_TROUGH), TILDE_TROUGH, TROUGH_PROFILE)
    first, last = TILDE_CREST - TILDE_HALF, TILDE_TROUGH + TILDE_HALF  # the outer extremes

    def to_edge(layer, x, edge, profile):
        # The wave is level at an extreme, so moving the flat end out keeps it level.
        moved = geo.stretch(layer, x - 1 if edge > x else x + 1, edge - x)
        return geo.snap_edge(moved, edge, profile)

    def waves(head, tail):
        return geo.weld(geo.weld(head, fall, TILDE_CREST), tail, TILDE_TROUGH)

    sta = to_edge(waves(start, rise), last, ADVANCE + OVERLAP, CREST_PROFILE)
    mid_low = to_edge(to_edge(waves(rise_before, rise), first, -OVERLAP, TROUGH_PROFILE),
                      last, ADVANCE + OVERLAP, CREST_PROFILE)
    end_low = to_edge(waves(rise_before, finish), first, -OVERLAP, TROUGH_PROFILE)
    mid = geo.mirrored_y(mid_low, TILDE_MIDDLE)
    mid = geo.snap_edge(geo.snap_edge(mid, -OVERLAP, CREST_PROFILE),
                        ADVANCE + OVERLAP, TROUGH_PROFILE)
    end = geo.snap_edge(geo.mirrored_y(end_low, TILDE_MIDDLE), -OVERLAP, CREST_PROFILE)
    return {"asciitilde.sta": sta, "asciitilde.mid": mid, "asciitilde.end": end,
            "asciitilde.mid.low": mid_low, "asciitilde.end.low": end_low}


def arm_halves(font, name):
    """< or > split at the axis into its upper and lower arm."""
    angle = outline(font, name)
    # Each half reaches 30 past the axis so reshaped halves overlap instead of meeting at a
    # shallow crossing, which removeOverlap turns into a self-intersection.
    return geo.trim(angle, y0=AXIS - 30), geo.trim(angle, y1=AXIS + 30)


def middle_at(layer, y):
    """The middle of the stroke that the horizontal line at y crosses."""
    x0, _, x1, _ = geo.trim(layer, y0=y - 1, y1=y + 1).boundingBox()
    return (x0 + x1) / 2, y


def turned(layer, name, angle):
    """`layer` rotated by `angle` about the point of < or >."""
    return geo.transformed(layer, geo.about(psMat.rotate(angle), TIP[name], AXIS))


def longer_angle(font, name, scale):
    """< or > with its arm ends `scale` times as high above and below the axis. Unlike scaling
    the glyph, lengthening the arms keeps their stroke weight."""
    tip = TIP[name]
    arms = []
    for (_, end_y), half in zip(ARM_ENDS[name], arm_halves(font, name), strict=True):
        # The arms are drawn by hand, so the point-to-end line misses their axis by up to 5°;
        # stretching along it would skew them. Take the axis through two cross-sections, on
        # the straight part between the point and the end cap.
        rise = end_y - AXIS
        (x0, y0), (x1, y1) = middle_at(half, AXIS + 0.3 * rise), middle_at(half, AXIS + 0.65 * rise)
        direction = math.atan2(y1 - y0, x1 - x0)
        gain = (scale - 1) * rise / math.sin(direction)
        # Lay the arm along +x from the point, lengthen its straight part, then turn it back.
        flat = geo.stretch_span(turned(half, name, -direction),
                                tip + ARM_SPAN[0], tip + ARM_SPAN[1], gain)
        arms.append(turned(flat, name, direction))
    return geo.union(*arms)


def arrowheads(font):
    def head(name, shaft, x0, x1):
        return geo.union(longer_angle(font, name, HEAD_SCALE), stroke(font, shaft, x0, x1))

    left, right = TIP["less"], TIP["greater"]
    return {
        "less.arrow": head("less", "hyphen", left + SHAFT_INTO_HEAD, ADVANCE + OVERLAP),
        "greater.arrow": head("greater", "hyphen", -OVERLAP, right - SHAFT_INTO_HEAD),
        "less.darrow": head("less", "equal", left + BARS_INTO_HEAD, ADVANCE + OVERLAP),
        "greater.darrow": head("greater", "equal", -OVERLAP, right - BARS_INTO_HEAD),
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


def flatter_angle(font, name):
    """< or > with each arm turned flatter about the point and lengthened so its end keeps
    its height, which widens the angle by ANGLE_WIDTH_GAIN."""
    tip = TIP[name]
    arms = []
    for (end_x, end_y), half in zip(ARM_ENDS[name], arm_halves(font, name), strict=True):
        dx, dy = end_x - tip, end_y - AXIS
        new_dx = dx + OUTWARD[name] * ANGLE_WIDTH_GAIN
        old_direction, new_direction = math.atan2(dy, dx), math.atan2(dy, new_dx)
        gain = math.hypot(new_dx, dy) - math.hypot(dx, dy)
        # Lay the arm along +x from the point, lengthen its far half, then turn it into place.
        flat = geo.stretch(turned(half, name, -old_direction), tip + ARM_SPAN[0], gain)
        arms.append(turned(flat, name, new_direction))
    return geo.union(*arms)


def or_equal(font, name):
    """<= or >= as ⩽ ⩾: the flatter angle with a bar under its lower arm, centred on the
    boundary between the two cells. The point stays on the axis, level with < >."""
    tip = TIP[name]
    end_x, end_y = ARM_ENDS[name][1]
    far = (end_x + OUTWARD[name] * ANGLE_WIDTH_GAIN, end_y)
    direction = math.atan2(far[1] - AXIS, far[0] - tip)
    length = math.hypot(far[0] - tip, far[1] - AXIS)
    bar = geo.stretch(outline(font, "hyphen"), 275, length - HYPHEN_SPAN - 20)
    x0, y0, x1, y1 = bar.boundingBox()
    drop = BAR_GAP / abs(math.cos(direction))
    bar = geo.transformed(bar, psMat.compose(
        psMat.compose(psMat.translate(-(x0 + x1) / 2, -(y0 + y1) / 2), psMat.rotate(direction)),
        psMat.translate((tip + far[0]) / 2, (AXIS + far[1]) / 2 - drop)))
    symbol = geo.union(flatter_angle(font, name), bar)
    x0, _, x1, _ = symbol.boundingBox()
    return geo.transformed(symbol, psMat.translate(-(x0 + x1) / 2, 0))


def squeezed_bar(font, height):
    """| shortened to `height` along its straight middle, so it keeps its round ends."""
    bar = outline(font, "bar")
    _, y0, _, y1 = bar.boundingBox()
    # stretch_span works along x, so lay the bar on its side and stand it up again.
    lying = geo.transformed(bar, psMat.rotate(-math.pi / 2))
    lying = geo.stretch_span(lying, *BAR_SPAN, height - (y1 - y0))
    return geo.transformed(lying, psMat.rotate(math.pi / 2))


def pipe(font, name):
    """|> or <| as a triangle: the enlarged head closed by a bar as tall as it."""
    arrow = longer_angle(font, name, PIPE_HEAD_SCALE)
    hx0, hy0, hx1, hy1 = arrow.boundingBox()
    bar = squeezed_bar(font, hy1 - hy0)
    bx0, by0, bx1, _ = bar.boundingBox()
    # The bar's outer edge goes where the references put it, and the arm ends' outer edge
    # onto it; arm and bar are about equally heavy, so their round ends then coincide.
    edge = PIPE_BAR_EDGE[name]
    outer = bx0 if name == "greater" else bx1  # |> has its bar on the left, <| on the right
    bar = geo.transformed(bar, psMat.translate(edge - outer, hy0 - by0))
    arrow = geo.transformed(arrow, psMat.translate(edge - (hx0 if name == "greater" else hx1), 0))
    return geo.union(bar, arrow)


def build(font):
    """Every generated glyph in SFD order: name -> outline layer, or a list of
    (glyph, dx, dy) references for pure shifts."""
    glyphs = {"LIG": []}  # the empty spacer before a .liga glyph
    glyphs.update(run_pieces(font))
    glyphs.update(tilde_pieces(font))
    glyphs.update(arrowheads(font))
    glyphs["exclam_equal.liga"] = not_equal(font, 2)
    glyphs["exclam_equal_equal.liga"] = not_equal(font, 3)
    glyphs["colon.eq"] = [("colon", 0, COLON_LIFT)]
    glyphs["less_equal.liga"] = or_equal(font, "less")
    glyphs["greater_equal.liga"] = or_equal(font, "greater")
    glyphs["bar_greater.liga"] = pipe(font, "greater")
    glyphs["less_bar.liga"] = pipe(font, "less")
    for name, shift in TIGHT.items():
        glyphs[f"{name}.tight_r"] = [(name, shift, 0)]
        glyphs[f"{name}.tight_l"] = [(name, -shift, 0)]
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
    declared = re.findall(r"^\s*lookup\s+(lig_\w+)\s*\{", FEA.read_text(), re.MULTILINE)
    missing = sorted(set(declared) - set(font.gsub_lookups))
    if missing:
        sys.exit(f"{FEA.name} did not merge; missing lookups: {', '.join(missing)}")


def check(path):
    """Exit non-zero if a generated glyph in the SFD at `path` fails validate()."""
    font = fontforge.open(str(path))
    failed = {glyph.glyphname: hex(flags) for glyph in font.glyphs()
              if GENERATED.fullmatch(glyph.glyphname) and (flags := validation_errors(glyph))}
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
    remove_previous(font)
    add_glyphs(font, build(font))
    merge_features(font)
    # Validating in this process would write "Validated:" into the saved glyphs, so a fresh
    # process checks the saved copy before it replaces the SFD.
    tmp = sfd.with_name(f".{sfd.name}.tmp")
    font.save(str(tmp))
    if subprocess.run([sys.executable, __file__, "--check", str(tmp)], check=False).returncode:
        tmp.unlink()
        sys.exit(f"{sfd} is unchanged.")
    os.replace(tmp, sfd)


if __name__ == "__main__":
    main()
