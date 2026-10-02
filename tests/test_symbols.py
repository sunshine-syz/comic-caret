"""Coding, prompt, CLI and math symbols: ≠ ≈ ≡ ∞ ∑ ∫, arrows, marks, shapes, boxes and signs.

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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # the tests' shared helpers
import lig_geometry as geo
import measure
from helpers import bullet_seam
from measure import outline
from project import ADVANCE, ROUNDING, SFD, WOBBLE

SYMBOLS = ("≠≈≡∞←→↔↕↖↗↘↙⇐⇒⇔↦✓✗�✕✖✔✘❯❮➜○●◉▷▶▹▸►◀◁◂◃◄▲△▴▵▼▽▾▿◇◆☆★☐☑☒⚠ℹ⋯⋮⇡⇣⇕"
           "⎿⏺✢✳✶✻✽⏵⏸⧉∴※◯■□▪▫◦❰❱⏎↵⇥⇤↹␣⍽⌘⌥⌃⇧⌫⌦⎋↳↰↱↲↩↪⇑⇓∂∆∇∏∑√∫◊∅′″‖⟨⟩₹₺₽₩₫‣‐‑‒―₦₱₿ʼʻʺ№ℓ℮℃℉⇞⇟⇪⇦⇨⇩"
           "◐◑◒◓◴◵◶◷◜◝◞◟◠◡◰◱◲◳◢◣◤◥▮▯◎⊙⦾⦿◌◍⧆⧇☰☱☲☳☴☵☶☷✷✸✹✺⊶⊷☖☗▰▱∙‼"
           "↑↓≤≥−∀∃∄•†‡…‰™€–—‘’‚“”„‹›«»")
# Typed arrow -> the ligature head it is as tall as, so → beside -> reads as the same arrow.
LIGATURE_HEADS = {"→": "greater.arrow", "⇒": "greater.darrow", "←": "less.arrow",
                  "⇐": "less.darrow"}
SHAFT = 90  # thicker than any stroke; the arrows' shafts are the hyphen's 76-81
# How far ≠'s slash runs past ='s bars: at least the narrowest reference's, Fira Code's below its
# bars at our cap height (Intel One Mono's 147, Maple Mono's 174).
NOT_EQUAL_REACH = 146
# The white between ≈'s waves: at least the narrowest reference's, Intel One Mono's at our cap
# height (Fira Code's 79, Maple Mono's 85).
APPROX_GAP = 69
# The white between ¦'s pieces: at least the narrowest reference's, Maple Mono's at our cap
# height (Fira Code's 192).
BROKEN_BAR_GAP = 162
# How much taller each mark stands than ×: at least the least of the references that have it,
# measured at our cap height. ✓: Intel One Mono's 99 (Maple Mono 103, Fira Code 327); ✗: Maple
# Mono's 131, the one reference with it; ✕: Maple Mono's 68, the one reference with it.
MARK_OVER_TIMES = {"✓": 99, "✗": 131, "✕": 68}
# Marks short of their floor, held to the least floor until a proof decides their size.
SHORT_MARKS = {}
# Heavy mark -> the light mark it is drawn from. ➜ is another arrow: → takes the -> ligature's
# head, which no one-cell arrow pushed out 23 could hold, and Maple Mono's ➜ (416 tall) is
# another arrow than its → too; it stands where → does (BuiltFromTest).
HEAVY = {"✔": "✓", "✘": "✗", "✖": "✕"}
# The lightest of Maple Mono's ✔ ✘ ❯ against ✓ ✗ > (1.72, 1.70, 1.46).
HEAVY_INK = 1.45
# Mark -> (the lighter glyph, how many times its ink the mark carries at least). ❯ is no heavy
# >, but the tall ornament JetBrains Mono, Cascadia Code and Maple Mono draw (its rows are in
# test_consistency); like theirs, it still carries more ink than >: at least the lightest's,
# Cascadia Code's 1.39 times (Maple Mono's 1.46, JetBrains Mono's 1.70).
HEAVIER = {**{heavy: (light, HEAVY_INK) for heavy, light in HEAVY.items()}, "❯": (">", 1.39)}
# •'s width: at least the smallest reference's, Maple Mono's 220 at our cap height, less the
# hand's wobble.
BULLET_WIDTH = 220 - WOBBLE
# Every symbol keeps at least as far inside the cell as ●, the widest full-size shape, so two
# side by side stay as far apart as ●●: a seam at 16 px, as in Fira Code. These come no closer
# to the edges than a reference's: ∞ and � (11 inside) as Fira Code's ∞ and Maple Mono's �,
# which run past the cell, and ™ (13) as Fira Code's, 11 inside on the left.
OWN_SIDES = "∞�™"
# Black shape -> the white shape whose outer contour it is.
BLACK = {"●": "○", "▶": "▷", "▸": "▹", "◆": "◇", "★": "☆", "■": "☐", "▪": "▫", "▮": "▯",
         "☗": "☖", "▰": "▱"}
# Claude Code's spinner cycles through the first, cli-spinners' star spinner through the
# second; frames of different sizes would make them pulse.
SPINNERS = ("✢✳✶✻✽", "✶✷✸✹✺")
MEDIA = "⏵⏸⏺"  # media controls, which status lines show side by side
# Keyboard symbols, which key hints string together (⌃⌥⌘⇧⏎): one band on the math axis, and
# ⌃, the up arrowhead, at its top. Not ⇪, ⇧ lifted over a bar, which rises past the band.
KEYS = "⌘⌥⇧⎋⏎⇦⇨⇩"
# Symbols drawn as separate pieces, which keep apart (№'s o and its bar sit as close as º's).
PIECES = "※⧉⇥⇤↹⎋⌦⌫℃℉"
FISHEYE_GAP = 58  # ◉'s dot clears the ring by at least Maple Mono's gap; Fira Code's is 73
# Turned glyph -> (the glyph it turns, degrees anticlockwise), as its one reference.
TURNED = {"▲": ("▶", 90), "△": ("▷", 90), "▴": ("▸", 90), "▵": ("▹", 90),
          "▼": ("▶", -90), "▽": ("▷", -90), "▾": ("▸", -90), "▿": ("▹", -90),
          "⋮": ("…", 90), "⇣": ("⇡", 180), "⇓": ("⇑", 180), "↰": ("↳", 180),
          "↱": ("↲", 180), "∇": ("∆", 180), "↙": ("↗", 180), "↘": ("↖", 180),
          "⇦": ("⇧", 90), "⇨": ("⇧", -90), "⇩": ("⇧", 180), "◤": ("◢", 180), "◥": ("◣", 180),
          "¡": ("!", 180), "¿": ("?", 180)}
SMALLER = 0.6  # ▸ ▹ ► ▪ ▫ against ▶ ▷ ■ □: Maple Mono's are 0.48 and 0.5 of theirs
# The white across ▹'s middle, ▫'s and ◦'s, at least the narrowest reference's: Maple Mono's
# ▹ and ◦, the only reference's, and Fira Code's ▫, at our cap height.
SMALL_COUNTER = 159
SMALL_SQUARE_COUNTER = 122
WHITE_BULLET_COUNTER = 144
# Double mark -> (the single mark, the white between its two copies at their middle): at
# least the narrowest reference's, scaled to our cell: Maple Mono's ″ and ‼, the only
# reference's, Fira Code's ‖ (Maple Mono's 156), and Fira Code's “ ” „ (Maple Mono's 103-125,
# Intel One Mono's 119-120).
DOUBLES = {"″": ("′", 108), "‖": ("|", 90), "‼": ("!", 110),
           "“": ("‘", 101), "”": ("’", 102), "„": (",", 100)}
# How far ✗'s top stays under X's: at least Maple Mono's, the one reference with ✗, at our cap
# height.
BALLOT_UNDER_X = 100


def linear(matrix):
    """A reference's matrix without its move: its turn. -0.0 equals 0.0."""
    return tuple(round(v, 6) for v in matrix[:4])


