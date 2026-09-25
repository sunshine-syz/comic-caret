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

SYMBOLS = "≠≈≡∞↔↕↖↗↘↙⇐⇒⇔↦✓✗�✕✖✔✘❯❮➜○●◉▷▶▹▸►◀◁◂◃◄▲△▴▵▼▽▾▿◇◆☆★☐☑☒⚠ℹ⋯⋮⇡⇣⇕"
DIAGONALS = {0x2197: 45, 0x2196: 135, 0x2199: 225, 0x2198: 315}
SHAFT = 90  # thicker than any stroke; the arrows' shafts are the hyphen's 76-81
MIDDLE_TOLERANCE = 10  # test_consistency's TOLERANCE: the hand's wobble
# Heavy mark -> the light mark it is drawn from.
HEAVY = {"✔": "✓", "✘": "✗", "✖": "✕", "❯": ">", "➜": "→"}
# The lightest of Maple Mono's ✔ ✘ ❯ against ✓ ✗ > (1.72, 1.70, 1.46). Its ➜ carries only 1.11
# of its →'s ink: another arrow, not → made heavier, so it sets no floor.
HEAVY_INK = 1.45
# How far heavy marks keep inside the cell: about ✗'s side bearing (22), so two side by side
# stay about as far apart as ✗✗.
HEAVY_SIDE = 20
# Black shape -> the white shape whose outer contour it is.
BLACK = {"●": "○", "▶": "▷", "▸": "▹", "◆": "◇", "★": "☆"}
FISHEYE_GAP = 58  # ◉'s dot clears the ring by at least Maple Mono's gap; Fira Code's is 73
# Turned glyph -> (the glyph it turns, degrees anticlockwise), as its one reference.
TURNED = {"▲": ("▶", 90), "△": ("▷", 90), "▴": ("▸", 90), "▵": ("▹", 90),
          "▼": ("▶", -90), "▽": ("▷", -90), "▾": ("▸", -90), "▿": ("▹", -90),
          "⋮": ("…", 90), "⇣": ("⇡", 180)}
SMALLER = 0.6  # ▸ ▹ ► against ▶ ▷: Maple Mono's are 0.48 of its ▶'s height
# The white across ▹'s middle. Maple Mono's, the only reference's, is 161 at our cap height;
# ours is 4 narrower, its outline a little heavier (41 against 37) to stay nearer our weight.
SMALL_COUNTER = 157


def linear(matrix):
    """A reference's matrix without its move: its turn. -0.0 equals 0.0."""
    return tuple(round(v, 6) for v in matrix[:4])


def points(contour):
    return sorted((p.x, p.y, p.on_curve) for p in contour)


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

    def test_vertical_arrows_share_one_height(self):
        # ⇡'s two dashes set it; the solid and two-headed arrows match it.
        _, y0, _, y1 = self.box(0x2191)
        for code in (0x2193, 0x2195, 0x21E1, 0x21E3, 0x21D5):
            with self.subTest(arrow=chr(code)):
                _, b0, _, b1 = self.box(code)
                self.assertAlmostEqual(b1 - b0, y1 - y0, delta=2)

    def test_up_down_double_arrow_has_the_double_arrows_heads(self):
        # ⇔ turned, its shaft lengthened: as wide as ⇔ is tall.
        x0, _, x1, _ = self.box(0x21D5)
        _, y0, _, y1 = self.box(0x21D4)
        self.assertAlmostEqual(x1 - x0, y1 - y0, delta=2)

    def test_dashed_arrow_shaft_breaks_into_two_dashes(self):
        # Each gap is at least as wide as the hyphen's stroke, so it stays open at 12 px.
        [(h0, h1)] = measure.spans_at_x(self.font["hyphen"].foreground, ADVANCE / 2)
        dashed = self.font[0x21E1].foreground
        _, y0, _, _ = dashed.boundingBox()
        spans = measure.spans_at_x(dashed, measure.ink_center(geo.trim(dashed, y1=y0 + 20)))
        # Two dashes and the head, the three pieces Font Bakery's contour_count expects of ⇡.
        self.assertEqual(len(spans), 3)
        for lower, upper in itertools.pairwise(spans):
            self.assertGreaterEqual(upper[0] - lower[1], h1 - h0)

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

    def test_signs_are_black_shapes_with_a_white_mark(self):
        # As � is: ! and i each cut out as a stroke and a dot.
        for char in "⚠ℹ":
            with self.subTest(sign=char):
                contours = list(self.font[ord(char)].foreground)
                self.assertEqual(sum(1 for c in contours if c.isClockwise()), 1)
                self.assertEqual(sum(1 for c in contours if not c.isClockwise()), 2)


