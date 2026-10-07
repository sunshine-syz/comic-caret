"""Tests for tools/add_ligatures.py itself.

Run: python3 -m unittest discover tests
"""
import math
import pathlib
import sys
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import add_ligatures
from add_ligatures import GENERATED
from make_bold import HEAD_WHITE
from measure import gap, horizontal_edges, ink, spans_at_x, spans_at_y, vertical_edges
from project import ADVANCE, AXIS, BOLD_SFD, OVERLAP, ROUNDING, SFD, WOBBLE

PIPES = {"bar_greater.liga": "greater", "less_bar.liga": "less"}
TRIANGLES = [*PIPES, "less_bar_greater.liga"]  # <|> is both pipes' heads on one bar
# The points of the angles built from < and >: glyph -> the side it points to, and the lowest
# row of the angle, above the bar of <= >=, which lies below the axis.
POINTS = {"greater_equal.liga": ("right", AXIS), "less_equal.liga": ("left", AXIS),
          "greater.arrow": ("right", None), "less.arrow": ("left", None)}
# The shortest white between the two heads of Fira Code's ->>, the one reference that draws
# it: 289.6 in its 1200-unit cell, scaled to ours. The bold's is make_bold's HEAD_WHITE, Fira
# Code Bold's.
FIRA_HEAD_GAP = 289.6 * ADVANCE / 1200
# The angle of <= >= apart from its bar, in x-heights: Fira Code's (1156 of 1053) and Maple
# Mono's (620 of 550).
OR_EQUAL_ANGLES = (1.098, 1.127)
# The white between <= >='s lower arm and its bar: Maple Mono's, the narrower reference's (Fira
# Code's are 141 and 121), at our cap height; regular, then bold.
OR_EQUAL_WHITE, BOLD_OR_EQUAL_WHITE = 106, 85
# |> <|'s ink in x-heights, tall then wide: Fira Code's is 1603 by 1306 of 1053 (1.52, 1.240),
# JetBrains Mono's 835 by 685 of 550 (1.52, 1.245).
PIPE_HEIGHT, PIPE_WIDTHS = 1.52, (1.240, 1.245)


def widths_at(layer, y):
    """Widths of the strokes a horizontal line at y crosses, left to right."""
    return [x1 - x0 for x0, x1 in spans_at_y(layer, y)]


def peaks(profile, tolerance):
    """How many peaks `profile` rises to, a dip between two counting only where it falls more
    than `tolerance` below both."""
    count, high, low, falling = 1, profile[0], profile[0], False
    for value in profile:
        if falling and value - low > tolerance:
            count, high, falling = count + 1, value, False
        elif not falling and high - value > tolerance:
            low, falling = value, True
        high, low = max(high, value), min(low, value)
    return count


def one_layer(contour):
    layer = fontforge.layer()
    layer += contour
    return layer


def corners(contour):
    """The turn in degrees at each on-curve point of the contour, from the point before it to
    the point after it, handles included: 0 where the outline runs on smoothly."""
    points = list(contour)
    turns = []
    for k, point in enumerate(points):
        if point.on_curve:
            before, after = points[k - 1], points[(k + 1) % len(points)]
            ax, ay = point.x - before.x, point.y - before.y
            bx, by = after.x - point.x, after.y - point.y
            turns.append(math.degrees(math.atan2(ax * by - ay * bx, ax * bx + ay * by)))
    return turns


class GeneratorTest(unittest.TestCase):
    def test_generated_names_match_only_generated_glyphs(self):
        # The generator deletes every glyph whose name matches GENERATED before rebuilding, so
        # a hand-made glyph with such a name would silently disappear.
        font = fontforge.open(str(SFD))
        matching = {g.glyphname for g in font.glyphs()
                    if add_ligatures.GENERATED.fullmatch(g.glyphname)}
        self.assertEqual(matching, set(add_ligatures.build(font)))


