"""Build Comic Caret's coding ligatures into the SFD: the glyphs, then src/ligatures.fea.

Usage: python3 tools/add_ligatures.py [SFD]

Replaces every glyph and GSUB lookup an earlier run made (the glyphs GENERATED matches and the
lig_* lookups), and redraws ⎯ (U+23AF) as the `--` line's middle piece, so a row of them joins
into that line; running it again changes nothing but ModificationTime. Rerun it after adding
glyphs, since a new glyph lands after the generated ones. Its constants are measurements of
`- = _ # ~ < > | :`; after redrawing one of those, measure again until
tests/test_add_ligatures.py's MeasurementTest passes, then rerun it.
"""
import argparse
import math
import pathlib
import re
import sys
from typing import NamedTuple

import fontforge
import psMat

import lig_geometry as geo
from project import ADVANCE, AXIS, OVERLAP, ROOT, SFD, WOBBLE, save_checked, validation_errors

FEA = ROOT / "src" / "ligatures.fea"
LINE_EXTENSION = 0x23AF

STRETCH = 600    # pushes a stroke's cap past any cut the pieces need
# Arrowheads: < > with each arm turned this much steeper, to about Fira Code's slope, 46-50°
# from level, and reaching as high and low as → ←. The steeper arms end nearer the point, so
# → ← ⇒ ⇐, which carry these heads in one cell, keep a shaft.
HEAD_TURN = math.radians(14.4)

# The names of everything this script makes, and of nothing else in the font.
GENERATED = re.compile(r"LIG|colon\.eq|.+\.(sta|mid|end|mid\.low|end\.low|arrow|darrow"
                       r"|warrow|warrow\.low|dtail|twohead|shaft|comment|liga|tight_[lr]2?)")


class Bar(NamedTuple):
    cuts: tuple     # x of the stretch lines, left and right, inside the bar's straight part
    band: tuple     # y range holding this bar, and nothing else, beyond the cuts
    profile: tuple  # canonical (bottom, top) that the bar's flat edges snap to


# Straight run strokes, one Bar per horizontal stroke.
RUNS = {
    "hyphen": (Bar((225, 375), (215, 325), (231, 310)),),
    # ='s profile is ='s own hint edges, so the CFF hinter snaps the pieces' bars as it snaps
    # ='s. With the upper bar's middle 1.5 lower, at 8 px it rounded down onto the lower bar.
    "equal": (Bar((225, 375), (125, 218), (131, 208)), Bar((225, 375), (328, 420), (338, 414))),
    "underscore": (Bar((225, 375), (-115, -20), (-107, -29)),),
    # The crossbars stick out past the slanted verticals, each by a different amount.
    "numbersign": (Bar((125, 465), (170, 262), (178, 255)),
                   Bar((175, 490), (408, 502), (415, 494))),
}

# ~ is a wave: a fall from crest to trough and its mirror image repeat. In a run each is a
# third of the cell wide, so a cell ends at the other extreme from where it began and the
# pieces alternate between starting low (.sta, .mid.low, .end.low) and high (.mid, .end).
# The single ~ keeps its own fall, 174 wide.
TILDE_CREST, TILDE_TROUGH = 207, 381
TILDE_HALF = ADVANCE / 3
CREST_PROFILE, TROUGH_PROFILE = (292, 378), (161, 246)
TILDE_MIDDLE = (TROUGH_PROFILE[0] + CREST_PROFILE[1]) / 2  # mirroring about it swaps the two

# The point of > and < sits on the axis at these x, and their arms run from it this way.
TIP = {"greater": 513, "less": ADVANCE - 513}
OUTWARD = {"greater": -1, "less": 1}
SHAFT_INTO_HEAD = 80   # a - shaft ends this far inside the point, where the arms have met
BARS_INTO_HEAD = 120   # = bars end this far inside the point, within both arms
ARM_SPAN = (200, 370)  # along an arm from the point: straight, clear of the join and cap
HALF_REACH = 30        # how far past the axis each half of < > reaches (arm_halves)
# A flatter arm's turn eases in between these distances from the point of < or >: none within
# 60, which takes in the round point (55 from its tip), so the two arms keep it as drawn; all of
# it from 160, well short of the arm's end cap (430 away), so the cap stands at the height
# reaching() gave it.
POINT_EASE = (60, 160)

# != !==: the / at 83 %, centred on the bars: 726 tall, between Maple Mono's 662 and Fira
# Code's 786, with a stroke (70) near the bars' (75).
SLASH_SCALE = 0.83
EQUAL_MIDDLE = ADVANCE / 2  # stretch line through the middle of the = bars
EQUAL_PITCH = 338 - 131  # distance between the two = bars

