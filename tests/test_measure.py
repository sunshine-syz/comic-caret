"""Tests for tools/measure.py on synthetic outlines.

Run: python3 -m unittest discover tests
"""
import math
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


class OutlineDistanceTest(unittest.TestCase):
    def test_an_extra_contour_is_as_far_as_its_farthest_point_either_way_round(self):
        # The extra bar's right edge, x = 390, lies 300 from the shared bar's, x = 90; every
        # point of the shared bar lies on both outlines, so only measuring both ways finds it.
        one, two = bars((0, 90)), bars((0, 90), (300, 390))
        self.assertAlmostEqual(measure.outline_distance(one, two), 300, delta=1)
        self.assertAlmostEqual(measure.outline_distance(two, one), 300, delta=1)

    def test_an_empty_layer_is_infinitely_far_from_a_drawn_one(self):
        self.assertEqual(measure.outline_distance(fontforge.layer(), bars((0, 90))), math.inf)
        self.assertEqual(measure.outline_distance(bars((0, 90)), fontforge.layer()), math.inf)

    def test_two_empty_layers_coincide(self):
        self.assertEqual(measure.outline_distance(fontforge.layer(), fontforge.layer()), 0)


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

    def test_length_runs_round_every_contour(self):
        layer = geo.rect(0, 0, 100, 50)
        layer += geo.rect(200, 0, 210, 10)
        self.assertAlmostEqual(measure.length(layer), 2 * (100 + 50) + 4 * 10)


class DistanceTest(unittest.TestCase):
    def test_distance_is_to_the_nearest_edge_inside_or_out(self):
        layer = geo.rect(0, 0, 100, 100)
        self.assertAlmostEqual(measure.distance((20, 50), layer), 20)
        self.assertAlmostEqual(measure.distance((130, 140), layer), 50)  # 30 across, 40 up


class OutlineTest(unittest.TestCase):
    def test_contour_order_and_starting_points_do_not_count(self):
        layer = geo.rect(0, 0, 100, 100)
        layer += geo.rect(150, 0, 200, 100)
        other = fontforge.layer()
        for contour in reversed(list(layer)):
            contour.makeFirst(2)
            other += contour
        self.assertEqual(measure.outline(layer), measure.outline(other))
        self.assertNotEqual(measure.outline(layer), measure.outline(geo.moved(other, 1, 0)))


class PiecesTest(unittest.TestCase):
    def test_each_outline_keeps_the_counters_inside_it(self):
        ring = geo.rect(0, 0, 100, 100)
        hole = geo.rect(25, 25, 75, 75)
        for contour in hole:
            contour.reverseDirection()
        layer = ring.dup()
        layer += hole
        layer += geo.rect(150, 0, 200, 100)
        found = sorted(measure.pieces(layer), key=lambda piece: piece.boundingBox())
        self.assertEqual([len(piece) for piece in found], [2, 1])
        self.assertEqual([piece.boundingBox() for piece in found],
                         [(0, 0, 100, 100), (150, 0, 200, 100)])


class EdgeTest(unittest.TestCase):
    def test_a_rectangle_has_two_edges_each_way(self):
        layer = geo.rect(0, 0, 100, 50)
        self.assertEqual(sorted(measure.vertical_edges(layer)), [(0, 0, 50), (100, 0, 50)])
        self.assertEqual(sorted(measure.horizontal_edges(layer)), [(0, 0, 100), (50, 0, 100)])

    def test_curves_and_slants_are_not_edges(self):
        slanted = fontforge.contour()
        slanted.moveTo(0, 0)
        slanted.lineTo(40, 100)
        slanted.lineTo(100, 100)
        slanted.closed = True
        layer = fontforge.layer()
        layer += slanted
        self.assertEqual(measure.vertical_edges(layer), [])
        self.assertEqual(measure.horizontal_edges(layer), [(100, 40, 100)])


if __name__ == "__main__":
    unittest.main()