class MeasurementTest(unittest.TestCase):
    """The generator's constants are measurements of - = _ # ~ < > | : and fail here once one
    of those glyphs is redrawn. Without this, the generator would cut and snap the new
    outlines at the old places, and every other check would pass."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def only(self, spans, what):
        self.assertEqual(len(spans), 1, f"expected one stroke {what}, got {spans}")
        return spans[0]

    def test_tight_pairs_keep_their_side(self):
        # The shift follows the glyph's side bearing, so the white between a pair survives a
        # wider cell or a redrawn glyph.
        for name, keep in add_ligatures.TIGHT_KEEP.items():
            x0, _, x1, _ = self.font[name].boundingBox()
            # Recomputed here, not through tight_shift: this checks the generator's output.
            shift = round((x0 + ADVANCE - x1) / 2 - keep)
            for suffix, sign in (("tight_r", 1), ("tight_l", -1)):
                with self.subTest(glyph=f"{name}.{suffix}"):
                    [(base, matrix, *_)] = self.font[f"{name}.{suffix}"].references
                    self.assertEqual(base, name)
                    self.assertEqual(matrix[4], sign * shift)

    def test_run_bars_meet_their_profiles_at_the_cuts(self):
        for name, bars in add_ligatures.RUNS.items():
            for bar in bars:
                for cut in bar.cuts:
                    with self.subTest(glyph=name, band=bar.band, cut=cut):
                        y0, y1 = self.only([s for s in spans_at_x(self.font[name].foreground, cut)
                                            if bar.band[0] <= s[0] and s[1] <= bar.band[1]],
                                           "in the band")
                        self.assertAlmostEqual(y0, bar.profile[0], delta=5)
                        self.assertAlmostEqual(y1, bar.profile[1], delta=5)

    def test_tilde_peaks_at_the_crest_and_dips_at_the_trough(self):
        al, tilde = add_ligatures, self.font["asciitilde"].foreground
        for x, profile, extreme in ((al.TILDE_CREST, al.CREST_PROFILE, 1),
                                    (al.TILDE_TROUGH, al.TROUGH_PROFILE, 0)):
            with self.subTest(x=x):
                span = self.only(spans_at_x(tilde, x), f"at x {x}")
                self.assertAlmostEqual(span[0], profile[0], delta=3)
                self.assertAlmostEqual(span[1], profile[1], delta=3)
                for beside in (x - 20, x + 20):
                    edge = spans_at_x(tilde, beside)[0][extreme]
                    self.assertTrue(edge <= span[1] if extreme else edge >= span[0])

    def test_angles_have_their_point_and_arm_ends_where_the_constants_say(self):
        al = add_ligatures
        for name, tip in al.TIP.items():
            with self.subTest(glyph=name):
                angle = self.font[name].foreground
                x0, x1 = self.only(spans_at_y(angle, AXIS), "at the point")
                self.assertAlmostEqual(x1 if name == "greater" else x0, tip, delta=2)
                # The arm ends are their round ends' centres, rounded to whole units.
                for end, above in zip(al.ARM_ENDS[name], (True, False), strict=True):
                    for constant, found in zip(end, al.end_centre(angle, above), strict=True):
                        self.assertAlmostEqual(constant, found, delta=ROUNDING)

    def test_colon_lift_centres_the_colon_on_the_equal_sign(self):
        _, c0, _, c1 = self.font["colon"].boundingBox()
        _, e0, _, e1 = self.font["equal"].boundingBox()
        self.assertAlmostEqual((c0 + c1) / 2 + add_ligatures.COLON_LIFT, (e0 + e1) / 2, delta=2)

    def test_hyphen_span_is_the_distance_between_its_cap_centres(self):
        # Each round cap's centre sits half the stroke's height in from its end.
        x0, y0, x1, y1 = self.font["hyphen"].boundingBox()
        self.assertAlmostEqual((x1 - x0) - (y1 - y0), add_ligatures.HYPHEN_SPAN, delta=10)

    def test_bar_span_lies_on_the_straight_part_of_the_bar(self):
        bar = self.font["bar"].foreground
        span = add_ligatures.BAR_SPAN
        middle = self.only(widths_at(bar, sum(span) / 2), "in the middle")
        for y in span:
            with self.subTest(y=y):
                self.assertAlmostEqual(self.only(widths_at(bar, y), f"at y {y}"), middle,
                                       delta=0.05 * middle)


class TwoHeadsTest(unittest.TestCase):
    """->> <<-: the white between the two heads, at least Fira Code's."""
    sfd, head_gap = SFD, FIRA_HEAD_GAP

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(cls.sfd))

    def test_two_heads_stay_apart(self):
        for glyph in ("greater.twohead", "less.twohead"):
            with self.subTest(glyph=glyph):
                layer = self.font[glyph].foreground
                self.assertEqual(len(layer), 2)  # the outer head, and the inner one with the shaft
                self.assertGreaterEqual(gap(*(one_layer(c) for c in layer)), self.head_gap)


class BoldTwoHeadsTest(TwoHeadsTest):
    sfd, head_gap = BOLD_SFD, HEAD_WHITE


