"""Coding, prompt and CLI symbols: ≠ ≈ ≡ ∞, arrows, marks, shapes, boxes and signs.

Run: python3 -m unittest discover tests

Centering, the math axis and mirrored pairs are checked in test_consistency.py.
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

SYMBOLS = "≠≈≡∞↔↕↖↗↘↙⇐⇒⇔↦✓✗�✕✖✔✘❯❮➜"
DIAGONALS = {0x2197: 45, 0x2196: 135, 0x2199: 225, 0x2198: 315}
SHAFT = 90  # thicker than any stroke; the arrows' shafts are the hyphen's 76-81
MIDDLE_TOLERANCE = 10  # test_consistency's TOLERANCE: the hand's wobble
# Heavy mark -> the light mark it is drawn from.
HEAVY = {"✔": "✓", "✘": "✗", "✖": "✕", "❯": ">", "➜": "→"}
HEAVY_INK = 1.45  # the lightest of Maple Mono's heavy-to-light ink ratios (1.46-1.72)
# How far heavy marks keep inside the cell: about ✗'s side bearing (22), so two side by side
# stay about as far apart as ✗✗.
HEAVY_SIDE = 20
# Mirrored glyph -> the glyph it mirrors. An outline, since validate() flags a flipped
# reference (0x10).
MIRRORED_FROM = {"❮": "❯"}


def linear(matrix):
    """A reference's matrix without its move: its turn. -0.0 equals 0.0."""
    return tuple(round(v, 6) for v in matrix[:4])


def outline(layer):
    """The layer's points, contour by contour, in an order that ignores where each starts."""
    return sorted(sorted((p.x, p.y, p.on_curve) for p in contour) for contour in layer)


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

    def test_two_headed_arrows_show_shaft_between_their_heads(self):
        # Two full-size heads meet in the middle, and ↔ reads as a diamond.
        for code, spans_across in ((0x2194, measure.spans_at_x), (0x2195, measure.spans_at_y)):
            with self.subTest(arrow=chr(code)):
                x0, y0, x1, y1 = self.box(code)
                middle = (x0 + x1) / 2 if code == 0x2194 else (y0 + y1) / 2
                self.assertEqual(len(self.font[code].foreground), 1)
                [(s0, s1)] = spans_across(self.font[code].foreground, middle)
                self.assertLessEqual(s1 - s0, SHAFT)


class MarkTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_marks_are_larger_than_times(self):
        _, t0, _, t1 = self.font["multiply"].boundingBox()
        for code in (0x2713, 0x2717, 0x2715):
            with self.subTest(mark=chr(code)):
                _, y0, _, y1 = self.font[code].boundingBox()
                self.assertGreaterEqual((y1 - y0) - (t1 - t0), 100)

    def test_ballot_x_is_not_the_letter_x(self):
        # About as wide as it is tall and under cap height, as Maple Mono's (494 × 486); at X's
        # tall, narrow proportions [✗] and [X] look the same.
        x0, y0, x1, y1 = self.font[0x2717].boundingBox()
        self.assertAlmostEqual((x1 - x0) / (y1 - y0), 1, delta=0.1)
        self.assertLessEqual(y1, self.font["X"].boundingBox()[3] - 60)

    def test_replacement_character_is_a_diamond_with_a_question_mark(self):
        contours = list(self.font[0xFFFD].foreground)
        self.assertEqual(sum(1 for c in contours if c.isClockwise()), 1)
        self.assertEqual(sum(1 for c in contours if not c.isClockwise()), 2)  # hook and dot



class HeavyMarkTest(unittest.TestCase):
    """✔ ✘ ✖ ❯ ➜ are ✓ ✗ ✕ > → drawn heavier, so each pair differs only in weight."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def ink(self, char):
        return measure.ink(self.font, self.font[ord(char)].glyphname)

    def test_heavy_marks_keep_their_light_marks_middle(self):
        for heavy, light in HEAVY.items():
            with self.subTest(mark=heavy):
                h0, i0, h1, i1 = self.ink(heavy).boundingBox()
                l0, m0, l1, m1 = self.ink(light).boundingBox()
                self.assertAlmostEqual((h0 + h1) / 2, (l0 + l1) / 2, delta=MIDDLE_TOLERANCE)
                self.assertAlmostEqual((i0 + i1) / 2, (m0 + m1) / 2, delta=MIDDLE_TOLERANCE)

    def test_heavy_marks_carry_more_ink(self):
        for heavy, light in HEAVY.items():
            with self.subTest(mark=heavy):
                ratio = measure.area(self.ink(heavy)) / measure.area(self.ink(light))
                self.assertGreaterEqual(ratio, HEAVY_INK)

    def test_heavy_marks_stay_clear_of_their_neighbours(self):
        for heavy in HEAVY:
            with self.subTest(mark=heavy):
                x0, _, x1, _ = self.ink(heavy).boundingBox()
                self.assertGreaterEqual(x0, HEAVY_SIDE)
                self.assertLessEqual(x1, ADVANCE - HEAVY_SIDE)


class BuiltFromTest(unittest.TestCase):
    """Glyphs built from other glyphs, so they follow any redrawing of them."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def only_reference(self, char):
        """(base glyph name, matrix) of a glyph that is one reference and nothing else."""
        glyph = self.font[ord(char)]
        self.assertEqual(len(glyph.foreground), 0)
        [(name, matrix, *_)] = glyph.references
        return name, matrix

    def middle(self, outline):
        x0, y0, x1, y1 = outline.boundingBox()
        return (x0 + x1) / 2, (y0 + y1) / 2

    def test_mirrored_glyphs_are_their_base_mirrored(self):
        for char, base in MIRRORED_FROM.items():
            with self.subTest(glyph=char):
                mirrored = geo.mirrored_x(self.font[ord(base)].foreground, ADVANCE / 2)
                self.assertEqual(outline(self.font[ord(char)].foreground), outline(mirrored))


if __name__ == "__main__":
    unittest.main()