def weight_tolerance(font):
    """How far a stroke drawn from another may stray from its weight: as far as the pen's
    weight strays along |'s straight middle, and both edges' rounding."""
    bar = font["bar"].foreground
    _, y0, _, y1 = bar.boundingBox()
    widths = [x1 - x0 for y in range(round(y0) + 100, round(y1) - 100, 10)
              for x0, x1 in measure.spans_at_y(bar, y)]
    return max(widths) - min(widths) + 2 * ROUNDING


class CoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_symbols_are_present(self):
        self.assertEqual([c for c in SYMBOLS if ord(c) not in self.font], [])

    def test_symbols_stay_clear_of_their_neighbours(self):
        x0, _, x1, _ = self.font[ord("●")].boundingBox()
        side = min(x0, ADVANCE - x1)
        for char in SYMBOLS:
            if char not in OWN_SIDES:
                with self.subTest(symbol=char):
                    x0, _, x1, _ = self.font[ord(char)].boundingBox()
                    self.assertGreaterEqual(min(x0, ADVANCE - x1), side)


class OperatorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))
        cls.weight = weight_tolerance(cls.font)

    def test_not_equal_slash_crosses_both_bars(self):
        glyph = self.font["notequal"]
        _, bottom, _, top = glyph.boundingBox()
        _, bar_bottom, _, bar_top = self.font["equal"].boundingBox()
        self.assertEqual(len(glyph.foreground), 1)  # slash and bars are one outline
        self.assertGreaterEqual(top - bar_top, NOT_EQUAL_REACH)
        self.assertGreaterEqual(bar_bottom - bottom, NOT_EQUAL_REACH)

    def test_identical_bars_are_three_equal_bars(self):
        # ≡'s bars weigh as ='s, within the pen's measured weight tolerance, and are spaced as
        # ='s, within the hand's wobble.
        equal = measure.spans_at_x(self.font["equal"].foreground, 275)
        bars = measure.spans_at_x(self.font["equivalence"].foreground, 275)
        self.assertEqual(len(bars), 3)
        gap = equal[1][0] - equal[0][1]
        for (b0, b1), (e0, e1) in zip(bars, equal + equal[:1]):
            self.assertAlmostEqual(b1 - b0, e1 - e0, delta=self.weight)
        for lower, upper in itertools.pairwise(bars):
            self.assertAlmostEqual(upper[0] - lower[1], gap, delta=WOBBLE)

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
        self.assertGreaterEqual(measure.gap(*waves), APPROX_GAP)

    def test_not_sign_bar_lies_on_the_hyphen(self):
        # Its bar is the hyphen's stroke, as Fira Code's is, and the drop hangs below it.
        [(b0, b1)] = measure.spans_at_x(self.font["logicalnot"].foreground, ADVANCE / 2)
        _, h0, _, h1 = self.font["hyphen"].boundingBox()
        self.assertAlmostEqual((b0 + b1) / 2, (h0 + h1) / 2, delta=WOBBLE)

    def test_broken_bar_is_the_bar_broken(self):
        # As long as |, as in both references that have ¦, broken into two pieces.
        layer = self.font["brokenbar"].foreground
        _, y0, _, y1 = layer.boundingBox()
        _, b0, _, b1 = self.font["bar"].boundingBox()
        self.assertAlmostEqual(y0, b0, delta=WOBBLE)
        self.assertAlmostEqual(y1, b1, delta=WOBBLE)
        x0, _, x1, _ = layer.boundingBox()
        (_, low), (high, _) = measure.spans_at_x(layer, (x0 + x1) / 2)
        self.assertGreaterEqual(high - low, BROKEN_BAR_GAP)

    def test_partial_stands_no_taller_than_six(self):
        # Its hook tops out at 6's height or under, as in both references that have ∂.
        self.assertLessEqual(self.font["partialdiff"].boundingBox()[3],
                             self.font["six"].boundingBox()[3])

    def test_infinity_has_two_matching_holes(self):
        # At least the narrowest reference's holes, 155 wide and 169 tall, and each the other
        # mirrored within the hand's wobble.
        contours = list(self.font["infinity"].foreground)
        holes = [c.boundingBox() for c in contours if not c.isClockwise()]
        self.assertEqual(len(holes), 2)
        for x0, y0, x1, y1 in holes:
            self.assertGreaterEqual(x1 - x0, 155)
            self.assertGreaterEqual(y1 - y0, 169)
        (a0, b0, a1, b1), (c0, d0, c1, d1) = holes
        self.assertAlmostEqual(a1 - a0, c1 - c0, delta=WOBBLE)
        self.assertAlmostEqual(b1 - b0, d1 - d0, delta=WOBBLE)


class ArrowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def box(self, code):
        return self.font[code].boundingBox()

    def test_typed_arrows_are_as_tall_as_the_ligature_heads(self):
        # ↖ ↗ ↘ ↙ keep to themselves (mirrored and turned, in test_consistency and TURNED):
        # → turned 45° would leave the cell.
        for char, head in LIGATURE_HEADS.items():
            with self.subTest(arrow=char):
                _, y0, _, y1 = self.box(ord(char))
                _, h0, _, h1 = self.font[head].boundingBox()
                self.assertAlmostEqual(y0, h0, delta=2 * ROUNDING)
                self.assertAlmostEqual(y1, h1, delta=2 * ROUNDING)

    def test_vertical_arrows_share_one_height(self):
        # ⇡'s two dashes set it; the solid and two-headed arrows match it.
        _, y0, _, y1 = self.box(0x2191)
        for code in (0x2193, 0x2195, 0x21E1, 0x21E3, 0x21D5, 0x21D1, 0x21D3, 0x21DE, 0x21DF):
            with self.subTest(arrow=chr(code)):
                _, b0, _, b1 = self.box(code)
                self.assertAlmostEqual(b1 - b0, y1 - y0, delta=2 * ROUNDING)

    def test_up_down_double_arrow_has_the_double_arrows_heads(self):
        # ⇔ turned, its shaft lengthened: as wide as ⇔ is tall.
        x0, _, x1, _ = self.box(0x21D5)
        _, y0, _, y1 = self.box(0x21D4)
        self.assertAlmostEqual(x1 - x0, y1 - y0, delta=2 * ROUNDING)

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

    def test_turning_arrows_point_along_the_math_axis(self):
        # ↵ ↩ ↪ rise above → and ←, but their heads stay where →'s and ←'s are; near the tip
        # the head is one span, its middle the shaft's.
        _, y0, _, y1 = self.box(ord("-"))
        for char in "↵↩↪":
            with self.subTest(arrow=char):
                x0, _, x1, _ = self.box(ord(char))
                points_left = char != "↪"
                layer = self.font[ord(char)].foreground
                [(s0, s1)] = measure.spans_at_x(layer, x0 + 40 if points_left else x1 - 40)
                self.assertAlmostEqual((s0 + s1) / 2, (y0 + y1) / 2, delta=WOBBLE)

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
        over = {}
        for mark, floor in MARK_OVER_TIMES.items():
            _, y0, _, y1 = self.font[ord(mark)].boundingBox()
            over[mark] = (y1 - y0) - (t1 - t0)
        # The exceptions are exactly the marks below their own floor, so one redrawn to its
        # floor fails until its entry goes.
        short = {mark for mark, floor in MARK_OVER_TIMES.items() if over[mark] < floor}
        self.assertEqual(short, set(SHORT_MARKS), over)
        for mark, floor in MARK_OVER_TIMES.items():
            with self.subTest(mark=mark):
                if mark in SHORT_MARKS:
                    floor = min(MARK_OVER_TIMES.values())
                self.assertGreaterEqual(over[mark], floor, SHORT_MARKS.get(mark))

    def test_ballot_x_is_not_the_letter_x(self):
        # About as wide as it is tall and well under X's top, as Maple Mono's (494 × 486); at
        # X's tall, narrow proportions [✗] and [X] look the same.
        x0, y0, x1, y1 = self.font[0x2717].boundingBox()
        self.assertAlmostEqual((x1 - x0) / (y1 - y0), 1, delta=0.1)
        self.assertLessEqual(y1, self.font["X"].boundingBox()[3] - BALLOT_UNDER_X)

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
                self.assertEqual(outline([own]), outline([outer]))

    def test_small_shapes_are_about_half_size(self):
        for small, large in (("▸", "▶"), ("▹", "▷"), ("▪", "■"), ("▫", "□")):
            with self.subTest(shape=small):
                self.assertLessEqual(self.height(small), SMALLER * self.height(large))

    def test_small_white_triangle_keeps_its_counter(self):
        # ▹ must read white next to ▸ at 14 px, where a heavier outline fills its counter in.
        layer = self.font[ord("▹")].foreground
        _, y0, _, y1 = layer.boundingBox()
        self.assertGreaterEqual(round(measure.counter(layer, (y0 + y1) / 2)), SMALL_COUNTER)

    def test_small_white_shapes_keep_their_counters(self):
        for char, floor in (("▫", SMALL_SQUARE_COUNTER), ("◦", WHITE_BULLET_COUNTER)):
            with self.subTest(shape=char):
                layer = self.font[ord(char)].foreground
                _, y0, _, y1 = layer.boundingBox()
                self.assertGreaterEqual(round(measure.counter(layer, (y0 + y1) / 2)), floor)

    def radius(self, char):
        """How far the glyph's ink reaches from the middle of its ink box, the farthest way."""
        layer = self.font[ord(char)].foreground
        x0, y0, x1, y1 = layer.boundingBox()
        middle = psMat.translate(-(x0 + x1) / 2, -(y0 + y1) / 2)
        return max(geo.transformed(layer, psMat.compose(middle, psMat.rotate(math.radians(a))))
                   .boundingBox()[2] for a in range(0, 360, 5))

    def test_spinner_frames_share_one_size(self):
        # Their middles are held by test_consistency's CENTERED and ON_AXIS.
        for spinner in SPINNERS:
            first = self.radius(spinner[0])
            for char in spinner[1:]:
                with self.subTest(frame=char):
                    self.assertAlmostEqual(self.radius(char), first, delta=WOBBLE)

    def test_media_controls_share_one_height(self):
        first = self.height(MEDIA[0])
        for char in MEDIA[1:]:
            with self.subTest(control=char):
                self.assertAlmostEqual(self.height(char), first, delta=2 * ROUNDING)

    def test_keyboard_symbols_share_one_band(self):
        # Within the hand's wobble: where two strokes meet in a point, as atop ⇧ and ⌃, their
        # caps reach a little past it.
        _, y0, _, y1 = self.font[ord(KEYS[0])].boundingBox()
        for char in KEYS[1:]:
            with self.subTest(key=char):
                _, b0, _, b1 = self.font[ord(char)].boundingBox()
                self.assertAlmostEqual(b0, y0, delta=WOBBLE)
                self.assertAlmostEqual(b1, y1, delta=WOBBLE)
        self.assertAlmostEqual(self.font[ord("⌃")].boundingBox()[3], y1, delta=WOBBLE)

    def test_visible_spaces_lie_on_the_underscore(self):
        # ␣ ⍽ stand for a space where _ would go, so their bottoms line up with it.
        bottom = self.font["underscore"].boundingBox()[1]
        for char in "␣⍽":
            with self.subTest(space=char):
                self.assertAlmostEqual(self.font[ord(char)].boundingBox()[1], bottom,
                                       delta=WOBBLE)

    def test_bullet_is_as_wide_as_the_smallest_reference_bullet(self):
        x0, _, x1, _ = self.font[ord("•")].boundingBox()
        self.assertGreaterEqual(x1 - x0, BULLET_WIDTH)

    def test_white_bullet_stands_where_the_bullet_does(self):
        # As in every reference, so • and ◦ line up in nested lists.
        white, black = self.font[ord("◦")].boundingBox(), self.font[ord("•")].boundingBox()
        for a, b in ((white[0] + white[2], black[0] + black[2]),
                     (white[1] + white[3], black[1] + black[3])):
            self.assertAlmostEqual(a / 2, b / 2, delta=WOBBLE)

    def test_pointer_is_long_and_flat(self):
        # ► points where ▶ stands, as Maple Mono's (559 × 270) does.
        x0, y0, x1, y1 = self.font[ord("►")].boundingBox()
        self.assertLessEqual(y1 - y0, SMALLER * self.height("▶"))
        self.assertGreaterEqual((x1 - x0) / (y1 - y0), 1.5)