# <= >=: the arms of < > turned flatter about the point and lengthened so their ends keep
# their height, widening the angle from 425 to 519, Fira Code's 1.10 x-heights.
ANGLE_WIDTH_GAIN = 94
# The centres of the round ends of >'s arms, upper then lower, as end_centre() measures them.
# The hand-drawn arms differ, so each has its own. < is > turned 180° about the middle of the
# cell on the axis, so its ends are these turned.
GREATER_ENDS = ((144, 490), (147, 63))
ARM_ENDS = {"greater": GREATER_ENDS,
            "less": tuple((ADVANCE - x, 2 * AXIS - y) for x, y in reversed(GREATER_ENDS))}
HYPHEN_SPAN = 281      # distance between the centres of the hyphen's two end caps
# <= >=: lower arm to bar, centre to centre. The bar runs along the arm, so the white between
# them is about this less a stroke all along: Maple Mono's 106 at our cap height, and 85 in
# the bold, where the pen takes 20 (Fira Code's are 141 and 121).
BAR_GAP = 196

# |> <|: the head with its arms lengthened until it is as tall as Fira Code's triangle, 1603
# of its 1053 x-height (JetBrains Mono's is 835 of 550), over the round ends of a bar as tall
# as the head. Both arms are >'s flatter one, mirrored about >'s point (pipe_head()), so both
# ends meet the bar's round ends and each corner turns as one round stroke end. That arm is
# turned steeper until the triangle's width over its height is the mean of Fira Code's, 1306
# over 1603, and JetBrains Mono's, 685 over 835. Unturned, it would be 1.29 x-heights wide,
# past both.
PIPE_HEIGHT = 1603 / 1053  # in x-heights
PIPE_ASPECT = (1306 / 1603 + 685 / 835) / 2  # width over height
# The bar's outer edge, in the head's cell: 295 into the bar's own cell from its outer side,
# 2 past Fira Code's 293.
PIPE_BAR_EDGE = {"greater": 295 - ADVANCE, "less": ADVANCE - 295}
BAR_SPAN = (0, 600)    # heights of |'s straight part, clear of its round ends

COLON_LIFT = 36        # raises the colon's centre (236) to the = centre (272)

# <>: each half's angle widened by this, so the diamond is as wide as the references' at the
# same x-height: 1.70 x-heights, between Maple Mono's 1.67 and Fira Code's 1.76.
DIAMOND_WIDTH_GAIN = 35

# The side bearing each glyph keeps toward its partner once moved, so the white between a pair
# stays when the cell or the glyph's width changes. & keeps 45 of white in &&, Maple Mono's
# (Fira Code joins its two), and ? 107 between the hooks of ??, Maple Mono's (Fira Code 104).
TIGHT_KEEP = {"colon": 107, "period": 107, "ampersand": 15, "plus": -5.5, "slash": -41.5,
              "asterisk": -4.5, "less": 54.5, "greater": 54.5, "question": 53, "bar": 131,
              "equal": 20.5}
# The outer glyphs of a tightened three beside a copy of themselves (/// ... &&& <<< >>> |||, and
# ..= ??= <<= >>= =<< ||= &&=): the middle glyph stays in place, so each moves twice a pair's
# shift and the three keeps its pair's white.
THREE_ENDS = {"tight_r2": ("slash", "period", "ampersand", "question", "less", "greater", "bar"),
              "tight_l2": ("slash", "period", "ampersand", "less", "greater", "bar")}

JOIN = 4  # how far a stroke reaches into the one it runs into, so they overlap, never just meet

# ->> <<-: the inner head sits this much closer to the shaft than the outer one. The white
# between the two, 171, goes with the heads' size, not the cell's: more than Fira Code's (145
# at our cell), the one reference that draws ->>. The inner head's crotch then lies inside its
# cell, clear of the shaft's cut end at the cell's edge; a pitch from 382 to 423 brings the
# crotch onto that end, which then shows in it. At 375 the inner head stands 6 nearer the
# cell's edge, and FreeType's hinting sets the piece's bar a pixel row off the next piece's at
# 8 to 35 px.
HEAD_PITCH = 369

# ~> <~: the wave ends here in the head's cell, where its crest (or trough) lies inside the
# upper (or lower) arm; for < mirrored, at ADVANCE - WAVE_END.
WAVE_END = 411
SPECK = 90  # the stem weight: a hole no wider than a stroke reads as a blot, not a counter


def outline(font, name):
    return font[name].foreground.dup()


