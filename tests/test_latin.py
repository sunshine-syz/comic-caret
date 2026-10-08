"""Western and Central European Latin: the characters that complete the Windows code pages.

Run: python3 -m unittest discover tests

Rows, centering and accented letters are checked for every glyph in test_consistency.py.
The bold runs these rules too (the Bold* classes), its floors measured from the reference bolds.
The floors the font gives (the hyphen's stroke, the pen) hold for it as they stand. Two keep the
regular's: ð's bar reaching 100 past its stroke, as the pen grows the bar's length and the
stroke's width alike, and ™'s 15 between T and M, a margin of our own (Fira Code's ™ joins them).
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
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))  # the tests' shared helpers
import make_bold
import measure
import sfnt
from helpers import require_current_build
from project import ADVANCE, BOLD_SFD, ROUNDING, SFD, SYMBOL_SIDE, WOBBLE, font_file

TTF = font_file("Regular", "ttf")
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
# scaled to our cell (Maple Mono's ½ ¼ 24, Intel One Mono's ⅔ ⅖ 30).
FRACTION_CLEARANCE = 22
# The white between ª º's bar and their letter: the narrowest reference's with a bar, Intel One
# Mono's at our cap height (Fira Code's 225; Maple Mono's ª º have none).
ORDINAL_CLEARANCE = 89
# The closest ‰'s slash comes to its rings: the narrowest reference's, Maple Mono's scaled to our
# cell (Fira Code's 36; Intel One Mono has no ‰).
PER_MILLE_CLEARANCE = 24

# The bold's floors, measured from the reference bolds as the ones above were from the
# regulars, scaled as tools/compare_glyphs.py scales: x to our advance, y to the bold's cap
# height. The narrowest reference bold's, rounded down; the others' in brackets.
# Hole width over letter height, a ratio compared at the same letter height, so in each
# reference's own units, as COUNTER_FLOOR's: Maple Mono's º, Fira Code's ª, Maple Mono's ¼'s 4
# (Maple Mono's ª 0.309, Intel One Mono's º 0.450; Fira Code's 4 is open).
BOLD_COUNTER_FLOOR = {"o": 93 / 285, "a": 255 / 909, "four": 49 / 360}
BOLD_FRACTION_CLEARANCE = 7  # Fira Code's ⅘ 7.4 (Maple Mono's ½ 10.0, Intel One Mono's ⅓ 24.1)
BOLD_ORDINAL_CLEARANCE = 86  # Intel One Mono's º 86.6 (Fira Code's 191)
BOLD_PER_MILLE_CLEARANCE = 21  # Maple Mono's 21.5 (Fira Code's 24.7)
# “ ” „ are two of their single mark (‘ ’ or the comma), level, not a copied outline.
COMPOSITES = {"periodcentered": {"period"}, "Dcroat": {"Eth"},
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
                "parenleft": (0.5, 0), "a": (0.7, -1), "o": (0.5, 0), "T": (0.4, 0),
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


OS2_CODE_PAGES = 78  # offset of OS/2.ulCodePageRange1


def code_page_range(path):
    """ulCodePageRange1 of the font's OS/2 table, read from the file itself."""
    return struct.unpack_from(">L", sfnt.tables(path)[b"OS/2"], OS2_CODE_PAGES)[0]


def hyphen_stroke(font):
    """The stroke's weight: the hyphen's, at its middle."""
    [(h0, h1)] = measure.spans_at_x(font["hyphen"].foreground, ADVANCE / 2)
    return h1 - h0


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
        require_current_build(("Regular",), ("ttf",))
        declared = code_page_range(TTF)
        for codec, bit in CODE_PAGE_BITS.items():
            with self.subTest(codec=codec):
                self.assertTrue(declared >> bit & 1)


