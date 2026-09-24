"""Tests for tools/measure.py on synthetic outlines.

Run: python3 -m unittest discover tests
"""
import pathlib
import sys
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import lig_geometry as geo
import measure


def bars(*spans, height=400):
    """One layer holding an upright bar for each (x0, x1)."""
    out = fontforge.layer()
    for x0, x1 in spans:
        out += geo.rect(x0, 0, x1, height)
    return out


def rounded(spans):
    return [(round(a), round(b)) for a, b in spans]


class SpanTest(unittest.TestCase):
    def test_spans_at_y_run_left_to_right(self):
        self.assertEqual(rounded(measure.spans_at_y(bars((200, 290), (0, 90)), 100)),
                         [(0, 90), (200, 290)])

    def test_spans_at_x_run_bottom_to_top(self):
        layer = fontforge.layer()
        layer += geo.rect(0, 300, 100, 380)
        layer += geo.rect(0, 0, 100, 80)
        self.assertEqual(rounded(measure.spans_at_x(layer, 50)), [(0, 80), (300, 380)])

    def test_counter_sums_the_white_between_strokes(self):
        self.assertEqual(round(measure.counter(bars((0, 90), (200, 290), (350, 440)), 100)), 170)
        self.assertEqual(measure.counter(bars((0, 90)), 100), 0)

    def test_ink_width_and_center(self):
        layer = bars((10, 90), (200, 290))
        self.assertEqual(measure.ink_width(layer), 280)
        self.assertEqual(measure.ink_center(layer), 150)


class GapTest(unittest.TestCase):
    def test_gap_between_side_by_side_bars(self):
        self.assertAlmostEqual(measure.gap(bars((0, 90)), bars((130, 220))), 40, delta=1)

    def test_gap_across_a_corner(self):
        # Corner to corner, (90, 400) to (120, 440): 30 across and 40 up.
        above = fontforge.layer()
        above += geo.rect(120, 440, 200, 500)
        self.assertAlmostEqual(measure.gap(bars((0, 90)), above), 50, delta=1)

    def test_touching_outlines_have_no_gap(self):
        self.assertAlmostEqual(measure.gap(bars((0, 90)), bars((90, 180))), 0, delta=1)


class ThicknessChangeTest(unittest.TestCase):
    def test_a_rigid_move_changes_nothing(self):
        bar = bars((100, 190))
        change, _ = measure.thickness_change(bar, geo.displaced(bar, lambda x, y: -40))
        self.assertAlmostEqual(change, 0, delta=0.01)

    def test_a_widened_stroke_changes_by_the_widening(self):
        bar = bars((100, 190))
        change, where = measure.thickness_change(
            bar, geo.displaced(bar, lambda x, y: 10 if x > 150 else 0))
        # Near the corners the normals lean, so a leaning ray gains a little more than 10.
        self.assertAlmostEqual(change, 10, delta=0.5)
        self.assertIsNotNone(where)

    def test_shortening_a_long_stroke_is_no_change_in_weight(self):
        # Rays from a stroke's ends run along it and measure its length, not its weight.
        bar = geo.rect(0, 0, 400, 90)
        change, _ = measure.thickness_change(bar, geo.stretch_span(bar, 100, 300, -60))
        self.assertAlmostEqual(change, 0, delta=0.01)

    def test_squeezing_a_slanted_stroke_thins_it(self):
        # 45 degrees and 64 thick; squeezed to half its run it stands at 63 degrees, 40 thick.
        contour = fontforge.contour()
        for x, y in ((0, 0), (300, 300), (390, 300), (90, 0)):
            contour += fontforge.point(x, y)
        contour.closed = True
        stroke = fontforge.layer()
        stroke += contour
        change, _ = measure.thickness_change(stroke, geo.displaced(stroke, lambda x, y: -x / 2))
        self.assertGreater(change, 10)


if __name__ == "__main__":
    unittest.main()
