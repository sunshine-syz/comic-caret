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
from measure import gap, horizontal_edges, ink, spans_at_x, spans_at_y, vertical_edges
from project import ADVANCE, AXIS, OVERLAP, SFD

PIPES = {"bar_greater.liga": "greater", "less_bar.liga": "less"}
TRIANGLES = [*PIPES, "less_bar_greater.liga"]  # <|> is both pipes' heads on one bar
# The shortest white between the two heads of Fira Code's ->>, the one reference that draws
# it, with its cell scaled to ours.
FIRA_HEAD_GAP = 133


def widths_at(layer, y):
    """Widths of the strokes a horizontal line at y crosses, left to right."""
    return [x1 - x0 for x0, x1 in spans_at_y(layer, y)]


def one_layer(contour):
    layer = fontforge.layer()
    layer += contour
    return layer


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
                for end_x, end_y in al.ARM_ENDS[name]:
                    self.assertTrue(any(a < end_x < b for a, b in spans_at_y(angle, end_y)),
                                    f"{name} has no arm end at ({end_x}, {end_y})")

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
        # Two stroke ends side by side would leave two caps with a notch between them.
        for glyph in [*TRIANGLES, "less_greater.liga"]:
            layer = self.font[glyph].foreground
            _, bottom, _, top = layer.boundingBox()
            for y in (top - 4, top - 10, bottom + 4, bottom + 10):
                with self.subTest(glyph=glyph, y=y):
                    self.assertEqual(len(widths_at(layer, y)), 1)

    def test_strokes_are_cut_flat_only_where_they_run_on(self):
        # Every stroke in the font ends round. A straight edge is a stroke cut flat, which a
        # piece may show only where it runs on into the next cell: upright, at the cell's
        # edge. Any other cut has to lie inside a stroke it runs into. The bars of _ and # are
        # drawn with straight sides.
        seams = {-OVERLAP, ADVANCE + OVERLAP}
        cut = {}
        for glyph in self.font.glyphs():
            name = glyph.glyphname
            if not GENERATED.fullmatch(name):
                continue
            edges = [e for e in vertical_edges(glyph.foreground)
                     if e[2] - e[1] >= 20 and e[0] not in seams]
            if not name.startswith(("underscore.", "numbersign.")):
                edges += [e for e in horizontal_edges(glyph.foreground) if e[2] - e[1] >= 20]
            if edges:
                cut[name] = edges
        self.assertEqual(cut, {})

    def test_diamond_is_one_ring_centred_on_its_cells(self):
        # <> as ◇: the halves meet at both corners around one counter, centred on the boundary
        # between its two cells and on the axis, like < and >.
        layer = self.font["less_greater.liga"].foreground
        # One outline and one hole: two halves that don't meet are two outlines.
        self.assertEqual(sorted(c.isClockwise() for c in layer), [False, True])
        x0, y0, x1, y1 = layer.boundingBox()
        self.assertAlmostEqual((x0 + x1) / 2, 0, delta=2)
        self.assertAlmostEqual((y0 + y1) / 2, AXIS, delta=5)

    def test_pipes_are_centred_on_their_middle_cell(self):
        x0, _, x1, _ = self.font["less_bar_greater.liga"].boundingBox()
        self.assertAlmostEqual((x0 + x1) / 2, -ADVANCE / 2, delta=2)

    def test_tails_leave_the_point_open(self):
        # >=> <=<: each arm runs into its = bar, and nothing joins the bars at the axis.
        for tail in ("greater.dtail", "less.dtail"):
            with self.subTest(tail=tail):
                layer = self.font[tail].foreground
                self.assertEqual(len(layer), 2)
                self.assertEqual(spans_at_y(layer, AXIS), [])

    def test_two_heads_stay_apart(self):
        for glyph in ("greater.twohead", "less.twohead"):
            with self.subTest(glyph=glyph):
                layer = self.font[glyph].foreground
                self.assertEqual(len(layer), 2)  # the outer head, and the inner one with the shaft
                self.assertGreaterEqual(gap(*(one_layer(c) for c in layer)), FIRA_HEAD_GAP)

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