class LookalikeTest(unittest.TestCase):
    """Letters set apart from the ones they would otherwise read as."""
    sfd = SFD
    per_mille_clearance = PER_MILLE_CLEARANCE
    # The floors the tests below take from the references, which they name.
    sharp_s_foot, sharp_s_waist, capital_sharp_s_foot, capital_sharp_s_middle = 69, 75, 68, 79
    slash_short = 0  # how much less than half a stroke Ø's slash may run past O

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(cls.sfd))
        cls.stroke = hyphen_stroke(cls.font)

    def test_slash_runs_past_the_letter(self):
        # Past O, Ø reads apart from our slashed zero, whose slash stays inside it: by at least
        # half a stroke, so the slash's round end clears the bowl.
        floor = self.stroke / 2 - self.slash_short
        for slashed, letter in (("Oslash", "O"), ("oslash", "o")):
            with self.subTest(glyph=slashed):
                _, bottom, _, top = self.font[slashed].boundingBox()
                _, letter_bottom, _, letter_top = self.font[letter].boundingBox()
                self.assertGreaterEqual(top - letter_top, floor)
                self.assertGreaterEqual(letter_bottom - bottom, floor)

    def test_middle_dot_l_ends_its_dot_past_the_l(self):
        # Over the l's foot, ŀ's dot reads as a mark on l. Fira Code, Maple Mono and Intel One
        # Mono end it 118, 104 and 148 past the l at our cell, into the next cell, and the five
        # reference bolds 65 to 135; ours keeps to its cell, so it ends past the l by less.
        ends = {}
        for name, matrix, *_ in self.font["ldot"].references:
            layer = measure.ink(self.font, name)
            layer.transform(matrix)
            ends[name] = layer.boundingBox()[2]
        self.assertGreater(ends["periodcentered"], ends["l"])

    def test_d_caron_clears_the_l_after_it(self):
        # ď's caron runs on into the next cell (test_sanity.py), where l's flag stands; it keeps
        # as far from it as two symbols side by side keep, SYMBOL_SIDE each. Grown by the pen
        # alone, the bold's would run into the flag, as Intel One Mono Bold's and Fira Code
        # Bold's do.
        l = measure.ink(self.font, "l")
        l.transform(psMat.translate(ADVANCE, 0))
        self.assertGreaterEqual(measure.gap(measure.ink(self.font, "dcaron"), l), 2 * SYMBOL_SIDE)

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
                self.assertGreaterEqual(end - stem, self.sharp_s_foot)

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
        self.assertGreaterEqual(min(gaps), self.sharp_s_waist)

    def test_capital_sharp_s_stays_open_at_the_bottom(self):
        # The bowl ends short of the stem, or ẞ reads as B: at least as far as the narrowest
        # reference's, at our cap height as a counter is compared (Maple Mono 68.6 at 3-9 % of
        # the height; Fira Code 89.2, Intel One Mono 147.1).
        layer = self.font["uni1E9E"].foreground
        _, y0, _, y1 = layer.boundingBox()
        for share in (0.03, 0.06, 0.09):
            with self.subTest(share=share):
                (_, stem), (end, _) = measure.spans_at_y(layer, y0 + share * (y1 - y0))
                self.assertGreaterEqual(end - stem, self.capital_sharp_s_foot)

    def test_capital_sharp_s_middle_is_open(self):
        # The white between the stem and the diagonal, down to where it meets the bowl: at
        # least the narrowest reference's, at our cap height (Maple Mono 79.5; Fira Code 117.9,
        # Intel One Mono 155.0).
        layer = self.font["uni1E9E"].foreground
        _, y0, _, y1 = layer.boundingBox()
        gaps = []
        for percent in range(30, 71):
            spans = measure.spans_at_y(layer, y0 + percent / 100 * (y1 - y0))
            if len(spans) >= 2:
                gaps.append(spans[1][0] - spans[0][1])
        self.assertGreaterEqual(min(gaps), self.capital_sharp_s_middle)

    def test_eth_bar_crosses_its_stroke(self):
        # The bar tells ð from ∂: bar and rising stroke make one outline, the bar reaching past
        # the stroke both sides.
        layer = self.font["eth"].foreground
        crossing = measure.spans_at_y(layer, 540)
        self.assertEqual(len(crossing), 1)
        # The rising stroke alone, just under the bar: below the bar's bottom, half a stroke in
        # from its left end.
        bottoms = [y0 for y0, y1 in measure.spans_at_x(layer, crossing[0][0] + self.stroke / 2)
                   if y0 < 540 < y1]
        self.assertEqual(len(bottoms), 1, "no ink at 540 half a stroke in from the bar's left end")
        rising = measure.spans_at_y(layer, bottoms[0] - 1)[-1]
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
            self.assertGreaterEqual(measure.gap(slash, ring), self.per_mille_clearance)


