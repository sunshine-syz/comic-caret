"""Western and Central European Latin: the characters that complete the Windows code pages.

Run: python3 -m unittest discover tests

Rows, centering and accented letters are checked for every glyph in test_consistency.py.
"""
import math
import pathlib
import struct
import sys
import unicodedata
import unittest

import fontforge
import psMat

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # the tests' shared tolerances
import measure
from project import ADVANCE, ROOT, SFD
from test_consistency import ROUNDING, TOLERANCE

TTF = ROOT / "fonts" / "ComicCaret-Regular.ttf"
CODE_PAGE_BITS = {"cp1252": 0, "cp1250": 1, "cp1254": 4, "cp1257": 7}  # of ulCodePageRange1
# As heavy for their height as Intel One Mono's and Maple Mono's superscripts (0.16-0.17 of
# it); at 74, as Fira Code's, the 4's counter in ¼ ¾ closed up.
SMALL_STEM = (54, 4)
# Hole width over letter height in Maple Mono's º ª and ¼'s 4, the narrowest reference's.
COUNTER_FLOOR = {"o": 115 / 285, "a": 103 / 285, "four": 71 / 360}
# ™ © ® are lighter, as in every reference (43-66): an M at 74 has no room left for its
# counters, and a ring at our full weight crowds the letter inside it.
SIGN_STEM = (56, 4)
# The closest a fraction's slash comes to its figures: the narrowest reference's, Fira Code's ⅖ ⅘
# scaled to our cell (Maple Mono's ½ ¼ 22, Intel One Mono's ⅔ ⅖ 28).
FRACTION_CLEARANCE = 21
# The closest ‰'s slash comes to its rings: the narrowest reference's, Maple Mono's scaled to our
# cell (Fira Code's 33; Intel One Mono has no ‰).
PER_MILLE_CLEARANCE = 22
COMPOSITES = {"uni00AD": {"hyphen"}, "periodcentered": {"period"}, "Dcroat": {"Eth"},
              "Ldot": {"L", "periodcentered"}, "ldot": {"l", "periodcentered"},
              "Lcaron": {"L", "caron.alt"}, "lcaron": {"l", "caron.alt"},
              "quotedblleft": {"quoteleft"}, "quotedblright": {"quoteright"},
              "quotedblbase": {"comma"}}
# small component: (height as a fraction of the glyph's, and which of the strokes a line there
# crosses is upright): the stem, a bowl's side or the round side of 2 and 3. 7 has no upright
# stroke.
SMALL_PROBES = {"zero": (0.5, 0), "one": (0.5, 0), "two": (0.75, -1), "three": (0.75, -1),
                "four": (0.12, 0), "five": (0.8, 0), "six": (0.3, 0), "eight": (0.25, 0),
                "nine": (0.7, -1), "i": (0.3, 0), "n": (0.5, 0), "plus": (0.2, 0),
                "parenleft": (0.5, 0), "a": (0.5, 0), "o": (0.5, 0), "T": (0.4, 0),
                "M": (0.25, 0), "C": (0.5, 0), "R": (0.75, 0)}
# Each superscript and the subscript Unicode pairs with it.
SUPERSCRIPTS = "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾"
SUBSCRIPTS = "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎"
FRACTIONS = {"onequarter": ("one.small", "four.small"),
             "onehalf": ("one.small", "two.small"),
             "threequarters": ("three.small", "four.small"),
             "uni2153": ("one.small", "three.small"), "uni2154": ("two.small", "three.small"),
             "uni2155": ("one.small", "five.small"), "uni2156": ("two.small", "five.small"),
             "uni2157": ("three.small", "five.small"), "uni2158": ("four.small", "five.small"),
             "uni2159": ("one.small", "six.small"), "uni215A": ("five.small", "six.small"),
             "uni215B": ("one.small", "eight.small"), "uni215C": ("three.small", "eight.small"),
             "uni215D": ("five.small", "eight.small"), "uni215E": ("seven.small", "eight.small")}


