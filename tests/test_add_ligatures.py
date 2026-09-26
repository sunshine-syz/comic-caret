"""Tests for tools/add_ligatures.py itself.

Run: python3 -m unittest discover tests
"""
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import add_ligatures
from add_ligatures import AXIS, GENERATED, OVERLAP
from measure import spans_at_x, spans_at_y
from project import ADVANCE, ROOT, SFD

GENERATOR = ROOT / "tools" / "add_ligatures.py"
PIPES = {"bar_greater.liga": "greater", "less_bar.liga": "less"}
TRIANGLES = [*PIPES, "less_bar_greater.liga"]  # <|> is both pipes' heads on one bar


def without_timestamp(path):
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("ModificationTime: ")]


def widths_at(layer, y):
    """Widths of the strokes a horizontal line at y crosses, left to right."""
    return [x1 - x0 for x0, x1 in spans_at_y(layer, y)]


def flat_edges(layer, length):
    """Straight horizontal edges at least `length` long, as (y, x0, x1)."""
    edges = []
    for contour in layer:
        for i in range(len(contour)):
            a, b = contour[i], contour[(i + 1) % len(contour)]
            if a.on_curve and b.on_curve and a.y == b.y and abs(a.x - b.x) >= length:
                edges.append((a.y, min(a.x, b.x), max(a.x, b.x)))
    return edges


def cut_edges(layer, length):
    """Straight vertical edges at least `length` long, as (x, y0, y1): strokes cut flat."""
    edges = []
    for contour in layer:
        for i in range(len(contour)):
            a, b = contour[i], contour[(i + 1) % len(contour)]
            if a.on_curve and b.on_curve and a.x == b.x and abs(a.y - b.y) >= length:
                edges.append((a.x, min(a.y, b.y), max(a.y, b.y)))
    return edges


class GeneratorTest(unittest.TestCase):
    def test_rerunning_changes_nothing(self):
        # Fails when src/ligatures.fea or the generator changed without a rerun, or when a
        # generated glyph was edited by hand, as well as when a run is not repeatable.
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / SFD.name
            shutil.copy(SFD, copy)
            subprocess.run([sys.executable, str(GENERATOR), str(copy)], check=True)
            self.assertEqual(without_timestamp(copy), without_timestamp(SFD))

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
                x0, x1 = self.only(spans_at_y(angle, al.AXIS), "at the point")
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

    def mean_widths(self, name):
        """Mean stroke widths along the upper arm's height, left to right. Hand-drawn strokes
        vary in width along their length, so a single height would compare unlike parts."""
        # Above the arrow shafts, below where the arms of |> <| reach their bar.
        heights = range(add_ligatures.AXIS + 60, add_ligatures.AXIS + 161, 20)
        rows = [widths_at(self.font[name].foreground, y) for y in heights]
        self.assertEqual(len({len(row) for row in rows}), 1, f"{name}: strokes merge")
        return [sum(column) / len(rows) for column in zip(*rows, strict=True)]

    def test_enlarged_heads_are_no_heavier_than_the_angles(self):
        # Scaling > up would thicken its arms past the shaft or bar they join.
        for glyph, angle in {"greater.arrow": "greater", "less.arrow": "less",
                             "less_bar_greater.liga": "less", **PIPES}.items():
            with self.subTest(glyph=glyph):
                [arm] = self.mean_widths(angle)
                strokes = self.mean_widths(glyph)
                head = strokes[-1] if angle == "greater" else strokes[0]
                self.assertAlmostEqual(head, arm, delta=0.05 * arm)
                self.assertGreater(self.font[glyph].boundingBox()[3],
                                   self.font[angle].boundingBox()[3])

    def test_pipe_bars_are_as_heavy_as_the_bar(self):
        [bar] = self.mean_widths("bar")
        for pipe, index in {**{p: 0 if a == "greater" else -1 for p, a in PIPES.items()},
                            "less_bar_greater.liga": 1}.items():
            with self.subTest(pipe=pipe):
                strokes = self.mean_widths(pipe)
                self.assertEqual(len(strokes), 3 if index == 1 else 2)
                self.assertAlmostEqual(strokes[index], bar, delta=0.05 * bar)

    def test_pipe_bars_keep_their_round_ends(self):
        # Every stroke in the font ends round; a bar cut flat shows a straight horizontal
        # edge as wide as the stroke.
        for pipe in TRIANGLES:
            with self.subTest(pipe=pipe):
                self.assertEqual(flat_edges(self.font[pipe].foreground, 20), [])

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
            edges = [e for e in cut_edges(glyph.foreground, 20) if e[0] not in seams]
            if not name.startswith(("underscore.", "numbersign.")):
                edges += flat_edges(glyph.foreground, 20)
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


if __name__ == "__main__":
    unittest.main()