class CapitalTest(unittest.TestCase):
    """Capitals drawn the way the references agree on."""
    sfd = SFD

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(cls.sfd))
        cls.stroke = hyphen_stroke(cls.font)

    def test_J_bar_stays_left_of_the_stem(self):
        # No reference carries J's bar past the stem on the right: Fira Code's and Maple
        # Mono's runs left from it, Intel One Mono's J has none. Ours was the I's bar once,
        # 114 units past the stem. What the top reaches beyond the stem's right edge is its
        # round end's bulge, within the hand's wobble.
        layer = self.font["J"].foreground
        _, _, right, top = layer.boundingBox()
        [(_, stem)] = measure.spans_at_y(layer, top - 150)  # on the stem, below the bar
        self.assertLess(right - stem, WOBBLE)

    def test_Y_stem_stands_straight_under_the_notch(self):
        # Fira Code, Intel One Mono and Maple Mono all set Y's stem vertical under the notch;
        # ours once ran on down the right arm's slant, its foot 96 left of the notch. The foot
        # and the stem's middle both stay within a quarter of the stem's width of the notch:
        # the I's and T's stems drift 6 and 11 over their whole height.
        layer = self.font["Y"].foreground
        _, bottom, _, top = layer.boundingBox()
        notch = next(y for y in range(round(bottom), round(top), 2)  # the first line that
                     if len(measure.spans_at_y(layer, y)) == 2)        # crosses both arms
        (_, left), (right, _) = measure.spans_at_y(layer, notch)
        foot = bottom + self.stroke / 2  # above the round end
        [(x0, x1)] = measure.spans_at_y(layer, foot)
        [(m0, m1)] = measure.spans_at_y(layer, (foot + notch) / 2)
        for part, centre in (("foot", (x0 + x1) / 2), ("middle", (m0 + m1) / 2)):
            with self.subTest(part=part):
                self.assertLess(abs(centre - (left + right) / 2), (x1 - x0) / 4)


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

    def test_soft_hyphen_is_blank_and_a_cell_wide(self):
        # Shaping renderers draw nothing for it; terminals that reserve a cell keep one; and
        # one that draws a zero-width character's glyph over the previous cell (Alacritty)
        # must not strike through the letter before it.
        glyph = self.font["uni00AD"]
        self.assertEqual((len(glyph.references), len(glyph.foreground), glyph.width),
                         (0, 0, ADVANCE))


def stem_of(font, base):
    """The weight of `base`.small's upright stroke, where its SMALL_PROBES line crosses it."""
    layer = font[f"{base}.small"].foreground
    _, y0, _, y1 = layer.boundingBox()
    height, index = SMALL_PROBES[base]
    a, b = measure.spans_at_y(layer, y0 + height * (y1 - y0))[index]
    return b - a