def code_page(codec):
    """The printable characters of a Windows code page, and the soft hyphen."""
    chars = set()
    for byte in range(0x20, 0x100):
        try:
            char = bytes([byte]).decode(codec)
        except UnicodeDecodeError:
            continue
        if char.isprintable() or char == "­":
            chars.add(char)
    return chars


def code_page_range(path):
    """ulCodePageRange1 of the font's OS/2 table, read from the file itself."""
    data = path.read_bytes()
    for i in range(struct.unpack_from(">H", data, 4)[0]):
        tag, _, offset, _ = struct.unpack_from(">4sLLL", data, 12 + 16 * i)
        if tag == b"OS/2":
            return struct.unpack_from(">L", data, offset + 78)[0]
    raise ValueError(f"{path.name} has no OS/2 table")


class CoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def missing(self, chars):
        return {c for c in chars if ord(c) not in self.font}

    def test_code_pages_are_complete(self):
        for codec in CODE_PAGE_BITS:
            with self.subTest(codec=codec):
                self.assertEqual(self.missing(code_page(codec)), set())

    def test_latin_blocks_are_complete(self):
        # Latin-1 Supplement and Latin Extended-A, but ŉ, which Unicode deprecates.
        blocks = {chr(c) for c in range(0xA0, 0x180) if c != 0x149}
        self.assertEqual(self.missing(blocks), set())

    def test_decomposed_letters_stay_in_the_font(self):
        # Decomposed text, as in macOS file names and NFD output, needs every combining mark
        # the font's letters decompose to.
        missing = set()
        for glyph in self.font.glyphs():
            if glyph.unicode >= 0 and chr(glyph.unicode).isalpha():
                missing |= self.missing(unicodedata.normalize("NFD", chr(glyph.unicode)))
        self.assertEqual({f"U+{ord(c):04X}" for c in missing}, set())

    def test_built_font_declares_the_code_pages(self):
        # FontForge derives the flags from the cmap; CLAUDE.md keeps them out of the SFD.
        if not TTF.exists() or TTF.stat().st_mtime < SFD.stat().st_mtime:
            raise AssertionError(f"{TTF.name} is missing or older than {SFD.name}; "
                                 "run ./build.sh")
        declared = code_page_range(TTF)
        for codec, bit in CODE_PAGE_BITS.items():
            with self.subTest(codec=codec):
                self.assertTrue(declared >> bit & 1)