class HeavyMarkTest(unittest.TestCase):
    """✔ ✘ ✖ are ✓ ✗ ✕ drawn heavier, so each pair differs only in weight."""

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
                self.assertAlmostEqual((h0 + h1) / 2, (l0 + l1) / 2, delta=WOBBLE)
                self.assertAlmostEqual((i0 + i1) / 2, (m0 + m1) / 2, delta=WOBBLE)

    def test_heavy_marks_carry_more_ink(self):
        for heavy, (light, floor) in HEAVIER.items():
            with self.subTest(mark=heavy):
                ratio = measure.area(self.ink(heavy)) / measure.area(self.ink(light))
                self.assertGreaterEqual(ratio, floor)


class ApartTest(unittest.TestCase):
    """Parts of a symbol keep at least ●●'s seam between them, so they stay apart at 16 px."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))
        cls.seam = bullet_seam(cls.font)

    def pieces(self, char):
        return measure.pieces(self.font[ord(char)].foreground)

    def test_pieces_keep_apart(self):
        # ※'s dots and X, ⧉'s squares, ⇥ ⇤ ↹'s arrows and bars (Font Bakery's contour_count
        # expects them apart), ⎋'s ring and arrow, and ⌫ ⌦'s tag and ×.
        for char in PIECES:
            pieces = self.pieces(char)
            with self.subTest(symbol=char):
                self.assertGreater(len(pieces), 1)
                for a, b in itertools.combinations(pieces, 2):
                    self.assertGreaterEqual(measure.gap(a, b), self.seam)


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

    def test_double_marks_are_the_single_mark_twice(self):
        for char, (single, floor) in DOUBLES.items():
            with self.subTest(glyph=char):
                glyph = self.font[ord(char)]
                self.assertEqual(len(glyph.foreground), 0)
                [(a, first, *_), (b, second, *_)] = glyph.references
                self.assertEqual({self.base(a), self.base(b)},
                                 {self.base(self.font[ord(single)].glyphname)})
                self.assertEqual(first[:4] + first[5:], second[:4] + second[5:])
                layer = measure.ink(self.font, glyph.glyphname)
                _, y0, _, y1 = layer.boundingBox()
                self.assertGreaterEqual(measure.counter(layer, (y0 + y1) / 2), floor)

    def test_double_exclamation_dots_keep_apart(self):
        # ‼'s dots are wider than its stems, so the white between them is the narrow gap:
        # at least Maple Mono's 93, the only reference's, measured through the dots.
        _, y0, _, _ = self.font["exclam"].boundingBox()
        dots = measure.spans_at_y(measure.ink(self.font, self.font[ord("‼")].glyphname), y0 + 50)
        self.assertEqual(len(dots), 2)
        self.assertGreaterEqual(dots[1][0] - dots[0][1], 93)

    def test_midline_ellipsis_is_the_ellipsis_raised(self):
        name, matrix = self.only_reference("⋯")
        self.assertEqual(name, "ellipsis")
        self.assertEqual(linear(matrix), (1, 0, 0, 1))

    def test_arrows_stand_where_the_plain_arrows_do(self):
        for char, plain in (("⇡", "↑"), ("⇣", "↓"), ("⇕", "↕"), ("⇑", "↑"), ("⇓", "↓"),
                            ("➜", "→"), ("⇞", "↑"), ("⇟", "↓")):
            with self.subTest(arrow=char):
                pairs = zip(self.middle(self.font[ord(char)]), self.middle(self.font[ord(plain)]),
                            strict=True)
                for a, b in pairs:
                    self.assertAlmostEqual(a, b, delta=WOBBLE)

    def base(self, name):
        """The glyph that `name` is one unmoved reference to, followed down, or `name`."""
        glyph = self.font[name]
        if len(glyph.foreground) == 0 and len(glyph.references) == 1:
            [(base, matrix, *_)] = glyph.references
            if matrix == psMat.identity():
                return self.base(base)
        return name

    def test_same_shapes_are_references(self):
        # Where every reference draws two characters alike, one is the other: ∆ as Fira Code,
        # the only reference with ∆, draws it. And ′ is the modifier prime ʹ: Maple Mono, the
        # only reference with ′, draws the two alike, only set apart in the cell. The modifier
        # letters ʼ ʻ are ’ ‘ (Intel One Mono and Maple Mono; Fira Code's ʼ is its own
        # apostrophe, which here would read as ') and ʺ is ″ (Fira Code and Maple Mono).
        for char, base in (("◯", "○"), ("□", "☐"), ("∆", "Δ"), ("′", "ʹ"), ("ʼ", "’"),
                           ("ʻ", "‘"), ("ʺ", "″")):
            with self.subTest(glyph=char):
                name, matrix = self.only_reference(char)
                self.assertEqual(name, self.font[ord(base)].glyphname)
                self.assertEqual(matrix, psMat.identity())

    def test_line_extension_is_the_dash_lines_middle_piece(self):
        # So a row of ⎯ joins into the line -- draws, as Vitest's dividers need.
        self.assertEqual(self.only_reference("⎯"), ("hyphen.mid", psMat.identity()))

    def test_media_shapes_are_the_black_shapes_smaller(self):
        for char, base in (("⏺", "●"), ("⏵", "▶")):
            with self.subTest(glyph=char):
                name, matrix = self.only_reference(char)
                self.assertEqual(name, self.font[ord(base)].glyphname)
                scale, skew, turn, other = linear(matrix)
                self.assertEqual((skew, turn), (0, 0))
                self.assertEqual(scale, other)
                self.assertLess(scale, 1)

    def test_therefore_is_three_periods(self):
        # Two on the colon's lower dot, the third on its upper dot, midway between them.
        glyph = self.font[ord("∴")]
        self.assertEqual(len(glyph.foreground), 0)
        self.assertEqual([name for name, *_ in glyph.references], ["period"] * 3)
        (a, low), (b, low2), (top_x, top_y) = sorted(
            ((m[4], m[5]) for _, m, *_ in glyph.references), key=lambda xy: (xy[1], xy[0]))
        colon = sorted(m[5] for _, m, *_ in self.font["colon"].references)
        self.assertEqual((low, low2, top_y), (colon[0], colon[0], colon[1]))
        self.assertAlmostEqual(top_x, (a + b) / 2, delta=ROUNDING)

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
            self.assertAlmostEqual(a, b, delta=WOBBLE)
        self.assertGreaterEqual(measure.gap(ring, dot), FISHEYE_GAP)


class LetterlikeTest(unittest.TestCase):
    """№ ℓ ℮ ℃ ℉: letters, or pieces of letters, drawn together in the cell. Their rows and
    centring are in test_consistency.py."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))
        cls.seam = bullet_seam(cls.font)

    def pieces(self, char):
        return measure.pieces(self.font[ord(char)].foreground)

    def test_numero_is_a_full_height_N_beside_a_raised_o(self):
        # N keeps its height, narrowed to make room, and º's o stands to its right as high as
        # º, its bar under it; Fira Code and Maple Mono set № so.
        pieces = self.pieces("№")
        self.assertEqual(len(pieces), 3)
        n = max(pieces, key=lambda p: p.boundingBox()[3] - p.boundingBox()[1])
        [o] = [p for p in pieces if len(p) == 2]
        [bar] = [p for p in pieces if p is not n and p is not o]
        _, n0, _, n1 = n.boundingBox()
        _, N0, _, N1 = self.font["N"].boundingBox()
        self.assertAlmostEqual(n0, N0, delta=ROUNDING)
        self.assertAlmostEqual(n1, N1, delta=ROUNDING)
        self.assertAlmostEqual(o.boundingBox()[3], self.font["ordmasculine"].boundingBox()[3],
                               delta=WOBBLE)
        self.assertLess(bar.boundingBox()[3], o.boundingBox()[1])
        for piece in (o, bar):
            self.assertGreaterEqual(measure.gap(n, piece), self.seam)

    def test_script_ell_loops_above_the_middle(self):
        # One stroke as tall as l (ROWS), whose loop closes above the hyphen's middle, where
        # every reference crosses its strokes.
        [piece] = self.pieces("ℓ")
        self.assertEqual(len(piece), 2)  # the stroke and its loop
        [loop] = [c for c in piece if not c.isClockwise()]
        _, y0, _, y1 = self.font["hyphen"].boundingBox()
        self.assertGreaterEqual(loop.boundingBox()[1], (y0 + y1) / 2)

    def test_estimated_sign_bar_runs_out_past_the_bowl(self):
        # e's bar run on to the left: the ink reaches at least a stroke further left than the
        # bowl above the eye does, as Fira Code's and Maple Mono's ℮ do.
        [piece] = self.pieces("℮")
        self.assertEqual(len(piece), 2)  # e's eye
        [eye] = [c for c in piece if not c.isClockwise()]
        bowl = geo.trim(piece, y0=eye.boundingBox()[3] + 20)
        [(h0, h1)] = measure.spans_at_x(self.font["hyphen"].foreground, ADVANCE / 2)
        self.assertGreaterEqual(bowl.boundingBox()[0] - piece.boundingBox()[0], h1 - h0)

    def test_degree_signs_put_a_small_ring_before_the_letter(self):
        # A ring at the top left, its top level with the letter's, before a letter standing
        # where the letter stands, as Maple Mono (the only reference) sets them; ApartTest
        # keeps them apart.
        for char, letter in (("℃", "C"), ("℉", "F")):
            with self.subTest(sign=char):
                pieces = sorted(self.pieces(char), key=lambda p: p.boundingBox()[0])
                self.assertEqual(len(pieces), 2)
                ring, body = pieces
                self.assertEqual(len(ring), 2)
                self.assertEqual(len(body), len(self.font[letter].foreground))
                _, _, rx1, r_top = ring.boundingBox()
                bx0, b_bottom, _, b_top = body.boundingBox()
                self.assertLess(rx1, bx0)
                self.assertAlmostEqual(r_top, b_top, delta=WOBBLE)
                self.assertAlmostEqual(b_bottom, self.font[letter].boundingBox()[1],
                                       delta=WOBBLE)


