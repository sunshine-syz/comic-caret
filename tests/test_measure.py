"""Tests for tools/measure.py on synthetic outlines.

Run: python3 -m unittest discover tests
"""
import pathlib
import sys
import unittest

import fontforge
import psMat

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


class InkTest(unittest.TestCase):
    def test_resolves_nested_references_where_they_are_placed(self):
        font = fontforge.font()
        font.createChar(-1, "bar").foreground = bars((0, 90))
        font.createChar(-1, "two").addReference("bar", psMat.translate(200, 0))
        pair = font.createChar(-1, "pair")
        pair.foreground = bars((400, 490))
        pair.addReference("two", psMat.translate(0, 100))
        self.assertEqual(sorted(tuple(round(v) for v in contour.boundingBox())
                                for contour in measure.ink(font, "pair")),
                         [(200, 100, 290, 500), (400, 0, 490, 400)])


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


class AreaTest(unittest.TestCase):
    def test_holes_subtract(self):
        layer = geo.rect(0, 0, 100, 100)
        hole = geo.rect(25, 25, 75, 75)
        for contour in hole:
            contour.reverseDirection()
        layer += hole
        self.assertAlmostEqual(measure.area(layer), 100 * 100 - 50 * 50)

    def test_covered_is_the_share_inside(self):
        inner, outer = geo.rect(0, 0, 100, 100), geo.rect(50, -10, 200, 110)
        self.assertAlmostEqual(measure.covered(inner, outer), 0.5)


if __name__ == "__main__":
    unittest.main()