class SmallFigureTest(unittest.TestCase):
    """The small figures, letters and signs that superscripts, subscripts, fractions, ª º ™ © ®
    are built from: the regular glyph scaled down, its strokes thickened back towards a regular
    stem."""
    sfd = SFD
    small_stem, sign_stem, counter_floor = SMALL_STEM, SIGN_STEM, COUNTER_FLOOR
    # Three quarters up ™'s M: Maple Mono's 57.5, the narrowest reference's, 51.9 at our cap
    # height. A counter, so compared at the same letter height.
    trademark_counter = 51

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(cls.sfd))

    def test_stems(self):
        for base in SMALL_PROBES:
            with self.subTest(glyph=f"{base}.small"):
                weight, delta = self.sign_stem if base in "TMCR" else self.small_stem
                self.assertAlmostEqual(stem_of(self.font, base), weight, delta=delta)

    def test_counters_are_as_open_as_the_references(self):
        for base, floor in self.counter_floor.items():
            with self.subTest(glyph=f"{base}.small"):
                layer = self.font[f"{base}.small"].foreground
                _, y0, _, y1 = layer.boundingBox()
                [(x0, _, x1, _)] = [c.boundingBox() for c in layer if not c.isClockwise()]
                self.assertGreaterEqual((x1 - x0) / (y1 - y0), floor)

    def test_trademark_M_keeps_its_counters(self):
        # Its V stops short, as the references' do, leaving the bottom open; three quarters up,
        # their Ms keep 52-78 units of white at our cap height.
        layer = self.font["M.small"].foreground
        _, y0, _, y1 = layer.boundingBox()
        self.assertEqual(len(measure.spans_at_y(layer, y0 + 0.25 * (y1 - y0))), 2)
        self.assertGreaterEqual(measure.counter(layer, y0 + 0.75 * (y1 - y0)),
                                self.trademark_counter)

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
        self.assertAlmostEqual(t1 - t0, m1 - m0, delta=WOBBLE * (t1 - t0) / (b1 - b0))


class FigureTest(unittest.TestCase):
    """Superscripts, fractions, ordinals and the signs built from the small components."""
    sfd = SFD
    small_stem = SMALL_STEM
    fraction_bar = SMALL_STEM  # the bar's weight normal to its lean
    fraction_clearance, ordinal_clearance = FRACTION_CLEARANCE, ORDINAL_CLEARANCE
    circle_room = 48  # around ©, the narrowest reference's

    @classmethod
    def setUpClass(cls):
        cls.font = fontforge.open(str(cls.sfd))

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
                                            self.fraction_clearance)

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
                                       delta=WOBBLE)
                self.assertAlmostEqual(num.boundingBox()[3], one.boundingBox()[3],
                                       delta=2 * ROUNDING)
                self.assertAlmostEqual(measure.ink_center(den), measure.ink_center(two),
                                       delta=WOBBLE)
                self.assertAlmostEqual(den.boundingBox()[1], two.boundingBox()[1],
                                       delta=2 * ROUNDING)

    def test_fraction_bar_is_as_heavy_as_the_figures(self):
        bar = self.font["slash.fraction"].foreground
        _, y0, _, y1 = bar.boundingBox()
        [(a, b)] = measure.spans_at_y(bar, (y0 + y1) / 2)
        across = (b - a) * math.sin(math.radians(60))  # the bar leans at our slash's 60°
        self.assertAlmostEqual(across, self.fraction_bar[0], delta=self.fraction_bar[1])

    def test_ordinal_bars_are_as_heavy_as_the_letters_and_clear_them(self):
        for name, letter in (("ordfeminine", "a.small"), ("ordmasculine", "o.small")):
            with self.subTest(glyph=name):
                bar = self.part(name, "bar.ordinal")
                x0, _, x1, _ = bar.boundingBox()
                [(t0, t1)] = measure.spans_at_x(bar, (x0 + x1) / 2)
                self.assertAlmostEqual(t1 - t0, self.small_stem[0], delta=self.small_stem[1])
                self.assertGreaterEqual(measure.gap(bar, self.part(name, letter)),
                                        self.ordinal_clearance)

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
                self.assertGreaterEqual(measure.gap(ring, inside), self.circle_room)

    def test_circled_letters_ring_is_as_heavy_as_the_letter(self):
        # The regular draws the ring at its letters' weight, so neither reads as the bolder.
        ring = self.font["circle.copyright"].foreground
        _, y0, _, y1 = ring.boundingBox()
        sides = measure.spans_at_y(ring, (y0 + y1) / 2)
        self.assertEqual(len(sides), 2)
        for base in "CR":
            for side, (x0, x1) in zip(("left", "right"), sides, strict=True):
                with self.subTest(letter=f"{base}.small", side=side):
                    self.assertAlmostEqual(x1 - x0, stem_of(self.font, base),
                                           delta=SIGN_STEM[1])