class KeyHintTest(unittest.TestCase):
    """⇦ ⇨ ⇩ are ⇧ turned (TURNED); ⇪ is ⇧ lifted over a bar; ⇞ ⇟ are ↑ ↓ with two bars."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))
        cls.weight = weight_tolerance(cls.font)

    def test_caps_lock_is_the_up_arrow_lifted_over_a_bar(self):
        # ⇧'s outline moved up, unchanged, over a bar of ⇧'s own stroke as wide as its shaft.
        # The references keep ⇪ at ⇧'s height with a smaller arrow; here ⇪A and ⇧A read as
        # one arrow.
        up = self.font[ord("⇧")].foreground
        pieces = measure.pieces(self.font[ord("⇪")].foreground)
        self.assertEqual(len(pieces), 2)
        arrow = max(pieces, key=lambda p: p.boundingBox()[3] - p.boundingBox()[1])
        [bar] = [p for p in pieces if p is not arrow]
        dy = arrow.boundingBox()[1] - up.boundingBox()[1]
        self.assertEqual(outline(arrow), outline(geo.transformed(up, psMat.translate(0, dy))))
        # The shaft's walls, a quarter of the way up: ⇧'s head takes its upper half.
        _, y0, _, y1 = up.boundingBox()
        (l0, l1), *_, (_, r1) = measure.spans_at_y(up, y0 + (y1 - y0) / 4)
        bx0, by0, bx1, by1 = bar.boundingBox()
        self.assertLess(by1, arrow.boundingBox()[1])
        self.assertAlmostEqual(by1 - by0, l1 - l0, delta=self.weight)
        self.assertAlmostEqual(bx0, l0, delta=WOBBLE)
        self.assertAlmostEqual(bx1, r1, delta=WOBBLE)

    def test_page_arrows_are_the_arrows_with_two_bars(self):
        # ↑ and ↓ whole, with two bars of the hyphen's stroke across the shaft, reaching past
        # it on both sides: Fira Code's span 61% of the arrow's width, Maple Mono's 95%.
        [(h0, h1)] = measure.spans_at_x(self.font["hyphen"].foreground, ADVANCE / 2)
        for char, plain in (("⇞", "↑"), ("⇟", "↓")):
            with self.subTest(arrow=char):
                layer = self.font[ord(char)].foreground
                arrow = self.font[ord(plain)].foreground
                self.assertGreaterEqual(measure.covered(arrow, layer), 0.99)
                _, y0, _, y1 = arrow.boundingBox()
                [(s0, s1)] = measure.spans_at_y(arrow, (y0 + y1) / 2)  # the shaft
                # Half a stroke out from the shaft: clear of it, short of the bars' round ends.
                for x in (s0 - (h1 - h0) / 2, s1 + (h1 - h0) / 2):
                    # Not the arrow's own spans, which may differ by both outlines' rounding.
                    own = measure.spans_at_x(arrow, x)
                    bars = [span for span in measure.spans_at_x(layer, x)
                            if not any(max(abs(span[0] - a), abs(span[1] - b)) <= 2 * ROUNDING
                                       for a, b in own)]
                    self.assertEqual(len(bars), 2, (x, bars))
                    for a, b in bars:
                        self.assertAlmostEqual(b - a, h1 - h0, delta=self.weight)


# Currency sign -> the letter it is built on, with bars of the hyphen's stroke through it.
LETTER_SIGNS = {"₽": "P", "₩": "W", "₺": "t", "₦": "N", "₱": "P"}
# Where a sign's bars cross a vertical line: (x, how many bars, whether they are the topmost
# spans there rather than the lowest). ₽'s bowl lies over its bar, W's arm over ₩'s bars, and
# ₹'s leg under its bars; ₦'s and ₱'s bars run out left of their letters, alone there (past
# the bars' rounded ends, which taper like the hyphen's).
BARS = {"₽": (300, 1, False), "₩": (40, 2, False), "₹": (120, 2, True), "₦": (40, 2, False),
        "₱": (40, 2, False)}
TICK_REACH = 100  # ₿'s ticks past B: Maple Mono's, the only reference's, reach 130
# How far ¢'s stroke runs past its c, above and below: at least the narrowest reference's,
# Maple Mono's at our cap height (Fira Code's 138 below and Intel One Mono's 130).
CENT_REACH = 117
# Dash look-alike -> the dash it is: the hyphen for ‐ and the non-breaking hyphen ‑, the en
# dash for the figure dash ‒ and the em dash for the horizontal bar ―, as their Unicode names
# say and as the references that have them draw them.
DASHES = {"‐": "-", "‑": "-", "‒": "–", "―": "—"}


class CurrencyTest(unittest.TestCase):
    """₽ ₩ ₺ ₦ ₱ are letters with bars and ₹ two bars over a small bowl; every bar is a
    piece of the hyphen's stroke, so it weighs as the hyphen's middle does. ₫ is đ over the
    em dash, both references, and ₿ is B with two ticks of |'s stroke through it."""

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))
        hyphen = cls.font["hyphen"].foreground
        x0, _, x1, _ = hyphen.boundingBox()
        # The stroke's thickness along the hyphen's straight middle, which the bars stretch.
        thickness = [y1 - y0 for x in range(round(x0) + 100, round(x1) - 100, 10)
                     for y0, y1 in measure.spans_at_x(hyphen, x)]
        # Give or take both edges' rounding, as weight_tolerance() allows.
        cls.stroke = (min(thickness) - 2 * ROUNDING, max(thickness) + 2 * ROUNDING)
        cls.weight = weight_tolerance(cls.font)

    def test_letter_signs_keep_their_letters_height(self):
        for sign, letter in LETTER_SIGNS.items():
            with self.subTest(sign=sign):
                _, y0, _, y1 = self.font[ord(sign)].boundingBox()
                _, ly0, _, ly1 = self.font[ord(letter)].boundingBox()
                self.assertAlmostEqual(y0, ly0, delta=ROUNDING)  # the sign's outline is rounded
                self.assertAlmostEqual(y1, ly1, delta=ROUNDING)

    def bars(self, sign, x):
        """The bars' (bottom, top) at x, lowest first."""
        _, count, topmost = BARS[sign]
        ink = measure.ink(self.font, self.font[ord(sign)].glyphname)
        spans = sorted(measure.spans_at_x(ink, x))
        bars = spans[-count:] if topmost else spans[:count]
        self.assertEqual(len(bars), count)
        return bars

    def test_bars_weigh_as_the_hyphen(self):
        low, high = self.stroke
        for sign, (x, *_) in BARS.items():
            with self.subTest(sign=sign):
                for y0, y1 in self.bars(sign, x):
                    self.assertGreaterEqual(y1 - y0, low)
                    self.assertLessEqual(y1 - y0, high)

    def test_rupee_bars_are_level(self):
        # Both bars run at one height across the left half, before the bowl and the leg join.
        x, *_ = BARS["₹"]
        for (a0, a1), (b0, b1) in zip(self.bars("₹", x), self.bars("₹", 2 * x), strict=True):
            self.assertAlmostEqual(a0, b0, delta=WOBBLE)
            self.assertAlmostEqual(a1, b1, delta=WOBBLE)

    def test_bitcoin_ticks_pass_through_the_letter(self):
        # Two ticks as thick as | rise above B and drop below it, and nothing else does.
        layer = self.font[ord("₿")].foreground
        _, y0, _, y1 = layer.boundingBox()
        _, b0, _, b1 = self.font["B"].boundingBox()
        self.assertGreaterEqual(y1 - b1, TICK_REACH)
        self.assertGreaterEqual(b0 - y0, TICK_REACH)
        bar = self.font["bar"].foreground
        _, bar0, _, bar1 = bar.boundingBox()
        [(s0, s1)] = measure.spans_at_y(bar, (bar0 + bar1) / 2)  # |'s stroke, at its middle
        for y in (b1 + TICK_REACH / 2, b0 - TICK_REACH / 2):
            with self.subTest(y=y):
                ticks = measure.spans_at_y(layer, y)
                self.assertEqual(len(ticks), 2)
                for a, b in ticks:
                    self.assertAlmostEqual(b - a, s1 - s0, delta=self.weight)

    def test_cent_is_c_with_a_stroke_through_it(self):
        # c whole, as each reference's ¢ holds its c, with a stroke past both ends.
        cent = self.font["cent"].foreground
        c = self.font["c"].foreground
        self.assertGreaterEqual(measure.covered(c, cent), 0.99)
        _, y0, _, y1 = cent.boundingBox()
        _, c0, _, c1 = c.boundingBox()
        self.assertGreaterEqual(y1 - c1, CENT_REACH)
        self.assertGreaterEqual(c0 - y0, CENT_REACH)

    def test_dong_is_the_letter_over_the_em_dash(self):
        # The em dash only moved, to lie under the letter, clear of it.
        glyph = self.font[ord("₫")]
        self.assertEqual(len(glyph.foreground), 0)
        refs = {name: matrix for name, matrix, *_ in glyph.references}
        letter, dash = self.font[ord("đ")], self.font[ord("—")]
        self.assertEqual(set(refs), {letter.glyphname, dash.glyphname})
        self.assertEqual(refs[letter.glyphname], psMat.identity())
        self.assertEqual(linear(refs[dash.glyphname]), linear(psMat.identity()))
        _, letter_bottom, _, _ = letter.boundingBox()
        _, _, _, dash_top = geo.transformed(dash.foreground, refs[dash.glyphname]).boundingBox()
        self.assertLess(dash_top, letter_bottom)

    def test_lira_bars_cross_the_stem(self):
        # Two bars left of t's stem, where nothing else of t is, and no sliver of its crossbar
        # left on either side: every span beside the stem is at least a stroke thick. The stem
        # stands alone halfway from x-height to t's top, above the bars; half a stroke beside
        # it a sliver would cling, and the bars are still at full weight.
        low, _ = self.stroke
        layer = self.font[ord("₺")].foreground
        _, _, _, top = self.font["t"].boundingBox()
        [(x0, x1)] = measure.spans_at_y(layer, (self.font.os2_xheight + top) / 2)
        beside = low / 2
        self.assertEqual(len(measure.spans_at_x(layer, x0 - beside)), 2)
        for x in (x0 - beside, x1 + beside):
            with self.subTest(x=x):
                for y0, y1 in measure.spans_at_x(layer, x):
                    self.assertGreaterEqual(y1 - y0, low)

    def test_dash_look_alikes_are_the_dashes(self):
        for char, dash in DASHES.items():
            with self.subTest(glyph=char):
                glyph = self.font[ord(char)]
                self.assertEqual(len(glyph.foreground), 0)
                [(name, matrix, *_)] = glyph.references
                self.assertEqual(name, self.font[ord(dash)].glyphname)
                self.assertEqual(matrix, psMat.identity())

    def test_triangular_bullet_is_the_small_triangle(self):
        # Maple Mono, the only reference with ‣, draws it 258 wide at our em, which is our ▸.
        glyph = self.font[ord("‣")]
        self.assertEqual(len(glyph.foreground), 0)
        [(name, matrix, *_)] = glyph.references
        self.assertEqual(name, self.font[ord("▸")].glyphname)
        self.assertEqual(matrix, psMat.identity())


if __name__ == "__main__":
    unittest.main()
