"""Tests for tools/lig_geometry.py on synthetic outlines.

Run: python3 -m unittest discover tests
"""
import pathlib
import sys
import unittest

import fontforge
import psMat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import lig_geometry as geo


def box(layer):
    return tuple(round(v) for v in layer.boundingBox())


def bars(*spans):
    """One layer holding a 0..100 wide rectangle for each (y0, y1)."""
    out = fontforge.layer()
    for y0, y1 in spans:
        out += geo.rect(0, y0, 100, y1)
    return out


class TrimTest(unittest.TestCase):
    def test_cuts_flat_at_the_box(self):
        self.assertEqual(box(geo.trim(geo.rect(0, 0, 100, 50), x0=20, x1=60)), (20, 0, 60, 50))
        self.assertEqual(box(geo.trim(geo.rect(0, 0, 100, 50), y1=30)), (0, 0, 100, 30))

    def test_keeps_separate_contours_and_holes(self):
        self.assertEqual(len(geo.trim(bars((0, 10), (20, 30)), x1=50)), 2)
        ring = geo.rect(0, 0, 100, 100)
        hole = geo.rect(30, 30, 70, 70)
        hole[0].reverseDirection()
        ring += hole
        self.assertEqual(len(geo.trim(ring, x1=80)), 2)


class StretchTest(unittest.TestCase):
    def test_moves_only_points_beyond_the_cut(self):
        self.assertEqual(box(geo.stretch(geo.rect(0, 0, 100, 50), 50, 30)), (0, 0, 130, 50))
        self.assertEqual(box(geo.stretch(geo.rect(0, 0, 100, 50), 50, -30)), (-30, 0, 100, 50))

    def test_band_limits_which_points_move(self):
        grown = geo.stretch(bars((0, 10), (20, 30)), 50, 40, band=(15, 35))
        self.assertEqual([box(geo.trim(grown, y1=15)), box(geo.trim(grown, y0=15))],
                         [(0, 0, 100, 10), (0, 20, 140, 30)])

    def test_leaves_its_input_alone(self):
        layer = geo.rect(0, 0, 100, 50)
        geo.stretch(layer, 50, 30)
        self.assertEqual(box(layer), (0, 0, 100, 50))


class StretchSpanTest(unittest.TestCase):
    def arrow(self):
        """A shaft from x 0 to 600 with a pointed end at 700 and a point halfway along."""
        contour = fontforge.contour()
        for x, y in ((0, 0), (0, 100), (300, 100), (600, 100), (700, 50), (600, 0)):
            contour += fontforge.point(x, y)
        contour.closed = True
        layer = fontforge.layer()
        layer += contour
        return layer

    def points(self, layer):
        return [(round(p.x), round(p.y)) for p in layer[0]]

    def test_moves_the_end_along_and_spaces_the_span_evenly(self):
        self.assertEqual(self.points(geo.stretch_span(self.arrow(), 200, 500, 150)),
                         [(0, 0), (0, 100), (350, 100), (750, 100), (850, 50), (750, 0)])

    def test_shortens_without_folding(self):
        # stretch() cannot shorten: the point at 300 would stay behind a cut end moved to 250.
        self.assertEqual(self.points(geo.stretch_span(self.arrow(), 200, 500, -250)),
                         [(0, 0), (0, 100), (217, 100), (350, 100), (450, 50), (350, 0)])

    def test_leaves_its_input_alone(self):
        layer = self.arrow()
        geo.stretch_span(layer, 200, 500, 150)
        self.assertEqual(self.points(layer)[3], (600, 100))


class RampTest(unittest.TestCase):
    def test_runs_from_0_to_1_and_clamps(self):
        self.assertEqual([geo.ramp(v, 0, 10) for v in (-5, 0, 5, 10, 15)], [0, 0, 0.5, 1, 1])

    def test_runs_downhill_when_its_ends_are_swapped(self):
        self.assertEqual(geo.ramp(2, 10, 0), 0.8)


class DisplacedTest(unittest.TestCase):
    def test_moves_points_sideways_by_the_field(self):
        moved = geo.displaced(geo.rect(0, 0, 100, 50), lambda x, y: 10 * geo.ramp(x, 40, 60))
        self.assertEqual(box(moved), (0, 0, 110, 50))

    def test_never_moves_points_vertically(self):
        moved = geo.displaced(geo.rect(0, 0, 100, 50), lambda x, y: y)
        self.assertEqual(sorted(p.y for p in moved[0]), [0, 0, 50, 50])

    def test_leaves_its_input_alone(self):
        layer = geo.rect(0, 0, 100, 50)
        geo.displaced(layer, lambda x, y: 10)
        self.assertEqual(box(layer), (0, 0, 100, 50))


class SnapEdgeTest(unittest.TestCase):
    def test_moves_corners_on_the_edge_to_the_nearest_height(self):
        contour = fontforge.contour()
        contour.moveTo(0, 0)
        contour.lineTo(0, 48)
        contour.lineTo(100, 52)
        contour.lineTo(100, 3)
        contour.closed = True
        layer = fontforge.layer()
        layer += contour
        geo.snap_edge(layer, 100, (0, 50))
        self.assertEqual(sorted((p.x, p.y) for p in layer[0]),
                         [(0, 0), (0, 48), (100, 0), (100, 50)])


class WeldTest(unittest.TestCase):
    def test_joins_along_a_shared_edge_into_one_clockwise_contour(self):
        joined = geo.weld(geo.rect(0, 0, 100, 50), geo.rect(100, 0, 200, 50), 100)
        self.assertEqual(len(joined), 1)
        self.assertEqual(box(joined), (0, 0, 200, 50))
        self.assertTrue(joined[0].isClockwise())
        self.assertFalse(joined.selfIntersects())

    def test_needs_the_edge(self):
        with self.assertRaises(ValueError):
            geo.weld(geo.rect(0, 0, 100, 50), geo.rect(120, 0, 200, 50), 100)


class UnionAndMirrorTest(unittest.TestCase):
    def test_union_merges_crossing_outlines(self):
        self.assertEqual(len(geo.union(geo.rect(0, 0, 100, 50), geo.rect(50, -20, 70, 80))), 1)

    def test_mirrors_keep_contours_clockwise(self):
        for mirrored in (geo.mirrored_x(geo.rect(0, 0, 100, 50), 150),
                         geo.mirrored_y(geo.rect(0, 0, 100, 50), 100)):
            self.assertTrue(mirrored[0].isClockwise())
        self.assertEqual(box(geo.mirrored_x(geo.rect(0, 0, 100, 50), 150)), (200, 0, 300, 50))
        self.assertEqual(box(geo.mirrored_y(geo.rect(0, 0, 100, 50), 100)), (0, 150, 100, 200))

    def test_about_applies_a_matrix_about_a_point(self):
        turned = geo.transformed(geo.rect(0, 0, 100, 50), geo.about(psMat.scale(2), 100, 50))
        self.assertEqual(box(turned), (-100, -50, 100, 50))


class CleanupTest(unittest.TestCase):
    def test_rounds_every_point(self):
        layer = geo.transformed(geo.rect(0, 0, 100, 50), psMat.translate(0.4, 0.6))
        cleaned = geo.cleanup(layer)
        self.assertTrue(all(p.x == int(p.x) and p.y == int(p.y) for p in cleaned[0]))


if __name__ == "__main__":
    unittest.main()