class LookalikeTest(unittest.TestCase):
    """Letters set apart from the ones they would otherwise read as."""
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))
        [(h0, h1)] = measure.spans_at_x(cls.font["hyphen"].foreground, ADVANCE / 2)
        cls.stroke = h1 - h0  # the hyphen's, at its middle

    def test_slash_runs_past_the_letter(self):
        # Past O, Ø reads apart from our slashed zero, whose slash stays inside it: by at least
        # half a stroke, so the slash's round end clears the bowl.
        for slashed, letter in (("Oslash", "O"), ("oslash", "o")):
            with self.subTest(glyph=slashed):
                _, bottom, _, top = self.font[slashed].boundingBox()
                _, letter_bottom, _, letter_top = self.font[letter].boundingBox()
                self.assertGreaterEqual(top - letter_top, self.stroke / 2)
                self.assertGreaterEqual(letter_bottom - bottom, self.stroke / 2)

    def test_zero_slash_stays_inside(self):
        ring = max(self.font["zero"].foreground, key=lambda c: c.boundingBox()[3])
        self.assertEqual(ring.boundingBox(), self.font["zero"].boundingBox())

    def test_H_bar_clears_the_crossbar(self):
        # A gap of at least a stroke keeps Ħ from reading as a filled block.
        spans = measure.spans_at_x(measure.ink(self.font, "Hbar"), ADVANCE / 2)
        self.assertEqual(len(spans), 2)
        self.assertGreaterEqual(spans[1][0] - spans[0][1], self.stroke)

    def test_sharp_s_stays_open_at_the_bottom(self):
        # The 3's lower end stops short of the stem, or ß reads as B: at least as far as the
        # narrowest reference's (Fira Code 69; Maple Mono 77, Intel One Mono 143).
        layer = self.font["germandbls"].foreground
        self.assertEqual(len(layer), 1)
        for y in (20, 40, 60):
            with self.subTest(y=y):
                (_, stem), (end, _) = measure.spans_at_y(layer, y)
                self.assertGreaterEqual(end - stem, 69)

    def test_sharp_s_waist_is_open(self):
        # The white between the stem and the 3's middle, where B's bowls meet its stem: at
        # least the narrowest reference's (Maple Mono 75; Fira Code 96, Intel One Mono 131).
        layer = self.font["germandbls"].foreground
        _, y0, _, y1 = layer.boundingBox()
        gaps = []
        for percent in range(30, 71):
            spans = measure.spans_at_y(layer, y0 + percent / 100 * (y1 - y0))
            if len(spans) >= 2:
                gaps.append(spans[1][0] - spans[0][1])
        self.assertGreaterEqual(min(gaps), 75)

    def test_capital_sharp_s_stays_open_at_the_bottom(self):
        # The bowl ends short of the stem, or ẞ reads as B: at least as far as the narrowest
        # reference's (Maple Mono 70 at 3-9 % of the height; Fira Code 84, Intel One Mono 129).
        layer = self.font["uni1E9E"].foreground
        _, y0, _, y1 = layer.boundingBox()
        for share in (0.03, 0.06, 0.09):
            with self.subTest(share=share):
                (_, stem), (end, _) = measure.spans_at_y(layer, y0 + share * (y1 - y0))
                self.assertGreaterEqual(end - stem, 70)

    def test_capital_sharp_s_middle_is_open(self):
        # The white between the stem and the diagonal, down to where it meets the bowl: at
        # least the narrowest reference's (Maple Mono 81; Fira Code 111, Intel One Mono 136).
        layer = self.font["uni1E9E"].foreground
        _, y0, _, y1 = layer.boundingBox()
        gaps = []
        for percent in range(30, 71):
            spans = measure.spans_at_y(layer, y0 + percent / 100 * (y1 - y0))
            if len(spans) >= 2:
                gaps.append(spans[1][0] - spans[0][1])
        self.assertGreaterEqual(min(gaps), 81)

    def test_eth_bar_crosses_its_stroke(self):
        # The bar tells ð from ∂: bar and rising stroke make one outline, the bar reaching past
        # the stroke both sides.
        layer = self.font["eth"].foreground
        crossing = measure.spans_at_y(layer, 540)
        self.assertEqual(len(crossing), 1)
        rising = measure.spans_at_y(layer, 400)[-1]
        self.assertGreater(crossing[0][1] - crossing[0][0], rising[1] - rising[0] + 100)

    def test_per_mille_rings_and_slash_stay_apart(self):
        contours = list(self.font["perthousand"].foreground)
        slash = fontforge.layer()
        slash += max(contours, key=lambda c: c.boundingBox()[3] - c.boundingBox()[1])
        rings = [c for c in contours if c.isClockwise() and c.boundingBox()[3] < 300]
        self.assertEqual(len(rings), 2)  # the lower two, side by side
        left, right = sorted((c.boundingBox() for c in rings), key=lambda b: b[0])
        # Apart beyond both rings' rounding; Maple Mono's join, Fira Code's keep 14.
        self.assertGreater(right[0] - left[2], 2 * ROUNDING)
        for contour in rings:
            ring = fontforge.layer()
            ring += contour
            self.assertGreaterEqual(measure.gap(slash, ring), PER_MILLE_CLEARANCE)


class CompositeTest(unittest.TestCase):
    """Glyphs that are another glyph, or a letter and a mark, as references."""
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_references(self):
        for name, refs in COMPOSITES.items():
            with self.subTest(glyph=name):
                self.assertEqual({r for r, *_ in self.font[name].references}, refs)
                self.assertEqual(len(self.font[name].foreground), 0)

    def test_soft_hyphen_is_the_hyphen(self):
        [(_, matrix, *_)] = self.font["uni00AD"].references
        self.assertEqual(matrix, psMat.identity())


