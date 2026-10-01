"""Tests for tests/sfd_files.py on small synthetic SFDs.

Run: python3 -m unittest discover tests
"""
import pathlib
import sys
import tempfile
import unittest

import fontforge

# the tests' shared SFD comparison
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from sfd_files import differences

# A ring like O, as (x, y, on-curve) going round each contour: its handles lean a little, as
# the hand's do, so moving one moves the stems the autohinter finds.
OUTER = [(275, -10, 1), (150, -8, 0), (40, 120, 0), (42, 330, 1), (44, 540, 0), (150, 682, 0),
         (275, 680, 1), (400, 678, 0), (510, 540, 0), (508, 330, 1), (506, 120, 0),
         (400, -12, 0)]
INNER = [(275, 80, 1), (360, 82, 0), (420, 180, 0), (418, 330, 1), (416, 480, 0),
         (360, 590, 0), (275, 590, 1), (190, 590, 0), (130, 480, 0), (132, 330, 1),
         (134, 180, 0), (190, 78, 0)]


def moved(points, index, dx, dy):
    x, y, on = points[index]
    return [*points[:index], (x + dx, y + dy, on), *points[index + 1:]]


def split(points, index):
    """`points` with the cubic that starts at on-curve point `index` split at t = 0.5, its new
    points rounded, as a build that splits the curve writes it."""
    def mid(a, b):
        return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    p0, c1, c2, p3 = (points[(index + k) % len(points)][:2] for k in range(4))
    a, m, d = mid(p0, c1), mid(c1, c2), mid(c2, p3)
    b, c = mid(a, m), mid(m, d)
    new = [(round(x), round(y), on)
           for (x, y), on in ((a, 0), (b, 0), (mid(b, c), 1), (c, 0), (d, 0))]
    return [*points[:index + 1], *new, *points[index + 3:]]


def draw(glyph, *contours):
    """Draw the contours, each as points like OUTER's, and hint them, as the generators do."""
    layer = fontforge.layer()
    for points in contours:
        contour = fontforge.contour()
        for x, y, on in points:
            contour += fontforge.point(x, y, bool(on))
        contour.closed = True
        layer += contour
    glyph.foreground = layer
    glyph.autoHint()


class DifferencesTest(unittest.TestCase):
    """A rerun on another FontForge build may split a curve or put a control point a unit
    away, and must still match; any other change must not."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.dir = pathlib.Path(cls.tmp.name)
        font = fontforge.font()
        font.createChar(ord("O"), "O").width = 550
        # A new font is saved with OnlyBitmaps, which only drawing in a reopened copy clears, so
        # the base is drawn in one. Every variant is the base opened, changed and saved, so
        # they share its creation time and differ from it only by their change.
        cls.base = cls.dir / "base.sfd"
        font.save(str(cls.base))
        cls.redrawn("base", OUTER, INNER)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def variant(cls, name, change):
        font = fontforge.open(str(cls.base))
        change(font)
        path = cls.dir / f"{name}.sfd"
        font.save(str(path))
        return path

    @classmethod
    def redrawn(cls, name, *contours):
        return cls.variant(name, lambda font: draw(font["O"], *contours))

    def test_a_file_matches_itself(self):
        self.assertEqual(differences(self.base, self.base), [])

    def test_a_control_point_a_unit_away_matches(self):
        found = self.redrawn("control", moved(OUTER, 1, 0, -1), INNER)
        self.assertEqual(differences(self.base, found), [])

    def test_a_curve_split_in_two_matches(self):
        found = self.redrawn("split", split(OUTER, 0), INNER)
        self.assertEqual(differences(self.base, found), [])

    def test_an_on_curve_point_moved_differs(self):
        # 3 units: the tolerance stays below that, so a point moved a few units by hand shows.
        found = self.redrawn("on-curve", moved(OUTER, 3, -3, 0), INNER)
        self.assertTrue(differences(self.base, found))

    def test_a_contour_removed_differs_either_way_round(self):
        # Every point of the ring without its counter lies on the ring's outside, so only
        # measuring both ways round finds the counter missing.
        found = self.redrawn("no-counter", OUTER)
        self.assertTrue(differences(self.base, found))
        self.assertTrue(differences(found, self.base))

    def test_another_width_differs(self):
        def widen(font):
            font["O"].width = 600
        self.assertTrue(differences(self.base, self.variant("width", widen)))

    def test_another_glyph_differs(self):
        def add(font):
            font.createChar(ord("P"), "P").width = 550
        self.assertTrue(differences(self.base, self.variant("glyph", add)))

    def test_another_header_field_differs(self):
        def relicense(font):
            font.copyright = "Copyright (c) 2026, someone else"
        self.assertTrue(differences(self.base, self.variant("header", relicense)))


if __name__ == "__main__":
    unittest.main()