def stroke(font, name, x0=None, x1=None):
    """A run character cut flat at x0 and x1, where None keeps that end's cap.

    Each bar is first stretched past both cuts, so any x0 < x1 works. A cut past the cell's
    edge is a seam, where the piece runs on into the next cell: its corners snap to the bar's
    profile, so the pieces meet at identical heights. A cut inside the cell lies inside another
    stroke and meets nothing, so it keeps the outline's height: snapped a unit past an outline
    point, its corner would hook the curve's end back along the cut.
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
        if x is not None and not 0 <= x <= ADVANCE:
            geo.snap_edge(layer, x, profile)
    return level(layer, profile)


def level(layer, profile, x0=-geo.FAR, x1=geo.FAR):
    """`layer` with every point between x0 and x1 within the hand's wobble of a height in
    `profile` moved onto it.

    FreeType's light autohinter hints each piece alone and rounds a bar by its whole edges, so
    a bar that strays from its profile, toward a cap or a head's point, lands a pixel row off
    the next piece's. Edits `layer` in place and returns it.
    """
    for contour in layer:
        for point in contour:
            nearest = min(profile, key=lambda y: abs(y - point.y))
            if abs(nearest - point.y) <= WOBBLE / 2 and x0 <= point.x <= x1:
                point.y = nearest
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
    # Spread across to TILDE_HALF about the crest: the flat edges keep their heights.
    fall = geo.transformed(fall, geo.about(
        psMat.scale(TILDE_HALF / (TILDE_TROUGH - TILDE_CREST), 1), TILDE_CREST, 0))
    trough = TILDE_CREST + TILDE_HALF  # where the run's fall ends
    rise = geo.mirrored_x(fall, trough)
    rise_before = geo.transformed(rise, psMat.translate(-2 * TILDE_HALF, 0))
    start = geo.snap_edge(geo.trim(tilde, x1=TILDE_CREST), TILDE_CREST, CREST_PROFILE)
    finish = geo.transformed(
        geo.snap_edge(geo.trim(tilde, x0=TILDE_TROUGH), TILDE_TROUGH, TROUGH_PROFILE),
        psMat.translate(trough - TILDE_TROUGH, 0))
    first, last = TILDE_CREST - TILDE_HALF, trough + TILDE_HALF  # the outer extremes

    def to_edge(layer, x, edge, profile):
        # The wave is level at an extreme, so moving the flat end out keeps it level.
        moved = geo.stretch(layer, x - 1 if edge > x else x + 1, edge - x)
        return geo.snap_edge(moved, edge, profile)

    def waves(head, tail):
        return geo.weld(geo.weld(head, fall, TILDE_CREST), tail, trough)

    sta = to_edge(waves(start, rise), last, ADVANCE + OVERLAP, CREST_PROFILE)
    mid_low = to_edge(to_edge(waves(rise_before, rise), first, -OVERLAP, TROUGH_PROFILE),
                      last, ADVANCE + OVERLAP, CREST_PROFILE)
    end_low = to_edge(waves(rise_before, finish), first, -OVERLAP, TROUGH_PROFILE)
    # Mirrored, a trough is a crest a unit thicker, as the profiles differ by one; each cut
    # edge moves back onto its profile with the level run leading to it, so the stroke meets
    # the seam level, as the piece across it does.
    mid = geo.mirrored_y(mid_low, TILDE_MIDDLE)
    mid = geo.snap_edge(geo.snap_edge(mid, -OVERLAP, CREST_PROFILE, level=True),
                        ADVANCE + OVERLAP, TROUGH_PROFILE, level=True)
    end = geo.snap_edge(geo.mirrored_y(end_low, TILDE_MIDDLE), -OVERLAP, CREST_PROFILE,
                        level=True)
    return {"asciitilde.sta": sta, "asciitilde.mid": mid, "asciitilde.end": end,
            "asciitilde.mid.low": mid_low, "asciitilde.end.low": end_low}


def arm_halves(font, name):
    """< or > split at the axis into its upper and lower arm."""
    angle = outline(font, name)
    # Each half reaches past the axis so reshaped halves overlap instead of meeting at a
    # shallow crossing, which removeOverlap turns into a self-intersection.
    return geo.trim(angle, y0=AXIS - HALF_REACH), geo.trim(angle, y1=AXIS + HALF_REACH)


def span_at(layer, y):
    """(x0, x1) of the stroke that the horizontal line at y crosses."""
    x0, _, x1, _ = geo.trim(layer, y0=y - 1, y1=y + 1).boundingBox()
    return x0, x1


def middle_at(layer, y):
    """The middle of the stroke that the horizontal line at y crosses."""
    return sum(span_at(layer, y)) / 2, y


def turned(layer, name, angle):
    """`layer` rotated by `angle` about the point of < or >."""
    return geo.transformed(layer, geo.about(psMat.rotate(angle), TIP[name], AXIS))


def reaching(flat, name, direction, goal):
    """The arm `flat`, laid along +x from the point of < or >, lengthened along its straight
    part so that, turned to `direction`, its ink reaches the height `goal`. The end cap moves
    along the arm, so its height changes by the gain times the sine."""
    tip = TIP[name]
    arm = turned(flat, name, direction)
    arm.addExtrema("all")  # else the box reaches to the control points
    _, low, _, high = arm.boundingBox()
    gain = (goal - (high if goal > AXIS else low)) / math.sin(direction)
    return geo.stretch_span(flat, tip + ARM_SPAN[0], tip + ARM_SPAN[1], gain)


def arm_axis(half, end_y):
    """(direction, heights): the direction of the arm `half` of < or >, whose end is at height
    end_y, and the two heights it is measured at. The arms are drawn by hand, so the
    point-to-end line misses their axis by up to 5°; stretching along it would skew them. The
    axis runs through two cross-sections, on the straight part between the point and the end
    cap."""
    rise = end_y - AXIS
    sections = AXIS + 0.3 * rise, AXIS + 0.65 * rise
    (x0, y0), (x1, y1) = (middle_at(half, y) for y in sections)
    return math.atan2(y1 - y0, x1 - x0), sections


def longer_angle(font, name, reach, steeper=0.0):
    """< or > with each arm turned `steeper` radians toward upright about the point and
    lengthened along its own line until its ink reaches `reach`, the (bottom, top) heights.
    Unlike scaling the glyph, lengthening and turning the arms keeps their stroke weight."""
    tip = TIP[name]
    inner = 0 if name == "greater" else 1  # which end of a span faces into the angle
    arms, inner_edges = [], []
    for (_, end_y), half, goal in zip(ARM_ENDS[name], arm_halves(font, name), reversed(reach),
                                      strict=True):
        direction, sections = arm_axis(half, end_y)
        # Upright is up for the upper arm and down for the lower, whichever way the point faces.
        toward_upright = math.copysign(1, math.cos(direction) * math.sin(direction))
        new_direction = direction + toward_upright * steeper
        # Lay the arm along +x from the point, lengthen it, then turn it into place.
        flat = reaching(turned(half, name, -direction), name, new_direction, goal)
        arms.append(turned(flat, name, new_direction))
        m = geo.about(psMat.rotate(new_direction - direction), tip, AXIS)
        inner_edges.append([(m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5])
                            for x, y in ((span_at(half, y)[inner], y) for y in sections)])
    angle = geo.union(*arms)
    return open_crotch(angle, name, *inner_edges) if steeper else angle


def open_crotch(angle, name, upper, lower):
    """`angle` cleared inside its point out to where its arms' inner edges, each given as two
    points on its straight part, meet.

    Each half reaches past the axis over the old inner corner; once the arms are turned apart,
    that reach shows inside the angle as a spike.
    """
    def x_at(edge, y):
        (x0, y0), (x1, y1) = edge
        return x0 + (x1 - x0) * (y - y0) / (y1 - y0)

    # Each edge is x = x_at(edge, AXIS) + slope * (y - AXIS); they meet where those agree.
    slopes = [x_at(edge, AXIS + 1) - x_at(edge, AXIS) for edge in (upper, lower)]
    meet_y = AXIS + (x_at(lower, AXIS) - x_at(upper, AXIS)) / (slopes[0] - slopes[1])
    meet = (x_at(upper, meet_y), meet_y)
    # Along each edge to twice the halves' reach from the axis, then 2 off it into the angle,
    # so the cut never runs along the edge itself.
    clear = 2 * HALF_REACH
    ux, lx = x_at(upper, AXIS + clear), x_at(lower, AXIS - clear)
    arm_side, point_side = OUTWARD[name] * geo.FAR, -OUTWARD[name] * geo.FAR
    opened = geo.clip(angle, geo.polygon([
        (point_side, -geo.FAR), (point_side, geo.FAR), (arm_side, geo.FAR),
        (arm_side, AXIS + clear - 2), (ux, AXIS + clear - 2), meet,
        (lx, AXIS - clear + 2), (arm_side, AXIS - clear + 2),
        (arm_side, -geo.FAR)]))
    # The cut can pass within a unit of an outline point. Rounded now, the two merge in the
    # cleanup that follows instead of leaving a zero-length segment that validate() flags.
    opened.round()
    return opened


def arrowhead(font, name):
    """> or < as the head of → or ←: its arms turned HEAD_TURN steeper and reaching as high and
    low as that arrow, so → beside -> reads as the same arrow."""
    _, y0, _, y1 = font["arrowright" if name == "greater" else "arrowleft"].boundingBox()
    return longer_angle(font, name, (y0, y1), HEAD_TURN)


def arrowheads(font):
    def head(name, shaft, x0, x1):
        return level(geo.union(arrowhead(font, name), stroke(font, shaft, x0, x1)),
                     [y for bar in RUNS[shaft] for y in bar.profile])

    left, right = TIP["less"], TIP["greater"]
    return {
        "less.arrow": head("less", "hyphen", left + SHAFT_INTO_HEAD, ADVANCE + OVERLAP),
        "greater.arrow": head("greater", "hyphen", -OVERLAP, right - SHAFT_INTO_HEAD),
        "less.darrow": head("less", "equal", left + BARS_INTO_HEAD, ADVANCE + OVERLAP),
        "greater.darrow": head("greater", "equal", -OVERLAP, right - BARS_INTO_HEAD),
    }


def equal_bars(font, cells):
    """= bars across `cells` cells, ending in the last: two over two cells, three over three,
    as both references draw === and !==."""
    span = ADVANCE * (cells - 1)
    bars = geo.transformed(geo.stretch(outline(font, "equal"), EQUAL_MIDDLE, span),
                           psMat.translate(-span, 0))
    if cells == 3:
        third = geo.transformed(geo.trim(bars, y1=AXIS), psMat.translate(0, -EQUAL_PITCH))
        return geo.transformed(geo.union(bars, third), psMat.translate(0, EQUAL_PITCH / 2))
    # Level, so the stretched middle, which the hinter takes the bars' edges from, lies on ='s
    # hint edges: there != kept the upper bar's middle on a pixel edge at 8 px, a tie the
    # hinter rounded down onto the lower bar.
    return level(bars, [y for bar in RUNS["equal"] for y in bar.profile])


def not_equal(font, cells):
    """!= over two cells or !== over three: equal_bars() and a / centred on the span."""
    span = ADVANCE * (cells - 1)
    bars = equal_bars(font, cells)
    slash = outline(font, "slash")
    sx0, sy0, sx1, sy1 = slash.boundingBox()
    _, by0, _, by1 = bars.boundingBox()
    centre = ((ADVANCE - span) / 2, (by0 + by1) / 2)
    slash = geo.transformed(slash, psMat.compose(
        geo.about(psMat.scale(SLASH_SCALE), (sx0 + sx1) / 2, (sy0 + sy1) / 2),
        psMat.translate(centre[0] - (sx0 + sx1) / 2, centre[1] - (sy0 + sy1) / 2)))
    return geo.union(bars, slash)


def eased(layer, name, angle):
    """`layer` turned by `angle` about the point of < or >, the turn easing in from none near
    the point to all of it further out (POINT_EASE), so the two halves of an angle, turned
    apart, keep the round point they share as drawn. A handle turns with its on-curve point,
    so the outline stays smooth where it was."""
    tip, (near, far) = TIP[name], POINT_EASE

    def turn_of(point):
        t = min(1.0, max(0.0, (math.hypot(point.x - tip, point.y - AXIS) - near) / (far - near)))
        return angle * t * t * (3 - 2 * t)  # smoothstep: no kink where the ease ends

    out = fontforge.layer()
    for contour in layer.dup():  # a contour's points are its own: moving one moves it there
        points = list(contour)
        # A handle belongs to the on-curve point before it, or else to the one after it.
        turns = [turn_of(point if point.on_curve else points[k - 1] if points[k - 1].on_curve
                         else points[(k + 1) % len(points)]) for k, point in enumerate(points)]
        moved = fontforge.contour()
        for point, turn in zip(points, turns, strict=True):
            dx, dy = point.x - tip, point.y - AXIS
            point.x = tip + dx * math.cos(turn) - dy * math.sin(turn)
            point.y = AXIS + dx * math.sin(turn) + dy * math.cos(turn)
            moved += point
        moved.closed = contour.closed
        out += moved
    return out


def flatter_angle(font, name, width_gain=ANGLE_WIDTH_GAIN):
    """< or > with each arm turned flatter about the point, so its end cap's centre moves out
    by `width_gain`, and lengthened until its ink reaches the height it had."""
    tip = TIP[name]
    _, bottom, _, top = font[name].boundingBox()
    arms = []
    for (end_x, end_y), half, goal in zip(ARM_ENDS[name], arm_halves(font, name), (top, bottom),
                                          strict=True):
        dx, dy = end_x - tip, end_y - AXIS
        old_direction = math.atan2(dy, dx)
        new_direction = math.atan2(dy, dx + OUTWARD[name] * width_gain)
        # Lay the arm along +x from the point, lengthen it, lay it back, then turn it into place.
        flat = reaching(turned(half, name, -old_direction), name, new_direction, goal)
        arms.append(eased(turned(flat, name, old_direction), name, new_direction - old_direction))
    return geo.union(*arms)


def or_equal(font, name):
    """<= or >= as ⩽ ⩾: the flatter angle with a bar under its lower arm, centred on the
    boundary between the two cells and on the axis, as ≤ ≥ and the references' ligatures
    are, so the angle rises above < > and the bar hangs below the baseline."""
    tip = TIP[name]
    end_x, end_y = ARM_ENDS[name][1]
    far = (end_x + OUTWARD[name] * ANGLE_WIDTH_GAIN, end_y)
    direction = math.atan2(far[1] - AXIS, far[0] - tip)
    length = math.hypot(far[0] - tip, far[1] - AXIS)
    bar = geo.stretch(outline(font, "hyphen"), ADVANCE / 2, length - HYPHEN_SPAN - 20)
    x0, y0, x1, y1 = bar.boundingBox()
    drop = BAR_GAP / abs(math.cos(direction))
    bar = geo.transformed(bar, psMat.compose(
        psMat.compose(psMat.translate(-(x0 + x1) / 2, -(y0 + y1) / 2), psMat.rotate(direction)),
        psMat.translate((tip + far[0]) / 2, (AXIS + far[1]) / 2 - drop)))
    symbol = geo.union(flatter_angle(font, name), bar)
    tight = symbol.dup()
    tight.addExtrema("all")  # else the box reaches to the control points
    x0, y0, x1, y1 = tight.boundingBox()
    # Moved up by whole units, so rounding keeps the angle as tall as < >.
    return geo.transformed(symbol, psMat.translate(-(x0 + x1) / 2, round(AXIS - (y0 + y1) / 2)))


def squeezed_bar(font, height):
    """| shortened to `height` along its straight middle, so it keeps its round ends."""
    bar = outline(font, "bar")
    _, y0, _, y1 = bar.boundingBox()
    # stretch_span works along x, so lay the bar on its side and stand it up again.
    lying = geo.transformed(bar, psMat.rotate(-math.pi / 2))
    lying = geo.stretch_span(lying, *BAR_SPAN, height - (y1 - y0))
    return geo.transformed(lying, psMat.rotate(math.pi / 2))


def pipe_head(font, name):
    """The head of > or < enlarged for |> <| <|>, PIPE_HEIGHT x-heights tall and centred on the
    axis: >'s lower arm, its flatter, turned steeper, and that arm mirrored about the height
    where >'s arms meet inside the point, so both arm ends reach as far and the point closes in
    one corner. <'s is that head turned, as < is > turned."""
    half = PIPE_HEIGHT * font.os2_xheight / 2

    def head(turn):
        angle = longer_angle(font, "greater", (AXIS - half, AXIS + half), turn)
        # >'s inner edges meet a little under the axis, where the white inside its point
        # reaches furthest. Mirrored about the axis instead, the foot of the upper arm under it
        # would stand inside the point as a notch.
        meet = max(range(AXIS - HALF_REACH, AXIS + HALF_REACH),
                   key=lambda y: span_at(angle, y)[0])
        lower = geo.trim(longer_angle(font, "greater", (meet - half, meet + half), turn), y1=meet)
        return geo.transformed(geo.weld_y(lower, geo.mirrored_y(lower, meet), meet),
                               psMat.translate(0, AXIS - meet))

    # Its end's height fixed, the arm reaches across by the run of its middle line, from the
    # end cap's centre up to the point, over the tangent of its slope. Turn it to the slope
    # whose reach takes the head from its unturned width to PIPE_ASPECT times its height.
    direction, _ = arm_axis(arm_halves(font, "greater")[1], GREATER_ENDS[1][1])
    slope = direction + math.pi  # >'s lower arm runs left and down from the point
    x0, _, x1, _ = head(0).boundingBox()
    run = half - SPECK / 2
    goal = math.atan(run / (run / math.tan(slope) - (x1 - x0 - PIPE_ASPECT * 2 * half)))
    turned_head = head(goal - slope)
    if name == "greater":
        return turned_head
    return geo.transformed(turned_head, geo.turned(ADVANCE / 2, AXIS))