class ShapeTest(unittest.TestCase):
    """The white shapes are rings in the font's stroke, and the black ones fill them in."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def height(self, char):
        _, y0, _, y1 = self.font[ord(char)].boundingBox()
        return y1 - y0

    def test_white_shapes_are_rings(self):
        for white in BLACK.values():
            with self.subTest(shape=white):
                clockwise = sorted(bool(c.isClockwise()) for c in self.font[ord(white)].foreground)
                self.assertEqual(clockwise, [False, True])  # an outline and its counter

    def test_black_shapes_are_their_white_shapes_filled(self):
        for black, white in BLACK.items():
            with self.subTest(shape=black):
                [outer] = [c for c in self.font[ord(white)].foreground if c.isClockwise()]
                [own] = list(self.font[ord(black)].foreground)
                self.assertEqual(points(own), points(outer))

    def test_small_triangles_are_about_half_size(self):
        for small, large in (("▸", "▶"), ("▹", "▷")):
            with self.subTest(shape=small):
                self.assertLessEqual(self.height(small), SMALLER * self.height(large))

    def test_small_white_triangle_keeps_its_counter(self):
        # ▹ must read white next to ▸ at 14 px, where a heavier outline fills its counter in.
        layer = self.font[ord("▹")].foreground
        _, y0, _, y1 = layer.boundingBox()
        self.assertGreaterEqual(round(measure.counter(layer, (y0 + y1) / 2)), SMALL_COUNTER)

    def test_pointer_is_long_and_flat(self):
        # ► points where ▶ stands, as Maple Mono's (559 × 270) does.
        x0, y0, x1, y1 = self.font[ord("►")].boundingBox()
        self.assertLessEqual(y1 - y0, SMALLER * self.height("▶"))
        self.assertGreaterEqual((x1 - x0) / (y1 - y0), 1.5)


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
    """Glyphs built from other glyphs. References follow a redrawing of their base; the
    outlines copied from one (●, ☑ ☒, ⇕) don't, so these tests hold them to it."""

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

    def test_turned_glyphs_are_references_turned(self):
        for char, (base, degrees) in TURNED.items():
            with self.subTest(glyph=char):
                name, matrix = self.only_reference(char)
                self.assertEqual(name, self.font[ord(base)].glyphname)
                self.assertEqual(linear(matrix), linear(psMat.rotate(math.radians(degrees))))

    def test_midline_ellipsis_is_the_ellipsis_raised(self):
        name, matrix = self.only_reference("⋯")
        self.assertEqual(name, "ellipsis")
        self.assertEqual(linear(matrix), (1, 0, 0, 1))

    def test_arrows_stand_where_the_plain_arrows_do(self):
        for char, plain in (("⇡", "↑"), ("⇣", "↓"), ("⇕", "↕")):
            with self.subTest(arrow=char):
                pairs = zip(self.middle(self.font[ord(char)]), self.middle(self.font[ord(plain)]),
                            strict=True)
                for a, b in pairs:
                    self.assertAlmostEqual(a, b, delta=MIDDLE_TOLERANCE)

    def test_marked_boxes_hold_the_whole_box(self):
        # ☑ ☒ are single outlines, since a mark crossing a reference to ☐ fails validate()
        # (0x4); so check that all of ☐ is there.
        box = self.font[ord("☐")].foreground
        for char in "☑☒":
            with self.subTest(glyph=char):
                self.assertGreaterEqual(measure.covered(box, self.font[ord(char)].foreground),
                                        0.99)

    def test_fisheye_is_a_dot_centered_in_the_ring(self):
        glyph = self.font[ord("◉")]
        self.assertEqual(len(glyph.foreground), 0)
        parts = {name: geo.transformed(measure.ink(self.font, name), matrix)
                 for name, matrix, *_ in glyph.references}
        ring_name = self.font[ord("○")].glyphname
        self.assertEqual(sorted(parts), sorted([ring_name, "bullet"]))
        ring, dot = parts[ring_name], parts["bullet"]
        for a, b in zip(self.middle(ring), self.middle(dot), strict=True):
            self.assertAlmostEqual(a, b, delta=MIDDLE_TOLERANCE)
        self.assertGreaterEqual(measure.gap(ring, dot), FISHEYE_GAP)


if __name__ == "__main__":
    unittest.main()
