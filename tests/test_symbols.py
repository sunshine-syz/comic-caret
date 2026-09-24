"""Coding and CLI symbols: ≠ ≈ ≡ ∞, arrows, ✓ ✗ and �.

Run: python3 -m unittest discover tests
"""
import itertools
import math
import pathlib
import sys
import unittest

import fontforge
import psMat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
import lig_geometry as geo
import measure
from project import ADVANCE, SFD

SYMBOLS = "≠≈≡∞↔↕↖↗↘↙⇐⇒⇔↦✓✗\ufffd"
AXIS = 270  # the middle of - = + and of ← →'s shafts
DIAGONALS = {0x2197: 45, 0x2196: 135, 0x2199: 225, 0x2198: 315}
SHAFT = 90  # thicker than any stroke; the arrows' shafts are the hyphen's 76-81


class CoverageTest(unittest.TestCase):
    def test_symbols_are_present(self):
        font = fontforge.open(str(SFD))
        self.assertEqual([c for c in SYMBOLS if ord(c) not in font], [])


class OperatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_not_equal_slash_crosses_both_bars(self):
        glyph = self.font["notequal"]
        _, bottom, _, top = glyph.boundingBox()
        _, bar_bottom, _, bar_top = self.font["equal"].boundingBox()
        self.assertEqual(len(glyph.foreground), 1)  # slash and bars are one outline
        self.assertGreaterEqual(top - bar_top, 60)
        self.assertGreaterEqual(bar_bottom - bottom, 60)

    def test_identical_bars_are_three_equal_bars(self):
        equal = measure.spans_at_x(self.font["equal"].foreground, 275)
        bars = measure.spans_at_x(self.font["equivalence"].foreground, 275)
        self.assertEqual(len(bars), 3)
        gap = equal[1][0] - equal[0][1]
        for (b0, b1), (e0, e1) in zip(bars, equal + equal[:1]):
            self.assertAlmostEqual(b1 - b0, e1 - e0, delta=4)
        for lower, upper in itertools.pairwise(bars):
            self.assertAlmostEqual(upper[0] - lower[1], gap, delta=4)

    def test_approx_is_two_tildes(self):
        # References, so ≈ follows any redrawing of ~.
        glyph = self.font["approxequal"]
        self.assertEqual([name for name, *_ in glyph.references], ["asciitilde", "asciitilde"])
        self.assertEqual(len(glyph.foreground), 0)

    def test_approx_waves_stay_apart(self):
        tilde = self.font["asciitilde"].foreground
        waves = [geo.transformed(tilde, matrix)
                 for _, matrix, *_ in self.font["approxequal"].references]
        self.assertEqual(len(waves), 2)
        self.assertGreaterEqual(measure.gap(*waves), 60)

    def test_infinity_has_two_matching_holes(self):
        # At least the narrowest reference's holes, 155 wide and 169 tall.
        contours = list(self.font["infinity"].foreground)
        holes = [c.boundingBox() for c in contours if not c.isClockwise()]
        self.assertEqual(len(holes), 2)
        for x0, y0, x1, y1 in holes:
            self.assertGreaterEqual(x1 - x0, 155)
            self.assertGreaterEqual(y1 - y0, 169)
        (a0, b0, a1, b1), (c0, d0, c1, d1) = holes
        self.assertAlmostEqual(a1 - a0, c1 - c0, delta=4)
        self.assertAlmostEqual(b1 - b0, d1 - d0, delta=4)


class ArrowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def box(self, code):
        return self.font[code].boundingBox()

    def test_diagonals_are_the_right_arrow_turned(self):
        # Turned back, each has →'s box; only its size counts, as each is centered in the cell.
        x0, y0, x1, y1 = self.box(0x2192)
        for code, degrees in DIAGONALS.items():
            with self.subTest(arrow=chr(code)):
                back = geo.transformed(self.font[code].foreground,
                                       psMat.rotate(math.radians(-degrees)))
                b0, c0, b1, c1 = back.boundingBox()
                self.assertAlmostEqual(b1 - b0, x1 - x0, delta=2)
                self.assertAlmostEqual(c1 - c0, y1 - y0, delta=2)

    def test_double_arrows_mirror_each_other(self):
        x0, y0, x1, y1 = self.box(0x21D2)
        u0, v0, u1, v1 = self.box(0x21D0)
        self.assertAlmostEqual(u0, ADVANCE - x1, delta=3)
        self.assertAlmostEqual(u1, ADVANCE - x0, delta=3)
        self.assertEqual((v0, v1), (y0, y1))

    def test_two_headed_arrows_are_centered(self):
        for code in (0x2194, 0x2195, 0x21D4):
            with self.subTest(arrow=chr(code)):
                x0, _, x1, _ = self.box(code)
                self.assertAlmostEqual((x0 + x1) / 2, ADVANCE / 2, delta=10)

    def test_two_headed_arrows_show_shaft_between_their_heads(self):
        # Two full-size heads meet in the middle, and ↔ reads as a diamond.
        for code, spans_across in ((0x2194, measure.spans_at_x), (0x2195, measure.spans_at_y)):
            with self.subTest(arrow=chr(code)):
                x0, y0, x1, y1 = self.box(code)
                middle = (x0 + x1) / 2 if code == 0x2194 else (y0 + y1) / 2
                self.assertEqual(len(self.font[code].foreground), 1)
                [(s0, s1)] = spans_across(self.font[code].foreground, middle)
                self.assertLessEqual(s1 - s0, SHAFT)

    def test_shafts_lie_on_the_axis(self):
        for code in (0x2194, 0x21A6, 0x21D0, 0x21D2, 0x21D4):
            with self.subTest(arrow=chr(code)):
                spans = measure.spans_at_x(self.font[code].foreground, 275)
                middle = (spans[0][0] + spans[-1][1]) / 2
                self.assertAlmostEqual(middle, AXIS, delta=8)

    def test_maps_to_bar_is_as_tall_as_the_head(self):
        _, y0, _, y1 = self.box(0x2192)
        [(b0, b1)] = measure.spans_at_x(self.font[0x21A6].foreground, 80)
        self.assertAlmostEqual(b1 - b0, y1 - y0, delta=12)


class MarkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_marks_are_larger_than_times(self):
        _, t0, _, t1 = self.font["multiply"].boundingBox()
        for code in (0x2713, 0x2717):
            with self.subTest(mark=chr(code)):
                _, y0, _, y1 = self.font[code].boundingBox()
                self.assertGreaterEqual((y1 - y0) - (t1 - t0), 100)

    def test_ballot_x_is_not_the_letter_x(self):
        # About as wide as it is tall and under cap height, as Maple Mono's (494 × 486); at X's
        # tall, narrow proportions [✗] and [X] look the same.
        x0, y0, x1, y1 = self.font[0x2717].boundingBox()
        self.assertAlmostEqual((x1 - x0) / (y1 - y0), 1, delta=0.1)
        self.assertLessEqual(y1, self.font["X"].boundingBox()[3] - 60)
        self.assertAlmostEqual((x0 + x1) / 2, ADVANCE / 2, delta=5)

    def test_replacement_character_is_a_diamond_with_a_question_mark(self):
        glyph = self.font[0xFFFD]
        contours = list(glyph.foreground)
        self.assertEqual(sum(1 for c in contours if c.isClockwise()), 1)
        self.assertEqual(sum(1 for c in contours if not c.isClockwise()), 2)  # hook and dot
        x0, y0, x1, y1 = glyph.boundingBox()
        self.assertAlmostEqual((x0 + x1) / 2, ADVANCE / 2, delta=5)
        self.assertAlmostEqual((y0 + y1) / 2, 334, delta=10)


if __name__ == "__main__":
    unittest.main()