def bold_stems():
    """SMALL_STEM, SIGN_STEM and the fraction bar's weight for the bold: the regular's weights
    grown by the pen the bold grows the small parts by, read from the fonts: what the bold
    adds to one's stem across and to the hyphen's stroke up and down, scaled by one.small's
    stem over one's in the regular (tests/test_make_bold.py holds the bold to that share). The
    pen grows an upright stem by its width, and the leaning bar by its reach normal to the bar:
    turned by the bar's lean, so the bar lies level, its reach up and down."""
    regular, bold = fontforge.open(str(SFD)), fontforge.open(str(BOLD_SFD))

    def stem(font, name):
        return make_bold.middle_stroke(font[name].foreground, name)

    def thickness(font):
        _, y0, _, y1 = font["hyphen"].boundingBox()
        return y1 - y0
    share = stem(regular, "one.small") / stem(regular, "one")
    width = (stem(bold, "one") - stem(regular, "one")) * share
    height = (thickness(bold) - thickness(regular)) * share
    bar = 2 * make_bold.reach((width, height, math.radians(60)))[1]
    # The regular's stems and hyphen are exact, as drawn. The bold one's stem and the bold
    # hyphen each sit up to ROUNDING off what the pen grew them to, so the pen read here, and
    # each weight from it, is up to ROUNDING times the share off.
    off = ROUNDING * share
    return ((SMALL_STEM[0] + width, SMALL_STEM[1] + off),
            (SIGN_STEM[0] + width, SIGN_STEM[1] + off),
            (SMALL_STEM[0] + bar, SMALL_STEM[1] + off))


class BoldLookalikeTest(LookalikeTest):
    sfd = BOLD_SFD
    per_mille_clearance = BOLD_PER_MILLE_CLEARANCE
    # The reference bolds' narrowest. ß's per 1000 em, as the regular's: Fira Code's 34.2 at
    # its foot (Maple Mono's 65.6, Intel One Mono's 94.9) and 48.2 at its waist (65.0, 85.0).
    # ẞ's at the bold's cap height, as the regular's: Fira Code's 47.9 at its foot (Maple
    # Mono's 62.3, Intel One Mono's 107.9) and Maple Mono's 64.8 at its middle (Fira Code's
    # 76.0, Intel One Mono's 118.5).
    sharp_s_foot, sharp_s_waist, capital_sharp_s_foot, capital_sharp_s_middle = 34, 48, 47, 64
    # Known exception: Ø ø's slash need run past the bowl by only half the regular's stroke
    # (39.6), not half the bold's (46.6); it runs 45 past, as the regular's does. The pen
    # grows the slash's end and the bowl's top alike, by its half height, while half the
    # stroke grows as much. Running further would grow the slash past the pen, which
    # tests/test_make_bold.py holds every glyph to, so the bold keeps the regular's rows.
    slash_short = make_bold.PEN[1] / 2


class BoldCapitalTest(CapitalTest):
    sfd = BOLD_SFD


class BoldSmallFigureTest(SmallFigureTest):
    sfd = BOLD_SFD
    counter_floor = BOLD_COUNTER_FLOOR
    # Maple Mono Bold's 27.0, 24.6 at the bold's cap height (Intel One Mono Bold's 51.8).
    trademark_counter = 24

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_stem, cls.sign_stem, _ = bold_stems()


class BoldFigureTest(FigureTest):
    sfd = BOLD_SFD
    fraction_clearance, ordinal_clearance = BOLD_FRACTION_CLEARANCE, BOLD_ORDINAL_CLEARANCE
    circle_room = 41  # Fira Code Bold's 41.5 around its © (Intel One Mono's 47.2)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_stem, _, cls.fraction_bar = bold_stems()


if __name__ == "__main__":
    unittest.main()