class SmallFigureTest(unittest.TestCase):
    """The small figures, letters and signs that superscripts, subscripts, fractions, ª º ™ © ®
    are built from: the regular glyph scaled down, its strokes thickened back towards a regular
    stem."""
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def test_stems(self):
        for base, (height, index) in SMALL_PROBES.items():
            with self.subTest(glyph=f"{base}.small"):
                layer = self.font[f"{base}.small"].foreground
                _, y0, _, y1 = layer.boundingBox()
                a, b = measure.spans_at_y(layer, y0 + height * (y1 - y0))[index]
                weight, delta = SIGN_STEM if base in "TMCR" else SMALL_STEM
                self.assertAlmostEqual(b - a, weight, delta=delta)

    def test_counters_are_as_open_as_the_references(self):
        for base, floor in COUNTER_FLOOR.items():
            with self.subTest(glyph=f"{base}.small"):
                layer = self.font[f"{base}.small"].foreground
                _, y0, _, y1 = layer.boundingBox()
                [(x0, _, x1, _)] = [c.boundingBox() for c in layer if not c.isClockwise()]
                self.assertGreaterEqual((x1 - x0) / (y1 - y0), floor)

    def test_trademark_M_keeps_its_counters(self):
        # Its V stops short, as the references' do, leaving the bottom open; three quarters up,
        # their Ms keep 53-73 units of white.
        layer = self.font["M.small"].foreground
        _, y0, _, y1 = layer.boundingBox()
        self.assertEqual(len(measure.spans_at_y(layer, y0 + 0.25 * (y1 - y0))), 2)
        self.assertGreaterEqual(measure.counter(layer, y0 + 0.75 * (y1 - y0)), 53)

    def test_one_scale_for_each_set(self):
        # Letters shrink alike within a set: the figures, ª º, and ™ © ®.
        def ratio(base):
            _, y0, _, y1 = self.font[f"{base}.small"].boundingBox()
            _, b0, _, b1 = self.font[base].boundingBox()
            return (y1 - y0) / (b1 - b0)

        # The figures with the superscript letters and signs; ( ) are larger, to reach past
        # the figures as far as the references' do, and - = too thin to compare.
        figures = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
                   "nine", "i", "n", "plus")
        for group in (figures, ("a", "o"), ("T", "C", "R")):
            for base in group:
                with self.subTest(glyph=f"{base}.small"):
                    self.assertAlmostEqual(ratio(base), ratio(group[0]), delta=0.03)

    def test_trademark_letters_match(self):
        # As tall as each other within the hand's wobble, shrunk with the letters.
        _, t0, _, t1 = self.font["T.small"].boundingBox()
        _, m0, _, m1 = self.font["M.small"].boundingBox()
        _, b0, _, b1 = self.font["T"].boundingBox()
        self.assertAlmostEqual(t1 - t0, m1 - m0, delta=TOLERANCE * (t1 - t0) / (b1 - b0))