class TwoWayHeadsTest(unittest.TestCase):
    """<-> <==>: a head each way, standing level; one taller than the other reads as a slip."""
    sfd = SFD

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(cls.sfd))

    def test_two_way_heads_stand_level(self):
        for left, right in (("less.arrow", "greater.arrow"), ("less.darrow", "greater.darrow")):
            with self.subTest(heads=(left, right)):
                _, l0, _, l1 = self.font[left].boundingBox()
                _, r0, _, r1 = self.font[right].boundingBox()
                self.assertAlmostEqual(l0, r0, delta=ROUNDING)
                self.assertAlmostEqual(l1, r1, delta=ROUNDING)


class BoldTwoWayHeadsTest(TwoWayHeadsTest):
    sfd = BOLD_SFD


class OrEqualTest(unittest.TestCase):
    """<= >=: the bar stands clear of the lower arm, by at least the narrower reference's."""
    sfd, white = SFD, OR_EQUAL_WHITE

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(cls.sfd))

    def test_bar_stands_clear_of_the_arm(self):
        # At 54 the bold's bar and arm read as one stroke at 12 px, so <= read as <.
        for glyph in ("less_equal.liga", "greater_equal.liga"):
            with self.subTest(glyph=glyph):
                angle, bar = sorted(self.font[glyph].foreground,
                                    key=lambda contour: contour.boundingBox()[3], reverse=True)
                self.assertGreaterEqual(gap(one_layer(angle), one_layer(bar)), self.white)


class BoldOrEqualTest(OrEqualTest):
    sfd, white = BOLD_SFD, BOLD_OR_EQUAL_WHITE


class PointTest(unittest.TestCase):
    sfd = SFD

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(cls.sfd))

    def bend(self, glyph, side, lowest=None):
        """The most the glyph's outer edge on `side` bends outward from one row to the next,
        within 40 rows of its point, from `lowest` up."""
        layer = self.font[glyph].foreground
        _, y0, _, y1 = layer.boundingBox()
        outer = {}
        for y in range(math.ceil(max(y0, lowest or y0)), math.floor(y1)):
            if spans := spans_at_y(layer, y):
                outer[y] = spans[-1][1] if side == "right" else -spans[0][0]
        point = max(outer, key=outer.get)
        ys = [y for y in sorted(outer) if abs(y - point) <= 40]
        return round(max(outer[a] + outer[c] - 2 * outer[b]
                         for a, b, c in zip(ys, ys[1:], ys[2:], strict=False)), 6)

    def test_points_stay_round(self):
        # A point turns as one round stroke end, as < and > do, so across it the outer edge
        # bends outward no more than theirs. Halves of an angle turned apart, each with its
        # half of the end, leave a ledge where they meet. Outline points rounded to whole
        # units bend the edge outward by up to a unit.
        allowed = max(ROUNDING, self.bend("greater", "right"), self.bend("less", "left"))
        for glyph, (side, lowest) in POINTS.items():
            with self.subTest(glyph=glyph):
                self.assertLessEqual(self.bend(glyph, side, lowest), allowed)


class BoldPointTest(PointTest):
    sfd = BOLD_SFD


