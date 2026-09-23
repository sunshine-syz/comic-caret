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

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import add_ligatures  # noqa: E402
import lig_geometry as geo  # noqa: E402

GENERATOR = ROOT / "tools" / "add_ligatures.py"


def without_timestamp(path):
    return [line for line in path.read_text(encoding="utf-8").splitlines()
            if not line.startswith("ModificationTime: ")]


def spans_at_y(layer, y):
    """(x0, x1) of each stroke a horizontal line at y crosses, left to right."""
    # A thin band rather than a line; strokes at the same slant gain the same extra width.
    band = geo.trim(layer, y0=y - 1, y1=y + 1)
    return [(x0, x1) for x0, _, x1, _ in sorted(contour.boundingBox() for contour in band)]


def spans_at_x(layer, x):
    """(y0, y1) of each stroke a vertical line at x crosses, bottom to top."""
    band = geo.trim(layer, x0=x - 1, x1=x + 1)
    return sorted((y0, y1) for _, y0, _, y1 in (contour.boundingBox() for contour in band))


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


class GeneratorTest(unittest.TestCase):
    def test_rerunning_changes_nothing(self):
        # Fails when src/ligatures.fea or the generator changed without a rerun, or when a
        # generated glyph was edited by hand, as well as when a run is not repeatable.
        with tempfile.TemporaryDirectory() as tmp:
            copy = pathlib.Path(tmp) / add_ligatures.SFD.name
            shutil.copy(add_ligatures.SFD, copy)
            subprocess.run([sys.executable, str(GENERATOR), str(copy)], check=True)
            self.assertEqual(without_timestamp(copy), without_timestamp(add_ligatures.SFD))

    def test_generated_names_match_only_generated_glyphs(self):
        # The generator deletes every glyph whose name matches GENERATED before rebuilding, so
        # a hand-made glyph with such a name would silently disappear.
        font = fontforge.open(str(add_ligatures.SFD))
        matching = {g.glyphname for g in font.glyphs()
                    if add_ligatures.GENERATED.fullmatch(g.glyphname)}
        self.assertEqual(matching, set(add_ligatures.build(font)))

    def test_rejects_head_scales_outside_the_checked_range(self):
        result = subprocess.run([sys.executable, str(GENERATOR), "--head-scale", "1.3",
                                 "/nonexistent.sfd"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--head-scale must be within", result.stderr)


class MeasurementTest(unittest.TestCase):
    """The generator's constants are measurements of - = _ # ~ < > | : and fail here once one
    of those glyphs is redrawn. Without this, the generator would cut and snap the new
    outlines at the old places, and every other check would pass."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(add_ligatures.SFD))

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
        for name, tip in (("greater", al.GREATER_TIP), ("less", al.LESS_TIP)):
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
    PIPES = {"bar_greater.liga": "greater", "less_bar.liga": "less"}

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(add_ligatures.SFD))

    def mean_widths(self, name):
        """Mean stroke widths along the upper arm's height, left to right. Hand-drawn strokes
        vary in width along their length, so a single height would compare unlike parts."""
        # Above the arrow shafts, below where the arms of |> <| reach their bar.
        heights = range(add_ligatures.AXIS + 60, add_ligatures.AXIS + 161, 20)
        rows = [widths_at(self.font[name].foreground, y) for y in heights]
        self.assertEqual(len({len(row) for row in rows}), 1, f"{name}: strokes merge")
        return [sum(column) / len(rows) for column in zip(*rows)]

    def test_enlarged_heads_are_no_heavier_than_the_angles(self):
        # Scaling > up would thicken its arms past the shaft or bar they join.
        for glyph, angle in {"greater.arrow": "greater", "less.arrow": "less",
                             **self.PIPES}.items():
            with self.subTest(glyph=glyph):
                [arm] = self.mean_widths(angle)
                strokes = self.mean_widths(glyph)
                head = strokes[-1] if angle == "greater" else strokes[0]
                self.assertAlmostEqual(head, arm, delta=0.05 * arm)
                self.assertGreater(self.font[glyph].boundingBox()[3],
                                   self.font[angle].boundingBox()[3])

    def test_pipe_bars_are_as_heavy_as_the_bar(self):
        [bar] = self.mean_widths("bar")
        for pipe, angle in self.PIPES.items():
            with self.subTest(pipe=pipe):
                strokes = self.mean_widths(pipe)
                self.assertEqual(len(strokes), 2)
                self.assertAlmostEqual(strokes[0] if angle == "greater" else strokes[-1], bar,
                                       delta=0.05 * bar)

    def test_pipe_bars_keep_their_round_ends(self):
        # Every stroke in the font ends round; a bar cut flat shows a straight horizontal
        # edge as wide as the stroke.
        for pipe in self.PIPES:
            with self.subTest(pipe=pipe):
                self.assertEqual(flat_edges(self.font[pipe].foreground, 20), [])

    def test_pipe_corners_are_one_round_end(self):
        # An arm end beside the bar's end would leave two caps with a notch between them.
        for pipe in self.PIPES:
            layer = self.font[pipe].foreground
            _, bottom, _, top = layer.boundingBox()
            for y in (top - 4, top - 10, bottom + 4, bottom + 10):
                with self.subTest(pipe=pipe, y=y):
                    self.assertEqual(len(widths_at(layer, y)), 1)


if __name__ == "__main__":
    unittest.main()
