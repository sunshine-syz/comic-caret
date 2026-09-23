"""The legibility pass's rules, checked on the SFD with FontForge.

Run: python3 -m unittest discover tests
"""
import pathlib
import sys
import unittest

import fontforge

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import lig_geometry as geo
import measure
from project import ADVANCE, SFD

X_HEIGHT = 473


def offsets(glyph, name):
    """(dx, dy) of each of the glyph's references to `name`, sorted."""
    # FontForge gives each reference as (name, matrix, selected).
    return sorted((matrix[4], matrix[5]) for ref, matrix, *_ in glyph.references if ref == name)


def center(glyph, dx=0):
    """The middle of the glyph's ink, moved dx."""
    x0, _, x1, _ = glyph.boundingBox()
    return (x0 + x1) / 2 + dx


class LookalikeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_l_ends_in_a_tail_where_1_has_a_foot(self):
        # 30 units up, 1's foot spans the glyph; l's tail covers little more than half as much
        # (the references: 54-59 %).
        [(l0, l1)] = measure.spans_at_y(self.font["l"].foreground, 30)
        [(f0, f1)] = measure.spans_at_y(self.font["one"].foreground, 30)
        self.assertLessEqual(l1 - l0, 0.6 * (f1 - f0))

    def test_l_is_balanced_in_the_cell(self):
        self.assertAlmostEqual(center(self.font["l"]), ADVANCE / 2, delta=10)

    def test_l_marks_stay_on_its_stem(self):
        stem = geo.trim(self.font["l"].foreground, y0=300, y1=500)
        for name, mark in (("lacute", "acute"), ("lcommaaccent", "commaaccent")):
            with self.subTest(glyph=name):
                [(dx, _)] = offsets(self.font[name], mark)
                self.assertAlmostEqual(center(self.font[mark], dx), measure.ink_center(stem),
                                       delta=10)

    def test_i_and_j_dots_are_periods_well_above_the_x_height(self):
        _, bottom, _, _ = self.font["period"].boundingBox()
        for name in ("i", "iogonek", "j"):
            with self.subTest(glyph=name):
                [(_, dy)] = offsets(self.font[name], "period")
                self.assertEqual(dy, 584)
                self.assertGreaterEqual(bottom + dy - X_HEIGHT, 90)

    def test_zero_slash_runs_through_the_middle_of_the_counter(self):
        layer = self.font["zero"].foreground
        _, y0, _, y1 = layer.boundingBox()
        left_ring, slash, right_ring = measure.spans_at_y(layer, (y0 + y1) / 2)
        self.assertLessEqual(abs((slash[0] - left_ring[1]) - (right_ring[0] - slash[1])), 10)


class ColonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_colon_is_two_periods_from_the_baseline_past_the_x_height(self):
        colon = self.font["colon"]
        self.assertEqual(len(colon.foreground), 0)
        self.assertEqual(offsets(colon, "period"), [(0, 0), (0, 356)])
        self.assertEqual(colon.boundingBox()[3], 487)

    def test_semicolon_is_the_colon_dot_over_a_comma(self):
        semicolon = self.font["semicolon"]
        self.assertEqual(len(semicolon.foreground), 0)
        self.assertEqual(offsets(semicolon, "period"), [(0, 356)])
        [(dx, dy)] = offsets(semicolon, "comma")
        self.assertEqual(dy, 0)
        # The comma's round head, above y 60, sits under the dot.
        head = geo.trim(self.font["comma"].foreground, y0=60)
        self.assertAlmostEqual(measure.ink_center(head) + dx, center(self.font["period"]),
                               delta=5)


if __name__ == "__main__":
    unittest.main()