def pipe_bar(font, head):
    """| squeezed to the height of `head` and level with it."""
    _, hy0, _, hy1 = head.boundingBox()
    bar = squeezed_bar(font, hy1 - hy0)
    return geo.transformed(bar, psMat.translate(0, hy0 - bar.boundingBox()[1]))


def against(head, name, x):
    """The pipe head of > or < moved so its arm ends' outer edge, the same for both arms
    (pipe_head()), lies at x. Arm and bar are about equally heavy, so with a bar's edge at x
    their round ends overlap and turn as one."""
    x0, _, x1, _ = head.boundingBox()
    return geo.transformed(head, psMat.translate(x - (x0 if name == "greater" else x1), 0))


def pipe(font, name):
    """|> or <| as a triangle: the enlarged head closed by a bar as tall as it."""
    arrow = pipe_head(font, name)
    bar = pipe_bar(font, arrow)
    bx0, _, bx1, _ = bar.boundingBox()
    # The bar's outer edge goes where the references put it, and the arm ends' outer edge onto it.
    edge = PIPE_BAR_EDGE[name]
    outer = bx0 if name == "greater" else bx1  # |> has its bar on the left, <| on the right
    bar = geo.transformed(bar, psMat.translate(edge - outer, 0))
    return geo.union(bar, against(arrow, name, edge))