class FigureTest(unittest.TestCase):
    """Superscripts, fractions, ordinals and the signs built from the small components."""
    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(SFD))

    def part(self, glyph, component):
        """The component's ink where the glyph places it."""
        [matrix] = [m for r, m, *_ in self.font[glyph].references if r == component]
        layer = measure.ink(self.font, component)
        layer.transform(matrix)
        return layer

    def test_subscripts_are_the_superscripts_lowered(self):
        # The same small glyph, placed alike across, and all lowered by one distance.
        drops = set()
        for sup, sub in zip(SUPERSCRIPTS, SUBSCRIPTS, strict=True):
            with self.subTest(glyph=sub):
                self.assertEqual(len(self.font[ord(sub)].foreground), 0)
                [(a, m, *_)] = self.font[ord(sup)].references
                [(b, n, *_)] = self.font[ord(sub)].references
                self.assertEqual((a, tuple(m[:5])), (b, tuple(n[:5])))
                drops.add(m[5] - n[5])
        self.assertEqual(len(drops), 1)

    def test_fraction_bar_touches_neither_figure(self):
        for name, figures in FRACTIONS.items():
            bar = self.part(name, "slash.fraction")
            for figure in figures:
                with self.subTest(glyph=name, figure=figure):
                    self.assertGreaterEqual(measure.gap(bar, self.part(name, figure)),
                                            FRACTION_CLEARANCE)

    def test_fractions_place_their_figures_where_one_half_does(self):
        # Every numerator's ink stands centred where ½'s 1 is, its top at the 1's, and every
        # denominator where ½'s 2 is, its bottom at the 2's, so a row of fractions lines up.
        # Centred within the hand's wobble, as glyphs are in the cell; tops and bottoms to the
        # rounding of both figures' offsets.
        one = self.part("onehalf", "one.small")
        two = self.part("onehalf", "two.small")
        for name, (numerator, denominator) in FRACTIONS.items():
            with self.subTest(glyph=name):
                num, den = self.part(name, numerator), self.part(name, denominator)
                self.assertAlmostEqual(measure.ink_center(num), measure.ink_center(one),
                                       delta=TOLERANCE)
                self.assertAlmostEqual(num.boundingBox()[3], one.boundingBox()[3],
                                       delta=2 * ROUNDING)
                self.assertAlmostEqual(measure.ink_center(den), measure.ink_center(two),
                                       delta=TOLERANCE)
                self.assertAlmostEqual(den.boundingBox()[1], two.boundingBox()[1],
                                       delta=2 * ROUNDING)

    def test_fraction_bar_is_as_heavy_as_the_figures(self):
        bar = self.font["slash.fraction"].foreground
        _, y0, _, y1 = bar.boundingBox()
        [(a, b)] = measure.spans_at_y(bar, (y0 + y1) / 2)
        across = (b - a) * math.sin(math.radians(60))  # the bar leans at our slash's 60°
        self.assertAlmostEqual(across, SMALL_STEM[0], delta=SMALL_STEM[1])

    def test_ordinal_bars_are_as_heavy_as_the_letters_and_clear_them(self):
        # The bar keeps at least ●●'s seam from its letter, as a symbol's parts do
        # (test_symbols), so they stay apart at 16 px.
        left, _, right, _ = self.font[ord("●")].boundingBox()
        seam = 2 * min(left, ADVANCE - right)
        for name, letter in (("ordfeminine", "a.small"), ("ordmasculine", "o.small")):
            with self.subTest(glyph=name):
                bar = self.part(name, "bar.ordinal")
                x0, _, x1, _ = bar.boundingBox()
                [(t0, t1)] = measure.spans_at_x(bar, (x0 + x1) / 2)
                self.assertAlmostEqual(t1 - t0, SMALL_STEM[0], delta=SMALL_STEM[1])
                self.assertGreaterEqual(measure.gap(bar, self.part(name, letter)), seam)

    def test_trademark_letters_stay_apart(self):
        self.assertGreaterEqual(measure.gap(self.part("trademark", "T.small"),
                                            self.part("trademark", "M.small")), 15)

    def test_circled_letters_share_one_ring(self):
        self.assertEqual(self.part("copyright", "circle.copyright").boundingBox(),
                         self.part("registered", "circle.copyright").boundingBox())

    def test_circled_letters_sit_in_the_middle_with_room(self):
        # At least the 48 units the references leave around their © at the closest point;
        # around ® they leave 16-48.
        for name, letter in (("copyright", "C.small"), ("registered", "R.small")):
            with self.subTest(glyph=name):
                ring = self.part(name, "circle.copyright")
                inside = self.part(name, letter)
                rx0, ry0, rx1, ry1 = ring.boundingBox()
                x0, y0, x1, y1 = inside.boundingBox()
                # The letters are centered by their boxes; only the reference offset's rounding
                # to whole units can move the centre.
                self.assertAlmostEqual((x0 + x1) / 2, (rx0 + rx1) / 2, delta=ROUNDING)
                self.assertAlmostEqual((y0 + y1) / 2, (ry0 + ry1) / 2, delta=ROUNDING)
                self.assertGreaterEqual(measure.gap(ring, inside), 48)


if __name__ == "__main__":
    unittest.main()