class EasedTest(unittest.TestCase):
    """eased(), which turns the arms of <= >= apart about their point."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_turning_keeps_every_corner(self):
        # An on-curve point turns with its handles, so a smooth point stays smooth.
        layer = self.font["greater"].foreground
        drawn = [corners(contour) for contour in layer]
        turned = add_ligatures.eased(layer, "greater", math.radians(5))
        for before, contour in zip(drawn, turned, strict=True):
            for corner, now in zip(before, corners(contour), strict=True):
                self.assertAlmostEqual(corner, now, places=6)

    def test_turning_leaves_its_input_as_it_was(self):
        layer = self.font["greater"].foreground
        drawn = [(point.x, point.y) for contour in layer for point in contour]
        add_ligatures.eased(layer, "greater", math.radians(5))
        self.assertEqual([(point.x, point.y) for contour in layer for point in contour], drawn)


class GlyphShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def mean_weights(self, name):
        """Mean stroke weights along the upper arm's height, left to right. Hand-drawn strokes
        vary in width along their length, so a single height would compare unlike parts."""
        # Above the arrow shafts, below where the arms of |> <| reach their bar.
        heights = range(AXIS + 60, AXIS + 161, 20)
        rows = [spans_at_y(self.font[name].foreground, y) for y in heights]
        self.assertEqual(len({len(row) for row in rows}), 1, f"{name}: strokes merge")
        weights = []
        for column in zip(*rows, strict=True):
            # A line across a slanted stroke cuts it wider than its weight, the steeper the
            # less, so the arrowheads' steeper arms are measured square to their slant.
            middles = [(x0 + x1) / 2 for x0, x1 in column]
            slant = math.atan2(heights[-1] - heights[0], middles[-1] - middles[0])
            width = sum(x1 - x0 for x0, x1 in column) / len(column)
            weights.append(width * abs(math.sin(slant)))
        return weights

    def test_enlarged_heads_are_no_heavier_than_the_angles(self):
        # Scaling > up would thicken its arms past the shaft or bar they join.
        for glyph, angle in {"greater.arrow": "greater", "less.arrow": "less",
                             "less_bar_greater.liga": "less", **PIPES}.items():
            with self.subTest(glyph=glyph):
                [arm] = self.mean_weights(angle)
                strokes = self.mean_weights(glyph)
                head = strokes[-1] if angle == "greater" else strokes[0]
                self.assertAlmostEqual(head, arm, delta=0.05 * arm)
                (_, y0, _, y1), (_, a0, _, a1) = (self.font[name].boundingBox()
                                                  for name in (glyph, angle))
                self.assertGreater(y1 - y0, a1 - a0)

    def test_pipe_bars_are_as_heavy_as_the_bar(self):
        [bar] = self.mean_weights("bar")
        for pipe, index in {**{p: 0 if a == "greater" else -1 for p, a in PIPES.items()},
                            "less_bar_greater.liga": 1}.items():
            with self.subTest(pipe=pipe):
                strokes = self.mean_weights(pipe)
                self.assertEqual(len(strokes), 3 if index == 1 else 2)
                self.assertAlmostEqual(strokes[index], bar, delta=0.05 * bar)

    def test_pipe_bars_keep_their_round_ends(self):
        # Every stroke in the font ends round; a bar cut flat shows a straight horizontal
        # edge as wide as the stroke.
        for pipe in TRIANGLES:
            with self.subTest(pipe=pipe):
                edges = horizontal_edges(self.font[pipe].foreground)
                flat = [e for e in edges if e[2] - e[1] >= 20]
                self.assertEqual(flat, [])

    def test_corners_are_one_round_end(self):
        # Where stroke ends meet at a corner they turn as one round end, so the ink's top edge
        # rises to one peak and its bottom edge falls to one. Two ends side by side would leave
        # two caps with a dip between them, however shallow.
        for glyph in TRIANGLES:
            layer = self.font[glyph].foreground
            x0, _, x1, _ = layer.boundingBox()
            columns = [spans_at_x(layer, x) for x in range(math.ceil(x0) + 1, math.floor(x1))]
            for side, edge in (("top", [spans[-1][1] for spans in columns]),
                               ("bottom", [-spans[0][0] for spans in columns])):
                with self.subTest(glyph=glyph, side=side):
                    self.assertEqual(peaks(edge, ROUNDING / 2), 1)

    def test_heads_close_to_one_point(self):
        # Inside each head the white narrows to one point, where the arms' inner edges meet. A
        # bit of one arm left standing inside the point splits it into two, a notch between.
        heads = {"bar_greater.liga": ("right",), "less_bar.liga": ("left",),
                 "less_bar_greater.liga": ("left", "right")}
        for glyph, sides in heads.items():
            layer = self.font[glyph].foreground
            _, y0, _, y1 = layer.boundingBox()
            # The rows that cross the bar and each head's white, clear of the corners.
            rows = [spans for spans in (spans_at_y(layer, y) for y in range(round(y0), round(y1)))
                    if len(spans) == 1 + len(sides)]
            for side in sides:
                edge = [spans[-1][0] if side == "right" else -spans[0][1] for spans in rows]
                with self.subTest(glyph=glyph, side=side):
                    self.assertEqual(peaks(edge, ROUNDING / 2), 1)

    def test_strokes_are_cut_flat_only_where_they_run_on(self):
        # Every stroke in the font ends round. A straight edge is a stroke cut flat, which a
        # piece may show only where it runs on into the next cell: upright, at the cell's
        # edge. Any other cut has to lie inside a stroke it runs into. The bars of _ and # are
        # drawn with straight sides, and a run's bars are levelled onto their profiles.
        seams = {-OVERLAP, ADVANCE + OVERLAP}
        levelled = {y for bars in add_ligatures.RUNS.values() for bar in bars for y in bar.profile}
        cut = {}
        for glyph in self.font.glyphs():
            name = glyph.glyphname
            if not GENERATED.fullmatch(name):
                continue
            edges = [e for e in vertical_edges(glyph.foreground)
                     if e[2] - e[1] >= 20 and e[0] not in seams]
            if not name.startswith(("underscore.", "numbersign.")):
                edges += [e for e in horizontal_edges(glyph.foreground)
                          if e[2] - e[1] >= 20 and e[0] not in levelled]
            if edges:
                cut[name] = edges
        self.assertEqual(cut, {})

    def test_or_equal_angle_is_as_wide_as_the_references(self):
        # The angle apart from its bar, in x-heights, between Fira Code's and Maple Mono's,
        # give or take the hand's wobble.
        wobble = WOBBLE / self.font.os2_xheight
        for glyph in ("less_equal.liga", "greater_equal.liga"):
            with self.subTest(glyph=glyph):
                layer = self.font[glyph].foreground
                self.assertEqual(len(layer), 2)  # the angle and the bar, apart
                angle = max(layer, key=lambda contour: contour.boundingBox()[3])
                x0, _, x1, _ = angle.boundingBox()
                width = (x1 - x0) / self.font.os2_xheight
                self.assertGreaterEqual(width, OR_EQUAL_ANGLES[0] - wobble)
                self.assertLessEqual(width, OR_EQUAL_ANGLES[1] + wobble)

    def test_pipe_heads_are_as_large_as_the_references(self):
        # In x-heights, at least as tall as Fira Code's and JetBrains Mono's |> <|, and as
        # wide as one of them, give or take the hand's wobble.
        wobble = WOBBLE / self.font.os2_xheight
        for glyph in PIPES:
            with self.subTest(glyph=glyph):
                x0, y0, x1, y1 = self.font[glyph].boundingBox()
                width = (x1 - x0) / self.font.os2_xheight
                self.assertGreaterEqual((y1 - y0) / self.font.os2_xheight, PIPE_HEIGHT - wobble)
                self.assertGreaterEqual(width, PIPE_WIDTHS[0] - wobble)
                self.assertLessEqual(width, PIPE_WIDTHS[1] + wobble)

    def test_pipes_are_centred_on_their_middle_cell(self):
        x0, _, x1, _ = self.font["less_bar_greater.liga"].boundingBox()
        self.assertAlmostEqual((x0 + x1) / 2, -ADVANCE / 2, delta=2)

    def test_triangles_are_centred_on_the_axis_and_equally_tall(self):
        # Like < > and the arrows, each triangle centres on the axis, and <|> is as tall as
        # |> <|, its heads meeting its bar's round ends. The generator places them by
        # computation, so only rounding may move them; WOBBLE would hide a head hung low.
        heights = {}
        for glyph in TRIANGLES:
            with self.subTest(glyph=glyph):
                _, y0, _, y1 = self.font[glyph].boundingBox()
                heights[glyph] = y1 - y0
                self.assertAlmostEqual((y0 + y1) / 2, AXIS, delta=ROUNDING)
        self.assertLessEqual(max(heights.values()) - min(heights.values()), ROUNDING, heights)

    def test_or_equal_angles_share_one_span(self):
        # <= and >= mirror each other, as in Fira Code and Maple Mono, so their angles stand
        # at one height. < is > turned, not mirrored: an angle built from each would hang its
        # bar under a different hand-drawn arm.
        spans = []
        for glyph in ("less_equal.liga", "greater_equal.liga"):
            angle = max(self.font[glyph].foreground, key=lambda contour: contour.boundingBox()[3])
            spans.append(angle.boundingBox()[1::2])
        for less, greater in zip(*spans, strict=True):
            self.assertAlmostEqual(less, greater, delta=ROUNDING)

    def test_tails_leave_the_point_open(self):
        # >=> <=<: each arm runs into its = bar, and nothing joins the bars at the axis.
        for tail in ("greater.dtail", "less.dtail"):
            with self.subTest(tail=tail):
                layer = self.font[tail].foreground
                self.assertEqual(len(layer), 2)
                self.assertEqual(spans_at_y(layer, AXIS), [])

    def test_wave_arrows_are_one_stroke(self):
        # The wave runs into the head, leaving no counter or speck of white between them.
        for glyph in ("greater.warrow", "greater.warrow.low", "less.warrow"):
            with self.subTest(glyph=glyph):
                self.assertEqual(len(self.font[glyph].foreground), 1)

    def test_comment_arrow_reads_as_an_arrow(self):
        # <!--: the shaft reaches past the arm ends, and the ! sits midway between the shaft's
        # end and the -- run.
        arrow = self.font["less.comment"].foreground
        _, _, end, _ = arrow.boundingBox()
        self.assertAlmostEqual(spans_at_y(arrow, AXIS)[-1][1], end, delta=1)
        x0, _, x1, _ = ink(self.font, "exclam.tight_r").boundingBox()
        start = self.font["hyphen.sta"].boundingBox()[0] + ADVANCE
        self.assertAlmostEqual(x0 - (end - ADVANCE), start - x1, delta=2)


if __name__ == "__main__":
    unittest.main()