def pipes(font):
    """<|> as ◁|▷: the heads of <| and |> on either side of one bar, centred on the middle of
    its three cells."""
    right = pipe_head(font, "greater")
    bar = pipe_bar(font, right)
    bx0, _, bx1, _ = bar.boundingBox()
    left = against(pipe_head(font, "less"), "less", bx1)
    symbol = geo.union(left, bar, against(right, "greater", bx0))
    x0, _, x1, _ = symbol.boundingBox()
    return geo.transformed(symbol, psMat.translate(-ADVANCE / 2 - (x0 + x1) / 2, 0))


def end_centre(angle, above):
    """(x, y): the centre of the round end of the arm of `angle` above or below the axis, half
    a stroke back from the arm's far end along its middle line. ARM_ENDS holds them for < and
    > as drawn."""
    _, y0, _, y1 = angle.boundingBox()
    rise = (y1 if above else y0) - AXIS
    (ax, ay), (bx, by) = (middle_at(angle, AXIS + k * rise) for k in (0.3, 0.65))
    direction = math.atan2(by - ay, bx - ax)
    # Laid along +x from (ax, ay), the arm's far end is its right edge.
    arm = geo.trim(angle, y0=AXIS) if above else geo.trim(angle, y1=AXIS)
    flat = geo.transformed(arm, geo.about(psMat.rotate(-direction), ax, ay))
    far = flat.boundingBox()[2]
    _, low, _, high = geo.trim(flat, x0=(ax + far) / 2 - 1, x1=(ax + far) / 2 + 1).boundingBox()
    reach = far - ax - (high - low) / 2
    return ax + reach * math.cos(direction), ay + reach * math.sin(direction)


def diamond(font):
    """<> as ◇: < and > widened by DIAMOND_WIDTH_GAIN and moved together until their arm ends
    meet on the boundary between the two cells, so each corner turns as one round stroke end."""
    halves = []
    for name in ("less", "greater"):
        angle = flatter_angle(font, name, DIAMOND_WIDTH_GAIN)
        middle = sum(end_centre(angle, above)[0] for above in (True, False)) / 2
        halves.append(geo.transformed(angle, psMat.translate(-middle, 0)))
    return geo.union(*halves)


def tail(font, name):
    """> or < as the tail of a double arrow (>=> <=<): each arm runs into an = bar, and the bars
    carry on into the next cell, so the point between them stays open."""
    angle = arrowhead(font, name)
    parts, joins = [], []
    for bar in RUNS["equal"]:
        bottom, top = bar.profile
        upper = bottom > AXIS
        inner = bottom if upper else top  # the bar's edge nearer the axis
        parts.append(geo.trim(angle, y0=inner) if upper else geo.trim(angle, y1=inner))
        # The bar starts where the arm's edge crosses the bar's inner edge, so the arm's edge
        # runs on into the bar's with no step, and the bar's flat end lies inside the arm.
        x0, x1 = span_at(angle, inner)
        cut = (x0, ADVANCE + OVERLAP) if name == "greater" else (-OVERLAP, x1)
        parts.append(geo.trim(stroke(font, "equal", *cut), y0=bar.band[0], y1=bar.band[1]))
        joins.append(x0 if name == "greater" else x1)
    # The bars are level out to where they meet the arms; the arms' own curves stay as drawn.
    reach = WOBBLE / 2 * OUTWARD[name]
    span = (min(joins) + reach, geo.FAR) if name == "greater" else (-geo.FAR, max(joins) + reach)
    return level(geo.union(*parts), [y for bar in RUNS["equal"] for y in bar.profile], *span)


def two_heads(font, name):
    """The end of ->> or <<-: a second head HEAD_PITCH inside the first, where the shaft ends."""
    head = arrowhead(font, name)
    inner = geo.transformed(head, psMat.translate(OUTWARD[name] * HEAD_PITCH, 0))
    end = TIP[name] + OUTWARD[name] * (HEAD_PITCH + SHAFT_INTO_HEAD)
    shaft = (stroke(font, "hyphen", -OVERLAP, end) if name == "greater"
             else stroke(font, "hyphen", end, ADVANCE + OVERLAP))
    return level(geo.union(head, inner, shaft), RUNS["hyphen"][0].profile)


def wave_arrows(font):
    """~> and <~: the head's cell carries on the ~ run, from the crest or trough the cell
    before ends on, and the wave's next turn runs into an arm, which hides its cut end.

    The wave's turn before that brushes the other arm and shuts in a speck of white near the
    point, which is filled.
    """
    tildes = tilde_pieces(font)
    right, left = (arrowhead(font, name) for name in ("greater", "less"))
    high = geo.trim(tildes["asciitilde.mid"], x1=WAVE_END)
    low = geo.trim(tildes["asciitilde.mid.low"], x1=WAVE_END)
    return {"greater.warrow": geo.without_specks(geo.union(right, high), SPECK),
            "greater.warrow.low": geo.without_specks(geo.union(right, low), SPECK),
            "less.warrow": geo.without_specks(geo.union(left, geo.mirrored_x(high, ADVANCE / 2)),
                                              SPECK)}


def comment_open(font):
    """<!--: the < as an arrow head whose shaft runs to the cell's edge and ends round, and how
    far the ! moves right to sit midway between that end and the start of the -- run."""
    shaft = stroke(font, "hyphen", TIP["less"] + SHAFT_INTO_HEAD)
    [bar] = RUNS["hyphen"]
    shaft = geo.stretch(shaft, bar.cuts[1], ADVANCE + OVERLAP - shaft.boundingBox()[2], bar.band)
    arrow = geo.union(arrowhead(font, "less"), shaft)
    x0, _, x1, _ = font["exclam"].boundingBox()
    start = font["hyphen"].boundingBox()[0] + ADVANCE  # the run's start, from the !'s cell
    return arrow, round(((start - x1) - (x0 - OVERLAP)) / 2)


def build(font):
    """Every generated glyph in SFD order: name -> outline layer, or a list of
    (glyph, dx, dy) references for pure shifts."""
    glyphs = {"LIG": []}  # the empty spacer before a .liga glyph
    glyphs.update(run_pieces(font))
    glyphs.update(tilde_pieces(font))
    glyphs.update(arrowheads(font))
    glyphs["exclam_equal.liga"] = not_equal(font, 2)
    glyphs["exclam_equal_equal.liga"] = not_equal(font, 3)
    glyphs["equal_equal_equal.liga"] = equal_bars(font, 3)
    glyphs["colon.eq"] = [("colon", 0, COLON_LIFT)]
    # <= is >= mirrored, as in Fira Code and Maple Mono: < is > turned, so built from its own
    # arms, the bar would hang under the other hand-drawn arm and stand the two apart.
    glyphs["greater_equal.liga"] = or_equal(font, "greater")
    glyphs["less_equal.liga"] = geo.mirrored_x(glyphs["greater_equal.liga"], 0)
    glyphs["bar_greater.liga"] = pipe(font, "greater")
    glyphs["less_bar.liga"] = pipe(font, "less")
    for name in TIGHT_KEEP:
        shift = tight_shift(font, name)
        glyphs[f"{name}.tight_r"] = [(name, shift, 0)]
        glyphs[f"{name}.tight_l"] = [(name, -shift, 0)]
    for side, sign in (("tight_r2", 2), ("tight_l2", -2)):
        for name in THREE_ENDS[side]:
            glyphs[f"{name}.{side}"] = [(name, sign * tight_shift(font, name), 0)]
    glyphs["less_greater.liga"] = diamond(font)
    glyphs["less_bar_greater.liga"] = pipes(font)
    for name in ("greater", "less"):
        glyphs[f"{name}.dtail"] = tail(font, name)
    for name in ("greater", "less"):
        glyphs[f"{name}.twohead"] = two_heads(font, name)
        glyphs[f"{name}.shaft"] = [("hyphen.mid", 0, 0)]  # a > or < inside ->> <<-
    glyphs.update(wave_arrows(font))
    glyphs["less.comment"], bang = comment_open(font)
    glyphs["exclam.tight_r"] = [("exclam", bang, 0)]
    return glyphs


def tight_shift(font, name):
    """How far `name` moves toward its partner in a tightened pair."""
    x0, _, x1, _ = font[name].boundingBox()
    return round((x0 + ADVANCE - x1) / 2 - TIGHT_KEEP[name])


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


def add_line_extension(font):
    """⎯ (U+23AF), which Vitest draws its dividers with, as the -- line's middle piece, so a
    row of them draws the line -- does. Removing the pieces unlinked it into an outline, so it
    is redrawn in place."""
    glyph = font.createChar(LINE_EXTENSION, f"uni{LINE_EXTENSION:04X}")
    glyph.foreground = fontforge.layer()
    glyph.references = (("hyphen.mid", psMat.identity()),)
    glyph.width = ADVANCE
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
    add_line_extension(font)
    merge_features(font)
    save_checked(font, sfd, __file__)


if __name__ == "__main__":
    main()
